@echo off
REM X + Reddit reading (Agent Reach), installed inside the bot's own Python so Windows'
REM app-blocking policy doesn't stop it. Sign in with your SECONDARY accounts only.
title Agent HQ Trading Bot - X and Reddit setup
cd /d "%~dp0..\.."
set "PY=trading_bot\.venv\Scripts\python.exe"
if not exist "%PY%" (
  echo Run setup.bat first.
  pause
  exit /b 1
)
echo Installing Agent Reach into the bot (1-2 minutes)...
"%PY%" -m pip install -q https://github.com/Panniantong/Agent-Reach/releases/latest/download/agent-reach.zip
"%PY%" -m agent_reach.cli setup
"%PY%" -m agent_reach.cli add twitter
"%PY%" -m agent_reach.cli add reddit
echo.
echo A browser window opens for X. Sign in with your SECONDARY X account, then close that window.
pause
"%PY%" -m agent_reach.cli login twitter
echo.
echo Now Reddit. Sign in with your SECONDARY Reddit account, then close that window.
pause
"%PY%" -m agent_reach.cli login reddit
echo.
"%PY%" -m trading_bot.bot check
pause
