@echo off
REM ═══════════════════════════════════════════════════════
REM  Wesco MRO Parser — Windows .exe Build Script
REM  Run this on a Windows machine with Python 3.10+ installed
REM ═══════════════════════════════════════════════════════

echo.
echo  W  Wesco MRO Parser — Build Tool
echo  ══════════════════════════════════
echo.

REM Step 1: Install dependencies
echo [1/3] Installing dependencies...
pip install -r requirements.txt
pip install pyinstaller

REM Step 2: Build the .exe
echo [2/3] Building executable...
pyinstaller ^
    --onefile ^
    --windowed ^
    --name "WescoMROParser" ^
    --add-data "engine;engine" ^
    --hidden-import customtkinter ^
    --hidden-import openpyxl ^
    --hidden-import openpyxl.cell ^
    --hidden-import openpyxl.cell._writer ^
    --hidden-import openpyxl.styles ^
    --hidden-import openpyxl.styles.stylesheet ^
    --hidden-import openpyxl.worksheet ^
    --hidden-import openpyxl.worksheet._writer ^
    --hidden-import openpyxl.xml.functions ^
    --hidden-import openpyxl.utils ^
    --hidden-import et_xmlfile ^
    --collect-all customtkinter ^
    --collect-all openpyxl ^
    app.py

REM Step 3: Done
echo.
echo [3/3] Build complete!
echo.
echo  ✓ Your .exe is at: dist\WescoMROParser.exe
echo  ✓ Share this single file with your team — no Python install needed
echo  ✓ Built for Wesco International Global Accounts Team
echo.
pause
