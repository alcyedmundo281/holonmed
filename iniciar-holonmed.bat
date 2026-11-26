@echo off
rem HolonMed en localhost: backend + frontend contra LM Studio.
rem Doble clic, o:  iniciar-holonmed.bat [--sin-navegador] [--puerto-backend N] [--puerto-frontend N]
rem Aqui solo se busca Python; el resto lo comprueba holonmed\lanzador.py.
setlocal
chcp 65001 >nul
title HolonMed
set "PYTHONUTF8=1"
cd /d "%~dp0backend"
if errorlevel 1 goto sin_carpeta

rem Python: HOLONMED_PYTHON, el .venv de aqui o, si esto es un worktree de
rem git, el .venv del checkout principal. No se usa el Python del sistema.
set "PY=%HOLONMED_PYTHON%"
if not defined PY if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"
if not defined PY for /f "delims=" %%G in ('git rev-parse --path-format^=absolute --git-common-dir 2^>nul') do (
    if exist "%%G\..\backend\.venv\Scripts\python.exe" set "PY=%%G\..\backend\.venv\Scripts\python.exe"
)
if not defined PY goto sin_python

"%PY%" -c "import holonmed.api.app"
if errorlevel 1 goto sin_dependencias

"%PY%" -m holonmed.lanzador %*
if errorlevel 1 goto fallo
exit /b 0

:sin_carpeta
echo No encuentro la carpeta backend junto a este archivo.
goto fallo

:sin_python
echo No se puede continuar: no encuentro el entorno de Python de HolonMed.
echo Crealo desde la carpeta backend del proyecto con estas dos ordenes:
echo     python -m venv .venv
echo     .venv\Scripts\pip install -e .
goto fallo

:sin_dependencias
echo.
echo No se puede continuar: el Python elegido no logra cargar HolonMed (motivo arriba).
echo Desde la carpeta backend, instala las dependencias en su entorno:
echo     .venv\Scripts\pip install -e .
goto fallo

:fallo
echo.
if not defined HOLONMED_SIN_PAUSA pause
exit /b 1
