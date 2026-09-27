@echo off
rem One-click launcher: installs what's needed, builds the UI, starts Vectron, opens the browser.
cd /d "%~dp0backend"
where uv >nul 2>nul
if errorlevel 1 (
  echo uv is not installed. In PowerShell run:
  echo   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  echo then run this again.
  pause
  exit /b 1
)
uv sync --quiet
uv run vectron start
pause
