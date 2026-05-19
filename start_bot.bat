@echo off
title RandAI Telegram Bot

cd /d "%~dp0"

:START

cls

echo =====================================
echo        RandAI Telegram Bot
echo =====================================
echo.
echo Starting bot...
echo.

python bot.py

echo.
echo =====================================
echo Bot stopped or crashed.
echo Restarting in 5 seconds...
echo =====================================

timeout /t 5 >nul

goto START