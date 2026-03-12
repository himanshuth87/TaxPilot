@echo off
echo ================================================
echo           🚀 STARTING TAXPILOT
echo ================================================
echo.
echo Installing dependencies...
pip install -r requirements.txt
echo.
echo Launching Hub...
python main.py
pause
