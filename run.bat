@echo off
cd /d "%~dp0"
set "ROOT=%cd%"

echo ============================================
echo  Sonobuoy Acoustic Analysis System
echo ============================================
echo.

:: ── Check Python ──
where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: python is not installed or not in PATH.
    goto :fail
)
echo [OK] Python found.

:: ── Check Node.js / npm ──
where npm >nul 2>&1
if not errorlevel 1 goto :node_ok
where npm.cmd >nul 2>&1
if not errorlevel 1 goto :node_ok

echo Node.js is not installed. Installing now...
echo.
echo Downloading Node.js LTS installer...
powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://nodejs.org/dist/v22.16.0/node-v22.16.0-x64.msi' -OutFile '%TEMP%\node-install.msi'"
if errorlevel 1 (
    echo ERROR: Failed to download Node.js installer.
    echo Please install manually from https://nodejs.org/
    goto :fail
)

echo Installing Node.js (this may ask for admin permission)...
msiexec /i "%TEMP%\node-install.msi" /qb
if errorlevel 1 (
    echo ERROR: Node.js installation failed.
    echo Please install manually from https://nodejs.org/
    goto :fail
)

del "%TEMP%\node-install.msi" >nul 2>&1
set "PATH=%ProgramFiles%\nodejs;%PATH%"

where npm >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js installed but npm not found in PATH.
    echo Please close this window, open a new terminal, and run run.bat again.
    goto :fail
)
echo Node.js installed successfully.
echo.

:node_ok
echo [OK] Node.js / npm found.
echo.

:: ── Install backend dependencies ──
echo [1/3] Installing backend dependencies...
cd /d "%ROOT%\backend"
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo ERROR: Failed to install backend dependencies.
    goto :fail
)
echo      Backend dependencies ready.

:: ── Install frontend dependencies ──
echo [2/3] Installing frontend dependencies...
cd /d "%ROOT%\frontend"
call npm install --legacy-peer-deps
if errorlevel 1 (
    echo ERROR: Failed to install frontend dependencies.
    goto :fail
)
echo      Frontend dependencies ready.

:: ── Start servers ──
echo.
echo [3/3] Starting servers...
echo.
echo  Backend  : http://localhost:8000
echo  Frontend : http://localhost:3000
echo.
echo  Close this window to stop the frontend.
echo  Close the minimized "Sonobuoy Backend" window to stop the backend.
echo ============================================
echo.

cd /d "%ROOT%\backend"
start "Sonobuoy Backend" /min python server.py

timeout /t 4 /nobreak >nul

cd /d "%ROOT%\frontend"
set REACT_APP_API_URL=http://localhost:8000/api
echo Starting frontend...
call npm start

echo.
echo Frontend stopped.
goto :done

:fail
echo.
echo ============================================
echo  Something went wrong. See errors above.
echo ============================================

:done
pause