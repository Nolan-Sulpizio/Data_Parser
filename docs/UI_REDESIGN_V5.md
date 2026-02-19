# MRO Parser UI Redesign — V5.0 Spec
## "Impossible to Get Wrong"

**Author:** Nolan Sulpizio & Co-founder  
**Date:** February 18, 2026  
**Status:** Ready for Claude Code Implementation  
**Branch:** `feature/ui-v5-streamlined`

---

## The Problem (What's Broken)

The current UI (v4.x) was built iteratively, feature-by-feature. The result is a power-user interface that a BDA who didn't build it will fumble through. Here's every UX friction point from the screenshots:

| # | Problem | Why It Hurts Performance |
|---|---------|--------------------------|
| 1 | **Sidebar with 3 nav pages** (Parser / History / Saved Configs) | Users click around confused before doing the one thing they came to do |
| 2 | **Quick Templates in sidebar** (MFG+PN Extract, Part Number Clean, Build SIM Values) | Implies multiple modes — but 95% of usage is MFG+PN Extract. Templates create a choice where there shouldn't be one |
| 3 | **"How to Use" expander** | If you need instructions, the UI already failed |
| 4 | **SOURCE COLUMNS checkboxes for ALL columns** | Shows 7-9 checkboxes. Users don't know which ones matter. The "Unnamed: 1, 2, 3..." problem on messy files makes this useless |
| 5 | **OUTPUT PLACEMENT radio** (end vs front) | Unnecessary choice — always append at end. Two options = one more way to mess up |
| 6 | **SUPPLIER COLUMN dropdown** | "Optional — used as MFG fallback" means nothing to a BDA. They either skip it (losing accuracy) or pick wrong |
| 7 | **Custom Instruction (Advanced) expander** | Legacy from text-instruction era. The column-first design made this obsolete |
| 8 | **Re-run (reconfigure) / Export / Save Config** — 3 buttons post-run | Too many choices after parsing. User just wants the file |
| 9 | **Input/Output toggle on preview** | Cognitive overhead for no value |
| 10 | **~XX chars column hints** on right side | Noise that doesn't help selection decisions |
| 11 | **Data Preparation Tips** buried at bottom | Nobody scrolls down to read tips before running |

**Core diagnosis:** The UI exposes the engine's internal architecture to the user. Users don't need to understand pipelines, supplier fallbacks, or output placement. They need to point at data and get MFG + PN out.

---

## The Redesign Philosophy

### Three Rules

1. **One screen, one flow.** No navigation. No pages. No tabs.
2. **Smart defaults eliminate choices.** The engine should figure out what the user would have configured manually.
3. **The only way to use it IS the right way.** Every possible click path produces correct output.

### The User Flow (3 Steps, Zero Decisions)

```
┌─────────────────────────────────────────────────┐
│                                                   │
│   STEP 1: DROP FILE                              │
│   ───────────────                                │
│   Giant drag zone. Click or drag .xlsx/.csv.     │
│   File loads → auto-scan columns.                │
│                                                   │
│   STEP 2: CONFIRM COLUMNS                        │
│   ───────────────────                            │
│   Engine auto-selects the best source column(s). │
│   User sees a SMART PREVIEW showing what the     │
│   engine detected. Can override if needed.        │
│   Supplier column auto-detected, shown inline.   │
│                                                   │
│   STEP 3: CLICK "PARSE"                          │
│   ──────────────────                             │
│   One big green button. Progress bar.            │
│   Auto-exports to same directory as source file. │
│   Shows summary: "2,684 rows → 1,593 MFG /       │
│   1,813 PN extracted. File saved."               │
│                                                   │
└─────────────────────────────────────────────────┘
```

---

## Detailed UI Specification

### Layout: Single Panel, No Sidebar

Kill the sidebar entirely. The app is ONE vertically-scrolling panel, centered, max-width 800px, with generous padding. Think of it like a form, not a dashboard.

```
┌──────────────────────────────────────────────┐
│  [W] WESCO   MRO Data Parser          v5.0  │
│──────────────────────────────────────────────│
│                                              │
│  ┌────────────────────────────────────────┐  │
│  │                                        │  │
│  │     📁  Drop Excel file here           │  │
│  │         or click to browse             │  │
│  │                                        │  │
│  │     .xlsx  .xls  .csv                  │  │
│  └────────────────────────────────────────┘  │
│                                              │
│  ── after file loads ──                      │
│                                              │
│  ✓ WESCO_Empty.xlsx                          │
│    2,684 rows • 9 columns                    │
│                                              │
│  SOURCE DATA  (where MFG/PN info lives)      │
│  ┌────────────────────────────────────────┐  │
│  │ ✅ E: Short Text          ← auto-pick │  │
│  │ ☐  A: Supplier Name1                  │  │
│  │ ☐  D: Material                        │  │
│  └────────────────────────────────────────┘  │
│  Only shows columns likely to contain data.  │
│  Irrelevant columns (Plant, Date, Org)       │
│  are hidden by default.                      │
│                                              │
│  SUPPLIER HINT  (helps identify MFG)         │
│  ┌────────────────────────────────────────┐  │
│  │ Auto-detected: Supplier Name1     [✓]  │  │
│  └────────────────────────────────────────┘  │
│                                              │
│  PREVIEW  (sample of what engine will do)    │
│  ┌────────────────────────────────────────┐  │
│  │ Row 1: "S-17080 - ANTIBACTERIAL HAND  │  │
│  │        SOAP" → MFG: ULINE  PN: S-17080│  │
│  │ Row 4: "PWR SPLY UNIT,SIEMENS,        │  │
│  │        PN:6EP1434-28A20"              │  │
│  │        → MFG: SIEMENS  PN: 6EP1434... │  │
│  │ Row 5: "CKT BRKR,MINTR,40A,48/96VDC, │  │
│  │        EATON,19Y..." → MFG: EATON     │  │
│  │        PN: 19YG89                      │  │
│  └────────────────────────────────────────┘  │
│  Shows 3-5 representative rows so user can   │
│  visually confirm engine is reading the      │
│  right column before committing.             │
│                                              │
│  ┌────────────────────────────────────────┐  │
│  │                                        │  │
│  │         ▶  PARSE FILE                  │  │
│  │                                        │  │
│  └────────────────────────────────────────┘  │
│  One big button. Green. Unmissable.          │
│                                              │
│  ── after parse completes ──                 │
│                                              │
│  ✅ COMPLETE                                 │
│  2,684 rows processed                        │
│  MFG filled: 1,593 (59%)                     │
│  PN filled: 1,813 (68%)                      │
│  Issues: 1,966                               │
│                                              │
│  📄 Saved: WESCO_Empty_parsed.xlsx           │
│  📊 QA Report: WESCO_Empty_QA.csv            │
│                                              │
│  [Open File Location]   [Parse Another File] │
│                                              │
└──────────────────────────────────────────────┘
```

---

## What Gets REMOVED (Kill List)

These features are being removed from the UI. The engine functionality stays — we're just hardcoding the smart defaults instead of exposing choices.

| Feature | Disposition |
|---------|-------------|
| **Sidebar navigation** | REMOVED. Single page. |
| **History page** | REMOVED from v5 UI. History DB stays in engine for future analytics. |
| **Saved Configs page** | REMOVED. Auto-detection replaces manual config. |
| **Quick Templates** | REMOVED. Engine auto-detects pipeline (MFG+PN is default). |
| **"How to Use" section** | REMOVED. UI is self-explanatory. |
| **Custom Instruction (Advanced)** | REMOVED. Column-first design obsoleted this. |
| **OUTPUT PLACEMENT radio** | REMOVED. Always append MFG + PN at end. Hardcode `position='end'`. |
| **Input/Output preview toggle** | REMOVED. Show only the smart preview. |
| **~XX chars hints** | REMOVED. Replaced by smart preview showing actual parsed samples. |
| **Data Preparation Tips** | REMOVED. If file has issues, show inline warning during scan. |
| **"Save Config" button** | REMOVED. |
| **"Re-run (reconfigure)" button** | REPLACED by "Parse Another File" which resets to Step 1. |
| **Separate Export button** | REMOVED. Auto-export on completion. |

---

## What Gets ADDED (Smart Defaults)

### 1. Auto-Column Detection (The Key Innovation)

When a file loads, the engine should automatically identify:

**Source columns** — columns most likely to contain MFG/PN data. Scoring heuristic:

```python
def score_column_for_parsing(col_name: str, sample_values: list[str]) -> float:
    """Score 0-100 how likely this column contains parseable MFG/PN data."""
    score = 0
    name_lower = col_name.lower().strip()
    
    # Column name signals (high confidence)
    high_signal_names = ['short text', 'description', 'item description', 
                         'material description', 'part description', 'item']
    medium_signal_names = ['material', 'product', 'catalog', 'item #',
                           'part', 'part number', 'mfg part']
    
    if any(sig in name_lower for sig in high_signal_names):
        score += 50
    elif any(sig in name_lower for sig in medium_signal_names):
        score += 30
    
    # Content signals (sample the first 20 non-empty values)
    samples = [str(v) for v in sample_values[:20] if pd.notna(v) and str(v).strip()]
    if samples:
        avg_len = sum(len(s) for s in samples) / len(samples)
        if avg_len > 15:  # Descriptions tend to be longer
            score += 20
        
        # Contains commas, hyphens, mixed alpha-numeric (description-like)
        desc_pattern_count = sum(1 for s in samples 
                                  if ',' in s or '-' in s or 
                                  (any(c.isalpha() for c in s) and any(c.isdigit() for c in s)))
        if desc_pattern_count / len(samples) > 0.3:
            score += 20
        
        # Contains known MFG names in values
        mfg_hints = ['eaton', 'siemens', 'hubbell', 'allen bradley', 'schneider',
                     'abb', '3m', 'ge ', 'honeywell', 'square d']
        has_mfg = sum(1 for s in samples 
                      if any(m in s.lower() for m in mfg_hints))
        if has_mfg > 0:
            score += 10
    
    # Negative signals (definitely NOT a source column)
    skip_names = ['plant', 'date', 'organization', 'purch', 'order', 'quantity',
                  'document', 'unnamed', 'unit', 'uom', 'price', 'cost', 
                  'total', 'currency', 'po ', 'po#']
    if any(skip in name_lower for skip in skip_names):
        score = max(score - 60, 0)
    
    return min(score, 100)
```

**Supplier column** — auto-detect the supplier/vendor column:

```python
def detect_supplier_column(columns: list[str]) -> str | None:
    """Find the supplier column automatically."""
    supplier_signals = ['supplier', 'vendor', 'vendor name', 'supplier name',
                        'mfg name', 'manufacturer name']
    for col in columns:
        if any(sig in col.lower() for sig in supplier_signals):
            return col
    return None
```

**Display logic:**
- Auto-check the highest-scoring column (score > 40)
- Show only columns with score > 10 in the selector (hide the garbage)
- If a file has "Unnamed: 1, 2, 3..." columns, peek at row values and use the FIRST row as a pseudo-header hint, showing: `"B: Unnamed:1 (e.g., 'HUBBELL 40A BREAKER...')"` so the user can visually identify what's in each column

### 2. Smart Preview (Live Parse Sample)

After column selection, immediately parse 3-5 sample rows and show the results inline. This lets the user visually confirm the engine is reading the right data BEFORE processing 2,684 rows.

```python
def generate_preview(df: pd.DataFrame, source_cols: list[str], 
                     supplier_col: str | None, n_samples: int = 5) -> list[dict]:
    """Parse a small sample to show the user what the engine will do."""
    # Pick diverse samples: first row, middle row, rows with different suppliers
    sample_indices = pick_diverse_samples(df, n_samples)
    preview_rows = []
    
    for idx in sample_indices:
        row = df.iloc[idx]
        source_text = ' | '.join(str(row[c]) for c in source_cols if pd.notna(row[c]))
        supplier_hint = str(row[supplier_col]) if supplier_col and pd.notna(row[supplier_col]) else None
        
        # Run the parser on just this one row
        mfg, pn, flags = parse_single_row(source_text, supplier_hint)
        
        preview_rows.append({
            'row_num': idx + 1,
            'source_text': source_text[:80] + ('...' if len(source_text) > 80 else ''),
            'mfg': mfg or '—',
            'pn': pn or '—',
            'confidence': 'high' if mfg and pn else 'partial' if mfg or pn else 'none'
        })
    
    return preview_rows
```

Display with color coding: green for high confidence, yellow for partial, gray for no extraction.

### 3. Auto-Export (No Export Button)

When parsing completes, automatically save:
- `{original_name}_parsed.xlsx` — the output file with MFG + PN appended
- `{original_name}_QA.csv` — the QA report

Save to the SAME DIRECTORY as the source file. Show the file paths and an "Open File Location" button.

### 4. Inline File Validation Warnings

Instead of "Data Preparation Tips" buried at the bottom, show warnings inline immediately after file load:

```
⚠ 3 columns have no headers (showing as "Unnamed"). 
  The engine will use row content to identify data.

⚠ 847 rows have empty description fields.
  These rows will have blank MFG/PN output.
```

---

## Component Architecture

### Single-File UI Structure

```python
class WescoMROParser(ctk.CTk):
    """V5 — Streamlined single-panel interface."""
    
    def __init__(self):
        # Window setup (smaller — no sidebar means less width needed)
        self.geometry("900x700")
        self.minsize(750, 600)
        
        # State
        self.current_file = None
        self.df_input = None
        self.df_output = None
        self.source_col_vars = {}    # {col_name: BooleanVar} — only scored columns
        self.supplier_col = None     # Auto-detected, shown as info
        self.is_processing = False
        
        # Build single scrollable panel
        self._build_header()         # Logo + version
        self._build_dropzone()       # File import
        self._build_column_panel()   # Hidden until file loads
        self._build_preview_panel()  # Hidden until columns selected  
        self._build_parse_button()   # Hidden until columns selected
        self._build_results_panel()  # Hidden until parse completes
    
    # ── Flow Control ──
    
    def _on_file_loaded(self, filepath):
        """File dropped/selected → scan and show column panel."""
        self.df_input = read_excel_smart(filepath)
        scores = {col: score_column_for_parsing(col, self.df_input[col].tolist()) 
                  for col in self.df_input.columns}
        self.supplier_col = detect_supplier_column(self.df_input.columns)
        self._show_column_panel(scores)
        self._update_preview()
    
    def _on_columns_changed(self):
        """User toggled a column checkbox → refresh preview."""
        self._update_preview()
    
    def _on_parse_clicked(self):
        """Big green button → run full parse in background thread."""
        selected_cols = [c for c, var in self.source_col_vars.items() if var.get()]
        if not selected_cols:
            self._show_error("Select at least one source column")
            return
        self._run_parse_async(selected_cols)
    
    def _on_parse_complete(self, result):
        """Parse done → auto-export and show results."""
        self._auto_export(result)
        self._show_results_panel(result)
```

### What Stays From Current Engine

The engine layer (`parser_core.py`, `column_mapper.py`, etc.) is UNTOUCHED. We're only rebuilding the UI layer (`app.py`). This means:

- `pipeline_mfg_pn()` — same extraction logic
- `run_qa()` — same QA reporting
- `suggest_columns()` — enhanced with the new scoring heuristic
- `detect_supplier_column()` — new helper, lives in `column_mapper.py`
- `parse_single_row()` — new helper for preview, wraps existing pipeline for one row

---

## Implementation Sequence for Claude Code

### Phase 1: Strip & Scaffold (Branch: `feature/ui-v5-streamlined`)

```
1. Create new branch from main
2. Back up current app.py → app_v4_backup.py  
3. Gut app.py — remove:
   - _build_sidebar() and all sidebar components
   - _show_history(), _show_configs() 
   - Template buttons and template logic
   - Custom instruction panel
   - Output placement radio
   - Input/Output preview toggle
   - "How to Use" section
4. Replace with single-panel layout:
   - _build_header()
   - _build_dropzone()  
   - _build_column_panel()
   - _build_preview_panel()
   - _build_parse_button()
   - _build_results_panel()
5. Window geometry: 900x700 (narrower, no sidebar)
```

### Phase 2: Smart Column Detection

```
1. Add score_column_for_parsing() to column_mapper.py
2. Add detect_supplier_column() to column_mapper.py
3. Column panel shows ONLY columns with score > 10
4. Auto-check columns with score > 40
5. Handle "Unnamed" columns by showing sample values
6. Supplier column shown as auto-detected info line (not a dropdown)
```

### Phase 3: Smart Preview

```
1. Add parse_single_row() wrapper to parser_core.py
2. Add generate_preview() to parser_core.py or new preview.py
3. Preview panel shows 3-5 sample rows with color-coded results
4. Preview auto-refreshes when column selection changes
5. Pick diverse samples (different suppliers, different complexity)
```

### Phase 4: Auto-Export & Results

```
1. On parse complete → auto-save _parsed.xlsx and _QA.csv
2. Save to same directory as source file
3. Results panel shows metrics + file paths
4. "Open File Location" button (os.startfile on Windows, open on Mac)  
5. "Parse Another File" button resets to Step 1
```

### Phase 5: Polish & Edge Cases

```
1. Drag-and-drop visual feedback (border glow on hover)
2. Processing progress bar with row count
3. Error states: invalid file, no extractable columns, empty file
4. File validation warnings (unnamed columns, empty fields)
5. Keyboard shortcut: Enter to parse, Escape to reset
6. Window title shows current file name during processing
```

---

## Regression Safety

**CRITICAL:** The engine is NOT changing. Only `app.py` is being rewritten. This means:

- All existing test suites pass without modification
- Golden test snapshots remain valid
- Parser accuracy is unchanged — we're just feeding it better inputs via smart defaults
- `parser_core.py`, `column_mapper.py`, `instruction_parser.py` get **additions only** (new helper functions), never modifications to existing functions

The only net-new engine code:
- `score_column_for_parsing()` — new function in column_mapper.py
- `detect_supplier_column()` — new function in column_mapper.py  
- `parse_single_row()` — new function in parser_core.py (thin wrapper)
- `generate_preview()` — new function (can live in a new `preview.py`)

---

## Success Criteria

After this redesign, the following must be true:

1. **A brand new BDA can use the tool in under 30 seconds** with zero training
2. **There is no configuration that produces worse results** than the auto-defaults
3. **The number of clicks from launch to exported file is ≤ 5** (open file, confirm column, click parse, done)
4. **The smart preview catches misconfiguration** before a full parse runs
5. **All existing test suites pass** with zero changes to test code
6. **Window is smaller and feels faster** — no visual clutter, no decision anxiety

---

## Claude Code Prompt

Copy this directly into Claude Code to execute the implementation:

```
Read CLAUDE.md for project context. We're doing a UI-only redesign of app.py.
Branch: feature/ui-v5-streamlined

PHILOSOPHY: Strip everything. One screen. Three steps. Impossible to get wrong.

DO:
- Back up app.py → app_v4_backup.py
- Rewrite app.py as a single-panel interface (no sidebar, no nav, no tabs)
- Add score_column_for_parsing() and detect_supplier_column() to column_mapper.py
- Add parse_single_row() to parser_core.py  
- Auto-detect best source column, auto-detect supplier column
- Show smart preview (3-5 sample parsed rows) before full run
- Auto-export to source file directory on completion
- One big green "PARSE FILE" button
- "Parse Another File" to reset

DON'T:
- Don't modify ANY existing function in parser_core.py or column_mapper.py
- Don't remove History/Saved Configs from the engine DB layer — just from the UI
- Don't change the BRAND colors or Wesco logo loading
- Don't break any existing tests

Refer to docs/UI_REDESIGN_V5.md for full wireframe and component spec.
```
