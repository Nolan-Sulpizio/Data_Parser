"""
Test suite for v3.1 refinement — edge case fixes.
Run AFTER test_v3_upgrades.py and test_engine_hardening.py pass.

Tests cover all 7 precision fixes:
  Fix 1: GE substring false positive elimination
  Fix 2: Descriptor/keyword blocklist expansion
  Fix 3: MFG normalization map additions
  Fix 4: Descriptor-pattern PN rejection
  Fix 5: McMaster dash-separated catalog number extraction
  Fix 6: Heuristic confidence calibration
  Fix 7: Clean training_data.json known manufacturers
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import re
import pandas as pd
from engine.parser_core import (
    pipeline_mfg_pn,
    sanitize_mfg,
    extract_pn_from_text,
    extract_pn_dash_catalog,
    NORMALIZE_MFG,
    KNOWN_MANUFACTURERS,
)

PASS = 0
FAIL = 0


def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name} — {detail}")


# ═══════════════════════════════════════════════════════════════
print("=" * 70)
print("  FIX 1: GE SUBSTRING FALSE POSITIVES")
print("=" * 70)

# GE should NOT match inside these words
ge_false_texts = [
    "MTR,GEARED,GR 17.54:1,101RPM,SEW EURODR",
    "SWITCH,EMERGENCY STOP,6741K46",
    "H-1349 - WINDOW SQUEEGEE",
    "FLG,D.340,SUPPORT,GEARBOX,26000120500",
    "PLATE,LEGEND,PANELMOUNT,7550K374",
    "2093A11 - Steel Feeler Gauge",
    "SCRAPER,DRAINAGE,SCREW,AUGER,S2493-116",
    "AUGER ASSEMBLY L0091-C003-114AF1",
    "PARTS,GEARBX,FEET,TYPE,W63,4900095",
    "Onsite Service Emergency Onsite Service",
]

for text in ge_false_texts:
    test_df = pd.DataFrame({'Short Text': [text], 'MFG': [None], 'PN': [None]})
    result = pipeline_mfg_pn(test_df, source_cols=['Short Text'], mfg_col='MFG', pn_col='PN', add_sim=False)
    mfg = str(result.df.at[0, 'MFG']).strip().upper()
    if mfg in ('NAN', 'NONE', ''):
        mfg = ''
    check(f"'{text[:50]}' → MFG ≠ GE",
          mfg != 'GE', f"got MFG='{mfg}'")

# GE SHOULD still match when it's a standalone token
ge_valid_texts = [
    ("CONTACTOR,MAGNETIC,NON REV,GE,PN: AF146", "GE"),
    ("BREAKER,GE,20A,1P", "GE"),
]
for text, expected in ge_valid_texts:
    test_df = pd.DataFrame({'Short Text': [text], 'MFG': [None], 'PN': [None]})
    result = pipeline_mfg_pn(test_df, source_cols=['Short Text'], mfg_col='MFG', pn_col='PN', add_sim=False)
    mfg = str(result.df.at[0, 'MFG']).strip().upper()
    if mfg in ('NAN', 'NONE', ''):
        mfg = ''
    check(f"'{text[:50]}' → MFG = {expected}",
          mfg == expected, f"got MFG='{mfg}'")


# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("  FIX 2: DESCRIPTOR BLOCKLIST")
print("=" * 70)

blocked_mfgs = ['DISCONNECT', 'RESIST', 'PLANE', 'FLG', 'RLR', 'KIT',
                'RED', 'BAR', 'H/W', 'CVR', 'ZNT', 'PWR', 'NPT', 'LLC', 'MAC', 'LIP']
for mfg in blocked_mfgs:
    result = sanitize_mfg(mfg)
    check(f"sanitize_mfg('{mfg}') → None",
          result is None, f"got '{result}'")

# Real manufacturers should NOT be blocked
real_mfgs = ['WEG', 'HKK', 'OLI', 'WAM', 'PTI', 'ABB', 'GE', 'SIEMENS', 'HUBBELL']
for mfg in real_mfgs:
    result = sanitize_mfg(mfg)
    check(f"sanitize_mfg('{mfg}') → kept",
          result is not None, f"got None (should be kept)")


# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("  FIX 3: NORMALIZATION MAP")
print("=" * 70)

norm_checks = [
    ('ALN BRDLY', 'ALLEN BRADLEY'),
    ('PHOENIX CNTCT', 'PHOENIX CONTACT'),
    ('FOLCIERI', 'BRUNO FOLCIERI'),
    ('SEW EURODR', 'SEW EURODRIVE'),
    ('SEW', 'SEW EURODRIVE'),
    ('PHNX CNTCT', 'PHOENIX CONTACT'),
    ('BACO', 'BACO CONTROLS'),
    ('ROSSI', 'ROSSI MOTORIDUTTORI'),
]
for raw, expected in norm_checks:
    result = NORMALIZE_MFG.get(raw)
    check(f"NORMALIZE_MFG['{raw}'] = '{expected}'",
          result == expected, f"got '{result}'")

# Known manufacturers check
known_mfg_checks = ['WEG', 'HKK', 'OLI', 'WAM', 'GATES', 'FESTO', 'PILZ', 'SEW EURODRIVE']
for mfg in known_mfg_checks:
    check(f"'{mfg}' in KNOWN_MANUFACTURERS",
          mfg in KNOWN_MANUFACTURERS, f"missing from set")


# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("  FIX 4: DESCRIPTOR-PATTERN PN REJECTION")
print("=" * 70)

bad_pns = ['2-DI/O', '700-HOUR', '3-WAY', '4-BOLT', '12-POINT', '2-WAY', '18-SPC', '6-POINT']
for pn_text in bad_pns:
    result_pn, src = extract_pn_from_text(pn_text)
    check(f"extract_pn('{pn_text}') → None",
          result_pn is None, f"got '{result_pn}'")

# These SHOULD still extract when labeled
labeled_good = [
    ("PN: PKZ2-M4", "PKZ2-M4"),
    ("PN: 3AXD50000731121", "3AXD50000731121"),
]
for text, expected_contains in labeled_good:
    result_pn, src = extract_pn_from_text(text)
    check(f"extract_pn('{text}') extracts something",
          result_pn is not None, f"got None")


# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("  FIX 5: DASH-SEPARATED CATALOG NUMBER EXTRACTION")
print("=" * 70)

dash_tests = [
    ("6970T53 - Antislip Tape", "6970T53"),
    ("5997T82 - Reflective Floor Tape", "5997T82"),
    ("2093A11 - Steel Feeler Gauge", "2093A11"),
    ("97840A860 - lanyard kit", "97840A860"),
    ("5163A56 - Ratcheting Wrench", "5163A56"),
    ("2334A4 - FEELER GAUGE SET", "2334A4"),
]

for text, expected in dash_tests:
    pn, src, conf = extract_pn_dash_catalog(text)
    check(f"dash_catalog('{text[:40]}') → PN = {expected}",
          pn == expected.upper(), f"got PN='{pn}'")

# Test via full pipeline as well
for text, expected in dash_tests[:4]:
    test_df = pd.DataFrame({'Short Text': [text], 'MFG': [None], 'PN': [None]})
    result = pipeline_mfg_pn(test_df, source_cols=['Short Text'], mfg_col='MFG', pn_col='PN', add_sim=False)
    pn = str(result.df.at[0, 'PN']).strip().upper()
    if pn in ('NAN', 'NONE', ''):
        pn = None
    check(f"pipeline('{text[:40]}') → PN = {expected}",
          pn == expected.upper(), f"got PN='{pn}'")


# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("  FIX 6: HEURISTIC CONFIDENCE CALIBRATION")
print("=" * 70)

# These should have HIGH enough confidence to pass threshold
high_quality_heuristics = [
    "3AXD50000731121",       # Long alphanumeric — definitely a real PN
    "17000120500-01",        # Structured with dash — likely real PN
    "6EP1434-2BA20",         # Classic structured PN format
]
for text in high_quality_heuristics:
    test_df = pd.DataFrame({'Short Text': [text], 'MFG': [None], 'PN': [None]})
    result = pipeline_mfg_pn(test_df, source_cols=['Short Text'], mfg_col='MFG', pn_col='PN', add_sim=False)
    pn = str(result.df.at[0, 'PN']).strip().upper()
    if pn in ('NAN', 'NONE', ''):
        pn = None
    check(f"'{text}' extracted as PN (not rejected by threshold)",
          pn is not None, f"got None (threshold too aggressive)")

# 3PH is a spec token — should always be rejected
test_df = pd.DataFrame({'Short Text': ['3PH'], 'MFG': [None], 'PN': [None]})
result = pipeline_mfg_pn(test_df, source_cols=['Short Text'], mfg_col='MFG', pn_col='PN', add_sim=False)
pn = str(result.df.at[0, 'PN']).strip().upper()
if pn in ('NAN', 'NONE', ''):
    pn = None
check("'3PH' rejected as PN (spec token)", pn is None, f"got PN='{pn}'")


# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("  FIX 7: CLEANED KNOWN_MANUFACTURERS (no descriptors)")
print("=" * 70)

should_not_be_known = ['DISCONNECT', 'RESIST', 'FIBRE OPTIC', 'INSERT MALE SCREW',
                        'MTG HSE', 'GENERIC CONDUIT', 'GENERIC WIRE']
for name in should_not_be_known:
    check(f"'{name}' removed from KNOWN_MANUFACTURERS",
          name not in KNOWN_MANUFACTURERS, f"still present")

should_be_known = ['WEG', 'HKK', 'OLI', 'FESTO', 'GATES', 'SEW EURODRIVE', 'PILZ']
for name in should_be_known:
    check(f"'{name}' in KNOWN_MANUFACTURERS",
          name in KNOWN_MANUFACTURERS, f"missing")


# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("  FULL PIPELINE — WESCO.xlsx REGRESSION")
print("=" * 70)

wesco_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           'test_data', 'WESCO.xlsx')
if os.path.exists(wesco_path):
    df = pd.read_excel(wesco_path)

    # Determine supplier col
    supplier_col = None
    for c in df.columns:
        if 'supplier' in c.lower() or 'vendor' in c.lower():
            supplier_col = c
            break

    result = pipeline_mfg_pn(df, source_cols=['Short Text'], mfg_col='MFG', pn_col='PN',
                              add_sim=True, supplier_col=supplier_col)
    out = result.df
    total = len(out)

    def count_filled(col):
        if col not in out.columns:
            return 0
        return (out[col].notna()
                & (out[col].astype(str).str.strip() != '')
                & (out[col].astype(str).str.upper() != 'NAN')).sum()

    mfg_filled = count_filled('MFG')
    pn_filled = count_filled('PN')

    print(f"  MFG filled: {mfg_filled}/{total} ({mfg_filled/total*100:.1f}%)")
    print(f"  PN filled:  {pn_filled}/{total} ({pn_filled/total*100:.1f}%)")

    # GE false positives eliminated
    ge_count = (out['MFG'].astype(str).str.upper().str.strip() == 'GE').sum()
    check(f"GE as MFG: {ge_count} rows (should be < 10, was 201)",
          ge_count < 10, f"still {ge_count}")

    # Zero descriptor MFGs
    desc_mfgs = {'DISCONNECT', 'RESIST', 'PLANE', 'FLG', 'RLR', 'KIT', 'RED',
                 'BAR', 'H/W', 'CVR', 'ZNT', 'PWR', 'NPT', 'LLC'}
    desc_count = out['MFG'].astype(str).str.upper().str.strip().isin(desc_mfgs).sum()
    check(f"Zero descriptor MFGs (was 75+)",
          desc_count == 0, f"found {desc_count}")

    # No descriptor-pattern PNs
    desc_pn_re = re.compile(r'^\d+-(?:WAY|BOLT|POINT|HOUR|DI/O|SPC)', re.IGNORECASE)
    desc_pn_count = (out['PN'].astype(str).str.upper().str.strip()
                     .apply(lambda x: bool(desc_pn_re.match(x))).sum())
    check(f"Zero descriptor-pattern PNs (was 23)",
          desc_pn_count == 0, f"found {desc_pn_count}")

    # McMaster dash rows now have PNs (if supplier column found)
    if supplier_col:
        mcm = out[df[supplier_col].str.contains('McMaster', na=False)]
        mcm_dash = mcm[df.loc[mcm.index, 'Short Text'].str.contains(' - ', na=False)]
        mcm_dash_pn = mcm_dash[
            mcm_dash['PN'].notna()
            & (mcm_dash['PN'].astype(str).str.strip() != '')
            & (mcm_dash['PN'].astype(str).str.upper() != 'NAN')
        ]
        check(f"McMaster dash rows with PN: {len(mcm_dash_pn)}/{len(mcm_dash)}",
              len(mcm_dash_pn) >= min(6, len(mcm_dash)), f"only {len(mcm_dash_pn)}")

    # Print top MFG values for visual review
    print(f"\n  Top 15 MFG values:")
    mfg_dist = (out['MFG']
                [out['MFG'].notna()
                 & (out['MFG'].astype(str).str.strip() != '')
                 & (out['MFG'].astype(str).str.upper() != 'NAN')]
                .astype(str).str.upper().value_counts().head(15))
    for mfg_val, cnt in mfg_dist.items():
        print(f"    {mfg_val:40s} {cnt:5d}")

else:
    print("  ⚠️  WESCO.xlsx not found in test_data/ — skipping WESCO regression")


# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("  DATA SET 1 REGRESSION (must stay >= 95%)")
print("=" * 70)

ds1_input = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          'test_data', 'Data Set 1',
                          'Electrical PN_MFG Search_NOT COMPLETE.XLSX')
ds1_truth = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          'test_data', 'Data Set 1',
                          'Electrical PN_MFG Search_COMPLETE.xlsx')

if os.path.exists(ds1_input) and os.path.exists(ds1_truth):
    df_in = pd.read_excel(ds1_input)
    df_tr = pd.read_excel(ds1_truth)
    src = [c for c in df_in.columns if any(k in c.upper() for k in ['DESCRIPTION', 'PO TEXT', 'MATERIAL'])]
    r = pipeline_mfg_pn(df_in, source_cols=src, mfg_col='MFG', pn_col='PN', add_sim=True)
    df_o = r.df

    mc, mt, pc, pt = 0, 0, 0, 0
    for i in range(min(len(df_tr), len(df_o))):
        tm = str(df_tr.at[i, 'MFG']).strip().upper() if pd.notna(df_tr.at[i, 'MFG']) else ''
        om = str(df_o.at[i, 'MFG']).strip().upper() if pd.notna(df_o.at[i, 'MFG']) else ''
        tp = str(df_tr.at[i, 'PN']).strip().upper() if pd.notna(df_tr.at[i, 'PN']) else ''
        op = str(df_o.at[i, 'PN']).strip().upper() if pd.notna(df_o.at[i, 'PN']) else ''
        for s in ('NAN', 'NONE', ''):
            tm = '' if tm == s else tm
            om = '' if om == s else om
            tp = '' if tp == s else tp
            op = '' if op == s else op
        if tm:
            mt += 1
            mc += 1 if (om == tm or tm in om or om in tm) else 0
        if tp:
            pt += 1
            pc += 1 if (op == tp or tp in op or op in tp) else 0

    ma = mc / mt * 100 if mt else 0
    pa = pc / pt * 100 if pt else 0
    print(f"  MFG: {mc}/{mt} = {ma:.1f}%")
    print(f"  PN:  {pc}/{pt} = {pa:.1f}%")
    check("MFG regression >= 95%", ma >= 95, f"got {ma:.1f}%")
    check("PN regression >= 95%", pa >= 95, f"got {pa:.1f}%")
else:
    print("  ⚠️  Data Set 1 not found — skipping regression")


# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print(f"  FINAL: {PASS} passed, {FAIL} failed")
print("=" * 70)
if FAIL > 0:
    print("\n  ⚠️  SOME TESTS FAILED — fix before committing")
    sys.exit(1)
else:
    print("\n  🎉 ALL TESTS PASSED — v3.1 refinement complete")
    sys.exit(0)
