"""
parser_core.py — Unified MRO parsing engine.

Combines logic from:
  - MFG_PN_Parsing_Agent_Spec.md (electrical MFG/PN extraction)
  - MRO_Part_Number_Processing_Spec.md (part number cleaning)
  - SIM_BOM_Automation_Spec.md (SIM generation)

All processing is deterministic — no API calls required.
"""

import re
import pandas as pd
from dataclasses import dataclass, field
from typing import Optional

# ═══════════════════════════════════════════════════════════════
#  CONFIGURATION — externalize later to JSON for business users
# ═══════════════════════════════════════════════════════════════

NORMALIZE_MFG = {
    'PANDT': 'PANDUIT', 'CUTLR-HMR': 'CUTLER-HAMMER', 'APLTN': 'APPLETON',
    'CROUS HIND': 'CROUSE HINDS', 'CROUSE-HINDS': 'CROUSE HINDS',
    'EFECTOR': 'IFM EFECTOR', 'TOPWRX': 'TOPWORX',
    'ELCTRO': 'ELECTRO-SENSORS', 'TELCO SYSTEMS': 'TELCO',
    'T&BETTS': 'THOMAS & BETTS', 'FXBRO': 'FOXBORO', 'FXBRO INVN': 'FOXBORO',
    'WATLOW-E': 'WATLOW', 'WATTS-RG': 'WATTS',
    'MONITOR': 'MONITOR TECHNOLOGIES LLC', 'MONITEUR': 'MONITEUR DEVICES',
    'SOUTHWRE': 'SOUTHWIRE', 'USG CORP': 'USG CORPORATION',
    'STATIC O RING': 'STATIC O-RING', 'SQUARE-D': 'SQUARE D',
}

DISTRIBUTORS = {'GRAYBAR', 'CED', 'MC- MC', 'MC-MC', 'MCNAUGHTON-MCKAY', 'EISI'}
DESCRIPTORS = {'LVL', 'CTRL', 'FIBRE OPTIC', 'EF-11', 'EF 2', 'EF1 1/2', 'EF 1 1/2', 'EF1/2'}

DESCRIPTOR_KEYWORDS = [
    'SWITCH', 'TRANSMITTER', 'CONNECTOR', 'THERMOCOUPLE', 'CABLE', 'VALVE',
    'RELAY', 'SENSOR', 'HEAD', 'CONTACTOR', 'MODULE', 'FAN', 'BEACON',
    'BRUSH', 'PLUG', 'RECEPTACLE', 'REGULATOR',
]

PN_LABEL_PATTERNS = [
    r"PN\s*[:#]\s*([A-Z0-9][A-Z0-9\-_/\. ]{0,60})",
    r"P\s*/\s*N\s*[:#]\s*([A-Z0-9][A-Z0-9\-_/\. ]{0,60})",
    r"PART\s+NUMBER\s*[:#]\s*([A-Z0-9][A-Z0-9\-_/\. ]{0,60})",
    r"MODEL\s+NUMBER\s*[:#]\s*([A-Z0-9][A-Z0-9\-_/\. ]{0,60})",
    r"MODEL\s*[:#]\s*([A-Z0-9][A-Z0-9\-_/\. ]{0,60})",
    r"MN\s*[:#]\s*([A-Z0-9][A-Z0-9\-_/\. ]{0,60})",
    r"C\s*/\s*N\s*[:#]?\s*([A-Z0-9][A-Z0-9\-_/\. ]{0,60})",
    r"MFR\s+PART\s+NUMBER\s*[:#]?\s*([A-Z0-9][A-Z0-9\-_/\. ]{0,60})",
    r"MFR\s+NUMBER\s*[:#]?\s*([A-Z0-9][A-Z0-9\-_/\. ]{0,60})",
    r"MFG\s+NUMBER\s*[:#]?\s*([A-Z0-9][A-Z0-9\-_/\. ]{0,60})",
]

MFG_LABEL_RE = re.compile(
    r"MANUFACTURER:\s*([A-Z0-9\-&\./\s]+?)(?=\s+(?:MODEL|PART|PN|P/N|MN|PRODUCT|SERIES|MODEL NUMBER|PART NUMBER)\b|[,.]|$)"
)
PRELABEL_MFG_RE = re.compile(
    r",\s*([A-Z][A-Z0-9\-&\./\s]{2,40}?)\s*,\s*(?:PN|P\s*/\s*N|MN|MODEL(?:\s+NUMBER)?|PART(?:\s+NUMBER)?)\s*[:#]",
    re.IGNORECASE,
)

# Part Number Processing (from MRO spec)
VALID_PN_RE = re.compile(r'^[A-Z0-9]+(?:[\-/][A-Z0-9]+)*$')
STRUCTURED_PN_RE = re.compile(r'\b([A-Z0-9]+(?:[\-/][A-Z0-9]+)+)\b')
INVALID_PN_PREFIXES = ('N0', 'N7', 'N71', 'N72', 'N73', 'CNVL', 'T7', 'T71', 'T72', 'T76', 'T77', 'T78', 'T79')


# ═══════════════════════════════════════════════════════════════
#  DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════

@dataclass
class ParseResult:
    """Result from processing a single row."""
    mfg: Optional[str] = None
    pn: Optional[str] = None
    sim: Optional[str] = None
    mfg_source: str = 'none'
    pn_source: str = 'none'
    flags: list = field(default_factory=list)


@dataclass
class JobResult:
    """Result from processing a full workbook."""
    df: pd.DataFrame = None
    total_rows: int = 0
    mfg_filled: int = 0
    pn_filled: int = 0
    sim_filled: int = 0
    issues: list = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════
#  EXTRACTION HELPERS
# ═══════════════════════════════════════════════════════════════

def _clean_pn_token(token: str) -> Optional[str]:
    if not token:
        return None
    s = str(token).strip().upper()
    s = re.split(r"[\s,;]\s*", s)[0]
    m = re.match(r"^[A-Z0-9][A-Z0-9\-_/\.]*", s)
    return m.group(0) if m else None


def extract_pn_from_text(text: str) -> tuple[Optional[str], str]:
    """Extract a Part Number from free text. Returns (pn, source_type)."""
    if not text:
        return None, 'none'
    t = str(text).upper()

    # Priority 1: labeled fields
    for pat in PN_LABEL_PATTERNS:
        m = re.search(pat, t)
        if m:
            return _clean_pn_token(m.group(1)), 'label'

    # Priority 2: heuristic — tokens with letters+digits
    tokens = re.split(r"[\s,;]\s*", t)
    cands = []
    for tok in tokens:
        tok2 = _clean_pn_token(tok)
        if not tok2:
            continue
        if (re.search(r"[A-Z]", tok2) and re.search(r"\d", tok2)
                and len(tok2) <= 25
                and not re.match(r"\d+/?\d*IN$", tok2)):
            cands.append(tok2)
    return (cands[-1], 'fallback') if cands else (None, 'none')


def extract_mfg_from_text(text: str, pn_hint: Optional[str], known_mfgs: set) -> tuple[Optional[str], str]:
    """Extract a Manufacturer from free text. Returns (mfg, source_type)."""
    if not text:
        return None, 'none'
    T = str(text).upper()

    # 1) MANUFACTURER: label
    m = MFG_LABEL_RE.search(T)
    if m:
        return re.sub(r"\s+", " ", m.group(1).strip()), 'label'

    # 2) pre-label pattern: ", <MFG>, PN:"
    m = PRELABEL_MFG_RE.search(T)
    if m:
        return re.sub(r"\s+", " ", m.group(1).strip()), 'context'

    # 3) known manufacturer names
    for name in sorted(known_mfgs, key=len, reverse=True):
        if name and name in T:
            return name, 'known'

    # 4) context with PN hint
    if pn_hint:
        m = re.search(r",\s*([A-Z][A-Z\-&\./\s]{2,40}?)\s*,\s*" + re.escape(pn_hint), T)
        if m:
            return re.sub(r"\s+", " ", m.group(1).strip()), 'context'

    return None, 'none'


def sanitize_mfg(x: str) -> Optional[str]:
    """Clean and validate an MFG string."""
    if not x:
        return None
    x = x.strip().upper()
    x = re.sub(r"\s+", " ", x)
    if any(k in x for k in DESCRIPTOR_KEYWORDS):
        return None
    if x in DISTRIBUTORS or x in DESCRIPTORS:
        return None
    if re.search(r"\d", x):
        return None
    x = NORMALIZE_MFG.get(x, x)
    x = x.replace('SQUARE-D', 'SQUARE D').replace('CROUSE-HINDS', 'CROUSE HINDS')
    x = x.replace('STATIC O RING', 'STATIC O-RING')
    return x.replace('  ', ' ')


def is_valid_pn(x: str) -> bool:
    """Check if string is a well-formed Part Number."""
    if not isinstance(x, str):
        return False
    x = x.strip().upper()
    if any(x.startswith(p) for p in INVALID_PN_PREFIXES):
        return False
    return bool(VALID_PN_RE.match(x))


def pn_needs_review(x: str, max_length: int = 30) -> bool:
    """
    Flag part numbers that exceed max length for human review.
    Long PNs (>30 chars) are often concatenated config codes that need QA.
    """
    if not isinstance(x, str):
        return False
    return len(x.strip()) > max_length


def build_sim(mfg: Optional[str], pn: Optional[str], pattern: str = 'space') -> str:
    """
    Build a SIM value from MFG and PN.
    Patterns: 'space' = "MFG PN", 'dash' = "MFG-PN", 'compact' = "MFGPN"
    """
    m = (mfg or '').strip()
    p = (pn or '').strip()
    if pattern == 'dash':
        return f"{m}-{p}".strip('-')
    elif pattern == 'compact':
        return f"{m}{p}"
    else:
        return f"{m} {p}".strip()


# ═══════════════════════════════════════════════════════════════
#  PIPELINE: MFG + PN EXTRACTION (Electrical spec)
# ═══════════════════════════════════════════════════════════════

def pipeline_mfg_pn(df: pd.DataFrame, source_cols: list[str],
                     mfg_col: str = 'MFG', pn_col: str = 'PN',
                     add_sim: bool = True) -> JobResult:
    """
    Full MFG/PN extraction pipeline.
    source_cols: list of column names to search for MFG and PN text.
    """
    result = JobResult(total_rows=len(df))
    df = df.copy()

    # Mine known manufacturers across all source columns
    known_mfgs = set()
    for col in source_cols:
        if col in df.columns:
            for text in df[col].dropna().astype(str).str.upper().values:
                m = MFG_LABEL_RE.search(text)
                if m:
                    known_mfgs.add(re.sub(r"\s+", " ", m.group(1).strip()))

    mfg_filled = 0
    pn_filled = 0

    for idx, row in df.iterrows():
        texts = [str(row.get(c, '')) for c in source_cols if c in df.columns]

        # Extract best PN
        best_pn, best_pn_src = None, 'none'
        for t in texts:
            pn, src = extract_pn_from_text(t)
            if src == 'label' or (src == 'fallback' and best_pn is None):
                if pn:
                    best_pn, best_pn_src = pn, src

        # Extract best MFG using PN hint
        best_mfg, best_mfg_src = None, 'none'
        for t in texts:
            mfg, src = extract_mfg_from_text(t, best_pn, known_mfgs)
            if src == 'label' or (src in ('context', 'known') and best_mfg is None):
                if mfg:
                    best_mfg, best_mfg_src = mfg, src

        mfg_final = sanitize_mfg(best_mfg)
        pn_final = best_pn

        # Write MFG if blank
        cur_mfg = str(row.get(mfg_col, '')).strip()
        if cur_mfg in ('', 'nan', 'None', 'NaN'):
            if mfg_final:
                df.at[idx, mfg_col] = mfg_final
                mfg_filled += 1

        # Write PN if blank
        cur_pn = str(row.get(pn_col, '')).strip()
        if cur_pn in ('', 'nan', 'None', 'NaN'):
            if pn_final:
                df.at[idx, pn_col] = pn_final
                pn_filled += 1

    # Tidy formatting
    if mfg_col in df.columns:
        df[mfg_col] = df[mfg_col].apply(
            lambda s: re.sub(r"\s+", " ", NORMALIZE_MFG.get(str(s).strip().upper(), str(s).strip().upper()))
            if pd.notna(s) else s
        )
    if pn_col in df.columns:
        df[pn_col] = df[pn_col].apply(
            lambda s: re.sub(r"\s+", "", str(s).strip().upper()) if pd.notna(s) else s
        )

    # SIM
    sim_filled = 0
    if add_sim:
        df['SIM'] = (df[mfg_col].fillna('').astype(str) + ' ' + df[pn_col].fillna('').astype(str)).str.strip()
        sim_filled = (df['SIM'] != '').sum()

    result.df = df
    result.mfg_filled = mfg_filled
    result.pn_filled = pn_filled
    result.sim_filled = sim_filled
    return result


# ═══════════════════════════════════════════════════════════════
#  PIPELINE: PART NUMBER REPROCESSING (MRO spec)
# ═══════════════════════════════════════════════════════════════

def pipeline_part_number(df: pd.DataFrame, pn_col: str = 'Part Number 1',
                          mfg_col: str = 'Manufacturer 1',
                          text_cols: Optional[list[str]] = None) -> JobResult:
    """Strict part number extraction and cleaning pipeline."""
    result = JobResult(total_rows=len(df))
    df = df.copy()

    if text_cols is None:
        text_cols = [c for c in df.columns if 'DESCRIPTION' in c.upper()] + \
                    [c for c in ['Notes', 'INFORECTXT1', 'INFORECTXT2'] if c in df.columns]

    updated = 0
    for i, row in df.iterrows():
        cur = row.get(pn_col)
        if not is_valid_pn(str(cur) if pd.notna(cur) else ''):
            blob = ' '.join(str(row.get(c)) for c in text_cols if pd.notna(row.get(c)))
            cands = STRUCTURED_PN_RE.findall(blob.upper())
            cands = [t for t in cands if not any(t.startswith(p) for p in INVALID_PN_PREFIXES)]
            cands = [t for t in cands if re.search(r'[A-Z]', t) and re.search(r'[0-9]', t)]
            if cands:
                best = sorted(cands, key=len, reverse=True)[0]
                if is_valid_pn(best):
                    df.at[i, pn_col] = best
                    updated += 1

    result.df = df
    result.pn_filled = updated
    return result


# ═══════════════════════════════════════════════════════════════
#  PIPELINE: SIM BUILDER (SIM BOM spec)
# ═══════════════════════════════════════════════════════════════

def pipeline_sim_builder(df: pd.DataFrame, mfg_col: str = 'MFG',
                          item_col: str = 'ITEM #', sim_col: str = 'SIM',
                          pattern: str = 'C') -> JobResult:
    """Build SIM values for rows where SIM is missing."""
    result = JobResult(total_rows=len(df))
    df = df.copy()

    # Normalize column names
    df.columns = [str(c).strip() for c in df.columns]

    # Find actual column names (case-insensitive matching)
    col_map = {c.upper(): c for c in df.columns}
    actual_mfg = col_map.get(mfg_col.upper(), mfg_col)
    actual_item = col_map.get(item_col.upper(), item_col)
    actual_sim = col_map.get(sim_col.upper(), sim_col)

    if actual_sim not in df.columns:
        df[actual_sim] = ''

    sim_series = df[actual_sim]
    missing = sim_series.isna() | (sim_series == 0) | (sim_series.astype(str).str.strip().isin(['', '0', '0.0', 'nan', 'None']))

    filled = 0
    for idx in df.index[missing]:
        mfg_val = str(df.at[idx, actual_mfg]).strip().upper() if pd.notna(df.at[idx, actual_mfg]) else ''
        item_val = str(df.at[idx, actual_item]).strip() if pd.notna(df.at[idx, actual_item]) else ''
        mfg_val = mfg_val.replace('  ', ' ')

        if pattern == 'A':
            sim_val = f"{mfg_val}-{item_val}"
        elif pattern == 'B':
            sim_val = f"{mfg_val}{item_val.replace(' ', '')}"
        else:  # C
            item_clean = re.sub(r'[^0-9A-Za-z]', '', item_val)
            sim_val = f"{mfg_val}-{item_clean}"

        if sim_val.strip('-'):
            df.at[idx, actual_sim] = sim_val
            filled += 1

    result.df = df
    result.sim_filled = filled
    return result


# ═══════════════════════════════════════════════════════════════
#  QA ENGINE
# ═══════════════════════════════════════════════════════════════

QA_RULES = [
    ('MFG_missing',       lambda r, mc: str(r.get(mc, '')).strip() in ('', 'nan', 'None'), 'MFG is empty'),
    ('PN_missing',        lambda r, mc: str(r.get('PN', r.get('Part Number 1', ''))).strip() in ('', 'nan', 'None'), 'PN is empty'),
    ('MFG_is_distributor', lambda r, mc: str(r.get(mc, '')).upper().strip() in DISTRIBUTORS, 'MFG is a distributor'),
    ('MFG_has_digits',    lambda r, mc: re.search(r"\d", str(r.get(mc, ''))) is not None, 'MFG contains digits'),
    ('PN_too_long',       lambda r, mc: pn_needs_review(str(r.get('PN', r.get('Part Number 1', '')))), 'PN exceeds 30 chars - review for concatenated codes'),
    ('MFG_equals_PN',     lambda r, mc: str(r.get(mc, '')).strip() != '' and str(r.get(mc, '')).strip() == str(r.get('PN', '')).strip(), 'MFG identical to PN'),
]

def run_qa(df: pd.DataFrame, mfg_col: str = 'MFG') -> list[dict]:
    """Run QA checks and return a list of flagged issues."""
    issues = []
    for i, row in df.iterrows():
        for key, fn, note in QA_RULES:
            try:
                if fn(row, mfg_col):
                    issues.append({
                        'row': int(i) + 2,  # Excel row (1-indexed + header)
                        'flag': key,
                        'note': note,
                        'MFG': row.get(mfg_col, ''),
                    })
            except Exception:
                pass
    return issues
