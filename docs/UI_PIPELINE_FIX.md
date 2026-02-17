# UI-to-Engine Pipeline Fix — instruction_parser.py + app.py + column_mapper.py

## The Problem

When users interact with the Wesco MRO Parser app, results are dramatically worse than when the engine is called directly with correct parameters. This is because three layers between the user and the engine are misconfiguring the pipeline call.

**Proven performance gap (WESCO.xlsx, 2,684 rows):**

| Configuration | MFG Filled | PN Filled |
|--------------|-----------|----------|
| App (template click) | **0** | 2,684 (all garbage) |
| Direct engine call | **1,120** | **1,360** |

The engine works. The wiring doesn't.

---

## Root Cause Analysis

### Failure 1: Instruction Parser False-Matches Column Names

**File:** `engine/instruction_parser.py`, lines ~120-128

The template instruction is: `"Extract MFG and PN from Material Description and PO Text into MFG and PN columns"`

The instruction parser loops through the file's actual column names and checks if each column name appears as a substring in the instruction text:

```python
for col in available_columns:
    col_clean = col.strip().lower()
    if col_clean in t_lower:
        result.source_columns.append(col)
```

The file has a column called `Material` (SAP material numbers like `4102073838`). The word "material" appears in the instruction template ("Material Description"), so the parser matches `Material` as a source column — **wrong column**.

Meanwhile `Short Text` (the actual description column with parseable data like `BELT,V,SPC6300,RBR,GATES,PN: SPC6300`) is never matched because "short text" doesn't appear in the template.

**Result:** `parsed.source_columns = ['Material']` with 100% confidence — confidently wrong.

### Failure 2: app.py Never Passes supplier_col

**File:** `app.py`, lines 1035-1041

```python
result = pipeline_mfg_pn(
    self.df_input, source_cols,
    mfg_col=parsed.target_mfg_col,
    pn_col=parsed.target_pn_col,
    add_sim=parsed.add_sim,
    column_mapping=self.column_mapping,
    # ← supplier_col is NEVER passed
)
```

The column mapper correctly detects `Supplier Name1` as a supplier column (`source_supplier: ['Supplier Name1']`), but `_execute_pipeline()` never reads this from the mapping and never passes it to the pipeline. This completely disables the supplier-as-MFG fallback, which is responsible for 800+ of the 1,120 MFG fills on this file.

### Failure 3: Column Mapper Includes SAP Numbers as Description

**File:** `engine/column_mapper.py`, KEYWORD_FALLBACKS

The column mapper returns `source_description: ['Short Text', 'Material']` because the keyword fallback matches "material" in the column name `Material`. But this is the SAP material NUMBER column, not a material DESCRIPTION column.

---

## Fixes Required

### Fix 1: app.py — Always Pass supplier_col (CRITICAL, 2 minutes)

In `_execute_pipeline()`, extract the supplier column from `self.column_mapping` and pass it to the pipeline.

**Current code (line 1035-1041):**
```python
result = pipeline_mfg_pn(
    self.df_input, source_cols,
    mfg_col=parsed.target_mfg_col,
    pn_col=parsed.target_pn_col,
    add_sim=parsed.add_sim,
    column_mapping=self.column_mapping,
)
```

**Fixed code:**
```python
# Extract supplier column from mapping
supplier_col = None
if self.column_mapping:
    supplier_col = self.column_mapping.get('supplier')

result = pipeline_mfg_pn(
    self.df_input, source_cols,
    mfg_col=parsed.target_mfg_col,
    pn_col=parsed.target_pn_col,
    add_sim=parsed.add_sim,
    column_mapping=self.column_mapping,
    supplier_col=supplier_col,
)
```

Also apply the same fix to the default/fallback pipeline call (line 1063):
```python
result = pipeline_mfg_pn(self.df_input, source_cols,
                          column_mapping=self.column_mapping,
                          supplier_col=supplier_col)
```

**Anti-regression:** This is purely additive. If `supplier_col` is None (no supplier column detected), behavior is unchanged.

### Fix 2: instruction_parser.py — Prevent False Column Matching (CRITICAL, 15 minutes)

The current matching logic does bare substring checks. Replace with a smarter approach:

**Problem code (lines ~120-128):**
```python
for col in available_columns:
    col_clean = col.strip().lower()
    if col_clean in t_lower:
        result.source_columns.append(col)
```

**Fix approach — require EXACT column name match, not substring:**

```python
for col in available_columns:
    col_clean = col.strip().lower()
    # EXACT match: the column name must appear as a standalone phrase in the instruction,
    # not as a substring of another word. Use word-boundary-like matching.
    # "Material" should NOT match "Material Description" — those are different concepts.
    # "Short Text" SHOULD match "from Short Text column"
    pattern = r'(?<![a-z])' + re.escape(col_clean) + r'(?![a-z])'
    if re.search(pattern, t_lower):
        # Extra guard: if the column name is a single common word (<=8 chars),
        # require it to be preceded by "from", "in", "column", or "col" to avoid
        # false matches on words that happen to also be column names.
        if len(col_clean) <= 8 and not re.search(
            r'(?:from|in|column|col\.?)\s+' + re.escape(col_clean), t_lower
        ):
            continue  # Skip ambiguous short matches
        result.source_columns.append(col)
```

**AND — add column_mapper fallback when instruction parser finds nothing useful:**

After the instruction parser's source column detection (end of step 2), add:

```python
# If no source columns matched from instruction text, fall back to column_mapper
if not result.source_columns and column_mapping:
    auto_sources = (column_mapping.get('source_description', []) +
                   column_mapping.get('source_po_text', []) +
                   column_mapping.get('source_notes', []))
    result.source_columns = auto_sources
```

This already exists as a fallback (lines 133-148) but it's gated behind `not result.source_columns`. The problem is that the false match on `Material` means `result.source_columns` is NOT empty, so the fallback never fires. The fix above prevents the false match from happening in the first place.

**Anti-regression:** The fallback to column_mapper only fires when the instruction parser finds zero matches, which is the same as the current behavior for instructions that genuinely don't mention column names. The word-boundary matching is strictly more conservative than the current substring matching.

### Fix 3: column_mapper.py — Don't Map Numeric Columns as Description Sources (MEDIUM, 10 minutes)

**Problem:** The keyword fallback matches "material" in `Material` column name, but this column contains SAP numeric IDs, not text descriptions.

**Fix approach — validate column content before assigning as description source:**

After the keyword fallback matching, add a validation step:

```python
# ── Step 5: Content validation for source_description columns ──
# Remove columns that are primarily numeric (SAP IDs, quantities, dates)
# These match keyword patterns but don't contain parseable text
validated_desc = []
for col in result.get('source_description', []):
    if col not in df.columns:
        continue
    sample = df[col].dropna().head(50).astype(str)
    if len(sample) == 0:
        continue
    # Check: does the column contain mostly text (with letters)?
    text_ratio = sum(1 for v in sample if any(c.isalpha() for c in str(v))) / len(sample)
    if text_ratio >= 0.3:  # At least 30% of non-null values contain letters
        validated_desc.append(col)
result['source_description'] = validated_desc
```

This would remove `Material` (SAP numbers like `4102073838`) from `source_description` while keeping `Short Text` (actual text descriptions).

**Anti-regression:** This only removes columns from `source_description` that are >=70% pure-numeric. Columns with real text content (even sparse) are preserved. The threshold of 30% is conservative — Short Text has 100% text content.

### Fix 4: Dynamic Templates That Adapt to the Loaded File (HIGH VALUE, 20 minutes)

**Problem:** The hardcoded templates reference column names that may not exist in the user's file:

```python
templates = [
    ("MFG + PN Extract", "Extract MFG and PN from Material Description and PO Text into MFG and PN columns"),
    ...
]
```

**Fix approach — generate templates dynamically based on column_mapping:**

When `_load_file()` completes and `self.column_mapping` is populated, regenerate the template buttons with instructions that reference the ACTUAL detected columns:

```python
def _update_templates(self):
    """Regenerate quick templates based on detected columns."""
    if not self.column_mapping:
        return

    desc_cols = self.column_mapping.get('source_description', [])
    supplier_col = self.column_mapping.get('supplier')
    
    source_text = ' and '.join(desc_cols) if desc_cols else 'description columns'

    templates = [
        ("MFG + PN Extract",
         f"Extract MFG and PN from {source_text}"),
        ("Part Number Clean",
         "Clean and validate part numbers from description fields"),
        ("Build SIM Values",
         "Generate SIM from MFG and ITEM # for rows with missing SIM"),
    ]

    # Clear existing template buttons and rebuild
    # ... (rebuild sidebar template section with new instructions)
```

Call `_update_templates()` at the end of `_load_file()` after `self.column_mapping` is set.

Also update the placeholder examples to be file-aware:

```python
def _update_placeholders(self):
    if not self.column_mapping:
        return
    desc_cols = self.column_mapping.get('source_description', [])
    if desc_cols:
        self.placeholder_examples[0] = f"Extract MFG and PN from {desc_cols[0]}"
```

**Anti-regression:** Templates are regenerated on file load. If no file is loaded, the original generic templates remain. If column_mapping is empty, the original generic templates remain.

### Fix 5: Nuclear Fallback — column_mapper Takes Priority Over Bad Instruction Matches (SAFETY NET)

Even after Fixes 1-4, there will be edge cases where a user types something that triggers a false column match. Add a safety net in `_execute_pipeline()`:

```python
# SAFETY: If instruction parser returned source columns that don't look like text columns,
# prefer the column_mapper's source_description instead
if source_cols and self.column_mapping:
    mapper_sources = (self.column_mapping.get('source_description', []) +
                     self.column_mapping.get('source_po_text', []) +
                     self.column_mapping.get('source_notes', []))
    
    if mapper_sources and source_cols != mapper_sources:
        # Verify instruction parser's columns contain text
        for col in source_cols:
            if col in self.df_input.columns:
                sample = self.df_input[col].dropna().head(20).astype(str)
                text_pct = sum(1 for v in sample if any(c.isalpha() for c in str(v))) / max(len(sample), 1)
                if text_pct < 0.3:
                    # This column is mostly numeric — instruction parser got it wrong
                    source_cols = mapper_sources
                    break
```

**Anti-regression:** This only overrides the instruction parser when a source column is demonstrably non-text (>=70% numeric). In normal files where "Material Description" IS the column name, the parser's match is correct and this check passes harmlessly.

---

## Implementation Order

1. **Fix 1** (supplier_col in app.py) — 2 minutes, zero risk, massive MFG improvement
2. **Fix 2** (instruction parser word-boundary matching) — 15 minutes, prevents the root cause
3. **Fix 3** (column_mapper content validation) — 10 minutes, fixes secondary confusion
4. **Fix 4** (dynamic templates) — 20 minutes, best UX improvement
5. **Fix 5** (nuclear fallback) — 10 minutes, safety net

**After each fix, test by:**
1. Loading WESCO.xlsx in the app
2. Clicking "MFG + PN Extract" template
3. Verifying the "Interpreted as" feedback shows `Short Text` as source (not `Material`)
4. Running the parser and confirming MFG filled >= 1,100 and PN filled >= 1,300

---

## Files to Modify

```
app.py                          ← Fix 1 (supplier_col), Fix 4 (dynamic templates), Fix 5 (safety net)
engine/instruction_parser.py    ← Fix 2 (word-boundary matching + column_mapper fallback)
engine/column_mapper.py         ← Fix 3 (content validation for description sources)
```

**DO NOT MODIFY:**
- `engine/parser_core.py` — the engine is working correctly; this prompt fixes the layers ABOVE it
- `engine/file_profiler.py` — not involved in this issue
- `engine/training.py` — not involved
- `engine/history_db.py` — not involved
