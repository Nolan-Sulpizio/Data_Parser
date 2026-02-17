"""
column_mapper.py — Smart Column Detection for MRO Parser

Maps arbitrary column names from uploaded files to semantic roles using:
  - Exact matching against known aliases
  - Case-insensitive matching
  - Fuzzy string matching (difflib)
  - Keyword containment patterns

No API calls required — pure offline matching.
"""

import pandas as pd
import difflib
import re
from typing import Optional

# ═══════════════════════════════════════════════════════════════
#  SEMANTIC ROLES
# ═══════════════════════════════════════════════════════════════

ROLES = {
    'source_description': [],   # Columns containing product descriptions to parse FROM
    'source_po_text': [],       # PO text / long text columns (secondary source)
    'source_notes': [],         # Notes / supplementary text columns
    'source_supplier': [],      # Supplier/vendor name columns (for MFG fallback)
    'mfg_output': None,         # Column where MFG should be written TO
    'pn_output': None,          # Column where PN should be written TO
    'sim_output': None,         # Column where SIM should be written TO
    'item_number': None,        # Item/catalog number column (for SIM builder)
    'supplier': None,           # Convenience single-value supplier column
}


# ═══════════════════════════════════════════════════════════════
#  DEFAULT KNOWN COLUMN ALIASES (Seed Dictionary)
# ═══════════════════════════════════════════════════════════════

DEFAULT_COLUMN_ALIASES = {
    'source_description': [
        'Material Description', 'MATERIAL DESCRIPTION', 'Description',
        'DESCRIPTION', 'Item Description', 'ITEM DESCRIPTION',
        'Mtrl Desc', 'LONG_TEXT', 'Long Text', 'Material Desc',
        'Product Description', 'Line Description', 'Short Description',
        'MATNR_DESC', 'Mat Description', 'DESC', 'Desc',
        'Item Desc', 'Product Desc',
        # v3: compressed short-text format (e.g. Wesco WESCO.xlsx)
        'Short Text', 'SHORT TEXT', 'Short_Text', 'ShortText',
        # v4: additional short/item text aliases
        'Short Desc', 'SHORT DESC', 'Item Text', 'ITEM TEXT',
        'Line Text', 'LINE TEXT', 'Mat Text', 'MAT TEXT',
        'Material Text', 'MATERIAL TEXT',
    ],
    'source_po_text': [
        'Material PO Text', 'PO Text', 'PO_TEXT', 'Purchase Order Text',
        'PO Description', 'PO Line Text', 'PO ITEM TEXT',
        'MATERIAL PO TEXT', 'Material PO TEXT',
    ],
    'source_notes': [
        'Notes', 'NOTES', 'INFORECTXT1', 'INFORECTXT2', 'Comments',
        'Remarks', 'Additional Info', 'INFO REC TXT 1', 'INFO REC TXT 2',
    ],
    'mfg_output': [
        'MFG', 'Manufacturer', 'MANUFACTURER', 'Mfg', 'Manufacturer 1',
        'MFR', 'Brand', 'OEM', 'Vendor', 'VENDOR', 'MFGR',
        'Manufacturer Name', 'MFG Name',
    ],
    'pn_output': [
        'PN', 'Part Number', 'PART NUMBER', 'Part Number 1', 'Part No',
        'Part #', 'PART#', 'Model Number', 'MODEL NUMBER', 'Catalog Number',
        'CAT NO', 'MFG Part Number', 'MFR Part Number',
        'Part No.', 'PART NO', 'Part Num',
    ],
    'sim_output': [
        'SIM', 'SIM Number', 'SIM #', 'SIM_NUMBER', 'SIM NUM',
    ],
    'item_number': [
        'Item #', 'ITEM #', 'ITEM#', 'Item Number', 'Catalog #',
        'Cat #', 'CAT#', 'Stock Number', 'ITEM NUMBER',
    ],
    # v3: supplier/vendor columns used as MFG fallback for Short Text files
    'source_supplier': [
        'Supplier Name1', 'Supplier Name 1', 'Supplier Name', 'Supplier',
        'SUPPLIER', 'SUPPLIER NAME', 'SUPPLIER NAME1', 'Vendor Name',
        'VENDOR NAME', 'Vendor', 'VENDOR',
    ],
}


# ═══════════════════════════════════════════════════════════════
#  KEYWORD FALLBACK PATTERNS
# ═══════════════════════════════════════════════════════════════

KEYWORD_FALLBACKS = {
    'source_description': ['desc', 'material', 'text', 'long', 'product', 'item desc', 'short text'],
    'source_po_text': ['po', 'purchase', 'order text'],
    'source_notes': ['note', 'info', 'comment', 'remark'],
    'source_supplier': ['supplier', 'vendor name'],
    'supplier': ['supplier', 'vendor'],
    'mfg_output': ['mfg', 'manuf', 'brand', 'oem', 'mfr'],
    'pn_output': ['part', 'pn', 'model', 'catalog', 'cat no', 'part no'],
    'sim_output': ['sim'],
    'item_number': ['item', 'stock', 'catalog'],
}


# ═══════════════════════════════════════════════════════════════
#  CORE MAPPING FUNCTION
# ═══════════════════════════════════════════════════════════════

def map_columns(df: pd.DataFrame, training_data: Optional[dict] = None) -> dict:
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
        5. For unmapped required roles, return None
    """
    # Initialize result with empty structure
    result = {
        'source_description': [],
        'source_po_text': [],
        'source_notes': [],
        'source_supplier': [],
        'mfg_output': None,
        'pn_output': None,
        'sim_output': None,
        'item_number': None,
        'supplier': None,
    }

    # Get available column names from DataFrame
    available_columns = list(df.columns)

    # Merge training data aliases with defaults
    column_aliases = DEFAULT_COLUMN_ALIASES.copy()
    if training_data and 'column_aliases' in training_data:
        for role, aliases in training_data['column_aliases'].items():
            if role in column_aliases:
                # Extend with training data, avoiding duplicates
                column_aliases[role] = list(set(column_aliases[role] + aliases))

    # Track which columns have been assigned to avoid duplicates
    assigned_columns = set()

    # ── Step 1-2: Exact and case-insensitive matching (all roles) ──
    for role in result.keys():
        aliases = column_aliases.get(role, [])

        for col in available_columns:
            if col in assigned_columns:
                continue

            # Try exact match
            if col in aliases:
                _assign_column(result, role, col, assigned_columns)
                continue

            # Try case-insensitive match
            col_lower = col.lower().strip()
            for alias in aliases:
                if col_lower == alias.lower().strip():
                    _assign_column(result, role, col, assigned_columns)
                    break

    # ── Step 3: Fuzzy matching with high threshold (0.85) ──
    for role in result.keys():
        aliases = column_aliases.get(role, [])

        for col in available_columns:
            if col in assigned_columns:
                continue

            col_lower = col.lower().strip()

            # Try fuzzy match with stricter threshold to avoid false positives
            for alias in aliases:
                ratio = difflib.SequenceMatcher(None, col_lower, alias.lower().strip()).ratio()
                if ratio >= 0.85:
                    _assign_column(result, role, col, assigned_columns)
                    break

    # ── Step 4: Keyword containment fallback ──
    for role, keywords in KEYWORD_FALLBACKS.items():
        for col in available_columns:
            if col in assigned_columns:
                continue

            col_lower = col.lower().strip()

            # Check if any keyword appears in the column name
            for keyword in keywords:
                if keyword.lower() in col_lower:
                    _assign_column(result, role, col, assigned_columns)
                    break

    # ── Step 5: Content validation for source_description columns ──
    # Remove columns that are primarily numeric (SAP IDs, material numbers, quantities).
    # These columns match keyword patterns (e.g. "material" in column name "Material") but
    # contain numeric data, not parseable text descriptions.
    validated_desc = []
    for col in result.get('source_description', []):
        if col not in df.columns:
            continue
        sample = df[col].dropna().head(50).astype(str)
        if len(sample) == 0:
            validated_desc.append(col)  # Keep empty columns; can't disqualify on no data
            continue
        text_ratio = sum(1 for v in sample if any(c.isalpha() for c in str(v))) / len(sample)
        if text_ratio >= 0.3:  # At least 30% of sampled values contain letters
            validated_desc.append(col)
    result['source_description'] = validated_desc

    # ── Convenience: populate single-value 'supplier' from source_supplier list ──
    if result.get('supplier') is None and result.get('source_supplier'):
        result['supplier'] = result['source_supplier'][0]

    return result


def _assign_column(result: dict, role: str, col_name: str, assigned_set: set):
    """
    Helper to assign a column to a role and track it in assigned_set.

    For list roles (source_*), append to the list.
    For single roles (output_*, item_number), set as single value.
    """
    if role.startswith('source_'):
        # Source columns can have multiple values
        if col_name not in result[role]:
            result[role].append(col_name)
            assigned_set.add(col_name)
    else:
        # Output columns are single value - only assign if not already set
        if result[role] is None:
            result[role] = col_name
            assigned_set.add(col_name)


# ═══════════════════════════════════════════════════════════════
#  VALIDATION & REPORTING
# ═══════════════════════════════════════════════════════════════

def validate_mapping(mapping: dict, strict: bool = False) -> tuple[bool, list[str]]:
    """
    Validate that a column mapping has the minimum required fields.

    Args:
        mapping: Result from map_columns()
        strict: If True, require both mfg_output and pn_output

    Returns:
        (is_valid, list_of_issues)
    """
    issues = []

    # Check that we have at least one source column
    all_sources = (mapping.get('source_description', []) +
                   mapping.get('source_po_text', []) +
                   mapping.get('source_notes', []))

    if not all_sources:
        issues.append("No source columns detected. Need at least one description/text column.")

    # Check output columns (if strict mode)
    if strict:
        if not mapping.get('mfg_output'):
            issues.append("No MFG output column detected.")
        if not mapping.get('pn_output'):
            issues.append("No PN output column detected.")

    return (len(issues) == 0, issues)


def suggest_columns(df: pd.DataFrame, mapping: Optional[dict] = None) -> dict:
    """
    Analyze DataFrame columns and return UI-ready suggestions for the column selector.

    Wraps map_columns() and adds content-based confidence scoring so the UI can
    pre-select the most likely source columns and explain the reasoning.

    Args:
        df: The uploaded DataFrame
        mapping: Optional pre-computed result from map_columns(); computed if not given

    Returns:
        {
            'source_suggestions': [
                {'column': str, 'letter': str, 'confidence': float, 'reason': str},
                ...  # sorted by confidence descending
            ],
            'supplier_suggestion': {'column': str, 'letter': str, ...} | None,
        }
    """
    if mapping is None:
        mapping = map_columns(df)

    suggestions: dict = {'source_suggestions': [], 'supplier_suggestion': None}
    cols = list(df.columns)

    # Aggregate all source column candidates across all source roles
    all_source_cols = (
        mapping.get('source_description', [])
        + mapping.get('source_po_text', [])
        + mapping.get('source_notes', [])
    )

    seen: set = set()
    for col in all_source_cols:
        if col in seen or col not in df.columns:
            continue
        seen.add(col)

        idx = cols.index(col)
        letter = chr(ord('A') + idx) if idx < 26 else f"Col{idx + 1}"

        # Content-based confidence scoring
        sample = df[col].dropna().head(20).astype(str)
        if len(sample) > 0:
            avg_len = sample.str.len().mean()
            text_pct = sum(1 for v in sample if any(c.isalpha() for c in v)) / len(sample)
        else:
            avg_len = 0.0
            text_pct = 0.0

        confidence = 0.5
        if text_pct > 0.8:
            confidence += 0.30
        if avg_len > 15:
            confidence += 0.15
        confidence = min(confidence, 0.99)

        reason = f"{text_pct:.0%} text · avg {avg_len:.0f} chars"
        suggestions['source_suggestions'].append({
            'column': col,
            'letter': letter,
            'confidence': confidence,
            'reason': reason,
        })

    # Sort by confidence descending so highest-confidence columns appear first
    suggestions['source_suggestions'].sort(key=lambda x: x['confidence'], reverse=True)

    # Supplier suggestion (first match only — used as MFG fallback)
    sup_cols = mapping.get('source_supplier', [])
    if sup_cols:
        col = sup_cols[0]
        if col in cols:
            idx = cols.index(col)
            letter = chr(ord('A') + idx) if idx < 26 else f"Col{idx + 1}"
            suggestions['supplier_suggestion'] = {
                'column': col,
                'letter': letter,
                'confidence': 0.80,
                'reason': 'Header matches supplier/vendor pattern',
            }

    return suggestions


def format_mapping_summary(mapping: dict) -> str:
    """
    Generate a human-readable summary of the column mapping.

    Returns:
        Multi-line string describing the mapping
    """
    lines = ["Column Mapping Summary:"]
    lines.append("=" * 50)

    # Source columns
    sources = mapping.get('source_description', [])
    if sources:
        lines.append(f"  Description Sources: {', '.join(sources)}")

    po_sources = mapping.get('source_po_text', [])
    if po_sources:
        lines.append(f"  PO Text Sources: {', '.join(po_sources)}")

    notes_sources = mapping.get('source_notes', [])
    if notes_sources:
        lines.append(f"  Notes Sources: {', '.join(notes_sources)}")

    # Output columns
    if mapping.get('mfg_output'):
        lines.append(f"  MFG Output → {mapping['mfg_output']}")
    else:
        lines.append("  MFG Output → [not detected]")

    if mapping.get('pn_output'):
        lines.append(f"  PN Output → {mapping['pn_output']}")
    else:
        lines.append("  PN Output → [not detected]")

    if mapping.get('sim_output'):
        lines.append(f"  SIM Output → {mapping['sim_output']}")

    if mapping.get('item_number'):
        lines.append(f"  Item Number → {mapping['item_number']}")

    return '\n'.join(lines)
