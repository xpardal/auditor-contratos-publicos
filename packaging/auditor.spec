# =============================================================================
# Auditor de Contratos Públicos · Universidade de Santiago de Compostela
# PyInstaller spec multiplataforma para construir un binario distribuible.
#
# Uso (en cada SO objetivo):
#     pip install -r requirements.txt
#     pip install -r requirements-dev.txt
#     pyinstaller packaging/auditor.spec --clean --noconfirm
#
# El binario resultante queda en dist/auditor-contratos/.
#
# Autores: Xoán Xosé Pardal Pérez; Alberto Quian (apoyo metodológico y técnico).
# Esta aplicacion es parte del proyecto de I+D+i:
# - XornalIA: Desarrollo, validacion y transferencia de una plataforma integradora de soluciones de inteligencia artificial generativa para medios de comunicacion (PDC2025-166024-I00).
# Licencia: MIT (https://opensource.org/license/mit).
# SPDX-License-Identifier: MIT
# =============================================================================

# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_submodules,
    copy_metadata,
)

PROJECT_ROOT = Path(SPECPATH).resolve().parent

block_cipher = None

# Streamlit, Plotly y otros paquetes cargan recursos en runtime que PyInstaller
# no detecta automáticamente. Hay que recolectar datos y metadatos para que el
# binario los encuentre dentro del bundle.
datas = []
datas += collect_data_files("streamlit")
datas += collect_data_files("plotly")
datas += collect_data_files("kaleido")
datas += collect_data_files("certifi")
datas += copy_metadata("streamlit")
datas += copy_metadata("plotly")

# La app y sus módulos se incluyen como datos para que el wrapper los encuentre
# en _MEIPASS con la misma estructura que en desarrollo.
datas += [
    (str(PROJECT_ROOT / "app.py"), "."),
    (str(PROJECT_ROOT / "core"), "core"),
    (str(PROJECT_ROOT / ".streamlit"), ".streamlit"),
    (str(PROJECT_ROOT / "README.md"), "."),
    (str(PROJECT_ROOT / "LICENSE"), "."),
    (str(PROJECT_ROOT / "AUTHORS.md"), "."),
    (str(PROJECT_ROOT / "CITATION.cff"), "."),
    (str(PROJECT_ROOT / "THIRD_PARTY_LICENSES.md"), "."),
]

hiddenimports = []
hiddenimports += collect_submodules("streamlit")
hiddenimports += collect_submodules("plotly")
hiddenimports += [
    "core",
    "core.analysis",
    "core.constants",
    "core.downloaders",
    "core.money",
    "core.placsp",
    "core.report",
    "core.tribunal_cuentas",
    "core.visual",
    "core.pdf_report",
]

a = Analysis(
    [str(PROJECT_ROOT / "packaging" / "run_app.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # No necesitamos pruebas ni tooling de desarrollo dentro del binario.
        "pytest",
        "PyInstaller",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="auditor-contratos",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,            # UPX puede activar antivirus; desactivado por defecto.
    console=True,         # Mantener consola: muestra logs de Streamlit y errores claros.
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="auditor-contratos",
)
