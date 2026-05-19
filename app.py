# =============================================================================
# Auditor de Contratos Públicos
# Universidade de Santiago de Compostela
#
# Descripción: interfaz Streamlit local-first para descargar, cargar y analizar
# datos oficiales de contratación pública y gasto local en España.
# Autor principal: Xoán Xosé Pardal Pérez.
# Apoyo metodológico y técnico: Alberto Quian (https://albertoquian.github.io/).
# Esta aplicación es parte de los proyectos de I+D+i: PID2024-156034OB-C22 y XornalIA (PDC2025-166024-I00).
# Licencia: MIT (https://opensource.org/license/mit).
# SPDX-License-Identifier: MIT
# =============================================================================

"""
AUDITOR DE CONTRATOS PÚBLICOS
=============================
Herramienta local-first para detectar fraccionamiento de contratos
("pitufeo") y analizar el gasto público de los entes locales españoles.

Tres fuentes de datos unificadas:

  1) PLACSP        — Plataforma de Contratación del Sector Público
                     (carpeta de archivos .atom, p. ej. 1100/año).
  2) Tribunal de Cuentas — Liquidaciones presupuestarias de TODOS los
                     entes locales (1,19 M filas) consultadas con DuckDB.
  3) Archivos sueltos — PDF / CSV / Excel para análisis forense puntual.

Ejecutar:
    streamlit run app.py
"""
from __future__ import annotations

import os
import platform
import re
import shutil
import time
from pathlib import Path

import pandas as pd
import pdfplumber
import streamlit as st

from core.analysis import (
    analizar_texto_por_pagina,
    detectar_banderas,
    ejecutar_radar,
    parsear_fechas_mixtas,
    pintar_filas_banderas,
)
from core.constants import (
    LIMITE_OBRAS,
    LIMITE_SERVICIOS,
    PATRONES,
    PROVINCIAS_GALICIA,
    inferir_geografia,
    inferir_municipio,
)
from core.downloaders import (
    DEFAULT_PLACSP_MENORES_URL,
    descargar_placsp_menores,
    descargar_url_directa,
)
from core.money import formatear_euros, limpiar_dinero
from core.placsp import cargar_placsp, filtrar_por_organos, filtrar_por_texto_organismo
from core.pdf_report import render_informe_pdf
from core.report import (
    export_estatico_disponible,
    figuras_a_zip,
    render_informe_entidad,
    tablas_a_zip,
)
from core.tribunal_cuentas import (
    detalle_partidas_entidad,
    exportar_accdb_a_csv,
    mdbtools_disponible,
    ranking_gasto_capitulo,
)
from core.visual import (
    grafico_dispersion_riesgo,
    grafico_heatmap_mensual,
    grafico_histograma_importes,
    grafico_mapa_burbujas_territorial,
    grafico_mapa_calor_territorial,
    grafico_pareto_adjudicatarios,
    grafico_red_organo_adjudicatario,
    grafico_ranking_entidades,
    grafico_relaciones_principales,
    grafico_serie_temporal,
    grafico_timeline_contratos,
    grafico_treemap_adjudicatarios,
    grafo_relaciones_interactivo_html,
)


MIT_LICENSE_URL = "https://opensource.org/license/mit"
RESEARCH_PROJECTS_HTML = """
<ul style="margin: .35rem 0 0 1.1rem; padding: 0;">
    <li><em>Inteligencia artificial en medios digitales en España: efectos y roles</em> (PID2024-156034OB-C22), financiado por MICIU/AEI/10.13039/501100011033 y “FEDER/UE”.</li>
    <li><em>XornalIA</em> (PDC2025-166024-I00 - Desarrollo, validación y transferencia de una plataforma integradora de soluciones de inteligencia artificial generativa para medios de comunicación), financiado por el Ministerio de Ciencia e Innovación y la Agencia Estatal de Investigación.</li>
</ul>
""".strip()
AUTHORS_LINE_HTML = (
    "<strong>Xoán Xosé Pardal Pérez</strong> (autor principal) y "
    "<a href=\"https://albertoquian.github.io/\" target=\"_blank\">Alberto Quian</a> "
    "(apoyo metodológico y técnico)"
)
PLOTLY_CONFIG = {
    "displaylogo": False,
    "responsive": True,
    "toImageButtonOptions": {
        "format": "png",
        "filename": "grafico_auditoria",
        "width": 1600,
        "height": 950,
        "scale": 2,
    },
}
DATA_DIR = Path("data")
UPLOADS_DIR = DATA_DIR / "uploads"
DEFAULT_PLACSP_DIR = DATA_DIR / "placsp_menores"
DEFAULT_TRIBUNAL_DIR = DATA_DIR / "tribunal_cuentas"

# =============================================================================
# CONFIGURACIÓN STREAMLIT
# =============================================================================
st.set_page_config(
    page_title="Auditor de Contratos Públicos",
    page_icon="🕵️",
    layout="wide",
    initial_sidebar_state="auto",
)

st.title("🕵️ Auditor de Contratos Públicos")
st.caption(
    "Detección de fraccionamiento (*pitufeo*) y análisis del gasto local "
    "para periodismo de investigación y rendición de cuentas."
)


def _plotly(fig) -> None:
    st.plotly_chart(fig, width="stretch", config=PLOTLY_CONFIG)


def _ruta_usuario(valor: str | Path) -> Path:
    return Path(valor).expanduser()


def _nombre_seguro(nombre: str) -> str:
    limpio = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(nombre).name).strip("._")
    return limpio or "archivo"


def _crear_carpeta_boton(ruta: str, *, key: str, etiqueta: str = "Crear carpeta") -> None:
    if st.button(etiqueta, key=key):
        try:
            carpeta = _ruta_usuario(ruta)
            carpeta.mkdir(parents=True, exist_ok=True)
            st.success(f"✅ Carpeta disponible: {carpeta.resolve()}")
        except Exception as exc:
            st.error(f"❌ No se pudo crear la carpeta: {exc}")


def _guardar_archivo_subido(archivo, carpeta_destino: str | Path) -> Path:
    destino = _ruta_usuario(carpeta_destino)
    destino.mkdir(parents=True, exist_ok=True)
    salida = destino / _nombre_seguro(archivo.name)
    if salida.exists() and salida.stat().st_size == getattr(archivo, "size", -1):
        return salida.resolve()
    salida.write_bytes(archivo.getbuffer())
    return salida.resolve()


def _guardar_archivos_subidos(archivos, carpeta_destino: str | Path) -> list[Path]:
    return [_guardar_archivo_subido(archivo, carpeta_destino) for archivo in archivos]


# =============================================================================
# CACHÉ
# =============================================================================
@st.cache_data(show_spinner=False)
def _cached_placsp(carpeta: str) -> pd.DataFrame:
    barra = st.progress(0.0, text="Procesando PLACSP…")

    def _prog(i, total):
        barra.progress(i / total, text=f"Procesando PLACSP… {i}/{total}")

    df = cargar_placsp(carpeta, progreso=_prog)
    barra.empty()
    return df


def _cargar_placsp_en_estado(ruta: str, *, forzar: bool = False) -> pd.DataFrame:
    """Carga una carpeta PLACSP y la deja disponible para filtros y radar."""
    if not ruta or not Path(ruta).is_dir():
        st.error("❌ La ruta no existe o no es accesible.")
        return pd.DataFrame()
    if forzar:
        _cached_placsp.clear()
    try:
        df_bruto = _cached_placsp(str(Path(ruta).resolve()))
    except FileNotFoundError as e:
        st.error(str(e))
        return pd.DataFrame()

    if df_bruto.empty:
        st.warning("⚠️ No se encontraron contratos menores en esa carpeta.")
        return df_bruto

    st.session_state["placsp_df"] = df_bruto
    st.success(f"✅ {len(df_bruto):,} contratos menores cargados.")
    return df_bruto


@st.cache_data(show_spinner=True)
def _cached_ranking(econ: str, inv: str, capitulo: int, provincias_key: str) -> pd.DataFrame:
    provs = tuple(provincias_key.split(",")) if provincias_key else None
    return ranking_gasto_capitulo(econ, inv, capitulo=capitulo, provincias=provs)


def _columnas_radar_visibles(radar: pd.DataFrame) -> list[str]:
    columnas = [
        "Prioridad", "Indice_Riesgo", "Adjudicatario", "Organo", "Tipo_Contrato",
        "Año_Fiscal", "Num_Contratos", "Total_Formateado", "Limite_Legal",
        "Porcentaje_Limite_Formateado", "Nivel_Riesgo", "Señales_Riesgo",
        "Dias_Entre_Contratos", "Importes_Individuales",
    ]
    return [columna for columna in columnas if columna in radar.columns]


def _mostrar_resumen_radar(radar: pd.DataFrame) -> None:
    if radar is None or radar.empty:
        return
    niveles = radar["Nivel_Riesgo"].value_counts() if "Nivel_Riesgo" in radar.columns else pd.Series(dtype=int)
    col_supera, col_roza, col_cerca, col_total = st.columns(4)
    col_supera.metric("Acumulado > límite", int(niveles.get("🚨 Acumulado > límite legal", 0)))
    col_roza.metric("Roza >95 %", int(niveles.get("🔴 Roza el límite (>95%)", 0)))
    col_cerca.metric("Cerca >90 %", int(niveles.get("🟠 Cerca del límite (>90%)", 0)))
    col_total.metric("Grupos analizados", f"{len(radar):,}".replace(",", "."))


def _detalle_caso(df_input: pd.DataFrame, caso: pd.Series) -> pd.DataFrame:
    if df_input is None or df_input.empty:
        return pd.DataFrame()

    columna_adjudicatario = "_Adjudicatario_Radar" if "_Adjudicatario_Radar" in df_input.columns else "Adjudicatario"
    if columna_adjudicatario not in df_input.columns:
        return pd.DataFrame()

    mascara = df_input[columna_adjudicatario].astype(str) == str(caso.get("Adjudicatario", ""))
    for columna in ["Organo", "Tipo_Contrato"]:
        if columna in df_input.columns and columna in caso:
            mascara &= df_input[columna].astype(str) == str(caso[columna])
    if "Año_Fiscal" in df_input.columns and "Año_Fiscal" in caso:
        anio_caso = pd.to_numeric(pd.Series([caso["Año_Fiscal"]]), errors="coerce").iloc[0]
        anios = pd.to_numeric(df_input["Año_Fiscal"], errors="coerce")
        mascara &= anios == anio_caso

    detalle = df_input.loc[mascara].copy()
    if "Fecha" in detalle.columns:
        detalle["_Fecha_Orden"] = parsear_fechas_mixtas(detalle["Fecha"])
        detalle = detalle.sort_values("_Fecha_Orden", na_position="last")
    columnas = [
        "Fecha", "Organo", "Año_Fiscal", "Tipo_Contrato", "Concepto",
        "Adjudicatario", "Importe_euros",
    ]
    return detalle[[columna for columna in columnas if columna in detalle.columns]]


def _mostrar_ficha_caso(radar: pd.DataFrame, df_input: pd.DataFrame, titulo: str) -> None:
    alertas = radar[radar["Es_Alerta"]].copy() if "Es_Alerta" in radar.columns else pd.DataFrame()
    if alertas.empty:
        return

    st.markdown("### 🧾 Ficha de caso prioritario")
    casos = alertas.sort_values(["Indice_Riesgo", "Total_euros"], ascending=False).reset_index(drop=True)
    seleccion = st.selectbox(
        titulo,
        options=list(casos.index),
        format_func=lambda indice: (
            f"{casos.loc[indice, 'Prioridad']} · {casos.loc[indice, 'Adjudicatario']} · "
            f"{casos.loc[indice, 'Total_Formateado']}"
        ),
    )
    caso = casos.loc[seleccion]

    col_indice, col_total, col_contratos, col_porcentaje = st.columns(4)
    col_indice.metric("Índice", f"{int(caso['Indice_Riesgo'])}/100", caso["Prioridad"])
    col_total.metric("Total", caso["Total_Formateado"])
    col_contratos.metric("Contratos", int(caso["Num_Contratos"]))
    col_porcentaje.metric(
        "Acumulado vs. límite",
        caso.get("Porcentaje_Limite_Formateado", "—"),
        help=(
            "Suma de los importes de todos los contratos del grupo, expresada como "
            "porcentaje del límite legal de contrato menor (15.000 € servicios, "
            "40.000 € obras). Un valor > 100 % no significa que un contrato individual "
            "supere el límite, sino que la suma de varios contratos del mismo "
            "adjudicatario lo rebasa: posible indicio de fraccionamiento."
        ),
    )

    st.markdown(f"**Señales:** {caso.get('Señales_Riesgo', '—')}")
    detalle = _detalle_caso(df_input, caso)
    if not detalle.empty:
        st.dataframe(
            detalle,
            width="stretch",
            column_config={
                "Importe_euros": st.column_config.NumberColumn("💰 Importe", format="%.2f €"),
                "Año_Fiscal": st.column_config.NumberColumn("📅 Año", format="%d"),
            },
        )


def _figuras_forenses(radar: pd.DataFrame, df_input: pd.DataFrame, *, para_informe: bool = False) -> list:
    relaciones = (
        grafico_relaciones_principales(df_input)
        if para_informe
        else grafico_red_organo_adjudicatario(df_input)
    )
    figuras = [
        grafico_treemap_adjudicatarios(radar),
        grafico_dispersion_riesgo(radar),
        grafico_serie_temporal(df_input),
        grafico_histograma_importes(df_input),
        grafico_timeline_contratos(df_input),
        grafico_pareto_adjudicatarios(df_input),
        relaciones,
    ]
    # Mapa y ranking territorial: emitimos todos los niveles disponibles.
    for nivel in ("CCAA", "Provincia", "Municipio"):
        if nivel not in df_input.columns or not df_input[nivel].notna().any():
            continue
        if nivel != "Municipio":
            figuras.append(grafico_mapa_burbujas_territorial(df_input, nivel=nivel))
        figuras.append(grafico_mapa_calor_territorial(df_input, nivel=nivel))
    figuras.append(grafico_heatmap_mensual(df_input))
    return figuras


def _mostrar_visualizaciones_forenses(radar: pd.DataFrame, df_input: pd.DataFrame, titulo_informe: str) -> None:
    st.markdown("### 📊 Visualizaciones interactivas")
    pestanas = st.tabs([
        "Treemap adjudicatarios",
        "Dispersión riesgo",
        "Serie temporal",
        "Distribución importes",
        "Timeline contratos",
        "Concentración gasto",
        "Red relaciones",
        "Mapa territorial",
        "Calendario mensual",
        "📄 Informe y descargas",
    ])
    (tab_tree, tab_disp, tab_serie, tab_hist, tab_time, tab_pareto, tab_red,
     tab_geo, tab_heat, tab_html) = pestanas
    with tab_tree:
        _plotly(grafico_treemap_adjudicatarios(radar))
        if radar is not None and not radar.empty:
            columnas_treemap = [
                columna for columna in [
                    "Adjudicatario",
                    "Organo",
                    "Total_Formateado",
                    "Num_Contratos",
                    "Porcentaje_Limite_Formateado",
                    "Nivel_Riesgo",
                ]
                if columna in radar.columns
            ]
            if columnas_treemap:
                tabla_treemap = (
                    radar.sort_values("Total_euros", ascending=False)
                    .head(30)[columnas_treemap]
                    .copy()
                )
                st.markdown("#### Top adjudicatarios del treemap")
                st.dataframe(tabla_treemap, width="stretch", hide_index=True)
    with tab_disp:
        _plotly(grafico_dispersion_riesgo(radar))
    with tab_serie:
        _plotly(grafico_serie_temporal(df_input))
    with tab_hist:
        _plotly(grafico_histograma_importes(df_input))
    with tab_time:
        _plotly(grafico_timeline_contratos(df_input))
    with tab_pareto:
        _plotly(grafico_pareto_adjudicatarios(df_input))
    with tab_red:
        st.caption(
            "Arrastra los nodos, usa los filtros y el botón ⛶ para abrir el grafo a pantalla completa."
        )
        st.iframe(
            grafo_relaciones_interactivo_html(df_input),
            width="stretch",
            height=760,
        )
    with tab_geo:
        niveles_geo = [
            n for n in ("CCAA", "Provincia", "Municipio")
            if n in df_input.columns and df_input[n].notna().any()
        ]
        if not niveles_geo:
            st.info("Esta fuente no incluye datos geográficos para mapear.")
        else:
            opcion = st.radio(
                "Nivel territorial",
                niveles_geo,
                horizontal=True,
                key=f"geo_nivel_{titulo_informe}",
            )
            metrica = st.radio(
                "Métrica",
                ["Importe total", "Número de contratos"],
                horizontal=True,
                key=f"geo_metrica_{titulo_informe}",
            )
            territorios = sorted(df_input[opcion].dropna().astype(str).unique().tolist())
            if len(territorios) == 1:
                st.caption(
                    f"En el filtro actual solo hay un valor para {opcion}: {territorios[0]}. "
                    "Por eso el mapa puede parecer igual al cambiar de nivel territorial."
                )
            if opcion == "Municipio" and set(territorios) & {"Ceuta", "Melilla"}:
                st.caption(
                    "En Ceuta y Melilla, ciudad autónoma, provincia y municipio coinciden administrativamente."
                )
            if opcion in ("CCAA", "Provincia"):
                _plotly(
                    grafico_mapa_burbujas_territorial(
                        df_input,
                        nivel=opcion,
                        metrica="importe" if metrica.startswith("Importe") else "contratos",
                    )
                )
            else:
                st.info("El nivel municipal se muestra como ranking porque PLACSP no publica coordenadas municipales normalizadas.")
            _plotly(
                grafico_mapa_calor_territorial(
                    df_input,
                    nivel=opcion,
                    metrica="importe" if metrica.startswith("Importe") else "contratos",
                )
            )
    with tab_heat:
        _plotly(grafico_heatmap_mensual(df_input))
    with tab_html:
        radar_para_informe = (
            radar[radar["Es_Alerta"]] if mostrar_solo_alertas and "Es_Alerta" in radar.columns
            else radar
        )
        st.caption(
            "El informe refleja la selección actual del checkbox «Mostrar solo "
            "casos con alerta» (barra lateral)."
        )
        figuras_informe = _figuras_forenses(radar_para_informe, df_input, para_informe=True)
        col_html, col_pdf, col_tablas, col_png = st.columns(4)
        with col_html:
            html = render_informe_entidad(
                titulo=titulo_informe,
                radar=radar_para_informe,
                df_input=df_input,
                figuras=figuras_informe,
            )
            st.download_button(
                "⬇️ Informe HTML",
                html.encode("utf-8"),
                "informe_auditoria.html",
                "text/html",
                key=f"dl_html_{titulo_informe}",
            )
            st.caption(
                "HTML autoportante con resumen, tablas y gráficos interactivos."
            )
        with col_pdf:
            pdf_bytes = render_informe_pdf(
                titulo=titulo_informe,
                radar=radar_para_informe,
                df_input=df_input,
                figuras=[],
            )
            st.download_button(
                "📄 Informe PDF",
                pdf_bytes,
                "informe_auditoria.pdf",
                "application/pdf",
                key=f"dl_pdf_{titulo_informe}",
            )
            st.caption(
                "PDF imprimible con resumen narrativo, alertas y tablas de contexto."
            )
        with col_tablas:
            zip_tablas = tablas_a_zip(radar_para_informe, df_input)
            st.download_button(
                "🧾 Tablas CSV",
                zip_tablas,
                "tablas_auditoria.zip",
                "application/zip",
                key=f"dl_tablas_{titulo_informe}",
            )
            st.caption("ZIP con alertas, radar, relaciones y contratos filtrados.")
        with col_png:
            clave_png = f"zip_png_{abs(hash(titulo_informe))}"
            if not export_estatico_disponible():
                st.info(
                    "PNG no disponible: instala `kaleido` para generar el ZIP "
                    "de gráficos estáticos."
                )
            elif st.button("🖼️ Preparar PNG", key=f"prep_{clave_png}"):
                with st.spinner("Generando ZIP con los gráficos de la interfaz…"):
                    st.session_state[clave_png] = figuras_a_zip(
                        figuras_informe,
                        prefijo="grafico_auditoria",
                    )
            zip_png = st.session_state.get(clave_png)
            if zip_png:
                st.download_button(
                    "⬇️ Gráficos PNG",
                    zip_png,
                    "graficos_auditoria_png.zip",
                    "application/zip",
                    key=f"dl_{clave_png}",
                )
            st.caption(
                "ZIP con los gráficos Plotly de la interfaz exportados en PNG."
            )


# =============================================================================
# BARRA LATERAL
# =============================================================================
with st.sidebar:
    st.header("Fuente de datos")
    fuente = st.radio(
        "Elige el tipo de análisis:",
        [
            "🌐 PLACSP (carpeta .atom)",
            "🏛️ Tribunal de Cuentas (CSV/.accdb)",
            "📄 Archivo individual (PDF/CSV/Excel)",
            "❓ Guía de uso",
        ],
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.header("Umbrales del radar")
    min_contratos = st.slider(
        "Mínimo de contratos para alerta",
        min_value=2, max_value=10, value=2,
        help="2 = máxima sensibilidad · 3+ = menos falsos positivos",
    )
    mostrar_solo_alertas = st.checkbox(
        "Mostrar solo casos con alerta",
        value=True,
        help=(
            "Filtra las tablas y el informe para mostrar únicamente los grupos "
            "que el radar marca como alerta (acumulado >= 90 % del límite legal). "
            "Desactívalo para ver también los grupos sin alerta y comparar."
        ),
    )


# =============================================================================
# RUTA 1 — PLACSP NACIONAL (.atom)
# =============================================================================
if fuente.startswith("🌐"):
    st.subheader("Base de datos PLACSP (.atom)")
    st.info(
        "Procesa miles de contratos menores publicados por el Estado. "
        "El primer cargado tarda; los siguientes son instantáneos gracias al caché."
    )

    with st.expander("⬇️ Descargar/actualizar .atom oficiales de PLACSP", expanded=False):
        st.caption(
            "Descarga el feed oficial paginado de contratos menores. La app guarda "
            "cada página .atom y un manifiesto JSON con las URLs visitadas."
        )
        url_placsp = DEFAULT_PLACSP_MENORES_URL
        st.markdown("**URL de la fuente oficial (automática):**")
        st.code(url_placsp, language="text")
        destino_placsp = st.session_state.get("placsp_carpeta", str(DEFAULT_PLACSP_DIR))
        st.caption(f"📁 Los .atom se guardarán en: `{destino_placsp}` (se crea automáticamente si no existe).")
        col_d2, col_d3 = st.columns([1, 1])
        with col_d2:
            max_atom = st.number_input(
                "Máx. páginas a descargar (más páginas → más antigüedad)",
                min_value=1,
                max_value=5000,
                value=30,
                step=10,
                help=(
                    "Cada página del feed contiene un lote de contratos en orden "
                    "cronológico inverso. Cuanto mayor sea el número de páginas, "
                    "más histrórico (más antigüedad) se descargará."
                ),
            )
        with col_d3:
            sobrescribir_atom = st.checkbox("Sobrescribir", value=False)
        auto_cargar_placsp = st.checkbox(
            "Cargar y analizar al terminar",
            value=True,
            help="Tras descargar el feed, procesa automáticamente la carpeta y deja los contratos listos para filtrar.",
        )

        if st.button("⬇️ Descargar/actualizar PLACSP"):
            barra_descarga = st.progress(0.0, text="Preparando descarga…")

            def _progreso_descarga(i, total, url_actual):
                nombre = str(url_actual).rsplit("/", 1)[-1] or str(url_actual)
                barra_descarga.progress(
                    min(i / total, 1.0),
                    text=f"Descargando {i}/{total}: {nombre}",
                )

            resultado = descargar_placsp_menores(
                destino_placsp,
                url_inicial=url_placsp,
                max_archivos=int(max_atom),
                sobrescribir=sobrescribir_atom,
                progreso=_progreso_descarga,
            )
            barra_descarga.empty()
            st.session_state["placsp_carpeta"] = str(Path(destino_placsp).resolve())
            st.success(
                f"✅ {len(resultado.descargados)} archivos descargados; "
                f"{len(resultado.omitidos)} ya existían."
            )
            if resultado.manifest_path:
                st.caption(f"Manifiesto: {resultado.manifest_path}")
            if resultado.errores:
                st.warning("Algunos lotes no se pudieron descargar:\n" + "\n".join(resultado.errores[:5]))
            if auto_cargar_placsp:
                _cargar_placsp_en_estado(
                    st.session_state["placsp_carpeta"],
                    forzar=bool(resultado.descargados) or sobrescribir_atom,
                )

    st.markdown("### Cargar contratos .atom")
    st.caption(
        "Si acabas de descargar el feed (panel superior), pulsa directamente \u201c🚀 Cargar y analizar\u201d. "
        "Si traes .atom de otra parte, puedes seleccionarlos con el botón del navegador."
    )
    modo_placsp = st.radio(
        "Modo de carga PLACSP",
        ["Usar carpeta local", "Seleccionar archivos .atom"],
        horizontal=True,
    )
    forzar = st.checkbox("Recargar caché", value=False)

    if modo_placsp == "Seleccionar archivos .atom":
        archivos_atom = st.file_uploader(
            "Selecciona uno o varios archivos .atom/.xml",
            type=["atom", "xml"],
            accept_multiple_files=True,
            help="Para históricos grandes suele ser más cómodo descargar desde la pestaña anterior.",
        )
        carpeta_atom_subidos = st.session_state.get("placsp_upload_dir", str(UPLOADS_DIR / "placsp_atom"))
        st.caption(f"📁 Los archivos seleccionados se copiarán a `{carpeta_atom_subidos}`.")
        ruta = st.session_state.get("placsp_carpeta", "")
        if st.button("💾 Guardar .atom seleccionados y analizar"):
            if not archivos_atom:
                st.error("❌ Selecciona al menos un archivo .atom o .xml.")
            else:
                guardados = _guardar_archivos_subidos(archivos_atom, carpeta_atom_subidos)
                st.session_state["placsp_upload_dir"] = str(_ruta_usuario(carpeta_atom_subidos))
                st.session_state["placsp_carpeta"] = str(_ruta_usuario(carpeta_atom_subidos).resolve())
                st.success(f"✅ {len(guardados)} archivo(s) guardado(s) en {st.session_state['placsp_carpeta']}")
                _cargar_placsp_en_estado(st.session_state["placsp_carpeta"], forzar=forzar)
    else:
        ruta_default = st.session_state.get("placsp_carpeta", str(DEFAULT_PLACSP_DIR))
        st.caption(f"📁 Carpeta a analizar: `{ruta_default}`")
        with st.expander("⚙️ Cambiar carpeta (avanzado)", expanded=False):
            ruta_default = st.text_input(
                "Ruta de la carpeta con archivos .atom",
                value=ruta_default,
                placeholder="Ej.: data/placsp_menores o /ruta/a/contratosMenores...",
                help="Sólo necesario si quieres analizar una carpeta distinta a la que descargó la app.",
            )
        ruta = ruta_default
        if st.button("🚀 Cargar y analizar"):
            _cargar_placsp_en_estado(ruta, forzar=forzar)

    palabras = ""

    df_bruto = st.session_state.get("placsp_df", pd.DataFrame())
    if not df_bruto.empty:
        df_filtrado = filtrar_por_organos(df_bruto, palabras.split(",")) if palabras else df_bruto

        st.markdown("### 🎯 Filtro de precisión")

        col_geo1, col_geo2, col_geo3, col_geo4 = st.columns(4)
        with col_geo1:
            ccaa_disp = (
                sorted(df_filtrado["CCAA"].dropna().unique().tolist())
                if "CCAA" in df_filtrado.columns else []
            )
            ccaa_sel = st.multiselect(
                "Comunidad autónoma",
                options=ccaa_disp,
                placeholder="Todas",
            )
        with col_geo2:
            df_para_provs = df_filtrado.copy()
            if ccaa_sel and "CCAA" in df_para_provs.columns:
                df_para_provs = df_para_provs[df_para_provs["CCAA"].isin(ccaa_sel)]
            provs_disp = (
                sorted(df_para_provs["Provincia"].dropna().unique().tolist())
                if "Provincia" in df_para_provs.columns else []
            )
            provs_sel = st.multiselect(
                "Provincia",
                options=provs_disp,
                placeholder="Todas",
            )
        with col_geo3:
            df_para_munis = df_para_provs.copy()
            if provs_sel and "Provincia" in df_para_munis.columns:
                df_para_munis = df_para_munis[df_para_munis["Provincia"].isin(provs_sel)]
            munis_disp = (
                sorted(df_para_munis["Municipio"].dropna().unique().tolist())
                if "Municipio" in df_para_munis.columns else []
            )
            munis_sel = st.multiselect(
                "Municipio",
                options=munis_disp,
                placeholder="Todos",
            )
        with col_geo4:
            tipos_ent_disp = (
                sorted(df_filtrado["Tipo_Entidad"].dropna().unique().tolist())
                if "Tipo_Entidad" in df_filtrado.columns else []
            )
            tipos_ent_sel = st.multiselect(
                "Tipo de entidad",
                options=tipos_ent_disp,
                placeholder="Todos (ayuntamientos, diputaciones, ministerios…)",
            )

        df_geo = df_filtrado.copy()
        if ccaa_sel and "CCAA" in df_geo.columns:
            df_geo = df_geo[df_geo["CCAA"].isin(ccaa_sel)]
        if provs_sel and "Provincia" in df_geo.columns:
            df_geo = df_geo[df_geo["Provincia"].isin(provs_sel)]
        if munis_sel and "Municipio" in df_geo.columns:
            df_geo = df_geo[df_geo["Municipio"].isin(munis_sel)]
        if tipos_ent_sel and "Tipo_Entidad" in df_geo.columns:
            df_geo = df_geo[df_geo["Tipo_Entidad"].isin(tipos_ent_sel)]

        col1, col2 = st.columns([3, 1])
        with col1:
            busca_organo = st.text_input(
                "🔎 Buscar ayuntamiento u órgano",
                value="",
                placeholder="Ej.: Santiago de Compostela, Compostela, València…",
                help=(
                    "Filtra los organismos por cualquier parte del nombre del órgano "
                    "o del municipio, sin distinguir acentos. Sirve para nombres "
                    "compuestos: puedes escribir el nombre completo o una parte."
                ),
            )
            df_geo_organos = (
                filtrar_por_texto_organismo(df_geo, busca_organo)
                if busca_organo.strip() else df_geo
            )
            organos = sorted(df_geo_organos["Organo"].dropna().unique().tolist())
            if busca_organo.strip():
                st.caption(
                    f"{len(organos):,} organismo(s) encontrados para "
                    f"'{busca_organo.strip()}'."
                )
            default_organos = []
            if busca_organo.strip() and len(organos) <= 50:
                default_organos = organos
            elif len(organos) <= 50:
                default_organos = organos[: min(3, len(organos))]
            organos_sel = st.multiselect(
                "Organismos a auditar",
                options=organos,
                default=default_organos,
                placeholder="Escribe para filtrar…",
            )
        with col2:
            años = sorted(df_geo_organos["Año_Fiscal"].dropna().unique(), reverse=True)
            años_sel = st.multiselect("Años fiscales", años, default=años)

        col_busc1, col_busc2, col_busc3 = st.columns([2, 2, 2])
        with col_busc1:
            busca_adj = st.text_input(
                "🔎 Buscar adjudicatario (contiene)",
                value="",
                placeholder="Ej.: GRÁFICAS, S.L.",
            )
        with col_busc2:
            busca_concepto = st.text_input(
                "🔎 Buscar en el concepto",
                value="",
                placeholder="Ej.: cartelería, festejos, mantenimiento…",
            )
        with col_busc3:
            tipo_contrato_sel = st.multiselect(
                "Tipo de contrato",
                options=sorted(df_geo["Tipo_Contrato"].dropna().unique().tolist())
                if "Tipo_Contrato" in df_geo.columns else [],
                placeholder="Servicios y obras",
            )

        rango_importes = st.slider(
            "Rango de importe (€, sin IVA)",
            min_value=0.0,
            max_value=float(LIMITE_OBRAS),
            value=(0.0, float(LIMITE_OBRAS)),
            step=500.0,
            help=(
                "Por defecto cubre todo el rango legal del contrato menor. "
                "Sube el mínimo para concentrarte en importes pegados al límite."
            ),
        )

        if organos_sel:
            df_input = df_geo_organos[
                df_geo_organos["Organo"].isin(organos_sel)
                & df_geo_organos["Año_Fiscal"].isin(años_sel)
            ].copy()

            if busca_adj.strip():
                df_input = df_input[df_input["Adjudicatario"].astype(str).str.contains(
                    busca_adj.strip(), case=False, na=False, regex=False)]
            if busca_concepto.strip() and "Concepto" in df_input.columns:
                df_input = df_input[df_input["Concepto"].astype(str).str.contains(
                    busca_concepto.strip(), case=False, na=False, regex=False)]
            if tipo_contrato_sel and "Tipo_Contrato" in df_input.columns:
                df_input = df_input[df_input["Tipo_Contrato"].isin(tipo_contrato_sel)]
            if "Importe_euros" in df_input.columns:
                lo, hi = rango_importes
                df_input = df_input[df_input["Importe_euros"].between(lo, hi)]

            st.success(f"✅ {len(df_input):,} contratos cargados para auditoría.")
            columnas_tabla = [
                c for c in [
                    "Fecha", "CCAA", "Provincia", "Municipio", "Tipo_Entidad", "Organo",
                    "Año_Fiscal", "Tipo_Contrato", "CPV", "Concepto",
                    "Adjudicatario", "Importe_euros", "Link_Expediente",
                ] if c in df_input.columns
            ]
            column_config = {
                "Importe_euros": st.column_config.NumberColumn("💰 Importe", format="%.2f €"),
                "Año_Fiscal": st.column_config.NumberColumn("📅 Año", format="%d"),
            }
            if "Link_Expediente" in df_input.columns:
                column_config["Link_Expediente"] = st.column_config.LinkColumn(
                    "🔗 Expediente PLACSP",
                    display_text="Abrir en PLACSP",
                )
            st.dataframe(
                df_input[columnas_tabla],
                width="stretch",
                column_config=column_config,
            )
            st.download_button(
                "⬇️ Descargar contratos filtrados (CSV)",
                df_input[columnas_tabla].to_csv(index=False).encode("utf-8-sig"),
                "contratos_filtrados.csv",
                "text/csv",
            )

            # --- Radar ---
            st.markdown("---")
            st.header("🦊 Radar de fraccionamiento sistemático")
            radar = ejecutar_radar(df_input, min_contratos=min_contratos)
            if radar.empty:
                st.info("No hay datos suficientes para el radar.")
            else:
                _mostrar_resumen_radar(radar)
                alertas = radar[radar["Es_Alerta"]]
                if alertas.empty:
                    st.success("✅ Sin acumulaciones sospechosas.")
                    tabla_radar = radar
                else:
                    st.error(f"🚨 {len(alertas)} casos posibles de fraccionamiento.")
                    tabla_radar = alertas if mostrar_solo_alertas else radar
                st.caption(
                    "Filtro activo: solo casos con alerta. Desactiva el "
                    "checkbox de la barra lateral para ver también los "
                    "grupos sin alerta dentro de esta misma tabla."
                    if mostrar_solo_alertas else
                    f"Mostrando los {len(radar)} grupos analizados (con y sin alerta)."
                )
                st.dataframe(
                    tabla_radar[_columnas_radar_visibles(tabla_radar)],
                    width="stretch",
                    column_config={
                        "Porcentaje_Limite_Formateado": st.column_config.TextColumn(
                            "Acumulado vs. límite",
                            help=(
                                "Porcentaje que suma el grupo completo de contratos "
                                "respecto al límite legal. No indica que un contrato "
                                "individual haya superado el límite."
                            ),
                        ),
                        "Limite_Legal": st.column_config.TextColumn("Límite legal del grupo"),
                        "Total_Formateado": st.column_config.TextColumn("Total acumulado"),
                    },
                )
                if not alertas.empty:
                    st.download_button(
                        "⬇️ Descargar alertas (CSV)",
                        alertas.to_csv(index=False).encode("utf-8-sig"),
                        "alertas_fraccionamiento.csv",
                        "text/csv",
                    )
                    _mostrar_ficha_caso(
                        radar,
                        df_input,
                        "Caso a revisar",
                    )

                # --- Visualizaciones interactivas + informes y descargas ---
                titulo_informe = "Informe PLACSP · " + ", ".join(organos_sel[:3])
                if len(organos_sel) > 3:
                    titulo_informe += f" (+{len(organos_sel) - 3})"
                _mostrar_visualizaciones_forenses(radar, df_input, titulo_informe)
        else:
            st.info(
                "Selecciona uno o varios organismos en el campo «Organismos a auditar» "
                "para generar el radar y las visualizaciones."
            )


# =============================================================================
# RUTA 2 — TRIBUNAL DE CUENTAS (CSV/.accdb)
# =============================================================================
elif fuente.startswith("🏛️"):
    st.subheader("Tribunal de Cuentas — Liquidaciones de entes locales")
    st.info(
        "Cruza `tb_economica` (millones de partidas) con `tb_inventario` "
        "(catálogo de entidades) usando DuckDB. No carga los CSV en RAM."
    )
    st.caption(
        "Salida de este flujo: ranking de entidades, tabla descargable, detalle "
        "por entidad y gráficos de ranking. El radar de fraccionamiento y el "
        "informes y descargas completos se activan cuando hay contratos individuales "
        "con adjudicatario, importe y año fiscal (PLACSP o CSV/Excel individual)."
    )

    tab_csv, tab_accdb, tab_descarga = st.tabs([
        "📊 Ranking presupuestario (CSV)",
        "🔧 Convertir .accdb",
        "⬇️ Descargar fuente",
    ])

    # --- Consulta sobre los CSV ---
    with tab_csv:
        st.markdown("#### Paso a paso para ver el ranking")
        st.markdown(
            "1. Consigue `tb_economica.csv` y `tb_inventario.csv`: puedes "
            "cargarlos si ya los tienes, descargarlos en **⬇️ Descargar fuente** "
            "o generarlos desde un `.accdb` en **🔧 Convertir .accdb**.\n"
            "2. Selecciona los dos CSV o pega sus rutas locales.\n"
            "3. Elige el capítulo presupuestario; para bienes y servicios usa "
            "**2 — Gastos en bienes y servicios**.\n"
            "4. Pulsa **📈 Calcular ranking** para ver la tabla, el gráfico y "
            "el CSV descargable."
        )
        modo_csv = st.radio(
            "Cómo quieres cargar los CSV del Tribunal",
            ["Seleccionar archivos CSV", "Usar rutas locales"],
            horizontal=True,
        )
        ruta_econ = st.session_state.get("tribunal_ruta_econ", "")
        ruta_inv = st.session_state.get("tribunal_ruta_inv", "")
        if modo_csv == "Seleccionar archivos CSV":
            carpeta_csv_subidos = st.text_input(
                "Carpeta de trabajo para los CSV seleccionados",
                value=st.session_state.get("tribunal_upload_dir", str(UPLOADS_DIR / "tribunal")),
            )
            _crear_carpeta_boton(carpeta_csv_subidos, key="crear_upload_tribunal_csv")
            col1, col2 = st.columns(2)
            with col1:
                archivo_econ = st.file_uploader(
                    "Selecciona tb_economica.csv",
                    type=["csv"],
                    key="upload_tb_economica",
                )
            with col2:
                archivo_inv = st.file_uploader(
                    "Selecciona tb_inventario.csv",
                    type=["csv"],
                    key="upload_tb_inventario",
                )
            if archivo_econ is not None:
                ruta_econ = str(_guardar_archivo_subido(archivo_econ, carpeta_csv_subidos))
                st.session_state["tribunal_ruta_econ"] = ruta_econ
            if archivo_inv is not None:
                ruta_inv = str(_guardar_archivo_subido(archivo_inv, carpeta_csv_subidos))
                st.session_state["tribunal_ruta_inv"] = ruta_inv
            st.session_state["tribunal_upload_dir"] = carpeta_csv_subidos
            if ruta_econ or ruta_inv:
                st.caption("Archivos activos:\n" + "\n".join(p for p in [ruta_econ, ruta_inv] if p))
        else:
            col1, col2 = st.columns(2)
            with col1:
                ruta_econ = st.text_input(
                    "Ruta de tb_economica.csv",
                    value=ruta_econ,
                    placeholder="/ruta/a/tb_economica.csv",
                )
            with col2:
                ruta_inv = st.text_input(
                    "Ruta de tb_inventario.csv",
                    value=ruta_inv,
                    placeholder="/ruta/a/tb_inventario.csv",
                )

        capitulo = st.selectbox(
            "Capítulo presupuestario de gasto",
            options=[1, 2, 3, 4, 6, 7, 8, 9],
            index=1,
            format_func=lambda c: {
                1: "1 — Personal",
                2: "2 — Gastos en bienes y servicios",
                3: "3 — Gastos financieros",
                4: "4 — Transferencias corrientes",
                6: "6 — Inversiones reales",
                7: "7 — Transferencias de capital",
                8: "8 — Activos financieros",
                9: "9 — Pasivos financieros",
            }[c],
        )

        ambito = st.radio(
            "Ámbito territorial",
            ["🇪🇸 Toda España", "🟢 Solo Galicia", "✏️ Provincias personalizadas"],
            horizontal=True,
        )
        if ambito == "🟢 Solo Galicia":
            provincias = PROVINCIAS_GALICIA
        elif ambito == "✏️ Provincias personalizadas":
            provs_str = st.text_input(
                "Códigos INE de provincia separados por coma (ej: 28, 08)",
                value="28",
            )
            provincias = tuple(p.strip() for p in provs_str.split(",") if p.strip()) or None
        else:
            provincias = None

        top = st.slider("Top N entidades", 10, 1000, 100)

        if st.button("📈 Calcular ranking"):
            if not (Path(ruta_econ).exists() and Path(ruta_inv).exists()):
                st.error("❌ Comprueba las rutas de ambos CSV.")
            else:
                with st.spinner("DuckDB consultando los CSV…"):
                    key = ",".join(provincias) if provincias else ""
                    df = _cached_ranking(ruta_econ, ruta_inv, capitulo, key)
                if df.empty:
                    st.warning("Sin resultados para esos filtros.")
                else:
                    df_top = df.head(top)
                    st.success(
                        f"✅ {len(df):,} entidades. Total ranking mostrado: "
                        f"{formatear_euros(df_top['total_gastado'].sum())}"
                    )
                    st.dataframe(
                        df_top,
                        width="stretch",
                        column_config={
                            "total_gastado": st.column_config.NumberColumn(
                                "💰 Total gastado", format="%.2f €"
                            ),
                            "num_partidas": st.column_config.NumberColumn("Nº partidas"),
                        },
                    )
                    st.bar_chart(
                        df_top.head(20).set_index("entidad")["total_gastado"],
                        color="#1f77b4",
                    )
                    with st.expander("📊 Visualización interactiva del ranking", expanded=False):
                        _plotly(grafico_ranking_entidades(df_top, top=20))
                    st.download_button(
                        "⬇️ Descargar ranking (CSV)",
                        df.to_csv(index=False).encode("utf-8-sig"),
                        f"ranking_capitulo_{capitulo}.csv",
                        "text/csv",
                    )

        with st.expander("🔎 Ver detalle de una entidad concreta"):
            entidad = st.text_input(
                "Buscar entidad (usa % como comodín)",
                value="%santiago%",
                help=(
                    "Búsqueda LIKE de SQL: % = cualquier secuencia de caracteres. "
                    "Ejemplos: '%santiago%' encuentra todo lo que contenga 'santiago'; "
                    "'concello de %' empieza por esa cadena. Sin % es coincidencia exacta."
                ),
            )
            if st.button("Buscar partidas"):
                if Path(ruta_econ).exists() and Path(ruta_inv).exists():
                    df_det = detalle_partidas_entidad(
                        ruta_econ, ruta_inv, entidad, capitulo=capitulo
                    )
                    st.dataframe(df_det, width="stretch")

    # --- Conversor .accdb ---
    with tab_accdb:
        st.markdown(
            "Si tienes el archivo original `Liquidaciones2024.accdb`, esta "
            "herramienta lo convierte a CSV automáticamente usando "
            "[`mdbtools`](https://github.com/mdbtools/mdbtools). Es una "
            "dependencia opcional del sistema operativo: no se instala con "
            "`requirements.txt` porque no es una librería Python."
        )
        if not mdbtools_disponible():
            sistema = platform.system()
            instrucciones = {
                "Darwin": (
                    "1. Instala Homebrew si todavía no está instalado: "
                    "https://brew.sh/\n"
                    "2. Abre Terminal, pega este comando y pulsa Enter:\n"
                    "```bash\nbrew install mdbtools\n```\n"
                    "3. Vuelve a abrir la app o recarga esta página."
                ),
                "Linux": (
                    "En Debian/Ubuntu, abre Terminal y ejecuta:\n"
                    "```bash\nsudo apt update\nsudo apt install mdbtools\n```\n"
                    "En Fedora:\n"
                    "```bash\nsudo dnf install mdbtools\n```\n"
                    "Después vuelve a abrir la app o recarga esta página."
                ),
                "Windows": (
                    "`mdbtools` no está disponible de forma práctica en Windows. "
                    "Abre el `.accdb` en Microsoft Access o LibreOffice Base y "
                    "exporta las tablas `tb_economica` y `tb_inventario` como CSV. "
                    "Después carga esos CSV en la pestaña *Consultar CSV*."
                ),
            }.get(sistema, "Instala `mdbtools` con tu gestor de paquetes.")
            st.error(
                "❌ No se detecta `mdbtools` en este sistema "
                f"({sistema}). La conversión directa de `.accdb` está bloqueada "
                "hasta instalarlo."
            )
            st.markdown(instrucciones)
            st.info(
                "Alternativa sin instalar nada: consigue los CSV ya exportados "
                "(`tb_economica.csv` y `tb_inventario.csv`) y usa la pestaña "
                "📊 Consultar CSV. El análisis final es el mismo."
            )
        else:
            rutas_mdb = [shutil.which("mdb-tables"), shutil.which("mdb-export")]
            st.success(
                "✅ mdbtools detectado en el sistema: "
                + " · ".join(r for r in rutas_mdb if r)
            )
            modo_accdb = st.radio(
                "Cómo quieres indicar el archivo Access",
                ["Seleccionar .accdb", "Usar ruta local"],
                horizontal=True,
            )
            ruta_accdb = st.session_state.get("tribunal_ruta_accdb", "")
            carpeta_accdb_subidos = st.session_state.get(
                "tribunal_accdb_upload_dir",
                str(UPLOADS_DIR / "tribunal"),
            )
            if modo_accdb == "Seleccionar .accdb":
                carpeta_accdb_subidos = st.text_input(
                    "Carpeta de trabajo para el .accdb seleccionado",
                    value=carpeta_accdb_subidos,
                )
                _crear_carpeta_boton(carpeta_accdb_subidos, key="crear_upload_accdb")
                archivo_accdb = st.file_uploader(
                    "Selecciona el archivo .accdb o .mdb",
                    type=["accdb", "mdb"],
                    key="upload_accdb",
                    help="Si el archivo supera el límite de subida del navegador, usa la opción 'Usar ruta local'.",
                )
                if archivo_accdb is not None:
                    ruta_accdb = str(_guardar_archivo_subido(archivo_accdb, carpeta_accdb_subidos))
                    st.session_state["tribunal_ruta_accdb"] = ruta_accdb
                    st.session_state["tribunal_accdb_upload_dir"] = carpeta_accdb_subidos
                    st.caption(f"Archivo activo: {ruta_accdb}")
            else:
                ruta_accdb = st.text_input(
                    ".accdb a convertir",
                    value=ruta_accdb,
                    placeholder="/ruta/a/Liquidaciones2024.accdb",
                )
            destino = st.text_input(
                "Carpeta de salida",
                value=st.session_state.get("tribunal_accdb_destino", str(DEFAULT_TRIBUNAL_DIR / "accdb_export")),
            )
            _crear_carpeta_boton(destino, key="crear_destino_accdb")
            if st.button("🔧 Convertir todas las tablas"):
                try:
                    if not ruta_accdb or not Path(ruta_accdb).exists():
                        raise FileNotFoundError("Indica una ruta válida al archivo .accdb/.mdb.")
                    estado = st.empty()
                    barra_accdb = st.progress(0.0, text="Preparando conversión…")
                    inicio_conversion = time.monotonic()

                    def _duracion(segundos: float) -> str:
                        segundos = max(0, int(segundos))
                        minutos, resto = divmod(segundos, 60)
                        if minutos:
                            return f"{minutos} min {resto:02d} s"
                        return f"{resto} s"

                    def _progreso_accdb(i, total, nombre_tabla, estado_tabla="inicio"):
                        # Cada `mdb-export` puede tardar segundos en tablas grandes;
                        # avisamos antes de procesar la tabla para que el usuario
                        # vea que la app sigue trabajando.
                        completadas = i - 1 if estado_tabla == "inicio" else i
                        proporcion = min(completadas / max(total, 1), 1.0)
                        transcurrido = time.monotonic() - inicio_conversion
                        if completadas > 0 and completadas < total:
                            restante = transcurrido / completadas * (total - completadas)
                            eta = f" · faltan aprox. {_duracion(restante)}"
                        elif completadas >= total:
                            eta = f" · tiempo total {_duracion(transcurrido)}"
                        else:
                            eta = " · calculando tiempo restante"
                        accion = "Exportando" if estado_tabla == "inicio" else "Completada"
                        barra_accdb.progress(
                            proporcion,
                            text=f"{accion} tabla {i}/{total}: {nombre_tabla}{eta}",
                        )
                        estado.caption(
                            f"Progreso: {completadas}/{total} tablas completadas{eta}."
                        )

                    creados = exportar_accdb_a_csv(
                        ruta_accdb, destino, progreso=_progreso_accdb
                    )
                    barra_accdb.progress(1.0, text="✅ Conversión completada")
                    estado.empty()
                    st.session_state["tribunal_accdb_destino"] = destino
                    st.success(f"✅ {len(creados)} CSV creados en {destino}")
                    st.info(
                        "Siguiente paso: ve a la pestaña **📊 Ranking presupuestario "
                        "(CSV)** y selecciona la carpeta de salida que acabas de "
                        "generar para ver el ranking."
                    )
                    st.code("\n".join(str(c) for c in creados))
                except Exception as e:
                    st.error(f"❌ {e}")

    # --- Descarga directa de fuente oficial ---
    with tab_descarga:
        st.markdown(
            "Usa esta pestaña cuando el portal oficial ofrezca una URL directa "
            "a un `.accdb`, `.zip`, `.csv` o `.xlsx`. La descarga queda "
            "registrada con manifiesto para poder justificar la procedencia."
        )
        url_fuente = st.text_input("URL directa oficial", value="")
        col_f1, col_f2 = st.columns([2, 1])
        with col_f1:
            destino_fuente = st.text_input("Carpeta destino", value=str(DEFAULT_TRIBUNAL_DIR))
            _crear_carpeta_boton(destino_fuente, key="crear_destino_fuente")
        with col_f2:
            nombre_fuente = st.text_input("Nombre archivo (opcional)", value="")
        col_f3, col_f4 = st.columns(2)
        with col_f3:
            sobrescribir_fuente = st.checkbox("Sobrescribir archivo existente", value=False)
        with col_f4:
            descomprimir_zip = st.checkbox("Descomprimir si es ZIP", value=True)

        if st.button("⬇️ Descargar archivo oficial"):
            if not url_fuente.strip():
                st.error("❌ Pega una URL directa de descarga.")
            else:
                with st.spinner("Descargando fuente oficial…"):
                    resultado = descargar_url_directa(
                        url_fuente,
                        destino_fuente,
                        nombre_archivo=nombre_fuente or None,
                        sobrescribir=sobrescribir_fuente,
                        descomprimir_zip=descomprimir_zip,
                    )
                if resultado.errores:
                    st.error("❌ " + "\n".join(resultado.errores[:5]))
                else:
                    st.success(
                        f"✅ {len(resultado.descargados)} archivo(s) descargado(s), "
                        f"{len(resultado.omitidos)} omitido(s), "
                        f"{len(resultado.extraidos)} extraído(s)."
                    )
                    rutas = resultado.descargados + resultado.omitidos + resultado.extraidos[:20]
                    if rutas:
                        st.code("\n".join(str(r) for r in rutas))
                    if resultado.manifest_path:
                        st.caption(f"Manifiesto: {resultado.manifest_path}")


# =============================================================================
# RUTA 4 — GUÍA DE USO INTEGRADA
# =============================================================================
elif fuente.startswith("❓"):
    st.subheader("Guía de uso de la herramienta")
    guia_path = Path(__file__).parent / "docs" / "GUIA_USO.md"
    if not guia_path.exists():
        st.warning(
            "No se encontró `docs/GUIA_USO.md`. Comprueba que la guía no se "
            "haya borrado del proyecto."
        )
    else:
        contenido = guia_path.read_text(encoding="utf-8")
        # Partimos por encabezados H2 (## Sección) para construir un
        # índice clicable sin depender de los anclajes #sección del
        # markdown nativo (que cambian según la versión de Streamlit).
        bloques = re.split(r"^## ", contenido, flags=re.MULTILINE)
        cabecera = bloques[0]
        secciones: list[tuple[str, str]] = []
        for bloque in bloques[1:]:
            titulo, _, cuerpo = bloque.partition("\n")
            secciones.append((titulo.strip(), "## " + bloque))

        st.markdown(cabecera)
        if secciones:
            opciones = ["📑 Índice completo"] + [t for t, _ in secciones]
            seleccion = st.radio(
                "Navegar por la guía",
                opciones,
                horizontal=False,
                label_visibility="collapsed",
            )
            if seleccion == "📑 Índice completo":
                st.markdown(
                    "**Haz clic en una sección de la lista de la izquierda "
                    "para abrirla.** A continuación tienes la guía completa "
                    "para imprimir o leer en línea:"
                )
                for _, cuerpo in secciones:
                    st.markdown(cuerpo)
            else:
                for titulo, cuerpo in secciones:
                    if titulo == seleccion:
                        st.markdown(cuerpo)
                        break
        else:
            st.markdown(contenido)
    st.divider()
    st.caption(
        "Sistema detectado: "
        f"**{platform.system()} {platform.release()}** · Python {platform.python_version()}"
    )


# =============================================================================
# RUTA 3 — ARCHIVO INDIVIDUAL (PDF / CSV / Excel)
# =============================================================================
else:
    st.subheader("Análisis forense de archivo suelto")

    st.info(
        "💡 **Mejor con CSV o Excel.** El análisis de PDF detecta patrones "
        "(importes, NIFs, fechas, palabras clave) sobre texto extraído, pero "
        "**no reconstruye tablas estructuradas**: en PDFs escaneados, con "
        "columnas complejas o sin capa de texto los resultados pueden ser "
        "parciales. Si dispones del mismo informe en CSV/Excel, úsalo: el "
        "auditor podrá entonces aplicar el radar de fraccionamiento completo."
    )

    archivo = st.file_uploader(
        "Sube un PDF, CSV o Excel",
        type=["pdf", "csv", "xlsx", "xls"],
    )

    col1, col2 = st.columns(2)
    with col1:
        limite_paginas = st.slider("Máx. páginas a leer (PDF)", 10, 500, 50)
    with col2:
        filas_saltar = st.number_input("Filas iniciales a ignorar (CSV/Excel)", 0, 20, 0)

    filtros_disp = st.multiselect(
        "Patrones a buscar",
        options=list(PATRONES.keys()),
        default=["Importes (€)"],
    )
    filtros_activos = {k: (k in filtros_disp) for k in PATRONES}

    if archivo:
        nombre_ext = archivo.name.lower()
        df_resultados = pd.DataFrame()
        df_input = pd.DataFrame()

        # --- PDF ---
        if nombre_ext.endswith(".pdf"):
            try:
                with pdfplumber.open(archivo) as pdf:
                    total = len(pdf.pages)
                    leer = min(total, limite_paginas)
                    barra = st.progress(0.0)
                    textos: dict[int, str] = {}
                    for i in range(leer):
                        t = pdf.pages[i].extract_text()
                        if t:
                            textos[i + 1] = t
                        barra.progress((i + 1) / leer)
                st.success(f"✅ Leídas {leer} de {total} páginas.")
                df_resultados = analizar_texto_por_pagina(textos, filtros_activos)
            except Exception as e:
                st.error(f"❌ Error al procesar el PDF: {e}")

        # --- CSV / Excel ---
        elif nombre_ext.endswith((".csv", ".xlsx", ".xls")):
            try:
                if nombre_ext.endswith(".csv"):
                    df_input = pd.read_csv(archivo, sep=None, engine="python", skiprows=filas_saltar)
                else:
                    df_input = pd.read_excel(archivo, skiprows=filas_saltar)
                st.success(f"✅ {len(df_input):,} filas, {len(df_input.columns)} columnas.")

                pal_emp = ["adjudicatario", "empresa", "contratista", "tercero", "nombre", "proveedor"]
                pal_din = ["importe", "prezo", "precio", "total", "adxudicacion", "orzamento", "presupuesto"]
                pal_fecha = ["fecha", "date", "data", "fiscal"]
                pal_organo = ["organo", "órgano", "entidad", "ayuntamiento", "concello", "administracion"]
                pal_tipo = ["tipo", "clase", "categoria", "categoría"]
                cols_emp = [c for c in df_input.columns if any(p in str(c).lower() for p in pal_emp)]
                cols_din = [c for c in df_input.columns if any(p in str(c).lower() for p in pal_din)]
                cols_fecha = [c for c in df_input.columns if any(p in str(c).lower() for p in pal_fecha)]
                cols_organo = [c for c in df_input.columns if any(p in str(c).lower() for p in pal_organo)]
                cols_tipo = [c for c in df_input.columns if any(p in str(c).lower() for p in pal_tipo)]

                # Construye df_resultados para escáner
                filas: list[dict] = []
                for col in cols_din:
                    serie_num = df_input[col].apply(limpiar_dinero)
                    for idx, val in df_input.loc[serie_num.notna(), col].items():
                        ctx = " | ".join(df_input.loc[idx].astype(str).tolist())[:200]
                        for nombre, activo in filtros_activos.items():
                            if not activo:
                                continue
                            for m in re.finditer(PATRONES[nombre], f"{val} €"):
                                filas.append({
                                    "Localizacion": f"Fila {idx + 2}",
                                    "Tipo": nombre,
                                    "Valor": m.group(),
                                    "Contexto": ctx,
                                })
                df_resultados = pd.DataFrame(filas)

                # Normaliza para el radar
                if cols_emp and cols_din:
                    df_input = df_input.rename(columns={cols_emp[0]: "Adjudicatario", cols_din[0]: "Importe_euros"})
                    df_input["Importe_euros"] = df_input["Importe_euros"].apply(limpiar_dinero)
                    df_input["_Adjudicatario_Radar"] = df_input["Adjudicatario"].where(
                        df_input["Adjudicatario"].notna()
                        & (df_input["Adjudicatario"].astype(str).str.strip() != "")
                    )
                    df_input["Tipo_Contrato"] = (
                        df_input[cols_tipo[0]].astype(str)
                        if cols_tipo and cols_tipo[0] in df_input.columns
                        else "Servicios"
                    )
                    df_input["Organo"] = (
                        df_input[cols_organo[0]].astype(str)
                        if cols_organo and cols_organo[0] in df_input.columns
                        else "Archivo local"
                    )
                    if "Provincia" not in df_input.columns or "CCAA" not in df_input.columns:
                        geografia = df_input["Organo"].apply(inferir_geografia)
                        if "Provincia" not in df_input.columns:
                            df_input["Provincia"] = geografia.apply(lambda valor: valor[0])
                        if "CCAA" not in df_input.columns:
                            df_input["CCAA"] = geografia.apply(lambda valor: valor[1])
                    if "Municipio" not in df_input.columns:
                        df_input["Municipio"] = df_input["Organo"].apply(inferir_municipio)
                    if cols_fecha and cols_fecha[0] in df_input.columns:
                        fechas = parsear_fechas_mixtas(df_input[cols_fecha[0]])
                        df_input["Fecha"] = fechas
                        df_input["Año_Fiscal"] = fechas.dt.year.astype("Int64")
                    else:
                        df_input["Año_Fiscal"] = pd.NA
            except Exception as e:
                st.error(f"❌ Error al leer la tabla: {e}")

        # --- Resultados del escáner ---
        if not df_resultados.empty:
            st.markdown("---")
            st.header("🔍 Escáner de patrones")
            df_b = detectar_banderas(df_resultados)
            alertas = df_b[df_b["Bandera"] != "OK"] if "Bandera" in df_b.columns else pd.DataFrame()
            if not alertas.empty:
                st.warning(f"⚠️ {len(alertas)} importes con banderas rojas.")
                st.dataframe(
                    alertas.style.apply(pintar_filas_banderas, axis=1),
                    width="stretch",
                )
            else:
                st.success("✅ Ningún importe roza los límites.")
            with st.expander("Ver todos los hallazgos"):
                st.dataframe(df_b, width="stretch")

        # --- Radar para CSV/Excel con adjudicatario, importe y fecha ---
        columnas_radar = {"_Adjudicatario_Radar", "Importe_euros", "Año_Fiscal"}
        if not df_input.empty and columnas_radar.issubset(df_input.columns):
            radar_archivo = ejecutar_radar(df_input, min_contratos=min_contratos)
            if radar_archivo.empty:
                if df_input["Año_Fiscal"].isna().all():
                    st.info("El radar necesita una columna de fecha o año fiscal para agrupar contratos.")
            else:
                st.markdown("---")
                st.header("🦊 Radar del archivo cargado")
                _mostrar_resumen_radar(radar_archivo)
                alertas_archivo = radar_archivo[radar_archivo["Es_Alerta"]]
                if alertas_archivo.empty:
                    st.success("✅ Sin acumulaciones sospechosas en este archivo.")
                    tabla_radar = radar_archivo
                else:
                    st.warning(f"⚠️ {len(alertas_archivo)} grupos con señales de fraccionamiento.")
                    tabla_radar = alertas_archivo if mostrar_solo_alertas else radar_archivo
                st.dataframe(
                    tabla_radar[_columnas_radar_visibles(tabla_radar)],
                    width="stretch",
                )
                _mostrar_ficha_caso(
                    radar_archivo,
                    df_input,
                    "Caso del archivo a revisar",
                )
                _mostrar_visualizaciones_forenses(
                    radar_archivo,
                    df_input,
                    f"Informe archivo · {archivo.name}",
                )


# =============================================================================
# PIE
# =============================================================================
st.markdown("---")
st.caption(
    f"Límite legal contrato menor: servicios {formatear_euros(LIMITE_SERVICIOS)} · "
    f"obras {formatear_euros(LIMITE_OBRAS)} · "
    "Datos: [PLACSP](https://contrataciondelestado.es) · "
    "[Tribunal de Cuentas](https://www.rendiciondecuentas.es)"
)
st.markdown(
    f"""
    <div style="
        margin-top: 1.25rem;
        padding: 1.1rem 1.4rem;
        border: 1px solid #e2e8f0;
        border-left: 4px solid #2b6cb0;
        border-radius: .35rem;
        background: linear-gradient(180deg, #f7fafc 0%, #edf2f7 100%);
        font-size: .92rem;
        line-height: 1.55;
        color: #1a202c;
    ">
      <div style="font-size: .78rem; letter-spacing: .08em; text-transform: uppercase; color: #4a5568; margin-bottom: .35rem;">
                Autoría · Institución · Proyectos · Licencia
      </div>
      <div><strong>Autores:</strong> {AUTHORS_LINE_HTML}.</div>
      <div><strong>Institución:</strong> Universidade de Santiago de Compostela.</div>
            <div><strong>Esta aplicación es parte de los proyectos de I+D+i:</strong> {RESEARCH_PROJECTS_HTML}</div>
      <div><strong>Licencia:</strong> código libre <a href=\"{MIT_LICENSE_URL}\" target=\"_blank\">MIT</a>.</div>
    </div>
    """,
    unsafe_allow_html=True,
)
