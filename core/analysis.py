# =============================================================================
# Auditor de Contratos Públicos · Universidade de Santiago de Compostela
# Módulo: radar de fraccionamiento y escáner forense.
# Autores: Xoán Xosé Pardal Pérez; Alberto Quian (apoyo metodológico y técnico).
# Esta aplicación es parte de los proyectos de I+D+i:
# - Inteligencia artificial en medios digitales en España: efectos y roles (PID2024-156034OB-C22).
# - XornalIA: Desarrollo, validación y transferencia de una plataforma integradora de soluciones de inteligencia artificial generativa para medios de comunicación (PDC2025-166024-I00).
# Licencia: MIT (https://opensource.org/license/mit).
# SPDX-License-Identifier: MIT
# =============================================================================

"""Análisis: radar de fraccionamiento de contratos menores y escáner forense."""
from __future__ import annotations

import re
import pandas as pd

from .constants import (
    LIMITE_OBRAS,
    LIMITE_SERVICIOS,
    PATRONES,
    UMBRAL_ALERTA_OBRAS,
    UMBRAL_ALERTA_SERVICIOS,
)
from .money import formatear_euros, limpiar_dinero


def _limite_para_tipo(tipo: str) -> float:
    return LIMITE_OBRAS if "obra" in (tipo or "").lower() else LIMITE_SERVICIOS


def _porcentaje_formateado(valor: float | None) -> str:
    if valor is None or pd.isna(valor):
        return "—"
    return f"{valor:.1f} %".replace(".", ",")


def parsear_fechas_mixtas(valores) -> pd.Series:
    """Parsea fechas españolas e ISO sin que `dayfirst` invierta YYYY-MM-DD."""
    serie = pd.Series(valores)
    fechas = pd.Series(pd.NaT, index=serie.index, dtype="datetime64[ns]")
    mascara_iso = serie.astype(str).str.match(r"^\d{4}-\d{1,2}-\d{1,2}(?:\s|$)")
    if mascara_iso.any():
        fechas.loc[mascara_iso] = pd.to_datetime(serie.loc[mascara_iso], errors="coerce")
    if (~mascara_iso).any():
        fechas.loc[~mascara_iso] = pd.to_datetime(
            serie.loc[~mascara_iso], errors="coerce", dayfirst=True
        )
    return fechas


# -----------------------------------------------------------------------------
# Escáner forense (PDFs y CSVs sueltos)
# -----------------------------------------------------------------------------

def analizar_texto_por_pagina(textos: dict[int, str], filtros: dict[str, bool]) -> pd.DataFrame:
    """Aplica los patrones regex a un dict {pagina: texto}."""
    filas: list[dict] = []
    for num_pag, texto in textos.items():
        if not texto:
            continue
        for nombre, activo in filtros.items():
            if not activo:
                continue
            for match in re.finditer(PATRONES[nombre], texto):
                ini = max(0, match.start() - 45)
                fin = min(len(texto), match.end() + 45)
                ctx = "..." + texto[ini:fin].replace("\n", " ") + "..."
                filas.append({
                    "Localizacion": f"Pág. {num_pag}",
                    "Tipo": nombre,
                    "Valor": match.group(),
                    "Contexto": ctx,
                })
    return pd.DataFrame(filas)


def detectar_banderas(df: pd.DataFrame) -> pd.DataFrame:
    """Marca con una bandera los importes sospechosos (rozan límite o trampa de IVA)."""
    if df.empty:
        return df

    def _bandera(row):
        if row.get("Tipo") != "Importes (€)":
            return "OK"
        n = limpiar_dinero(row["Valor"])
        if n is None:
            return "OK"
        if 14_000 <= n <= LIMITE_SERVICIOS:
            return "🚩 Roza 15k (sin IVA)"
        if 39_000 <= n <= LIMITE_OBRAS:
            return "🚩 Roza 40k — Obras (sin IVA)"
        if 17_900 <= n <= 18_150:
            return "🚨 Trampa IVA 21% ≈ 15k sin IVA"
        if 47_500 <= n <= 48_400:
            return "🚨 Trampa IVA 21% ≈ 40k sin IVA"
        if 16_300 <= n <= 16_500:
            return "🚨 Trampa IVA 10% ≈ 15k sin IVA"
        return "OK"

    df = df.copy()
    df["Bandera"] = df.apply(_bandera, axis=1)
    return df


# -----------------------------------------------------------------------------
# Radar de fraccionamiento ("pitufeo")
# -----------------------------------------------------------------------------

def ejecutar_radar(df_input: pd.DataFrame, min_contratos: int = 2) -> pd.DataFrame:
    """Detecta empresas que acumulan contratos menores superando el límite legal.

    Agrupa por (Adjudicatario, Órgano, Tipo_Contrato, Año_Fiscal). Excluye
    adjudicatarios desconocidos y contratos sin año fiscal.
    """
    if df_input.empty:
        return pd.DataFrame()

    df = df_input[
        df_input["_Adjudicatario_Radar"].notna()
        & df_input["Año_Fiscal"].notna()
        & df_input["Importe_euros"].notna()
    ].copy()

    if df.empty:
        return pd.DataFrame()

    if "Fecha" in df.columns:
        df["_Fecha_Parsed"] = parsear_fechas_mixtas(df["Fecha"]).values
    else:
        df["_Fecha_Parsed"] = pd.NaT

    grupo = ["_Adjudicatario_Radar", "Organo", "Tipo_Contrato", "Año_Fiscal"]
    radar = df.groupby(grupo).agg(
        Total_euros=("Importe_euros", "sum"),
        Num_Contratos=("Importe_euros", "count"),
        _Importes_Num=("Importe_euros", lambda x: sorted(float(v) for v in x.dropna())),
        Primera_Fecha=("_Fecha_Parsed", "min"),
        Ultima_Fecha=("_Fecha_Parsed", "max"),
        Importes_Individuales=(
            "Importe_euros",
            lambda x: " | ".join(formatear_euros(v) for v in sorted(x, reverse=True)),
        ),
    ).reset_index().rename(columns={"_Adjudicatario_Radar": "Adjudicatario"})

    def _alerta(row) -> bool:
        if row["Num_Contratos"] < min_contratos:
            return False
        umbral = UMBRAL_ALERTA_OBRAS if row["Tipo_Contrato"] == "Obras" else UMBRAL_ALERTA_SERVICIOS
        return row["Total_euros"] >= umbral

    radar["Es_Alerta"] = radar.apply(_alerta, axis=1)
    radar["Limite_Num"] = radar["Tipo_Contrato"].apply(_limite_para_tipo)
    radar["Porcentaje_Limite"] = (radar["Total_euros"] / radar["Limite_Num"] * 100).round(1)

    def _riesgo(row) -> str:
        if not row["Es_Alerta"]:
            return "✅ Sin alerta"
        pct = row["Total_euros"] / row["Limite_Num"]
        if pct >= 1.0:
            return "🚨 Acumulado > límite legal"
        if pct >= 0.95:
            return "🔴 Roza el límite (>95%)"
        return "🟠 Cerca del límite (>90%)"

    def _dias_entre(row):
        if pd.isna(row["Primera_Fecha"]) or pd.isna(row["Ultima_Fecha"]):
            return pd.NA
        return int((row["Ultima_Fecha"] - row["Primera_Fecha"]).days)

    def _senales(row) -> str:
        senales: list[str] = []
        pct = row["Porcentaje_Limite"]
        importes = row.get("_Importes_Num", []) or []

        if pct >= 100:
            senales.append("acumulado superior al límite legal")
        elif pct >= 95:
            senales.append("acumulado por encima del 95 % del límite")
        elif pct >= 90:
            senales.append("acumulado por encima del 90 % del límite")

        if row["Num_Contratos"] >= 4:
            senales.append(f"proveedor recurrente ({int(row['Num_Contratos'])} contratos)")
        elif row["Num_Contratos"] >= 2:
            senales.append("varios contratos al mismo proveedor")

        if row["Tipo_Contrato"] == "Obras":
            cerca_umbral = any(39_000 <= v <= 40_000 for v in importes)
        else:
            cerca_umbral = any(14_000 <= v <= 15_000 for v in importes)
        if cerca_umbral:
            senales.append("importe individual pegado al umbral")

        if len(importes) != len(set(importes)):
            senales.append("importes repetidos exactamente")

        dias = row.get("Dias_Entre_Contratos")
        if not pd.isna(dias) and row["Num_Contratos"] >= 2 and dias <= 45:
            senales.append(f"contratos concentrados en {int(dias)} días")

        return " · ".join(senales) if senales else "Sin señales adicionales"

    def _indice(row) -> int:
        pct = row["Porcentaje_Limite"] / 100
        puntos = min(45, pct * 35)
        if pct >= 1.0:
            puntos += 20
        elif pct >= 0.95:
            puntos += 15
        elif pct >= 0.90:
            puntos += 10

        puntos += min(20, max(0, row["Num_Contratos"] - 1) * 8)
        senales = row["Señales_Riesgo"]
        if "pegado al umbral" in senales:
            puntos += 10
        if "concentrados" in senales:
            puntos += 8
        if "repetidos" in senales:
            puntos += 5
        return int(round(min(100, puntos)))

    def _prioridad(indice: int) -> str:
        if indice >= 75:
            return "Alta"
        if indice >= 50:
            return "Media"
        if indice >= 25:
            return "Baja"
        return "Informativa"

    radar["Nivel_Riesgo"] = radar.apply(_riesgo, axis=1)
    radar["Dias_Entre_Contratos"] = radar.apply(_dias_entre, axis=1)
    radar["Señales_Riesgo"] = radar.apply(_senales, axis=1)
    radar["Indice_Riesgo"] = radar.apply(_indice, axis=1)
    radar["Prioridad"] = radar["Indice_Riesgo"].apply(_prioridad)
    radar["Porcentaje_Limite_Formateado"] = radar["Porcentaje_Limite"].apply(_porcentaje_formateado)
    radar["Total_Formateado"] = radar["Total_euros"].apply(formatear_euros)
    radar["Limite_Legal"] = radar["Limite_Num"].apply(formatear_euros)

    return radar.sort_values(["Indice_Riesgo", "Total_euros"], ascending=False)


def pintar_filas_banderas(row):
    bandera = str(row.get("Bandera", ""))
    if "🚨" in bandera:
        return ["background-color: #ffebcc; color: black"] * len(row)
    if "🚩" in bandera:
        return ["background-color: #ffcccc; color: black"] * len(row)
    return [""] * len(row)
