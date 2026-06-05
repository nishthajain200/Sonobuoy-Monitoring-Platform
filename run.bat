@echo off
setlocal
cd /d "%~dp0"
set "ROOT=%~dp0"

echo ============================================
echo  Sonobuoy Acoustic Analysis System
echo ============================================
echo.

:: ── Install backend dependencies ──
echo [1/3] Installing backend dependencies...
cd /d "%ROOT%backend"
pip install -r requirements.txt --quiet
cd /d "%ROOT%"

:: ── Install frontend dependencies ──
echo [2/3] Installing frontend dependencies...
cd /d "%ROOT%frontend"
call npm install --legacy-peer-deps --silent
cd /d "%ROOT%"

:: ── Start backend server ──
echo [3/3] Starting servers...
echo.
echo  Backend  : http://localhost:8000
echo  Frontend : http://localhost:3000
echo.
echo  Press Ctrl+C in this window to stop both servers.
echo ============================================

start "Sonobuoy Backend" /min cmd /c "cd /d %ROOT%backend && python server.py"

:: Give backend a moment to start
timeout /t 3 /nobreak >nul

:: ── Start frontend dev server ──
cd /d "%ROOT%frontend"
set REACT_APP_API_URL=http://localhost:8000/api
call npm start