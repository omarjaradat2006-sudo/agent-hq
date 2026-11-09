@echo off
cd /d "%~dp0..\.."
"trading_bot\.venv\Scripts\python.exe" -m trading_bot.bot check
pause
