@echo off
REM Agent HQ paper-trading bot. Double-click to start. Close this window to stop it.
REM Stop-losses live on Alpaca's servers, so open trades stay protected while this is closed.
title Agent HQ Trading Bot (PAPER)
cd /d "%~dp0..\.."
if not exist "trading_bot\.venv\Scripts\python.exe" (
  echo Run trading_bot\windows\setup.bat first.
  pause
  exit /b 1
)
:loop
"trading_bot\.venv\Scripts\python.exe" -m trading_bot.bot run
if "%errorlevel%"=="3" (
  timeout /t 8 >nul
  exit /b 0
)
echo.
echo The bot stopped (code %errorlevel%). Restarting in 60 seconds. Close this window to stop for good.
timeout /t 60 /nobreak >nul
goto loop
