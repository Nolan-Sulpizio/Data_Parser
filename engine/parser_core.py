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
import os

# Import training data loader
try:
    from .training import load_training_data
except ImportError:
    def load_training_data(path=None):
        return {'mfg_normalization': {}, 'known_manufacturers': []}

# Import FileProfile for type annotations
try:
    from .file_profiler import FileProfile, profile_file, STRATEGY_WEIGHTS
except ImportError:
    FileProfile = None
    profile_file = None
    STRATEGY_WEIGHTS = {}

# Import schema classifier (v3.5.0 — column-structure-aware routing)
try:
    from .schema_classifier import classify_schema as _classify_schema
except ImportError:
    _classify_schema = None

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

# Load training data and merge with defaults
_training_data_path = os.path.join(os.path.dirname(__file__), '..', 'training_data.json')
_training = load_training_data(_training_data_path)
NORMALIZE_MFG.update(_training.get('mfg_normalization', {}))
# v3.1: Additional normalization entries — added after training merge to always take effect (Fix 3)
NORMALIZE_MFG.update({
    'ALN BRDLY': 'ALLEN BRADLEY',
    'ALLEN-BRADLEY': 'ALLEN BRADLEY',
    'A-B': 'ALLEN BRADLEY',
    'PHOENIX CNTCT': 'PHOENIX CONTACT',
    'PHNX CNTCT': 'PHOENIX CONTACT',
    'FOLCIERI': 'BRUNO FOLCIERI',
    'BRU FOLC': 'BRUNO FOLCIERI',   # v3.2: abbreviated form found in Short Text (Fix 4)
    'SEW EURODR': 'SEW EURODRIVE',
    'SEW': 'SEW EURODRIVE',
    'SEW,EURODRIVE': 'SEW EURODRIVE',
    'ROSSI': 'ROSSI MOTORIDUTTORI',
    'MOLR': 'EATON',
    'BACO': 'BACO CONTROLS',
    # v3.2: Fix 3 — ENDRESS HAUSER partial-name normalization
    'HAUSER': 'ENDRESS HAUSER',
    'ENDRESS': 'ENDRESS HAUSER',
    # v3.2: Discovery-loop normalization shortcuts found in WESCO data
    'ALNBRDLY': 'ALLEN BRADLEY',
    'SIEMNS': 'SIEMENS',
    'MARTN': 'MARTIN',
    'WSTNGHS': 'WESTINGHOUSE',
    'ACME ELE': 'ACME ELECTRIC',
    'BRUNO FOLCUERI': 'BRUNO FOLCIERI',   # typo variant
    'PAAL BALER': 'PAAL',
    # v3.6: SAP-truncated brand names found in WESCO compressed Short Text
    'SEW EURO': 'SEW EURODRIVE',
})

KNOWN_MANUFACTURERS = set(_training.get('known_manufacturers', []))
# v3.1: Additional known manufacturers (Fix 3)
KNOWN_MANUFACTURERS.update({
    'ALLEN BRADLEY', 'SEW EURODRIVE', 'PHOENIX CONTACT',
    'BRUNO FOLCIERI', 'ROSSI MOTORIDUTTORI', 'BACO CONTROLS',
    'OLI', 'WEG', 'HKK', 'WAM', 'LAFERT', 'MORRIS', 'DODGE',
    'MARTIN', 'WOODS', 'AMEC', 'LOVEJOY', 'GATES',
    'BALEMASTER', 'PILZ', 'FESTO',
    # v3.2: Fix 3 — add ENDRESS HAUSER so it never gets blocked
    'ENDRESS HAUSER',
    # v3.2: Discovery-loop — legitimate rare manufacturers found in WESCO data
    'TSUBAKI', 'IDEC', 'LENZE', 'TRAVAINI', 'MARATHON', 'ERIEZ', 'BALDOR',
    'NORD', 'SMC', 'BONFIGLIOLI', 'REGAL REXNORD', 'HYDRAFORCE', 'DUPLOMATIC',
    'WENGLOR', 'VORTEX', 'OMAL', 'ACME ELECTRIC', 'WESTINGHOUSE', 'PAAL',
    # v3.6: SAP-truncated brand abbreviations found in WESCO Short Text
    'SEW EURODR', 'SEW EURO',
    'ULINE',                              # ULINE is both supplier and brand for packaging goods
})

DISTRIBUTORS = {
    'GRAYBAR', 'CED', 'MC- MC', 'MC-MC', 'MCNAUGHTON-MCKAY', 'EISI',
    # v3: additional distributors for Short Text format files
    'MCMASTER-CARR', 'MCMASTER-CARR SUPPLY CO.', 'MCMASTER',
    # NOTE: ULINE removed from distributors — ULINE IS the brand for its packaging products.
    # When Supplier = ULINE, supplier_fallback correctly returns MFG = ULINE.
    'APPLIED INDUSTRIAL TECHNOLOGIE', 'APPLIED INDUSTRIAL TECHNOLOGIES',
    'MAYER ELECTRIC', 'MAYER ELECTRIC SUPPLY',
    'BEARING & DRIVE SUPPLY', 'NATIONAL RECOVERY TECHNOLOGIES',
    'MG AUTOMATION', 'MG AUTOMATION & CONTROLS',
}

DESCRIPTORS = {
    'LVL', 'CTRL', 'FIBRE OPTIC', 'EF-11', 'EF 2', 'EF1 1/2', 'EF 1 1/2', 'EF1/2',
    # v3: short mechanical/electrical descriptor codes that must never be treated as MFG
    'TE', 'NM', 'BLK', 'DIA', 'GR', 'FR', 'DC', 'AC', 'SP', 'SS',
    # v3.2: Italian screw-standard codes (Fix 3)
    'TSEI', 'TCEI',
    'RBR', 'STL', 'BRS', 'ALU', 'CU', 'PVC', 'PE', 'PP', 'CS',
    'HEX', 'SQ', 'RND', 'FLT', 'THD', 'TAP',
    'MTR', 'DRV', 'BRG', 'SCR', 'VLV', 'FAN', 'PMP',
    'ELE', 'MEC', 'HYD', 'PNE',
}

DESCRIPTOR_KEYWORDS = [
    'SWITCH', 'TRANSMITTER', 'CONNECTOR', 'THERMOCOUPLE', 'CABLE', 'VALVE',
    'RELAY', 'SENSOR', 'HEAD', 'CONTACTOR', 'MODULE', 'FAN', 'BEACON',
    'BRUSH', 'PLUG', 'RECEPTACLE', 'REGULATOR',
    # v3.1: additional equipment/descriptor keywords (Fix 2)
    'DISCONNECT', 'BEARING', 'BUSHING', 'COUPLING', 'STARTER', 'ENCLOSURE',
]

# ── v3.1: Extended MFG blocklist — tokens that are never valid manufacturer names (Fix 2)
# Check against KNOWN_MANUFACTURERS before blocking (see sanitize_mfg).
MFG_BLOCKLIST = {
    # Equipment types
    'DISCONNECT', 'INSERT', 'STARTER', 'ENCLOSURE', 'SWITCH',
    'TRANSMITTER', 'CONNECTOR', 'THERMOCOUPLE', 'CABLE', 'VALVE',
    'RELAY', 'SENSOR', 'CONTACTOR', 'MODULE', 'BEACON', 'PLUG',
    'RECEPTACLE', 'REGULATOR', 'BEARING', 'BUSHING', 'COUPLING',
    # Material/property descriptors
    'RESIST', 'PLANE',
    # v3.2: Fix 3 — position descriptors, material codes, equipment types
    'UPPER', 'LOWER', 'CENTRAL', 'FIBERGLASS', 'DELABELER',
    'TSEI', 'TCEI',   # Italian screw standards
    'MC-VLV',         # Valve type abbreviation (not a manufacturer)
    # Abbreviations for non-MFG things
    'FLG', 'RLR', 'KIT', 'BAR', 'CVR', 'PWR', 'NPT', 'LLC',
    'MAC', 'LIP', 'ZNT', 'GRY', 'WHI', 'BLU', 'YEL', 'GRN',
    'BRN', 'ORG', 'RED', 'BLK',
    'H/W', 'HW', 'S/S', 'C/S',
    # Pipe/thread/material codes
    'FNPT', 'MNPT', 'BSP', 'SAE',
    # v3.2: Discovery-loop false-positive single-word descriptors
    'MOTOR', 'GEARBOX', 'COVER', 'ASSY', 'COMPLETE', 'SCREW', 'SOCKET',
    'BOTTOM', 'DRUM', 'LINER', 'IDLER', 'RETURN', 'TAIL', 'TAILSHAFT',
    'AUGER', 'GASKET', 'SELECTOR', 'SPARE', 'SPECIAL', 'MANUAL', 'CUSTOM',
    'ROTARY', 'LOCKING', 'RETAINING', 'KEYLESS', 'GEARED', 'COMMS',
    'INDUCTIVE', 'TUBULAR', 'GROUNDED', 'THREADED', 'DELAY', 'SPLIT',
    'STARTING', 'CLEAR', 'FEMLE', 'OVERCENTER', 'HIGH', 'LOW',
    'COUNTERSHAFT', 'ROTORE', 'ELECTRICAL', 'PANELMOUNT', 'PULLEY',
    # v3.2: Discovery-loop multi-word false-positive descriptors
    'EMERGENCY STOP', 'SQURL CAGE', 'SINGL PHASE', 'AC GEN PURP',
    'MOTION CONTROL', 'HIGH LEVEL', 'PILLOW BLOCK', 'SPEED CTRL',
    'OPTICAL KIT', 'FOR NRT',
    'LEFT SIDE', 'RIGHT SIDE', 'REAR LEFT', 'REAR RIGHT',
    'FRNT SHT', 'W/PACKING', 'HEAVY DUTY', 'EXTENDED REACH',
}

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

# ── v3: Spec-value rejection patterns for PN heuristic ──────────────────────
# Matches electrical/mechanical spec values that must NOT be extracted as PNs
SPEC_VALUE_RE = re.compile(
    r'^(?:DC|AC)?[\d\.]+(?:/\d+)?'
    r'(?:V|A|W|VA|KW|KVA|HP|RPM|PH|OHM|HZ|AMP|AMPS|VOLT|VOLTS|WATT|WATTS)$',
    re.IGNORECASE,
)
DIMENSION_RE = re.compile(
    r'^\d+[\.\-/\d]*(?:IN|MM|CM|FT|MTR)$',
    re.IGNORECASE,
)
# Bare spec tokens that have letters+digits patterns but are NOT part numbers
BARE_SPEC_TOKENS = {
    '3PH', '1PH', 'DC', 'AC', 'SS', 'CS', 'BLK', 'WHI', 'RED',
    'GRN', 'BLU', 'YEL', 'GRY', 'BRN', 'EA', 'AU',
}

# ── P2: Non-product row patterns — rows whose text exactly matches these get no MFG/PN ──
NON_PRODUCT_PATTERNS = frozenset({
    'FREIGHT', 'FREIGHT CHARGE', 'FREIGHT CHARGES', 'FREIGHT COST',
    'SHIPPING', 'SHIPPING CHARGE', 'SHIPPING CHARGES', 'SHIPPING COST',
    'HANDLING', 'HANDLING CHARGE', 'HANDLING FEE', 'HANDLING COST',
    'SERVICE FEE', 'SERVICE CHARGE', 'SERVICE COST',
    'ADMIN CHARGE', 'ADMINISTRATIVE CHARGE',
    'TAX', 'SALES TAX', 'USE TAX', 'EXCISE TAX',
    'MISC', 'MISCELLANEOUS', 'MISCELLANEOUS CHARGE',
    'LABOR', 'LABOR CHARGE', 'LABOUR', 'LABOUR CHARGE',
    'INSTALLATION', 'INSTALLATION CHARGE', 'SETUP', 'SETUP CHARGE',
    'DISCOUNT', 'REBATE', 'CREDIT', 'ADJUSTMENT',
    'SURCHARGE', 'FUEL SURCHARGE', 'ENERGY SURCHARGE',
})

# ── v3.1: Descriptor-pattern PN rejection (Fix 4) ────────────────────────────
# Tokens matching NUMBER-DESCRIPTOR patterns are NOT part numbers
# v3.4: Dash made optional so "2BOLT", "4BOLT" are also rejected (not just "2-BOLT")
PN_DESCRIPTOR_PATTERNS = re.compile(
    r'^\d+-?(?:WAY|BOLT|POINT|HOLE|PIN|POLE|GANG|SLOT|SPEED|STAGE|STEP|'
    r'HOUR|PACK|PIECE|SET|PAIR|DI|DI/O|AI|AO|SPC|POS|PORT|WIRE|COND|BLADE)$',
    re.IGNORECASE,
)

# ── v3: Manufacturer prefix lookup (concatenated codes like HUBCS120W) ───────
MFG_PREFIX_MAP = {
    'HUB': 'HUBBELL',
    'SQD': 'SQUARE D',
    'ABB': 'ABB',
    'SIE': 'SIEMENS',
    'CUT': 'CUTLER-HAMMER',
    'PAN': 'PANDUIT',
    'APP': 'APPLETON',
    'CRO': 'CROUSE HINDS',
    'LEV': 'LEVITON',
    'LIT': 'LITTON',
    'EAT': 'EATON',
    'GE': 'GE',
}

# ── P0: 4-char composite code map (MDM-style concatenated codes) ─────────────
# Format: [4-char MFG code][PN suffix], e.g. TBCO222TB → T&B PN=222TB
# Source: Rigelwood / part_number_id dataset
MFG_COMPOSITE_CODE_MAP = {
    'TBCO': 'THOMAS & BETTS',
    'BLIN': 'B-LINE',
    'EGSM': 'EGS',
    'AMCO': 'AMCO',
    'HUWI': 'HUBBELL',
    'GEDI': 'GE',
    'BURN': 'BURNDY',
    'COND': 'GENERIC CONDUIT',
    'ALBR': 'ALLEN BRADLEY',
    'WAGO': 'WAGO',
    'IDEA': 'IDEAL',
    'RAYC': 'RAYCHEM',
    'HOFF': 'HOFFMAN',
    '3MCO': '3M',
    'TPCW': 'TPC WIRE & CABLE',
    'CABR': 'CABLE',
    'CRHI': 'CROUSE HINDS',
    'CUHA': 'CUTLER-HAMMER',
    'ELFL': 'ELECTRI-FLEX',
    'ERMA': 'ERICSON',
    'HULI': 'HUBBELL',
    'KILL': 'KILLARK',
    'OLFL': 'LAPP',
    'PAND': 'PANDUIT',
    'SHAW': 'MERSEN',
    'WIRE': None,        # generic wire — no specific manufacturer
}

# Part Number Processing (from MRO spec)
VALID_PN_RE = re.compile(r'^[A-Z0-9]+(?:[\-/][A-Z0-9]+)*$')
# v3.4: Added _ to separator class to catch revision codes like 37090310152_REV2, LEGR_3106
STRUCTURED_PN_RE = re.compile(r'\b([A-Z0-9]+(?:[\-/_][A-Z0-9]+)+)\b')
# v3.4: Dimension annotation pattern — rejects tokens like "W 2.6875IN", "ID 180MM"
DIMENSION_ANNOTATION_RE = re.compile(r'^[A-Z]{1,2}\s+[\d]', re.IGNORECASE)
INVALID_PN_PREFIXES = ('N0', 'N7', 'N71', 'N72', 'N73', 'CNVL', 'T7', 'T71', 'T72', 'T76', 'T77', 'T78', 'T79')

# ═══════════════════════════════════════════════════════════════
#  CONFIDENCE SCORING
# ═══════════════════════════════════════════════════════════════

CONFIDENCE_SCORES = {
    # PN extraction sources
    'pn_label': 0.95,           # PN:, MN:, MODEL: explicit label
    'pn_structured': 0.70,      # Structured token with dashes/slashes (e.g., 6EP1434-2BA20)
    'pn_fallback': 0.35,        # Heuristic base (now scored dynamically via _score_heuristic_pn)
    'pn_fallback_min': 0.10,    # Worst-case heuristic
    'pn_fallback_max': 0.65,    # Best-case heuristic
    'pn_catalog': 0.60,         # Pure catalog number (entire text IS the PN)
    'pn_prefix_decode': 0.75,   # Decoded from manufacturer prefix
    'pn_composite_code': 0.82,  # P0: Decoded from 4-char MDM composite code
    'pn_dash_catalog': 0.80,    # Dash-separated catalog number (McMaster format)
    'pn_trailing_catalog': 0.68,  # v3.2: Trailing code in DESC,DESC,CATALOG format (Fix 1)
    'pn_trailing_numeric': 0.50,  # v3.2: Trailing pure-numeric code ≥7 digits (Fix 5)
    'pn_first_token_catalog': 0.68,  # v3.4: First token is catalog number (CATALOG, description)
    'pn_embedded_code': 0.72,        # v3.6: Long alphanumeric code embedded in comma-delimited list

    # MFG extraction sources
    'mfg_label': 0.95,          # MANUFACTURER: explicit label
    'mfg_context': 0.80,        # Pre-label context pattern (", GATES, PN:")
    'mfg_known': 0.85,          # Known manufacturer name found in text
    'mfg_prefix_decode': 0.80,  # Decoded from manufacturer prefix
    'mfg_composite_code': 0.85, # P0: Decoded from 4-char MDM composite code
    'mfg_supplier': 0.55,       # Supplier name fallback (non-distributor)
}

# Confidence modifiers
MUTUAL_CONSISTENCY_BOOST = 0.05
SHORT_VALUE_PENALTY = -0.15
SPEC_ADJACENT_PENALTY = -0.20
TRAINING_MATCH_BOOST = 0.10


# ═══════════════════════════════════════════════════════════════
#  DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════

@dataclass
class ExtractionCandidate:
    """A single extraction attempt from one strategy."""
    value: Optional[str]
    source: str           # strategy name (label, known_mfg, prefix_decode, etc.)
    confidence: float     # raw confidence before strategy weight


@dataclass
class ParseResult:
    """Result from processing a single row."""
    mfg: Optional[str] = None
    pn: Optional[str] = None
    sim: Optional[str] = None
    mfg_source: str = 'none'
    pn_source: str = 'none'
    mfg_confidence: float = 0.0
    pn_confidence: float = 0.0
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
    file_profile: object = None              # FileProfile instance
    schema_profile: object = None            # SchemaProfile instance (v3.5.0)
    low_confidence_items: list = field(default_factory=list)
    confidence_stats: dict = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════
#  MULTI-STRATEGY BEST-PICK
# ═══════════════════════════════════════════════════════════════

def pick_best(
    candidates: list,
    strategy_weights: dict,
) -> tuple:
    """
    Pick the highest-confidence candidate after applying strategy weights.

    Args:
        candidates: List of ExtractionCandidate objects
        strategy_weights: Dict mapping source name → weight multiplier

    Returns:
        (value, source, weighted_confidence) tuple. Returns (None, 'none', 0.0)
        if no valid candidates.
    """
    if not candidates:
        return None, 'none', 0.0

    scored = []
    for c in candidates:
        if c.value is None:
            continue
        weight = strategy_weights.get(c.source, 1.0)
        weighted = c.confidence * weight
        scored.append((c.value, c.source, weighted))

    if not scored:
        return None, 'none', 0.0

    # Sort by weighted confidence descending, pick best
    scored.sort(key=lambda x: x[2], reverse=True)
    return scored[0]


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


def _is_spec_value(tok: str) -> bool:
    """Return True if token is an electrical/mechanical spec value (should not be a PN)."""
    return (
        SPEC_VALUE_RE.match(tok) is not None
        or DIMENSION_RE.match(tok) is not None
        or tok in BARE_SPEC_TOKENS
        or re.match(r"\d+/?\d*IN$", tok) is not None
        or (len(tok) <= 2 and re.match(r'^[A-Z]+$', tok))
        or _is_plant_code(tok)           # v3.6: reject SAP plant/org codes (N141, N041, T141)
    )


def _is_descriptor_pn(tok: str) -> bool:
    """Return True if token is a descriptor-pattern false PN (e.g. '3-WAY', '4-BOLT'). (Fix 4)"""
    return bool(PN_DESCRIPTOR_PATTERNS.match(tok))


def _is_plant_code(tok: str) -> bool:
    """
    Return True if token looks like a SAP plant/purchasing-org code.

    Plant codes in WESCO SAP data follow the pattern: one letter + 3-4 digits,
    e.g. 'N141', 'N041', 'T141'.  These must never be used as part numbers.
    """
    return bool(re.match(r'^[A-Z]\d{3,4}$', tok))


def is_non_product_row(texts: list) -> bool:
    """
    P2: Return True if this row is a non-product entry (freight, service charge,
    admin line, etc.) that should not receive MFG/PN extraction.

    Avoids filling MFG/PN for overhead line items like FREIGHT, LABOR, TAX,
    DISCOUNT, MISC, etc. Only fires when the row text is an exact match to a
    known non-product keyword (whole text or first comma-token) — no partial
    matching to avoid accidentally skipping legitimate product rows.

    Checks:
      - Combined non-blank source text exactly matches a NON_PRODUCT_PATTERNS entry
      - OR the first comma-token of the combined text matches a NON_PRODUCT_PATTERNS entry
    """
    non_empty = [
        str(t).strip() for t in texts
        if str(t).strip() not in ('', 'nan', 'None', 'NaN')
    ]
    if not non_empty:
        return False  # blank row — let natural logic handle it
    combined = ', '.join(non_empty).upper().strip()
    if combined in NON_PRODUCT_PATTERNS:
        return True
    first_token = combined.split(',')[0].strip()
    if first_token in NON_PRODUCT_PATTERNS:
        return True
    return False


def _score_heuristic_pn(candidate: str) -> float:
    """
    Score a heuristic PN candidate based on how much it looks like a real part number.
    Returns confidence between 0.10 and 0.65. (Fix 6)

    Replaces the flat CONFIDENCE_SCORES['pn_fallback'] = 0.35 for heuristic extractions.
    """
    score = 0.35  # base

    # Boost: has both letters AND digits (most real PNs do)
    if re.search(r'[A-Z]', candidate) and re.search(r'[0-9]', candidate):
        score += 0.10

    # Boost: contains dash or slash separator (structured format)
    if re.search(r'[\-/]', candidate):
        score += 0.10

    # Boost: length 6-20 (sweet spot for part numbers)
    if 6 <= len(candidate) <= 20:
        score += 0.05

    # Boost: long pure alphanumeric string (like 3AXD50000731121) — very likely a real PN
    if len(candidate) >= 10 and re.match(r'^[A-Z0-9]+$', candidate):
        score += 0.10

    # Penalize: very short (1-3 chars)
    if len(candidate) <= 3:
        score -= 0.15

    # Penalize: looks like a standard/spec code (ISO, UNI, DIN prefix)
    if re.match(r'^(?:ISO|UNI|DIN|ANSI|ASTM|IEEE)\d', candidate):
        score -= 0.10

    # Penalize: starts with a digit and is short (often a dimension or quantity)
    if re.match(r'^\d', candidate) and len(candidate) < 6:
        score -= 0.10

    return max(0.10, min(0.65, score))


# ─────────────────────────────────────────────────────────────
#  PN INDIVIDUAL STRATEGY FUNCTIONS  (return 3-tuple)
# ─────────────────────────────────────────────────────────────

def extract_pn_labeled(text: str) -> tuple:
    """
    Strategy: Labeled PN extraction (PN:, MN:, MODEL:, etc.)
    Returns (pn, 'label', confidence) or (None, 'none', 0.0).

    v3.4: If the first word has no digits (e.g. "PNOZ" from "MN: PNOZ MI1P"), tries
    collapsing spaces out of the full match to recover "PNOZMI1P", "MVE160/2M", etc.
    """
    if not text:
        return None, 'none', 0.0
    t = str(text).upper()
    for pat in PN_LABEL_PATTERNS:
        m = re.search(pat, t)
        if m:
            raw = m.group(1).strip()
            pn = _clean_pn_token(raw)
            if pn and re.search(r'[0-9]', pn):
                # Normal path: first word already has digits — use it as-is
                return pn, 'label', CONFIDENCE_SCORES['pn_label']
            # v3.4: first word has no digits (all-alpha prefix like "PNOZ", "MVE", "MRV")
            # Try collapsing spaces from the full matched value: "PNOZ MI1P" → "PNOZMI1P"
            collapsed_raw = re.sub(r'\s+', '', raw.split(',')[0].split(';')[0])
            cm = re.match(r'^[A-Z0-9][A-Z0-9\-_/\.]*', collapsed_raw)
            if cm:
                cand = cm.group(0)
                if re.search(r'[A-Z]', cand) and re.search(r'[0-9]', cand) and len(cand) >= 4:
                    return cand, 'label', CONFIDENCE_SCORES['pn_label']
            # Fall back to the original pn (may be all-alpha, will be caught by Rule 8)
            if pn:
                return pn, 'label', CONFIDENCE_SCORES['pn_label']
    return None, 'none', 0.0


def extract_pn_structured(text: str) -> tuple:
    """
    Strategy: Structured PN extraction (tokens with dashes/slashes like 6EP1434-2BA20).
    Returns (pn, 'pn_structured', confidence) or (None, 'none', 0.0).
    """
    if not text:
        return None, 'none', 0.0
    t = str(text).upper()
    matches = STRUCTURED_PN_RE.findall(t)
    # Filter out spec values, descriptor patterns, and invalid prefixes
    valid = [
        m for m in matches
        if not _is_spec_value(m)
        and not _is_descriptor_pn(m)
        and not any(m.startswith(p) for p in INVALID_PN_PREFIXES)
        and re.search(r'[A-Z]', m)
        and re.search(r'[0-9]', m)
        and len(m) <= 30
        and not (len(m) <= 3 and m.isalpha())  # reject short pure-alpha tokens
    ]
    if valid:
        # Prefer the longest candidate (more specific)
        best = max(valid, key=len)
        return best, 'pn_structured', CONFIDENCE_SCORES['pn_structured']
    return None, 'none', 0.0


def extract_pn_heuristic(text: str) -> tuple:
    """
    Strategy: Heuristic PN extraction (last mixed alphanumeric token).
    Uses graduated confidence via _score_heuristic_pn() (Fix 6).
    Rejects descriptor-pattern tokens and short pure-alpha tokens (Fix 4).
    Returns (pn, 'heuristic', confidence) or (None, 'none', 0.0).
    """
    if not text:
        return None, 'none', 0.0
    t = str(text).upper()
    tokens = re.split(r"[\s,;]\s*", t)
    cands = []
    for tok in tokens:
        tok2 = _clean_pn_token(tok)
        if not tok2:
            continue
        if (re.search(r"[A-Z]", tok2) and re.search(r"\d", tok2)
                and len(tok2) <= 25
                and not _is_spec_value(tok2)
                and not _is_descriptor_pn(tok2)  # Fix 4: reject NUMBER-DESCRIPTOR patterns
                and not (len(tok2) <= 3 and tok2.isalpha())):  # Fix 4: reject short pure-alpha
            cands.append(tok2)
    if cands:
        # v3.2 Fix 2: prefer highest-scoring candidate (favours longer, mixed-format codes
        # like 3AXD50000731121 over shorter trailing tokens). Rightmost position used as
        # tiebreaker so original last-wins behaviour is preserved when scores are equal.
        if len(cands) == 1:
            best = cands[0]
        else:
            scored_cands = [(c, _score_heuristic_pn(c), i) for i, c in enumerate(cands)]
            scored_cands.sort(key=lambda x: (x[1], x[2]), reverse=True)
            best = scored_cands[0][0]
        conf = _score_heuristic_pn(best)  # Fix 6: graduated confidence
        return best, 'heuristic', conf
    return None, 'none', 0.0


def extract_pn_dash_catalog(text: str) -> tuple:
    """
    Strategy: Extract PN from 'CATALOG_NUMBER - Description' format. (Fix 5)
    Common in McMaster-Carr, ULINE, and other distributor catalog entries.
    Example: "6970T53 - Antislip Tape" → PN='6970T53'
    v3.4: Also handles "CATALOG_NUMBER / Description" (space-slash-space) format.
    Example: "7619K144 / LINE 2 WASHLINE" → PN='7619K144'
    Returns (pn, 'dash_catalog', confidence) or (None, 'none', 0.0).
    """
    if not text:
        return None, 'none', 0.0
    m = re.match(r'^([A-Z0-9][A-Z0-9\-\.]*?)\s+[-/]\s+', text.strip(), re.IGNORECASE)
    if m:
        candidate = m.group(1).strip().upper()
        # Validate: must have both letters and digits, and a reasonable length
        if (re.search(r'[A-Z]', candidate) and re.search(r'[0-9]', candidate)
                and 3 <= len(candidate) <= 20):
            return candidate, 'dash_catalog', CONFIDENCE_SCORES['pn_dash_catalog']
    return None, 'none', 0.0


def extract_pn_trailing_catalog(text: str) -> tuple:
    """
    v3.2 Fix 1 — Extract PN from trailing catalog code in comma-delimited description.

    Targets McMaster-Carr and Applied Industrial rows in DESC,DESC,CATALOG format:
        'SWITCH,DISCONNECT,80A,7815N15'   → PN='7815N15'
        'ENCLOSURE,ELECTRICAL,7619K144'   → PN='7619K144'
        'SWITCH,EMERGENCY STOP,6741K46'   → PN='6741K46'

    Validation gates:
      - ≥ 2 tokens total (need at least one descriptor + one code)
      - Last token has mixed alpha+digits
      - Last token length 5-15 chars
      - Last token is NOT a spec value or descriptor pattern
      - At least half of preceding tokens are alpha-only or spec values

    Returns (pn, 'trailing_catalog', 0.68) or (None, 'none', 0.0).
    Anti-regression: caller skips this candidate if a labeled PN (conf 0.95) already exists.
    """
    if not text:
        return None, 'none', 0.0
    t = str(text).strip().upper()
    tokens = [tok.strip() for tok in t.split(',')]
    if len(tokens) < 2:
        return None, 'none', 0.0

    last = tokens[-1]
    # Must have mixed alpha+digits
    if not (re.search(r'[A-Z]', last) and re.search(r'[0-9]', last)):
        return None, 'none', 0.0
    # Length gate: 5-15 chars
    if not (5 <= len(last) <= 15):
        return None, 'none', 0.0
    # Not a spec value or descriptor-pattern
    if _is_spec_value(last) or _is_descriptor_pn(last):
        return None, 'none', 0.0

    # v3.4: Reject dimension-annotation tokens like "W 2.6875IN", "ID 180MM"
    if DIMENSION_ANNOTATION_RE.match(last):
        return None, 'none', 0.0
    # v3.4: Last token must contain only valid PN characters (no spaces, #, ", etc.)
    if not re.match(r'^[A-Z0-9][A-Z0-9\-_/\.]+$', last):
        return None, 'none', 0.0

    # Preceding tokens: majority should be alpha-only descriptors or spec values
    # v3.4: Space-aware — "MOLD CASE", "CKT BRKR" count as descriptors (not just single words)
    preceding = tokens[:-1]
    descriptor_count = sum(
        1 for tok in preceding
        if all(c.isalpha() or c == ' ' for c in tok) or _is_spec_value(tok) or tok in BARE_SPEC_TOKENS
    )
    if descriptor_count < len(preceding) / 2:
        return None, 'none', 0.0

    return last, 'trailing_catalog', CONFIDENCE_SCORES['pn_trailing_catalog']


def extract_pn_trailing_numeric(text: str) -> tuple:
    """
    v3.2 Fix 5 — Extract pure-numeric trailing part code from comma-delimited description.

    Targets Bruno Folcieri internal part codes that are pure digits:
        'BOX,COUNTERSHAFT,4900047'       → PN='4900047'
        'SHAFT,SPACER,BOTTOM,17000120'   → PN='17000120' (if ≥7 digits)

    Validation gates:
      - ≥ 2 tokens total
      - Last token is purely numeric
      - Last token is ≥ 7 digits (guards against quantities, dimension numbers)

    Confidence 0.50 ensures any structured/labeled/trailing_catalog candidate wins over this.
    Returns (pn, 'trailing_numeric', 0.50) or (None, 'none', 0.0).
    """
    if not text:
        return None, 'none', 0.0
    t = str(text).strip().upper()
    tokens = [tok.strip() for tok in t.split(',')]
    if len(tokens) < 2:
        return None, 'none', 0.0

    last = tokens[-1]
    # Pure numeric ≥7 digits (original behaviour)
    if last.isdigit() and len(last) >= 7:
        return last, 'trailing_numeric', CONFIDENCE_SCORES['pn_trailing_numeric']
    # v3.4: Numeric-dash codes like "17000120500-01" (all-digit groups joined by dashes)
    if (re.match(r'^\d{6,}(?:[\-/]\d+)+$', last) and
            last.replace('-', '').replace('/', '').isdigit()):
        return last, 'trailing_numeric', CONFIDENCE_SCORES['pn_trailing_numeric']

    return None, 'none', 0.0


def extract_pn_first_token_catalog(text: str) -> tuple:
    """
    v3.4 — Extract PN when the first comma-separated token is a catalog number.

    Targets distributor catalog format where the PN comes first:
        '7950K146, 4 GAUGE WIRE'     → PN='7950K146'
        'RA107RR, Timken, Cylindrical OD' → PN='RA107RR'
        '3488K94,ELECTRIC MIXER,...' → PN='3488K94'

    Validation gates:
      - ≥ 2 comma-separated tokens
      - First token is purely alphanumeric (no spaces, valid PN chars only)
      - First token has both letters AND digits
      - First token length 5-20 chars
      - First token is NOT a spec value or descriptor pattern
      - First token NOT in INVALID_PN_PREFIXES

    Returns (pn, 'first_token_catalog', 0.68) or (None, 'none', 0.0).
    """
    if not text:
        return None, 'none', 0.0
    t = str(text).strip().upper()
    tokens = [tok.strip() for tok in t.split(',')]
    if len(tokens) < 2:
        return None, 'none', 0.0

    first = tokens[0]
    # Must be valid PN characters only (no spaces, no special chars)
    if not re.match(r'^[A-Z0-9][A-Z0-9\-/\.]+$', first):
        return None, 'none', 0.0
    # Must have both letters AND digits
    if not (re.search(r'[A-Z]', first) and re.search(r'[0-9]', first)):
        return None, 'none', 0.0
    # Length gate: 5-20 chars
    if not (5 <= len(first) <= 20):
        return None, 'none', 0.0
    # Not a spec value or descriptor pattern
    if _is_spec_value(first) or _is_descriptor_pn(first):
        return None, 'none', 0.0
    # Not an invalid PN prefix
    if any(first.startswith(p) for p in INVALID_PN_PREFIXES):
        return None, 'none', 0.0

    return first, 'first_token_catalog', CONFIDENCE_SCORES['pn_first_token_catalog']


def extract_pn_embedded_code(text: str) -> tuple:
    """
    v3.6 — Extract PN from a long alphanumeric code embedded in comma-delimited text.

    Targets drive/module/unit part numbers that appear as a middle token in a comma
    list, not first and not last:
        'DRV,3AXD50000731121,5HP,480V,BAGGING'  → PN='3AXD50000731121'
        'MODULE,ABB123456789AB,2-DI,2-DI/O'     → PN='ABB123456789AB'

    The ≥10-char length gate keeps short spec codes (M12X40, L150N, 3PH)
    from firing while still catching typical 10-16 char drive part numbers.

    Validation gates (middle tokens only — not first, not last):
      - Both letters AND digits present
      - No spaces (pure code token, not a description phrase)
      - Length ≥ 10 chars
      - Not a spec value, descriptor pattern, or plant code
      - Not starting with an INVALID_PN_PREFIX

    Returns the longest qualifying candidate.
    Returns (pn, 'embedded_code', 0.72) or (None, 'none', 0.0).
    """
    if not text:
        return None, 'none', 0.0
    t = str(text).strip().upper()
    tokens = [tok.strip() for tok in t.split(',')]
    if len(tokens) < 3:   # need at least: descriptor, code, something-else
        return None, 'none', 0.0

    middle_tokens = tokens[1:-1]
    candidates = []
    for tok in middle_tokens:
        if ' ' in tok:                                     # reject phrase tokens
            continue
        if not (re.search(r'[A-Z]', tok) and re.search(r'[0-9]', tok)):
            continue
        if len(tok) < 10:                                  # length gate
            continue
        if _is_spec_value(tok) or _is_descriptor_pn(tok):
            continue
        if any(tok.startswith(p) for p in INVALID_PN_PREFIXES):
            continue
        candidates.append(tok)

    if candidates:
        best = max(candidates, key=len)
        return best, 'embedded_code', CONFIDENCE_SCORES['pn_embedded_code']
    return None, 'none', 0.0


# ─────────────────────────────────────────────────────────────
#  MFG INDIVIDUAL STRATEGY FUNCTIONS  (return 3-tuple)
# ─────────────────────────────────────────────────────────────

def extract_mfg_labeled(text: str) -> tuple:
    """
    Strategy: Labeled MFG extraction (MANUFACTURER: label).
    Returns (mfg, 'label', confidence) or (None, 'none', 0.0).
    """
    if not text:
        return None, 'none', 0.0
    T = str(text).upper()
    m = MFG_LABEL_RE.search(T)
    if m:
        mfg = re.sub(r"\s+", " ", m.group(1).strip())
        return mfg, 'label', CONFIDENCE_SCORES['mfg_label']
    return None, 'none', 0.0


def extract_mfg_context(text: str, pn_hint: Optional[str] = None) -> tuple:
    """
    Strategy: Pre-label context MFG extraction (", GATES, PN:").
    Returns (mfg, 'context', confidence) or (None, 'none', 0.0).
    """
    if not text:
        return None, 'none', 0.0
    T = str(text).upper()

    # Pre-label pattern: ", <MFG>, PN:"
    m = PRELABEL_MFG_RE.search(T)
    if m:
        mfg = re.sub(r"\s+", " ", m.group(1).strip())
        return mfg, 'context', CONFIDENCE_SCORES['mfg_context']

    # Context with PN hint
    if pn_hint:
        m = re.search(r",\s*([A-Z][A-Z\-&\./\s]{2,40}?)\s*,\s*" + re.escape(pn_hint), T)
        if m:
            mfg = re.sub(r"\s+", " ", m.group(1).strip())
            return mfg, 'context', CONFIDENCE_SCORES['mfg_context']

    return None, 'none', 0.0


def extract_mfg_known(text: str, known_mfgs: set) -> tuple:
    """
    Strategy: Known manufacturer name lookup in text.
    Uses word-boundary matching to prevent false positives from substrings.
    (Fix 1) Prevents "GE" from matching inside "GEARED", "EMERGENCY", "SQUEEGEE", etc.
    Returns (mfg, 'known_mfg', confidence) or (None, 'none', 0.0).
    """
    if not text or not known_mfgs:
        return None, 'none', 0.0
    T = str(text).upper()
    for name in sorted(known_mfgs, key=len, reverse=True):
        if not name:
            continue
        # Word-boundary matching: name must not be embedded in a larger alphanumeric token.
        # e.g. "GE" won't match "GEARED" because GE is followed by A (alphanumeric).
        if re.search(r'(?<![A-Z0-9])' + re.escape(name) + r'(?![A-Z0-9])', T):
            return name, 'known_mfg', CONFIDENCE_SCORES['mfg_known']
    return None, 'none', 0.0


def _extract_mfg_from_supplier_value(supplier_raw: str) -> tuple:
    """
    Internal: extract MFG from a supplier column value.
    Returns (mfg_cleaned, confidence) excluding distributors.

    P1: Applies NORMALIZE_MFG to raw and cleaned supplier names before returning,
    so abbreviated supplier forms (e.g. "SEW EURODR") resolve to their canonical
    manufacturer name early — preventing sanitize_mfg from wrongly rejecting them.
    Confidence stays at 0.55 so text-derived MFG candidates still win when present.
    """
    if not supplier_raw:
        return None, 0.0
    s = str(supplier_raw).strip()
    if s.upper() in ('', 'NAN', 'NONE'):
        return None, 0.0
    supplier_upper = s.upper()
    is_distributor = (
        supplier_upper in DISTRIBUTORS
        or any(d in supplier_upper for d in DISTRIBUTORS if len(d) > 5)
    )
    if is_distributor:
        return None, 0.0

    # P1: Try NORMALIZE_MFG on raw supplier name (catches abbreviated forms in supplier col)
    normalized_raw = NORMALIZE_MFG.get(supplier_upper)
    if normalized_raw and normalized_raw in KNOWN_MANUFACTURERS:
        return normalized_raw, CONFIDENCE_SCORES['mfg_supplier']

    cleaned = _clean_supplier_name(s)
    if not cleaned:
        return None, 0.0

    cleaned_upper = cleaned.strip().upper()

    # P1: Normalize cleaned name so abbreviations resolve before sanitize_mfg sees them
    normalized_cleaned = NORMALIZE_MFG.get(cleaned_upper, cleaned_upper)
    return normalized_cleaned, CONFIDENCE_SCORES['mfg_supplier']


# ─────────────────────────────────────────────────────────────
#  BACKWARD-COMPATIBLE PUBLIC WRAPPERS (return 2-tuple)
# ─────────────────────────────────────────────────────────────

def extract_pn_from_text(text: str) -> tuple:
    """
    Extract a Part Number from free text.

    Returns (pn, source_type) — backward-compatible 2-tuple.
    Internally uses multi-strategy extraction and returns the best result.
    """
    if not text:
        return None, 'none'

    # Try labeled first (highest priority)
    pn, src, _ = extract_pn_labeled(text)
    if pn:
        return pn, 'label'

    # Try heuristic (original fallback behavior)
    pn, src, _ = extract_pn_heuristic(text)
    if pn:
        return pn, 'fallback'

    return None, 'none'


def extract_mfg_from_text(text: str, pn_hint: Optional[str], known_mfgs: set) -> tuple:
    """
    Extract a Manufacturer from free text.

    Returns (mfg, source_type) — backward-compatible 2-tuple.
    Internally uses multi-strategy extraction and returns the best result.
    """
    if not text:
        return None, 'none'

    # 1) MANUFACTURER: label
    mfg, src, _ = extract_mfg_labeled(text)
    if mfg:
        return mfg, 'label'

    # 2) pre-label pattern
    mfg, src, _ = extract_mfg_context(text, pn_hint)
    if mfg:
        return mfg, 'context'

    # 3) known manufacturer names
    mfg, src, _ = extract_mfg_known(text, known_mfgs)
    if mfg:
        return mfg, 'known'

    return None, 'none'


# ═══════════════════════════════════════════════════════════════
#  SHARED HELPERS
# ═══════════════════════════════════════════════════════════════

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
    # v3.1: extended blocklist — reject descriptor/non-MFG tokens unless they are a known manufacturer (Fix 2)
    if x in MFG_BLOCKLIST and x not in KNOWN_MANUFACTURERS:
        return None
    # P0: if it's a confirmed known manufacturer, pass through immediately
    # (e.g. "3M" contains a digit but is a valid manufacturer name)
    if x in KNOWN_MANUFACTURERS:
        return NORMALIZE_MFG.get(x, x)
    if re.search(r"\d", x):
        return None
    # v3: reject ≤2-char tokens unless they are a known manufacturer
    if len(x) <= 2 and x not in KNOWN_MANUFACTURERS:
        return None
    x = NORMALIZE_MFG.get(x, x)
    x = x.replace('SQUARE-D', 'SQUARE D').replace('CROUSE-HINDS', 'CROUSE HINDS')
    x = x.replace('STATIC O RING', 'STATIC O-RING')
    return x.replace('  ', ' ')


def decode_mfg_prefix(text: str) -> tuple:
    """
    Attempt to decode a manufacturer prefix from the first token of a Short Text value.

    Some compressed product codes concatenate the MFG prefix directly with the PN,
    e.g. "HUBCS120W" → MFG "HUBBELL", PN "CS120W".

    Returns:
        (mfg, remainder_pn) if a known prefix is found and remainder has mixed alpha+digits.
        (None, None) otherwise.
    """
    if not text:
        return None, None
    # Isolate the first token (split on whitespace, dash separators, and commas)
    first_token = str(text).strip().upper().split()[0]
    first_token = first_token.split(' - ')[0].split(',')[0]

    # Try 3-char prefixes before 2-char to prefer longer matches
    for prefix_len in (3, 2):
        if len(first_token) > prefix_len:
            prefix = first_token[:prefix_len]
            remainder = first_token[prefix_len:]
            if (prefix in MFG_PREFIX_MAP
                    and re.search(r'[A-Z]', remainder)
                    and re.search(r'[0-9]', remainder)):
                return MFG_PREFIX_MAP[prefix], remainder

    return None, None


def decode_composite_code(text: str) -> tuple:
    """
    P0: Decode a 4-char manufacturer-prefixed composite product code.

    MDM systems sometimes concatenate a 4-char vendor code with the actual PN,
    e.g. "TBCO222TB" → MFG "THOMAS & BETTS", PN "222TB".
         "ALBR1492EAJ35" → MFG "ALLEN BRADLEY", PN "1492EAJ35".
         "WAGO222412" → MFG "WAGO", PN "222412".

    Unlike decode_mfg_prefix() (which handles 2-3 char SAP codes), this function
    handles 4-char MDM composite codes and allows pure-digit remainders since the
    4-char prefix is specific enough to avoid false positives.

    Returns:
        (mfg, remainder_pn) if a known 4-char prefix is found and remainder ≥ 2 chars.
        (None, None) otherwise.
    """
    if not text:
        return None, None
    # Isolate the first token — composite codes have no spaces
    first_token = str(text).strip().upper().split()[0]
    first_token = first_token.split(',')[0]

    if len(first_token) <= 4:
        return None, None

    prefix = first_token[:4]
    remainder = first_token[4:]

    if prefix not in MFG_COMPOSITE_CODE_MAP:
        return None, None
    if len(remainder) < 2:
        return None, None

    mfg = MFG_COMPOSITE_CODE_MAP[prefix]
    return mfg, remainder


def _clean_supplier_name(name: str) -> Optional[str]:
    """
    Clean a supplier name for use as an MFG fallback.

    Removes corporate suffixes (Inc., Corp., LLC, Srl, S.p.A., etc.)
    and parenthetical descriptors before normalizing whitespace.
    """
    if not name:
        return None
    s = str(name).strip()
    # Remove parenthetical info like "(Bulk Handling Systems)"
    s = re.sub(r'\s*\([^)]*\)', '', s)
    # Remove common corporate suffixes (case-insensitive)
    s = re.sub(
        r'\b(?:S\.?P\.?A\.?|Inc\.?|Corp\.?|LLC|Ltd\.?|Co\.?|Srl\.?|'
        r'Incorporated|Corporation|Limited|Company|Group|Holdings|'
        r'Intl\.?|International)\b\.?',
        '',
        s,
        flags=re.IGNORECASE,
    )
    s = re.sub(r'\s+', ' ', s).strip().rstrip('.,')
    return s if s else None


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
#  POST-EXTRACTION VALIDATION (Layer 4)
# ═══════════════════════════════════════════════════════════════

def validate_and_clean(
    df: pd.DataFrame,
    mfg_col: str = 'MFG',
    pn_col: str = 'PN',
    profile: object = None,
) -> tuple:
    """
    Post-extraction validation pass. Clears values that are likely wrong
    and returns (cleaned_df, corrections_list).

    Rules applied in order:
      1. PN is a spec value → clear PN
      2. MFG contains digits → clear MFG
      3. MFG is a known descriptor → clear MFG
      4. MFG == PN → clear MFG
      5. MFG frequency anomaly (>60% of filled rows, not a real known MFG) → clear those rows
      6. PN is too short (1-2 chars) → clear PN
      7. PN is a known manufacturer name → clear PN

    Args:
        df: DataFrame with MFG and PN columns already filled
        mfg_col: Name of the MFG column
        pn_col: Name of the PN column
        profile: FileProfile (unused currently, reserved for future tuning)

    Returns:
        (cleaned_df, corrections) where corrections is a list of dicts describing
        each change made.
    """
    df = df.copy()
    corrections = []

    # Check columns exist
    has_mfg = mfg_col in df.columns
    has_pn = pn_col in df.columns

    # Build in-frame manufacturer set for Rule 7
    in_frame_mfgs = set()
    if has_mfg:
        for v in df[mfg_col].dropna().astype(str):
            v_clean = v.strip().upper()
            if v_clean and v_clean not in ('', 'NAN', 'NONE'):
                in_frame_mfgs.add(v_clean)
    all_known_mfgs = KNOWN_MANUFACTURERS | in_frame_mfgs

    def _is_blank(val):
        return str(val).strip().upper() in ('', 'NAN', 'NONE', 'NAT')

    def _clear(df, idx, col, old_val, reason):
        df.at[idx, col] = ''
        corrections.append({
            'row': idx,
            'field': col,
            'old_value': old_val,
            'reason': reason,
            'action': 'cleared',
        })

    # ── Rule 1: PN is a spec value ────────────────────────────────────────────
    if has_pn:
        for idx, row in df.iterrows():
            pn_val = str(row.get(pn_col, '')).strip().upper()
            if _is_blank(pn_val):
                continue
            if (SPEC_VALUE_RE.match(pn_val)
                    or DIMENSION_RE.match(pn_val)
                    or pn_val in BARE_SPEC_TOKENS):
                _clear(df, idx, pn_col, pn_val, 'spec_value')

    # ── Rule 2: MFG contains digits ───────────────────────────────────────────
    # Exception: known manufacturers like "3M" are allowed to have digits.
    if has_mfg:
        for idx, row in df.iterrows():
            mfg_val = str(row.get(mfg_col, '')).strip().upper()
            if _is_blank(mfg_val):
                continue
            if re.search(r'\d', mfg_val) and mfg_val not in KNOWN_MANUFACTURERS:
                _clear(df, idx, mfg_col, mfg_val, 'mfg_has_digits')

    # ── Rule 3: MFG is a known descriptor ─────────────────────────────────────
    if has_mfg:
        for idx, row in df.iterrows():
            mfg_val = str(row.get(mfg_col, '')).strip().upper()
            if _is_blank(mfg_val):
                continue
            if (mfg_val in DESCRIPTORS
                    or any(k in mfg_val for k in DESCRIPTOR_KEYWORDS)):
                _clear(df, idx, mfg_col, mfg_val, 'descriptor')

    # ── Rule 4: MFG == PN ─────────────────────────────────────────────────────
    if has_mfg and has_pn:
        for idx, row in df.iterrows():
            mfg_val = str(row.get(mfg_col, '')).strip().upper()
            pn_val = str(row.get(pn_col, '')).strip().upper()
            if _is_blank(mfg_val) or _is_blank(pn_val):
                continue
            if mfg_val == pn_val:
                _clear(df, idx, mfg_col, mfg_val, 'mfg_equals_pn')

    # ── Rule 5: MFG frequency anomaly ─────────────────────────────────────────
    if has_mfg:
        filled_mfgs = [
            str(row.get(mfg_col, '')).strip().upper()
            for _, row in df.iterrows()
            if not _is_blank(str(row.get(mfg_col, '')))
        ]
        total_filled = len(filled_mfgs)
        if total_filled > 0:
            from collections import Counter
            mfg_counts = Counter(filled_mfgs)
            for mfg_val, count in mfg_counts.items():
                if (count / total_filled > 0.60
                        and mfg_val not in KNOWN_MANUFACTURERS
                        and mfg_val not in all_known_mfgs):
                    for idx, row in df.iterrows():
                        cur = str(row.get(mfg_col, '')).strip().upper()
                        if cur == mfg_val:
                            _clear(df, idx, mfg_col, mfg_val, 'mfg_frequency_anomaly')

    # ── Rule 6: PN is too short (1-2 chars) ───────────────────────────────────
    if has_pn:
        for idx, row in df.iterrows():
            pn_val = str(row.get(pn_col, '')).strip().upper()
            if _is_blank(pn_val):
                continue
            if len(pn_val) <= 2:
                _clear(df, idx, pn_col, pn_val, 'pn_too_short')

    # ── Rule 7: PN is a known manufacturer name ───────────────────────────────
    if has_pn:
        for idx, row in df.iterrows():
            pn_val = str(row.get(pn_col, '')).strip().upper()
            if _is_blank(pn_val):
                continue
            if pn_val in all_known_mfgs:
                _clear(df, idx, pn_col, pn_val, 'pn_is_manufacturer')

    # ── Rule 8: v3.2 — PN is all-alpha (no digits) → not a real part number ──
    # Safety net for cases where pure-word text (PACKAGING, CALIPERS, etc.) slips through.
    # Exception: labeled PNs like "PKZ" are valid model codes; we only reject when they're
    # clearly natural-language words (all-alpha, no digits, length ≤ 10).
    if has_pn:
        for idx, row in df.iterrows():
            pn_val = str(row.get(pn_col, '')).strip().upper()
            if _is_blank(pn_val):
                continue
            if (pn_val.isalpha()
                    and not re.search(r'[0-9]', pn_val)
                    and len(pn_val) <= 12
                    and pn_val not in KNOWN_MANUFACTURERS):
                _clear(df, idx, pn_col, pn_val, 'pn_all_alpha_no_digits')

    return df, corrections


# ═══════════════════════════════════════════════════════════════
#  PIPELINE: MFG + PN EXTRACTION (Electrical spec)
# ═══════════════════════════════════════════════════════════════

def pipeline_mfg_pn(
    df: pd.DataFrame,
    source_cols: Optional[list] = None,
    mfg_col: str = 'MFG',
    pn_col: str = 'PN',
    add_sim: bool = True,
    column_mapping: Optional[dict] = None,
    supplier_col: Optional[str] = None,
    confidence_threshold: Optional[float] = None,
    profile_override: object = None,
    auto_validate: bool = True,
) -> JobResult:
    """
    Full MFG/PN extraction pipeline with format-adaptive multi-strategy extraction.

    Args:
        df: Input DataFrame
        source_cols: List of column names to search for MFG and PN text
        mfg_col: Target column for MFG output
        pn_col: Target column for PN output
        add_sim: Whether to generate SIM column
        column_mapping: Optional column mapping from column_mapper.map_columns()
        supplier_col: Optional column name containing supplier/vendor names
        confidence_threshold: Override confidence threshold (uses profiler default if None)
        profile_override: Use this FileProfile instead of profiling the file
        auto_validate: Whether to run post-extraction validation pass (default True)

    Returns:
        JobResult with df, counts, file_profile, low_confidence_items, confidence_stats
    """
    result = JobResult(total_rows=len(df))
    df = df.copy()

    # If column_mapping provided and source_cols not explicitly set, use mapping
    if column_mapping and not source_cols:
        source_cols = (column_mapping.get('source_description', []) +
                       column_mapping.get('source_po_text', []) +
                       column_mapping.get('source_notes', []))
        mfg_col = column_mapping.get('mfg_output') or mfg_col
        pn_col = column_mapping.get('pn_output') or pn_col

    if not source_cols:
        source_cols = []

    # Ensure output columns exist
    if mfg_col not in df.columns:
        df[mfg_col] = ''
    if pn_col not in df.columns:
        df[pn_col] = ''

    # ── Step 1: File profiling ─────────────────────────────────────────────────
    file_profile = profile_override
    if file_profile is None and profile_file is not None:
        valid_source_cols = [c for c in source_cols if c in df.columns]
        file_profile = profile_file(
            df,
            source_cols=valid_source_cols,
            supplier_col=supplier_col,
            mfg_col=mfg_col if mfg_col in df.columns else None,
        )

    # Determine strategy weights and confidence threshold
    if file_profile is not None:
        strategy_weights = file_profile.strategy_weights or {}
        thresh = confidence_threshold if confidence_threshold is not None else file_profile.confidence_threshold
    else:
        strategy_weights = STRATEGY_WEIGHTS.get('MIXED', {})
        thresh = confidence_threshold if confidence_threshold is not None else 0.40

    result.file_profile = file_profile

    # ── Step 1b: Schema classification — column-structure-aware routing (v3.5.0) ──
    # Detects which schema pattern the file uses (SAP_STANDARD, SAP_SHORT_TEXT, etc.)
    # and multiplicatively merges schema multipliers with content-archetype weights.
    # Both layers must agree to produce a strong boost; disagreement dampens.
    schema_profile = None
    if _classify_schema is not None and column_mapping is not None:
        schema_profile = _classify_schema(column_mapping, file_profile)
        strategy_weights = schema_profile.strategy_weights
        if confidence_threshold is None:
            thresh = schema_profile.confidence_threshold

    result.schema_profile = schema_profile

    # ── Step 2: Mine known manufacturers ──────────────────────────────────────
    known_mfgs = set(KNOWN_MANUFACTURERS)
    for col in source_cols:
        if col in df.columns:
            for text in df[col].dropna().astype(str).str.upper().values:
                m = MFG_LABEL_RE.search(text)
                if m:
                    known_mfgs.add(re.sub(r"\s+", " ", m.group(1).strip()))

    mfg_filled = 0
    pn_filled = 0
    low_confidence_flags = []
    mfg_confidences = []
    pn_confidences = []

    # ── Step 3: Per-row multi-strategy extraction ──────────────────────────────
    for idx, row in df.iterrows():
        texts = [str(row.get(c, '')) for c in source_cols if c in df.columns]
        combined_text = ' | '.join(t for t in texts if t.strip())

        # P2: Skip non-product rows only when there is no supplier fallback available.
        # Rows with a non-blank supplier are still processed so supplier_fallback
        # can record the correct MFG (e.g. shipping row with supplier=ULINE → MFG=ULINE).
        if is_non_product_row(texts):
            supplier_val = (
                str(row.get(supplier_col, '')).strip()
                if supplier_col and supplier_col in df.columns
                else ''
            )
            if supplier_val in ('', 'nan', 'None', 'NaN'):
                continue

        # ── Collect ALL PN candidates ──
        pn_candidates = []

        for t in texts:
            pn, src, conf = extract_pn_labeled(t)
            if pn:
                pn_candidates.append(ExtractionCandidate(pn, 'label', conf))

            pn, src, conf = extract_pn_structured(t)
            if pn:
                pn_candidates.append(ExtractionCandidate(pn, 'pn_structured', conf))

            pn, src, conf = extract_pn_heuristic(t)
            if pn:
                pn_candidates.append(ExtractionCandidate(pn, 'heuristic', conf))

            # Fix 5 (old): dash-separated catalog number (McMaster-Carr / ULINE format)
            pn, src, conf = extract_pn_dash_catalog(t)
            if pn:
                pn_candidates.append(ExtractionCandidate(pn, 'dash_catalog', conf))

            # v3.2 Fix 1: trailing catalog code in DESC,DESC,CATALOG format
            # Skip if a labeled PN already exists (labeled confidence 0.95 wins naturally,
            # but explicit guard prevents noisy candidates polluting the list).
            has_label = any(c.source == 'label' for c in pn_candidates)
            if not has_label:
                pn, src, conf = extract_pn_trailing_catalog(t)
                if pn:
                    pn_candidates.append(ExtractionCandidate(pn, 'trailing_catalog', conf))

            # v3.2 Fix 5: trailing pure-numeric code ≥7 digits (Bruno Folcieri internal codes)
            pn, src, conf = extract_pn_trailing_numeric(t)
            if pn:
                pn_candidates.append(ExtractionCandidate(pn, 'trailing_numeric', conf))

            # v3.4: First-token catalog format (CATALOG_NUM, description)
            pn, src, conf = extract_pn_first_token_catalog(t)
            if pn:
                pn_candidates.append(ExtractionCandidate(pn, 'first_token_catalog', conf))

            # v3.6: Embedded long alphanumeric code in comma-delimited list (e.g. ABB drives)
            pn, src, conf = extract_pn_embedded_code(t)
            if pn:
                pn_candidates.append(ExtractionCandidate(pn, 'embedded_code', conf))

        # Strategy: prefix decode (from first token, 2-3 char SAP-style codes)
        prefix_mfg, prefix_pn = decode_mfg_prefix(combined_text)
        if prefix_pn:
            pn_candidates.append(ExtractionCandidate(
                prefix_pn, 'prefix_decode', CONFIDENCE_SCORES['pn_prefix_decode']
            ))

        # P0: composite code decode (4-char MDM-style codes, e.g. TBCO222TB)
        composite_mfg, composite_pn = decode_composite_code(combined_text)
        if composite_pn:
            pn_candidates.append(ExtractionCandidate(
                composite_pn, 'composite_code', CONFIDENCE_SCORES['pn_composite_code']
            ))

        # Strategy: pure catalog (entire first text blob IS the PN)
        # v3.2: require at least one digit — pure-alpha words like "PACKAGING" are not PNs
        # v3.4: allow underscore so "37520423011_REV1" is caught as a catalog code
        first_text = texts[0].strip().upper() if texts else ''
        if (re.match(r'^[A-Z0-9][A-Z0-9\-/_\.]*$', first_text)
                and len(first_text) < 25
                and re.search(r'[0-9]', first_text)
                and not _is_spec_value(first_text)):
            pn_candidates.append(ExtractionCandidate(
                first_text, 'pn_catalog', CONFIDENCE_SCORES['pn_catalog']
            ))

        # Pick best PN
        best_pn, best_pn_src, best_pn_conf = pick_best(pn_candidates, strategy_weights)

        # ── Collect ALL MFG candidates ──
        mfg_candidates = []

        for t in texts:
            mfg, src, conf = extract_mfg_labeled(t)
            if mfg:
                mfg_candidates.append(ExtractionCandidate(mfg, 'label', conf))

            mfg, src, conf = extract_mfg_context(t, best_pn)
            if mfg:
                mfg_candidates.append(ExtractionCandidate(mfg, 'context', conf))

            mfg, src, conf = extract_mfg_known(t, known_mfgs)
            if mfg:
                mfg_candidates.append(ExtractionCandidate(mfg, 'known_mfg', conf))

        # Strategy: prefix decode (2-3 char SAP-style codes)
        if prefix_mfg:
            mfg_candidates.append(ExtractionCandidate(
                prefix_mfg, 'prefix_decode', CONFIDENCE_SCORES['mfg_prefix_decode']
            ))

        # P0: composite code decode (4-char MDM-style codes)
        if composite_mfg:
            mfg_candidates.append(ExtractionCandidate(
                composite_mfg, 'composite_code', CONFIDENCE_SCORES['mfg_composite_code']
            ))

        # Strategy: supplier fallback
        if supplier_col and supplier_col in df.columns:
            sup_raw = str(row.get(supplier_col, ''))
            sup_mfg, sup_conf = _extract_mfg_from_supplier_value(sup_raw)
            if sup_mfg:
                mfg_candidates.append(ExtractionCandidate(
                    sup_mfg, 'supplier_fallback', sup_conf
                ))

        # Pick best MFG
        best_mfg, best_mfg_src, best_mfg_conf = pick_best(mfg_candidates, strategy_weights)

        # Sanitize MFG
        mfg_final = sanitize_mfg(best_mfg) if best_mfg else None
        pn_final = best_pn

        # ── Write MFG if blank and confidence passes threshold ──────────────
        cur_mfg = str(row.get(mfg_col, '')).strip()
        if cur_mfg in ('', 'nan', 'None', 'NaN'):
            if mfg_final and best_mfg_conf >= thresh:
                df.at[idx, mfg_col] = mfg_final
                mfg_filled += 1
                mfg_confidences.append(best_mfg_conf)
            elif mfg_final and best_mfg_conf > 0:
                low_confidence_flags.append({
                    'row': idx, 'field': 'MFG',
                    'value': mfg_final, 'confidence': best_mfg_conf,
                    'source': best_mfg_src,
                })

        # ── Write PN if blank and confidence passes threshold ───────────────
        cur_pn = str(row.get(pn_col, '')).strip()
        if cur_pn in ('', 'nan', 'None', 'NaN'):
            if pn_final and best_pn_conf >= thresh:
                df.at[idx, pn_col] = pn_final
                pn_filled += 1
                pn_confidences.append(best_pn_conf)
            elif pn_final and best_pn_conf > 0:
                low_confidence_flags.append({
                    'row': idx, 'field': 'PN',
                    'value': pn_final, 'confidence': best_pn_conf,
                    'source': best_pn_src,
                })

    # Tidy formatting
    if mfg_col in df.columns:
        df[mfg_col] = df[mfg_col].apply(
            lambda s: re.sub(r"\s+", " ", NORMALIZE_MFG.get(str(s).strip().upper(), str(s).strip().upper()))
            if pd.notna(s) and str(s).strip() not in ('', 'nan', 'None', 'NaN') else s
        )
    if pn_col in df.columns:
        df[pn_col] = df[pn_col].apply(
            lambda s: re.sub(r"\s+", "", str(s).strip().upper())
            if pd.notna(s) and str(s).strip() not in ('', 'nan', 'None', 'NaN') else s
        )

    # ── Step 4: Post-extraction validation ────────────────────────────────────
    validation_corrections = []
    if auto_validate:
        df, validation_corrections = validate_and_clean(df, mfg_col=mfg_col, pn_col=pn_col)

    # ── Step 5: SIM generation ────────────────────────────────────────────────
    sim_filled = 0
    if add_sim:
        df['SIM'] = (
            df[mfg_col].fillna('').astype(str)
            + ' '
            + df[pn_col].fillna('').astype(str)
        ).str.strip()
        sim_filled = (df['SIM'] != '').sum()

    # ── Step 6: Confidence stats ──────────────────────────────────────────────
    all_conf = mfg_confidences + pn_confidences
    n_above = sum(1 for c in all_conf if c >= thresh)
    n_below = len(all_conf) - n_above
    confidence_stats = {
        'avg_mfg_confidence': sum(mfg_confidences) / len(mfg_confidences) if mfg_confidences else 0.0,
        'avg_pn_confidence': sum(pn_confidences) / len(pn_confidences) if pn_confidences else 0.0,
        'pct_above_threshold': n_above / len(all_conf) if all_conf else 0.0,
        'pct_below_threshold': n_below / len(all_conf) if all_conf else 0.0,
        'threshold_used': thresh,
    }

    result.df = df
    result.mfg_filled = mfg_filled
    result.pn_filled = pn_filled
    result.sim_filled = sim_filled
    result.issues = validation_corrections
    result.low_confidence_items = low_confidence_flags
    result.confidence_stats = confidence_stats
    return result


# ═══════════════════════════════════════════════════════════════
#  PIPELINE: PART NUMBER REPROCESSING (MRO spec)
# ═══════════════════════════════════════════════════════════════

def pipeline_part_number(df: pd.DataFrame, pn_col: str = 'Part Number 1',
                          mfg_col: str = 'Manufacturer 1',
                          text_cols: Optional[list] = None) -> JobResult:
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

def run_qa(df: pd.DataFrame, mfg_col: str = 'MFG') -> list:
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
