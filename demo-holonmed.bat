@echo off
rem Demostracion publica de HolonMed: LM Studio + backend en modo demo + tutorial.
rem Uso: doble clic, o  demo-holonmed.bat [--puerto 8765] [--modelo ID]
setlocal
chcp 65001 >nul
title HolonMed - demostracion
cd /d "%~dp0backend"

set "MODELO=gemma-4-e4b-uncensored-hauhaucs-aggressive"
set "PYTHONUTF8=1"

rem --- Python con las dependencias: HOLONMED_PYTHON, el .venv de aqui,
rem     el .venv del checkout principal (si esto es un worktree) o el del PATH.
set "PY=%HOLONMED_PYTHON%"
if not defined PY if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"
if not defined PY for /f "delims=" %%G in ('git rev-parse --path-format^=absolute --git-common-dir 2^>nul') do (
    if exist "%%G\..\backend\.venv\Scripts\python.exe" set "PY=%%G\..\backend\.venv\Scripts\python.exe"
)
if not defined PY set "PY=python"

rem --- LM Studio: encender el servidor y cargar el modelo si hace falta.
set "LMS=lms"
where lms >nul 2>nul || set "LMS=%USERPROFILE%\.lmstudio\bin\lms.exe"
if not "%LMS%"=="lms" if not exist "%LMS%" goto sin_lms
echo [1/3] Encendiendo el servidor de LM Studio en el puerto 1234...
call "%LMS%" server start --port 1234
echo [2/3] Comprobando que el modelo este cargado...
call "%LMS%" ps 2>nul | findstr /i /c:"%MODELO%" >nul
if errorlevel 1 call "%LMS%" load %MODELO% -y
goto arrancar

:sin_lms
echo No encuentro "lms". Abre LM Studio, enciende el servidor en el puerto 1234 y carga %MODELO%.

:arrancar
echo [3/3] Arrancando HolonMed en modo demostracion...
"%PY%" scripts\demo.py --abrir %*
if errorlevel 1 (
    echo.
    echo La demo no arranco o termino con error. Lee el mensaje de arriba.
    pause
    exit /b 1
)
