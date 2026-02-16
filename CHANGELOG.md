# Changelog

All notable changes to the Wesco MRO Data Parser will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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
