@echo off
REM =============================================================================
REM Auditor de Contratos Publicos . Universidade de Santiago de Compostela
REM Construye el binario distribuible para Windows usando PyInstaller.
REM Ejecutar desde la raiz del repositorio.
REM
REM Autores: Xoan Xose Pardal Perez; Alberto Quian (apoyo metodologico y tecnico).
REM Esta aplicacion es parte del proyecto de I+D+i:
REM - XornalIA: Desarrollo, validacion y transferencia de una plataforma integradora de soluciones de inteligencia artificial generativa para medios de comunicacion (PDC2025-166024-I00).
REM Licencia: MIT (https://opensource.org/license/mit).
REM SPDX-License-Identifier: MIT
REM =============================================================================
setlocal

cd /d "%~dp0\.."

if not exist .venv (
    py -3 -m venv .venv
)
call .venv\Scripts\activate.bat

python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt

if exist build rmdir /s /q build
if exist dist  rmdir /s /q dist

pyinstaller packaging\auditor.spec --clean --noconfirm

echo.
echo Binario generado en: dist\auditor-contratos\
echo Lanzamiento manual : dist\auditor-contratos\auditor-contratos.exe
endlocal
