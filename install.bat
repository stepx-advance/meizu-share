@echo off
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel% equ 0 (
    py -3 tools\quick_setup.py %*
) else (
    python tools\quick_setup.py %*
)
set "setup_result=%errorlevel%"
echo.
pause
exit /b %setup_result%
