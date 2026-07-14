@echo off
cd /d "%~dp0"
echo ============================================
echo   Chat Customer - One-time Setup
echo ============================================
echo.
echo This script downloads Qdrant vector database
echo for local development and testing.
echo.
echo Download size: ~36MB, requires internet.
echo.
echo Press any key to start, or close this window to cancel.
pause >nul
echo.

set QDRANT_VER=1.18.2
set WEBUI_VER=0.2.14
set QDRANT_DIR=tools\qdrant

if not exist "%QDRANT_DIR%" mkdir "%QDRANT_DIR%"

:: ============================================================
::  Step 1: Download Qdrant binary
:: ============================================================
echo [1/2] Downloading Qdrant v%QDRANT_VER% (~29MB)...
echo.
powershell -Command "$ProgressPreference='SilentlyContinue'; try { Invoke-WebRequest -Uri 'https://github.com/qdrant/qdrant/releases/download/v%QDRANT_VER%/qdrant-x86_64-pc-windows-msvc.zip' -OutFile '%QDRANT_DIR%\qdrant.zip' -ErrorAction Stop } catch { exit 1 }"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Failed to download Qdrant from GitHub.
    echo Network may be restricted in your region.
    goto :manual
)

echo Extracting qdrant.exe...
powershell -Command "Expand-Archive -Path '%QDRANT_DIR%\qdrant.zip' -DestinationPath '%QDRANT_DIR%' -Force"
del "%QDRANT_DIR%\qdrant.zip"
echo Done.
echo.

:: ============================================================
::  Step 2: Download Web UI Dashboard
:: ============================================================
echo [2/2] Downloading Qdrant Dashboard v%WEBUI_VER% (~7MB)...
echo This provides the visual dashboard at http://localhost:6333/dashboard
echo.
powershell -Command "$ProgressPreference='SilentlyContinue'; try { Invoke-WebRequest -Uri 'https://github.com/qdrant/qdrant-web-ui/releases/download/v%WEBUI_VER%/dist-qdrant.zip' -OutFile '%QDRANT_DIR%\webui.zip' -ErrorAction Stop } catch { exit 1 }"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [WARNING] Failed to download dashboard.
    echo Qdrant API will still work, but http://localhost:6333/dashboard won't be available.
    goto :done
)

echo Extracting dashboard files...
if exist "%QDRANT_DIR%\static" rmdir /s /q "%QDRANT_DIR%\static"
powershell -Command "Expand-Archive -Path '%QDRANT_DIR%\webui.zip' -DestinationPath '%QDRANT_DIR%\_webui_tmp' -Force"
if exist "%QDRANT_DIR%\_webui_tmp\dist" (
    move "%QDRANT_DIR%\_webui_tmp\dist" "%QDRANT_DIR%\static" >nul
) else (
    move "%QDRANT_DIR%\_webui_tmp" "%QDRANT_DIR%\static" >nul
)
del "%QDRANT_DIR%\webui.zip" 2>nul
rmdir /s /q "%QDRANT_DIR%\_webui_tmp" 2>nul
echo Done.
echo.

:done
echo ============================================
echo   Setup complete!
echo.
echo   Run start.bat to launch the system.
echo   Dashboard: http://localhost:6333/dashboard
echo ============================================
echo.
pause
exit /b 0

:manual
echo.
echo ============================================
echo   Manual Download Instructions
echo ============================================
echo.
echo 1. Download Qdrant v%QDRANT_VER%:
echo    https://github.com/qdrant/qdrant/releases/tag/v%QDRANT_VER%
echo    File: qdrant-x86_64-pc-windows-msvc.zip
echo    Extract qdrant.exe to: %QDRANT_DIR%\
echo.
echo 2. Download Dashboard v%WEBUI_VER% (optional):
echo    https://github.com/qdrant/qdrant-web-ui/releases/tag/v%WEBUI_VER%
echo    File: dist-qdrant.zip
echo    Extract dist/ folder contents to: %QDRANT_DIR%\static\
echo.
pause
exit /b 1