# 🕵️ Auditor de Contratos Públicos

> **TFG — Periodismo de Datos.** Herramienta local-first para detectar
> fraccionamiento de contratos menores ("pitufeo") y analizar el gasto
> de los entes locales españoles. Pensada para procesar **millones de
> partidas presupuestarias** sin enviar nada a la nube.

[![tests](https://img.shields.io/badge/tests-53%20passed-brightgreen)](tests/)
[![python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![license](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![cross-platform](https://img.shields.io/badge/macOS%20·%20Linux%20·%20Windows-supported-lightgrey)](#-multiplataforma)

---

## Autoría, proyecto y licencia

Aplicación desarrollada en coautoría por **Xoán Xosé Pardal Pérez** (autor
principal) y **[Alberto Quian](https://albertoquian.github.io/)** (apoyo
metodológico y técnico), en la **Universidade de Santiago de Compostela**.

Esta aplicación es parte de los proyectos de I+D+i:

- *Inteligencia artificial en medios digitales en España: efectos y roles*
  (PID2024-156034OB-C22), financiado por MICIU/AEI/10.13039/501100011033
  y “FEDER/UE”.
- *XornalIA* (PDC2025-166024-I00 - Desarrollo, validación y transferencia
  de una plataforma integradora de soluciones de inteligencia artificial
  generativa para medios de comunicación), financiado por el Ministerio de
  Ciencia e Innovación y la Agencia Estatal de Investigación.

El código se publica bajo licencia libre **MIT** ([texto oficial OSI](https://opensource.org/license/mit)).
Consulta [LICENSE](LICENSE), [AUTHORS.md](AUTHORS.md), [CITATION.cff](CITATION.cff)
y [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md) para reutilización,
atribución, cita académica y licencias de dependencias.

---

## 🚀 Para investigadores sin terminal (recomendado)

Doble clic en el lanzador correspondiente a tu sistema:

| Sistema | Archivo | Notas |
| --- | --- | --- |
| 🍎 macOS | `launch_macos.command` | La primera vez: clic derecho → *Abrir* |
| 🐧 Linux | `launch_linux.sh` | Hazlo ejecutable: `chmod +x launch_linux.sh` |
| 🪟 Windows | `launch_windows.bat` | Doble clic; no cierres la ventana negra |

El lanzador:

1. Comprueba que tienes Python 3.10 o superior (única dependencia previa).
2. Crea un entorno virtual aislado en `.venv/` o lo recrea si quedó hecho con Python antiguo.
3. Instala todo lo necesario.
4. Abre la app en tu navegador en el primer puerto libre entre `8501` y `8520`.

> 💡 La primera ejecución tarda 2-3 minutos (descarga dependencias).
> Las siguientes son inmediatas.

📖 **Manual completo paso a paso:** [`docs/GUIA_USO.md`](docs/GUIA_USO.md)
(también accesible dentro de la app desde la pestaña **❓ Guía de uso**).

---

## ⌨️ Para usuarios de terminal

```bash
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py

# (opcional, solo si vas a leer .accdb)
brew install mdbtools                 # macOS
sudo apt install mdbtools             # Debian/Ubuntu
# Windows: abre el .accdb con MS Access o LibreOffice y exporta a CSV
```

> ⚠️ Se ejecuta `app.py`. No hay que abrir versiones antiguas ni copias de desarrollo.

`requirements.txt` instala las dependencias Python de la app. La conversión
directa de `.accdb` requiere **mdbtools**, que es una dependencia del sistema
operativo, no una librería Python. Por eso no puede instalarse con `pip`:
en macOS/Linux se instala una sola vez con el gestor del sistema; en
Windows se recomienda exportar `tb_economica` y `tb_inventario` desde
Microsoft Access o LibreOffice Base y analizar esos CSV en la app.

### Tests (solo para mantenedores)

```bash
pip install -r requirements-dev.txt   # pytest, pyinstaller, etc.
pytest -q                             # 53 tests sobre core/
```

> Los **usuarios finales no necesitan ejecutar tests**. `requirements-dev.txt`
> contiene herramientas de desarrollo (pytest, PyInstaller) que solo hacen falta
> si vas a contribuir al proyecto o a construir un binario distribuible.

---

## 💻 Multiplataforma

| Componente | macOS | Linux | Windows |
| --- | --- | --- | --- |
| Streamlit + Pandas + DuckDB + PDF | ✅ | ✅ | ✅ |
| Descarga PLACSP (SSL vía `certifi`) | ✅ | ✅ | ✅ |
| Descarga URL directa Tribunal | ✅ | ✅ | ✅ |
| Análisis CSV/PDF/Excel | ✅ | ✅ | ✅ |
| Visualizaciones Plotly + informes/tablas | ✅ | ✅ | ✅ |
| Conversión `.accdb` → CSV | ✅ con `mdbtools` | ✅ con `mdbtools` | ⚠️ usar MS Access / LibreOffice |

El análisis del Tribunal de Cuentas funciona igual una vez existen los CSV.
`mdbtools` solo hace falta para convertir el `.accdb` original a CSV en
macOS/Linux.

---

## 🧭 Tres fuentes de datos unificadas

| Fuente | Origen | Cómo se obtiene/carga | Volumen típico |
| --- | --- | --- | --- |
| **PLACSP** | [contrataciondelestado.es](https://contrataciondelestado.es) | Descarga automática, selección de `.atom` o carpeta local | ~1.100/año |
| **Tribunal de Cuentas** | Liquidaciones de TODOS los entes locales | URL directa oficial, selección de `.accdb` o CSVs `tb_economica`+`tb_inventario` | 1,2 M filas |
| **Archivo individual** | PDF / CSV / Excel sueltos | Subida directa | Cualquiera |

Las descargas nuevas se guardan en `data/` (ignorado por Git) y generan
un **manifiesto JSON** en `_manifests/` con fecha, URL visitada y
ficheros creados. Así se puede justificar metodológicamente de dónde
salió cada fuente.

La interfaz ofrece botones de selección de archivos cuando el navegador lo
permite (`.atom`, CSV, Excel, PDF, `.accdb`). Para carpetas completas o
archivos enormes también mantiene campos de ruta local, porque los
navegadores no pueden elegir carpetas arbitrarias del sistema por motivos
de seguridad. Las subidas locales se copian a `data/uploads/`, también
ignorado por Git.

### 1) PLACSP

- Pestaña **⬇️ Descargar/actualizar .atom oficiales de PLACSP**: sigue el
  feed paginado oficial de contratos menores.
- Modo **Seleccionar archivos .atom**: permite elegir uno o varios `.atom`
  desde el navegador y copiarlos a una carpeta de trabajo local.
- Modo **Usar carpeta local**: recomendado para históricos grandes ya
  descargados o compartidos por otro investigador.
- La opción **Cargar y analizar al terminar** procesa automáticamente la
  carpeta descargada y deja los contratos listos para filtrar, sin subirlos
  uno a uno.
- El control **Máx. páginas** limita la descarga para evitar traer
  cientos de lotes por accidente.
- Parsing **streaming** con `xml.etree.iterparse` → no carga el XML entero.
- **Caché Parquet** (`.cache/placsp_<hash>.parquet`): el primer escaneo
  tarda; los siguientes son instantáneos.
- Filtros por órgano, año fiscal, comunidad autónoma, provincia, tipo de
  entidad, tipo de contrato, adjudicatario, concepto y rango de importe.
- Tabla enriquecida con CPV, enlace directo al expediente PLACSP cuando
  está disponible y descarga del corpus filtrado.
- Radar de fraccionamiento automático.

### 2) Tribunal de Cuentas con DuckDB

La app:

1. Descarga una **URL directa oficial** a `.accdb`/`.zip`/`.csv`/`.xlsx`
   con manifiesto de procedencia. No automatiza formularios ni sesiones.
2. Permite seleccionar `tb_economica.csv` y `tb_inventario.csv` con botón
  de archivo o indicar rutas locales si ya están en disco.
3. Si tienes `Liquidaciones2024.accdb`, lo convierte a CSVs con
  `mdbtools` (macOS/Linux) o tras export manual desde Access/LibreOffice
  (Windows). Los lanzadores avisan si falta esta dependencia opcional.
4. Consulta los CSVs con **DuckDB** ejecutando SQL directamente sobre
   los ficheros: NO carga 1,19 M filas en RAM.
5. Genera rankings por entidad, capítulo presupuestario y ámbito
  territorial (toda España, solo Galicia, provincias INE), con gráfico
  de barras, ranking interactivo, detalle por entidad y descarga CSV.

### 3) Archivos individuales

PDF, CSV o Excel. Patrones regex (DNI/NIF, IBAN, importes, emails,
teléfonos, fechas) + banderas:

- 🚩 importe rozando 15k / 40k sin IVA
- 🚨 trampas IVA (15k+21%, 40k+21%, 15k+10%)

---

## 📊 Visualizaciones, informes y alcance por fuente

La salida depende del tipo de dato disponible en cada fuente:

| Fuente | Salida principal | Radar de fraccionamiento | Gráficos e informe |
| --- | --- | --- | --- |
| **PLACSP** | Contratos menores individuales | ✅ Sí | ✅ Paquete completo: gráficos interactivos, red, mapa, HTML, PDF, CSV y PNG |
| **Tribunal de Cuentas** | Partidas presupuestarias agregadas por entidad/capítulo | ⚠️ No contractual | ✅ Ranking, gráfico de barras, ranking Plotly y CSV |
| **Archivo individual PDF** | Hallazgos regex por página | ⚠️ No, salvo que sea tabla estructurada | ✅ Tabla de patrones y banderas |
| **Archivo individual CSV/Excel** | Tabla local | ✅ Si detecta adjudicatario, importe y fecha/año | ✅ Paquete completo cuando se activa el radar |

Cuando hay análisis con radar (PLACSP o CSV/Excel estructurado), la app ofrece:

- **Semáforo de riesgo** con grupos cuyo acumulado supera, roza o se acerca
  al límite.
- **Ficha de caso prioritario** con índice 0-100, señales explicables y detalle de contratos.
- **Treemap** de adjudicatarios: tamaño por total adjudicado y color por
  porcentaje del límite legal.
- **Dispersión** nº contratos × total acumulado.
- **Serie temporal** importe por año fiscal y tipo de contrato.
- **Distribución de importes** con líneas en 15.000 € y 40.000 €.
- **Timeline de contratos** por fecha e importe.
- **Concentración del gasto** tipo Pareto por adjudicatario.
- **Red órgano-adjudicatario** en la interfaz para detectar concentraciones
  y relaciones entre compradores públicos y proveedores.
- **Ranking de relaciones principales** en el HTML y en el ZIP PNG, como
  versión estática legible de la red para navegador, redacción o impresión.
- **Mapa territorial** interactivo por comunidad autónoma o provincia, más
  ranking territorial por comunidad, provincia o municipio inferido.
- **Calendario mensual** año × mes para detectar concentraciones temporales.
- **Informe HTML autoportante** descargable: incluye resumen narrativo,
  tabla de alertas y tablas de contexto. Se abre en cualquier navegador sin
  necesidad de la app.
- **Informe PDF** descargable: resumen narrativo, tabla de alertas y tablas
  para compartir en redacción.
- **ZIP de tablas CSV** con alertas, radar completo, relaciones y contratos
  filtrados para edición o maquetación externa.
- **ZIP de gráficos PNG** con versiones estáticas adaptadas, pensadas para
  conservar color y legibilidad fuera de la interfaz interactiva.

En Tribunal de Cuentas no se ejecuta el radar de fraccionamiento porque
las liquidaciones presupuestarias no contienen contratos menores por
adjudicatario. Sirve para ranking, contexto presupuestario y triangulación
con casos detectados en PLACSP.

---

## 🧱 Estructura del proyecto

```text
TFG/
├── app.py                  # UI Streamlit (única)
├── requirements.txt        # Dependencias de ejecución (usuarios)
├── requirements-dev.txt    # Dependencias de desarrollo (mantenedores)
├── pytest.ini
├── LICENSE
├── THIRD_PARTY_LICENSES.md
├── AUTHORS.md
├── CITATION.cff
├── CONTRIBUTING.md
├── README.md
├── launch_macos.command    # Lanzador doble clic macOS
├── launch_linux.sh         # Lanzador doble clic Linux
├── launch_windows.bat      # Lanzador doble clic Windows
├── .github/workflows/      # CI de tests y releases en GitHub Actions
├── packaging/              # Empaquetado binario opcional con PyInstaller
├── core/
│   ├── analysis.py         # Radar fraccionamiento + escáner
│   ├── constants.py        # Límites legales y patrones regex
│   ├── downloaders.py      # PLACSP + URLs directas + manifiestos
│   ├── money.py            # limpiar_dinero / formatear_euros
│   ├── placsp.py           # Loader .atom + caché Parquet
│   ├── report.py           # Informes HTML autoportantes
│   ├── tribunal_cuentas.py # mdbtools + DuckDB
│   └── visual.py           # Gráficos Plotly interactivos
├── tests/                  # tests pytest sobre core/
├── docs/
│   ├── GUIA_USO.md         # Manual completo para investigadores
│   └── ARCHITECTURE.md     # Representación de arquitectura y flujos
├── data/                   # Fuentes descargadas (ignorado por Git)
│   └── uploads/            # Copias locales de archivos seleccionados en la app
├── .streamlit/config.toml  # Límite de subida para CSV/ACCDB grandes
└── .cache/                 # Parquets de caché (auto-generado)
```

Los datos descargados, cachés, entornos virtuales, capturas, informes
exportados y bases voluminosas están excluidos mediante [.gitignore](.gitignore).
El repositorio debe contener el código, la documentación y las pruebas; las
fuentes grandes y resultados de análisis se descargan, se generan o se
cargan localmente desde la interfaz.

### Qué debe subirse al repositorio privado

Incluye código, tests, documentación, lanzadores, workflows, licencias y
metadatos de cita. No incluyas `.venv/`, `.cache/`, `data/`, ficheros `.accdb`,
exports, informes generados, credenciales, `.env`, capturas temporales ni
documentos con datos personales. Esos directorios y patrones ya están en
[.gitignore](.gitignore), de modo que cualquier persona que clone el repositorio
podrá reconstruir el entorno con `requirements.txt` y descargar o cargar sus
propias fuentes desde la interfaz.

---

## 🔬 Metodología del radar

Agrupa contratos por `(Adjudicatario, Órgano, Tipo_Contrato, Año_Fiscal)`
y dispara alerta si:

- Suma ≥ **90 %** del límite legal (13.500 € servicios / 36.000 € obras), Y
- Hay al menos **N contratos** (configurable).

Excluye adjudicatarios desconocidos, contratos > 50.000 € (ya no son
menores) y los que carecen de año fiscal identificable.

Cada grupo recibe además un **índice de riesgo 0-100** y una lista de
señales explicables: porcentaje sobre el límite, proveedor recurrente,
importe individual pegado al umbral, importes repetidos y concentración
temporal de contratos.

> Las alertas son **indicios estadísticos**, no acusación: requieren
> contraste documental antes de cualquier publicación.

---

## ⚙️ Detalles técnicos

- Python 3.10+.
- **DuckDB** para CSVs masivos: ranking nacional Capítulo 2 en ~2 s vs
  ~30 s con pandas.
- `@st.cache_data` + Parquet en disco: cambiar filtros nunca reprocesa.
- `core/downloaders.py` descarga fuentes a disco con SSL via `certifi`
  (resuelve el `CERTIFICATE_VERIFY_FAILED` típico de macOS/Windows).
- **Local-first**: nada sale del ordenador.
- `core/visual.py` → Plotly Express (treemap, scatter, barras apiladas).
- `core/report.py` → HTML embebido con `plotly.js` por CDN.
- `.github/workflows/tests.yml` → CI de GitHub Actions con Python 3.10 y 3.12.

La arquitectura funcional está documentada en [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## ✅ Qué hace y qué NO hace

**Sí**: descarga oficial paginada, detección de fraccionamiento, banderas
IVA, rankings DuckDB, gráficos interactivos, informe HTML, manifiestos de
procedencia.

**No**: scraping de formularios autenticados, decisiones legales,
suplantación de fuentes oficiales, envío de datos a la nube.

---

## 📦 Empaquetado binario opcional (experimental)

Para usuarios sin Python instalado y sin acceso a terminal, el repositorio
incluye una vía **opcional** de empaquetado con [PyInstaller](https://pyinstaller.org)
en [`packaging/`](packaging/) y un workflow de GitHub Actions
([`.github/workflows/release.yml`](.github/workflows/release.yml)) que produce
binarios para macOS, Linux y Windows al publicar un tag `vX.Y.Z`.

Limitaciones honestas a documentar:

- **No hay cross-compilation**: cada binario debe construirse en su sistema
  operativo de destino. Por eso la construcción se hace en runners de
  GitHub Actions (`macos-latest`, `ubuntu-latest`, `windows-latest`).
- Los binarios pesan **bastante** (Streamlit + Plotly + DuckDB + Pandas
  ocupan cientos de MB).
- En **macOS** los binarios sin firma muestran un aviso de Gatekeeper la
  primera vez (clic derecho → *Abrir*).
- En **Windows**, algunos antivirus marcan binarios PyInstaller como
  sospechosos por su naturaleza autoextraíble; esto es un falso positivo
  conocido.
- La vía **principal y recomendada** sigue siendo el lanzador `launch_*`
  con Python instalado: es ligera, transparente y reproducible.

Ver [`packaging/README.md`](packaging/README.md) para construir un binario
local o disparar un release.

---

## 🛣️ Próximos pasos sugeridos

- [ ] Cruzar PLACSP × Tribunal de Cuentas por NIF de adjudicatario.
- [ ] Mapa coroplético por provincia INE para Capítulo 2.
- [ ] Más patrones forenses (números de expediente, firmas digitales).
