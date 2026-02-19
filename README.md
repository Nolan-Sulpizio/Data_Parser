<div align="center">

# Wesco MRO Data Parser

**Intelligent Excel parsing for MRO data extraction — Built for the Global Accounts Team**

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS-blue.svg)]()
[![License](https://img.shields.io/badge/license-Proprietary-red.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-5.0.0-green.svg)](CHANGELOG.md)
[![Maintained](https://img.shields.io/badge/maintained-yes-brightgreen.svg)]()

[Features](#-features) •
[Quick Start](#-quick-start) •
[Usage](#-usage-guide) •
[Architecture](#-architecture) •
[Contributing](CONTRIBUTING.md) •
[Security](SECURITY.md)

</div>

---

## Overview

**Wesco MRO Parser** is a standalone desktop application that automates extraction of **Manufacturer (MFG)**, **Part Number (PN)**, and **SIM** values from unstructured MRO Excel data.

Built for Wesco International's Global Accounts Business Development Associates (BDAs), it replaces the manual, error-prone process of rebuilding AI chat sessions for every new file — delivering a three-step solution that works on any Windows or Mac machine.

### 100% Offline. No API Keys. No Internet Required.

All processing happens locally on your machine. No data leaves your computer.

---

## The Problem

Global Accounts BDAs receive large Excel files with thousands of messy, unstructured MRO line items. Extracting clean MFG, PN, and SIM values manually is:

- **Time-intensive** — Hours per file
- **Error-prone** — Abbreviations, distributors mistaken for manufacturers, spec values captured as part numbers
- **Repetitive** — Same logic rebuilt in Copilot for every new file

### Before This Tool
```
Import Excel → Build AI prompt → Parse columns → Fix errors → Export → Repeat
                   ↑______________________________________↑
                         (Every. Single. File.)
```

### With This Tool
```
Drop file → Confirm source column → Click PARSE FILE → Done
```

---

## Features

### Core Capabilities

| Feature | Description |
|---------|-------------|
| 📂 **Drag-and-drop import** | Load `.xlsx`, `.xls`, or `.csv` files directly |
| 🧠 **Smart column detection** | Automatically scores and selects the best source column(s) — no manual mapping |
| 👁️ **Live parse preview** | Shows parsed MFG/PN from 3–5 sample rows before committing to a full run |
| ⚙️ **Multi-strategy engine** | Labeled, prefix-decoded, context-inferred, known-MFG, and heuristic extraction — best result wins |
| ✅ **Automated QA report** | Flags missing data, distributor-as-MFG, digit anomalies, naming inconsistencies |
| 📤 **Auto-export** | Saves `_parsed.xlsx` and `_QA.csv` to the source file's directory — no export button needed |
| 📦 **Team-distributable** | Single `.exe` or `.app` — no Python required |

### Technical Highlights

- Modern dark theme with Wesco corporate branding (#009639 green)
- **5-layer extraction engine:** File profiling → confidence scoring → multi-strategy extraction → post-validation → QA
- **File format detection:** Classifies files as `LABELED_RICH`, `COMPRESSED_SHORT`, `CATALOG_ONLY`, or `MIXED` — adjusts strategy weights accordingly
- **Distributor filtering** — GRAYBAR, CED, REXEL, McMaster-Carr, and 30+ others excluded as MFG
- **MFG normalization** — handles SAP truncations (e.g., `SEW EURODR` → `SEW EURODRIVE`) and abbreviations
- **Zero spec leaks** — voltage, amperage, RPM, dimensions never appear as part numbers
- **Zero plant code leaks** — SAP plant codes (e.g., `N141`, `N041`) never appear as part numbers
- ⚡ Fast — handles 10,000+ row files efficiently
- 🔐 100% offline — no internet, no APIs, no telemetry

### Production Benchmarks (2,684-row WESCO file)

| Metric | Result |
|--------|--------|
| MFG fill rate | **60.5%** (1,624 / 2,684) |
| PN fill rate | **59.3%** (1,592 / 2,684) |
| AB / TE / GE hallucinations | **0** |
| Spec/plant code leaks | **0** |
| Distributor-as-MFG | **0** |

---

## Demo

### The Interface (v5.0 — Three-Step Flow)

```
┌──────────────────────────────────────────────────────────┐
│  [W] WESCO   MRO Data Parser                      v5.0  │
│──────────────────────────────────────────────────────────│
│                                                          │
│  ┌──────────────────────────────────────────────────┐    │
│  │                                                  │    │
│  │        📁  Drop Excel file here                  │    │
│  │            or click to browse                    │    │
│  │                                                  │    │
│  │        .xlsx    .xls    .csv                     │    │
│  └──────────────────────────────────────────────────┘    │
│                                                          │
│  ✓ WESCO_Empty.xlsx  ·  2,684 rows  ·  9 columns        │
│                                                          │
│  SOURCE DATA  (columns scored for MFG/PN content)        │
│  ┌──────────────────────────────────────────────────┐    │
│  │  ✅ E: Short Text            ← auto-selected     │    │
│  │  ☐  A: Supplier Name1                            │    │
│  └──────────────────────────────────────────────────┘    │
│  Supplier hint auto-detected: Supplier Name1             │
│                                                          │
│  PARSE PREVIEW                                           │
│  ┌──────────────────────────────────────────────────┐    │
│  │  Row 1:  "S-17080 - ANTIBACTERIAL HAND SOAP"    │    │
│  │          → MFG: ULINE   PN: S-17080              │    │
│  │  Row 4:  "PWR SPLY UNIT,SIEMENS,PN:6EP1434..."  │    │
│  │          → MFG: SIEMENS  PN: 6EP1434-2BA20       │    │
│  │  Row 5:  "CKT BRKR,EATON,19YG89"                │    │
│  │          → MFG: EATON    PN: 19YG89              │    │
│  └──────────────────────────────────────────────────┘    │
│                                                          │
│  ┌──────────────────────────────────────────────────┐    │
│  │                                                  │    │
│  │              ▶  PARSE FILE                       │    │
│  │                                                  │    │
│  └──────────────────────────────────────────────────┘    │
│                                                          │
│  ── after parse completes ──                             │
│                                                          │
│  ✅ COMPLETE                                             │
│  2,684 rows processed                                    │
│  MFG filled: 1,624 (60.5%)                               │
│  PN filled:  1,592 (59.3%)                               │
│                                                          │
│  📄 Saved: WESCO_Empty_parsed.xlsx                       │
│  📊 QA:    WESCO_Empty_QA.csv                            │
│                                                          │
│  [Open File Location]      [Parse Another File]          │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### What the Engine Does to Raw Data

**Input (Short Text column):**
```
PANDT CABLE TIE 8IN BLACK
PWR SPLY UNIT,SIEMENS,6EP1434-28A20,INPUT 85-264VAC
CKT BRKR,MINTR,40A,48/96VDC,EATON,19YG89
SEW EURODR GEAR MOTOR 3AXD50000731121
```

**Output (MFG + PN appended):**
```
MFG            PN
──────────────────────────────────────
PANDUIT        (no PN in source)
SIEMENS        6EP1434-28A20
EATON          19YG89
SEW EURODRIVE  3AXD50000731121
```

---

## ⚡ Quick Start

### Option 1: Run the App (Team Members)

1. **Download** `WescoMROParser.exe` (Windows) or `WescoMROParser.app` (Mac) from the latest release
2. **Double-click** to launch — no installation needed
3. **Drop your Excel file** and follow the three steps

### Option 2: Run from Source (Developers)

```bash
# Clone the repository
git clone https://github.com/Nolan-Sulpizio/Data_Parser.git
cd Data_Parser

# Install dependencies
pip install -r requirements.txt

# Launch
python app.py
```

### Option 3: Build the App Yourself

```bash
# macOS
./build_mac.sh
# → WescoMROParser.app

# Windows
build_windows.bat
# → dist/WescoMROParser.exe
```

---

## Usage Guide

### Step 1: Drop Your File

Drag an Excel file onto the import zone (or click to browse).

**Supported formats:** `.xlsx`, `.xls`, `.csv`

The app immediately scans the file and shows:
```
✓ Loaded: MRO_Data_Q1_2026.xlsx
  1,247 rows  •  12 columns
```

Any inline warnings appear here (unnamed columns, large empty ranges, etc.).

### Step 2: Confirm Source Columns

The engine scores every column 0–100 based on name signals and content patterns, then shows only the columns worth considering:

- **Score ≥ 40** — auto-checked
- **Score 10–39** — shown unchecked (user can enable)
- **Score < 10** — hidden (Plant, Date, Qty columns, etc.)

The supplier column (e.g., `Supplier Name1`) is auto-detected and shown as a hint — no configuration needed.

A **live parse preview** shows 3–5 representative rows so you can visually confirm the engine is reading the right column before running the full file.

### Step 3: Parse

Click **▶ PARSE FILE**. The progress bar tracks row processing.

When complete, the results appear automatically:
```
✅ COMPLETE
1,247 rows processed
MFG filled: 1,198 (96%)
PN filled:  1,156 (93%)

📄 Saved: MRO_Data_Q1_2026_parsed.xlsx
📊 QA:    MRO_Data_Q1_2026_QA.csv
```

Both files are saved to the same directory as your source file. Click **Open File Location** to go there directly, or **Parse Another File** to start over.

---

## 🏗️ Architecture

### High-Level Design

```
┌────────────────────────────────────────────────────────────┐
│                    Wesco MRO Parser                        │
│                                                            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                   GUI Layer (app.py)                │   │
│  │  Drop Zone → Column Selector → Preview → Parse Btn │   │
│  │                  → Results + Auto-Export            │   │
│  └─────────────────────────┬───────────────────────────┘   │
│                            │                               │
│  ┌─────────────────────────▼───────────────────────────┐   │
│  │                  Engine Layer (engine/)              │   │
│  │                                                     │   │
│  │  column_mapper.py                                   │   │
│  │  ├── score_column_for_parsing()  ← auto-detection   │   │
│  │  ├── detect_supplier_column()    ← auto-detection   │   │
│  │  └── suggest_columns()                              │   │
│  │                                                     │   │
│  │  file_profiler.py                                   │   │
│  │  └── profile_file()  → LABELED_RICH | MIXED | ...  │   │
│  │                                                     │   │
│  │  schema_classifier.py                               │   │
│  │  └── classify()  → SAP_SHORT_TEXT | GENERIC | ...  │   │
│  │                                                     │   │
│  │  parser_core.py                                     │   │
│  │  ├── pipeline_mfg_pn()   ← primary pipeline        │   │
│  │  ├── parse_single_row()  ← preview helper          │   │
│  │  └── run_qa()                                      │   │
│  │                                                     │   │
│  │  instruction_parser.py  (secondary / advanced)     │   │
│  │  history_db.py           (SQLite job log)          │   │
│  │  training.py             (training ingestion)      │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                            │
│  training_data.json    ← mfg_normalization + known MFGs   │
└────────────────────────────────────────────────────────────┘
```

### File Structure

```
mro-parser/
├── app.py                          # Main GUI — v5.0 single-panel interface
├── engine/
│   ├── __init__.py                 # Package init + version
│   ├── parser_core.py              # MFG/PN pipelines, confidence scoring, QA
│   ├── column_mapper.py            # Column scoring, supplier detection, mapping
│   ├── file_profiler.py            # File archetype detection + strategy weights
│   ├── schema_classifier.py        # Schema detection (SAP_SHORT_TEXT, GENERIC, etc.)
│   ├── instruction_parser.py       # NL instruction → pipeline config (advanced)
│   ├── history_db.py               # SQLite job history
│   └── training.py                 # Training data ingestion
├── training_data.json              # mfg_normalization map + known_manufacturers list
├── docs/
│   ├── MFG_PN_Parsing_Agent_Spec.md
│   ├── MRO_Part_Number_Processing_Spec.md
│   ├── SIM_BOM_Automation_Spec.md
│   ├── TESTING_GUIDE.md
│   └── GAMMA_PRESENTATION_METRICS.md
├── tests/                          # Test suites (31 hardening + 4 smoke tests)
├── assets/
│   ├── icon.ico                    # Windows icon
│   └── icon.icns                   # macOS icon
├── .github/
│   ├── ISSUE_TEMPLATE/
│   └── pull_request_template.md
├── build_mac.sh                    # One-click macOS app builder
├── build_windows.bat               # One-click Windows exe builder
├── run_tests.sh                    # Test runner
├── requirements.txt
├── CHANGELOG.md
├── CONTRIBUTING.md
├── SECURITY.md
└── README.md
```

### Technology Stack

| Layer | Technology |
|-------|------------|
| **GUI Framework** | `customtkinter` — Modern themed Tkinter |
| **Data Engine** | `pandas` — DataFrame manipulation |
| **Excel I/O** | `openpyxl` — Read/write .xlsx files |
| **Database** | SQLite3 — Local job history |
| **Packaging** | PyInstaller — Standalone app generation |

---

## 🔍 QA Engine

Every parse run automatically flags potential issues:

| Flag | Description | Example |
|------|-------------|---------|
| `MFG_missing` | MFG cell is empty after processing | — |
| `PN_missing` | PN cell is empty after processing | — |
| `PN_NOT_IN_SOURCE` | Extracted PN not found in source text — potential hallucination | audit manually |
| `MFG_is_distributor` | MFG contains a known distributor name | `GRAYBAR`, `CED`, `REXEL` |
| `MFG_has_digits` | MFG contains numerics (likely a PN or code) | `PAND123` |
| `PN_same_as_MFG` | PN and MFG are identical (extraction error) | both = `PANDUIT` |
| `CROUSE_variant` | CROUSE HINDS hyphenation inconsistency | `CROUSE HIND` vs `CROUSE HINDS` |
| `SQUARED_variant` | SQUARE D formatting inconsistency | `SQ D` vs `SQUARE D` |

Flagged rows are exported to a separate `*_QA.csv` file for team review.

---

## 📚 Manufacturer Normalization

The engine handles common SAP short-text truncations and field abbreviations automatically:

| Raw Value | Normalized To |
|-----------|---------------|
| `PANDT` | `PANDUIT` |
| `SEW EURODR` / `SEW EURO` | `SEW EURODRIVE` |
| `BRU FOLC` | `BRUNO FOLCIERI` |
| `CUTLR-HMR` / `CUTLER HMR` | `CUTLER-HAMMER` |
| `CROUS HIND` | `CROUSE HINDS` |
| `FXBRO` / `FXBRO INVN` | `FOXBORO` |
| `T&BETTS` | `THOMAS & BETTS` |
| `TOPWRX` | `TOPWORX` |
| `SOUTHWRE` | `SOUTHWIRE` |
| `ALN BRDLY` / `A-B` | `ALLEN BRADLEY` |
| `PHOENIX CNTCT` / `PHNX CNTCT` | `PHOENIX CONTACT` |

**Full map:** `engine/parser_core.py` → `NORMALIZE_MFG` + `training_data.json` → `mfg_normalization`

**Training data validation rule:** No key in `mfg_normalization` may match an entry in the `DISTRIBUTORS` set. This prevents distributor names from being ingested as manufacturer abbreviations.

---

## 🗺️ Roadmap

- [x] **v1.0** — Core parsing engine with MFG/PN/SIM pipelines + desktop GUI
- [x] **v2.0** — Wesco branding, production repository structure
- [x] **v2.2** — Short Text format support, spec value rejection, prefix decoder, supplier fallback
- [x] **v3.0** — Engine hardening: file profiler, confidence scoring, multi-strategy extraction, post-validation
- [x] **v3.1** — Precision refinement: word-boundary MFG matching, descriptor blocklist, McMaster dash format, graduated heuristic confidence
- [x] **v3.6** — Embedded code extraction (ABB drive PNs), plant code rejection, SEW/ULINE fixes
- [x] **v4.0** — Training data patch: removed contaminated entries, added distributor validation gate
- [x] **v5.0** — UI redesign: single-panel three-step flow, smart auto-detection, live preview, auto-export
- [ ] **v5.1** — Batch processing (multiple files at once)
- [ ] **v5.2** — Custom normalization map editor in UI
- [ ] **v5.3** — Network drive sync for team-wide training data

**Have a feature idea?** Open a [Feature Request](https://github.com/Nolan-Sulpizio/Data_Parser/issues/new?template=feature_request.md)

---

## 🤝 Contributing

Contributions are welcome from Wesco team members. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

- [Report a Bug](https://github.com/Nolan-Sulpizio/Data_Parser/issues/new?template=bug_report.md)
- [Request a Feature](https://github.com/Nolan-Sulpizio/Data_Parser/issues/new?template=feature_request.md)
- [Request a Normalization](https://github.com/Nolan-Sulpizio/Data_Parser/issues/new?template=normalization_request.md)
- [Security Policy](SECURITY.md)

---

## 📄 License

**Proprietary** — Internal use only.

Copyright (c) 2026 Wesco International, Inc.

This software is developed for internal use by Wesco International employees and authorized contractors. See [LICENSE](LICENSE) for full terms.

---

## 📧 Contact

**Maintainer:** Nolan Sulpizio
**Team:** Global Accounts — Business Development Associates
**Company:** Wesco International

- Microsoft Teams: @Nolan Sulpizio
- GitHub Issues: [Create an issue](https://github.com/Nolan-Sulpizio/Data_Parser/issues)

---

## Acknowledgments

Built with:
- [customtkinter](https://github.com/TomSchimansky/CustomTkinter) by Tom Schimansky
- [pandas](https://pandas.pydata.org/) by the pandas development team
- [openpyxl](https://openpyxl.readthedocs.io/) by the openpyxl team

Parsing logic derived from specifications authored by the Global Accounts team and refined through iterative testing with real MRO data.

---

<div align="center">

Built for the Wesco Global Accounts Team

</div>
