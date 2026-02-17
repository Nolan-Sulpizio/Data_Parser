# Changelog

All notable changes to the Wesco MRO Data Parser will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [3.1.0] — 2026-02-17

### Fixed — Precision Refinement Pass (7 targeted fixes against WESCO.xlsx production data)

**Fix 1 — GE Substring False Positive (201 rows eliminated)**
- `extract_mfg_known()` now uses word-boundary regex `(?<![A-Z0-9])NAME(?![A-Z0-9])` instead of simple `name in text` substring matching
- Prevents "GE" from matching inside "GEARED", "EMERGENCY", "SQUEEGEE", "GEARBOX", "GAUGE", "LEGEND", etc.
- Applies to ALL known manufacturer names (not a GE-only fix) — short names like ABB, SKF also benefit
- Legitimate standalone tokens like `BREAKER,GE,20A,1P` still match correctly

**Fix 2 — Expanded Descriptor/Keyword Blocklist (75+ rows cleaned)**
- Added `MFG_BLOCKLIST` set of 35+ tokens that are never valid manufacturer names: DISCONNECT, RESIST, PLANE, FLG, RLR, KIT, RED, BAR, H/W, CVR, ZNT, PWR, NPT, LLC, MAC, LIP, color codes, pipe thread standards, etc.
- `sanitize_mfg()` now checks blocklist with `if x in MFG_BLOCKLIST and x not in KNOWN_MANUFACTURERS` — real manufacturers are never blocked
- `DESCRIPTOR_KEYWORDS` extended with: DISCONNECT, BEARING, BUSHING, COUPLING, STARTER, ENCLOSURE

**Fix 3 — MFG Normalization Map Additions (22+ rows corrected)**
- Added normalization entries: ALN BRDLY → ALLEN BRADLEY, ALLEN-BRADLEY → ALLEN BRADLEY, A-B → ALLEN BRADLEY, PHOENIX CNTCT → PHOENIX CONTACT, PHNX CNTCT → PHOENIX CONTACT, FOLCIERI → BRUNO FOLCIERI, SEW EURODR → SEW EURODRIVE, SEW → SEW EURODRIVE, ROSSI → ROSSI MOTORIDUTTORI, MOLR → EATON, BACO → BACO CONTROLS
- Added to `KNOWN_MANUFACTURERS`: WEG, HKK, OLI, WAM, LAFERT, MORRIS, DODGE, MARTIN, WOODS, AMEC, LOVEJOY, GATES, BALEMASTER, PILZ, FESTO, ALLEN BRADLEY, SEW EURODRIVE, PHOENIX CONTACT, BRUNO FOLCIERI, ROSSI MOTORIDUTTORI, BACO CONTROLS

**Fix 4 — Descriptor-Pattern PN Rejection (23 rows fixed)**
- Added `PN_DESCRIPTOR_PATTERNS` regex: rejects `NUMBER-DESCRIPTOR` tokens like `3-WAY`, `4-BOLT`, `12-POINT`, `700-HOUR`, `2-DI/O`, `18-SPC` from being captured as part numbers
- Applied in both `extract_pn_structured()` and `extract_pn_heuristic()`
- Short pure-alpha tokens (≤3 chars like PKZ, MVE) rejected by heuristic but still captured when explicitly labeled (`PN: PKZ2-M4`)

**Fix 5 — McMaster Dash-Separated Catalog Format (8+ rows, pattern scales)**
- New `extract_pn_dash_catalog()` strategy: extracts PN from `CATALOG_NUMBER - Description` format
- Matches `6970T53 - Antislip Tape` → PN=`6970T53`, `2093A11 - Steel Feeler Gauge` → PN=`2093A11`
- Base confidence 0.80 — these are explicit catalog numbers, very reliable
- Registered in `pipeline_mfg_pn()` multi-strategy loop
- `STRATEGY_WEIGHTS` in `file_profiler.py` updated with `dash_catalog` weight (1.0 standard, 1.3 for CATALOG_ONLY archetype)

**Fix 6 — Graduated Heuristic Confidence (778 low-confidence items rescued)**
- `_score_heuristic_pn()` replaces flat `0.35` confidence for heuristic extractions
- Scoring range 0.10–0.65 based on token characteristics: letters+digits (+0.10), dash/slash (+0.10), length 6-20 (+0.05), long alphanumeric ≥10 chars (+0.10)
- Penalizes: very short ≤3 chars (−0.15), ISO/DIN/ANSI prefix (−0.10), starts-with-digit-short (−0.10)
- Result: `3AXD50000731121` scores ~0.60 (passes threshold), `100L` scores lower and is filtered

**Fix 7 — Cleaned `training_data.json` Known Manufacturers**
- Removed 18 false entries from `known_manufacturers`: AB, CTRL, DISCONNECT, DRAW IN SPD, ELECTRO, FIBRE OPTIC, GRN, INSERT MALE SCREW, MTG HSE, RESIST, TE, CABINET AB, GENERIC CONDUIT, GENERIC WIRE, HUBBEL, POLY-FLO, QIKLUG, BLINE, B-LINE, MC-MC, EISI, NORTH AM
- Added 18 real manufacturers: ALLEN BRADLEY, SEW EURODRIVE, PHOENIX CONTACT, BRUNO FOLCIERI, ROSSI MOTORIDUTTORI, BACO CONTROLS, OLI, WEG, HKK, WAM, LAFERT, MORRIS, DODGE, MARTIN, WOODS, AMEC, LOVEJOY, GATES, BALEMASTER, PILZ, FESTO (some already present)
- Removed 7 bad normalization entries that mapped to removed descriptors (DISCONNECT MODEL NUMBER, CTRL-ACC, FIBRE OPTIC PART NUMBER, etc.)

### Test Results Against WESCO.xlsx (2,684 rows)
- GE false positives: 201 → **0**
- Descriptor MFGs: 75+ → **0**
- Descriptor-pattern PNs: 23 → **0**
- McMaster dash rows with PN: 0/8 → **8/8**
- Data Set 1 regression: MFG **97.9%**, PN **97.0%** (both ≥ 95% target)

---

## [3.0.0] — 2026-02-17

### Added — Engine Hardening Architecture

**Layer 1 — File Format Profiler** (`engine/file_profiler.py`, new file)
- `profile_file()` samples up to 200 rows and classifies files into archetypes: `LABELED_RICH`, `COMPRESSED_SHORT`, `CATALOG_ONLY`, `MIXED`
- `FileProfile` dataclass stores signal percentages (labeled PN/MFG, comma-delimited, prefix-coded, pure catalog, free text), strategy weights, and confidence threshold recommendation
- `profile_file_cached()` caches results by MD5 hash of first 100 rows to avoid re-profiling the same file
- Strategy weights per archetype control which extraction strategies are boosted or suppressed (e.g. `COMPRESSED_SHORT` boosts prefix_decode 1.3x, suppresses heuristic to 0.4x)

**Layer 2 — Confidence Scoring**
- `CONFIDENCE_SCORES` dict assigns base confidence to each extraction source (label=0.95, known_mfg=0.85, prefix_decode=0.80/0.75, structured=0.70, catalog=0.60, supplier=0.55, heuristic=0.35)
- `ParseResult` dataclass extended with `mfg_confidence` and `pn_confidence` float fields
- `JobResult` extended with `file_profile`, `low_confidence_items`, and `confidence_stats` fields
- Items below confidence threshold are tracked in `low_confidence_items` rather than silently dropped

**Layer 3 — Multi-Strategy Extraction with Best-Pick**
- `ExtractionCandidate` dataclass holds (value, source, confidence) from each strategy
- `pick_best()` applies strategy weights from FileProfile and returns the highest-scoring candidate
- Individual strategy functions (return 3-tuples): `extract_pn_labeled`, `extract_pn_structured`, `extract_pn_heuristic`, `extract_mfg_labeled`, `extract_mfg_context`, `extract_mfg_known`
- All strategies run on every row; best result selected rather than stopping at first hit
- Backward-compatible wrappers `extract_pn_from_text` and `extract_mfg_from_text` preserved returning 2-tuples

**Layer 4 — Post-Extraction Validation** (`validate_and_clean()`)
- 7-rule validation pass clears bad values before output:
  1. PN is a spec value (voltage, current, RPM, dimensions) → clear PN
  2. MFG contains digits → clear MFG
  3. MFG is a known descriptor token → clear MFG
  4. MFG == PN → clear MFG
  5. MFG frequency anomaly (>60% of rows, not a real manufacturer) → clear
  6. PN is 1-2 chars → clear PN
  7. PN is a known manufacturer name (from training data + in-file MFG column) → clear PN
- Returns `(cleaned_df, corrections)` with detailed correction log per row
- Integrated into `pipeline_mfg_pn()` as post-processing step (controlled by `auto_validate=True`)

**Layer 5 — Training Pipeline Integration**
- `ingest_training_files()` now filters descriptor tokens from `known_manufacturers` before saving (removes TE, AB, CTRL, GRN and similar false positives)
- `learn_from_export()` function added for incremental learning from exported files
- `column_mapper.py`: added `supplier` single-value key to `map_columns()` result (first value from `source_supplier`)
- `column_mapper.py`: added new `source_description` aliases (Short Desc, Item Text, Line Text, Mat Text, Material Text)
- `training_data.json`: manually cleaned — removed `TE`, `AB`, `CTRL`, `GRN` from `known_manufacturers`

### Changed
- `pipeline_mfg_pn()` signature extended with `confidence_threshold`, `profile_override`, `auto_validate` parameters (all optional, fully backward-compatible)
- `pipeline_mfg_pn()` now runs file profiling, multi-strategy extraction, confidence gating, post-validation, and returns enriched `JobResult`

### Tests
- `tests/test_engine_hardening.py` — 7-test suite covering all 5 layers, plus regression gate (Data Set 1 must stay ≥ 95%)

---

## [2.2.0] — 2026-02-17

### Added
- **Short Text format support** — engine now handles compressed `Short Text` column files (e.g. SAP export with no `Material Description`/`PO Text` columns)
- **Spec value rejection filter** (Upgrade 1) — `extract_pn_from_text` now rejects electrical/mechanical spec tokens before they enter the PN candidate list. Rejects voltages (V), amperages (A), wattages (W/KW/KVA), speeds (RPM), phases (PH), horsepower (HP), and dimensions (IN/MM/CM/FT/MTR). Fixes false PNs like `120/277V`, `60A`, `2.02W`, `3PH`
- **Expanded descriptor blocklist** (Upgrade 2) — `DESCRIPTORS` set now includes short mechanical/electrical codes (`TE`, `NM`, `BLK`, `DIA`, `FR`, `MTR`, `DRV`, `BRG`, `SCR`, `VLV`, `FAN`, `PMP`, etc.) that previously slipped through as false manufacturer names
- **2-char MFG minimum length guard** (Upgrade 2) — `sanitize_mfg` now rejects tokens ≤2 characters unless they are a known manufacturer
- **Manufacturer prefix decoder** (Upgrade 3) — new `decode_mfg_prefix()` function decodes concatenated codes like `HUBCS120W` → MFG `HUBBELL`, PN `CS120W`. Prefix map covers HUB, SQD, SIE, CUT, PAN, APP, CRO, LEV, LIT, EAT, and more
- **Supplier name MFG fallback** (Upgrade 4) — `pipeline_mfg_pn` accepts optional `supplier_col` parameter; non-distributor suppliers are used as MFG fallback when text extraction fails. Distributor exclusion list expanded with McMaster-Carr, ULINE, Applied Industrial Technologies, Mayer Electric, and others
- **Short Text column mapper** — `column_mapper.py` now recognizes `Short Text` / `SHORT TEXT` as a valid `source_description` column
- **Supplier column role** — `column_mapper.py` adds `source_supplier` role; recognizes `Supplier Name1`, `Supplier Name`, `Vendor Name`, etc.
- **New test suite** `tests/test_v3_upgrades.py` — 88 unit + integration + regression tests covering all 4 upgrades

### Fixed
- `HUBCS120W`, `HUBGFR20W`, `HUBCR20WHI`, `HUBSHC1037CR` — now correctly extract MFG=HUBBELL
- `SCR,TE,14X265-ISO4017` — no longer extracts `TE` as manufacturer
- Voltage/amperage values like `120/277V`, `60A`, `480V` no longer appear as PN output
- McMaster-Carr rows correctly leave MFG blank (distributor, not manufacturer)

### Validated
- Regression: Data Set 1 MFG accuracy unchanged at 97.9% (184/188)
- Regression: Data Set 1 PN accuracy improved from 98.5% → 99.0% (198/200)
- WESCO.xlsx 2,684-row file: 50.1% MFG fill, 76.5% PN fill (vs 16% before)
- Zero spec values in PN column across full production file

---

## [2.0.4] — 2026-02-16

### Added
- PN length validation - flags part numbers >30 characters for human review
- MFG/PN duplicate detection - catches when MFG and PN are identical
- Comprehensive test suite with 6 validation phases (accuracy, QA, unit, scale, normalization, edge cases)
- Quick smoke tests for rapid development iteration
- Test convenience script (`./run_tests.sh`)
- Gamma presentation metrics documentation with validated numbers
- Complete testing guide for developers

### Improved
- Instruction parser confidence: "description column" now hits 100% (was 67%)
- Widened synonym matching for natural language variations
- Enhanced QA engine with `PN_too_long` and `MFG_equals_PN` rules
- Organized documentation structure (docs/ directory with README)

### Fixed
- Long concatenated part numbers now flagged for review instead of polluting output
- Instruction parser handles generic column references with full confidence

### Validated
- 89.4% MFG accuracy on 206 production rows
- 95.0% PN accuracy on 206 production rows
- 15,214 rows/second processing speed
- Zero critical QA violations

---

## [2.0.0] — 2026-02-16

### Changed
- **Complete rebrand** from prototype to Wesco International production tool
- Updated color scheme to Wesco corporate identity (#009639 primary green)
- Renamed all internal references: `CleanPlateParser` → `WescoMROParser`
- Database paths: `~/.clean_plate_parser/` → `~/.wesco_mro_parser/`
- Database file: `clean_plate_history.db` → `wesco_mro_history.db`
- Updated build scripts for `WescoMROParser.exe` output naming
- Window title: "Wesco MRO Parser"
- Sidebar logo: Bold "W" in Wesco green
- Version footer: "v2.0.0 • Wesco International • Global Accounts"

### Added
- **Professional repository structure:**
  - Comprehensive README with table of contents, badges, demo section
  - LICENSE file (proprietary - internal use)
  - SECURITY.md with vulnerability reporting process
  - CONTRIBUTING.md with team guidelines
  - GitHub issue templates (bug report, feature request, normalization request)
  - GitHub PR template
  - GitHub Actions workflow for quality checks
- App icon assets (Windows `.ico`, macOS `.icns`) with generation guide
- Specification documents in `docs/` directory:
  - `MFG_PN_Parsing_Agent_Spec.md`
  - `MRO_Part_Number_Processing_Spec.md`
  - `SIM_BOM_Automation_Spec.md`
- UI improvements:
  - Dashed border on import drop zone
  - Enhanced instruction placeholder text
  - Better visual feedback throughout

### Fixed
- Improved instruction interpretation feedback
- Better color contrast for accessibility

---

## [1.0.0] — 2026-02-16

### Added
- **Core Parsing Engine** with three deterministic pipelines:
  - MFG/PN Extraction from Material Descriptions and PO Text
  - Part Number Reprocessing with strict format validation
  - SIM Builder with three formatting patterns (A, B, C)
- **Desktop GUI** built with customtkinter:
  - Drag-and-drop Excel file import
  - Natural language instruction input
  - Live input/output preview table
  - One-click export with auto-generated QA report
- **Instruction Parser** — offline NL-to-pipeline mapper using keyword matching
  - Supports column letter references ("column A", "columns C and D")
  - Auto-detects pipeline type from file structure
  - Parses SIM pattern preferences from instructions
- **QA Engine** — automated flagging for:
  - Missing MFG/PN values
  - Distributors captured as manufacturers
  - MFG values containing digits
  - PN/MFG duplication
  - CROUSE HINDS and SQUARE D variant detection
- **Manufacturer Normalization Map** — 20+ common abbreviation corrections
- **Processing History** — SQLite-backed job log with full stats
- **Saved Configurations** — reusable instruction templates
- **Windows Build Script** — one-click PyInstaller `.exe` generation
- Three specification documents authored:
  - `MFG_PN_Parsing_Agent_Spec.md`
  - `MRO_Part_Number_Processing_Spec.md`
  - `SIM_BOM_Automation_Spec.md`
