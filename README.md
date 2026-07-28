# Auditor de Contratos Públicos

> Herramienta local-first para que periodistas, estudiantes e investigadores puedan explorar contratación pública española, detectar indicios estadísticos de fraccionamiento de contratos menores y generar informes reutilizables sin enviar datos a servicios externos.

[![tests](https://img.shields.io/badge/tests-57%20passed-brightgreen)](tests/)
[![python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![license](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![platform](https://img.shields.io/badge/macOS%20%7C%20Linux%20%7C%20Windows-supported-lightgrey)](#compatibilidad)
[![DOI](https://zenodo.org/badge/1264760836.svg)](https://doi.org/10.5281/zenodo.21652746)

## Qué permite hacer

- Descargar y procesar contratos menores publicados en la Plataforma de Contratación del Sector Público (PLACSP).
- Comprobar cobertura municipal en PLACSP para distinguir entre contratos ubicados en un municipio y ayuntamientos que aparecen como órgano contratante.
- Consultar liquidaciones presupuestarias del Tribunal de Cuentas mediante DuckDB, sin cargar millones de filas en memoria.
- Convertir `.accdb` del Tribunal de Cuentas de forma acotada, con tiempo máximo por tabla y limpieza de CSV parcial si `mdbtools` falla.
- Detectar agrupaciones de contratos por adjudicatario, órgano, tipo de contrato y año fiscal.
- Visualizar relaciones, importes, series temporales, concentración de gasto y distribución territorial.
- Exportar informes HTML/PDF, tablas CSV y gráficos PNG para redacción, docencia o revisión académica.

La herramienta no prueba irregularidades por sí sola. Sus alertas son indicios estadísticos que deben contrastarse con expedientes, fuentes oficiales y criterio periodístico.

## Instalación rápida

Requisito previo: Python 3.10 o superior.

| Sistema | Lanzador recomendado | Notas |
| --- | --- | --- |
| macOS | `launch_macos.command` | La primera vez: clic derecho -> Abrir |
| Linux | `launch_linux.sh` | Si hace falta: `chmod +x launch_linux.sh` |
| Windows | `launch_windows.bat` | Doble clic; no cierres la ventana de ejecución |

El lanzador crea `.venv/`, instala dependencias y abre Streamlit en el primer puerto libre entre `8501` y `8520`. La primera ejecución puede tardar unos minutos; las siguientes son más rápidas.

## Ejecución manual

```bash
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

La conversión directa de archivos `.accdb` del Tribunal de Cuentas requiere `mdbtools`, una dependencia del sistema operativo que no se instala con `pip`:

```bash
brew install mdbtools                 # macOS
sudo apt install mdbtools             # Debian/Ubuntu
```

En Windows se recomienda abrir el `.accdb` con Microsoft Access o LibreOffice Base y exportar `tb_economica` y `tb_inventario` a CSV.

## Fuentes de datos

| Fuente | Uso en la app | Salidas principales |
| --- | --- | --- |
| PLACSP | Contratos menores `.atom` descargados o cargados localmente | Radar, red de relaciones, mapas, informes HTML/PDF, CSV y PNG |
| Tribunal de Cuentas | CSV o `.accdb` convertido a CSV | Rankings presupuestarios, detalle por entidad y descarga CSV |

Las descargas y subidas locales se guardan en `data/`, ignorado por Git. Cada descarga oficial genera un manifiesto JSON con fecha, URL y archivos creados para mantener trazabilidad metodológica.

## Visualizaciones e informes

Cuando hay datos contractuales suficientes, la aplicación ofrece:

- Semáforo de riesgo y ficha de caso prioritario.
- Treemap de adjudicatarios y dispersión de riesgo.
- Serie temporal, distribución de importes y timeline de contratos.
- Concentración de gasto tipo Pareto.
- Red dinámica órgano-adjudicatario en la interfaz.
- Ranking estático de relaciones principales para HTML/PNG.
- Mapa y ranking territorial por comunidad, provincia o municipio cuando el dato existe.
- Informe HTML autoportante, informe PDF, ZIP de tablas CSV y ZIP de gráficos PNG.

El informe HTML conserva gráficos Plotly interactivos. El PDF prioriza texto y tablas legibles para impresión o circulación en redacción.

## Privacidad y seguridad

- La aplicación se ejecuta en local y no sube datos a la nube.
- No automatiza formularios autenticados ni sesiones privadas.
- No versiona datos descargados, cachés, bases voluminosas, entornos virtuales ni credenciales.
- No debe exponerse Streamlit directamente a internet sin autenticación o proxy seguro.

Los directorios `.venv/`, `.cache/`, `data/`, `exports/`, `reports/` y los archivos `.accdb`, `.parquet`, `.env` y similares están excluidos en [.gitignore](.gitignore). Para normas de contribución y preparación del repositorio, consulta [CONTRIBUTING.md](CONTRIBUTING.md).

## Compatibilidad

| Componente | macOS | Linux | Windows |
| --- | --- | --- | --- |
| Streamlit, pandas, DuckDB, Plotly, PDF | Sí | Sí | Sí |
| Descarga PLACSP y URL directa | Sí | Sí | Sí |
| Conversión `.accdb` con `mdbtools` | Sí | Sí | No práctico; usar Access/LibreOffice |

## Estructura del repositorio

```text
TFG/
├── app.py                  # Interfaz Streamlit
├── core/                   # Lógica de análisis, fuentes, informes y visualización
├── tests/                  # Suite pytest
├── docs/                   # Guía de uso y arquitectura
├── packaging/              # Empaquetado binario opcional con PyInstaller
├── .github/workflows/      # CI y release opcional
├── launch_macos.command    # Lanzador macOS
├── launch_linux.sh         # Lanzador Linux
├── launch_windows.bat      # Lanzador Windows
├── requirements.txt        # Dependencias de ejecución
└── requirements-dev.txt    # Dependencias de desarrollo
```

La guía completa para usuarios está en [docs/GUIA_USO.md](docs/GUIA_USO.md). La arquitectura funcional está en [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Desarrollo y pruebas

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
python -m py_compile app.py core/*.py
pytest -q
```

La integración continua ejecuta la suite en GitHub Actions con Python 3.10 y 3.12.

## Empaquetado binario opcional

El proyecto incluye configuración experimental de PyInstaller en [packaging/](packaging/) y un workflow de release en [.github/workflows/release.yml](.github/workflows/release.yml). La vía recomendada sigue siendo ejecutar la app con Python y los lanzadores incluidos, porque es más transparente y reproducible.

## Cómo citar

Si usas este repositorio, la aplicación o parte de su código en un trabajo académico, periodístico o docente, cita a sus autores:

> Pardal Pérez, Xoán, y Quian, Alberto (2026). *Auditor de Contratos Públicos* (versión 1.0.1) [software]. Universidade de Santiago de Compostela. https://github.com/AlbertoQuian/auditor-contratos-publicos

```bibtex
@software{pardal_perez_quian_2026_auditor_contratos_publicos,
	author = {Pardal Pérez, Xoán and Quian, Alberto},
	title = {Auditor de Contratos Públicos},
	year = {2026},
	version = {1.0.1},
	institution = {Universidade de Santiago de Compostela},
	url = {https://github.com/AlbertoQuian/auditor-contratos-publicos},
	note = {Software}
}
```

## Autoría, proyecto y licencia

Aplicación desarrollada en coautoría por **Xoán Pardal Pérez** (autor principal) y **[Alberto Quian](https://albertoquian.github.io/)** (apoyo metodológico y técnico), en la **Universidade de Santiago de Compostela**.

Esta aplicación es parte del proyecto de I+D+i:

- *XornalIA: Desarrollo, validación y transferencia de una plataforma integradora de soluciones de inteligencia artificial generativa para medios de comunicación* (PDC2025-166024-I00), financiado por el Ministerio de Ciencia e Innovación y la Agencia Estatal de Investigación.

El código se publica bajo licencia MIT. Consulta [LICENSE](LICENSE), [AUTHORS.md](AUTHORS.md), [CITATION.cff](CITATION.cff) y [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md) para detalles de reutilización, cita académica y licencias de dependencias.
