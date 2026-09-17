@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" Launcher.py
    goto :done
)
py -3 -c "import sys" >nul 2>&1
if not errorlevel 1 (
    py -3 Launcher.py
    goto :done
)
python -c "import sys" >nul 2>&1
if not errorlevel 1 (
    python Launcher.py
    goto :done
)
echo Install Python 3.10 or newer from https://www.python.org/downloads/
:done
pause
