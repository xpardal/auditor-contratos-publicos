@echo off
REM =============================================================================
REM Auditor de Contratos Publicos · Universidade de Santiago de Compostela
REM Lanzador: Windows, instalacion de dependencias y arranque de Streamlit.
REM Autores: Xoan Xose Pardal Perez; Alberto Quian (apoyo metodologico y tecnico).
REM Esta aplicacion es parte de los proyectos de I+D+i:
REM - Inteligencia artificial en medios digitales en Espana: efectos y roles (PID2024-156034OB-C22).
REM - XornalIA: Desarrollo, validacion y transferencia de una plataforma integradora de soluciones de inteligencia artificial generativa para medios de comunicacion (PDC2025-166024-I00).
REM Licencia: MIT (https://opensource.org/license/mit).
REM SPDX-License-Identifier: MIT
REM =============================================================================

REM =============================================================================
REM Launcher Windows -- Auditor de Contratos Publicos
REM =============================================================================
REM Doble clic en este archivo desde el Explorador. Si Windows Defender lo
REM bloquea: "Mas informacion" -> "Ejecutar de todas formas".
REM =============================================================================
setlocal EnableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo  Auditor de Contratos Publicos -- Windows
echo  =========================================
echo.

REM 1. Detectar Python 3.10+
set "PY="
where py >nul 2>&1
if not errorlevel 1 (
    for /f "delims=" %%v in ('py -3 -c "import sys; print(sys.version_info >= (3,10))"') do (
        if "%%v"=="True" set "PY=py -3"
    )
)

if "%PY%"=="" (
    where python >nul 2>&1
    if not errorlevel 1 (
        for /f "delims=" %%v in ('python -c "import sys; print(sys.version_info >= (3,10))"') do (
            if "%%v"=="True" set "PY=python"
        )
    )
)

if "%PY%"=="" (
    echo  [ERROR] No se encontro Python 3.10 o superior.
    echo         Descargalo en  https://www.python.org/downloads/
    echo         IMPORTANTE: marca la casilla "Add Python to PATH" durante la instalacion.
    pause
    exit /b 1
)

echo  [OK] Python detectado:
%PY% --version

REM 2. Crear entorno virtual si no existe
if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)"
    if errorlevel 1 (
        echo  Entorno virtual antiguo detectado. Recreandolo con Python 3.10+...
        rmdir /s /q .venv
    )
)

if not exist ".venv" (
    echo  Creando entorno virtual...
    %PY% -m venv .venv
    if errorlevel 1 goto :error
)

REM 3. Instalar dependencias
echo  Comprobando dependencias...
call .venv\Scripts\python.exe -m pip install -q --upgrade pip
call .venv\Scripts\python.exe -m pip install -q -r requirements.txt
if errorlevel 1 goto :error

echo  Comprobando conversor opcional .accdb...
echo  En Windows no se instala mdbtools. Para usar Liquidaciones2024.accdb,
echo  abre el archivo en Microsoft Access o LibreOffice Base y exporta
echo  tb_economica y tb_inventario como CSV. La app analizara esos CSV igual.

REM 4. Lanzar app y abrir navegador
for /f "delims=" %%p in ('.venv\Scripts\python.exe -c "import socket; print(next((p for p in range(8501, 8521) if socket.socket().connect_ex(('127.0.0.1', p)) != 0), 0))"') do set "PORT=%%p"
if "%PORT%"=="0" (
    echo  [ERROR] No se encontro un puerto libre entre 8501 y 8520.
    pause
    exit /b 1
)

echo.
echo  Abriendo la app en tu navegador (http://localhost:%PORT%)...
echo  Para detenerla: cierra esta ventana o pulsa Ctrl+C.
echo.
start "" "http://localhost:%PORT%"
call .venv\Scripts\streamlit.exe run app.py --server.port %PORT% --server.headless true --browser.gatherUsageStats false
goto :eof

:error
echo.
echo  [ERROR] Algo fallo durante la instalacion. Revisa el mensaje de arriba.
pause
exit /b 1
