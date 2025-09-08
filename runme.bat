@echo off
setlocal

REM Runme installer for Blox_Fruit_Fishing
REM - checks for Python 3.10+ (uses py launcher or python)
REM - if missing attempts to install via winget or download the official installer
REM - creates a venv, installs requirements from requirements.txt
REM We'll write a helper installer script and open it in a new CMD window so the commands are visible
set "INSTALLER=%TEMP%\bf_installer.cmd"

powershell -NoProfile -Command "@'
@echo off
setlocal

echo Checking for Python 3...

:: Try py launcher first (recommended on Windows)
py -3 --version >nul 2>&1
if %ERRORLEVEL%==0 (
    for /f \"tokens=2 delims= \" %%v in ('py -3 --version') do set PYVER=%%v
    set PYLAUNCHER=py -3
) else (
    python --version >nul 2>&1
    if %ERRORLEVEL%==0 (
        for /f \"tokens=2 delims= \" %%v in ('python --version') do set PYVER=%%v
        set PYLAUNCHER=python
    ) else (
        set PYLAUNCHER=
    )
)

if defined PYLAUNCHER (
    echo Found Python: %PYLAUNCHER% %PYVER%
    goto :setup_venv
) else (
    echo Python not found.
)

echo Please wait while we get things ready for you...

:: Try installing with winget if available
winget --version >nul 2>&1
if %ERRORLEVEL%==0 (
    echo Installing Python via winget...
    winget install --id Python.Python.3 --silent --accept-package-agreements --accept-source-agreements
    if %ERRORLEVEL%==0 (
        echo Python installed via winget.
        goto :verify_python
    ) else (
        echo winget failed to install Python.
    )
) else (
    echo winget not available, will attempt direct download.
)

:download_python
echo Downloading Python installer (standby)...
set PY_INSTALLER=%TEMP%\python-installer.exe
powershell -Command "try { (New-Object System.Net.WebClient).DownloadFile('https://www.python.org/ftp/python/3.12.2/python-3.12.2-amd64.exe', '%PY_INSTALLER%'); exit 0 } catch { exit 1 }"
if %ERRORLEVEL%==0 (
    echo Running Python installer (may prompt for elevation)...
    start /wait "" "%PY_INSTALLER%" /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
    if %ERRORLEVEL%==0 (
        echo Installer finished.
        goto :verify_python
    ) else (
        echo Installer failed or requires elevation. Please run the installer manually: %PY_INSTALLER%
        goto :fail
    )
) else (
    echo Failed to download Python installer. Please install Python 3.10+ manually from https://www.python.org/downloads/
    goto :fail
)

:verify_python
echo Verifying Python installation...
py -3 --version >nul 2>&1
if %ERRORLEVEL%==0 (
    set PYLAUNCHER=py -3
    for /f \"tokens=2 delims= \" %%v in ('py -3 --version') do set PYVER=%%v
    echo Found Python: %PYLAUNCHER% %PYVER%
    goto :setup_venv
)
python --version >nul 2>&1
if %ERRORLEVEL%==0 (
    set PYLAUNCHER=python
    for /f \"tokens=2 delims= \" %%v in ('python --version') do set PYVER=%%v
    echo Found Python: %PYLAUNCHER% %PYVER%
    goto :setup_venv
)
echo Could not find Python after install. Please install Python 3.10+ manually and re-run this script.
goto :fail

:setup_venv
echo Creating virtual environment in .venv ...
%PYLAUNCHER% -m venv .venv
if %ERRORLEVEL% neq 0 (
    echo Failed to create virtual environment. Ensure Python installation is correct.
    goto :fail
)

echo Activating virtual environment and installing requirements...
call .venv\Scripts\activate.bat
if exist requirements.txt (
    pip install --upgrade pip
    pip install -r requirements.txt
) else (
    echo requirements.txt not found in repository root. Skipping pip install.
)

echo
echo Setup complete.
echo
set /p RUNMAIN=Would you like me to run Main.py now? (y/N) 
if /i "%RUNMAIN%"=="y" (
    echo Running Main.py...
    .venv\Scripts\python.exe Main.py
) else (
    echo Not running Main.py. You can run it later with: .venv\Scripts\python.exe Main.py
)

pause

:fail
echo Setup failed. Please fix the issues above and try again.
pause
'@ | Out-File -FilePath "%INSTALLER%" -Encoding ASCII -Force"

echo Opening installer in a new CMD window...
start "" cmd /k "%INSTALLER%"

exit /b 0
