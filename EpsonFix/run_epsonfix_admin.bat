@echo off
setlocal
cd /d "%~dp0"

if exist "dist\EpsonFix.exe" (
  echo Ejecutando ejecutable compilado como Administrador...
  powershell -NoProfile -ExecutionPolicy Bypass -Command "$exe = Join-Path -LiteralPath (Get-Location) -ChildPath 'dist\EpsonFix.exe'; Start-Process -FilePath $exe -Verb RunAs"
) else (
  echo No se encontro dist\EpsonFix.exe.
  echo Ejecutando script de desarrollo python main.py como Administrador...
  powershell -NoProfile -ExecutionPolicy Bypass -Command "$cwd = (Get-Location).Path; Start-Process -FilePath 'python' -ArgumentList @('main.py') -WorkingDirectory $cwd -Verb RunAs"
)
