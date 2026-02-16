#!/bin/bash
# ═══════════════════════════════════════════════════════
#  Wesco MRO Parser — macOS Build Script
#  Run this on a Mac with Python 3.10+ installed
# ═══════════════════════════════════════════════════════

echo ""
echo "  W  Wesco MRO Parser — Build Tool"
echo "  ═══════════════════════════════════"
echo ""

# Step 1: Install dependencies
echo "[1/3] Installing dependencies..."
pip install -r requirements.txt
pip install pyinstaller

# Step 2: Build
echo "[2/3] Building application..."
pyinstaller \
    --onefile \
    --windowed \
    --name "WescoMROParser" \
    --add-data "engine:engine" \
    --hidden-import customtkinter \
    --hidden-import openpyxl \
    --collect-all customtkinter \
    app.py

# Step 3: Done
echo ""
echo "[3/3] Build complete!"
echo ""
echo "  ✓ Your app is at: dist/WescoMROParser"
echo "  ✓ Share this file with your team"
echo "  ✓ No Python install needed on their machines"
echo ""
