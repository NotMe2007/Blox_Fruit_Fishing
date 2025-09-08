@echo off
setlocal

echo Installer for Blox_Fruit_Fishing
echo -----------------------------

echo Checking for Python (py then python)...
where py >nul 2>&1
if %ERRORLEVEL%==0 set PYLAUNCHER=py -3

where python >nul 2>&1
if %ERRORLEVEL%==0 if not defined PYLAUNCHER set PYLAUNCHER=python

if defined PYLAUNCHER (
    echo Found Python launcher: %PYLAUNCHER%
) else (
    echo Python not found on PATH.
    echo Trying to install with winget (if available)...
    where winget >nul 2>&1
    if %ERRORLEVEL%==0 (
        echo Installing Python via winget...
        winget install --id Python.Python.3 --silent --accept-package-agreements --accept-source-agreements
    ) else (
        echo winget not available; will try to download installer.
    )
    rem try to detect py/python again after possible winget install
    where py >nul 2>&1
    if %ERRORLEVEL%==0 set PYLAUNCHER=py -3
    where python >nul 2>&1
    if %ERRORLEVEL%==0 if not defined PYLAUNCHER set PYLAUNCHER=python
)

if not defined PYLAUNCHER (
    echo Attempting to download Python installer to %TEMP%...
    set PY_INSTALLER=%TEMP%\python-installer.exe
    certutil -urlcache -split -f "https://www.python.org/ftp/python/3.12.2/python-3.12.2-amd64.exe" "%PY_INSTALLER%" >nul 2>&1
    if exist "%PY_INSTALLER%" (
        echo Running installer (may require elevation)...
        start /wait "" "%PY_INSTALLER%" /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
    ) else (
        echo Failed to download the installer automatically.
        echo Please install Python 3.10+ from https://www.python.org/downloads/ and re-run this script.
        pause
        exit /b 1
    )
    rem check again
    where py >nul 2>&1
    if %ERRORLEVEL%==0 set PYLAUNCHER=py -3
    where python >nul 2>&1
    if %ERRORLEVEL%==0 if not defined PYLAUNCHER set PYLAUNCHER=python
)

if not defined PYLAUNCHER (
    echo Python still not found. Aborting.
    pause
    exit /b 1
)

echo Creating virtual environment (.venv)...
%PYLAUNCHER% -m venv .venv
if %ERRORLEVEL% neq 0 (
    echo Failed to create virtual environment. Ensure Python is correctly installed.
    pause
    exit /b 1
)

echo Activating venv and installing requirements...
call .\venv\Scripts\activate.bat
if exist requirements.txt (
    pip install --upgrade pip
    pip install -r requirements.txt
) else (
    echo requirements.txt not found; skipping pip install.
)

echo.
echo Setup complete.
echo.
set /p RUNMAIN=Would you like me to run Main.py now? (y/N) 
if /i "%RUNMAIN%"=="y" (
    echo Running Main.py...
    .\venv\Scripts\python.exe Main.py
)

echo Done. Closing window.
exit /b 0
