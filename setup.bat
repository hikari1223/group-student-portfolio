@echo off
REM ============================================================
REM  Group Student Portfolio - one-time setup for a new computer
REM
REM  Run this the first time you open the project on a new PC
REM  or laptop, then delete it if you do not need it.
REM
REM    setup.bat
REM ============================================================

echo.
echo  Setting up the Group Student Portfolio...
echo.

REM --- 1. Check that Python is installed -------------------------------
python --version >nul 2>&1
if errorlevel 1 (
    echo  [X] Python was not found on this computer.
    echo.
    echo      Install Python 3.10 or newer from https://python.org
    echo      and tick "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo  [1/4] Found Python %PYVER%

REM --- 2. Create the virtual environment -------------------------------
if exist "venv\Scripts\python.exe" (
    echo  [2/4] Virtual environment already exists - skipping
) else (
    echo  [2/4] Creating the virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo  [X] Could not create the virtual environment.
        pause
        exit /b 1
    )
)

REM --- 3. Install the packages ----------------------------------------
echo  [3/4] Installing the packages Django needs...
venv\Scripts\python.exe -m pip install --quiet --upgrade pip
venv\Scripts\python.exe -m pip install --quiet -r requirements.txt
if errorlevel 1 (
    echo  [X] Could not install the packages. Check your internet connection.
    pause
    exit /b 1
)

REM --- 4. Check that the project is healthy ----------------------------
echo  [4/4] Checking the project...
venv\Scripts\python.exe manage.py check
echo.
venv\Scripts\python.exe manage.py check >nul 2>&1
if errorlevel 1 (
    echo  [!] Django reported a problem. Run:
    echo        venv\Scripts\python.exe manage.py check
    echo.
) else (
    echo  All good. The project is ready.
)

echo.
echo  ----------------------------------------------------------
echo   Start the site:   venv\Scripts\python.exe manage.py runserver
echo   Then open:        http://127.0.0.1:8000
echo  ----------------------------------------------------------
echo.
pause
