# Electrical MFG/PN Parsing Agent — End-to-End Specification

**Author:** Sulpizio, Nolan  
**Context:** Electrical PN_MFG Search cleanup  
**Last updated:** 2026-02-16

---

## 1) Goal & Scope
Create a repeatable "agent" that reads **unstructured item descriptions** and **PO text** from an Excel file, extracts a **Manufacturer (MFG)** and a **Part Number (PN)**, normalizes common spellings/abbreviations, and returns a clean workbook suitable for SIM creation, spend/vendor analysis, and stocking.

**Primary sources (columns):**
- **Material Description** (priority)
- **Material PO Text** (fallback)
- **PO Text** (second fallback when present)

**Targets (columns to produce/overwrite):**
- **MFG** (column A)
- **PN** (column B)

Optionally: **SIM** (`MFG + ' ' + PN`).

---

## 2) Data Assumptions
- Each row may contain a mix of uppercase descriptors, vendor names, and model numbers.
- Labels like **`MANUFACTURER:`**, **`PN:`**, **`P/N:`**, **`MODEL NUMBER:`**, **`MODEL:`**, **`MN:`** appear frequently and are the **most reliable sources**.
- If no labels exist, we select tokens that **look like part numbers** (letters+digits, often with dashes) and ignore obvious noise (e.g., `1/2IN`, `SPDT`).
- MFG strings should **not** be a distributor (e.g., GRAYBAR, CED), a descriptor (e.g., LVL, CTRL), or contain digits.

---

## 3) Extraction Rules (Deterministic)

### 3.1 PN Extraction (ordered by priority)
1. **Labeled fields** (first match wins):
   - `PN:` / `P/N:` / `PART NUMBER:`
   - `MODEL NUMBER:` / `MODEL:` / `MN:` / `C/N:`
2. **Heuristic fallback** if (1) fails:
   - Split on whitespace/commas/semicolons.
   - Keep tokens containing **both letters & digits** (and/or `-` `/` `_` `.`) with a max length ~25.
   - **Exclude** units & generic tokens (e.g., `EA`, `AC`, `DC`, and dimensional forms like `1/2IN`).

### 3.2 MFG Extraction (ordered by priority)
1. **Explicit label**: `MANUFACTURER: <MFG>` (stop at next label/period/comma/end).
2. **Pre-label pattern**: `, <MFG>, PN:` or `, <MFG>, MODEL:`.
3. **Known manufacturers library** mined from other rows (anything that follows `MANUFACTURER:` across the file).
4. **Context with PN hint**: `, <MFG>, <PN>` if `<PN>` is known.

### 3.3 Sanitization / Rejection Filters
- Reject MFGs that are **distributors** (e.g., GRAYBAR, CED) or **descriptors** (LVL, CTRL, FIBRE OPTIC).
- Reject MFGs containing **digits**.
- Trim spaces, collapse multiple spaces, unify case to **UPPER**.

---

## 4) Normalization Map (canonical manufacturer names)
Update/extend as needed **before** parsing runs. The agent applies this after extraction:

```python
NORMALIZE_MFG = {
    'PANDT': 'PANDUIT',
    'CUTLR-HMR': 'CUTLER-HAMMER',
    'APLTN': 'APPLETON',
    'CROUS HIND': 'CROUSE HINDS',
    'CROUSE-HINDS': 'CROUSE HINDS',
    'EFECTOR': 'IFM EFECTOR',
    'TOPWRX': 'TOPWORX',
    'ELCTRO': 'ELECTRO-SENSORS',
    'TELCO SYSTEMS': 'TELCO',
    'T&BETTS': 'THOMAS & BETTS',
    'FXBRO': 'FOXBORO',
    'FXBRO INVN': 'FOXBORO',
    'WATLOW-E': 'WATLOW',
    'WATTS-RG': 'WATTS',
    'MONITOR': 'MONITOR TECHNOLOGIES LLC',
    'MONITEUR': 'MONITEUR DEVICES',
    'SOUTHWRE': 'SOUTHWIRE',
    'USG CORP': 'USG CORPORATION',
    'STATIC O RING': 'STATIC O-RING',
}
```

**Canonical preferences:**
- `CROUSE HINDS` (no hyphen)
- `SQUARE D` (no hyphen)
- `STATIC O-RING` (hyphenated)

---

## 5) Implementation Notes & Edge Cases
- **PowerFlex 755** lines should be **MFG = Allen-Bradley / Rockwell Automation**, not GE.
- **Distributors** (GRAYBAR, CED, etc.) should **not** be set as MFG.
- **BALSTON** filters may show `PN=BALSTON` in raw text; use the specific element PN instead.
- **Static O-Ring** spelling unified: `STATIC O-RING`.
- **CROUSE HINDS** hyphenation unified to **no hyphen**.
- Keep **SIM** deterministic: `f"{MFG} {PN}"` (trimmed).

---

## 6) Deliverables Produced by This Agent
- `*.xlsx` with cleaned **MFG**, **PN**, and **SIM** columns.
- Optional `* - QA Open Issues.xlsx` listing all questionable rows with flags and notes for rapid triage.

---

## 7) Ops Checklist
1. Freeze top row & enable filters.
2. Add a simple pivot: **Rows = MFG**, **Values = Count of Materials** (Top 10 brands).
3. Keep "Open Issues" workbook/tab and note blockers.

---

*Reference implementation: `engine/parser_core.py` → `pipeline_mfg_pn()`*
