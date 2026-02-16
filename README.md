<div align="center">

# 🔧 Wesco MRO Data Parser

**Intelligent Excel parsing for MRO data extraction — Built for the Global Accounts Team**

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-Windows-blue.svg)]()
[![License](https://img.shields.io/badge/license-Proprietary-red.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-2.0.0-green.svg)](CHANGELOG.md)
[![Maintained](https://img.shields.io/badge/maintained-yes-brightgreen.svg)]()

[Features](#-features) •
[Quick Start](#-quick-start) •
[Usage](#-usage) •
[Architecture](#-architecture) •
[Contributing](CONTRIBUTING.md) •
[Security](SECURITY.md)

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [The Problem](#-the-problem)
- [The Solution](#-the-solution)
- [Features](#-features)
- [Demo](#-demo)
- [Quick Start](#-quick-start)
- [Usage Guide](#-usage-guide)
- [Processing Pipelines](#-processing-pipelines)
- [Architecture](#-architecture)
- [QA Engine](#-qa-engine)
- [Manufacturer Normalization](#-manufacturer-normalization)
- [Roadmap](#-roadmap)
- [Contributing](#-contributing)
- [License](#-license)

---

## 📖 Overview

**Wesco MRO Parser** is a standalone desktop application that automates the extraction of **Manufacturer (MFG)**, **Part Number (PN)**, and **SIM** values from unstructured MRO Excel data.

Built specifically for Wesco International's Global Accounts Business Development Associates (BDAs), this tool eliminates the manual, repetitive process of rebuilding AI chat sessions for every new file — giving the team a one-click solution they can run on any Windows machine.

### 🔒 **100% Offline. No API Keys. No Internet Required.**

All processing happens locally on your machine. No data leaves your computer.

---

## 🎯 The Problem

Global Accounts BDAs receive large Excel files containing thousands of line items with messy, unstructured product descriptions. Extracting clean MFG, PN, and SIM values manually is:

- ⏱️ **Time-intensive** — Hours per file
- ⚠️ **Error-prone** — Inconsistent formatting, abbreviations, distributors mistaken for manufacturers
- 🔄 **Repetitive** — Same logic rebuilt in Copilot for every new file
- 😤 **Frustrating** — Context gets lost, accuracy degrades with large files

### Before This Tool
```
Import Excel → Build Copilot prompt → Parse columns → Fix errors → Export → Repeat for next file
                    ↑______________________↑
               (This happens EVERY time)
```

### With This Tool
```
Import Excel → Click template → Export clean data
                    ↑
              (One click, every time)
```

---

## ✨ The Solution

This tool encapsulates proven parsing logic into a distributable desktop app with a modern GUI. Team members:

1. **Import** an Excel file (drag-and-drop or browse)
2. **Describe** what they need in plain English (or pick a pre-built template)
3. **Export** a cleaned workbook with auto-generated QA report

**Result:** Minutes instead of hours. Consistent quality. Reusable configurations.

---

## 🚀 Features

### Core Capabilities

| Feature | Description |
|---------|-------------|
| 📂 **Drag-and-drop import** | Load `.xlsx`, `.xls`, or `.csv` files directly into the app |
| 💬 **Natural language instructions** | Type what you need: *"Pull MFG and PN from Material Description into columns A and B"* |
| ⚙️ **3 built-in pipelines** | MFG/PN Extraction • Part Number Reprocessing • SIM Builder |
| 👁️ **Live preview** | Compare input vs. output side-by-side before exporting |
| ✅ **Automated QA report** | Flags missing data, distributor-as-MFG errors, digit issues, naming inconsistencies |
| 📊 **Processing history** | Every job logged locally with full stats (rows processed, fields filled, issues found) |
| 💾 **Saved configurations** | Save and reuse instruction templates across sessions |
| 📦 **Team-distributable** | Single `.exe` file — recipients don't need Python installed |

### Technical Highlights

- 🎨 Modern dark theme with Wesco corporate branding (#009639 green)
- 🗃️ Local SQLite database for history and saved configs
- 🔍 Smart column detection and pattern matching
- 📋 Manufacturer abbreviation normalization (20+ common abbreviations)
- 🚫 Distributor filtering (GRAYBAR, CED, REXEL, etc.)
- ⚡ Fast processing — handles 10,000+ row files efficiently
- 🔐 100% offline — no internet, no APIs, no telemetry

---

## 🎬 Demo

### Main Interface
The app provides a clean, intuitive interface with three main sections:

```
┌─────────────────────────────────────────────────────────────┐
│  [SIDEBAR]          │  [MAIN WORKSPACE]                     │
│                     │                                        │
│  ◉ WESCO           │  ┌──────────────────────────────────┐  │
│  MRO Data Parser   │  │  📂 Drop Excel file here         │  │
│                     │  └──────────────────────────────────┘  │
│  ⬡ Parser          │                                        │
│  ◷ History         │  ┌──────────────────────────────────┐  │
│  ⚙ Saved Configs   │  │  What do you need?               │  │
│                     │  │  "Extract MFG and PN from..."    │  │
│  QUICK TEMPLATES    │  └──────────────────────────────────┘  │
│  • MFG + PN Extract │                                        │
│  • Part Number Clean│  [▶ Run Parser]  [💾 Export]          │
│  • Build SIM Values │                                        │
│                     │  ┌──────────────────────────────────┐  │
│  v2.0.0 • Wesco    │  │  Preview: [Input] [Output]       │  │
│                     │  │  ┌────┬──────┬──────┬──────┐     │  │
│                     │  │  │Row │ MFG  │  PN  │ SIM  │     │  │
│                     │  │  ├────┼──────┼──────┼──────┤     │  │
│                     │  │  │ 1  │PAND..│ ...  │ ...  │     │  │
│                     │  │  └────┴──────┴──────┴──────┘     │  │
└─────────────────────────────────────────────────────────────┘
```

### Workflow Example

**Step 1:** Import a file
```
Material Description               | PO Text
──────────────────────────────────────────────────────
PANDT CABLE TIE 8IN BLACK         | CT-8-BLACK-100
CROUSE HIND EXPPROOF BOX 3/4      | EXB-075-1G
FXBRO TEMP SENSOR 0-200F          | TS-200F-4-20MA
```

**Step 2:** Pick template or type instruction
```
Template: "Extract MFG and PN from Material Description and PO Text"
⚡ Interpreted as: mfg_pn pipeline → columns A and B
```

**Step 3:** Review output
```
MFG           | PN              | SIM
────────────────────────────────────────────
PANDUIT       | CT-8-BLACK-100  | PANDUIT-CT-8-BLACK-100
CROUSE HINDS  | EXB-075-1G      | CROUSE HINDS-EXB-075-1G
FOXBORO       | TS-200F-4-20MA  | FOXBORO-TS-200F-4-20MA
```

**QA Report:**
```
✓ 3 rows processed
✓ 3 MFG filled
✓ 3 PN filled
✓ 0 issues detected
```

---

## ⚡ Quick Start

### Option 1: Run the .exe (Recommended for Team Members)

1. **Download** `WescoMROParser.exe` from the latest release
2. **Double-click** to launch (no installation needed)
3. **Import** your Excel file and start parsing

### Option 2: Run from Source (For Developers)

```bash
# 1. Clone the repository
git clone https://github.com/Nolan-Sulpizio/Data_Parser.git
cd Data_Parser

# 2. Install Python 3.10+ (if not already installed)
# Download from: https://www.python.org/downloads/

# 3. Install dependencies
pip install -r requirements.txt

# 4. Launch the application
python app.py
```

### Option 3: Build the .exe Yourself

```bash
# On a Windows machine:
build_windows.bat

# Output: dist/WescoMROParser.exe
```

Share the resulting `.exe` with your team — **no Python installation required** on their machines.

---

## 📘 Usage Guide

### Step 1: Import Your Data

Launch the app and **drag an Excel file** onto the import zone (or click to browse).

**Supported formats:** `.xlsx`, `.xls`, `.csv`

The app shows a preview of your data with row/column counts:
```
✓ Loaded: MRO_Data_Q1_2026.xlsx
  1,247 rows  •  12 columns  •  Cols: Material Description, PO Text, Notes, ...
```

### Step 2: Provide Instructions

Either **type a natural language instruction** or **pick a Quick Template** from the sidebar:

#### Quick Templates

| Template | What It Does |
|----------|-------------|
| **MFG + PN Extract** | Extract MFG and PN from Material Description and PO Text into separate columns |
| **Part Number Clean** | Clean and validate Part Number 1 from description fields (strict format rules) |
| **Build SIM Values** | Generate SIM from existing MFG and ITEM # for rows with missing SIM |

#### Example Instructions

```
"Pull MFG and PN from Material Description into columns A and B"
"Extract manufacturer and part number, include SIM"
"Build SIM from MFG and ITEM # using pattern C"
"Clean Part Number 1 from description fields"
```

The app will interpret your instruction and show feedback:
```
⚡ Interpreted as: mfg_pn pipeline → MFG to column A, PN to column B, add SIM
```

### Step 3: Run the Parser

Click **▶ Run Parser**. The progress bar tracks the operation:

```
Processing... ████████████████████████░░░░ 80%
```

When complete, the preview switches to the **Output** view showing your cleaned data.

### Step 4: Review & Export

Review the results:
- Toggle between **Input** and **Output** views
- Check the stats: `Rows: 1247  •  MFG filled: 1198  •  PN filled: 1156  •  ⚠ 23 issues`
- Review flagged rows in the preview table

Click **💾 Export** to save:
- `MRO_Data_Q1_2026 - parsed.xlsx` — Cleaned workbook
- `MRO_Data_Q1_2026 - QA Issues.xlsx` — Flagged rows (if any issues detected)

### Step 5: Save Configuration (Optional)

If you'll use the same instruction again, click **⚙ Save Config**:
```
Configuration name: "Standard MFG/PN Extract"
```

Next time, just load the config instead of retyping the instruction.

---

## 🔧 Processing Pipelines

The parser includes three specialized pipelines, each designed for a specific MRO data extraction task:

### Pipeline 1: MFG + PN Extraction

**Purpose:** Extract Manufacturer and Part Number from unstructured product descriptions

**Source Spec:** [`docs/MFG_PN_Parsing_Agent_Spec.md`](docs/MFG_PN_Parsing_Agent_Spec.md)

**How it works:**
1. Reads from columns like `Material Description`, `PO Text`, `Material PO Text`
2. Uses labeled pattern matching (e.g., `MFG: PANDUIT PN: CT-8-BLACK`)
3. Falls back to heuristic extraction (position-based, format-based)
4. Normalizes common abbreviations (`PANDT` → `PANDUIT`, `FXBRO` → `FOXBORO`)
5. Filters out distributor names and descriptor tokens
6. Optionally generates SIM (`MFG-PN`)

**Input columns:** `Material Description`, `Material PO Text`, `PO Text`
**Output columns:** `MFG`, `PN`, `SIM` (optional)

---

### Pipeline 2: Part Number Reprocessing

**Purpose:** Strictly clean and validate existing Part Number columns

**Source Spec:** [`docs/MRO_Part_Number_Processing_Spec.md`](docs/MRO_Part_Number_Processing_Spec.md)

**How it works:**
1. Reads from `Part Number 1`, `Description`, `Notes`, `INFORECTXT1/2`
2. Rejects bare specs like `500W`, `12V`, `3/4"`
3. Enforces structured format (must contain letters AND digits)
4. Excludes internal/legacy prefixes
5. Prefers tokens with dashes or slashes (`ABC-123` over `ABC 123`)
6. Cross-validates against MFG column

**Input columns:** Description fields, `Notes`, `INFORECTXT1/2`
**Output column:** `Part Number 1` (cleaned + validated)

---

### Pipeline 3: SIM Builder

**Purpose:** Generate SIM values for rows where SIM is missing

**Source Spec:** [`docs/SIM_BOM_Automation_Spec.md`](docs/SIM_BOM_Automation_Spec.md)

**How it works:**
1. Reads existing `MFG` and `ITEM #` columns
2. Only processes rows where `SIM` is blank
3. Concatenates using one of three patterns:

| Pattern | Format | Example |
|---------|--------|---------|
| **A** | `MFG-ITEM #` (keeps punctuation) | `PIP-50-N150G/L` |
| **B** | `MFGITEM` (compact, no hyphen) | `PIP50-N150G/L` |
| **C** | `MFG-ALNUM` (sanitized alphanumeric only) | `PIP-50N150GL` |

**Input columns:** `MFG`, `ITEM #`
**Output column:** `SIM`

---

## 🏗️ Architecture

### High-Level Design

```
┌──────────────────────────────────────────────────────────────────────┐
│                        Wesco MRO Parser                              │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │                     GUI Layer (app.py)                          │ │
│  │  ┌──────────┐  ┌───────────────┐  ┌──────────┐  ┌───────────┐ │ │
│  │  │  Import   │  │  Instruction  │  │  Preview │  │  Export   │ │ │
│  │  │   Zone    │  │    Input      │  │   Table  │  │  Manager  │ │ │
│  │  └─────┬────┘  └──────┬────────┘  └─────┬────┘  └─────┬─────┘ │ │
│  └────────┼──────────────┼──────────────────┼─────────────┼───────┘ │
│           │              │                  │             │          │
│  ┌────────▼──────────────▼──────────────────▼─────────────▼───────┐ │
│  │                    Engine Layer (engine/)                       │ │
│  │                                                                │ │
│  │  ┌────────────────────┐   ┌──────────────────────────────────┐ │ │
│  │  │ instruction_parser │   │         parser_core              │ │ │
│  │  │                    │   │                                  │ │ │
│  │  │ NL text ──────────►│   │  ┌────────────┐ ┌────────────┐  │ │ │
│  │  │  ──► Pipeline      │──►│  │  MFG / PN  │ │ Part Number│  │ │ │
│  │  │  ──► Source cols   │   │  │  Extraction │ │  Cleaning  │  │ │ │
│  │  │  ──► Target cols   │   │  └────────────┘ └────────────┘  │ │ │
│  │  │  ──► SIM pattern   │   │  ┌────────────┐ ┌────────────┐  │ │ │
│  │  └────────────────────┘   │  │    SIM     │ │  QA Engine │  │ │ │
│  │                           │  │   Builder  │ │            │  │ │ │
│  │                           │  └────────────┘ └────────────┘  │ │ │
│  │                           └──────────────────────────────────┘ │ │
│  │                                                                │ │
│  │  ┌────────────────────┐                                        │ │
│  │  │    history_db      │  SQLite: jobs, saved configs           │ │
│  │  └────────────────────┘                                        │ │
│  └────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
```

### File Structure

```
Data_Parser/
├── app.py                          # Main GUI application (customtkinter)
├── engine/
│   ├── __init__.py                 # Package init + version (v2.0.0)
│   ├── parser_core.py              # Core parsing logic & pipelines
│   ├── instruction_parser.py       # NL instruction → pipeline config
│   └── history_db.py               # Local SQLite for history + configs
├── docs/
│   ├── MFG_PN_Parsing_Agent_Spec.md           # Pipeline 1 specification
│   ├── MRO_Part_Number_Processing_Spec.md     # Pipeline 2 specification
│   └── SIM_BOM_Automation_Spec.md             # Pipeline 3 specification
├── assets/
│   ├── icon.ico                    # Windows app icon
│   └── README.md                   # Icon generation guide
├── .github/
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.md
│   │   ├── feature_request.md
│   │   └── normalization_request.md
│   ├── workflows/
│   │   └── quality-checks.yml      # GitHub Actions CI
│   └── pull_request_template.md
├── build_windows.bat               # One-click Windows .exe builder
├── requirements.txt                # Python dependencies
├── .gitignore                      # Git exclusions
├── LICENSE                         # Proprietary license (Wesco internal)
├── CHANGELOG.md                    # Version history
├── CONTRIBUTING.md                 # Contribution guidelines
├── SECURITY.md                     # Security policy
├── CLAUDE.md                       # Claude Code dev instructions
└── README.md                       # ← You are here
```

### Technology Stack

| Layer | Technology |
|-------|------------|
| **GUI Framework** | `customtkinter` — Modern themed Tkinter |
| **Data Engine** | `pandas` — DataFrame manipulation |
| **Excel I/O** | `openpyxl` — Read/write .xlsx files |
| **Database** | SQLite3 — Local job history & configs |
| **Packaging** | PyInstaller — Standalone .exe generation |

---

## 🔍 QA Engine

Every processing run automatically flags potential issues in the output:

| Flag | Description | Example |
|------|-------------|---------|
| `MFG_missing` | MFG cell is empty after processing | `""` |
| `PN_missing` | PN cell is empty after processing | `""` |
| `MFG_is_distributor` | MFG contains a distributor name | `GRAYBAR`, `CED`, `REXEL` |
| `MFG_has_digits` | MFG contains numeric characters (likely a PN or code) | `PAND123`, `FOXBORO-200` |
| `PN_same_as_MFG` | PN and MFG are identical (extraction error) | MFG: `PANDUIT`, PN: `PANDUIT` |
| `CROUSE_variant` | CROUSE HINDS hyphenation inconsistency | `CROUSE HIND` vs `CROUSE HINDS` |
| `SQUARED_variant` | SQUARE D formatting inconsistency | `SQ D` vs `SQUARE D` |

Flagged rows are exported to a separate `*- QA Issues.xlsx` workbook for team review.

---

## 📚 Manufacturer Normalization

The parser includes a built-in normalization map that standardizes common MFG abbreviations found in Wesco MRO data:

| Raw Value | Normalized To |
|-----------|---------------|
| `PANDT` | `PANDUIT` |
| `CUTLR-HMR` | `CUTLER-HAMMER` |
| `CROUS HIND` | `CROUSE HINDS` |
| `FXBRO` / `FXBRO INVN` | `FOXBORO` |
| `T&BETTS` | `THOMAS & BETTS` |
| `TOPWRX` | `TOPWORX` |
| `SOUTHWRE` | `SOUTHWIRE` |
| `SQ D` | `SQUARE D` |
| `CUTLER HMR` | `CUTLER-HAMMER` |

**Full map:** See [`engine/parser_core.py`](engine/parser_core.py) → `NORMALIZE_MFG` dictionary

**To request a new normalization:** Open a [Normalization Request](https://github.com/Nolan-Sulpizio/Data_Parser/issues/new?template=normalization_request.md)

---

## 🗺️ Roadmap

- [x] **v1.0** — Core parsing engine with 3 pipelines
- [x] **v1.0** — Desktop GUI with import, preview, export
- [x] **v1.0** — Processing history and saved configurations
- [x] **v2.0** — Wesco branding and production-ready UI
- [ ] **v2.1** — Batch processing (multiple files at once)
- [ ] **v2.2** — Config export/import for team sharing (JSON format)
- [ ] **v2.3** — Dark/Light theme toggle
- [ ] **v3.0** — Custom normalization map editor in UI
- [ ] **v3.1** — Network drive config sync for team-wide templates
- [ ] **v3.2** — Excel macro integration (call parser from Excel VBA)

**Have a feature idea?** Open a [Feature Request](https://github.com/Nolan-Sulpizio/Data_Parser/issues/new?template=feature_request.md)

---

## 🤝 Contributing

Contributions are welcome from Wesco team members! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Quick Links

- [Report a Bug](https://github.com/Nolan-Sulpizio/Data_Parser/issues/new?template=bug_report.md)
- [Request a Feature](https://github.com/Nolan-Sulpizio/Data_Parser/issues/new?template=feature_request.md)
- [Request a Normalization](https://github.com/Nolan-Sulpizio/Data_Parser/issues/new?template=normalization_request.md)
- [View Roadmap](#-roadmap)
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

For questions, support, or feedback:
- Microsoft Teams: @Nolan Sulpizio
- Slack: Global Accounts channel
- GitHub Issues: [Create an issue](https://github.com/Nolan-Sulpizio/Data_Parser/issues)

---

## 🙏 Acknowledgments

Built with:
- [customtkinter](https://github.com/TomSchimansky/CustomTkinter) by Tom Schimansky
- [pandas](https://pandas.pydata.org/) by the pandas development team
- [openpyxl](https://openpyxl.readthedocs.io/) by the openpyxl team

Parsing logic derived from specifications authored by the Global Accounts team and refined through iterative testing with real MRO data.

---

<div align="center">

**⭐ If this tool saves you time, give it a star!**

Built with ❤️ for the Wesco Global Accounts Team

</div>
