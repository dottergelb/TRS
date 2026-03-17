@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_EXE="

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -V >nul 2>&1
    if not errorlevel 1 set "PYTHON_EXE=.venv\Scripts\python.exe"
)

if not defined PYTHON_EXE if exist ".venv312\Scripts\python.exe" (
    ".venv312\Scripts\python.exe" -V >nul 2>&1
    if not errorlevel 1 set "PYTHON_EXE=.venv312\Scripts\python.exe"
)

if not defined PYTHON_EXE (
    python -V >nul 2>&1
    if not errorlevel 1 set "PYTHON_EXE=python"
)

if not defined PYTHON_EXE (
    echo Python not found. Install Python or recreate virtual environment.
    pause
    exit /b 1
)

"%PYTHON_EXE%" manage.py runserver

endlocal
