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
    'mfg_output': None,         # Column where MFG should be written TO
    'pn_output': None,          # Column where PN should be written TO
    'sim_output': None,         # Column where SIM should be written TO
    'item_number': None,        # Item/catalog number column (for SIM builder)
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
}


# ═══════════════════════════════════════════════════════════════
#  KEYWORD FALLBACK PATTERNS
# ═══════════════════════════════════════════════════════════════

KEYWORD_FALLBACKS = {
    'source_description': ['desc', 'material', 'text', 'long', 'product', 'item desc'],
    'source_po_text': ['po', 'purchase', 'order text'],
    'source_notes': ['note', 'info', 'comment', 'remark'],
    'mfg_output': ['mfg', 'manuf', 'brand', 'vendor', 'oem', 'mfr'],
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
        'mfg_output': None,
        'pn_output': None,
        'sim_output': None,
        'item_number': None,
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
