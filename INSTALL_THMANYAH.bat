@echo off
python scripts\install_thmanyah_fonts.py "Thmanyah-Font-Family(1).zip"
if errorlevel 1 pause & exit /b 1
echo Thmanyah font installed successfully.
pause
