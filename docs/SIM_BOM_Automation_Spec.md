# SIM (MFG + ITEM #) BOM Helper — End-to-End Spec

**Author:** Sulpizio, Nolan  
**Last updated:** 2026-02-16

---

## 1) Purpose
Automate creation and maintenance of **SIM** values in BOMs where **SIM = MFG + ITEM #**.

---

## 2) Inputs & Outputs

### Required Columns
- **MFG** — manufacturer (free text)
- **ITEM #** — part number (may include spaces, slashes, hyphens)
- **DESCRIPTION** — optional context
- **SIM** — target column to populate

### Missing SIM Definition
```
Missing when: SIM is (NaN) OR "" OR "0" OR 0 OR 0.0
```

### Outputs
1. **Missing SIMs — working list.xlsx** (Missing Items + Summary + By MFG tabs)
2. **Proposed SIMs — choose format.xlsx** (three proposed formats + CHOSEN_SIM column)
3. **Final BOM** with SIMs filled based on selected pattern

---

## 3) SIM Formatting Options

| Pattern | Format | Example |
|---------|--------|---------|
| **A** | `UPPER(MFG) + '-' + ITEM # (as-is)` | `PIP-50-N150G/L` |
| **B** | `UPPER(MFG) + ITEM # (spaces removed)` | `PIP50-N150G/L` |
| **C** | `UPPER(MFG) + '-' + ITEM # (alphanumeric only)` | `PIP-50N150GL` |

> **Recommendation:** Pattern C gives consistent keys across vendors.

---

## 4) Validation & QA
- **Uniqueness:** Check SIM duplicates post-fill, export duplicate report if found
- **Character policy:** If downstream systems forbid `/` or spaces, use Pattern C
- **Casing:** Force MFG to UPPER to avoid key drift
- **Null safety:** Guard against missing MFG/ITEM #; log and skip
- **Length check:** Alert if SIM exceeds downstream limits

---

## 5) Bot Flow
```
[Upload BOM] → [Normalize Columns] → [Find Missing SIMs] → [Generate Proposals A/B/C]
  → [User picks pattern] → [Apply fill to missing only]
  → [QA: duplicates, blanks, illegal chars] → [Export Final BOM + Reports]
```

---

## 6) Configuration
```yaml
sim_policy:
  pattern: C
  separator: '-'
  sanitize_alnum: true
  uppercase_mfg: true
  treat_zero_as_missing: true
  preserve_existing_sims: true
  duplicate_action: report
```

---

## 7) Edge Cases
- **ITEM # with slashes/hyphens/spaces** → sanitize if using Pattern C
- **Blank MFG or ITEM #** → cannot construct SIM; log to Exceptions sheet
- **Conflicting duplicates** → warning + duplicate report export
- **Inconsistent headers** (`ITEM#` vs `ITEM #`) → normalize to uppercase and known aliases

---

*Reference implementation: `engine/parser_core.py` → `pipeline_sim_builder()`*
