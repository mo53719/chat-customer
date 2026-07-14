@echo off
cd /d "%~dp0"

echo ============================================
echo   Chat Customer System Startup
echo ============================================
echo.

echo [0] Cleaning up old processes on port 8001
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8001.*LISTENING"') do taskkill /PID %%a /F >nul 2>&1

if exist "tools\qdrant\qdrant.exe" (
    echo [0.1] Cleaning up old processes on port 6333
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":6333.*LISTENING"') do taskkill /PID %%a /F >nul 2>&1
    echo [1] Starting Qdrant - port 6333
    start "Chat-Qdrant" /D "%~dp0tools\qdrant" cmd /k qdrant.exe
)

echo [2] Starting backend (port 8001)
start "Chat-Backend" /D "%~dp0" cmd /k "env\Scripts\activate && python -m uvicorn app.main:app --host 0.0.0.0 --port 8001"

echo [3] Starting frontend (port 5173)
start "Chat-Frontend" /D "%~dp0frontend" cmd /k "npm run dev"

echo.
echo [4] Waiting for backend to be ready

:wait_backend
timeout /t 3 /nobreak >nul
env\Scripts\python.exe -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/health', timeout=2)" >nul 2>&1
if errorlevel 1 (
    echo Waiting for backend
    goto wait_backend
)

echo.
echo [5] Waiting for Qdrant to be ready

:wait_qdrant
timeout /t 2 /nobreak >nul
env\Scripts\python.exe -c "import urllib.request; urllib.request.urlopen('http://localhost:6333/', timeout=2)" >nul 2>&1
if errorlevel 1 (
    echo Waiting for Qdrant
    goto wait_qdrant
)

echo.
echo ============================================
echo   All services ready
echo   Backend:  http://localhost:8001
echo   Frontend: http://localhost:5173
echo ============================================
echo.
echo Opening browser
start http://localhost:5173

echo All done. This window will close automatically.
timeout /t 3 /nobreak >nul
exit