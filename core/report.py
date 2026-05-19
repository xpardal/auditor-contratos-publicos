# =============================================================================
# Auditor de Contratos Públicos · Universidade de Santiago de Compostela
# Módulo: generación de informes HTML autoportantes.
# Autores: Xoán Xosé Pardal Pérez; Alberto Quian (apoyo metodológico y técnico).
# Esta aplicación es parte de los proyectos de I+D+i: PID2024-156034OB-C22 y XornalIA (PDC2025-166024-I00).
# Licencia: MIT (https://opensource.org/license/mit).
# SPDX-License-Identifier: MIT
# =============================================================================

"""Generación de informes HTML autocontenidos para entidades/órganos.

El informe combina lectura periodística, tablas de contexto y gráficos Plotly
interactivos embebidos para que se vean como en la interfaz de Streamlit.
"""
from __future__ import annotations

import copy
from datetime import datetime
from html import escape
from io import BytesIO, StringIO
from zipfile import ZIP_DEFLATED, ZipFile

import pandas as pd
import plotly.io as pio

from .visual import es_figura_vacia

try:  # exportación estática opcional
    import kaleido  # noqa: F401
    _KALEIDO_OK = True
except Exception:  # pragma: no cover - dependencia opcional
    _KALEIDO_OK = False


_PLANTILLA = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>{titulo}</title>
<style>
  :root {{ color-scheme: light; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        max-width: 1120px; margin: 24px auto; padding: 0 24px; color: #1d1d1f;
        background: #fff;
        overflow-x: hidden;
  }}
  header {{ border-bottom: 1px solid #ddd; padding-bottom: 16px; margin-bottom: 24px; }}
  h1 {{ margin: 0 0 6px; font-size: 1.6rem; }}
  h2 {{ font-size: 1.15rem; margin-top: 2rem; border-left: 3px solid #c0392b; padding-left: 10px; }}
    h3 {{ margin: 0 0 10px; font-size: 1rem; }}
  .meta {{ color: #555; font-size: 0.9rem; }}
    .note {{ background: #f8fafc; border: 1px solid #e2e8f0; padding: 12px 14px; border-radius: 8px; line-height: 1.45; }}
    .table-wrap {{ width: 100%; max-width: 100%; overflow-x: hidden; }}
    table {{ border-collapse: collapse; width: 100%; max-width: 100%; table-layout: fixed; font-size: 0.86rem; }}
    th, td {{ border: 1px solid #e0e0e0; padding: 6px 8px; text-align: left; vertical-align: top; overflow-wrap: anywhere; word-break: normal; }}
  th {{ background: #f6f6f6; }}
  .alerta {{ background: #fff3f0; }}
    .grid {{ display: grid; grid-template-columns: 1fr; gap: 20px; }}
    .figures {{ display: grid; grid-template-columns: 1fr; gap: 28px; margin-top: 12px; }}
    .figure-wrap {{ width: 100%; max-width: 100%; overflow: hidden; border: 1px solid #e5e7eb; border-radius: 8px; padding: 8px 8px 0; background: #fff; }}
    .figure-wrap h3 {{ margin: 6px 8px 0; color: #1f2937; }}
    @media print {{
        body {{ max-width: none; margin: 0; padding: 12mm; overflow-x: visible; }}
        table {{ font-size: 0.74rem; }}
        .figures {{ display: none; }}
    }}
  footer {{ margin-top: 40px; color: #777; font-size: 0.8rem; border-top: 1px solid #eee; padding-top: 12px; }}
</style>
</head>
<body>
<header>
  <h1>{titulo}</h1>
    <div class="meta">Generado el {fecha} · Auditor de Contratos Públicos</div>
</header>

<h2>Resumen</h2>
{resumen}

<h2>Lectura para redacción</h2>
{lectura}

<h2>Casos con alerta</h2>
{tabla_alertas}

<h2>Tablas de contexto</h2>
<div class="grid">
    <section>{tabla_adjudicatarios}</section>
    <section>{tabla_relaciones}</section>
    <section>{tabla_contratos}</section>
</div>

<h2>Visualizaciones</h2>
{figuras_html}

<footer>
Datos procesados localmente. Límites legales: Ley 9/2017, art. 118.
Las alertas son indicios estadísticos, no acusación: requieren contraste documental.
</footer>
</body>
</html>
"""

_PLOTLY_HTML_CONFIG = {
    "displaylogo": False,
    "responsive": True,
    "toImageButtonOptions": {
        "format": "png",
        "filename": "grafico_auditoria",
        "height": 900,
        "width": 1600,
        "scale": 2,
    },
}


def _df_a_html(df: pd.DataFrame, *, marcar_alertas: bool = False) -> str:
    if df is None or df.empty:
        return "<p><em>Sin datos.</em></p>"
    df = df.copy()
    cols_visibles = [c for c in df.columns if not c.startswith("_")]
    df = df[cols_visibles]
    classes = "alertas" if marcar_alertas else None
    return '<div class="table-wrap">' + df.to_html(
        index=False, escape=True, classes=classes, border=0, na_rep="—"
    ) + "</div>"


def export_estatico_disponible() -> bool:
    """Indica si está disponible la exportación PNG mediante Kaleido."""
    return _KALEIDO_OK


def _figuras_a_html(figuras: list | None) -> str:
    """Convierte figuras Plotly en bloques HTML interactivos."""
    if not figuras:
        return "<p><em>Sin visualizaciones para la selección actual.</em></p>"

    bloques: list[str] = ['<div class="figures">']
    incluidas = 0
    for indice, fig in enumerate(figuras, start=1):
        if fig is None or es_figura_vacia(fig):
            continue
        incluidas += 1
        titulo = escape(_titulo_figura(fig, f"Gráfico {incluidas}"))
        include_js = True if incluidas == 1 else False
        alto_layout = getattr(getattr(fig, "layout", None), "height", None)
        alto_px = int(alto_layout) if alto_layout else 620
        alto_px = max(420, min(alto_px, 1400))
        html_figura = pio.to_html(
            fig,
            include_plotlyjs=include_js,
            full_html=False,
            config=_PLOTLY_HTML_CONFIG,
            default_width="100%",
            default_height=f"{alto_px}px",
        )
        bloques.append(
            f'<section class="figure-wrap"><h3>{titulo}</h3>{html_figura}</section>'
        )
    bloques.append("</div>")
    if incluidas == 0:
        return "<p><em>Sin visualizaciones para la selección actual.</em></p>"
    return "\n".join(bloques)


def _titulo_figura(fig, fallback: str = "grafico") -> str:
    titulo = (
        getattr(getattr(fig, "layout", None), "title", None)
        and (fig.layout.title.text or "").strip()
    )
    return titulo or fallback


def _slug(texto: str, fallback: str) -> str:
    limpio = "".join(
        caracter.lower() if caracter.isalnum() else "_"
        for caracter in str(texto or "")
    )
    limpio = "_".join(fragmento for fragmento in limpio.split("_") if fragmento)
    return (limpio[:70] or fallback).strip("_")


def figura_a_png(fig, *, ancho: int = 1800, alto: int | None = None) -> bytes | None:
    """Renderiza una figura Plotly como PNG, preservando sus colores definidos."""
    if not _KALEIDO_OK or fig is None:
        return None
    try:
        fig_export = copy.deepcopy(fig)
        alto_figura = getattr(getattr(fig_export, "layout", None), "height", None)
        alto_export = int(alto or alto_figura or 900)
        alto_export = max(520, min(alto_export, 1800))
        fig_export.update_layout(
            template="plotly_white",
            paper_bgcolor="white",
            plot_bgcolor="white",
            width=ancho,
            height=alto_export,
        )
        return pio.to_image(
            fig_export,
            format="png",
            width=ancho,
            height=alto_export,
            scale=2,
        )
    except Exception:
        return None


def figuras_a_zip(figuras: list, *, prefijo: str = "grafico") -> bytes | None:
    """Empaqueta figuras Plotly en PNG estáticos dentro de un ZIP."""
    if not _KALEIDO_OK:
        return None
    buffer = BytesIO()
    incluidas = 0
    with ZipFile(buffer, "w", ZIP_DEFLATED) as zf:
        for fig in figuras or []:
            if fig is None or es_figura_vacia(fig):
                continue
            png = figura_a_png(fig)
            if png is None:
                continue
            incluidas += 1
            titulo = _titulo_figura(fig, f"{prefijo}_{incluidas:02d}")
            nombre = _slug(titulo, f"{prefijo}_{incluidas:02d}")
            zf.writestr(f"{incluidas:02d}_{nombre}.png", png)
        if incluidas:
            zf.writestr(
                "00_LEEME.txt",
                (
                    "Graficos PNG generados desde versiones estaticas adaptadas.\n"
                    "Se mantienen los colores definidos en las figuras Plotly, "
                    "pero los graficos que dependen de zoom o arrastre se sustituyen "
                    "por rankings legibles para exportacion.\n"
                ).encode("utf-8"),
            )
    if incluidas == 0:
        return None
    return buffer.getvalue()


def construir_resumen(radar: pd.DataFrame, df_input: pd.DataFrame) -> str:
    if radar is None or radar.empty:
        return "<p><em>El radar no devolvió grupos analizables.</em></p>"
    alertas = radar[radar["Es_Alerta"]] if "Es_Alerta" in radar.columns else pd.DataFrame()
    total_contratos = int(df_input.shape[0]) if df_input is not None else 0
    importe_total = (
        float(df_input["Importe_euros"].sum())
        if df_input is not None and "Importe_euros" in df_input.columns
        else 0.0
    )
    salida = StringIO()
    salida.write("<ul>")
    salida.write(f"<li>Contratos analizados: <strong>{total_contratos:,}</strong></li>")
    salida.write(f"<li>Importe total adjudicado: <strong>{importe_total:,.2f} €</strong></li>")
    salida.write(
        f"<li>Grupos potenciales de fraccionamiento: <strong>{len(radar):,}</strong></li>"
    )
    salida.write(
        f"<li>Casos con <strong>alerta</strong>: <strong>{len(alertas):,}</strong></li>"
    )
    salida.write("</ul>")
    return salida.getvalue().replace(",", ".")


def construir_lectura(radar: pd.DataFrame, df_input: pd.DataFrame) -> str:
    if radar is None or radar.empty:
        return "<p>No hay grupos analizables con los filtros actuales.</p>"
    alertas = radar[radar["Es_Alerta"]] if "Es_Alerta" in radar.columns else pd.DataFrame()
    total_alertas = len(alertas)
    if total_alertas:
        top = alertas.sort_values(["Indice_Riesgo", "Total_euros"], ascending=False).iloc[0]
        return (
            "<p>El caso prioritario combina a <strong>"
            f"{escape(str(top.get('Adjudicatario', '—')))}</strong> con el órgano "
            f"<strong>{escape(str(top.get('Organo', '—')))}</strong>. "
            f"Acumula {escape(str(top.get('Total_Formateado', '—')))} en "
            f"{int(top.get('Num_Contratos', 0) or 0)} contratos y alcanza un índice "
            f"de riesgo de {int(top.get('Indice_Riesgo', 0) or 0)}/100. "
            "La lectura recomendada para redacción es contrastar expediente, objeto, "
            "fechas, adjudicatario y posible unidad funcional de los contratos.</p>"
        )
    return (
        "<p>No aparecen alertas con los umbrales actuales. Conviene revisar si la "
        "selección de organismos, años o tipo de contrato ha sido demasiado restrictiva "
        "antes de descartar una línea de investigación.</p>"
    )


def _tabla_top_adjudicatarios(df_input: pd.DataFrame, top: int = 20) -> str:
    if df_input is None or df_input.empty or not {"Adjudicatario", "Importe_euros"}.issubset(df_input.columns):
        return "<h3>Top adjudicatarios</h3><p><em>Sin datos.</em></p>"
    tabla = (
        df_input.dropna(subset=["Adjudicatario", "Importe_euros"])
        .groupby("Adjudicatario", dropna=False)
        .agg(Importe_total=("Importe_euros", "sum"), Contratos=("Importe_euros", "count"))
        .sort_values("Importe_total", ascending=False)
        .head(top)
        .reset_index()
    )
    if tabla.empty:
        return "<h3>Top adjudicatarios</h3><p><em>Sin datos.</em></p>"
    tabla["Importe_total"] = tabla["Importe_total"].map(lambda v: f"{v:,.2f} €".replace(",", "X").replace(".", ",").replace("X", "."))
    return "<h3>Top adjudicatarios</h3>" + _df_a_html(tabla)


def _tabla_relaciones(df_input: pd.DataFrame, top: int = 20) -> str:
    columnas = {"Organo", "Adjudicatario", "Importe_euros"}
    if df_input is None or df_input.empty or not columnas.issubset(df_input.columns):
        return "<h3>Relaciones órgano-adjudicatario</h3><p><em>Sin datos.</em></p>"
    tabla = (
        df_input.dropna(subset=["Organo", "Adjudicatario", "Importe_euros"])
        .groupby(["Organo", "Adjudicatario"], dropna=False)
        .agg(Importe_total=("Importe_euros", "sum"), Contratos=("Importe_euros", "count"))
        .sort_values("Importe_total", ascending=False)
        .head(top)
        .reset_index()
    )
    if tabla.empty:
        return "<h3>Relaciones órgano-adjudicatario</h3><p><em>Sin datos.</em></p>"
    tabla["Importe_total"] = tabla["Importe_total"].map(lambda v: f"{v:,.2f} €".replace(",", "X").replace(".", ",").replace("X", "."))
    return "<h3>Relaciones órgano-adjudicatario</h3>" + _df_a_html(tabla)


def _tabla_contratos(df_input: pd.DataFrame, top: int = 40) -> str:
    if df_input is None or df_input.empty:
        return "<h3>Contratos revisables</h3><p><em>Sin datos.</em></p>"
    columnas = [
        c for c in ["Fecha", "Adjudicatario", "Organo", "Tipo_Contrato", "Importe_euros", "Concepto"]
        if c in df_input.columns
    ]
    if not columnas:
        return "<h3>Contratos revisables</h3><p><em>Sin datos.</em></p>"
    tabla = df_input.sort_values("Importe_euros", ascending=False).head(top)[columnas].copy()
    if "Importe_euros" in tabla.columns:
        tabla["Importe_euros"] = tabla["Importe_euros"].map(lambda v: f"{v:,.2f} €".replace(",", "X").replace(".", ",").replace("X", "."))
    return "<h3>Contratos revisables por importe</h3>" + _df_a_html(tabla)


def tablas_a_zip(radar: pd.DataFrame, df_input: pd.DataFrame) -> bytes:
    """Empaqueta las tablas auditables del informe en CSV editables."""
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as zf:
        if radar is not None and not radar.empty:
            alertas = radar[radar["Es_Alerta"]] if "Es_Alerta" in radar.columns else radar
            zf.writestr("01_alertas.csv", alertas.to_csv(index=False).encode("utf-8-sig"))
            zf.writestr("02_radar_completo.csv", radar.to_csv(index=False).encode("utf-8-sig"))
        if df_input is not None and not df_input.empty:
            if {"Adjudicatario", "Importe_euros"}.issubset(df_input.columns):
                top_adj = (
                    df_input.dropna(subset=["Adjudicatario", "Importe_euros"])
                    .groupby("Adjudicatario", dropna=False)
                    .agg(Importe_total=("Importe_euros", "sum"), Contratos=("Importe_euros", "count"))
                    .sort_values("Importe_total", ascending=False)
                    .reset_index()
                )
                zf.writestr("03_top_adjudicatarios.csv", top_adj.to_csv(index=False).encode("utf-8-sig"))
            if {"Organo", "Adjudicatario", "Importe_euros"}.issubset(df_input.columns):
                relaciones = (
                    df_input.dropna(subset=["Organo", "Adjudicatario", "Importe_euros"])
                    .groupby(["Organo", "Adjudicatario"], dropna=False)
                    .agg(Importe_total=("Importe_euros", "sum"), Contratos=("Importe_euros", "count"))
                    .sort_values("Importe_total", ascending=False)
                    .reset_index()
                )
                zf.writestr("04_relaciones_organo_adjudicatario.csv", relaciones.to_csv(index=False).encode("utf-8-sig"))
            zf.writestr("05_contratos_filtrados.csv", df_input.to_csv(index=False).encode("utf-8-sig"))
    return buffer.getvalue()


def render_informe_entidad(
    *,
    titulo: str,
    radar: pd.DataFrame,
    df_input: pd.DataFrame,
    figuras: list,
) -> str:
    """Devuelve un HTML autocontenido con resumen, tablas y gráficos."""
    alertas = (
        radar[radar["Es_Alerta"]] if radar is not None and "Es_Alerta" in radar.columns
        else pd.DataFrame()
    )
    columnas = [
        "Adjudicatario", "Organo", "Tipo_Contrato", "Año_Fiscal",
        "Num_Contratos", "Total_Formateado", "Limite_Legal",
        "Porcentaje_Limite_Formateado", "Indice_Riesgo", "Prioridad",
        "Nivel_Riesgo", "Señales_Riesgo", "Dias_Entre_Contratos",
        "Importes_Individuales",
    ]
    cols_existentes = [c for c in columnas if c in alertas.columns]
    tabla_alertas = _df_a_html(alertas[cols_existentes], marcar_alertas=True)
    return _PLANTILLA.format(
        titulo=escape(titulo),
        fecha=datetime.now().strftime("%d/%m/%Y %H:%M"),
        resumen=construir_resumen(radar, df_input),
        lectura=construir_lectura(radar, df_input),
        tabla_alertas=tabla_alertas,
        tabla_adjudicatarios=_tabla_top_adjudicatarios(df_input),
        tabla_relaciones=_tabla_relaciones(df_input),
        tabla_contratos=_tabla_contratos(df_input),
        figuras_html=_figuras_a_html(figuras),
    )
