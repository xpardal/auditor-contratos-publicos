# Empaquetado binario (opcional, experimental)

Esta carpeta contiene la vía **opcional** para producir un binario distribuible
del Auditor de Contratos Públicos usando [PyInstaller](https://pyinstaller.org/).

Está pensada para usuarios sin Python instalado y sin acceso cómodo a
terminal. La vía **principal** del proyecto sigue siendo:

1. Lanzadores doble clic (`launch_macos.command`, `launch_linux.sh`,
   `launch_windows.bat`) en la raíz del repositorio.
2. Instalación clásica con `pip install -r requirements.txt`.

## Por qué es experimental

- **No hay cross-compilation**: PyInstaller produce binarios para el sistema
  operativo en el que se ejecuta. Para distribuir en macOS, Linux y Windows
  hay que construir tres veces, una por SO. El workflow
  [`.github/workflows/release.yml`](../.github/workflows/release.yml) lo
  automatiza usando los runners correspondientes de GitHub Actions.
- **Tamaño**: Streamlit + Plotly + DuckDB + Pandas + PyArrow producen
  binarios de **varios cientos de MB** comprimidos.
- **macOS**: el binario no está firmado. La primera vez Gatekeeper avisa;
  hay que abrirlo con clic derecho → *Abrir*.
- **Windows**: algunos antivirus marcan binarios PyInstaller como
  sospechosos por su naturaleza autoextraíble. Es un falso positivo
  conocido del proyecto upstream.
- **Linux**: el binario depende de la versión de glibc del sistema en que se
  construyó. Construir en `ubuntu-latest` da compatibilidad razonable con
  distribuciones recientes.

## Construir localmente

Desde la raíz del repositorio:

```bash
# macOS / Linux
./packaging/build_unix.sh

# Windows (cmd o PowerShell)
packaging\build_windows.bat
```

El binario y todas sus dependencias quedan en `dist/auditor-contratos/`.
Para ejecutarlo:

```bash
./dist/auditor-contratos/auditor-contratos        # macOS / Linux
dist\auditor-contratos\auditor-contratos.exe      # Windows
```

Streamlit abrirá la app en el navegador en un puerto local disponible.

## Construir un release oficial multi-SO

El workflow `release.yml` se dispara automáticamente al publicar un tag
`vX.Y.Z`. Construye los tres binarios en paralelo y los publica como
artefactos de la *release* correspondiente.

```bash
git tag v1.0.0
git push origin v1.0.0
```

## Estructura

| Archivo | Función |
|---|---|
| `run_app.py` | Wrapper que arranca Streamlit con `app.py` desde el bundle. |
| `auditor.spec` | Spec de PyInstaller multiplataforma. |
| `build_unix.sh` | Construcción local en macOS/Linux. |
| `build_windows.bat` | Construcción local en Windows. |
| `README.md` | Este documento. |
