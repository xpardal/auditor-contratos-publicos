#!/usr/bin/env bash
# =============================================================================
# Auditor de Contratos Públicos · Universidade de Santiago de Compostela
# Lanzador: Linux, instalación de dependencias y arranque de Streamlit.
# Autores: Xoán Xosé Pardal Pérez; Alberto Quian (apoyo metodológico y técnico).
# Esta aplicación es parte de los proyectos de I+D+i: PID2024-156034OB-C22 y XornalIA (PDC2025-166024-I00).
# Licencia: MIT (https://opensource.org/license/mit).
# SPDX-License-Identifier: MIT
# =============================================================================

# =============================================================================
# Launcher Linux — Auditor de Contratos Públicos
# =============================================================================
# Hazlo ejecutable una vez:  chmod +x launch_linux.sh
# Después doble clic en GNOME/KDE → "Ejecutar" / "Run".
# =============================================================================
set -e

cd "$(dirname "$0")"

echo "🐧  Auditor de Contratos Públicos — Linux"
echo "==========================================="
echo

PY="${PYTHON:-}"
is_valid_python() {
  "$1" - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info >= (3, 10) else 1)
PY
}

if [ -n "$PY" ] && ! is_valid_python "$PY"; then
  PY=""
fi

if [ -z "$PY" ]; then
  for cand in python3.13 python3.12 python3.11 python3.10 python3; do
    if command -v "$cand" >/dev/null 2>&1 && is_valid_python "$cand"; then
      PY="$cand"; break
    fi
  done
fi

if [ -z "$PY" ]; then
  echo "❌ No se encontró Python 3.10+."
  echo "   Debian/Ubuntu:   sudo apt install python3 python3-venv python3-pip"
  echo "   Fedora:          sudo dnf install python3 python3-virtualenv"
  echo "   Arch:            sudo pacman -S python python-virtualenv"
  read -r -p "Pulsa Enter para cerrar…" _
  exit 1
fi

VER=$("$PY" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "✅ Python $VER detectado ($PY)"

if [ -d ".venv" ] && ! .venv/bin/python - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info >= (3, 10) else 1)
PY
then
  echo "♻️  Entorno virtual antiguo detectado; recreándolo con Python $VER…"
  rm -rf .venv
fi

if [ ! -d ".venv" ]; then
  echo "📦  Creando entorno virtual…"
  "$PY" -m venv .venv
fi

echo "📚  Comprobando dependencias…"
.venv/bin/python -m pip install -q --upgrade pip
.venv/bin/python -m pip install -q -r requirements.txt

echo "🧩  Comprobando conversor opcional .accdb…"
if command -v mdb-tables >/dev/null 2>&1 && command -v mdb-export >/dev/null 2>&1; then
  echo "✅  mdbtools detectado: la conversión .accdb → CSV estará disponible."
else
  echo "ℹ️   Para convertir .accdb directamente necesitas mdbtools."
  echo "     Debian/Ubuntu: sudo apt update && sudo apt install mdbtools"
  echo "     Fedora:        sudo dnf install mdbtools"
  echo "     La app seguirá funcionando con PLACSP, CSV, Excel y PDF."
fi

PORT=$(.venv/bin/python - <<'PY'
import socket

for port in range(8501, 8521):
  with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    if sock.connect_ex(("127.0.0.1", port)) != 0:
      print(port)
      break
else:
  print(0)
PY
)
if [ "$PORT" = "0" ]; then
  echo "❌ No se encontró un puerto libre entre 8501 y 8520."
  read -r -p "Pulsa Enter para cerrar…" _
  exit 1
fi

echo
echo "🚀  Abriendo la app en tu navegador (http://localhost:$PORT)…"
echo "    Para detenerla: cierra esta ventana o pulsa Ctrl+C."
echo
sleep 1
xdg-open "http://localhost:$PORT" 2>/dev/null || true
exec .venv/bin/streamlit run app.py --server.port "$PORT" --server.headless true --browser.gatherUsageStats false
