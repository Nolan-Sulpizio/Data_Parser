"""
test_engine_hardening.py — Test suite for engine hardening (Layers 1-5).
Run AFTER test_v3_upgrades.py passes.

Usage:
    python tests/test_engine_hardening.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from engine.parser_core import (
    pipeline_mfg_pn, sanitize_mfg, ExtractionCandidate, pick_best,
    CONFIDENCE_SCORES, validate_and_clean
)
from engine.file_profiler import profile_file, FileProfile
from engine.column_mapper import map_columns

PASS = 0
FAIL = 0


def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  \u2705 {name}")
    else:
        FAIL += 1
        print(f"  \u274c {name} {detail}")


# ═══════════════════════════════════════════════════════════════
print("=" * 70)
print("  TEST 1: FILE PROFILER")
print("=" * 70)

wesco_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'test_data', 'WESCO.xlsx',
)
if os.path.exists(wesco_path):
    df_wesco = pd.read_excel(wesco_path)
    profile = profile_file(df_wesco, source_cols=['Short Text'],
                           supplier_col='Supplier Name1')

    check("WESCO.xlsx archetype is COMPRESSED_SHORT or MIXED",
          profile.archetype in ('COMPRESSED_SHORT', 'MIXED'),
          f"got {profile.archetype}")
    check("WESCO.xlsx pct_labeled_pn < 0.20",
          profile.pct_labeled_pn < 0.20,
          f"got {profile.pct_labeled_pn:.2%}")
    check("WESCO.xlsx has_supplier_col is True",
          profile.has_supplier_col is True)
    check("WESCO.xlsx confidence_threshold >= 0.40",
          profile.confidence_threshold >= 0.40,
          f"got {profile.confidence_threshold}")
    check("FileProfile.summary() works", len(profile.summary()) > 100)
    print(f"\n  Profile summary:\n{profile.summary()}\n")
else:
    print(f"  \u26a0\ufe0f  WESCO.xlsx not found — skipping profiler test")

# Test with Data Set 1 (labeled rich format)
ds1_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'test_data', 'Data Set 1',
    'Electrical PN_MFG Search_NOT COMPLETE.XLSX',
)
if os.path.exists(ds1_path):
    df_ds1 = pd.read_excel(ds1_path)
    source_cols_ds1 = [c for c in df_ds1.columns if any(k in c.upper() for k in
                       ['DESCRIPTION', 'PO TEXT', 'MATERIAL'])]
    profile_ds1 = profile_file(df_ds1, source_cols=source_cols_ds1)

    check("Data Set 1 archetype is LABELED_RICH",
          profile_ds1.archetype == 'LABELED_RICH',
          f"got {profile_ds1.archetype}")
    check("Data Set 1 pct_labeled_pn > 0.30",
          profile_ds1.pct_labeled_pn > 0.30,
          f"got {profile_ds1.pct_labeled_pn:.2%}")
else:
    print(f"  \u26a0\ufe0f  Data Set 1 not found — skipping labeled-rich profiler test")


# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("  TEST 2: CONFIDENCE SCORING")
print("=" * 70)

check("CONFIDENCE_SCORES dict exists",
      isinstance(CONFIDENCE_SCORES, dict) and len(CONFIDENCE_SCORES) > 5)
check("Label confidence > heuristic confidence",
      CONFIDENCE_SCORES.get('pn_label', 0) > CONFIDENCE_SCORES.get('pn_fallback', 1))
check("Known MFG confidence > supplier fallback",
      CONFIDENCE_SCORES.get('mfg_known', 0) > CONFIDENCE_SCORES.get('mfg_supplier', 1))


# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("  TEST 3: MULTI-STRATEGY BEST-PICK")
print("=" * 70)

candidates = [
    ExtractionCandidate("120/277V", "heuristic", 0.35),
    ExtractionCandidate("CS120W", "prefix_decode", 0.75),
    ExtractionCandidate("SP20A", "pn_structured", 0.65),
]
weights = {'heuristic': 0.4, 'prefix_decode': 1.3, 'pn_structured': 1.0}

best_val, best_src, best_conf = pick_best(candidates, weights)
check("Best pick is CS120W (prefix_decode)",
      best_val == "CS120W", f"got {best_val}")
check("Best pick source is prefix_decode",
      best_src == "prefix_decode", f"got {best_src}")
check("Heuristic 120/277V was NOT picked",
      best_val != "120/277V")

# Test with no valid candidates
empty_val, _, _ = pick_best([], weights)
check("Empty candidates returns None", empty_val is None)


# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("  TEST 4: POST-EXTRACTION VALIDATION")
print("=" * 70)

test_df = pd.DataFrame({
    'Short Text': [
        'HUBCS120W - SWITCH - SP20A 120/277V',
        'SCR,TE,14X265-ISO4017,PN:4100697',
        'MTR,ELE,2.2KW,480V,1800RPM',
        'BELT,V,SPC6300,RBR,GATES,PN: SPC6300',
        'Some random text',
    ],
    'MFG': ['HUBBELL', 'TE', 'AMUT', 'GATES', 'GATES'],
    'PN': ['CS120W', '4100697', '480V', 'SPC6300', 'GATES'],
})

cleaned_df, corrections = validate_and_clean(test_df, mfg_col='MFG', pn_col='PN')

# Rule 1: 480V should be cleared from PN
row2_pn = str(cleaned_df.at[2, 'PN']).strip()
check("Validation clears spec value '480V' from PN",
      row2_pn in ('', 'nan', 'None', 'NaN'),
      f"got '{row2_pn}'")

# Rule 3: TE should be cleared from MFG
row1_mfg = str(cleaned_df.at[1, 'MFG']).strip()
check("Validation clears descriptor 'TE' from MFG",
      row1_mfg in ('', 'nan', 'None', 'NaN'),
      f"got '{row1_mfg}'")

# Rule 7: GATES as PN should be cleared (it's a manufacturer name that appears in MFG column)
row4_pn = str(cleaned_df.at[4, 'PN']).strip()
check("Validation clears MFG name 'GATES' from PN column",
      row4_pn in ('', 'nan', 'None', 'NaN'),
      f"got '{row4_pn}'")

# Good values should survive
check("Validation keeps valid MFG 'HUBBELL'",
      str(cleaned_df.at[0, 'MFG']).strip().upper() == 'HUBBELL')
check("Validation keeps valid PN 'SPC6300'",
      str(cleaned_df.at[3, 'PN']).strip().upper() == 'SPC6300')

check("Corrections list is populated",
      len(corrections) >= 2, f"got {len(corrections)} corrections")


# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("  TEST 5: COLUMN MAPPER — NEW ALIASES")
print("=" * 70)

test_df_cols = pd.DataFrame(columns=[
    'Supplier Name1', 'Short Text', 'Material', 'Plant', 'Order Quantity'
])
mapping = map_columns(test_df_cols)

check("'Short Text' mapped to source_description",
      'Short Text' in mapping.get('source_description', []),
      f"source_description = {mapping.get('source_description')}")

check("'Supplier Name1' mapped to supplier role",
      mapping.get('supplier') == 'Supplier Name1',
      f"supplier = {mapping.get('supplier')}")


# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("  TEST 6: FULL PIPELINE — WESCO.xlsx WITH HARDENING")
print("=" * 70)

if os.path.exists(wesco_path):
    df = pd.read_excel(wesco_path)
    result = pipeline_mfg_pn(df, source_cols=['Short Text'],
                              mfg_col='MFG', pn_col='PN',
                              add_sim=True, supplier_col='Supplier Name1',
                              auto_validate=True)
    out = result.df

    total = len(out)
    mfg_filled = (out['MFG'].notna() & (out['MFG'].astype(str).str.strip() != '') &
                  (out['MFG'].astype(str).str.upper() != 'NAN')).sum()
    pn_filled = (out['PN'].notna() & (out['PN'].astype(str).str.strip() != '') &
                 (out['PN'].astype(str).str.upper() != 'NAN')).sum()

    print(f"  Total rows: {total}")
    print(f"  MFG filled: {mfg_filled} ({mfg_filled/total*100:.1f}%)")
    print(f"  PN filled:  {pn_filled} ({pn_filled/total*100:.1f}%)")

    check("JobResult includes file_profile",
          result.file_profile is not None)
    if result.file_profile:
        print(f"  File archetype: {result.file_profile.archetype}")

    check("JobResult includes confidence_stats",
          isinstance(result.confidence_stats, dict) and len(result.confidence_stats) > 0,
          f"got {result.confidence_stats}")

    # Zero spec values in PN column after validation
    import re as _re
    spec_in_pn = out['PN'].astype(str).str.upper().apply(
        lambda v: bool(_re.match(r'^\d+(?:/\d+)?(?:V|A|W|KW|HP|RPM|PH)$', v))
        if v not in ('NAN', 'NONE', '') else False
    ).sum()
    check("Zero spec values in PN after validation",
          spec_in_pn == 0, f"found {spec_in_pn}")

    # Zero descriptor tokens in MFG column
    descriptor_tokens = {'TE', 'NM', 'BLK', 'DIA', 'FR', 'DC', 'AC', 'MTR', 'DRV',
                         'BRG', 'SCR', 'VLV', 'FAN', 'PMP', 'SS', 'CS'}
    desc_in_mfg = out['MFG'].astype(str).str.upper().str.strip().isin(descriptor_tokens).sum()
    check("Zero descriptor tokens in MFG after validation",
          desc_in_mfg == 0, f"found {desc_in_mfg}")

    # HUBCS120W test case
    hub_row = out[out['Short Text'].str.contains('HUBCS120W', case=False, na=False)]
    if not hub_row.empty:
        row = hub_row.iloc[0]
        check("HUBCS120W → MFG = HUBBELL",
              str(row.get('MFG', '')).upper() == 'HUBBELL',
              f"got '{row.get('MFG')}'")
        pn_val = str(row.get('PN', '')).upper()
        check("HUBCS120W → PN is NOT a spec value",
              not pn_val.endswith('V') and pn_val != '120/277V',
              f"got '{pn_val}'")
    else:
        print("  \u26a0\ufe0f  HUBCS120W row not found in WESCO.xlsx")

    check("Low confidence items tracked",
          isinstance(result.low_confidence_items, list))
    if result.low_confidence_items:
        print(f"  Low confidence items: {len(result.low_confidence_items)}")
else:
    print(f"  \u26a0\ufe0f  WESCO.xlsx not found — skipping pipeline test")


# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("  TEST 7: REGRESSION — Data Set 1 (must stay >= 95%)")
print("=" * 70)

ds1_complete = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'test_data', 'Data Set 1',
    'Electrical PN_MFG Search_COMPLETE.xlsx',
)

if os.path.exists(ds1_path) and os.path.exists(ds1_complete):
    df_input = pd.read_excel(ds1_path)
    df_truth = pd.read_excel(ds1_complete)

    source_cols = [c for c in df_input.columns if any(k in c.upper() for k in
                   ['DESCRIPTION', 'PO TEXT', 'MATERIAL'])]

    result = pipeline_mfg_pn(df_input, source_cols=source_cols,
                              mfg_col='MFG', pn_col='PN', add_sim=True)
    df_out = result.df

    mfg_correct = 0
    mfg_total = 0
    pn_correct = 0
    pn_total = 0

    for i in range(min(len(df_truth), len(df_out))):
        truth_mfg = str(df_truth.at[i, 'MFG']).strip().upper() if pd.notna(df_truth.at[i, 'MFG']) else ''
        out_mfg = str(df_out.at[i, 'MFG']).strip().upper() if pd.notna(df_out.at[i, 'MFG']) else ''
        truth_pn = str(df_truth.at[i, 'PN']).strip().upper() if pd.notna(df_truth.at[i, 'PN']) else ''
        out_pn = str(df_out.at[i, 'PN']).strip().upper() if pd.notna(df_out.at[i, 'PN']) else ''

        for s in ('NAN', 'NONE', ''):
            if truth_mfg == s: truth_mfg = ''
            if out_mfg == s: out_mfg = ''
            if truth_pn == s: truth_pn = ''
            if out_pn == s: out_pn = ''

        if truth_mfg:
            mfg_total += 1
            if out_mfg == truth_mfg or truth_mfg in out_mfg or out_mfg in truth_mfg:
                mfg_correct += 1
        if truth_pn:
            pn_total += 1
            if out_pn == truth_pn or truth_pn in out_pn or out_pn in truth_pn:
                pn_correct += 1

    mfg_acc = mfg_correct / mfg_total * 100 if mfg_total else 0
    pn_acc = pn_correct / pn_total * 100 if pn_total else 0

    print(f"  MFG accuracy: {mfg_correct}/{mfg_total} = {mfg_acc:.1f}%")
    print(f"  PN accuracy:  {pn_correct}/{pn_total} = {pn_acc:.1f}%")

    check("MFG regression >= 95%", mfg_acc >= 95, f"got {mfg_acc:.1f}%")
    check("PN regression >= 95%", pn_acc >= 95, f"got {pn_acc:.1f}%")
else:
    print(f"  \u26a0\ufe0f  Data Set 1 files not found — skipping regression test")


# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print(f"  FINAL RESULTS: {PASS} passed, {FAIL} failed")
print("=" * 70)

if FAIL > 0:
    print("\n  \u26a0\ufe0f  SOME TESTS FAILED \u2014 review and fix before committing")
    sys.exit(1)
else:
    print("\n  \U0001f389 ALL TESTS PASSED \u2014 engine hardening complete")
    sys.exit(0)
