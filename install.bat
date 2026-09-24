@echo off
TITLE Quick Panel Windows Installer
echo =======================================================
echo  Quick Panel - Windows Double-Click Installer
echo =======================================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install-windows.ps1"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Installation encountered an error.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [OK] Installed successfully! You can close this window.
pause
