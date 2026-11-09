@echo off
REM One-time setup for the Agent HQ paper-trading bot. Every prompt that needs you comes first,
REM then it installs everything by itself.
title Agent HQ Trading Bot setup
cd /d "%~dp0..\.."
echo.
echo ===== Agent HQ paper-trading bot setup (PAPER money only) =====
echo Everything that needs a click from you happens in steps 1-4. After that you can walk away.
echo.

REM ---- 1. autostart (one admin "Yes")
set /p AUTO="1/4  Start the bot automatically when you log in? (Y/N): "
if /i "%AUTO%"=="Y" call "%~dp0install_autostart.bat"

REM ---- 2. GitHub login (used only to save results for the Trading tab)
echo.
echo 2/4  Checking you can save results to GitHub (a login window may open: approve it)...
git push --dry-run -q origin HEAD:main
if errorlevel 1 echo      GitHub save not working yet. The bot still trades; results just won't show on the site.

REM ---- 3. keys (stay on this laptop)
echo.
if not exist "trading_bot\.env" copy "trading_bot\.env.example" "trading_bot\.env" >nul
echo 3/4  Notepad is opening trading_bot\.env. Paste your Alpaca PAPER keys and your Gemini key,
echo      save, close Notepad, then come back here.
notepad "trading_bot\.env"
pause

REM ---- 4. X / Reddit through Agent Reach (secondary accounts)
echo.
set /p REACH="4/4  Set up X + Reddit reading with Agent Reach? (Y/N): "
if /i not "%REACH%"=="Y" goto install
where uv >nul 2>&1 || powershell -ExecutionPolicy ByPass -NoProfile -c "irm https://astral.sh/uv/install.ps1 | iex"
set "PATH=%USERPROFILE%\.local\bin;%PATH%"
where agent-reach >nul 2>&1 || uv tool install https://github.com/Panniantong/Agent-Reach/releases/latest/download/agent-reach.zip
call agent-reach setup
call agent-reach add twitter
call agent-reach add reddit
echo.
echo  IMPORTANT: a browser window opens for X. Sign in with your SECONDARY X account (not your main one),
echo  then close that window. Then the same for Reddit with your SECONDARY Reddit account.
pause
call agent-reach login twitter
pause
call agent-reach login reddit
pause

:install
echo.
echo ===== Installing (no more clicks needed, takes a few minutes) =====
set "PY="
for %%V in (3.12 3.13 3.11) do (
  if not defined PY ( py -%%V -c "import sys" >nul 2>&1 && set "PY=py -%%V" )
)
if not defined PY ( python -c "import sys; assert sys.version_info >= (3,11)" >nul 2>&1 && set "PY=python" )
if not defined PY (
  echo Python 3.11 or newer is needed. Install it from python.org, then run setup.bat again.
  pause
  exit /b 1
)
if not exist "trading_bot\.venv\Scripts\python.exe" %PY% -m venv "trading_bot\.venv"
"trading_bot\.venv\Scripts\python.exe" -m pip install -q --upgrade pip
"trading_bot\.venv\Scripts\python.exe" -m pip install -q -r "trading_bot\requirements.txt"
echo.
echo Halal screen + connection check:
"trading_bot\.venv\Scripts\python.exe" -m trading_bot.bot check
"trading_bot\.venv\Scripts\python.exe" -m trading_bot.bot universe
echo.
echo Setup finished.
echo  - Run the backtest:   trading_bot\windows\run_backtest.bat
echo  - Start the bot:      trading_bot\windows\start_trading_bot.bat
pause
