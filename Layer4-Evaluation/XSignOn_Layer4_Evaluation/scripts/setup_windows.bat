@echo off
cd /d %~dp0\..
python -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
if /I "%1"=="full" (
  python -m pip install -r requirements-full.txt
) else (
  python -m pip install -r requirements-core.txt
)
echo.
echo Setup complete. Start with scripts\start_windows.bat
pause
