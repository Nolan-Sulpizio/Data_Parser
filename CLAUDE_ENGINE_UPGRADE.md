# CLAUDE.md — Engine Upgrade: Smart Column Detection + Training Data Pipeline

## Context
The Wesco MRO Parser (`mro-parser/`) currently works well on files with specific column names (Material Description, PO Text, MFG, PN). But real-world files from different Wesco clients use different column names, different layouts, and different description formats. The engine needs two upgrades to handle this:

1. **Smart Column Detection** — Automatically map any incoming file's columns to semantic roles
2. **Training Data Ingestion** — Learn from 600+ manually completed rows to expand MFG normalization, PN patterns, and column name variants

**CRITICAL: Do NOT modify the existing pipeline logic in `parser_core.py` beyond adding new imports and wiring. The extraction functions (`extract_pn_from_text`, `extract_mfg_from_text`, `sanitize_mfg`) work correctly. We are expanding what they know, not how they work.**

---

## Architecture Overview

```
User uploads file
        │
        ▼
┌─────────────────────┐
│  column_mapper.py   │  ← NEW: fuzzy-match columns to semantic roles
│  (Smart Detection)  │
└────────┬────────────┘
         │ mapped_columns = {source: [...], mfg_out: "...", pn_out: "..."}
         ▼
┌─────────────────────┐
│  instruction_parser  │  ← UPDATED: uses mapped columns instead of hardcoded
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  parser_core.py      │  ← UPDATED: loads training_data.json for expanded lookups
│  (Existing Engine)   │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  training.py         │  ← NEW: processes completed files → training_data.json
│  (One-time ingest)   │
└──────────────────────┘
```

---

## File 1: `engine/column_mapper.py` (NEW)

### Purpose
When a user uploads an Excel file, this module reads all column headers and maps them to semantic roles using fuzzy string matching + a learned dictionary of column name variants.

### Semantic Roles
```python
ROLES = {
    'source_description': [],   # Columns containing product descriptions to parse FROM
    'source_po_text': [],       # PO text / long text columns (secondary source)
    'source_notes': [],         # Notes / supplementary text columns
    'mfg_output': None,         # Column where MFG should be written TO
    'pn_output': None,          # Column where PN should be written TO
    'sim_output': None,         # Column where SIM should be written TO
    'item_number': None,        # Item/catalog number column (for SIM builder)
}
```

### Default Known Column Names (Seed Dictionary)
These are the known column name variants from Nolan's existing files. The training pipeline will expand this.

```python
DEFAULT_COLUMN_ALIASES = {
    'source_description': [
        'Material Description', 'MATERIAL DESCRIPTION', 'Description',
        'DESCRIPTION', 'Item Description', 'ITEM DESCRIPTION',
        'Mtrl Desc', 'LONG_TEXT', 'Long Text', 'Material Desc',
        'Product Description', 'Line Description', 'Short Description',
        'MATNR_DESC', 'Mat Description', 'DESC',
    ],
    'source_po_text': [
        'Material PO Text', 'PO Text', 'PO_TEXT', 'Purchase Order Text',
        'PO Description', 'PO Line Text', 'PO ITEM TEXT',
    ],
    'source_notes': [
        'Notes', 'NOTES', 'INFORECTXT1', 'INFORECTXT2', 'Comments',
        'Remarks', 'Additional Info',
    ],
    'mfg_output': [
        'MFG', 'Manufacturer', 'MANUFACTURER', 'Mfg', 'Manufacturer 1',
        'MFR', 'Brand', 'OEM', 'Vendor', 'VENDOR',
    ],
    'pn_output': [
        'PN', 'Part Number', 'PART NUMBER', 'Part Number 1', 'Part No',
        'Part #', 'PART#', 'Model Number', 'MODEL NUMBER', 'Catalog Number',
        'CAT NO', 'Item #', 'ITEM#', 'MFG Part Number',
    ],
    'sim_output': [
        'SIM', 'SIM Number', 'SIM #', 'SIM_NUMBER',
    ],
    'item_number': [
        'Item #', 'ITEM #', 'ITEM#', 'Item Number', 'Catalog #',
        'Cat #', 'CAT#', 'Stock Number',
    ],
}
```

### Core Function Signature
```python
def map_columns(df: pd.DataFrame, training_data: dict = None) -> dict:
    """
    Analyze a DataFrame's column headers and map them to semantic roles.
    
    Args:
        df: The uploaded DataFrame
        training_data: Optional dict from training_data.json with learned column mappings
    
    Returns:
        dict with keys matching ROLES, values are actual column names from df
    
    Algorithm:
    1. Exact match against DEFAULT_COLUMN_ALIASES + training_data aliases
    2. Case-insensitive match
    3. Fuzzy match using difflib.SequenceMatcher (threshold >= 0.7)
    4. Keyword containment match (e.g., column contains "desc" → source_description)
    5. For unmapped required roles, prompt user or return None
    """
```

### Keyword Containment Fallbacks
If fuzzy matching doesn't resolve, use substring patterns:
```python
KEYWORD_FALLBACKS = {
    'source_description': ['desc', 'material', 'text', 'long'],
    'source_po_text': ['po', 'purchase', 'order text'],
    'mfg_output': ['mfg', 'manuf', 'brand', 'vendor', 'oem'],
    'pn_output': ['part', 'pn', 'model', 'catalog', 'cat no'],
    'sim_output': ['sim'],
    'item_number': ['item', 'stock', 'catalog'],
}
```

### Integration Point
The `map_columns()` function should be called in `app.py` immediately after file import, BEFORE the instruction parser or pipeline runs. The returned mapping dict should be passed through to the pipeline functions.

---

## File 2: `engine/training.py` (NEW)

### Purpose
Process completed/ground-truth Excel files and extract patterns to improve the parsing engine. Outputs a `training_data.json` file that the engine loads at startup.

### Input
A directory of completed Excel files where MFG and PN columns are already filled in correctly by a human. These are in:
```
/Users/nolansulpizio/Desktop/Documents - Nolan's MacBook Pro/WESCO/Data Parse Agent/Data Context/
```

The function should also accept the `test_data/` directory within the mro-parser project.

### What to Extract

#### A. MFG Normalization Map Expansion
Scan all completed files. For each row where MFG is filled:
1. Get the MFG value from the output column
2. Get the raw description text from source columns
3. Find what substring in the description corresponds to the MFG
4. If the raw substring differs from the final MFG value, add it to the normalization map

Example: Description contains "CUTLR-HMR" but MFG column says "CUTLER-HAMMER" → add `"CUTLR-HMR": "CUTLER-HAMMER"` to the map.

Also build a **known_manufacturers** set — every unique normalized MFG value seen across all training files. This replaces the runtime mining of MANUFACTURER: labels.

#### B. PN Pattern Library
For each row where PN is filled:
1. Record the PN value
2. Record the source text it was extracted from
3. Record the MFG it was paired with
4. Build a frequency map of PN formats (e.g., "LETTERS-DIGITS", "DIGITS/LETTERS/DIGITS")

This helps the engine prioritize which candidate PN to select when multiple are found.

#### C. Column Name Dictionary
For each training file:
1. Record all column headers
2. Record which columns were used as source (description) vs. output (MFG, PN, SIM)
3. Add all new column name variants to the alias dictionary

This directly feeds `column_mapper.py`.

### Output Schema: `training_data.json`
```json
{
    "version": "1.0",
    "generated_at": "2026-02-16T...",
    "files_processed": 5,
    "total_rows_analyzed": 623,
    
    "mfg_normalization": {
        "CUTLR-HMR": "CUTLER-HAMMER",
        "PANDT": "PANDUIT",
        "USG CORP": "USG CORPORATION"
    },
    
    "known_manufacturers": [
        "PANDUIT", "CUTLER-HAMMER", "CROUSE HINDS", "APPLETON",
        "SQUARE D", "FOXBORO", "THOMAS & BETTS"
    ],
    
    "column_aliases": {
        "source_description": ["Material Description", "Item Description"],
        "mfg_output": ["MFG", "Manufacturer 1"]
    },
    
    "pn_patterns": {
        "format_frequency": {
            "ALPHA-NUMERIC": 234,
            "NUMERIC/ALPHA/NUMERIC": 45
        },
        "avg_length": 12.3,
        "max_valid_length": 28
    }
}
```

### Core Function Signatures
```python
def ingest_training_files(directory: str, output_path: str = 'training_data.json') -> dict:
    """
    Process all Excel files in directory and generate training_data.json.
    
    Args:
        directory: Path to folder containing completed Excel files
        output_path: Where to save the JSON output
    
    Returns:
        The training data dict
    
    Algorithm:
    1. Scan directory for .xlsx/.xls/.csv files
    2. For each file, use column_mapper to identify semantic roles
    3. For rows where MFG/PN are filled, extract patterns
    4. Aggregate across all files
    5. Merge with existing training_data.json if it exists (don't lose previous data)
    6. Write output
    """

def load_training_data(path: str = 'training_data.json') -> dict:
    """Load training data, returning empty defaults if file doesn't exist."""
```

### CLI Interface
```bash
# Run training ingestion
python -m engine.training /path/to/completed/files

# Or from within the app directory
python -c "from engine.training import ingest_training_files; ingest_training_files('/path/to/files')"
```

---

## File 3: Updates to `engine/parser_core.py`

### Changes Required (MINIMAL — don't break existing logic)

1. **At module load**, call `load_training_data()` and merge results into existing constants:
```python
# After existing NORMALIZE_MFG definition:
from engine.training import load_training_data
_training = load_training_data()
NORMALIZE_MFG.update(_training.get('mfg_normalization', {}))
KNOWN_MANUFACTURERS = set(_training.get('known_manufacturers', []))
```

2. **In `pipeline_mfg_pn()`**, replace the runtime `known_mfgs` mining with `KNOWN_MANUFACTURERS` as the seed set. Still mine from the current file, but start with the training data as a base:
```python
# Replace:
known_mfgs = set()
# With:
known_mfgs = set(KNOWN_MANUFACTURERS)  # Start with training data
```

3. **In `pipeline_mfg_pn()` signature**, accept a `column_mapping` parameter:
```python
def pipeline_mfg_pn(df, source_cols=None, mfg_col='MFG', pn_col='PN',
                     add_sim=True, column_mapping=None):
    # If column_mapping provided and source_cols not explicitly set,
    # use the mapping to determine source columns
    if column_mapping and not source_cols:
        source_cols = column_mapping.get('source_description', []) + \
                      column_mapping.get('source_po_text', []) + \
                      column_mapping.get('source_notes', [])
        mfg_col = column_mapping.get('mfg_output', mfg_col) or mfg_col
        pn_col = column_mapping.get('pn_output', pn_col) or pn_col
```

**DO NOT change any extraction logic, regex patterns, or QA rules.**

---

## File 4: Updates to `engine/instruction_parser.py`

### Changes Required

1. **In `parse_instruction()`**, accept and use `column_mapping`:
```python
def parse_instruction(text, available_columns=None, column_mapping=None):
    # If column_mapping is available, use it for source column detection
    # instead of hardcoded fallback list
```

2. **In the fallback auto-detect block**, replace hardcoded column names with column_mapping results:
```python
# Replace:
auto_sources = ['Material Description', 'Material PO Text', 'PO Text', ...]
# With:
if column_mapping:
    auto_sources = (column_mapping.get('source_description', []) +
                    column_mapping.get('source_po_text', []) +
                    column_mapping.get('source_notes', []))
else:
    auto_sources = ['Material Description', 'Material PO Text', ...]  # keep as fallback
```

---

## File 5: Updates to `app.py`

### Changes Required

1. **After file import**, call `map_columns()`:
```python
from engine.column_mapper import map_columns

# After loading the DataFrame:
column_mapping = map_columns(df, training_data=load_training_data())
```

2. **Pass `column_mapping` through** to both `parse_instruction()` and the pipeline functions.

3. **Add a "Train from Files" button** in the UI (or a menu option) that:
   - Opens a folder picker dialog
   - Calls `ingest_training_files(selected_folder)`
   - Shows a summary of what was learned (X new MFG entries, Y new column variants, Z total rows)
   - Reloads the training data into the engine

4. **On app startup**, load `training_data.json` if it exists.

---

## Implementation Order

1. Create `engine/column_mapper.py` with `map_columns()` function
2. Create `engine/training.py` with `ingest_training_files()` and `load_training_data()`
3. Update `engine/parser_core.py` — add training data loading + `column_mapping` parameter
4. Update `engine/instruction_parser.py` — use column_mapping in fallback detection
5. Update `app.py` — wire column_mapper into the import flow + add Train button
6. Run training ingestion against all completed files in Data Context
7. Run validation tests against Data Set 1 to confirm no regression
8. Run validation against a NEW file format to confirm column detection works

## Testing Checklist
- [ ] `column_mapper.py` correctly maps columns from Data Set 1 (known format)
- [ ] `column_mapper.py` correctly maps columns from a file with different column names
- [ ] `training.py` processes all completed files without errors
- [ ] `training_data.json` contains expanded MFG normalization map
- [ ] `training_data.json` contains known_manufacturers set larger than current hardcoded list
- [ ] `parser_core.py` loads training data on import
- [ ] `pipeline_mfg_pn()` accepts and uses column_mapping parameter
- [ ] Existing Data Set 1 accuracy is maintained or improved (no regression)
- [ ] A file with non-standard column names is correctly parsed
- [ ] "Train from Files" UI button works and shows results
- [ ] All existing tests still pass (21/21)

## Important Notes
- The training pipeline is a ONE-TIME batch process, not a per-request operation
- Training data persists in `training_data.json` — it survives app restarts
- New training files can be added incrementally (merge, don't replace)
- Column mapper runs per-file at import time — it's fast (header scanning only)
- Keep the engine 100% offline — no API calls
- If column_mapper can't confidently map a required column, show the user a mapping dialog in the UI
