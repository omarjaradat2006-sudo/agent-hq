@echo off
title Agent HQ Trading Bot - backtest
cd /d "%~dp0..\.."
echo Running Omar's rules over the last 30 days of past news and prices. Takes 10-40 minutes.
"trading_bot\.venv\Scripts\python.exe" -m trading_bot.backtest 30
echo.
echo Results are on the Trading floor in Agent HQ (Backtest tab).
pause
