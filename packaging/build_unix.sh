#!/usr/bin/env bash
# =============================================================================
# Auditor de Contratos Públicos · Universidade de Santiago de Compostela
# Construye el binario distribuible para macOS o Linux usando PyInstaller.
# Ejecutar desde la raíz del repositorio.
#
# Autores: Xoán Xosé Pardal Pérez; Alberto Quian (apoyo metodológico y técnico).
# Esta aplicacion es parte del proyecto de I+D+i:
# - XornalIA: Desarrollo, validacion y transferencia de una plataforma integradora de soluciones de inteligencia artificial generativa para medios de comunicacion (PDC2025-166024-I00).
# Licencia: MIT (https://opensource.org/license/mit).
# SPDX-License-Identifier: MIT
# =============================================================================
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt

rm -rf build dist
pyinstaller packaging/auditor.spec --clean --noconfirm

echo
echo "Binario generado en: dist/auditor-contratos/"
echo "Lanzamiento manual : ./dist/auditor-contratos/auditor-contratos"
