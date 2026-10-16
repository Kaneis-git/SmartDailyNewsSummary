@echo off
setlocal
cd /d "%~dp0"
title AI Daily News Assistant
py -3.12 -c "import sys; sys.exit(sys.version_info[:2] != (3, 12))" >nul 2>nul
if not errorlevel 1 goto use_py
python -c "import sys; sys.exit(sys.version_info[:2] != (3, 12))" >nul 2>nul
if not errorlevel 1 goto use_python
echo Python 3.12 was not found.
echo Install Python 3.12 with the Python Launcher, then run this file again.
echo Download: https://www.python.org/downloads/release/python-31210/
echo See docs\WINDOWS_LOCAL_START.md for installation steps.
pause
exit /b 1

:use_py
py -3.12 scripts\run_local.py
goto done

:use_python
python scripts\run_local.py

:done
set "news_exit_code=%errorlevel%"
if not "%news_exit_code%"=="0" pause
exit /b %news_exit_code%
