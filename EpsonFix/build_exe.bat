@echo off
setlocal
cd /d "%~dp0"

echo [1/3] Installing dependencies...
python -m pip install -r requirements.txt
python -m pip install pyinstaller

echo [2/3] Building EpsonFix.exe...
pyinstaller --noconfirm --onefile --windowed --name EpsonFix main.py

echo [3/3] Done.
echo EXE generated at: dist\EpsonFix.exe
pause
