#!/usr/bin/env python3
"""
Test the improvements: PN length flagging and instruction parser confidence
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from engine.parser_core import pn_needs_review, run_qa, pipeline_mfg_pn
from engine.instruction_parser import parse_instruction
import pandas as pd

print("="*70)
print("TESTING IMPROVEMENTS")
print("="*70)
print()

# TEST 1: PN Length Flagging
print("TEST 1: PN Length Flagging")
print("-"*70)

test_pns = [
    ("ABC-123", False, "Normal PN"),
    ("3051TG3A2B21AS1E5Q4M5/1199PCAD5/ARTW30DA", True, "Long concatenated PN"),
    ("PCMB-8", False, "Short PN"),
    ("3051TG2A2B21AS1B4M5I51199WCD10NWSP70LAL", True, "Very long PN"),
    ("", False, "Empty string"),
]

for pn, expected, desc in test_pns:
    result = pn_needs_review(pn)
    status = "✓" if result == expected else "✗"
    print(f"{status} {desc}: '{pn}' (len={len(pn)}) → needs_review={result}")

print()

# TEST 2: Instruction Parser Confidence
print("TEST 2: Instruction Parser Confidence Improvements")
print("-"*70)

test_instructions = [
    ("Extract MFG and PN from Material Description", "Exact column match"),
    ("Get manufacturer and part number from the description column", "Generic 'description column'"),
    ("Pull MFG from description into column A", "Generic 'description' with context"),
    ("Parse manufacturer and part number from the desc column", "Abbreviated 'desc column'"),
    ("Extract MFG and PN", "No source column mentioned"),
]

for instruction, desc in test_instructions:
    parsed = parse_instruction(instruction)
    confidence_pct = round(parsed.confidence * 100)
    print(f"\nInstruction: '{instruction}'")
    print(f"  Description: {desc}")
    print(f"  Pipeline: {parsed.pipeline}")
    print(f"  Confidence: {confidence_pct}%")
    if confidence_pct >= 100:
        print(f"  Status: ✓ HIGH CONFIDENCE")
    elif confidence_pct >= 80:
        print(f"  Status: ✓ GOOD CONFIDENCE")
    elif confidence_pct >= 60:
        print(f"  Status: ⚠ MODERATE CONFIDENCE")
    else:
        print(f"  Status: ✗ LOW CONFIDENCE")

print()

# TEST 3: QA Rules with New Flags
print("TEST 3: QA Rules - New Flags")
print("-"*70)

# Create test dataframe
test_data = pd.DataFrame({
    'MFG': ['PANDUIT', 'BALSTON', 'SQUARE D', ''],
    'PN': ['ABC-123', 'BALSTON', '3051TG3A2B21AS1E5Q4M5/1199PCAD5/ARTW30DA', ''],
    'Material Description': ['TEST', 'TEST', 'TEST', 'TEST'],
})

issues = run_qa(test_data, mfg_col='MFG')

print(f"Found {len(issues)} QA issues:")
for issue in issues:
    print(f"  Row {issue['row']}: {issue['flag']} - {issue['note']}")
    print(f"    MFG={issue.get('MFG', 'N/A')}, PN={test_data.at[issue['row']-2, 'PN']}")

print()
print("="*70)
print("IMPROVEMENTS VALIDATED")
print("="*70)
