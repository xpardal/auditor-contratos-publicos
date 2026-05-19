"""
Auditor de Contratos Públicos · Universidade de Santiago de Compostela
Punto de entrada para empaquetado binario con PyInstaller.

Streamlit no se ejecuta como un script Python normal: necesita el bootstrap
interno (`streamlit.web.bootstrap`) para registrar correctamente la sesión y
abrir la UI. Este wrapper localiza `app.py` (extraído por PyInstaller en el
directorio temporal `_MEIPASS`) y lo arranca con la misma configuración que
`streamlit run app.py`.

Autores: Xoán Xosé Pardal Pérez; Alberto Quian (apoyo metodológico y técnico).
Esta aplicación es parte de los proyectos de I+D+i: PID2024-156034OB-C22 y XornalIA (PDC2025-166024-I00).
Licencia: MIT (https://opensource.org/license/mit).
SPDX-License-Identifier: MIT
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def _resolve_app_path() -> Path:
    """Devuelve la ruta a `app.py` tanto en modo desarrollo como dentro del binario."""
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    else:
        base = Path(__file__).resolve().parent.parent
    return base / "app.py"


def main() -> None:
    app_path = _resolve_app_path()
    if not app_path.exists():
        sys.stderr.write(f"No se encuentra app.py en {app_path}\n")
        sys.exit(2)

    # Configuración por defecto: sin telemetría, sin abrir el navegador automáticamente
    # cuando el usuario ya está en el binario doble-clic (lo abre el propio launcher).
    os.environ.setdefault("STREAMLIT_BROWSER_GATHER_USAGE_STATS", "false")
    os.environ.setdefault("STREAMLIT_SERVER_HEADLESS", "false")

    # Import diferido para que PyInstaller incluya streamlit como dependencia.
    from streamlit.web import bootstrap

    bootstrap.run(str(app_path), is_hello=False, args=[], flag_options={})


if __name__ == "__main__":
    main()
