"""
schema_classifier.py — Column-structure-aware extraction routing for Wesco MRO Parser.

Synthesis layer that sits above column_mapper and file_profiler:
  - column_mapper  → which semantic role each column serves (header-level)
  - file_profiler  → what format the content is in (content-level)
  - schema_classifier → what SCHEMA PATTERN the file uses (structural-level)

Detects the overall column structure template and produces optimized strategy
weights by multiplicatively merging schema priors with content-archetype weights.
Both layers must agree to produce a strongly boosted weight; disagreement dampens.

No API calls — fully offline, deterministic.
"""

import re
from dataclasses import dataclass, field
from typing import Optional


# ═══════════════════════════════════════════════════════════════
#  SCHEMA TEMPLATES
# ═══════════════════════════════════════════════════════════════

SCHEMA_TEMPLATES = {
    "SAP_SHORT_TEXT": (
        "Short Text column (compressed, comma-delimited) with Supplier Name fallback. "
        "Classic SAP compressed format — prefix codes and known-MFG matching dominate."
    ),
    "SAP_DUAL_SOURCE": (
        "Both a rich description source (Material Description or PO Text) AND a secondary "
        "source (Short Text or PO Text). Richest extraction scenario — label and context "
        "patterns common in PO Text, prefix codes common in Short Text."
    ),
    "SAP_STANDARD": (
        "Material Description with pre-mapped MFG/PN output columns. "
        "Standard SAP format — balanced multi-strategy extraction."
    ),
    "DISTRIBUTOR_ORDER": (
        "Supplier/vendor column with catalog-style descriptions, no inline labels. "
        "Distributor order format — supplier fallback and catalog strategies boosted."
    ),
    "LABELED_SPEC": (
        "Descriptions contain explicit PN: / MANUFACTURER: labels. "
        "Labeled spec format — label extraction heavily prioritized."
    ),
    "GENERIC": (
        "No specific column structure pattern detected. "
        "Balanced extraction across all strategies."
    ),
}


# ═══════════════════════════════════════════════════════════════
#  SCHEMA-SPECIFIC STRATEGY MULTIPLIERS
#
# These are MULTIPLIERS applied on top of content-archetype weights,
# not absolute replacements. A value of 1.0 means no adjustment.
# Values > 1.0 boost the strategy; < 1.0 dampen it.
#
# Final weight = content_archetype_weight × schema_multiplier
# If COMPRESSED_SHORT gives prefix_decode: 1.3 and SAP_SHORT_TEXT
# gives prefix_decode: 1.5, merged = 1.3 × 1.5 = 1.95.
# ═══════════════════════════════════════════════════════════════

SCHEMA_MULTIPLIERS = {
    "SAP_SHORT_TEXT": {
        # Compact comma-delimited codes — prefix and supplier are highly reliable.
        # Heuristic is noisy in short compressed text.
        'label': 0.9,
        'known_mfg': 1.4,
        'context': 0.8,
        'prefix_decode': 1.5,
        'supplier_fallback': 1.6,
        'heuristic': 0.3,
        'dash_catalog': 1.0,
        'trailing_catalog': 1.2,
        'trailing_numeric': 1.0,
        'pn_structured': 1.0,
        'first_token_catalog': 1.2,
        'embedded_code': 1.4,   # v3.6 — boosted: compressed SAP text has embedded PNs (drives, modules)
    },
    "SAP_DUAL_SOURCE": {
        # Rich sources (Material Desc + PO Text or Short Text).
        # Context pattern (, PANDUIT, PN:) is extremely common in PO Text fields.
        # Label also strong. Prefix useful for Short Text component.
        'label': 1.2,
        'known_mfg': 1.1,
        'context': 1.2,
        'prefix_decode': 1.1,
        'supplier_fallback': 0.8,
        'heuristic': 0.7,
        'dash_catalog': 1.0,
        'trailing_catalog': 1.0,
        'trailing_numeric': 0.9,
        'pn_structured': 1.0,
        'first_token_catalog': 1.0,
        'embedded_code': 1.0,   # v3.6
    },
    "SAP_STANDARD": {
        # Material Description with output columns — balanced.
        # Slight label boost, slightly dampen heuristic and supplier fallback.
        'label': 1.1,
        'known_mfg': 1.0,
        'context': 1.0,
        'prefix_decode': 0.9,
        'supplier_fallback': 0.6,
        'heuristic': 0.8,
        'dash_catalog': 1.0,
        'trailing_catalog': 1.0,
        'trailing_numeric': 0.9,
        'pn_structured': 1.0,
        'first_token_catalog': 1.0,
        'embedded_code': 1.0,   # v3.6
    },
    "DISTRIBUTOR_ORDER": {
        # Vendor column present and no inline labels — supplier_fallback is gold here.
        # Catalog strategies also boosted. Label and context are unreliable.
        'label': 0.8,
        'known_mfg': 0.9,
        'context': 0.7,
        'prefix_decode': 1.0,
        'supplier_fallback': 1.8,
        'heuristic': 0.5,
        'dash_catalog': 1.4,
        'trailing_catalog': 1.1,
        'trailing_numeric': 1.0,
        'pn_structured': 1.0,
        'first_token_catalog': 1.2,
        'embedded_code': 1.1,   # v3.6
    },
    "LABELED_SPEC": {
        # Explicit PN:/MFG: labels in description — label extraction dominates.
        # Dampen prefix and supplier; they're unreliable when labels exist.
        'label': 1.5,
        'known_mfg': 1.0,
        'context': 1.0,
        'prefix_decode': 0.5,
        'supplier_fallback': 0.3,
        'heuristic': 0.5,
        'dash_catalog': 0.8,
        'trailing_catalog': 0.9,
        'trailing_numeric': 0.8,
        'pn_structured': 1.0,
        'first_token_catalog': 0.9,
        'embedded_code': 0.8,   # v3.6 — labels dominate; embedded codes are secondary
    },
    "GENERIC": {
        # No structural signal — all multipliers neutral (no adjustment).
        'label': 1.0,
        'known_mfg': 1.0,
        'context': 1.0,
        'prefix_decode': 1.0,
        'supplier_fallback': 1.0,
        'heuristic': 1.0,
        'dash_catalog': 1.0,
        'trailing_catalog': 1.0,
        'trailing_numeric': 1.0,
        'pn_structured': 1.0,
        'first_token_catalog': 1.0,
        'embedded_code': 1.0,   # v3.6
    },
}


# Confidence threshold base per schema.
# Used to blend with file_profiler's content-archetype threshold.
SCHEMA_CONFIDENCE_THRESHOLDS = {
    "SAP_SHORT_TEXT": 0.42,    # Compressed format is noisier — slightly stricter
    "SAP_DUAL_SOURCE": 0.36,   # Two rich sources = more signal = can afford lower threshold
    "SAP_STANDARD": 0.38,      # Moderate — balanced
    "DISTRIBUTOR_ORDER": 0.45, # Catalog descriptions have high noise
    "LABELED_SPEC": 0.32,      # Explicit labels are highly reliable — permissive threshold
    "GENERIC": 0.40,           # Default
}

# Absolute floor — threshold never drops below this regardless of blend.
_THRESHOLD_FLOOR = 0.35


# ═══════════════════════════════════════════════════════════════
#  COLUMN KEYWORD SETS (for structural signal extraction)
# ═══════════════════════════════════════════════════════════════

_SHORT_TEXT_KEYWORDS = frozenset({
    'short text', 'shorttext', 'short_text', 'short desc', 'short description',
    'short text ', 'item text', 'line text', 'mat text',
})

_MATERIAL_DESC_KEYWORDS = frozenset({
    'material description', 'mat description', 'material desc', 'material text',
    'mtrl desc', 'material po text', 'matnr_desc',
})

_PO_TEXT_KEYWORDS = frozenset({
    'po text', 'po_text', 'purchase order text', 'po description',
    'po line text', 'po item text', 'material po text',
})


# ═══════════════════════════════════════════════════════════════
#  DATA STRUCTURE
# ═══════════════════════════════════════════════════════════════

@dataclass
class SchemaProfile:
    """Result of column-structure classification."""
    template: str                    # SAP_STANDARD, SAP_SHORT_TEXT, etc.
    detection_confidence: float      # Structural certainty (0.0–1.0)
    explanation: str                 # Human-readable explanation

    # Detected column role signals
    source_columns: list = field(default_factory=list)
    primary_source: Optional[str] = None
    has_supplier: bool = False
    has_short_text: bool = False
    has_material_desc: bool = False
    has_po_text: bool = False
    has_mfg_output: bool = False
    has_pn_output: bool = False

    # Content archetype (from file_profiler)
    content_archetype: str = "MIXED"

    # Final merged weights and threshold
    strategy_weights: dict = field(default_factory=dict)
    confidence_threshold: float = 0.40

    def summary(self) -> str:
        lines = [
            f"Schema Template:   {self.template} (confidence: {self.detection_confidence:.0%})",
            f"Explanation:       {self.explanation}",
            f"Content archetype: {self.content_archetype}",
            f"Primary source:    {self.primary_source or '[auto]'}",
            f"Signals:           supplier={self.has_supplier}, short_text={self.has_short_text}, "
            f"material_desc={self.has_material_desc}, po_text={self.has_po_text}, "
            f"mfg_col={self.has_mfg_output}, pn_col={self.has_pn_output}",
            f"Confidence thresh: {self.confidence_threshold}",
        ]
        return '\n'.join(lines)


# ═══════════════════════════════════════════════════════════════
#  INTERNAL HELPERS
# ═══════════════════════════════════════════════════════════════

def _col_matches(col: str, keywords: frozenset) -> bool:
    return col.lower().strip() in keywords


def _any_col_matches(cols: list, keywords: frozenset) -> bool:
    return any(_col_matches(c, keywords) for c in cols)


def _extract_signals(column_mapping: dict) -> dict:
    """Extract structural signals from a column_mapping dict."""
    desc_cols = column_mapping.get('source_description', [])
    po_cols = column_mapping.get('source_po_text', [])
    supplier_cols = column_mapping.get('source_supplier', [])

    return {
        'has_short_text': _any_col_matches(desc_cols, _SHORT_TEXT_KEYWORDS),
        'has_material_desc': _any_col_matches(desc_cols, _MATERIAL_DESC_KEYWORDS),
        'has_po_text': bool(po_cols) or _any_col_matches(desc_cols, _PO_TEXT_KEYWORDS),
        'has_supplier': bool(supplier_cols) or bool(column_mapping.get('supplier')),
        'has_mfg_output': bool(column_mapping.get('mfg_output')),
        'has_pn_output': bool(column_mapping.get('pn_output')),
        'desc_col_count': len(desc_cols),
        'all_source_cols': (
            desc_cols
            + po_cols
            + column_mapping.get('source_notes', [])
        ),
    }


def _detect_template(signals: dict, file_profile) -> tuple[str, float, str]:
    """
    Determine schema template from structural signals and content profile.

    Priority order (first match wins):
    1. SAP_SHORT_TEXT  — Short Text col + Supplier col, no Material Desc
    2. SAP_DUAL_SOURCE — Short Text + Material Desc, OR Material Desc + PO Text
    3. SAP_STANDARD    — Material Desc + mapped MFG/PN output cols
    4. DISTRIBUTOR_ORDER — Supplier col, no labels, no Material Desc
    5. LABELED_SPEC    — Content archetype is LABELED_RICH (content signal overrides structure)
    6. GENERIC         — Default

    Returns (template, detection_confidence, explanation).
    """
    has_short = signals['has_short_text']
    has_mat = signals['has_material_desc']
    has_po = signals['has_po_text']
    has_sup = signals['has_supplier']
    has_mfg_col = signals['has_mfg_output']
    has_pn_col = signals['has_pn_output']

    archetype = file_profile.archetype if file_profile else "MIXED"

    # ── 1. SAP Short Text (compressed format) ────────────────────────────────
    if has_short and has_sup and not has_mat:
        return (
            "SAP_SHORT_TEXT",
            0.92,
            "Short Text + Supplier Name columns detected (no Material Description). "
            "SAP compressed format: boost prefix codes and known-manufacturer matching.",
        )

    # ── 2. SAP Dual Source (richest extraction scenario) ─────────────────────
    #    Covers: (a) Short Text + Material Desc, (b) Material Desc + PO Text
    if (has_short and has_mat) or (has_mat and has_po):
        secondary = "Short Text" if has_short else "PO Text"
        return (
            "SAP_DUAL_SOURCE",
            0.88,
            f"Material Description + {secondary} both present. "
            "Dual-source extraction: label/context patterns from PO Text, "
            "prefix codes from Short Text.",
        )

    # ── 3. SAP Standard (material desc + output columns exist) ───────────────
    if has_mat and has_mfg_col and has_pn_col:
        return (
            "SAP_STANDARD",
            0.85,
            "Material Description with MFG and PN output columns. "
            "Standard SAP format: balanced multi-strategy extraction.",
        )

    # ── 4. Distributor Order (supplier + no labels + no Material Desc) ───────
    #    Require: supplier present, no Material Description, and content does not
    #    have inline labels (to avoid misclassifying SAP files with a supplier col).
    pct_labeled_pn = getattr(file_profile, 'pct_labeled_pn', 0.10) if file_profile else 0.10
    pct_labeled_mfg = getattr(file_profile, 'pct_labeled_mfg', 0.10) if file_profile else 0.10

    if (
        has_sup
        and not has_mat
        and pct_labeled_pn < 0.05
        and pct_labeled_mfg < 0.05
    ):
        return (
            "DISTRIBUTOR_ORDER",
            0.75,
            "Supplier/vendor column present with no inline PN/MFG labels and no "
            "Material Description. Distributor order format: supplier fallback boosted.",
        )

    # ── 5. Labeled Spec (content archetype takes structural precedence) ───────
    if archetype == "LABELED_RICH":
        return (
            "LABELED_SPEC",
            0.80,
            "Descriptions contain explicit PN: / MANUFACTURER: labels (LABELED_RICH archetype). "
            "Label extraction heavily prioritized.",
        )

    # ── 6. Generic fallback ──────────────────────────────────────────────────
    return (
        "GENERIC",
        0.50,
        "No specific column structure pattern detected. "
        "Balanced extraction across all strategies.",
    )


def _merge_weights(content_weights: dict, schema_multipliers: dict) -> dict:
    """
    Multiplicatively merge content-archetype weights with schema multipliers.

    Formula: merged[strategy] = content_weight × schema_multiplier

    Both layers must agree to produce a strong boost. If content archetype
    gave prefix_decode: 1.3 and schema multiplier is 1.5, merged = 1.95.
    If content archetype gave 0.5, merged = 0.75 — still boosted but
    reflecting that content doesn't fully support the structural prior.
    """
    all_strategies = set(list(content_weights.keys()) + list(schema_multipliers.keys()))
    merged = {}
    for strategy in all_strategies:
        content_w = content_weights.get(strategy, 1.0)
        schema_mult = schema_multipliers.get(strategy, 1.0)
        merged[strategy] = round(content_w * schema_mult, 4)
    return merged


def _blend_threshold(schema_threshold: float, content_threshold: float) -> float:
    """
    Blend schema and content thresholds, with schema weighted 60%.
    Applies an absolute floor of 0.35.
    """
    blended = schema_threshold * 0.6 + content_threshold * 0.4
    return round(max(_THRESHOLD_FLOOR, blended), 3)


# ═══════════════════════════════════════════════════════════════
#  MAIN CLASSIFICATION FUNCTION
# ═══════════════════════════════════════════════════════════════

def classify_schema(
    column_mapping: dict,
    file_profile=None,  # FileProfile from file_profiler (optional)
) -> SchemaProfile:
    """
    Classify the file's column structure and produce optimized extraction routing.

    Args:
        column_mapping: Output from column_mapper.map_columns()
        file_profile:   Optional FileProfile from file_profiler.profile_file()

    Returns:
        SchemaProfile with:
          - template: Detected schema name
          - detection_confidence: Structural certainty (0–1)
          - strategy_weights: Multiplicatively merged weights (use these in pick_best)
          - confidence_threshold: Blended per-row confidence floor
          - explanation: Human-readable routing rationale
    """
    signals = _extract_signals(column_mapping)
    template, detection_confidence, explanation = _detect_template(signals, file_profile)

    # ── Merge strategy weights (multiplicative) ───────────────────────────────
    schema_multipliers = SCHEMA_MULTIPLIERS[template]

    if file_profile is not None and file_profile.strategy_weights:
        content_weights = file_profile.strategy_weights
    else:
        # No content profile — use neutral weights (1.0 for everything)
        content_weights = {k: 1.0 for k in schema_multipliers}

    merged_weights = _merge_weights(content_weights, schema_multipliers)

    # ── Blend confidence threshold ────────────────────────────────────────────
    schema_thresh = SCHEMA_CONFIDENCE_THRESHOLDS[template]
    content_thresh = file_profile.confidence_threshold if file_profile else 0.40
    final_threshold = _blend_threshold(schema_thresh, content_thresh)

    # ── Build source column list ──────────────────────────────────────────────
    all_source_cols = signals['all_source_cols']
    primary_source = all_source_cols[0] if all_source_cols else None

    return SchemaProfile(
        template=template,
        detection_confidence=detection_confidence,
        explanation=explanation,
        source_columns=all_source_cols,
        primary_source=primary_source,
        has_supplier=signals['has_supplier'],
        has_short_text=signals['has_short_text'],
        has_material_desc=signals['has_material_desc'],
        has_po_text=signals['has_po_text'],
        has_mfg_output=signals['has_mfg_output'],
        has_pn_output=signals['has_pn_output'],
        content_archetype=file_profile.archetype if file_profile else "MIXED",
        strategy_weights=merged_weights,
        confidence_threshold=final_threshold,
    )
