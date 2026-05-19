# =============================================================================
# Auditor de Contratos Públicos · Universidade de Santiago de Compostela
# Pruebas: generación de figuras Plotly para análisis visual.
# Autores: Xoán Xosé Pardal Pérez; Alberto Quian (apoyo metodológico y técnico).
# Esta aplicación es parte de los proyectos de I+D+i: PID2024-156034OB-C22 y XornalIA (PDC2025-166024-I00).
# Licencia: MIT (https://opensource.org/license/mit).
# SPDX-License-Identifier: MIT
# =============================================================================

"""Tests ligeros de las visualizaciones Plotly."""
from __future__ import annotations

import math

import pandas as pd
import plotly.graph_objects as go

from core.visual import (
    figuras_editoriales,
    grafico_alertas_prioritarias,
    grafico_histograma_importes,
    grafico_mapa_burbujas_territorial,
    grafico_pareto_adjudicatarios,
    grafico_relaciones_principales,
    grafico_red_organo_adjudicatario,
    grafico_serie_temporal,
    grafico_timeline_contratos,
    grafico_treemap_adjudicatarios,
)


def _df_visual():
    return pd.DataFrame([
        {"Adjudicatario": "ACME SL", "Importe_euros": 14900,
         "Fecha": "2024-01-10", "Tipo_Contrato": "Servicios",
         "Organo": "Concello X", "Concepto": "Servicio 1", "Año_Fiscal": 2024,
         "CCAA": "Galicia", "Provincia": "A Coruña", "Municipio": "Rois"},
        {"Adjudicatario": "ACME SL", "Importe_euros": 14500,
         "Fecha": "2024-01-28", "Tipo_Contrato": "Servicios",
         "Organo": "Concello X", "Concepto": "Servicio 2", "Año_Fiscal": 2024,
         "CCAA": "Galicia", "Provincia": "A Coruña", "Municipio": "Rois"},
        {"Adjudicatario": "Beta SL", "Importe_euros": 1200,
         "Fecha": "2024-03-01", "Tipo_Contrato": "Servicios",
         "Organo": "Concello X", "Concepto": "Compra", "Año_Fiscal": 2024,
         "CCAA": "Galicia", "Provincia": "A Coruña", "Municipio": "Rois"},
    ])


def test_grafico_histograma_importes_devuelve_figure():
    fig = grafico_histograma_importes(_df_visual())
    assert isinstance(fig, go.Figure)
    assert len(fig.data) >= 1


def test_grafico_timeline_contratos_devuelve_figure():
    fig = grafico_timeline_contratos(_df_visual())
    assert isinstance(fig, go.Figure)
    assert len(fig.data) >= 1
    assert fig.layout.title.text == "Calendario de contratos por adjudicatario"
    assert fig.data[0].showlegend is False


def test_graficos_exportables_no_usan_barras_negras_por_defecto():
    for fig in [grafico_serie_temporal(_df_visual()), grafico_histograma_importes(_df_visual())]:
        colores = [getattr(trace.marker, "color", None) for trace in fig.data]
        colores = [color for color in colores if isinstance(color, str)]
        assert colores
        assert all(color.lower() not in {"black", "#000", "#000000"} for color in colores)


def test_grafico_pareto_adjudicatarios_devuelve_barra_y_linea():
    fig = grafico_pareto_adjudicatarios(_df_visual())
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 2


def test_grafico_mapa_burbujas_territorial_devuelve_figure():
    fig = grafico_mapa_burbujas_territorial(_df_visual(), nivel="Provincia")
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 1


def test_grafico_red_organo_adjudicatario_devuelve_figure():
    fig = grafico_red_organo_adjudicatario(_df_visual())
    assert isinstance(fig, go.Figure)
    assert len(fig.data) >= 3


def test_grafico_relaciones_principales_devuelve_barras_exportables():
    fig = grafico_relaciones_principales(_df_visual())
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 1
    assert fig.layout.title.text == "Relaciones principales órgano-adjudicatario"


def test_grafico_alertas_prioritarias_devuelve_figure():
    radar = pd.DataFrame([
        {"Adjudicatario": "Empresa con nombre muy largo para validar etiquetas", "Organo": "Concello X",
         "Total_euros": 29_400, "Num_Contratos": 2, "Indice_Riesgo": 95,
         "Es_Alerta": True},
    ])
    fig = grafico_alertas_prioritarias(radar)
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 1


def test_figuras_editoriales_no_incluye_grafo_estatico():
    figs = figuras_editoriales(pd.DataFrame(), _df_visual())
    titulos = [fig.layout.title.text for fig in figs if fig.layout.title.text]
    assert "Relaciones principales órgano-adjudicatario" in titulos
    assert all("Red" not in titulo for titulo in titulos)


def test_grafico_treemap_sanea_colores_y_muestra_texto_uniforme():
    radar = pd.DataFrame([
        {"Adjudicatario": "Empresa A con nombre largo", "Tipo_Contrato": "Servicios",
         "Total_euros": 30_000, "Total_Formateado": "30.000,00 €",
         "Num_Contratos": 3, "Porcentaje_Limite": float("inf")},
        {"Adjudicatario": "Empresa B", "Tipo_Contrato": "Suministros",
         "Total_euros": 12_000, "Total_Formateado": "12.000,00 €",
         "Num_Contratos": 2, "Porcentaje_Limite": -5},
    ])
    fig = grafico_treemap_adjudicatarios(radar)
    colors = list(fig.data[0].marker.colors)
    assert colors[0] == "#ffffff"
    valores_color = [float(color) for color in colors[1:]]
    assert all(math.isfinite(color) for color in valores_color)
    assert min(valores_color) >= 0
    assert max(valores_color) <= 120
    assert fig.layout.uniformtext.mode == "show"
    assert fig.data[0].root.color == "#ffffff"
    assert fig.data[0].tiling.pad == 1
