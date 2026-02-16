"""
instruction_parser.py — Offline natural language instruction interpreter.

Maps user instructions like "pull MFG and PN from Material Description"
to structured pipeline configurations. No API calls — pure keyword matching.
"""

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ParsedInstruction:
    """Structured interpretation of a user's natural language instruction."""
    pipeline: str = 'auto'          # 'mfg_pn', 'part_number', 'sim', 'auto', 'custom'
    source_columns: list = field(default_factory=list)
    target_mfg_col: str = 'MFG'
    target_pn_col: str = 'PN'
    target_sim_col: str = 'SIM'
    add_sim: bool = False
    sim_pattern: str = 'space'      # 'space', 'dash', 'compact', 'A', 'B', 'C'
    confidence: float = 0.0
    explanation: str = ''


# ═══════════════════════════════════════════════════════════════
#  KEYWORD DICTIONARIES
# ═══════════════════════════════════════════════════════════════

PIPELINE_SIGNALS = {
    'mfg_pn': [
        r'\bmfg\b', r'\bmanufacturer\b', r'\bpart\s*number\b', r'\bpn\b',
        r'\bextract\s+mfg\b', r'\bpull\s+mfg\b', r'\bparse\s+mfg\b',
        r'\belectrical\b', r'\bmaterial\s+description\b',
    ],
    'part_number': [
        r'\bpart\s*number\s*(only|clean|reprocess|extract)\b',
        r'\bclean\s+part\s*numbers?\b', r'\breprocess\b',
        r'\bstrict\s+pn\b', r'\bvalidate\s+pn\b',
    ],
    'sim': [
        r'\bsim\b', r'\bbom\b', r'\bconcatenat', r'\bcombine\s+mfg',
        r'\bmfg\s*\+\s*item\b', r'\bmissing\s+sim\b', r'\bbuild\s+sim\b',
        r'\bgenerate\s+sim\b', r'\bfill\s+sim\b',
    ],
}

COLUMN_PATTERNS = {
    # Source columns - expanded synonyms for generic terms
    'material_description': [
        r'\bmaterial\s+desc',           # "material description"
        r'\bdescription\s+col',         # "description column"
        r'\bdesc\s+col',                # "desc column"
        r'\bthe\s+description',         # "the description"
        r'\bfrom\s+description\b',      # "from description"
        r'\bdescription\b',             # "description" (fallback)
    ],
    'material_po_text': [
        r'\bmaterial\s+po\s+text\b',
        r'\bpo\s+text\b',
        r'\bpo\s+col',                  # "PO column"
    ],
    'notes': [r'\bnotes?\b', r'\binforec'],
    # Target columns
    'mfg': [r'\bmfg\b', r'\bmanufacturer\b', r'\bmaker\b', r'\bbrand\b', r'\boem\b'],
    'pn': [r'\bpn\b', r'\bpart\s*num', r'\bmodel\s*num', r'\bitem\s*#?\b', r'\bpart\s*#?\b'],
    'sim': [r'\bsim\b'],
}

# Detect explicit column references like "column A", "col B", "columns C and D"
COL_LETTER_RE = re.compile(r'(?:column|col\.?)\s*([A-Z])', re.IGNORECASE)
COL_RANGE_RE = re.compile(r'(?:columns?|cols?\.?)\s*([A-Z])\s*(?:and|&|,|through|to|-)\s*([A-Z])', re.IGNORECASE)

SIM_PATTERN_MAP = {
    'dash': ['dash', 'hyphen', 'pattern a', 'pattern-a'],
    'compact': ['compact', 'no separator', 'no space', 'pattern b', 'pattern-b'],
    'C': ['alphanumeric', 'sanitize', 'clean', 'pattern c', 'pattern-c'],
    'space': ['space', 'default'],
}


# ═══════════════════════════════════════════════════════════════
#  PARSER
# ═══════════════════════════════════════════════════════════════

def parse_instruction(text: str, available_columns: list[str] = None) -> ParsedInstruction:
    """
    Interpret a natural language instruction and return a structured config.

    Args:
        text: User's instruction string.
        available_columns: Column headers from the uploaded Excel file.
    """
    result = ParsedInstruction()
    t = text.strip()
    t_lower = t.lower()
    t_upper = t.upper()

    if not t:
        result.explanation = "No instruction provided. Will attempt auto-detection."
        result.pipeline = 'auto'
        return result

    # ── 1) Detect pipeline type ──
    scores = {}
    for pipeline, patterns in PIPELINE_SIGNALS.items():
        score = sum(1 for p in patterns if re.search(p, t_lower))
        scores[pipeline] = score

    best_pipeline = max(scores, key=scores.get) if max(scores.values()) > 0 else 'auto'
    result.pipeline = best_pipeline

    # Calculate confidence with boost for source column references
    base_confidence = min(max(scores.values()) / 3.0, 1.0)

    # Boost confidence if we detect source column references (description, PO text, etc.)
    source_col_patterns = COLUMN_PATTERNS.get('material_description', []) + \
                         COLUMN_PATTERNS.get('material_po_text', []) + \
                         COLUMN_PATTERNS.get('notes', [])
    source_col_matches = sum(1 for p in source_col_patterns if re.search(p, t_lower))

    if source_col_matches > 0:
        # Boost confidence: if we detected both pipeline AND source column, treat as high confidence
        result.confidence = min(base_confidence + 0.33, 1.0)
    else:
        result.confidence = base_confidence

    # ── 2) Detect source columns ──
    if available_columns:
        # Try to match mentioned column names to actual columns
        for col in available_columns:
            # Check if column name appears in the instruction
            col_clean = col.strip().lower()
            if col_clean in t_lower or col_clean.replace(' ', '_') in t_lower.replace(' ', '_'):
                result.source_columns.append(col)

    # Also check for column letter references ("column C", "col D")
    letter_matches = COL_LETTER_RE.findall(t)
    range_matches = COL_RANGE_RE.findall(t)

    if available_columns and (letter_matches or range_matches):
        # Convert letter references to actual column names
        all_letters = set(letter_matches)
        for start, end in range_matches:
            for i in range(ord(start.upper()), ord(end.upper()) + 1):
                all_letters.add(chr(i))

        for letter in all_letters:
            idx = ord(letter.upper()) - ord('A')
            if idx < len(available_columns):
                col_name = available_columns[idx]
                if col_name not in result.source_columns:
                    result.source_columns.append(col_name)

    # Fallback: auto-detect common source columns
    if not result.source_columns and available_columns:
        auto_sources = ['Material Description', 'Material PO Text', 'PO Text',
                        'MATERIAL DESCRIPTION', 'DESCRIPTION', 'Notes',
                        'INFORECTXT1', 'INFORECTXT2']
        for col in available_columns:
            if col.strip() in auto_sources or any(s.lower() in col.lower() for s in auto_sources):
                result.source_columns.append(col)

    # ── 3) Detect target columns ──
    # Check for "into column A" / "in column B" patterns
    into_pattern = re.compile(r'(?:into|in|to)\s+(?:column|col\.?)\s*([A-Z])', re.IGNORECASE)
    into_matches = into_pattern.findall(t)

    if len(into_matches) >= 2 and available_columns:
        idx0 = ord(into_matches[0].upper()) - ord('A')
        idx1 = ord(into_matches[1].upper()) - ord('A')
        if idx0 < len(available_columns):
            result.target_mfg_col = available_columns[idx0]
        if idx1 < len(available_columns):
            result.target_pn_col = available_columns[idx1]
    elif len(into_matches) == 1 and available_columns:
        idx0 = ord(into_matches[0].upper()) - ord('A')
        if idx0 < len(available_columns):
            # Guess based on keyword context
            if any(re.search(p, t_lower) for p in COLUMN_PATTERNS['mfg']):
                result.target_mfg_col = available_columns[idx0]
            elif any(re.search(p, t_lower) for p in COLUMN_PATTERNS['pn']):
                result.target_pn_col = available_columns[idx0]

    # ── 4) Detect SIM preferences ──
    if re.search(r'\bsim\b', t_lower) or result.pipeline == 'sim':
        result.add_sim = True
        for pattern_key, keywords in SIM_PATTERN_MAP.items():
            if any(kw in t_lower for kw in keywords):
                result.sim_pattern = pattern_key
                break

    # Also add SIM if user says "and SIM" or "with SIM"
    if re.search(r'(?:and|with|plus|also|include)\s+sim\b', t_lower):
        result.add_sim = True

    # ── 5) Build explanation ──
    parts = [f"Pipeline: {result.pipeline}"]
    if result.source_columns:
        parts.append(f"Source columns: {', '.join(result.source_columns)}")
    parts.append(f"Target: MFG→{result.target_mfg_col}, PN→{result.target_pn_col}")
    if result.add_sim:
        parts.append(f"SIM: enabled (pattern={result.sim_pattern})")
    parts.append(f"Confidence: {result.confidence:.0%}")
    result.explanation = ' | '.join(parts)

    return result


def auto_detect_pipeline(df) -> str:
    """Auto-detect the best pipeline based on column names."""
    cols_upper = [c.upper().strip() for c in df.columns]

    # SIM BOM pattern
    if 'ITEM #' in cols_upper or 'ITEM#' in cols_upper:
        if 'SIM' in cols_upper:
            return 'sim'

    # MFG/PN Electrical pattern
    if any('MATERIAL' in c for c in cols_upper):
        return 'mfg_pn'

    # Part Number pattern
    if any('PART NUMBER' in c for c in cols_upper):
        return 'part_number'

    # Generic MFG/PN
    if 'MFG' in cols_upper or 'MANUFACTURER' in cols_upper:
        return 'mfg_pn'

    return 'mfg_pn'  # default
