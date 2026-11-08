@echo off
title Helmet Detection - PC Demo Simulator
cd /d "%~dp0"
echo =========================================================================
echo   Starting Helmet Detection - PC Demo Simulator...
echo =========================================================================
echo.

python pc_demo.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Program closed with error code %ERRORLEVEL%.
) else (
    echo.
    echo [INFO] Program closed normally.
)
echo.
pause
