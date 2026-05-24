# Licencias de terceros

Este proyecto se publica bajo licencia MIT. Sus dependencias directas mantienen sus propias licencias. La tabla siguiente resume las dependencias declaradas en `requirements.txt` y `requirements-dev.txt`; las dependencias transitivas deben consultarse en el entorno Python instalado.

| Paquete | Uso principal | Licencia declarada por el proyecto |
| --- | --- | --- |
| Streamlit | Interfaz web local | Apache License 2.0 |
| pandas | Manipulación tabular | BSD 3-Clause License |
| pdfplumber | Validación de informes PDF en pruebas | MIT License |
| DuckDB | Consultas SQL sobre CSV | MIT License |
| PyArrow | Caché Parquet y formatos columnares | Apache License 2.0 |
| lxml | Procesamiento XML | BSD 3-Clause License |
| certifi | Certificados raíz para HTTPS | Mozilla Public License 2.0 |
| Plotly | Visualizaciones interactivas | MIT License |
| Kaleido | Exportación estática de gráficos Plotly a PNG | MIT License |
| Jinja2 | Plantillas HTML | BSD 3-Clause License |
| ReportLab | Generación de informes PDF | BSD License |
| pytest | Pruebas automatizadas | MIT License |

## Comprobación antes de publicar

Antes de una publicación formal conviene ejecutar en el entorno virtual:

```bash
python -m pip list
python -m pip show streamlit pandas duckdb pyarrow lxml certifi plotly kaleido jinja2 reportlab pytest pdfplumber
```

Este documento no sustituye asesoramiento legal; sirve como inventario práctico para transparencia del repositorio.
