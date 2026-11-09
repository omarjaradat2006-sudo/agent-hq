@echo off
REM Adds a Windows Task Scheduler entry that starts the trading bot 1 minute after you log in.
REM Needs one "Yes" on the admin prompt.
net session >nul 2>&1
if not "%errorlevel%"=="0" (
  powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -ArgumentList '%USERNAME%' -Verb RunAs"
  exit /b
)
set "TARGET_USER=%~1"
if "%TARGET_USER%"=="" set "TARGET_USER=%USERNAME%"
schtasks /Create /F /TN "AgentHQ Trading Bot" /SC ONLOGON /DELAY 0001:00 /RL LIMITED /IT /RU "%TARGET_USER%" /TR "\"%~dp0start_trading_bot.bat\""
if "%errorlevel%"=="0" (
  echo.
  echo Done: the trading bot now starts by itself every time you log in.
  echo To remove it later: run remove_autostart.bat
) else (
  echo Could not create the scheduled task.
)
pause
