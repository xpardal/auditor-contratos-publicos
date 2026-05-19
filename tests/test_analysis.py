# =============================================================================
# Auditor de Contratos Públicos · Universidade de Santiago de Compostela
# Pruebas: radar de fraccionamiento, fechas y banderas forenses.
# Autores: Xoán Xosé Pardal Pérez; Alberto Quian (apoyo metodológico y técnico).
# Esta aplicación es parte de los proyectos de I+D+i:
# - Inteligencia artificial en medios digitales en España: efectos y roles (PID2024-156034OB-C22).
# - XornalIA: Desarrollo, validación y transferencia de una plataforma integradora de soluciones de inteligencia artificial generativa para medios de comunicación (PDC2025-166024-I00).
# Licencia: MIT (https://opensource.org/license/mit).
# SPDX-License-Identifier: MIT
# =============================================================================

"""Tests del radar de fraccionamiento y escáner de banderas."""
from __future__ import annotations

import pandas as pd

from core.analysis import detectar_banderas, ejecutar_radar, parsear_fechas_mixtas


def _df_contratos(filas):
    """Construye un DataFrame con la forma esperada por ejecutar_radar."""
    df = pd.DataFrame(filas)
    if "_Adjudicatario_Radar" not in df.columns:
        df["_Adjudicatario_Radar"] = df["Adjudicatario"]
    return df


def test_radar_dispara_alerta_servicios_acumulados():
    df = _df_contratos([
        {"Adjudicatario": "ACME SL", "Organo": "Concello X",
         "Tipo_Contrato": "Servicios", "Año_Fiscal": 2024,
         "Importe_euros": 7000},
        {"Adjudicatario": "ACME SL", "Organo": "Concello X",
         "Tipo_Contrato": "Servicios", "Año_Fiscal": 2024,
         "Importe_euros": 7000},
    ])
    radar = ejecutar_radar(df, min_contratos=2)
    assert len(radar) == 1
    fila = radar.iloc[0]
    assert fila["Es_Alerta"]
    assert fila["Num_Contratos"] == 2
    assert fila["Total_euros"] == 14000
    assert fila["Indice_Riesgo"] >= 50
    assert "90 %" in fila["Señales_Riesgo"]
    assert fila["Prioridad"] in {"Media", "Alta"}


def test_radar_no_alerta_si_falta_minimo_contratos():
    df = _df_contratos([
        {"Adjudicatario": "ACME SL", "Organo": "Concello X",
         "Tipo_Contrato": "Servicios", "Año_Fiscal": 2024,
         "Importe_euros": 14000},
    ])
    radar = ejecutar_radar(df, min_contratos=2)
    assert bool(radar.iloc[0]["Es_Alerta"]) is False


def test_radar_excluye_adjudicatario_desconocido():
    df = pd.DataFrame([
        {"Adjudicatario": "No consta", "_Adjudicatario_Radar": None,
         "Organo": "Concello X", "Tipo_Contrato": "Servicios",
         "Año_Fiscal": 2024, "Importe_euros": 14000},
        {"Adjudicatario": "No consta", "_Adjudicatario_Radar": None,
         "Organo": "Concello X", "Tipo_Contrato": "Servicios",
         "Año_Fiscal": 2024, "Importe_euros": 14000},
    ])
    assert ejecutar_radar(df).empty


def test_radar_obras_usa_umbral_propio():
    df = _df_contratos([
        {"Adjudicatario": "OBRAS SA", "Organo": "Diputación",
         "Tipo_Contrato": "Obras", "Año_Fiscal": 2024, "Importe_euros": 20000},
        {"Adjudicatario": "OBRAS SA", "Organo": "Diputación",
         "Tipo_Contrato": "Obras", "Año_Fiscal": 2024, "Importe_euros": 20000},
    ])
    fila = ejecutar_radar(df, min_contratos=2).iloc[0]
    assert fila["Es_Alerta"]
    assert fila["Nivel_Riesgo"] == "🚨 Acumulado > límite legal"


def test_detectar_banderas_marca_trampa_iva_21():
    df = pd.DataFrame([
        {"Tipo": "Importes (€)", "Valor": "18.000 €"},
        {"Tipo": "Importes (€)", "Valor": "1.000 €"},
    ])
    out = detectar_banderas(df)
    assert out.iloc[0]["Bandera"].startswith("🚨")
    assert out.iloc[1]["Bandera"] == "OK"


def test_detectar_banderas_marca_roza_15k():
    df = pd.DataFrame([{"Tipo": "Importes (€)", "Valor": "14.500 €"}])
    out = detectar_banderas(df)
    assert "Roza" in out.iloc[0]["Bandera"]


def test_parsear_fechas_mixtas_respeta_iso_y_formato_es():
    fechas = parsear_fechas_mixtas(["2024-01-28", "28/01/2024"])
    assert fechas.dt.strftime("%Y-%m-%d").tolist() == ["2024-01-28", "2024-01-28"]


def test_radar_detecta_concentracion_temporal_e_importe_pegado_al_umbral():
    df = _df_contratos([
        {"Adjudicatario": "ACME SL", "Organo": "Concello X",
         "Tipo_Contrato": "Servicios", "Año_Fiscal": 2024,
         "Importe_euros": 14900, "Fecha": "2024-01-10"},
        {"Adjudicatario": "ACME SL", "Organo": "Concello X",
         "Tipo_Contrato": "Servicios", "Año_Fiscal": 2024,
         "Importe_euros": 14500, "Fecha": "2024-01-28"},
    ])
    fila = ejecutar_radar(df, min_contratos=2).iloc[0]
    assert fila["Es_Alerta"]
    assert fila["Dias_Entre_Contratos"] == 18
    assert "pegado al umbral" in fila["Señales_Riesgo"]
    assert "concentrados" in fila["Señales_Riesgo"]
    assert fila["Porcentaje_Limite"] > 190
