@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
  py -3 tools\build.py
) else (
  python tools\build.py
)
if errorlevel 1 (
  echo [ERROR] MineNightAC build failed.
  pause
  exit /b 1
)
echo [SUCCESS] Completed build outputs are in dist.
pause
