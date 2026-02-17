# Engine Refinement Prompt — parser_core.py v3.2

## Context

You are refining the MRO Data Parser engine (`engine/parser_core.py`) for the Wesco MRO Data Parser desktop application. The engine uses deterministic, rule-based multi-strategy extraction to pull Manufacturer (MFG) and Part Number (PN) values from unstructured Excel data.

A comprehensive test was just run against a real 2,684-row production file (`WESCO.xlsx`) with the following column structure:

| Column | Contents |
|--------|----------|
| Supplier Name1 | Vendor/supplier name (11 unique suppliers) |
| Material | Internal SAP material number (present in ~41% of rows) |
| Short Text | Unstructured item description — **primary parsing source** |

### Current Performance Baseline (v3.1)

| Metric | Value |
|--------|-------|
| Total rows | 2,684 |
| MFG filled | 1,120 (41.7%) |
| PN filled | 1,360 (50.7%) |
| Processing time | 1.47s |
| Avg MFG confidence | 0.685 |
| Avg PN confidence | 0.762 |
| File archetype detected | MIXED |
| QA flags | 1,564 MFG_missing, 1,326 PN_missing |

### Fill Rates by Supplier (current)

| Supplier | Rows | MFG Fill | PN Fill |
|----------|------|----------|---------|
| McMaster-Carr Supply Co. | 491 | 5.3% | 18.9% |
| ULINE | 481 | 2.1% | 85.9% |
| Bruno Folcieri Srl | 403 | 87.6% | 38.0% |
| Applied Industrial Technologie | 291 | 43.6% | 37.1% |
| MG AUTOMATION & CONTROLS | 265 | 60.8% | 74.3% |
| AMUT S.p.A. | 247 | 96.8% | 61.9% |
| Mayer Electric Supply | 147 | 25.9% | 60.5% |
| NRT (BHS supplier) | 135 | 20.7% | 36.3% |
| BHS (Bulk Handling Systems) | 118 | 96.6% | 50.0% |
| Bearing & Drive Supply | 95 | 15.8% | 35.8% |
| BALEMASTER | 11 | 81.8% | 90.9% |

---

## CRITICAL: Anti-Regression Protection Rules

**Before making ANY change to parser_core.py, you MUST follow these rules. Violating any of them will break proven functionality.**

### DO NOT TOUCH — Locked Behaviors

These behaviors are validated and working correctly. Do not modify the logic that produces them:

1. **Labeled PN extraction (PN:, MN:, MODEL:) is perfect.**
   - `BELT,V,SPC6300,RBR,GATES,PN: SPC6300` → MFG=GATES, PN=SPC6300 ✅
   - `INSERT,CPLG,LOVEJOY,MN: L150N` → MFG=LOVEJOY, PN=L150N ✅
   - `PWR SPLY UNIT,SIEMENS,PN:6EP1434-2BA20` → MFG=SIEMENS, PN=6EP1434-2BA20 ✅
   - **DO NOT change `extract_pn_labeled()`, `PN_LABEL_PATTERNS`, or the label confidence score (0.95).**

2. **ULINE catalog extraction is working at 85.9%.**
   - `H-10233` → PN=H-10233 ✅
   - `S-8155 Circle Labels - Months` → PN=S-8155 ✅
   - `S-25078 INVENTORY LABELS` → PN=S-25078 ✅
   - **DO NOT change `extract_pn_dash_catalog()` or the dash_catalog confidence (0.80).**

3. **Bare catalog number extraction works for pure alphanumeric entries.**
   - `91578A841` → PN=91578A841 ✅
   - `33145T32` → PN=33145T32 ✅
   - **DO NOT change the `pn_catalog` strategy or its confidence (0.60).**

4. **Distributor blocking is correct.** McMaster-Carr, ULINE, Applied Industrial, Mayer Electric, and Bearing & Drive correctly excluded from MFG. **DO NOT remove any entries from the `DISTRIBUTORS` set.**

5. **Known manufacturer matching works.** GATES, LOVEJOY, SIEMENS, PANDUIT, ALLEN BRADLEY, PILZ, ABB, etc. all match correctly via word-boundary regex. **DO NOT change the word-boundary logic in `extract_mfg_known()`.**

6. **Supplier-as-MFG fallback works for non-distributors.** Bruno Folcieri, AMUT, BHS, BALEMASTER all correctly fall back. **DO NOT change `_extract_mfg_from_supplier_value()` or `_clean_supplier_name()`.**

7. **Spec value rejection is working.** `2.2KW`, `480V`, `1800RPM`, `3PH` all correctly rejected as PNs. **DO NOT weaken `_is_spec_value()` or `SPEC_VALUE_RE`.**

8. **Post-extraction validation layer is working.** Short PNs (≤2 chars) correctly cleared. **DO NOT disable `validate_and_clean()` or reduce Rule 6 threshold.**

9. **Confidence scoring and pick_best() architecture is working.** The multi-strategy candidate collection + weighted best-pick approach is sound. **DO NOT flatten this back to a linear priority chain.**

### Mandatory Testing After Every Change

After EVERY modification, re-run the engine against WESCO.xlsx and verify:

```
✅ Labeled PN rows still extract correctly (spot check 5+ rows with PN: or MN:)
✅ ULINE PN fill rate ≥ 85%
✅ Bare catalog McMaster rows still extract (91578A841, 33145T32, etc.)
✅ GATES, LOVEJOY, SIEMENS still match as MFG in comma-delimited descriptions
✅ McMaster-Carr and ULINE are NOT appearing in MFG column
✅ Spec values (480V, 3PH, 2.2KW) are NOT appearing in PN column
✅ Total PN fill count ≥ 1,360 (current baseline — should only go UP)
✅ Total MFG fill count ≥ 1,120 (current baseline — should only go UP)
```

If any of these checks regress, **revert the change immediately** before continuing.

---

## Issues to Fix (Ordered by Impact)

### Issue 1: McMaster Comma-Delimited PN Extraction (HIGH — ~398 missed rows)

**Problem:** McMaster-Carr rows in `DESC,DESC,DESC,CATALOG_CODE` format are not extracting the trailing catalog code as PN. The engine only captures PNs when the Short Text IS the catalog code (bare), but misses it when it's the last token in a comma-delimited description.

**Examples of rows currently missed:**
```
"SWITCH,DISCONNECT,80A,7815N15"          → PN should be 7815N15
"ENCLOSURE,ELECTRICAL,7619K144"          → PN should be 7619K144
"SWITCH,EMERGENCY STOP,6741K46"          → PN should be 6741K46
"BLK,CONTACT,SWITCH,7557K2"             → PN should be 7557K2
"SWITCH,PANEL MOUNT,22MM,6749K201"       → PN should be 6749K201
"MOP,DUST,54",FIBERGLASS,7321T71"        → PN should be 7321T71
```

**Pattern:** The PN is typically the LAST comma-separated token, and it contains mixed alpha+digits while the preceding tokens are pure-alpha descriptors or spec values.

**Fix approach:** Add a new strategy `extract_pn_trailing_catalog()` that:
1. Splits the text on commas
2. Takes the last token
3. Validates it has mixed alpha+digits, length 5-15, and is NOT a spec value
4. Validates preceding tokens are mostly descriptors (all-alpha or spec patterns)
5. Assign confidence ~0.65-0.70

**Anti-regression guard:** This strategy must NOT fire on rows where a labeled PN (PN:, MN:) already exists. The `pick_best()` system handles this via confidence, but add an explicit check: if any labeled PN candidate exists in the candidates list, skip this strategy entirely. Also must NOT extract spec values like `480V` or dimension codes like `22MM` — reuse `_is_spec_value()` for filtering.

### Issue 2: Embedded Drive/Product Codes in MG AUTOMATION Rows (MEDIUM — ~50+ rows)

**Problem:** MG AUTOMATION rows have long embedded alphanumeric product codes that are clearly part numbers but aren't being extracted because `extract_pn_heuristic()` picks the wrong token or the code gets filtered.

**Examples:**
```
"DRV,3AXD50000731121,5HP,480V,BAGGING"  → PN should be 3AXD50000731121
"ACTR,ELEC,SELECTOR,3LD2418-0TK11"       → PN should be 3LD2418-0TK11
```

**Pattern:** The PN is typically the longest mixed-alpha+digit token in the comma list, and it's significantly longer than surrounding spec tokens.

**Fix approach:** Enhance `extract_pn_heuristic()` (or add a new `extract_pn_longest_code()` strategy) to:
1. Among all comma-separated tokens with mixed alpha+digits
2. Prefer the longest one that passes `_score_heuristic_pn() >= 0.40`
3. Currently the heuristic takes the LAST candidate — change to prefer the longest candidate when its score is significantly higher

**Anti-regression guard:** Do NOT change the return behavior when there's only one candidate. Only change selection logic when multiple candidates exist and there's a clear length/score winner. The `_score_heuristic_pn()` function already boosts long alphanumeric strings (+0.10 for ≥10 chars), so this should naturally score higher.

### Issue 3: False Positive MFG Extraction (MEDIUM — ~25 rows)

**Problem:** Several non-manufacturer tokens are being captured as MFG values:

| False MFG | Actual Meaning | Example Text |
|-----------|---------------|-------------|
| `TSEI` | Italian screw standard code | `SCREW,TSEI,M12X40,4100425` |
| `MC-VLV` | Valve type abbreviation | `VLV,SOL,MC-VLV,MN: 6311D-211-PM-111DA` |
| `UPPER` | Position descriptor | `SIEVE,CENTRAL,UPPER,S3110-0000359` |
| `DELABELER` | Equipment type | `SCREEN,NM,PLATE,C,DELABELER,PN:S3037-995` |
| `FIBERGLASS` | Material descriptor | `MOP,DUST,54",FIBERGLASS,7321T71` |
| `HAUSER` | Incomplete — should be `ENDRESS HAUSER` | `SW,LVL,LIMIT,ENDRESS,HAUSER,PN:FTE20` |

**Fix approach:**
1. Add to `MFG_BLOCKLIST`: `TSEI`, `TCEI`, `UPPER`, `LOWER`, `CENTRAL`, `FIBERGLASS`, `DELABELER`
2. Add to `DESCRIPTORS`: `TSEI`, `TCEI` (Italian screw standard codes)
3. Add to `NORMALIZE_MFG`: `'HAUSER': 'ENDRESS HAUSER'`, `'ENDRESS': 'ENDRESS HAUSER'`
4. Add `ENDRESS HAUSER` to `KNOWN_MANUFACTURERS`
5. Handle `MC-VLV` — add to `MFG_BLOCKLIST` (it's a valve type prefix, not a manufacturer)

**Anti-regression guard:** Before adding anything to `MFG_BLOCKLIST`, verify the token is NOT in `KNOWN_MANUFACTURERS`. The blocklist check in `sanitize_mfg()` already has this guard (`if x in MFG_BLOCKLIST and x not in KNOWN_MANUFACTURERS`), so this is safe. For the ENDRESS HAUSER normalization, test that both `ENDRESS,HAUSER` and `ENDRESS HAUSER` map correctly.

### Issue 4: BRU FOLC Not Normalizing (LOW — 5 rows)

**Problem:** `BRU FOLC` appears in Short Text as a manufacturer abbreviation but isn't being normalized to `BRUNO FOLCIERI`.

**Example:** `HOLDER,BLADE,BRU FOLC,PN: E1500`

**Fix:** Add `'BRU FOLC': 'BRUNO FOLCIERI'` to `NORMALIZE_MFG` dict.

**Anti-regression guard:** This is a safe dictionary addition. No logic changes needed.

### Issue 5: Bruno Folcieri Missing PN Extraction (LOW-MEDIUM — ~250 rows)

**Problem:** Many Bruno Folcieri rows have internal part codes embedded in the description that aren't being captured because they're in non-standard positions.

**Examples:**
```
"SCREW,CONVEYOR,BED,17000120500-01"      → PN should be 17000120500-01
"BOX,COUNTERSHAFT,4900047"               → PN should be 4900047
```

**Note:** Many Bruno Folcieri descriptions genuinely don't have extractable PNs (they're generic part descriptions like `SHAFT,SUPPORT,DP 250,REV1`). Don't force extraction where none exists.

**Fix approach:** The structured PN strategy (`extract_pn_structured()`) should catch `17000120500-01` since it has dashes. The issue is with codes like `4900047` which are pure numeric. Consider: if the last comma-token is a 7+ digit pure-numeric code and the row has no other PN candidate, treat it as a PN with confidence 0.50.

**Anti-regression guard:** Pure numeric extraction is risky — could match quantities, dimensions, or material numbers. ONLY apply to the last comma-token position, ONLY when length ≥ 7 digits, and ONLY when no other PN candidate scores above 0.50. Test against the full file to ensure this doesn't create false positives from the Material column values.

---

## Stretch Goals (Only After Issues 1-5 Are Clean)

### Stretch 1: NRT Context Awareness
`NRT` is being correctly identified as a known manufacturer (National Recovery Technologies), but in some BHS rows it appears as a department/location descriptor rather than the actual MFG. Low priority — the current behavior is defensible since NRT IS a real manufacturer name.

### Stretch 2: Mayer Electric Catalog Codes
Mayer Electric uses `RAC192`, `RAC2082`, `BLNB22SH120GLV` catalog-style codes that could be extracted as PNs but currently aren't because they lack dash/slash structure. Would require a supplier-context-aware PN strategy.

---

## File Structure Reference

```
engine/
├── parser_core.py          ← PRIMARY FILE TO MODIFY
├── file_profiler.py        ← File format detection (DO NOT MODIFY unless adding new archetype)
├── column_mapper.py        ← Column auto-detection (DO NOT MODIFY)
├── instruction_parser.py   ← NL instruction parsing (DO NOT MODIFY)
├── training.py             ← Training data loader (DO NOT MODIFY)
└── history_db.py           ← Job history storage (DO NOT MODIFY)
```

## Implementation Order

1. Fix Issue 4 (BRU FOLC normalization) — 30 seconds, zero risk
2. Fix Issue 3 (false positive MFGs) — blocklist/descriptor additions
3. Fix Issue 1 (McMaster comma-delimited PNs) — new strategy, highest impact
4. Fix Issue 2 (embedded drive codes) — heuristic enhancement
5. Fix Issue 5 (Bruno Folcieri numeric PNs) — careful, test-heavy

**After each fix: run the test, verify the anti-regression checklist, commit.**

---

## Phase 2: Edge Case Discovery Loop

**After completing Issues 1-5, DO NOT stop. Run this discovery protocol to find patterns the initial analysis missed.**

### Step 1: Re-Profile the Remaining Gaps

After all Phase 1 fixes, re-run the engine against WESCO.xlsx and export two DataFrames:
- `df_mfg_empty` — all rows where MFG is still blank after parsing
- `df_pn_empty` — all rows where PN is still blank after parsing

For each DataFrame, run this analysis:

```python
# Group remaining empty rows by supplier
for supplier in df_pn_empty['Supplier Name1'].unique():
    sub = df_pn_empty[df_pn_empty['Supplier Name1'] == supplier]
    print(f"\n=== {supplier}: {len(sub)} rows still missing PN ===")
    # Print 15 sample Short Text values
    for _, row in sub.head(15).iterrows():
        print(f"  {str(row['Short Text'])[:80]}")
```

Look for repeating patterns in the remaining empty rows. If 10+ rows share a common structure that could yield a valid extraction, document the pattern and propose a fix.

### Step 2: Supplier-Specific Pattern Audit

For EACH supplier with a PN fill rate below 60%, investigate WHY:

| Supplier | Current PN Fill | Investigation Required |
|----------|----------------|------------------------|
| McMaster-Carr | was 18.9%, check post-fix | Are remaining misses genuinely un-parseable? |
| Applied Industrial | 37.1% | What format are the missed rows? Do they have extractable codes? |
| Bruno Folcieri | 38.0% | After Issue 5 fix, what's left? Generic descriptions or hidden codes? |
| Bearing & Drive Supply | 35.8% | What does their Short Text look like? Same comma-delimited? |
| NRT (via BHS) | 36.3% | Internal codes? Labeled differently? |

For each supplier, sample 20 of their remaining empty-PN rows and categorize them:
- **Extractable but missed** — engine should catch this, needs a fix
- **Ambiguous** — could go either way, would need supplier context
- **Genuinely no PN present** — description-only rows, no code to extract

Only propose fixes for the "extractable but missed" category. Do NOT inflate fill rates by force-extracting ambiguous values.

### Step 3: False Positive Sweep

After all fixes, scan for NEW false positives introduced by the changes:

```python
# Check for suspicious PN values
for i, row in result.df.iterrows():
    pn = str(row.get('PN', '')).strip()
    if not pn or pn in ('', 'nan', 'None'):
        continue
    # Flag: PN is a common English word
    if pn in {'STOP', 'START', 'PANEL', 'MOUNT', 'BLACK', 'RED', 'BLUE',
              'GREEN', 'WHITE', 'STEEL', 'BRASS', 'COPPER', 'RUBBER',
              'FLAKE', 'COMPLETE', 'ASSEMBLY', 'REPLACEMENT', 'SPARE'}:
        print(f"  SUSPECT PN (english word): Row {i+2}, PN={pn}, Text={row.get('Short Text','')}")
    # Flag: PN is all-alpha with no digits
    if pn.isalpha():
        print(f"  SUSPECT PN (no digits): Row {i+2}, PN={pn}, Text={row.get('Short Text','')}")
    # Flag: PN is a dimension pattern
    if re.match(r'^\d+/?\d*(?:IN|MM|CM)
, pn, re.I):
        print(f"  SUSPECT PN (dimension): Row {i+2}, PN={pn}, Text={row.get('Short Text','')}")

# Check for suspicious MFG values
for i, row in result.df.iterrows():
    mfg = str(row.get('MFG', '')).strip()
    if not mfg or mfg in ('', 'nan', 'None'):
        continue
    # Flag: MFG that appears only 1-2 times (likely false positive)
    if mfg_counts[mfg] <= 2:
        print(f"  SUSPECT MFG (rare): Row {i+2}, MFG={mfg}, Text={row.get('Short Text','')}")
```

If any false positives are found, add the offending tokens to the appropriate blocklist/descriptor set and re-run.

### Step 4: Confidence Distribution Audit

Check the low-confidence items that were rejected by the threshold:

```python
# Analyze what's sitting below threshold
for item in result.low_confidence_items:
    print(f"  Row {item['row']}: {item['field']}={item['value']} "
          f"conf={item['confidence']:.2f} src={item['source']}")
```

Look for clusters: if 20+ low-confidence items share the same source strategy and the values look correct on manual inspection, the confidence scoring for that strategy may be too conservative. Propose a targeted confidence adjustment (never a blanket threshold reduction).

### Step 5: Cross-Validation Check

For rows where BOTH MFG and PN were extracted, verify they make sense together:
- Does the PN format match what that manufacturer typically uses?
- Is the MFG a plausible manufacturer for the item described?
- Are there rows where MFG was extracted from one strategy and PN from a different one — do they still align?

This catches cases where two independent strategies each found "something" but the combined result is nonsensical (e.g., MFG=GATES but PN is a McMaster catalog number).

### Step 6: Document Findings

After the discovery loop, produce a summary:
```
=== POST-REFINEMENT METRICS ===
Total rows:     2,684
MFG filled:     ____ (was 1,120)
PN filled:      ____ (was 1,360)
New issues found: ____
New fixes applied: ____
Remaining genuinely un-parseable rows: ____
```

For each remaining gap, categorize it as:
- **Addressable in v3.3** — needs a new strategy or data source
- **Requires training data** — pattern is too ambiguous without examples
- **Genuinely empty** — the source data has no extractable value

---

## Phase 3: Under-Explored Supplier Patterns

These are patterns I partially identified during the initial analysis but did NOT fully investigate. The discovery loop (Phase 2) should catch them, but flagging them here so you know where to look.

### Applied Industrial Technologie (291 rows, only 37.1% PN fill)

This supplier has multiple Short Text formats mixed together:
- Comma-delimited with MFG name: `VLV,BALL,2IN,316SS,DURA,20500H` (MFG+PN extractable)
- Comma-delimited description only: `BRG,PILLOW BLK,DIA 2-7/16IN,W 2.6875IN` (no PN present)
- Labeled: `REGU,PRES,150PSI,PARKER-H,MN: 06E22A13AC` (already captured)

The challenge is that some trailing tokens like `20500H` are real part numbers while others like `2-7/16IN` are dimensions. The Issue 1 trailing-catalog strategy should help here, but the `_is_spec_value()` filter needs to be tight enough to reject dimensions while accepting part numbers. `20500H` passes (mixed alpha+digits, no unit suffix). `2-7/16IN` should fail (ends in dimension unit). Verify this.

### Mayer Electric Supply (147 rows, only 25.9% MFG / 60.5% PN)

Mayer Electric uses distributor catalog codes as the Short Text:
- `RAC192 - 4SQ 1-1/2D BOX COMB KO` — the `RAC192` is a distributor catalog number, NOT a manufacturer PN
- `BLNB22SH120GLV - STRUT 12G` — these are Mayer's internal catalog codes

Decision needed: Are these catalog codes useful as PNs for Wesco's purposes? If yes, the `dash_catalog` strategy should already catch the `CODE - Description` format. If no, they should be filtered. **Ask the business team what they want here before building logic.**

MFG fill is low (25.9%) because Mayer Electric is correctly blocked as a distributor, and most of their descriptions don't contain manufacturer names. The 25.9% that ARE filled come from rows where a real MFG name appears in the text (like HUBBELL from prefix decode).

### Bearing & Drive Supply (95 rows, only 15.8% MFG / 35.8% PN)

Similar to Applied Industrial — they supply branded products from multiple manufacturers. Their descriptions often include the MFG name in the comma-delimited text:
- `BELT,V,SPC6300,RBR,GATES,PN: SPC6300` — already captured
- `ASSY,BRG,COMPLETE,SNL3140-KIT` — structured PN should catch `SNL3140-KIT`

The remaining misses are likely generic descriptions without embedded manufacturer names. The supplier-as-MFG fallback won't help because Bearing & Drive is listed as a distributor.

### National Recovery Technologies (135 rows, 20.7% MFG / 36.3% PN)

NRT is flagged as a known manufacturer, and BHS rows sometimes reference NRT parts. But NRT is also a distributor/technology provider for BHS's recycling equipment. The engine is currently treating NRT as a valid MFG in comma-delimited text, which may or may not be correct depending on context. Low priority — would need domain expertise to resolve.
