# Arquitectura del proyecto

Auditor de Contratos Públicos es una aplicación local-first construida con Streamlit y módulos Python separados por responsabilidad. La interfaz orquesta la carga, el análisis y la visualización, mientras que `core/` concentra la lógica reutilizable y testeable.

## Principios

- **Local-first:** los datos se procesan en el ordenador del investigador.
- **Trazabilidad:** las descargas generan manifiestos con URL, fecha y ficheros creados.
- **Separación de responsabilidades:** la interfaz no contiene parsers ni consultas pesadas.
- **Reproducibilidad:** los loaders trabajan sobre ficheros locales y las pruebas cubren parsing, radar, descargas y gráficos.

## Diagrama general

```mermaid
flowchart TD
    U[Investigador/a] --> UI[app.py · Interfaz Streamlit]

    UI --> D[core/downloaders.py]
    D --> P1[PLACSP · feed Atom oficial]
    D --> P2[Tribunal/portales oficiales · URL directa]
    D --> M[data/_manifests · trazabilidad]

    UI --> PL[core/placsp.py]
    PL --> A1[Archivos .atom locales]
    UI --> UP[data/uploads · archivos seleccionados]
    PL --> C1[.cache/parquet]

    UI --> TC[core/tribunal_cuentas.py]
    TC --> CSV[tb_economica.csv + tb_inventario.csv]
    TC --> DB[DuckDB sobre CSV]

    UI --> AN[core/analysis.py]
    UI --> VI[core/visual.py]
    UI --> RP[core/report.py]
    UI --> PDF[core/pdf_report.py]

    AN --> R[Radar de fraccionamiento]
    VI --> G[Gráficos Plotly]
    RP --> H[Informe HTML autoportante]
    PDF --> P[Informe PDF]
```

## Componentes

| Componente | Responsabilidad |
| --- | --- |
| `app.py` | Interfaz Streamlit, navegación, formularios, presentación de resultados. |
| `core/analysis.py` | Radar de fraccionamiento, parsing de fechas, banderas forenses. |
| `core/constants.py` | Límites legales, patrones regex y provincias de referencia. |
| `core/downloaders.py` | Descargas reproducibles, extracción ZIP segura, manifiestos JSON. |
| `core/money.py` | Normalización y formato de importes en euros. |
| `core/placsp.py` | Lectura streaming de Atom PLACSP y caché Parquet. |
| `core/tribunal_cuentas.py` | Conversión `.accdb` con `mdbtools` y consultas DuckDB sobre CSV. |
| `core/visual.py` | Figuras Plotly desacopladas de Streamlit. |
| `core/report.py` | Informe HTML descargable con tablas y gráficos interactivos. |
| `core/pdf_report.py` | Informe PDF descargable con resumen, tablas e imágenes estáticas. |
| `.streamlit/config.toml` | Configuración local de Streamlit, incluido límite de subida para CSV/ACCDB grandes. |
| `tests/` | Pruebas unitarias del núcleo reutilizable. |

## Flujo PLACSP

```mermaid
sequenceDiagram
    participant I as Investigador/a
    participant UI as Streamlit
    participant DL as downloaders
    participant FS as Disco local
    participant PL as placsp
    participant AN as analysis

    I->>UI: Descargar/actualizar feed Atom
    UI->>DL: descargar_placsp_menores()
    DL->>FS: Guarda .atom + manifiesto
    I->>UI: Cargar y analizar carpeta
    UI->>PL: cargar_placsp()
    PL->>FS: Lee .atom y cachea Parquet
    UI->>AN: ejecutar_radar()
    AN-->>UI: Alertas, índice de riesgo y señales
```

## Flujo Tribunal de Cuentas

```mermaid
flowchart LR
    ACCDB[Liquidaciones .accdb] --> MDB[mdbtools]
    MDB --> CSV1[tb_economica.csv]
    MDB --> CSV2[tb_inventario.csv]
    CSV1 --> DUCK[DuckDB]
    CSV2 --> DUCK
    DUCK --> RANK[Rankings por entidad, capítulo y provincia]
```

## Datos y Git

El repositorio no debe incluir descargas completas, cachés, entornos virtuales ni bases pesadas. `.gitignore` excluye `data/`, `.cache/`, `.venv/`, `__pycache__/`, `.pytest_cache/`, `.accdb` y dumps voluminosos. Las fuentes reales se descargan desde la app o se cargan localmente por el investigador.

La app mantiene dos vías de entrada: selector de archivo del navegador para `.atom`, CSV, Excel, PDF y `.accdb`; y campos de ruta local para carpetas completas o ficheros muy grandes. Los archivos seleccionados se copian a `data/uploads/`, carpeta ignorada por Git.
