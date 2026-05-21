@echo off
setlocal
cd /d "%~dp0"

if exist "dist\EpsonFix.exe" (
  powershell -Command "Start-Process -FilePath '%cd%\dist\EpsonFix.exe' -Verb RunAs"
) else (
  echo No se encontro dist\EpsonFix.exe
  echo Primero ejecuta build_exe.bat
  pause
)
