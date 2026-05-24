# =============================================================================
# Auditor de Contratos Públicos · Universidade de Santiago de Compostela
# Módulo: generación de informes PDF descargables.
# Autores: Xoán Xosé Pardal Pérez; Alberto Quian (apoyo metodológico y técnico).
# Esta aplicación es parte del proyecto de I+D+i:
# - XornalIA: Desarrollo, validación y transferencia de una plataforma integradora de soluciones de inteligencia artificial generativa para medios de comunicación (PDC2025-166024-I00).
# Licencia: MIT (https://opensource.org/license/mit).
# SPDX-License-Identifier: MIT
# =============================================================================

# pyright: reportMissingImports=false

"""Genera un informe PDF autocontenido (texto explicativo + tablas).

Pensado para que un periodista pueda compartir/imprimir el resultado del
análisis sin depender del navegador. Combina:

- una **introducción narrativa** que explica qué se ha analizado y cómo,
- el **resumen cuantitativo** (contratos, importes, alertas),
- la **tabla de casos prioritarios** con índice de riesgo y señales,
La librería usada es `reportlab`. Se evita embeber capturas de gráficos
interactivos porque en PDF pierden etiquetas, color y legibilidad.
"""
from __future__ import annotations

from datetime import datetime
from html import escape
from io import BytesIO

import pandas as pd  # type: ignore[import-not-found]
from reportlab.lib import colors  # type: ignore[import-not-found]
from reportlab.lib.pagesizes import A4  # type: ignore[import-not-found]
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # type: ignore[import-not-found]
from reportlab.lib.units import cm  # type: ignore[import-not-found]
from reportlab.platypus import (  # type: ignore[import-not-found]
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


# ---------------------------------------------------------------------------
# Estilos
# ---------------------------------------------------------------------------

def _estilos():
    base = getSampleStyleSheet()
    base.add(ParagraphStyle(
        name="HeroTitle",
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#1d1d1f"),
        spaceAfter=4,
    ))
    base.add(ParagraphStyle(
        name="HeroMeta",
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#666666"),
        spaceAfter=12,
    ))
    base.add(ParagraphStyle(
        name="Section",
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#c0392b"),
        spaceBefore=14,
        spaceAfter=6,
    ))
    base.add(ParagraphStyle(
        name="BodyJustified",
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#1f2937"),
        alignment=4,  # justify
        spaceAfter=6,
    ))
    base.add(ParagraphStyle(
        name="BodySmall",
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#4b5563"),
        spaceAfter=4,
    ))
    base.add(ParagraphStyle(
        name="Footnote",
        fontName="Helvetica-Oblique",
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor("#6b7280"),
        spaceAfter=2,
    ))
    return base


# ---------------------------------------------------------------------------
# Helpers de datos
# ---------------------------------------------------------------------------

def _euros(valor: float) -> str:
    if valor is None or pd.isna(valor):
        return "—"
    return f"{valor:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


def _resumen(radar: pd.DataFrame, df_input: pd.DataFrame) -> dict[str, object]:
    total_contratos = int(df_input.shape[0]) if df_input is not None else 0
    importe_total = (
        float(df_input["Importe_euros"].sum())
        if df_input is not None and "Importe_euros" in df_input.columns
        else 0.0
    )
    grupos = int(len(radar)) if radar is not None else 0
    if radar is not None and "Es_Alerta" in radar.columns:
        alertas_df = radar[radar["Es_Alerta"]]
    else:
        alertas_df = pd.DataFrame()
    alertas = int(len(alertas_df))
    importe_alertas = (
        float(alertas_df["Total_euros"].sum())
        if not alertas_df.empty and "Total_euros" in alertas_df.columns
        else 0.0
    )
    organos = (
        int(df_input["Organo"].nunique())
        if df_input is not None and "Organo" in df_input.columns
        else 0
    )
    proveedores = (
        int(df_input["Adjudicatario"].nunique())
        if df_input is not None and "Adjudicatario" in df_input.columns
        else 0
    )
    return {
        "contratos": f"{total_contratos:,}".replace(",", "."),
        "importe": _euros(importe_total),
        "organos": f"{organos:,}".replace(",", "."),
        "proveedores": f"{proveedores:,}".replace(",", "."),
        "grupos": f"{grupos:,}".replace(",", "."),
        "alertas": f"{alertas:,}".replace(",", "."),
        "importe_alertas": _euros(importe_alertas),
        "_alertas": alertas_df,
    }


def _narrativa(resumen: dict[str, object], titulo: str) -> list[str]:
    """Texto explicativo en lenguaje periodístico sobre el resultado."""
    parrafos: list[str] = []
    parrafos.append(
        "Este informe resume el análisis automatizado realizado por el "
        "<b>Auditor de Contratos Públicos</b> sobre la fuente "
        f"<b>{titulo}</b>. La herramienta no acusa: aplica los límites legales "
        "del artículo 118 de la Ley 9/2017 de Contratos del Sector Público "
        "(15.000 € en servicios y suministros, 40.000 € en obras) y señala "
        "agrupaciones cuyo importe acumulado roza o supera esos topes."
    )
    parrafos.append(
        f"En el conjunto analizado se han revisado <b>{resumen['contratos']}</b> "
        f"contratos por un importe total de <b>{resumen['importe']}</b>, "
        f"adjudicados por <b>{resumen['organos']}</b> órganos contratantes a "
        f"<b>{resumen['proveedores']}</b> proveedores distintos. El radar de "
        f"fraccionamiento ha generado <b>{resumen['grupos']}</b> grupos de "
        "análisis (mismo adjudicatario × mismo órgano × mismo tipo × mismo "
        f"año fiscal), de los cuales <b>{resumen['alertas']}</b> presentan "
        "indicios de fraccionamiento, sumando "
        f"<b>{resumen['importe_alertas']}</b>."
    )
    if int(str(resumen['alertas']).replace('.', '')) == 0:
        parrafos.append(
            "<b>No se han detectado alertas</b> con los umbrales actuales. "
            "Esto no significa que no existan irregularidades en la fuente: "
            "el filtro aplicado pudo haber sido restrictivo o el conjunto "
            "haber excluido al órgano sospechoso. Recomendamos repetir el "
            "análisis con otros filtros antes de descartar la fuente."
        )
    else:
        parrafos.append(
            "Las filas marcadas como alerta son <b>indicios estadísticos</b>, "
            "no pruebas. Antes de publicar conviene verificar el NIF del "
            "adjudicatario, pedir el expediente completo a transparencia y "
            "comprobar si los contratos son objetivamente separables o si "
            "responden a un mismo objeto fragmentado para evitar la licitación."
        )
    return parrafos


# ---------------------------------------------------------------------------
# Tablas
# ---------------------------------------------------------------------------

_COLUMNAS_INFORME = [
    ("Adjudicatario", 4.6),
    ("Organo", 4.4),
    ("Tipo_Contrato", 1.8),
    ("Año_Fiscal", 1.0),
    ("Num_Contratos", 1.0),
    ("Total_Formateado", 2.2),
    ("Porcentaje_Limite_Formateado", 1.6),
    ("Indice_Riesgo", 1.0),
]


def _tabla_alertas(alertas: pd.DataFrame, ancho_total: float) -> Table:
    if alertas is None or alertas.empty:
        return Table([["Sin alertas en este conjunto."]], colWidths=[ancho_total])
    cols = [c for c, _ in _COLUMNAS_INFORME if c in alertas.columns]
    pesos = [w for c, w in _COLUMNAS_INFORME if c in alertas.columns]
    suma = sum(pesos) or 1
    anchos = [ancho_total * (w / suma) for w in pesos]
    cabecera = [_parrafo_tabla(c.replace("_", " "), _TABLE_HEADER_STYLE, 34) for c in cols]
    cuerpo: list[list[Paragraph]] = []
    for _, fila in alertas.head(40).iterrows():
        cuerpo.append([
            _parrafo_tabla(
                fila.get(c),
                _TABLE_CELL_RIGHT_STYLE if c not in {"Adjudicatario", "Organo", "Tipo_Contrato"} else _TABLE_CELL_STYLE,
                44 if c in {"Adjudicatario", "Organo"} else 22,
            )
            for c in cols
        ])
    data = [cabecera] + cuerpo
    tabla = Table(data, colWidths=anchos, repeatRows=1)
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fff3f0")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (3, 0), (-1, -1), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d1d5db")),
    ]))
    return tabla


def _recortar(valor, max_chars: int = 60) -> str:
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return "—"
    texto = str(valor).replace("\n", " ").strip()
    if len(texto) <= max_chars:
        return texto
    return texto[: max_chars - 1].rstrip() + "…"


_TABLE_HEADER_STYLE = ParagraphStyle(
    name="TableHeaderWrapped",
    fontName="Helvetica-Bold",
    fontSize=6.4,
    leading=7.4,
    textColor=colors.white,
    wordWrap="CJK",
)
_TABLE_CELL_STYLE = ParagraphStyle(
    name="TableCellWrapped",
    fontName="Helvetica",
    fontSize=6.4,
    leading=7.8,
    textColor=colors.HexColor("#111827"),
    wordWrap="CJK",
)
_TABLE_CELL_RIGHT_STYLE = ParagraphStyle(
    name="TableCellWrappedRight",
    parent=_TABLE_CELL_STYLE,
    alignment=2,
)


def _parrafo_tabla(valor, estilo: ParagraphStyle, max_chars: int = 60) -> Paragraph:
    return Paragraph(escape(_recortar(valor, max_chars)), estilo)


def _tabla_resumen(resumen: dict[str, object], ancho_total: float) -> Table:
    filas = [
        ["Contratos analizados", resumen["contratos"]],
        ["Importe total", resumen["importe"]],
        ["Órganos contratantes", resumen["organos"]],
        ["Proveedores distintos", resumen["proveedores"]],
        ["Grupos analizados (radar)", resumen["grupos"]],
        ["Casos con alerta", resumen["alertas"]],
        ["Importe en grupos con alerta", resumen["importe_alertas"]],
    ]
    tabla = Table(filas, colWidths=[ancho_total * 0.55, ancho_total * 0.45])
    tabla.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.HexColor("#f8fafc"), colors.white]),
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#e5e7eb")),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return tabla


def _tabla_simple(df: pd.DataFrame, columnas: list[str], ancho_total: float, max_filas: int = 22) -> Table:
    if df is None or df.empty:
        return Table([["Sin datos."]], colWidths=[ancho_total])
    columnas_presentes = [col for col in columnas if col in df.columns]
    if not columnas_presentes:
        return Table([["Sin datos."]], colWidths=[ancho_total])
    df_filtrado = df.reindex(columns=columnas_presentes).head(max_filas).copy()
    pesos = [3.6 if col in {"Adjudicatario", "Organo"} else 1.4 for col in columnas_presentes]
    suma = sum(pesos) or 1
    anchos = [ancho_total * (peso / suma) for peso in pesos]
    data = [[_parrafo_tabla(col.replace("_", " "), _TABLE_HEADER_STYLE, 36) for col in columnas_presentes]]
    for _, fila in df_filtrado.iterrows():
        data.append([
            _parrafo_tabla(
                fila.get(col),
                _TABLE_CELL_RIGHT_STYLE if col not in {"Adjudicatario", "Organo", "entidad"} else _TABLE_CELL_STYLE,
                58 if col in {"Adjudicatario", "Organo", "entidad"} else 28,
            )
            for col in columnas_presentes
        ])
    tabla = Table(data, colWidths=anchos, repeatRows=1)
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (-2, 1), (-1, -1), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d1d5db")),
    ]))
    return tabla


def _tabla_top_adjudicatarios(df_input: pd.DataFrame, ancho_total: float) -> Table:
    if df_input is None or df_input.empty or not {"Adjudicatario", "Importe_euros"}.issubset(df_input.columns):
        return Table([["Sin datos."]], colWidths=[ancho_total])
    tabla = (
        df_input.dropna(subset=["Adjudicatario", "Importe_euros"])
        .groupby("Adjudicatario", dropna=False)
        .agg(Importe_total=("Importe_euros", "sum"), Contratos=("Importe_euros", "count"))
        .sort_values("Importe_total", ascending=False)
        .reset_index()
    )
    tabla["Importe_total"] = tabla["Importe_total"].map(_euros)
    return _tabla_simple(tabla, ["Adjudicatario", "Importe_total", "Contratos"], ancho_total)


def _tabla_relaciones(df_input: pd.DataFrame, ancho_total: float) -> Table:
    columnas = {"Organo", "Adjudicatario", "Importe_euros"}
    if df_input is None or df_input.empty or not columnas.issubset(df_input.columns):
        return Table([["Sin datos."]], colWidths=[ancho_total])
    tabla = (
        df_input.dropna(subset=["Organo", "Adjudicatario", "Importe_euros"])
        .groupby(["Organo", "Adjudicatario"], dropna=False)
        .agg(Importe_total=("Importe_euros", "sum"), Contratos=("Importe_euros", "count"))
        .sort_values("Importe_total", ascending=False)
        .reset_index()
    )
    tabla["Importe_total"] = tabla["Importe_total"].map(_euros)
    return _tabla_simple(tabla, ["Organo", "Adjudicatario", "Importe_total", "Contratos"], ancho_total)


# ---------------------------------------------------------------------------
# Construcción del PDF
# ---------------------------------------------------------------------------

def render_informe_pdf(
    *,
    titulo: str,
    radar: pd.DataFrame,
    df_input: pd.DataFrame,
    figuras: list,
    introduccion: str | None = None,
) -> bytes:
    """Devuelve los bytes de un PDF con resumen, tablas y gráficos."""
    buffer = BytesIO()
    margen = 1.6 * cm
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=margen,
        rightMargin=margen,
        topMargin=margen,
        bottomMargin=margen,
        title=titulo,
        author="Auditor de Contratos Públicos",
    )
    estilos = _estilos()
    ancho = A4[0] - 2 * margen
    historia = []

    historia.append(Paragraph(titulo, estilos["HeroTitle"]))
    historia.append(Paragraph(
        f"Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')} · "
        "Auditor de Contratos Públicos",
        estilos["HeroMeta"],
    ))

    resumen = _resumen(radar, df_input)
    if introduccion:
        historia.append(Paragraph(introduccion, estilos["BodyJustified"]))
        historia.append(Spacer(1, 6))

    historia.append(Paragraph("Resumen ejecutivo", estilos["Section"]))
    for parrafo in _narrativa(resumen, titulo):
        historia.append(Paragraph(parrafo, estilos["BodyJustified"]))
    historia.append(Spacer(1, 6))
    historia.append(_tabla_resumen(resumen, ancho))

    historia.append(Paragraph("Casos con alerta de fraccionamiento", estilos["Section"]))
    historia.append(Paragraph(
        "Se listan los grupos cuyo importe acumulado supera el 90 % del límite "
        "legal aplicable a su tipo de contrato. La columna <b>Índice_Riesgo</b> "
        "ordena los casos de 0 a 100 combinando porcentaje sobre el límite, "
        "número de contratos, importes pegados al umbral y concentración temporal.",
        estilos["BodySmall"],
    ))
    alertas_resumen = resumen.get("_alertas")
    alertas_df = alertas_resumen if isinstance(alertas_resumen, pd.DataFrame) else pd.DataFrame()
    historia.append(_tabla_alertas(alertas_df, ancho))

    historia.append(Paragraph("Tablas de contexto", estilos["Section"]))
    historia.append(Paragraph(
        "Para compartir en redacción, el grafo interactivo se resume como tablas: "
        "top de adjudicatarios y relaciones órgano-adjudicatario con mayor importe acumulado.",
        estilos["BodySmall"],
    ))
    historia.append(Paragraph("Top adjudicatarios", estilos["BodySmall"]))
    historia.append(_tabla_top_adjudicatarios(df_input, ancho))
    historia.append(Spacer(1, 8))
    historia.append(Paragraph("Relaciones principales órgano-adjudicatario", estilos["BodySmall"]))
    historia.append(_tabla_relaciones(df_input, ancho))

    historia.append(Paragraph("Visualizaciones", estilos["Section"]))
    historia.append(Paragraph(
        "El informe HTML descargable incluye los gráficos interactivos. "
        "Este PDF prioriza texto y tablas para impresión; para imágenes, usa "
        "el ZIP de PNG generado desde los mismos gráficos de la interfaz.",
        estilos["BodySmall"],
    ))

    historia.append(Spacer(1, 14))
    historia.append(Paragraph(
        "Datos procesados localmente. Las alertas son indicios estadísticos, "
        "no acusación: requieren contraste documental. Límites legales: Ley "
        "9/2017, art. 118.",
        estilos["Footnote"],
    ))
    doc.build(historia)
    return buffer.getvalue()
