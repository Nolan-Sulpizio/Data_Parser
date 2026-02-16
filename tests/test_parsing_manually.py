#!/usr/bin/env python3
"""
Manual parsing test - simulate user interaction with Data Set 1
"""
import sys
from pathlib import Path
import pandas as pd

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from engine.parser_core import pipeline_mfg_pn
from engine.instruction_parser import parse_instruction

# Load the blank file
data_file = Path(__file__).parent / "test_data" / "Electrical PN_MFG Search_NOT COMPLETE.XLSX"
truth_file = Path(__file__).parent / "test_data" / "Electrical PN_MFG Search_COMPLETE.xlsx"

print("="*70)
print("MANUAL PARSING TEST - Data Set 1")
print("="*70)
print()

# Read the files
print("Loading files...")
df_blank = pd.read_excel(data_file, engine='openpyxl')
df_truth = pd.read_excel(truth_file, engine='openpyxl')

print(f"Blank file shape: {df_blank.shape}")
print(f"Truth file shape: {df_truth.shape}")
print()

print("Columns in blank file:")
for i, col in enumerate(df_blank.columns, 1):
    print(f"  {i}. {col}")
print()

print("Sample data from first row:")
print(df_blank.iloc[0].to_dict())
print()

# TEST 1: No instruction (automatic mode)
print("="*70)
print("TEST 1: Automatic parsing (no instruction)")
print("="*70)
source_cols = [c for c in df_blank.columns if 'description' in c.lower() or 'text' in c.lower()]
print(f"Source columns detected: {source_cols}")
print()

result1 = pipeline_mfg_pn(df_blank.copy(), source_cols=source_cols, mfg_col='MFG', pn_col='PN', add_sim=True)
df_auto = result1.df

print(f"MFG filled: {result1.mfg_filled}")
print(f"PN filled: {result1.pn_filled}")
print(f"SIM filled: {result1.sim_filled}")
print()

# Show first 5 results
print("First 5 rows (automatic):")
print(df_auto[['Material Description', 'MFG', 'PN']].head())
print()

# TEST 2: With instruction prompt (like user would enter)
print("="*70)
print("TEST 2: With instruction prompt")
print("="*70)

# Simulate common user instructions
test_instructions = [
    "Extract MFG and PN from Material Description",
    "Get manufacturer and part number from the description column",
    "Pull MFG from Material Description into column A and PN into column B",
]

for instruction in test_instructions:
    print(f"\nInstruction: '{instruction}'")
    parsed = parse_instruction(instruction)
    print(f"Pipeline: {parsed.pipeline}")
    print(f"Source columns: {parsed.source_columns}")
    print(f"Confidence: {parsed.confidence}")
    print(f"Explanation: {parsed.explanation}")
    print()

# TEST 3: Compare against ground truth
print("="*70)
print("TEST 3: Accuracy comparison (automatic vs truth)")
print("="*70)

matches = 0
mismatches = 0
for idx in range(min(10, len(df_truth))):  # Check first 10 rows
    truth_mfg = str(df_truth.at[idx, 'MFG']).strip().upper() if pd.notna(df_truth.at[idx, 'MFG']) else ''
    auto_mfg = str(df_auto.at[idx, 'MFG']).strip().upper() if pd.notna(df_auto.at[idx, 'MFG']) else ''

    truth_pn = str(df_truth.at[idx, 'PN']).strip().upper() if pd.notna(df_truth.at[idx, 'PN']) else ''
    auto_pn = str(df_auto.at[idx, 'PN']).strip().upper() if pd.notna(df_auto.at[idx, 'PN']) else ''

    desc = str(df_blank.at[idx, 'Material Description'])[:60] if 'Material Description' in df_blank.columns else ''

    mfg_match = truth_mfg == auto_mfg if truth_mfg else True
    pn_match = truth_pn == auto_pn if truth_pn else True

    if mfg_match and pn_match:
        matches += 1
        status = "✓"
    else:
        mismatches += 1
        status = "✗"

    print(f"Row {idx+1} {status}")
    print(f"  Desc: {desc}")
    if not mfg_match:
        print(f"  MFG: expected={truth_mfg}, got={auto_mfg}")
    if not pn_match:
        print(f"  PN: expected={truth_pn}, got={auto_pn}")
    print()

print(f"Summary: {matches} matches, {mismatches} mismatches (of first 10 rows)")
print()

# TEST 4: Check for "not clean" parsing issues
print("="*70)
print("TEST 4: Data quality check")
print("="*70)

# Check for common issues
issues = []

for idx in range(len(df_auto)):
    mfg = str(df_auto.at[idx, 'MFG']).strip() if pd.notna(df_auto.at[idx, 'MFG']) else ''
    pn = str(df_auto.at[idx, 'PN']).strip() if pd.notna(df_auto.at[idx, 'PN']) else ''

    # Issue 1: MFG has digits
    if mfg and any(c.isdigit() for c in mfg):
        issues.append(f"Row {idx+1}: MFG has digits: '{mfg}'")

    # Issue 2: PN looks like a description fragment
    if pn and len(pn) > 30:
        issues.append(f"Row {idx+1}: PN too long (likely extracted wrong): '{pn}'")

    # Issue 3: MFG same as PN
    if mfg and pn and mfg == pn:
        issues.append(f"Row {idx+1}: MFG same as PN: '{mfg}'")

print(f"Found {len(issues)} potential quality issues:")
for issue in issues[:10]:  # Show first 10
    print(f"  - {issue}")

if len(issues) > 10:
    print(f"  ... and {len(issues) - 10} more")

print()
print("="*70)
print("TEST COMPLETE")
print("="*70)
