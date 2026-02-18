"""
file_profiler.py — Pre-parse file format analysis.

Samples rows from an uploaded file and classifies it into a format
archetype that controls extraction strategy selection.
100% offline — no API calls.
"""

import re
import hashlib
import pandas as pd
from dataclasses import dataclass, field
from typing import Optional


# ═══════════════════════════════════════════════════════════════
#  DETECTION PATTERNS
# ═══════════════════════════════════════════════════════════════

_LABELED_PN_RE = re.compile(
    r'\b(?:PN|P/N|MN|MODEL|PART\s+NUMBER|MODEL\s+NUMBER)\s*[:#]',
    re.IGNORECASE,
)
_LABELED_MFG_RE = re.compile(r'MANUFACTURER\s*:', re.IGNORECASE)
_PURE_CATALOG_RE = re.compile(r'^[A-Z0-9\-/\.]+$')

# Prefix-coded pattern: 2–4 alpha chars followed by alphanumeric string with ≥1 digit
# Examples: HUBCS120W, SQDHOM123, SIEMK245
_PREFIX_CODED_RE = re.compile(r'^[A-Z]{2,4}[A-Z0-9]*[0-9][A-Z0-9]*$')


# ═══════════════════════════════════════════════════════════════
#  ARCHETYPE STRATEGY WEIGHTS
# ═══════════════════════════════════════════════════════════════

STRATEGY_WEIGHTS = {
    "LABELED_RICH": {
        'label': 1.2, 'known_mfg': 1.0, 'context': 1.0,
        'prefix_decode': 0.5, 'supplier_fallback': 0.3, 'heuristic': 0.6,
        'dash_catalog': 1.0,
        'trailing_catalog': 1.0, 'trailing_numeric': 0.9, 'pn_structured': 1.0,
        'first_token_catalog': 1.0,  # v3.4
        'embedded_code': 0.8,        # v3.6
    },
    "COMPRESSED_SHORT": {
        'label': 1.0, 'known_mfg': 1.2, 'context': 0.8,
        'prefix_decode': 1.3, 'supplier_fallback': 1.2, 'heuristic': 0.4,
        'dash_catalog': 1.0,
        'trailing_catalog': 1.0, 'trailing_numeric': 0.9, 'pn_structured': 1.0,
        'first_token_catalog': 1.0,  # v3.4
        'embedded_code': 1.2,        # v3.6 — boosted: compressed SAP text often has embedded PNs
    },
    "CATALOG_ONLY": {
        'label': 0.8, 'known_mfg': 0.5, 'context': 0.3,
        'prefix_decode': 1.0, 'supplier_fallback': 1.5, 'heuristic': 0.3,
        'dash_catalog': 1.3,
        'trailing_catalog': 1.0, 'trailing_numeric': 0.9, 'pn_structured': 1.0,
        'first_token_catalog': 1.1,  # v3.4 — slightly boosted in catalog-heavy files
        'embedded_code': 0.9,        # v3.6
    },
    "MIXED": {
        'label': 1.0, 'known_mfg': 1.0, 'context': 1.0,
        'prefix_decode': 1.0, 'supplier_fallback': 1.0,
        # v3.2: raised from 0.5 → 0.75 — the 0.5 weight was too aggressive:
        # max heuristic score (0.65) * 0.5 = 0.325, always below threshold (0.40),
        # meaning the heuristic was effectively disabled in MIXED files.
        # 0.65 * 0.75 = 0.49 now passes. 593 low-confidence items unlocked.
        'heuristic': 0.75,
        'dash_catalog': 1.0,
        'trailing_catalog': 1.0, 'trailing_numeric': 0.9, 'pn_structured': 1.0,
        'first_token_catalog': 1.0,  # v3.4
        'embedded_code': 1.0,        # v3.6
    },
}


# ═══════════════════════════════════════════════════════════════
#  DATA STRUCTURE
# ═══════════════════════════════════════════════════════════════

@dataclass
class FileProfile:
    """Result of file format analysis."""
    archetype: str              # LABELED_RICH, COMPRESSED_SHORT, CATALOG_ONLY, MIXED
    total_rows: int
    sample_size: int

    # Signal percentages (0.0 to 1.0)
    pct_labeled_pn: float       # Rows with PN:, MN:, MODEL: labels
    pct_labeled_mfg: float      # Rows with MANUFACTURER: label
    pct_explicit_mfg: float     # Rows with known MFG names in text
    pct_comma_delimited: float  # Rows using comma separation
    pct_pure_catalog: float     # Rows that are just a catalog/part number
    pct_free_text: float        # Rows with unstructured prose
    pct_prefix_coded: float     # Rows with manufacturer prefix codes

    avg_token_count: float      # Average comma/space-separated tokens per row
    has_supplier_col: bool      # Whether a supplier/vendor column exists
    has_separate_mfg_col: bool  # Whether MFG output column already has data

    # Recommended strategy weights (set by _classify_archetype)
    strategy_weights: dict = field(default_factory=dict)
    confidence_threshold: float = 0.40

    def summary(self) -> str:
        """Human-readable format profile summary."""
        lines = [
            f"File Profile: {self.archetype}",
            f"  Rows: {self.total_rows} (sampled {self.sample_size})",
            f"  Labeled PN: {self.pct_labeled_pn:.1%}",
            f"  Labeled MFG: {self.pct_labeled_mfg:.1%}",
            f"  Explicit MFG names: {self.pct_explicit_mfg:.1%}",
            f"  Comma-delimited: {self.pct_comma_delimited:.1%}",
            f"  Pure catalog numbers: {self.pct_pure_catalog:.1%}",
            f"  Free text: {self.pct_free_text:.1%}",
            f"  Prefix-coded: {self.pct_prefix_coded:.1%}",
            f"  Avg tokens/row: {self.avg_token_count:.1f}",
            f"  Has supplier column: {self.has_supplier_col}",
            f"  Has MFG column pre-filled: {self.has_separate_mfg_col}",
            f"  Confidence threshold: {self.confidence_threshold}",
        ]
        return '\n'.join(lines)


# ═══════════════════════════════════════════════════════════════
#  INTERNAL HELPERS
# ═══════════════════════════════════════════════════════════════

def _is_prefix_coded(text: str) -> bool:
    """
    Return True if the first token looks like a manufacturer-prefix-coded value.
    Pattern: 2–4 uppercase alpha chars immediately followed by alphanumeric with digits.
    Examples that match: HUBCS120W, SQDHOM123, SIEMK245
    """
    if not text:
        return False
    first_token = text.strip().split()[0].split(',')[0].split(' - ')[0]
    return bool(_PREFIX_CODED_RE.match(first_token)) and len(first_token) > 5


def _classify_archetype(
    pct_labeled_pn: float,
    pct_labeled_mfg: float,
    pct_comma_delimited: float,
    pct_pure_catalog: float,
) -> tuple[str, float]:
    """
    Classify file archetype and return (archetype, confidence_threshold).
    """
    if pct_labeled_pn >= 0.40 or pct_labeled_mfg >= 0.20:
        return "LABELED_RICH", 0.35
    elif pct_pure_catalog >= 0.30:
        return "CATALOG_ONLY", 0.50
    elif pct_comma_delimited >= 0.40 and pct_labeled_pn < 0.15:
        return "COMPRESSED_SHORT", 0.45
    else:
        return "MIXED", 0.40


# ═══════════════════════════════════════════════════════════════
#  MAIN PROFILING FUNCTION
# ═══════════════════════════════════════════════════════════════

def profile_file(
    df: pd.DataFrame,
    source_cols: list,
    supplier_col: Optional[str] = None,
    mfg_col: Optional[str] = None,
    known_mfgs: Optional[set] = None,
    sample_size: int = 200,
) -> FileProfile:
    """
    Analyze a DataFrame's format and classify it into an archetype.

    Args:
        df: Input DataFrame
        source_cols: Columns to sample for text analysis
        supplier_col: Optional supplier column name
        mfg_col: Optional MFG output column name (used to detect pre-filled data)
        known_mfgs: Optional set of known manufacturer names for explicit-MFG detection
        sample_size: Number of rows to sample (default 200)

    Returns:
        FileProfile with archetype, signal percentages, and strategy weights.
    """
    total_rows = len(df)
    actual_sample = min(sample_size, total_rows)

    if actual_sample == 0:
        archetype, threshold = "MIXED", 0.40
        return FileProfile(
            archetype=archetype, total_rows=0, sample_size=0,
            pct_labeled_pn=0.0, pct_labeled_mfg=0.0, pct_explicit_mfg=0.0,
            pct_comma_delimited=0.0, pct_pure_catalog=0.0, pct_free_text=1.0,
            pct_prefix_coded=0.0, avg_token_count=0.0,
            has_supplier_col=False, has_separate_mfg_col=False,
            strategy_weights=STRATEGY_WEIGHTS[archetype],
            confidence_threshold=threshold,
        )

    sample = df.sample(actual_sample, random_state=42)

    # Filter to only existing source columns
    valid_cols = [c for c in source_cols if c in df.columns]

    counters = {k: 0 for k in [
        'labeled_pn', 'labeled_mfg', 'prefix_coded',
        'explicit_mfg', 'pure_catalog', 'comma_delimited', 'free_text',
    ]}
    total_tokens = 0

    # Sort known_mfgs by length descending to prefer longer matches
    sorted_mfgs = sorted(known_mfgs, key=len, reverse=True) if known_mfgs else []

    for _, row in sample.iterrows():
        texts = [str(row.get(c, '')) for c in valid_cols]
        combined = ' | '.join(t for t in texts if str(t).strip())
        combined_upper = combined.strip().upper()

        # Count tokens (split on commas and spaces)
        tokens = [t for t in re.split(r'[,\s]+', combined_upper) if t]
        total_tokens += len(tokens)

        # Classify in priority order (first match wins)
        if _LABELED_PN_RE.search(combined_upper):
            counters['labeled_pn'] += 1
        elif _LABELED_MFG_RE.search(combined_upper):
            counters['labeled_mfg'] += 1
        elif _is_prefix_coded(combined_upper):
            counters['prefix_coded'] += 1
        elif sorted_mfgs and any(m and m in combined_upper for m in sorted_mfgs):
            counters['explicit_mfg'] += 1
        elif (
            _PURE_CATALOG_RE.match(combined_upper.strip())
            and len(combined_upper.strip()) < 20
        ):
            counters['pure_catalog'] += 1
        elif ',' in combined_upper:
            counters['comma_delimited'] += 1
        else:
            counters['free_text'] += 1

    n = actual_sample

    pct_labeled_pn = counters['labeled_pn'] / n
    pct_labeled_mfg = counters['labeled_mfg'] / n
    pct_explicit_mfg = counters['explicit_mfg'] / n
    pct_comma_delimited = counters['comma_delimited'] / n
    pct_pure_catalog = counters['pure_catalog'] / n
    pct_free_text = counters['free_text'] / n
    pct_prefix_coded = counters['prefix_coded'] / n
    avg_token_count = total_tokens / n if n > 0 else 0.0

    has_supplier_col = supplier_col is not None and supplier_col in df.columns
    has_separate_mfg_col = (
        mfg_col is not None
        and mfg_col in df.columns
        and df[mfg_col].notna().any()
    )

    archetype, confidence_threshold = _classify_archetype(
        pct_labeled_pn, pct_labeled_mfg, pct_comma_delimited, pct_pure_catalog
    )

    return FileProfile(
        archetype=archetype,
        total_rows=total_rows,
        sample_size=n,
        pct_labeled_pn=pct_labeled_pn,
        pct_labeled_mfg=pct_labeled_mfg,
        pct_explicit_mfg=pct_explicit_mfg,
        pct_comma_delimited=pct_comma_delimited,
        pct_pure_catalog=pct_pure_catalog,
        pct_free_text=pct_free_text,
        pct_prefix_coded=pct_prefix_coded,
        avg_token_count=avg_token_count,
        has_supplier_col=has_supplier_col,
        has_separate_mfg_col=has_separate_mfg_col,
        strategy_weights=STRATEGY_WEIGHTS[archetype],
        confidence_threshold=confidence_threshold,
    )


# ═══════════════════════════════════════════════════════════════
#  CACHED VARIANT
# ═══════════════════════════════════════════════════════════════

def _file_hash(df: pd.DataFrame) -> str:
    """Quick hash of first 100 rows for cache keying."""
    sample = df.head(100).to_string()
    return hashlib.md5(sample.encode()).hexdigest()[:12]


_profile_cache: dict = {}


def profile_file_cached(
    df: pd.DataFrame,
    source_cols: list,
    **kwargs,
) -> FileProfile:
    """
    Profile a file, returning cached result if same file was profiled before.

    Uses a hash of the first 100 rows as the cache key.
    """
    key = _file_hash(df)
    if key in _profile_cache:
        return _profile_cache[key]
    profile = profile_file(df, source_cols, **kwargs)
    _profile_cache[key] = profile
    return profile
