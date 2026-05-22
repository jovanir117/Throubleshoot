@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ============================================================
echo  EpsonFix ^| Build EXE
echo ============================================================

echo [1/4] Installing / updating dependencies...
python -m pip install -r requirements.txt --quiet
if errorlevel 1 ( echo ERROR: pip install failed & pause & exit /b 1 )

echo [2/4] Locating libusb DLL for USB detection...
set LIBUSB_DLL=
for /f "delims=" %%i in ('python -c "import libusb; print(libusb.dll._name)" 2^>nul') do set LIBUSB_DLL=%%i
if defined LIBUSB_DLL (
    echo   Found: !LIBUSB_DLL!
    set ADD_LIBUSB=--add-binary "!LIBUSB_DLL!;."
) else (
    echo   libusb DLL not found - USB hardware detection will be disabled in EXE
    set ADD_LIBUSB=
)

echo [3/4] Building EpsonFix.exe ...
python -m PyInstaller ^
  --noconfirm ^
  --onefile ^
  --windowed ^
  --uac-admin ^
  --name EpsonFix ^
  --icon "assets\icons\app_icon.ico" ^
  --add-data "knowledge;knowledge" ^
  --add-data "assets;assets" ^
  --collect-all customtkinter ^
  --hidden-import win32print ^
  --hidden-import win32api ^
  --hidden-import win32con ^
  --hidden-import win32security ^
  --hidden-import pythoncom ^
  --hidden-import pywintypes ^
  --hidden-import wmi ^
  --hidden-import usb ^
  --hidden-import usb.core ^
  --hidden-import usb.util ^
  --hidden-import usb.backend.libusb1 ^
  %ADD_LIBUSB% ^
  main.py

if errorlevel 1 ( echo ERROR: PyInstaller failed & pause & exit /b 1 )

echo [4/4] Done.
echo EXE: dist\EpsonFix.exe
echo.
echo Para publicar una release y activar auto-updates:
echo   gh release create vX.Y.Z dist\EpsonFix.exe --title "vX.Y.Z" --notes "..."
echo.
pause
