# 📚 Guía de uso — Auditor de Contratos Públicos

> Manual completo para investigadores y periodistas que **no necesitan
> usar la terminal**. Si arrancaste la app con el lanzador
> (`launch_macos.command`, `launch_linux.sh` o `launch_windows.bat`),
> esta guía cubre todo lo que verás dentro de la interfaz.

**Autores:** Xoán Xosé Pardal Pérez (autor principal) y
[Alberto Quian](https://albertoquian.github.io/) (apoyo metodológico y técnico).  
**Institución:** Universidade de Santiago de Compostela.  
**Esta aplicación es parte del proyecto de I+D+i:**

- *XornalIA: Desarrollo, validación y transferencia de una plataforma
  integradora de soluciones de inteligencia artificial generativa para medios
  de comunicación* (PDC2025-166024-I00), financiado por el Ministerio de
  Ciencia e Innovación y la Agencia Estatal de Investigación.

**Licencia:** [MIT](https://opensource.org/license/mit).

---

## Índice

1. [¿Qué hace la herramienta y qué no hace?](#1-qué-hace-la-herramienta-y-qué-no-hace)
2. [Antes de empezar: instalación rápida sin terminal](#2-antes-de-empezar-instalación-rápida-sin-terminal)
3. [Anatomía de la interfaz](#3-anatomía-de-la-interfaz)
4. [Flujo 1 · PLACSP (contratos menores del Estado)](#4-flujo-1--placsp-contratos-menores-del-estado)
5. [Flujo 2 · Tribunal de Cuentas (entes locales)](#5-flujo-2--tribunal-de-cuentas-entes-locales)
6. [Visualizaciones interactivas e informes](#6-visualizaciones-interactivas-e-informes)
7. [Cómo interpretar las alertas (lectura periodística)](#7-cómo-interpretar-las-alertas-lectura-periodística)
8. [Privacidad, trazabilidad y manifiestos](#8-privacidad-trazabilidad-y-manifiestos)
9. [Solución de problemas habituales](#9-solución-de-problemas-habituales)
10. [Glosario rápido](#10-glosario-rápido)

---

## 1. ¿Qué hace la herramienta y qué no hace?

**Sí hace:**

- Descarga datos oficiales (PLACSP, ficheros publicados por el Tribunal
  de Cuentas y otros portales públicos con URL directa).
- Detecta indicios estadísticos de **fraccionamiento de contratos
  menores** ("pitufeo") aplicando los límites de la Ley 9/2017.
- Procesa millones de partidas presupuestarias con **DuckDB**, sin saturar
  la memoria del ordenador.
- Genera **rankings**, **gráficos interactivos**, informes HTML/PDF y tablas
  CSV que puedes adjuntar a un reportaje.
- Se publica bajo licencia libre MIT, con autoría documentada en
  `AUTHORS.md`, licencias de terceros en `THIRD_PARTY_LICENSES.md` y
  arquitectura técnica en `docs/ARCHITECTURE.md`.

**No hace:**

- No es una acusación de corrupción. Lo que devuelve son **señales
  estadísticas** que necesitan contraste documental.
- No envía nada a la nube. Todo se procesa en tu ordenador.
- No automatiza formularios web ni navegación con sesión: solo trabaja
  con **fuentes oficiales con URL estable** para que el método sea
  defendible y reproducible.

---

## 2. Antes de empezar: instalación rápida sin terminal

Hay un lanzador para cada sistema operativo:

| Sistema | Doble clic en | Qué hace |
| --- | --- | --- |
| 🍎 macOS | `launch_macos.command` | Crea entorno, instala dependencias, abre el navegador |
| 🐧 Linux | `launch_linux.sh` | Igual, en GNOME/KDE basta con doble clic ("Ejecutar") |
| 🪟 Windows | `launch_windows.bat` | Igual, abre una ventana negra que **no debes cerrar** |

**Requisito previo para usar la app:** tener instalado **Python 3.10 o superior**.

- macOS: `brew install python@3.12` o desde [python.org](https://www.python.org/downloads/).
- Windows: instalador de [python.org](https://www.python.org/downloads/) marcando
  "Add Python to PATH".
- Linux: `sudo apt install python3 python3-venv python3-pip` (o equivalente).

La primera ejecución tarda 2-3 minutos porque descarga las dependencias.
Las siguientes son inmediatas.

Si ya existía una carpeta `.venv/` creada con Python anterior a 3.10, el
lanzador la recrea automáticamente con una versión válida antes de abrir la app.

### Dependencia opcional para `.accdb` del Tribunal de Cuentas

Para PLACSP, CSV e informes no necesitas nada más. Solo hay
un caso especial: si quieres abrir directamente `Liquidaciones2024.accdb`
del Tribunal de Cuentas, el ordenador necesita **mdbtools**, un conversor
externo de bases Access.

`mdbtools` no aparece en `requirements.txt` porque no es una librería
Python: se instala en el sistema operativo. La app funciona sin él; lo
único que queda desactivado es la conversión directa `.accdb` → CSV.

### macOS

1. Instala Homebrew si no lo tienes: abre <https://brew.sh/> y sigue el
  comando que muestra la página.
1. Abre la app Terminal.
1. Pega este comando y pulsa Enter:

```bash
brew install mdbtools
```

1. Cierra y vuelve a abrir el lanzador `launch_macos.command`.

### Linux Debian/Ubuntu

```bash
sudo apt update
sudo apt install mdbtools
```

### Windows

`mdbtools` no está disponible de forma práctica en Windows. Abre el
`.accdb` en Microsoft Access o LibreOffice Base, exporta las tablas
`tb_economica` y `tb_inventario` como CSV, y luego usa la pestaña
**📊 Consultar CSV**. El análisis posterior es el mismo.

---

## 3. Anatomía de la interfaz

Al abrir la app verás:

- **Barra lateral izquierda**:
  - *Fuente de datos*: elige entre PLACSP, Tribunal de Cuentas o la guía.
  - *Umbrales del radar*: cuántos contratos mínimo deben acumularse para
    disparar alerta (2 = más sensible, 3+ = menos falsos positivos).
- **Zona principal**: cambia según la fuente elegida.
- **Botones de selección de archivo**: permiten elegir `.atom`, CSV o
  `.accdb` desde el navegador local cuando tiene sentido.
- **Campos de ruta local**: siguen disponibles para carpetas completas o
  archivos muy grandes. Las carpetas de trabajo se pueden crear desde la
  interfaz.
- **Botones ⬇️**: en cada vista hay un botón para descargar lo que
  ves (CSV, HTML o PDF cuando el radar está disponible).
- **Pestaña ❓ Guía**: resumen rápido siempre accesible dentro de la app.

---

## 4. Flujo 1 · PLACSP (contratos menores del Estado)

Para auditar un organismo concreto (un ministerio, una diputación, un
ayuntamiento) usando la Plataforma de Contratación del Sector Público.

### Paso 1 — Descargar los `.atom` oficiales

1. En la barra lateral elige **🌐 PLACSP (carpeta .atom)**.
2. Despliega **⬇️ Descargar/actualizar .atom oficiales de PLACSP**.
3. Deja la URL por defecto. Decide cuántas páginas bajar:
   - 1-5 páginas: actualización del día.
   - 30-100 páginas: mes/trimestre.
   - 300+ páginas: histórico anual.
4. Pulsa **⬇️ Descargar/actualizar PLACSP**.
  Cada página es ~4 MB. Verás una barra de progreso y un manifiesto JSON. Para
  localizar ayuntamientos concretos en auditorías municipales, usa una descarga
  profunda: algunos órganos no aparecen hasta pasadas más de 100 páginas del feed.

También puedes saltarte la descarga oficial si ya tienes archivos `.atom`:

- Elige **Seleccionar archivos .atom** para escoger uno o varios ficheros
  desde el navegador. La app los copia a `data/uploads/placsp_atom/`.
- Elige **Usar carpeta local** si ya tienes una carpeta completa con
  muchos `.atom` en tu ordenador.

### Paso 2 — Procesar la carpeta

1. Si descargaste desde la app, la ruta queda rellenada automáticamente
  con la carpeta descargada. Si seleccionaste archivos, la app usará la
  carpeta de trabajo indicada.
2. Pulsa **🚀 Cargar y analizar**.
3. La primera vez tarda; después es **instantáneo** porque guarda un
   `.parquet` cacheado en `.cache/`.

### Paso 3 — Filtrar y disparar el radar

1. Abre **🧭 Diagnóstico de cobertura municipal** cuando quieras comprobar
  si un ayuntamiento/concello aparece como órgano contratante en los `.atom`
  cargados o si solo hay contratos ubicados en ese municipio. Si no aparece
  en este panel, amplía la descarga o verifica si la entidad publica sus
  contratos menores en otra plataforma.
2. Filtra por **comunidad autónoma**, **provincia**, **municipio**, **tipo de entidad**
  (ayuntamiento, diputación, ministerio, universidad, etc.), **organismo**
  y **año fiscal**.
3. Usa los buscadores de **adjudicatario** y **concepto** para localizar
  proveedores o servicios concretos, y ajusta el **rango de importe** para
  concentrarte en contratos próximos a los límites legales.
4. Revisa la tabla enriquecida: incluye órgano, territorio, tipo de entidad,
  CPV, concepto, adjudicatario, importe y enlace al expediente PLACSP cuando
  el feed lo publica.
5. Baja al **🦊 Radar de fraccionamiento sistemático**: cualquier grupo
   marcado 🟠/🔴/🚨 son los candidatos a investigar.
6. Abre la **ficha de caso prioritario** para ver el índice 0-100, las
  señales que explican la alerta y los contratos concretos que la forman.

### Paso 4 — Visualizar y exportar

- En la pestaña **📊 Visualizaciones** verás un treemap de adjudicatarios,
  una dispersión nº contratos × total acumulado, distribución de importes,
  línea temporal, concentración del gasto, ranking territorial y calendario
  mensual año × mes.
- En **📄 Informe y descargas** puedes bajar un informe HTML, un PDF
  imprimible, un ZIP de tablas CSV y un ZIP de gráficos PNG adaptados para
  adjuntar al reportaje o compartir con el editor.

---

## 5. Flujo 2 · Tribunal de Cuentas (entes locales)

Responde a la pregunta clásica del periodismo de gasto público:
*¿qué ayuntamientos de mi provincia gastaron más en bienes y servicios
en 2024?*.

### Si tienes los CSV (`tb_economica.csv` + `tb_inventario.csv`)

1. Pestaña **📊 Consultar CSV**.
2. Elige **Seleccionar archivos CSV** para escogerlos con botón, o
  **Usar rutas locales** si ya conoces su ubicación en disco.
3. Marca capítulo presupuestario (Capítulo 2 = bienes y servicios).
4. Elige ámbito: España entera, Galicia o provincias INE.
5. Pulsa **📈 Calcular ranking**. DuckDB consulta los CSV sin cargarlos
   en RAM.
6. Descarga el ranking como CSV o entra en el detalle por entidad.

### Si solo tienes el `.accdb`

1. Pestaña **🔧 Convertir .accdb**.
2. Si la app muestra "mdbtools detectado", selecciona el `.accdb` con
  botón o indica una ruta local. Para archivos muy grandes, la ruta local
  suele ser más cómoda.
3. Indica o crea desde la interfaz la carpeta de salida.
4. Deja activada la opción de convertir solo `tb_economica` y
  `tb_inventario` salvo que necesites exportar todo el `.accdb`.
5. Ajusta el tiempo máximo por tabla si el archivo es muy grande.
6. Pulsa **🔧 Convertir tablas**. Quedará todo como CSV listo para la
  pestaña anterior. Si `mdbtools` se queda bloqueado en una tabla, la app
  cancela esa conversión y muestra un error en vez de quedarse colgada.
7. Si la app avisa de que falta `mdbtools`, sigue las instrucciones que
  aparecen en pantalla o exporta las dos tablas principales a CSV desde
  Access/LibreOffice.

### Si solo tienes una URL oficial al `.zip`/`.accdb`

1. Pestaña **⬇️ Descargar fuente**.
2. Pega la URL directa, elige o crea una carpeta destino y, si quieres,
   define un nombre de archivo.
3. La herramienta deja un **manifiesto** con fecha y URL exacta. Esto
   permite citar la procedencia en el reportaje.

---

## 6. Visualizaciones interactivas e informes

No todas las fuentes tienen el mismo nivel de detalle. La app adapta las
salidas al dato disponible:

| Fuente | Qué verás |
| --- | --- |
| **PLACSP** | Radar completo, ficha de caso, tablas, gráficos interactivos, red de relaciones, mapa, informe HTML/PDF, CSV y PNG. |
| **Tribunal de Cuentas** | Ranking de entidades por capítulo, tabla descargable, gráfico de barras, ranking interactivo y detalle por entidad. No hay radar contractual porque las liquidaciones no incluyen contratos menores por adjudicatario. |

Cuando hay análisis con radar tienes:

- **Semáforo de riesgo**: grupos cuyo acumulado supera, roza o se acerca al
  límite.
- **Ficha de caso prioritario**: índice 0-100, señales detectadas y detalle.
- **Treemap por adjudicatario** (tamaño = total adjudicado; color = porcentaje del límite legal).
- **Dispersión** nº contratos × total acumulado.
- **Serie temporal** importe por año fiscal y tipo.
- **Distribución de importes** con líneas en 15.000 € y 40.000 €.
- **Timeline de contratos** por fecha, proveedor e importe.
- **Concentración del gasto**: cuánto peso acumulan los principales adjudicatarios.
- **Red órgano-adjudicatario** dinámica en la interfaz, con filtros por tipo
  de nodo, zoom, arrastre, pantalla completa y controles de reordenación.
- **Ranking de relaciones principales** en el HTML/PNG, como versión estática
  legible de la red para navegador, redacción o impresión.
- **Mapa territorial** por comunidad autónoma o provincia, y ranking
  territorial diferenciado por comunidad, provincia o municipio cuando el dato
  existe.
- **Calendario mensual** año × mes para detectar picos de contratación.
- **Informe HTML autoportante** descargable: incluye resumen narrativo,
  tabla de alertas y tablas de contexto. Se abre en cualquier navegador sin
  necesidad de la app.
- **Informe PDF** descargable: resumen narrativo, tabla de alertas y tablas
  envolventes preparadas para textos largos, útil para compartir en redacción.
- **ZIP de tablas CSV** con alertas, radar completo, relaciones y contratos
  filtrados para edición o maquetación externa.
- **ZIP de gráficos PNG** con versiones estáticas adaptadas, pensadas para
  conservar color y legibilidad fuera de la interfaz interactiva.

---

## 7. Cómo interpretar las alertas (lectura periodística)

Una alerta del radar significa que **un mismo adjudicatario** acumula
contratos menores con **un mismo órgano** y **un mismo tipo de contrato**
en **un mismo año fiscal** por encima del 90% del límite legal:

- 🟠 **Cerca del límite** (>90%): merece comprobación.
- 🔴 **Roza el límite** (>95%): sospechoso.
- 🚨 **Acumulado por encima del límite**: indicio claro de posible
  fraccionamiento.

La columna **Índice_Riesgo** ordena los casos de 0 a 100. No sustituye al
criterio periodístico: prioriza casos combinando porcentaje acumulado sobre el
límite, número de contratos, importes pegados al umbral, importes repetidos y
concentración temporal.

La columna **Señales_Riesgo** explica por qué se puntuó el caso. Ejemplos:
"acumulado superior al límite legal", "proveedor recurrente", "importe
individual pegado al umbral" o "contratos concentrados en 18 días".

**Importante**: una alerta NO es prueba de irregularidad. Antes de
publicar conviene:

1. Verificar la coincidencia exacta del NIF del adjudicatario.
2. Pedir el expediente completo a transparencia.
3. Comprobar si los contratos son objetivamente separables (servicios
   distintos en momentos distintos) o si responden a un mismo objeto
   troceado.
4. Triangular con datos del Tribunal de Cuentas (Capítulo 2).

---

## 8. Privacidad, trazabilidad y manifiestos

- **Local-first**: ningún dato se sube a servidores externos. Todo el
  procesamiento ocurre en tu ordenador.
- Cada descarga genera un **manifiesto JSON** en `data/.../_manifests/`
  con fecha, URL visitada y archivos creados. Sirve para responder
  "¿de dónde sacaste ese dato?" en cualquier auditoría editorial.
- Las cachés Parquet (`.cache/`) se pueden borrar sin perder nada
  importante: se regeneran al volver a procesar la carpeta.

---

## 9. Solución de problemas habituales

| Síntoma | Posible causa | Cómo arreglarlo |
| --- | --- | --- |
| "Python no está instalado" al abrir el lanzador | Falta Python 3.10+ | Instálalo desde [python.org](https://www.python.org/downloads/) |
| Aviso `NotOpenSSLWarning` o Python 3.9 en macOS | `.venv/` creada con Python antiguo | Vuelve a abrir el lanzador; si persiste, borra `.venv/` y ejecútalo de nuevo |
| Error SSL al descargar PLACSP | macOS sin certificados de sistema | El proyecto usa `certifi`; reinstala dependencias borrando `.venv/` |
| "mdbtools no está instalado" | macOS/Linux sin conversor Access | macOS: `brew install mdbtools`; Ubuntu/Debian: `sudo apt update && sudo apt install mdbtools`; después reabre la app |
| "No puedo abrir .accdb en Windows" | mdbtools no existe de forma práctica en Windows | Abre el `.accdb` en MS Access o LibreOffice Base y exporta `tb_economica` y `tb_inventario` como CSV |
| Carpeta PLACSP vacía | Aún no descargaste | Usa el botón **⬇️ Descargar/actualizar PLACSP** |
| Error al escribir `.cache/placsp_*.parquet` | Se borró `.cache/` durante una sesión anterior | Vuelve a pulsar **🚀 Cargar y analizar**; la app recrea la caché automáticamente |
| El radar no muestra nada | Filtros demasiado restrictivos | Sube el slider de "Mínimo de contratos" a 2 y revisa el filtro de organismo |
| La red de relaciones no se ve tras actualizar | El navegador conserva una sesión antigua | Recarga la página y vuelve a abrir la pestaña **Red relaciones** |
| "Address already in use" al lanzar manualmente | Otra app usa el puerto 8501 | Los lanzadores ya buscan puerto libre; si usas terminal, prueba `streamlit run app.py --server.port 8502` |

---

## 10. Glosario rápido

- **Contrato menor**: contrato sin licitación pública, hasta 15.000 € en
  servicios/suministros y 40.000 € en obras (Ley 9/2017, art. 118).
- **Pitufeo / fraccionamiento**: trocear un objeto contractual en varios
  contratos menores para evitar la licitación. Es ilegal.
- **Trampa IVA**: usar la frontera del IVA para esconder un contrato
  por encima del límite (un 18.150 € con IVA equivale a 15.000 € sin IVA).
- **PLACSP**: Plataforma de Contratación del Sector Público.
- **Capítulo 2**: capítulo presupuestario de "Gastos en bienes y
  servicios". Donde más fraccionamiento se concentra.
- **Manifiesto**: registro JSON automático de cada descarga.
- **Caché Parquet**: archivo binario columnar comprimido que guarda
  resultados intermedios para acelerar siguientes ejecuciones.

---

> Para detalles técnicos (estructura del proyecto, tests, cómo
> contribuir) consulta el [README.md](../README.md).
