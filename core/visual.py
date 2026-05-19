# =============================================================================
# Auditor de Contratos Públicos · Universidade de Santiago de Compostela
# Módulo: visualizaciones Plotly para radar, rankings y análisis temporal.
# Autores: Xoán Xosé Pardal Pérez; Alberto Quian (apoyo metodológico y técnico).
# Esta aplicación es parte de los proyectos de I+D+i:
# - Inteligencia artificial en medios digitales en España: efectos y roles (PID2024-156034OB-C22).
# - XornalIA: Desarrollo, validación y transferencia de una plataforma integradora de soluciones de inteligencia artificial generativa para medios de comunicación (PDC2025-166024-I00).
# Licencia: MIT (https://opensource.org/license/mit).
# SPDX-License-Identifier: MIT
# =============================================================================

"""Visualizaciones interactivas (Plotly) para el radar y los rankings.

Todas las funciones devuelven un `plotly.graph_objects.Figure` ya estilizado;
la app simplemente las pinta con `st.plotly_chart(fig, width="stretch")`.
Mantener Plotly aislado en este módulo evita que el resto del código dependa
de un backend gráfico concreto.
"""
from __future__ import annotations

import html
import json
import textwrap

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from .analysis import parsear_fechas_mixtas
from .constants import CCAA_CENTROIDES, PROVINCIA_CENTROIDES


_COLORES_RIESGO = {
    "🚨 Acumulado > límite legal": "#c0392b",
    "🔴 Roza el límite (>95%)": "#e74c3c",
    "🟠 Cerca del límite (>90%)": "#e67e22",
    "✅ Sin alerta": "#7f8c8d",
}

_COLORWAY_CATEGORIAS = [
    "#2563eb",
    "#dc2626",
    "#16a34a",
    "#f59e0b",
    "#7c3aed",
    "#0891b2",
    "#db2777",
    "#64748b",
]


def _figura_vacia(mensaje: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=mensaje, xref="paper", yref="paper", x=0.5, y=0.5,
        showarrow=False, font=dict(size=14, color="#666"),
    )
    fig.update_layout(
        height=300, xaxis=dict(visible=False), yaxis=dict(visible=False),
        margin=dict(l=20, r=20, t=20, b=20),
        meta={"figura_vacia": True, "mensaje_vacio": mensaje},
    )
    return fig


def es_figura_vacia(fig) -> bool:
    """Devuelve True si la figura fue generada por `_figura_vacia`."""
    try:
        meta = getattr(getattr(fig, "layout", None), "meta", None)
        if isinstance(meta, dict):
            return bool(meta.get("figura_vacia"))
        # Plotly puede envolverlo en un objeto tipo Mapping
        if meta is not None and hasattr(meta, "get"):
            return bool(meta.get("figura_vacia"))
    except Exception:
        return False
    return False


def _recortar(texto: object, max_chars: int = 42) -> str:
    limpio = " ".join(str(texto or "").split())
    return limpio if len(limpio) <= max_chars else limpio[: max_chars - 1].rstrip() + "…"


def _envolver(texto: object, ancho: int = 28, max_lineas: int = 3) -> str:
    limpio = " ".join(str(texto or "").split())
    if not limpio:
        return "—"
    lineas = textwrap.wrap(limpio, width=ancho, break_long_words=False, replace_whitespace=False)
    if not lineas:
        return limpio
    if len(lineas) > max_lineas:
        lineas = lineas[:max_lineas]
        lineas[-1] = _recortar(lineas[-1], max(8, ancho - 1))
    return "<br>".join(lineas)


def _formato_euros(valor: float) -> str:
    return f"{float(valor or 0):,.0f} €".replace(",", ".")


def _estilo_editorial(fig: go.Figure, *, titulo: str, alto: int = 520) -> go.Figure:
    fig.update_layout(
        title=dict(text=titulo, x=0.01, xanchor="left", font=dict(size=18, color="#111827")),
        height=alto,
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(family="Inter, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif", size=13, color="#111827"),
        margin=dict(l=76, r=42, t=86, b=48),
        legend=dict(orientation="h", yanchor="bottom", y=1.12, xanchor="right", x=1),
    )
    return fig


def grafico_treemap_adjudicatarios(radar: pd.DataFrame, top: int = 30) -> go.Figure:
    """Treemap del radar: tamaño = total acumulado, color = % del límite legal."""
    if radar is None or radar.empty:
        return _figura_vacia("Sin datos para el treemap.")

    df = radar.copy()
    df = df.nlargest(top, "Total_euros")
    df["Pct"] = (
        pd.to_numeric(df.get("Porcentaje_Limite", pd.Series([0] * len(df))), errors="coerce")
        .replace([np.inf, -np.inf], np.nan)
        .fillna(0)
    )
    df["Pct_Color"] = df["Pct"].clip(lower=0, upper=120)
    total_visible = float(df["Total_euros"].sum() or 1)
    df["Peso_Relativo"] = df["Total_euros"].fillna(0).astype(float) / total_visible

    def _texto_treemap(fila: pd.Series) -> str:
        peso = float(fila.get("Peso_Relativo", 0) or 0)
        nombre = fila.get("Adjudicatario", "")
        if peso >= 0.16:
            etiqueta = _envolver(nombre, 18, 3)
            return (
                f"<b>{etiqueta}</b><br>"
                f"{fila.get('Total_Formateado', '—')}<br>"
                f"{int(fila.get('Num_Contratos', 0) or 0)} contratos"
            )
        if peso >= 0.07:
            etiqueta = _envolver(nombre, 16, 2)
            return f"<b>{etiqueta}</b><br>{fila.get('Total_Formateado', '—')}"
        if peso >= 0.025:
            return f"<b>{_envolver(nombre, 12, 2)}</b>"
        return f"<b>{_recortar(nombre, 16)}</b>"

    df["Etiqueta_Corta"] = df["Adjudicatario"].apply(lambda texto: _envolver(texto, 18, 2))
    df["Texto_Celda"] = df.apply(_texto_treemap, axis=1)
    customdata = np.vstack([
        np.array([["Total", "", "", 0]], dtype=object),
        df[["Adjudicatario", "Tipo_Contrato", "Num_Contratos", "Pct"]].to_numpy(),
    ])
    ids = ["__root__"] + [f"adj_{indice}" for indice in range(len(df))]
    labels = [""] + df["Etiqueta_Corta"].tolist()
    parents = [""] + ["__root__"] * len(df)
    values = [total_visible] + df["Total_euros"].tolist()
    colors = ["#ffffff"] + df["Pct_Color"].tolist()
    textos = [""] + df["Texto_Celda"].tolist()

    fig = go.Figure(
        go.Treemap(
            ids=ids,
            labels=labels,
            parents=parents,
            values=values,
            branchvalues="total",
            marker=dict(
                colors=colors,
                colorscale=[
                    (0.00, "#d8f3dc"),
                    (0.50, "#fff3b0"),
                    (0.85, "#ffd6a5"),
                    (1.00, "#ffadad"),
                ],
                cmin=0,
                cmax=120,
                colorbar=dict(title="% del límite legal", thickness=14, len=0.6),
                line=dict(width=1, color="#ffffff"),
            ),
            text=textos,
            texttemplate="%{text}",
            textposition="middle center",
            textfont=dict(size=13, color="#111827", family="Inter, system-ui, sans-serif"),
            customdata=customdata,
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Total: %{value:,.0f} €<br>"
                "Tipo: %{customdata[1]}<br>"
                "Contratos: %{customdata[2]}<br>"
                "% del límite: %{customdata[3]:.1f} %<extra></extra>"
            ),
            tiling=dict(packing="squarify", squarifyratio=1.7, pad=1),
            pathbar=dict(visible=False),
            root=dict(color="#ffffff"),
            maxdepth=2,
        )
    )
    fig.update_layout(
        title=dict(text="Treemap de adjudicatarios por gasto acumulado", x=0.01, xanchor="left"),
        margin=dict(l=8, r=8, t=46, b=10),
        height=640,
        paper_bgcolor="white",
        plot_bgcolor="white",
        uniformtext=dict(minsize=7, mode="show"),
    )
    return fig


def _agregar_territorio(df_input: pd.DataFrame, nivel: str, metrica: str) -> tuple[pd.DataFrame, str, str]:
    if metrica == "importe":
        agreg = (
            df_input.groupby(nivel, dropna=False)["Importe_euros"]
            .sum().sort_values(ascending=True).reset_index()
        )
        return agreg, "Importe_euros", "Total adjudicado (€)"
    agreg = (
        df_input.groupby(nivel, dropna=False)["Importe_euros"]
        .count().sort_values(ascending=True).reset_index()
        .rename(columns={"Importe_euros": "Num_Contratos"})
    )
    return agreg, "Num_Contratos", "Nº de contratos"


def grafico_mapa_burbujas_territorial(
    df_input: pd.DataFrame,
    *,
    nivel: str = "Provincia",
    metrica: str = "importe",
) -> go.Figure:
    """Mapa interactivo de burbujas para CCAA o provincia con centroides aproximados."""
    if df_input is None or df_input.empty or nivel not in df_input.columns:
        return _figura_vacia(f"Sin información de {nivel.lower()} para representar en mapa.")

    centroides = CCAA_CENTROIDES if nivel == "CCAA" else PROVINCIA_CENTROIDES if nivel == "Provincia" else {}
    if not centroides:
        return _figura_vacia("El mapa geográfico está disponible para CCAA y provincia; usa el ranking para municipios.")

    df = df_input.dropna(subset=[nivel, "Importe_euros"]).copy()
    if df.empty:
        return _figura_vacia(f"No se pudo deducir {nivel.lower()} para los contratos cargados.")

    agreg, eje_valor, titulo_valor = _agregar_territorio(df, nivel, metrica)
    agreg["Lat"] = agreg[nivel].map(lambda nombre: centroides.get(str(nombre), (None, None))[0])
    agreg["Lon"] = agreg[nivel].map(lambda nombre: centroides.get(str(nombre), (None, None))[1])
    agreg = agreg.dropna(subset=["Lat", "Lon"])
    if agreg.empty:
        return _figura_vacia(f"No hay coordenadas para el nivel {nivel.lower()} en los datos filtrados.")

    max_valor = float(agreg[eje_valor].max() or 1)
    fig = go.Figure(go.Scattergeo(
        lat=agreg["Lat"],
        lon=agreg["Lon"],
        text=agreg[nivel] if len(agreg) <= 20 else None,
        mode="markers+text" if len(agreg) <= 20 else "markers",
        textposition="top center",
        marker=dict(
            size=agreg[eje_valor],
            sizemode="area",
            sizeref=2.0 * max_valor / (52 ** 2),
            sizemin=7,
            color=agreg[eje_valor],
            colorscale="YlOrRd",
            colorbar=dict(title=titulo_valor, thickness=14, len=0.62),
            line=dict(width=1, color="#ffffff"),
            opacity=0.82,
        ),
        customdata=agreg[[nivel, eje_valor]].to_numpy(),
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            + titulo_valor + ": %{customdata[1]:,.0f}<extra></extra>"
        ),
    ))
    fig.update_layout(
        title=dict(text=f"Mapa territorial por {titulo_valor.lower()} · {nivel}", x=0.01, xanchor="left"),
        height=520,
        margin=dict(l=8, r=8, t=56, b=8),
        geo=dict(
            scope="europe",
            projection_type="natural earth",
            lataxis_range=[27, 44.5],
            lonaxis_range=[-18.5, 5.0],
            showland=True,
            landcolor="#f8fafc",
            showcountries=True,
            countrycolor="#cbd5e1",
            showcoastlines=True,
            coastlinecolor="#cbd5e1",
            bgcolor="rgba(0,0,0,0)",
        ),
    )
    return fig


def grafico_dispersion_riesgo(radar: pd.DataFrame) -> go.Figure:
    """Dispersión nº contratos vs total acumulado coloreada por riesgo."""
    if radar is None or radar.empty:
        return _figura_vacia("Sin datos para el gráfico de dispersión.")

    fig = px.scatter(
        radar,
        x="Num_Contratos",
        y="Total_euros",
        color="Nivel_Riesgo",
        color_discrete_map=_COLORES_RIESGO,
        size="Total_euros",
        size_max=42,
        hover_name="Adjudicatario",
        hover_data={
            "Organo": True,
            "Tipo_Contrato": True,
            "Año_Fiscal": True,
            "Total_Formateado": True,
            "Total_euros": False,
            "Num_Contratos": True,
        },
        labels={
            "Num_Contratos": "Nº de contratos en el grupo",
            "Total_euros": "Total acumulado (€)",
            "Nivel_Riesgo": "Riesgo",
        },
    )
    fig.update_layout(legend_title_text="")
    _estilo_editorial(fig, titulo="Dispersión de riesgo por adjudicatario", alto=500)
    return fig


def grafico_serie_temporal(df_input: pd.DataFrame) -> go.Figure:
    """Importe agregado por año fiscal y tipo de contrato (barras apiladas)."""
    if df_input is None or df_input.empty or "Año_Fiscal" not in df_input.columns:
        return _figura_vacia("Sin datos temporales disponibles.")

    df = df_input.dropna(subset=["Año_Fiscal", "Importe_euros"]).copy()
    if df.empty:
        return _figura_vacia("Sin importes con año fiscal asociado.")

    agreg = (
        df.groupby(["Año_Fiscal", "Tipo_Contrato"], dropna=False)["Importe_euros"]
        .sum()
        .reset_index()
        .sort_values("Año_Fiscal")
    )
    fig = px.bar(
        agreg,
        x="Año_Fiscal",
        y="Importe_euros",
        color="Tipo_Contrato",
        color_discrete_sequence=_COLORWAY_CATEGORIAS,
        labels={"Importe_euros": "Total adjudicado (€)", "Año_Fiscal": "Año fiscal"},
        text_auto=".2s",
    )
    fig.update_layout(barmode="stack")
    _estilo_editorial(fig, titulo="Importe adjudicado por año fiscal y tipo", alto=460)
    fig.update_layout(
        margin=dict(l=92, r=42, t=118, b=96),
        yaxis=dict(title="Total adjudicado (€)", title_standoff=16, automargin=True),
        xaxis=dict(title="Año fiscal", automargin=True),
        legend=dict(orientation="h", yanchor="top", y=-0.20, xanchor="left", x=0),
        uniformtext=dict(minsize=10, mode="hide"),
    )
    fig.update_traces(textposition="inside", marker_line=dict(color="#ffffff", width=0.7))
    return fig


def grafico_ranking_entidades(df_ranking: pd.DataFrame, top: int = 20) -> go.Figure:
    """Barras horizontales del ranking de gasto por entidad."""
    if df_ranking is None or df_ranking.empty:
        return _figura_vacia("Sin datos en el ranking.")

    df = df_ranking.head(top).iloc[::-1]
    fig = px.bar(
        df,
        x="total_gastado",
        y="entidad",
        orientation="h",
        text="total_gastado",
        labels={"total_gastado": "Total gastado (€)", "entidad": ""},
    )
    fig.update_traces(texttemplate="%{x:,.0f} €")
    _estilo_editorial(fig, titulo="Ranking de entidades por gasto", alto=max(360, 28 * len(df) + 120))
    return fig


def grafico_histograma_importes(df_input: pd.DataFrame) -> go.Figure:
    """Distribución de importes con líneas en los límites legales principales."""
    if df_input is None or df_input.empty or "Importe_euros" not in df_input.columns:
        return _figura_vacia("Sin importes para representar.")

    df = df_input.dropna(subset=["Importe_euros"]).copy()
    df = df[df["Importe_euros"] > 0]
    if df.empty:
        return _figura_vacia("Sin importes positivos para representar.")

    color = "Tipo_Contrato" if "Tipo_Contrato" in df.columns else None
    fig = px.histogram(
        df,
        x="Importe_euros",
        color=color,
        color_discrete_sequence=_COLORWAY_CATEGORIAS,
        nbins=min(60, max(10, int(len(df) ** 0.5))),
        labels={"Importe_euros": "Importe adjudicado (€)", "count": "Contratos"},
    )
    fig.add_vline(x=15_000, line_width=2, line_dash="dash", line_color="#c0392b")
    fig.add_vline(x=40_000, line_width=2, line_dash="dash", line_color="#8e44ad")
    fig.add_annotation(x=15_000, y=1, yref="paper", text="15.000 €", showarrow=False, yshift=12)
    fig.add_annotation(x=40_000, y=1, yref="paper", text="40.000 €", showarrow=False, yshift=12)
    fig.update_layout(bargap=0.08, legend_title_text="")
    _estilo_editorial(fig, titulo="Distribución de importes adjudicados", alto=430)
    fig.update_layout(
        margin=dict(l=92, r=42, t=110, b=96),
        legend=dict(orientation="h", yanchor="top", y=-0.20, xanchor="left", x=0),
    )
    fig.update_traces(marker_line=dict(color="#ffffff", width=0.7), opacity=0.78)
    return fig


def grafico_timeline_contratos(df_input: pd.DataFrame, top: int = 18) -> go.Figure:
    """Calendario legible de contratos por adjudicatario e importe."""
    columnas_necesarias = {"Fecha", "Importe_euros", "Adjudicatario"}
    if df_input is None or df_input.empty or not columnas_necesarias.issubset(df_input.columns):
        return _figura_vacia("Sin fechas, importes o adjudicatarios para la línea temporal.")

    df = df_input.copy()
    df["_Fecha"] = parsear_fechas_mixtas(df["Fecha"]).values
    df = df.dropna(subset=["_Fecha", "Importe_euros", "Adjudicatario"])
    if df.empty:
        return _figura_vacia("Sin fechas válidas para la línea temporal.")

    totales = df.groupby("Adjudicatario")["Importe_euros"].sum().nlargest(top)
    principales = totales.index.tolist()
    df = df[df["Adjudicatario"].isin(principales)].copy()
    if df.empty:
        return _figura_vacia("Sin contratos para los adjudicatarios principales.")

    etiquetas = {nombre: _envolver(nombre, 24, 2) for nombre in principales}
    df["Adjudicatario_Label"] = df["Adjudicatario"].map(etiquetas)
    max_importe = float(df["Importe_euros"].max() or 1)
    df["Tamano"] = 8 + 20 * np.sqrt(df["Importe_euros"].clip(lower=0) / max_importe)
    for columna in ["Organo", "Tipo_Contrato", "Concepto", "Año_Fiscal"]:
        if columna not in df.columns:
            df[columna] = "—"
    customdata = df[["Adjudicatario", "Organo", "Tipo_Contrato", "Concepto", "Año_Fiscal", "Importe_euros"]].to_numpy()

    fig = go.Figure(go.Scatter(
        x=df["_Fecha"],
        y=df["Adjudicatario_Label"],
        mode="markers",
        marker=dict(
            size=df["Tamano"],
            color=df["Importe_euros"],
            colorscale="YlOrRd",
            cmin=0,
            cmax=max_importe,
            showscale=True,
            colorbar=dict(title="Importe (€)", thickness=14, len=0.7),
            line=dict(color="#ffffff", width=0.8),
            opacity=0.88,
        ),
        customdata=customdata,
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "Fecha: %{x|%d/%m/%Y}<br>"
            "Importe: %{customdata[5]:,.0f} €<br>"
            "Órgano: %{customdata[1]}<br>"
            "Tipo: %{customdata[2]}<br>"
            "Año fiscal: %{customdata[4]}<br>"
            "%{customdata[3]}<extra></extra>"
        ),
        showlegend=False,
    ))
    _estilo_editorial(fig, titulo="Calendario de contratos por adjudicatario", alto=max(540, 34 * len(principales) + 150))
    fig.update_layout(
        margin=dict(l=210, r=72, t=82, b=58),
        xaxis=dict(title="Fecha", automargin=True, showgrid=True),
        yaxis=dict(
            title="",
            categoryorder="array",
            categoryarray=[etiquetas[nombre] for nombre in principales[::-1]],
            automargin=True,
        ),
    )
    return fig


def grafico_pareto_adjudicatarios(df_input: pd.DataFrame, top: int = 25) -> go.Figure:
    """Concentración del gasto: barras por adjudicatario y curva acumulada."""
    if df_input is None or df_input.empty or "Importe_euros" not in df_input.columns:
        return _figura_vacia("Sin importes para calcular concentración.")

    columna_adj = "Adjudicatario" if "Adjudicatario" in df_input.columns else "_Adjudicatario_Radar"
    if columna_adj not in df_input.columns:
        return _figura_vacia("Sin adjudicatarios para calcular concentración.")

    df = df_input.dropna(subset=[columna_adj, "Importe_euros"]).copy()
    if df.empty:
        return _figura_vacia("Sin adjudicatarios con importe para calcular concentración.")

    agreg = (
        df.groupby(columna_adj, dropna=False)["Importe_euros"]
        .sum()
        .sort_values(ascending=False)
        .head(top)
        .reset_index()
        .rename(columns={columna_adj: "Adjudicatario"})
    )
    total = float(df["Importe_euros"].sum())
    agreg["Acumulado_pct"] = agreg["Importe_euros"].cumsum() / total * 100 if total else 0
    agreg = agreg.iloc[::-1].copy()
    agreg["Etiqueta"] = agreg["Adjudicatario"].apply(lambda texto: _envolver(texto, ancho=30, max_lineas=3))
    agreg["Texto"] = agreg["Importe_euros"].apply(_formato_euros)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=agreg["Importe_euros"],
        y=agreg["Etiqueta"],
        name="Importe acumulado",
        marker_color="#2c7fb8",
        orientation="h",
        text=agreg["Texto"],
        textposition="outside",
        customdata=agreg[["Adjudicatario", "Acumulado_pct"]].to_numpy(),
        hovertemplate="<b>%{customdata[0]}</b><br>Total: %{x:,.0f} €<br>Acumulado: %{customdata[1]:.1f} %<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=agreg["Acumulado_pct"],
        y=agreg["Etiqueta"],
        name="% acumulado",
        mode="lines+markers",
        marker_color="#c0392b",
        xaxis="x2",
        hovertemplate="% acumulado: %{x:.1f} %<extra></extra>",
    ))
    fig.update_layout(
        legend_title_text="",
        xaxis=dict(title="Importe (€)", rangemode="tozero", automargin=True),
        xaxis2=dict(title="% acumulado", overlaying="x", side="top", range=[0, 105], showgrid=False),
        yaxis=dict(title="", automargin=True),
    )
    _estilo_editorial(fig, titulo="Concentración del gasto por adjudicatario", alto=max(460, 34 * len(agreg) + 120))
    return fig


def grafico_red_organo_adjudicatario(df_input: pd.DataFrame, top_relaciones: int = 35) -> go.Figure:
    """Red bipartita órgano-adjudicatario: enlaces por importe agregado."""
    columnas = {"Organo", "Adjudicatario", "Importe_euros"}
    if df_input is None or df_input.empty or not columnas.issubset(df_input.columns):
        return _figura_vacia("Sin órganos, adjudicatarios e importes para construir la red.")

    df = df_input.dropna(subset=["Organo", "Adjudicatario", "Importe_euros"]).copy()
    df = df[df["Adjudicatario"].astype(str).str.lower().ne("no consta")]
    if df.empty:
        return _figura_vacia("Sin adjudicatarios identificados para construir la red.")

    enlaces = (
        df.groupby(["Organo", "Adjudicatario"], dropna=False)
        .agg(Total_euros=("Importe_euros", "sum"), Num_Contratos=("Importe_euros", "count"))
        .sort_values("Total_euros", ascending=False)
        .head(top_relaciones)
        .reset_index()
    )
    if enlaces.empty:
        return _figura_vacia("Sin relaciones órgano-adjudicatario que representar.")

    def _posiciones(nombres: list[str]) -> dict[str, float]:
        if len(nombres) == 1:
            return {nombres[0]: 0.5}
        return {nombre: 1 - (i / (len(nombres) - 1)) for i, nombre in enumerate(nombres)}

    organos = enlaces.groupby("Organo")["Total_euros"].sum().sort_values(ascending=False).index.tolist()
    adjudicatarios = enlaces.groupby("Adjudicatario")["Total_euros"].sum().sort_values(ascending=False).index.tolist()
    pos_org = _posiciones(organos)
    pos_adj = _posiciones(adjudicatarios)
    max_total = float(enlaces["Total_euros"].max() or 1)

    fig = go.Figure()
    for fila in enlaces.itertuples(index=False):
        ancho = 0.8 + 5.2 * (float(fila.Total_euros) / max_total)
        fig.add_trace(go.Scatter(
            x=[0.08, 0.92],
            y=[pos_org[fila.Organo], pos_adj[fila.Adjudicatario]],
            mode="lines",
            line=dict(width=ancho, color="rgba(71, 85, 105, 0.28)"),
            hoverinfo="text",
            text=(
                f"{fila.Organo}<br>{fila.Adjudicatario}<br>"
                f"{fila.Total_euros:,.0f} € · {fila.Num_Contratos} contratos"
            ),
            showlegend=False,
        ))

    total_org = enlaces.groupby("Organo")["Total_euros"].sum()
    total_adj = enlaces.groupby("Adjudicatario")["Total_euros"].sum()
    fig.add_trace(go.Scatter(
        x=[0.04] * len(organos),
        y=[pos_org[nombre] for nombre in organos],
        mode="markers+text",
        marker=dict(size=14 + 28 * (total_org.loc[organos] / total_org.max()), color="#2563eb"),
        text=[_recortar(nombre, 34) for nombre in organos],
        textposition="middle right",
        hovertext=[f"{nombre}<br>{total_org.loc[nombre]:,.0f} €" for nombre in organos],
        hoverinfo="text",
        showlegend=False,
    ))
    fig.add_trace(go.Scatter(
        x=[0.96] * len(adjudicatarios),
        y=[pos_adj[nombre] for nombre in adjudicatarios],
        mode="markers+text",
        marker=dict(size=14 + 28 * (total_adj.loc[adjudicatarios] / total_adj.max()), color="#dc2626"),
        text=[_recortar(nombre, 34) for nombre in adjudicatarios],
        textposition="middle left",
        hovertext=[f"{nombre}<br>{total_adj.loc[nombre]:,.0f} €" for nombre in adjudicatarios],
        hoverinfo="text",
        showlegend=False,
    ))
    fig.update_layout(
        height=max(520, 24 * max(len(organos), len(adjudicatarios))),
        margin=dict(l=10, r=10, t=45, b=10),
        xaxis=dict(visible=False, range=[0, 1]),
        yaxis=dict(visible=False, range=[-0.05, 1.05]),
        annotations=[
            dict(text="Órganos contratantes", x=0.04, y=1.06, xref="x", yref="y", showarrow=False, font=dict(size=13)),
            dict(text="Adjudicatarios", x=0.96, y=1.06, xref="x", yref="y", showarrow=False, font=dict(size=13)),
        ],
        paper_bgcolor="white",
        plot_bgcolor="white",
    )
    return fig


def grafico_relaciones_principales(df_input: pd.DataFrame, top: int = 18) -> go.Figure:
    """Barras exportables de relaciones órgano-adjudicatario.

    Sustituye al grafo en salidas estáticas: conserva la información clave
    (quién contrata a quién y cuánto suma) sin depender de zoom o arrastre.
    """
    columnas = {"Organo", "Adjudicatario", "Importe_euros"}
    if df_input is None or df_input.empty or not columnas.issubset(df_input.columns):
        return _figura_vacia("Sin relaciones órgano-adjudicatario para resumir.")

    df = df_input.dropna(subset=["Organo", "Adjudicatario", "Importe_euros"]).copy()
    df = df[df["Adjudicatario"].astype(str).str.strip().str.lower().ne("no consta")]
    if df.empty:
        return _figura_vacia("Sin adjudicatarios identificados para resumir relaciones.")

    enlaces = (
        df.groupby(["Organo", "Adjudicatario"], dropna=False)
        .agg(Total_euros=("Importe_euros", "sum"), Num_Contratos=("Importe_euros", "count"))
        .sort_values("Total_euros", ascending=False)
        .head(top)
        .reset_index()
        .iloc[::-1]
    )
    if enlaces.empty:
        return _figura_vacia("Sin relaciones órgano-adjudicatario para resumir.")

    enlaces["Relacion"] = enlaces["Adjudicatario"].apply(lambda texto: _envolver(texto, 34, 2))
    enlaces["Texto"] = enlaces.apply(
        lambda fila: f"{_formato_euros(fila['Total_euros'])} · {int(fila['Num_Contratos'])} c.",
        axis=1,
    )

    fig = go.Figure(go.Bar(
        x=enlaces["Total_euros"],
        y=enlaces["Relacion"],
        orientation="h",
        marker=dict(color=enlaces["Total_euros"], colorscale="OrRd", line=dict(color="#ffffff", width=1)),
        text=enlaces["Texto"],
        textposition="outside",
        cliponaxis=False,
        customdata=enlaces[["Organo", "Adjudicatario", "Num_Contratos"]].to_numpy(),
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "Adjudicatario: %{customdata[1]}<br>"
            "Total: %{x:,.0f} €<br>Contratos: %{customdata[2]}<extra></extra>"
        ),
    ))
    fig.update_layout(xaxis_title="Importe acumulado (€)", yaxis_title="", yaxis=dict(automargin=True))
    _estilo_editorial(fig, titulo="Relaciones principales órgano-adjudicatario", alto=max(520, 48 * len(enlaces) + 140))
    return fig


def grafico_alertas_prioritarias(radar: pd.DataFrame, top: int = 18) -> go.Figure:
    """Ranking exportable de alertas por índice de riesgo e importe."""
    if radar is None or radar.empty:
        return _figura_vacia("Sin grupos analizables para el ranking de alertas.")

    df = radar.copy()
    if "Es_Alerta" in df.columns and df["Es_Alerta"].any():
        df = df[df["Es_Alerta"]]
    df = df.sort_values(["Indice_Riesgo", "Total_euros"], ascending=False).head(top).iloc[::-1]
    if df.empty:
        return _figura_vacia("Sin alertas con los umbrales actuales.")

    df["Etiqueta"] = df["Adjudicatario"].apply(lambda texto: _envolver(texto, 34, 2))
    df["Texto"] = df.apply(
        lambda fila: f"{int(fila.get('Indice_Riesgo', 0))}/100 · {_formato_euros(fila.get('Total_euros', 0))}",
        axis=1,
    )
    fig = go.Figure(go.Bar(
        x=df["Indice_Riesgo"],
        y=df["Etiqueta"],
        orientation="h",
        marker=dict(color=df["Total_euros"], colorscale="Reds", line=dict(color="#ffffff", width=1)),
        text=df["Texto"],
        textposition="outside",
        cliponaxis=False,
        customdata=df[["Adjudicatario", "Organo", "Total_euros", "Num_Contratos"]].to_numpy(),
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>%{customdata[1]}<br>"
            "Índice: %{x}/100<br>Total: %{customdata[2]:,.0f} €<br>"
            "Contratos: %{customdata[3]}<extra></extra>"
        ),
    ))
    fig.update_layout(xaxis=dict(title="Índice de riesgo", range=[0, 108]), yaxis=dict(title="", automargin=True))
    _estilo_editorial(fig, titulo="Alertas prioritarias para revisar", alto=max(520, 48 * len(df) + 140))
    return fig


def figuras_editoriales(radar: pd.DataFrame, df_input: pd.DataFrame) -> list[go.Figure]:
    """Devuelve gráficos aptos para HTML, PDF y PNG estáticos.

    Evita exportar piezas que sólo funcionan bien con hover/zoom (treemap y
    grafo) y las sustituye por rankings y tablas visuales legibles.
    """
    figuras = [
        grafico_alertas_prioritarias(radar),
        grafico_pareto_adjudicatarios(df_input, top=18),
        grafico_relaciones_principales(df_input, top=16),
        grafico_serie_temporal(df_input),
        grafico_histograma_importes(df_input),
        grafico_heatmap_mensual(df_input),
    ]
    if df_input is None or df_input.empty:
        return figuras
    for nivel in ("CCAA", "Provincia", "Municipio"):
        if nivel in df_input.columns and df_input[nivel].notna().any():
            figuras.append(grafico_mapa_calor_territorial(df_input, nivel=nivel))
            break
    return figuras


def grafo_relaciones_interactivo_html(df_input: pd.DataFrame, top_relaciones: int = 80) -> str:
        """HTML con grafo arrastrable órgano-adjudicatario y relaciones secundarias."""
        columnas = {"Organo", "Adjudicatario", "Importe_euros"}
        if df_input is None or df_input.empty or not columnas.issubset(df_input.columns):
                return "<p>Sin órganos, adjudicatarios e importes para construir la red.</p>"

        df = df_input.dropna(subset=["Organo", "Adjudicatario", "Importe_euros"]).copy()
        df = df[df["Adjudicatario"].astype(str).str.strip().str.lower().ne("no consta")]
        if df.empty:
                return "<p>Sin adjudicatarios identificados para construir la red.</p>"

        enlaces_base = (
                df.groupby(["Organo", "Adjudicatario"], dropna=False)
                .agg(Total_euros=("Importe_euros", "sum"), Num_Contratos=("Importe_euros", "count"))
                .sort_values("Total_euros", ascending=False)
                .head(top_relaciones)
                .reset_index()
        )
        if enlaces_base.empty:
                return "<p>Sin relaciones órgano-adjudicatario que representar.</p>"

        nodos: dict[str, dict] = {}
        aristas: dict[tuple[str, str, str], dict] = {}
        totales_nodo: dict[str, float] = {}

        def _node_id(prefijo: str, valor: object) -> str:
                return f"{prefijo}::{str(valor)}"

        def _add_node(node_id: str, label: object, group: str, title: str, level: int, total: float = 0.0) -> None:
            totales_nodo[node_id] = totales_nodo.get(node_id, 0.0) + float(total or 0)
            etiqueta = str(label or "")
            nodos[node_id] = {
                "id": node_id,
                "label": _recortar(etiqueta, 30),
                "labelFull": etiqueta,
                "labelShort": _recortar(etiqueta, 24),
                "title": title,
                "group": group,
                "level": level,
            }

        def _add_edge(source: str, target: str, label: str, total: float, contratos: int, depth: int) -> None:
                key = (source, target, label)
                previo = aristas.get(key)
                if previo:
                        previo["value"] += float(total or 0)
                        previo["contratos"] += int(contratos or 0)
                        previo["title"] = f"{previo['value']:,.0f} € · {previo['contratos']} contratos"
                        return
                aristas[key] = {
                        "from": source,
                        "to": target,
                        "label": label,
                        "labelRaw": label,
                        "value": float(total or 0),
                        "contratos": int(contratos or 0),
                        "depth": depth,
                        "title": f"{float(total or 0):,.0f} € · {int(contratos or 0)} contratos",
                }

        adjudicatarios_top = set(enlaces_base["Adjudicatario"].astype(str))
        for fila in enlaces_base.itertuples(index=False):
                organo_id = _node_id("org", fila.Organo)
                adjud_id = _node_id("adj", fila.Adjudicatario)
                total = float(fila.Total_euros or 0)
                contratos = int(fila.Num_Contratos or 0)
                _add_node(organo_id, fila.Organo, "organo", f"Órgano: {html.escape(str(fila.Organo))}", 1, total)
                _add_node(adjud_id, fila.Adjudicatario, "adjudicatario", f"Adjudicatario: {html.escape(str(fila.Adjudicatario))}", 2, total)
                _add_edge(organo_id, adjud_id, f"{total:,.0f} €", total, contratos, 1)

        df_sec = df[df["Adjudicatario"].astype(str).isin(adjudicatarios_top)].copy()
        secundarios = [
                ("Tipo_Contrato", "tipo", "Tipo", 2),
                ("CPV", "cpv", "CPV", 3),
                ("Municipio", "mun", "Municipio", 2),
                ("Provincia", "prov", "Provincia", 3),
        ]
        for columna, prefijo, etiqueta, depth in secundarios:
                if columna not in df_sec.columns:
                        continue
                agreg = (
                        df_sec.dropna(subset=[columna])
                        .groupby(["Adjudicatario", columna], dropna=False)
                        .agg(Total_euros=("Importe_euros", "sum"), Num_Contratos=("Importe_euros", "count"))
                        .sort_values("Total_euros", ascending=False)
                        .head(top_relaciones * 2)
                        .reset_index()
                )
                for fila in agreg.itertuples(index=False):
                        valor = getattr(fila, columna)
                        if pd.isna(valor) or str(valor).strip() in ("", "None", "nan"):
                                continue
                        adjud_id = _node_id("adj", fila.Adjudicatario)
                        sec_id = _node_id(prefijo, valor)
                        total = float(fila.Total_euros or 0)
                        contratos = int(fila.Num_Contratos or 0)
                        _add_node(sec_id, valor, prefijo, f"{etiqueta}: {html.escape(str(valor))}", 3, total)
                        _add_edge(adjud_id, sec_id, etiqueta, total, contratos, depth)

        max_total = max(totales_nodo.values()) if totales_nodo else 1.0
        nodes_payload = []
        for node_id, nodo in nodos.items():
                total = totales_nodo.get(node_id, 0.0)
                nodo = nodo.copy()
                nodo["value"] = max(9, 9 + 34 * (total / max_total))
                nodo["title"] = f"{nodo['title']}<br>{total:,.0f} €"
                nodes_payload.append(nodo)

        max_edge = max((edge["value"] for edge in aristas.values()), default=1.0)
        edges_payload = []
        for edge in aristas.values():
                edge = edge.copy()
                edge["width"] = 0.9 + 5.5 * (edge["value"] / max_edge)
                edge["color"] = "rgba(30, 41, 59, 0.42)" if edge["depth"] == 1 else "rgba(100, 116, 139, 0.24)"
                edge["arrows"] = ""
                edges_payload.append(edge)

        payload_nodes = json.dumps(nodes_payload, ensure_ascii=False)
        payload_edges = json.dumps(edges_payload, ensure_ascii=False)

        return f"""
<!doctype html>
<html lang="es">
<head>
    <meta charset="utf-8" />
    <script src="https://unpkg.com/vis-network@9.1.9/standalone/umd/vis-network.min.js"></script>
    <style>
        body {{ margin: 0; font-family: Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; color: #111827; }}
        .toolbar {{ display: flex; flex-wrap: wrap; gap: 8px; align-items: center; padding: 10px 0; }}
        .toolbar button, .toolbar select {{ border: 1px solid #cbd5e1; background: #fff; color: #111827; border-radius: 6px; padding: 7px 10px; font-size: 13px; cursor: pointer; }}
        .toolbar button:hover {{ background: #f8fafc; }}
        .toolbar .toggle {{ font-size: 12px; color: #334155; display: inline-flex; align-items: center; gap: 4px; padding: 5px 8px; border: 1px solid #e2e8f0; border-radius: 999px; background: #f8fafc; }}
        .toolbar .toggle input {{ accent-color: #2563eb; }}
        #network {{ height: 640px; border: 1px solid #dbe3ef; border-radius: 8px; background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%); }}
        #network:fullscreen {{ height: 100vh; border-radius: 0; }}
        #details {{ min-height: 42px; padding: 9px 0 0; font-size: 13px; line-height: 1.45; color: #334155; }}
        .legend {{ display: flex; flex-wrap: wrap; gap: 10px; margin-left: auto; font-size: 12px; color: #475569; }}
        .dot {{ width: 10px; height: 10px; border-radius: 999px; display: inline-block; margin-right: 4px; }}
    </style>
</head>
<body>
    <div class="toolbar">
        <select id="depth">
            <option value="1">Relación principal</option>
            <option value="2" selected>+ tipo y municipio</option>
            <option value="3">+ CPV y provincia</option>
        </select>
        <select id="labelMode">
            <option value="main" selected>Etiquetas principales</option>
            <option value="all">Todas las etiquetas</option>
            <option value="none">Sin etiquetas</option>
        </select>
        <select id="layoutMode">
            <option value="free" selected>Layout libre</option>
            <option value="hierarchical">Layout por capas</option>
        </select>
        <label class="toggle"><input type="checkbox" data-group="organo" checked> Órganos</label>
        <label class="toggle"><input type="checkbox" data-group="adjudicatario" checked> Adjudicatarios</label>
        <label class="toggle"><input type="checkbox" data-group="tipo" checked> Tipo</label>
        <label class="toggle"><input type="checkbox" data-group="cpv" checked> CPV</label>
        <label class="toggle"><input type="checkbox" data-group="mun" checked> Municipio</label>
        <label class="toggle"><input type="checkbox" data-group="prov" checked> Provincia</label>
        <button id="edgeLabels">Mostrar importes</button>
        <button id="fit">Centrar</button>
        <button id="physics">Pausar física</button>
        <button id="stabilize">Reordenar</button>
        <button id="fullscreen">⛶ Pantalla completa</button>
        <div class="legend">
            <span><i class="dot" style="background:#2563eb"></i>Órgano</span>
            <span><i class="dot" style="background:#dc2626"></i>Adjudicatario</span>
            <span><i class="dot" style="background:#16a34a"></i>Tipo/CPV</span>
            <span><i class="dot" style="background:#f59e0b"></i>Territorio</span>
        </div>
    </div>
    <div id="network"></div>
    <div id="details">Arrastra nodos, usa la rueda para zoom y selecciona un nodo o enlace para ver detalle.</div>
    <script>
        const allNodes = {payload_nodes};
        const allEdges = {payload_edges};
        const nodeColors = {{
            organo: {{ background: '#dbeafe', border: '#2563eb' }},
            adjudicatario: {{ background: '#fee2e2', border: '#dc2626' }},
            tipo: {{ background: '#dcfce7', border: '#16a34a' }},
            cpv: {{ background: '#ecfccb', border: '#65a30d' }},
            mun: {{ background: '#fef3c7', border: '#f59e0b' }},
            prov: {{ background: '#ffedd5', border: '#ea580c' }}
        }};
        const nodeShapes = {{ organo: 'box', adjudicatario: 'dot', tipo: 'diamond', cpv: 'triangle', mun: 'hexagon', prov: 'hexagon' }};
        let physicsEnabled = true;
        let showEdgeLabels = false;
        let nodes = new vis.DataSet([]);
        let edges = new vis.DataSet([]);
        const container = document.getElementById('network');
        const options = {{
            interaction: {{ hover: true, navigationButtons: true, keyboard: true, multiselect: true, tooltipDelay: 120 }},
            physics: {{
                enabled: true,
                solver: 'forceAtlas2Based',
                forceAtlas2Based: {{ gravitationalConstant: -120, centralGravity: 0.018, springLength: 185, springConstant: 0.06, avoidOverlap: 0.62 }},
                stabilization: {{ iterations: 220 }}
            }},
            nodes: {{
                shape: 'dot',
                font: {{ size: 14, face: 'Inter, system-ui', color: '#111827', strokeWidth: 4, strokeColor: '#ffffff' }},
                borderWidth: 2,
                shadow: {{ enabled: true, color: 'rgba(15,23,42,0.12)', size: 8, x: 0, y: 2 }},
                scaling: {{ min: 12, max: 42, label: {{ enabled: true, min: 12, max: 18 }} }}
            }},
            edges: {{
                color: {{ highlight: '#0f172a', hover: '#334155' }},
                smooth: {{ type: 'continuous', roundness: 0.35 }},
                selectionWidth: 2,
                hoverWidth: 1.5,
                font: {{ size: 10, align: 'middle', color: '#475569', strokeWidth: 3, strokeColor: '#ffffff' }}
            }}
        }};
        const network = new vis.Network(container, {{ nodes, edges }}, options);

        function labelFor(node, mode) {{
            if (mode === 'none') return '';
            if (mode === 'main' && !['organo', 'adjudicatario'].includes(node.group)) return '';
            return mode === 'all' ? node.label : node.labelShort;
        }}

        function filtered(depth) {{
            const labelMode = document.getElementById('labelMode').value;
            const grupoOff = new Set(
                Array.from(document.querySelectorAll('.toggle input'))
                    .filter(el => !el.checked)
                    .map(el => el.dataset.group)
            );
            const visibleEdges = allEdges.filter(edge => {{
                if (Number(edge.depth || 1) > depth) return false;
                const fromNode = allNodes.find(n => n.id === edge.from);
                const toNode = allNodes.find(n => n.id === edge.to);
                if (!fromNode || !toNode) return false;
                if (grupoOff.has(fromNode.group) || grupoOff.has(toNode.group)) return false;
                return true;
            }});
            const visibleIds = new Set();
            visibleEdges.forEach(edge => {{ visibleIds.add(edge.from); visibleIds.add(edge.to); }});
            const visibleNodes = allNodes
                .filter(node => visibleIds.has(node.id))
                .map(node => ({{
                    ...node,
                    label: labelFor(node, labelMode),
                    color: nodeColors[node.group] || undefined,
                    shape: nodeShapes[node.group] || 'dot',
                    margin: node.group === 'organo' ? 9 : undefined
                }}));
            const visibleEdgesStyled = visibleEdges.map(edge => ({{
                ...edge,
                label: showEdgeLabels ? edge.labelRaw : '',
                color: {{ color: edge.color, highlight: '#0f172a', hover: '#334155' }}
            }}));
            nodes.clear(); edges.clear();
            nodes.add(visibleNodes); edges.add(visibleEdgesStyled);
            network.fit({{ animation: {{ duration: 400, easingFunction: 'easeInOutQuad' }} }});
        }}
        filtered(Number(document.getElementById('depth').value));

        document.getElementById('depth').addEventListener('change', event => filtered(Number(event.target.value)));
        document.getElementById('labelMode').addEventListener('change', () => filtered(Number(document.getElementById('depth').value)));
        document.querySelectorAll('.toggle input').forEach(input => {{
            input.addEventListener('change', () => filtered(Number(document.getElementById('depth').value)));
        }});
        document.getElementById('fullscreen').addEventListener('click', () => {{
            const target = document.getElementById('network');
            if (!document.fullscreenElement) {{
                if (target.requestFullscreen) target.requestFullscreen();
            }} else if (document.exitFullscreen) {{
                document.exitFullscreen();
            }}
        }});
        document.addEventListener('fullscreenchange', () => {{
            const btn = document.getElementById('fullscreen');
            btn.textContent = document.fullscreenElement ? '⤫ Salir de pantalla completa' : '⛶ Pantalla completa';
            try {{ network.redraw(); network.fit(); }} catch (e) {{}}
        }});
        document.getElementById('edgeLabels').addEventListener('click', event => {{
            showEdgeLabels = !showEdgeLabels;
            event.target.textContent = showEdgeLabels ? 'Ocultar importes' : 'Mostrar importes';
            filtered(Number(document.getElementById('depth').value));
        }});
        document.getElementById('layoutMode').addEventListener('change', event => {{
            if (event.target.value === 'hierarchical') {{
                network.setOptions({{ layout: {{ hierarchical: {{ enabled: true, direction: 'LR', sortMethod: 'directed', levelSeparation: 230, nodeSpacing: 150 }} }}, physics: false }});
                physicsEnabled = false;
                document.getElementById('physics').textContent = 'Activar física';
            }} else {{
                network.setOptions({{ layout: {{ hierarchical: false }}, physics: true }});
                physicsEnabled = true;
                document.getElementById('physics').textContent = 'Pausar física';
                network.stabilize(180);
            }}
        }});
        document.getElementById('fit').addEventListener('click', () => network.fit({{ animation: true }}));
        document.getElementById('stabilize').addEventListener('click', () => {{ network.setOptions({{ physics: true }}); network.stabilize(160); }});
        document.getElementById('physics').addEventListener('click', event => {{
            physicsEnabled = !physicsEnabled;
            network.setOptions({{ physics: physicsEnabled }});
            event.target.textContent = physicsEnabled ? 'Pausar física' : 'Activar física';
        }});
        network.on('selectNode', params => {{
            const node = nodes.get(params.nodes[0]);
            if (!node) return;
            const connected = network.getConnectedNodes(node.id).length;
            document.getElementById('details').innerHTML = `${{node.title}}<br><strong>${{connected}}</strong> conexiones visibles. Doble clic para centrar el vecindario.`;
        }});
        network.on('selectEdge', params => {{
            const edge = edges.get(params.edges[0]);
            document.getElementById('details').innerHTML = edge ? edge.title : '';
        }});
        network.on('doubleClick', params => {{
            if (!params.nodes.length) return;
            network.focus(params.nodes[0], {{ scale: 1.15, animation: {{ duration: 500, easingFunction: 'easeInOutQuad' }} }});
        }});
    </script>
</body>
</html>
"""


def grafico_mapa_calor_territorial(
    df_input: pd.DataFrame,
    *,
    nivel: str = "CCAA",
    metrica: str = "importe",
) -> go.Figure:
    """Ranking territorial (CCAA o Provincia) por importe o nº de contratos."""
    if df_input is None or df_input.empty or nivel not in df_input.columns:
        return _figura_vacia(f"Sin información de {nivel.lower()} para representar.")

    df = df_input.dropna(subset=[nivel]).copy()
    if df.empty:
        return _figura_vacia(f"No se pudo deducir {nivel.lower()} para los contratos cargados.")

    agreg, eje_x, titulo_x = _agregar_territorio(df, nivel, metrica)
    texto = (
        agreg[eje_x].apply(lambda v: f"{v:,.0f} €".replace(",", "."))
        if metrica == "importe" else agreg[eje_x].astype(int).astype(str)
    )
    agreg["Etiqueta"] = agreg[nivel].apply(lambda texto: _envolver(texto, ancho=32, max_lineas=3))

    fig = go.Figure(go.Bar(
        x=agreg[eje_x],
        y=agreg["Etiqueta"],
        orientation="h",
        marker=dict(
            color=agreg[eje_x],
            colorscale="Tealgrn",
            line=dict(color="#ffffff", width=1),
        ),
        text=texto,
        textposition="outside",
        cliponaxis=False,
        customdata=agreg[[nivel, eje_x]].to_numpy(),
        hovertemplate="<b>%{customdata[0]}</b><br>" + titulo_x + ": %{customdata[1]:,.0f}<extra></extra>",
    ))
    fig.update_layout(xaxis_title=titulo_x, yaxis_title="", yaxis=dict(automargin=True))
    _estilo_editorial(fig, titulo=f"Ranking territorial por {titulo_x.lower()} · {nivel}", alto=max(360, 34 * len(agreg) + 110))
    return fig


def grafico_heatmap_mensual(df_input: pd.DataFrame) -> go.Figure:
    """Heatmap de concentración mensual: filas año fiscal × columnas mes."""
    columnas = {"Fecha", "Importe_euros"}
    if df_input is None or df_input.empty or not columnas.issubset(df_input.columns):
        return _figura_vacia("Sin fechas o importes para construir el heatmap.")

    df = df_input.copy()
    df["_Fecha"] = parsear_fechas_mixtas(df["Fecha"]).values
    df = df.dropna(subset=["_Fecha", "Importe_euros"])
    if df.empty:
        return _figura_vacia("Sin fechas válidas para construir el heatmap.")

    df["_Año"] = df["_Fecha"].dt.year.astype(int)
    df["_Mes"] = df["_Fecha"].dt.month.astype(int)
    pivote = df.pivot_table(
        index="_Año", columns="_Mes", values="Importe_euros",
        aggfunc="sum", fill_value=0,
    ).reindex(columns=range(1, 13), fill_value=0).sort_index(ascending=False)

    meses = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
             "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    fig = go.Figure(go.Heatmap(
        z=pivote.values,
        x=meses,
        y=pivote.index.astype(str),
        colorscale="YlOrRd",
        colorbar=dict(title="€", thickness=12),
        hovertemplate="<b>%{y} · %{x}</b><br>Total: %{z:,.0f} €<extra></extra>",
    ))
    fig.update_layout(xaxis_title="Mes", yaxis_title="Año fiscal")
    _estilo_editorial(fig, titulo="Concentración mensual del gasto", alto=max(320, 80 + 42 * len(pivote)))
    return fig
