# =============================================================================
# Auditor de Contratos Públicos · Universidade de Santiago de Compostela
# Pruebas: informes descargables y tablas CSV.
# Autores: Xoán Xosé Pardal Pérez; Alberto Quian (apoyo metodológico y técnico).
# Esta aplicación es parte del proyecto de I+D+i:
# - XornalIA: Desarrollo, validación y transferencia de una plataforma integradora de soluciones de inteligencia artificial generativa para medios de comunicación (PDC2025-166024-I00).
# Licencia: MIT (https://opensource.org/license/mit).
# SPDX-License-Identifier: MIT
# =============================================================================

"""Tests de informes descargables orientados a texto y tablas."""
from __future__ import annotations

from io import BytesIO
from zipfile import ZipFile

import pandas as pd
import pdfplumber

from core.pdf_report import render_informe_pdf
from core.report import figuras_a_zip, render_informe_entidad, tablas_a_zip
from core.visual import _figura_vacia, grafico_histograma_importes


def _radar() -> pd.DataFrame:
    return pd.DataFrame([
        {
            "Adjudicatario": "ACME SL",
            "Organo": "Concello X",
            "Tipo_Contrato": "Servicios",
            "Año_Fiscal": 2024,
            "Num_Contratos": 2,
            "Total_euros": 29_400,
            "Total_Formateado": "29.400,00 €",
            "Limite_Legal": 15_000,
            "Porcentaje_Limite_Formateado": "196,0 %",
            "Indice_Riesgo": 95,
            "Prioridad": "Alta",
            "Nivel_Riesgo": "🚨 Crítico",
            "Señales_Riesgo": "Importes próximos al límite",
            "Dias_Entre_Contratos": 18,
            "Importes_Individuales": "14.900,00 €; 14.500,00 €",
            "Es_Alerta": True,
        },
    ])


def _df_input() -> pd.DataFrame:
    return pd.DataFrame([
        {
            "Fecha": "2024-01-10",
            "Adjudicatario": "ACME SL",
            "Organo": "Concello X",
            "Tipo_Contrato": "Servicios",
            "Importe_euros": 14_900,
            "Concepto": "Servicio 1",
        },
        {
            "Fecha": "2024-01-28",
            "Adjudicatario": "ACME SL",
            "Organo": "Concello X",
            "Tipo_Contrato": "Servicios",
            "Importe_euros": 14_500,
            "Concepto": "Servicio 2",
        },
    ])


def test_render_informe_entidad_embebe_plotly_y_no_etiqueta_tfg():
    html = render_informe_entidad(
        titulo="Validación",
        radar=_radar(),
        df_input=_df_input(),
        figuras=[grafico_histograma_importes(_df_input())],
    )
    assert "Plotly.newPlot" in html
    assert "plotly-graph-div" in html
    assert "TFG" not in html
    assert "table-layout: fixed" in html
    assert "overflow-x: hidden" in html
    assert "Las visualizaciones interactivas se consultan dentro de la aplicación" not in html


def test_render_informe_pdf_no_incluye_pie_de_licencia_o_tfg():
    pdf_bytes = render_informe_pdf(
        titulo="Validación",
        radar=_radar(),
        df_input=_df_input(),
        figuras=[],
    )
    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        texto = "\n".join(page.extract_text() or "" for page in pdf.pages)
    assert "Software publicado bajo licencia MIT" not in texto
    assert "XornalIA" not in texto
    assert "TFG Periodismo" not in texto


def test_tablas_a_zip_incluye_csv_editables():
    contenido = tablas_a_zip(_radar(), _df_input())
    with ZipFile(BytesIO(contenido)) as zip_file:
        assert zip_file.namelist() == [
            "01_alertas.csv",
            "02_radar_completo.csv",
            "03_top_adjudicatarios.csv",
            "04_relaciones_organo_adjudicatario.csv",
            "05_contratos_filtrados.csv",
        ]
        contratos = zip_file.read("05_contratos_filtrados.csv").decode("utf-8-sig")
    assert "ACME SL" in contratos
    assert "Servicio 1" in contratos


def test_figuras_vacias_se_filtran_de_html_y_zip():
    figuras = [grafico_histograma_importes(_df_input()), _figura_vacia("Sin datos")]
    html = render_informe_entidad(
        titulo="Validación",
        radar=_radar(),
        df_input=_df_input(),
        figuras=figuras,
    )
    assert html.count("plotly-graph-div") == 1
    assert "Sin datos" not in html
    zip_bytes = figuras_a_zip(figuras, prefijo="prueba")
    if zip_bytes is None:
        return  # Kaleido no disponible
    with ZipFile(BytesIO(zip_bytes)) as zf:
        nombres = [n for n in zf.namelist() if n.endswith(".png")]
    assert len(nombres) == 1
