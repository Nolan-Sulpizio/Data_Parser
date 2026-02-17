"""
test_v3_upgrades.py — Test suite for v3 engine upgrades (Short Text format support).

Tests all 4 upgrades + regression against existing Data Set 1.

Usage:
    python tests/test_v3_upgrades.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import re
import pandas as pd
from engine.parser_core import (
    extract_pn_from_text,
    extract_mfg_from_text,
    sanitize_mfg,
    pipeline_mfg_pn,
    decode_mfg_prefix,
    KNOWN_MANUFACTURERS,
)

PASS = 0
FAIL = 0


def check(name: str, actual, expected, allow_none: bool = False):
    global PASS, FAIL
    actual_clean = str(actual).strip().upper() if actual else None
    expected_clean = str(expected).strip().upper() if expected else None
    if actual_clean == expected_clean or (
        allow_none and actual_clean is None and expected_clean is None
    ):
        PASS += 1
        print(f"  \u2705 {name}: {actual_clean}")
    else:
        FAIL += 1
        print(f"  \u274c {name}: got '{actual_clean}', expected '{expected_clean}'")


# ═══════════════════════════════════════════════════════════════════════════
print("=" * 70)
print("  TEST 1: SPEC VALUE REJECTION (Upgrade 1)")
print("=" * 70)

# These spec-value tokens must NOT be extracted as part numbers
spec_rejections = [
    ("120/277V", None),
    ("60A", None),
    ("480V", None),
    ("3PH", None),
    ("2.02W", None),
    ("2.6875IN", None),
    ("1800RPM", None),
    ("2.2KW", None),
    ("5HP", None),
    ("DC24V", None),
    ("600V", None),
    ("120V", None),
    ("15A", None),
]
for val, expected in spec_rejections:
    pn, src = extract_pn_from_text(val)
    check(f"Reject spec '{val}'", pn, expected, allow_none=True)

# Full strings — spec at end must NOT become PN
full_spec_strings = [
    ("HUBCS120W - SWITCH - SP20A 120/277V", "SP20A"),   # spec rejected; SP20A survives
    ("SWITCH,FUSE,DISCONNECT,HUBBELL,600V,60A", None),  # all tokens are descriptors/specs
    ("DRV,3AXD50000731121,5HP,480V,BAGGING", "3AXD50000731121"),  # long alphanumeric survives
    ("FAN,COOLING,DC24V,2.02W", None),                  # only spec tokens
    ("BRG,PILLOW BLK,DIA 2-7/16IN,W 2.6875IN", None),  # only dimension tokens
]
for text, expected in full_spec_strings:
    pn, src = extract_pn_from_text(text)
    check(f"PN from '{text[:40]}'", pn, expected, allow_none=(expected is None))

# These SHOULD still be extracted as part numbers (labeled or valid alphanumeric)
valid_pns = [
    ("PN: CS120W", "CS120W"),
    ("PN:4100697", "4100697"),
    ("MN: L150N", "L150N"),
    ("3AXD50000731121", "3AXD50000731121"),
    ("PN: SPC6300", "SPC6300"),
    ("7815N15", "7815N15"),
    ("6EP1434-2BA20", "6EP1434-2BA20"),
    ("SHC1037CR", "SHC1037CR"),
]
for text, expected in valid_pns:
    pn, src = extract_pn_from_text(text)
    check(f"Valid PN from '{text}'", pn, expected)


# ═══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("  TEST 2: DESCRIPTOR BLOCKLIST — TE/NM rejection (Upgrade 2)")
print("=" * 70)

descriptor_rejections = [
    "TE", "NM", "BLK", "DIA", "FR", "DC", "AC", "SS",
    "MTR", "DRV", "BRG", "SCR", "VLV", "FAN", "PMP",
    "HEX", "SQ", "RND", "CS", "SP",
]
for desc in descriptor_rejections:
    result = sanitize_mfg(desc)
    check(f"Reject MFG '{desc}'", result, None, allow_none=True)

# Real manufacturer names must still pass sanitize_mfg
valid_mfgs = [
    ("HUBBELL", "HUBBELL"),
    ("SIEMENS", "SIEMENS"),
    ("GATES", "GATES"),
    ("LOVEJOY", "LOVEJOY"),
    ("PANDUIT", "PANDUIT"),
    ("SQUARE D", "SQUARE D"),
    ("EATON", "EATON"),
    ("APPLETON", "APPLETON"),
]
for mfg, expected in valid_mfgs:
    result = sanitize_mfg(mfg)
    check(f"Accept MFG '{mfg}'", result, expected)

# 2-char tokens with no known manufacturer match must be rejected
two_char_tokens = ["AB", "GE", "PE", "CU", "PP", "PH"]
for tok in two_char_tokens:
    if tok not in KNOWN_MANUFACTURERS:
        result = sanitize_mfg(tok)
        check(f"Reject 2-char '{tok}' (not known MFG)", result, None, allow_none=True)


# ═══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("  TEST 3: PREFIX DECODER — decode_mfg_prefix (Upgrade 3)")
print("=" * 70)

prefix_tests = [
    ("HUBCS120W", "HUBBELL", "CS120W"),
    ("HUBGFR20W", "HUBBELL", "GFR20W"),
    ("HUBSHC1037CR", "HUBBELL", "SHC1037CR"),
    ("HUBHBLDS10AC", "HUBBELL", "HBLDS10AC"),
    ("HUBCR20WHI", "HUBBELL", "CR20WHI"),
    # Full strings — decoder reads the first token only
    ("HUBCS120W - SWITCH - SP20A 120/277V", "HUBBELL", "CS120W"),
    ("HUBGFR20W RECEPTACLE", "HUBBELL", "GFR20W"),
    # Should NOT decode — not a known prefix
    ("BELT", None, None),
    ("SWITCH", None, None),
    ("GATES1234", None, None),   # GATE is not a known prefix
    ("DISCONNECT", None, None),
]
for text, exp_mfg, exp_pn in prefix_tests:
    mfg, pn = decode_mfg_prefix(text)
    check(f"Prefix '{text[:25]}' → MFG", mfg, exp_mfg, allow_none=(exp_mfg is None))
    check(f"Prefix '{text[:25]}' → PN", pn, exp_pn, allow_none=(exp_pn is None))


# ═══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("  TEST 4: FULL PIPELINE ON WESCO.xlsx (Upgrade 4 + integration)")
print("=" * 70)

wesco_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'test_data', 'WESCO.xlsx',
)
if os.path.exists(wesco_path):
    df = pd.read_excel(wesco_path)
    result = pipeline_mfg_pn(
        df,
        source_cols=['Short Text'],
        mfg_col='MFG',
        pn_col='PN',
        add_sim=True,
        supplier_col='Supplier Name1',
    )
    out = result.df

    total = len(out)
    mfg_filled = (
        out['MFG'].notna()
        & (out['MFG'].astype(str).str.strip() != '')
        & (out['MFG'].astype(str).str.upper() != 'NAN')
    ).sum()
    pn_filled = (
        out['PN'].notna()
        & (out['PN'].astype(str).str.strip() != '')
        & (out['PN'].astype(str).str.upper() != 'NAN')
    ).sum()

    print(f"  Total rows: {total}")
    print(f"  MFG filled: {mfg_filled} ({mfg_filled / total * 100:.1f}%)")
    print(f"  PN filled:  {pn_filled} ({pn_filled / total * 100:.1f}%)")

    # Spot-check: HUBCS120W row → MFG must be HUBBELL, PN must not be a spec value
    hub_rows = out[out['Short Text'].str.contains('HUBCS120W', case=False, na=False)]
    if not hub_rows.empty:
        row = hub_rows.iloc[0]
        check("HUBCS120W → MFG", row.get('MFG'), 'HUBBELL')
        pn_val = str(row.get('PN', '')).upper()
        spec_pn_re = re.compile(
            r'^\d+(?:/\d+)?(?:V|A|W|KW|HP|RPM|PH)$', re.IGNORECASE
        )
        if spec_pn_re.match(pn_val):
            FAIL += 1
            print(f"  \u274c HUBCS120W \u2192 PN '{pn_val}' is a spec value \u2014 rejection failed!")
        else:
            PASS += 1
            print(f"  \u2705 HUBCS120W \u2192 PN = '{pn_val}' (not a spec value)")
    else:
        print("  \u26a0\ufe0f  HUBCS120W row not found in WESCO.xlsx")

    # TE must never appear as MFG (descriptor rejection)
    te_rows = out[out['Short Text'].str.contains(r'SCR,TE,', case=True, na=False)]
    te_as_mfg = te_rows[te_rows['MFG'].astype(str).str.upper() == 'TE']
    if len(te_as_mfg) == 0:
        PASS += 1
        print(f"  \u2705 No rows have MFG='TE' (descriptor correctly rejected)")
    else:
        FAIL += 1
        print(f"  \u274c {len(te_as_mfg)} rows still have MFG='TE'")

    # McMaster rows must NOT have McMaster as MFG (distributor exclusion)
    mcm_mask = df['Supplier Name1'].str.contains('McMaster', na=False)
    mcm_rows = out[mcm_mask]
    mcm_as_mfg = mcm_rows[
        mcm_rows['MFG'].astype(str).str.contains('MCMASTER', case=False, na=False)
    ]
    if len(mcm_as_mfg) == 0:
        PASS += 1
        print(f"  \u2705 No McMaster rows have MFG='MCMASTER' (distributor excluded)")
    else:
        FAIL += 1
        print(f"  \u274c {len(mcm_as_mfg)} McMaster rows incorrectly have McMaster as MFG")

    # Non-distributor supplier (AMUT) should become MFG fallback
    amut_mask = df['Supplier Name1'].str.contains('AMUT', case=False, na=False)
    amut_rows = out[amut_mask]
    amut_mfg = amut_rows[
        amut_rows['MFG'].astype(str).str.contains('AMUT', case=False, na=False)
    ]
    print(
        f"  {'✅' if len(amut_mfg) > 0 else '❌'} AMUT supplier → MFG fallback: "
        f"{len(amut_mfg)}/{len(amut_rows)} rows"
    )
    if len(amut_rows) > 0:
        if len(amut_mfg) > 0:
            PASS += 1
        else:
            FAIL += 1
    else:
        print("  \u26a0\ufe0f  No AMUT supplier rows in WESCO.xlsx — skipping check")

    # Spec values must NOT appear in the PN column
    spec_in_pn_re = re.compile(
        r'^\d+(?:/\d+)?(?:V|A|W|KW|HP|RPM|PH)$', re.IGNORECASE
    )
    spec_in_pn = out['PN'].astype(str).str.upper().apply(
        lambda v: bool(spec_in_pn_re.match(v)) if v not in ('NAN', 'NONE', '') else False
    ).sum()
    if spec_in_pn == 0:
        PASS += 1
        print(f"  \u2705 Zero spec values in PN column")
    else:
        FAIL += 1
        print(f"  \u274c {spec_in_pn} rows still have spec values as PN")

else:
    print(f"  \u26a0\ufe0f  WESCO.xlsx not found at {wesco_path} — skipping pipeline test")


# ═══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("  TEST 5: REGRESSION — Data Set 1 (Electrical 206-row file)")
print("=" * 70)

_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ds1_input = os.path.join(
    _base, 'test_data', 'Data Set 1',
    'Electrical PN_MFG Search_NOT COMPLETE.XLSX',
)
ds1_truth = os.path.join(
    _base, 'test_data', 'Data Set 1',
    'Electrical PN_MFG Search_COMPLETE.xlsx',
)

if os.path.exists(ds1_input) and os.path.exists(ds1_truth):
    df_input = pd.read_excel(ds1_input)
    df_truth = pd.read_excel(ds1_truth)

    source_cols = [
        c for c in df_input.columns
        if any(k in c.upper() for k in ['DESCRIPTION', 'PO TEXT', 'MATERIAL'])
    ]

    result = pipeline_mfg_pn(
        df_input,
        source_cols=source_cols,
        mfg_col='MFG',
        pn_col='PN',
        add_sim=True,
    )
    df_out = result.df

    mfg_correct = 0
    mfg_total = 0
    pn_correct = 0
    pn_total = 0

    for i in range(min(len(df_truth), len(df_out))):
        def _clean(val):
            s = str(val).strip().upper() if pd.notna(val) else ''
            return '' if s in ('NAN', 'NONE') else s

        truth_mfg = _clean(df_truth.at[i, 'MFG']) if 'MFG' in df_truth.columns else ''
        out_mfg   = _clean(df_out.at[i, 'MFG'])   if 'MFG' in df_out.columns else ''
        truth_pn  = _clean(df_truth.at[i, 'PN'])  if 'PN'  in df_truth.columns else ''
        out_pn    = _clean(df_out.at[i, 'PN'])    if 'PN'  in df_out.columns else ''

        if truth_mfg:
            mfg_total += 1
            if out_mfg == truth_mfg or truth_mfg in out_mfg or out_mfg in truth_mfg:
                mfg_correct += 1
        if truth_pn:
            pn_total += 1
            if out_pn == truth_pn or truth_pn in out_pn or out_pn in truth_pn:
                pn_correct += 1

    mfg_acc = mfg_correct / mfg_total * 100 if mfg_total else 0
    pn_acc  = pn_correct  / pn_total  * 100 if pn_total  else 0

    print(f"  MFG accuracy: {mfg_correct}/{mfg_total} = {mfg_acc:.1f}%")
    print(f"  PN accuracy:  {pn_correct}/{pn_total} = {pn_acc:.1f}%")

    # REGRESSION GATE: must not drop below 95%
    if mfg_acc >= 95:
        PASS += 1
        print(f"  \u2705 MFG regression gate passed (>= 95%)")
    else:
        FAIL += 1
        print(f"  \u274c MFG REGRESSION: accuracy dropped to {mfg_acc:.1f}% (was 97.9%)")

    if pn_acc >= 95:
        PASS += 1
        print(f"  \u2705 PN regression gate passed (>= 95%)")
    else:
        FAIL += 1
        print(f"  \u274c PN REGRESSION: accuracy dropped to {pn_acc:.1f}% (was 98.5%)")

else:
    print(f"  \u26a0\ufe0f  Data Set 1 files not found \u2014 skipping regression test")
    print(f"    Expected: {ds1_input}")


# ═══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print(f"  FINAL RESULTS: {PASS} passed, {FAIL} failed")
print("=" * 70)

if FAIL > 0:
    print("\n  \u26a0\ufe0f  SOME TESTS FAILED \u2014 review and fix before committing")
    sys.exit(1)
else:
    print("\n  \U0001f389 ALL TESTS PASSED \u2014 ready to commit")
    sys.exit(0)
