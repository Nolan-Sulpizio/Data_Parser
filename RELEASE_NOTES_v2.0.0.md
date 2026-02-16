# 🎉 Wesco MRO Parser v2.0.0

**Released:** February 16, 2026

The first official production release of the Wesco MRO Parser — a complete rebrand and professional polish of the internal MRO data extraction tool built for the Global Accounts team.

---

## 🌟 Highlights

### Complete Wesco Rebrand
- **New Identity:** Rebranded from prototype to official Wesco International tool
- **Corporate Colors:** Wesco primary green (#009639) throughout the UI
- **Professional Logo:** Bold "W" in the sidebar with Wesco branding
- **Modern Dark Theme:** Clean, professional interface matching enterprise standards

### Production-Ready Features
- ✅ **3 Specialized Pipelines** — MFG/PN Extraction, Part Number Cleaning, SIM Builder
- ✅ **Natural Language Instructions** — Type what you need in plain English
- ✅ **Drag-and-Drop Import** — Load Excel files instantly
- ✅ **Live Preview** — Compare input vs output before exporting
- ✅ **Automated QA** — Flags issues automatically
- ✅ **Processing History** — Every job logged with full stats
- ✅ **Saved Configurations** — Reusable templates for common tasks
- ✅ **100% Offline** — No API keys, no internet required

### Enterprise Documentation
- 📚 Comprehensive README with demo, architecture diagrams, and usage guide
- 🔒 Security policy and vulnerability reporting process
- 🤝 Contributing guidelines for team collaboration
- 📋 GitHub issue templates (bug reports, feature requests, normalization requests)
- 🔄 GitHub Actions CI for automated quality checks
- 📄 Professional changelog following industry standards

---

## 📦 Installation

### Quick Start (Recommended)

1. **Download** `WescoMROParser.exe` from the Assets section below
2. **Run** the .exe (no installation required — double-click to launch)
3. **Import** your Excel file and start parsing

**No Python installation needed!** The .exe is completely standalone.

### From Source

```bash
git clone https://github.com/Nolan-Sulpizio/Data_Parser.git
cd Data_Parser
pip install -r requirements.txt
python app.py
```

---

## 🔧 What's New in v2.0.0

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
- Specification documents in `docs/` directory
- UI improvements:
  - Dashed border on import drop zone
  - Enhanced instruction placeholder text
  - Better visual feedback throughout

### Fixed
- Improved instruction interpretation feedback
- Better color contrast for accessibility

---

## 📊 Features Overview

| Feature | Description |
|---------|-------------|
| **MFG/PN Extraction** | Extract manufacturer and part number from unstructured descriptions |
| **Part Number Cleaning** | Validate and clean existing part numbers with strict format rules |
| **SIM Builder** | Generate SIM values from MFG + ITEM # with 3 format options |
| **QA Engine** | Auto-flag missing data, distributors-as-MFG, and inconsistencies |
| **Normalization** | Built-in map for 20+ common MFG abbreviations |
| **History Tracking** | SQLite database logs every processing job |
| **Saved Configs** | Save instruction templates for reuse |

---

## 🎯 Use Cases

Perfect for Global Accounts BDAs who need to:
- Extract MFG and PN from Material Descriptions
- Clean messy Part Number columns
- Generate SIM values for BOM automation
- Process large Excel files (1,000+ rows) quickly
- Ensure data quality before submitting to systems

---

## 📚 Documentation

- **README:** [Comprehensive guide](README.md)
- **Architecture:** [Technical overview](README.md#-architecture)
- **Pipelines:** [Processing pipeline specs](docs/)
- **Contributing:** [Team guidelines](CONTRIBUTING.md)
- **Security:** [Security policy](SECURITY.md)
- **Changelog:** [Full version history](CHANGELOG.md)

---

## 🔗 Quick Links

- [Report a Bug](https://github.com/Nolan-Sulpizio/Data_Parser/issues/new?template=bug_report.md)
- [Request a Feature](https://github.com/Nolan-Sulpizio/Data_Parser/issues/new?template=feature_request.md)
- [Request a Normalization](https://github.com/Nolan-Sulpizio/Data_Parser/issues/new?template=normalization_request.md)

---

## 👨‍💻 Built By

**Nolan Sulpizio**
Business Development Associate — Global Accounts
Wesco International

---

## 🙏 Acknowledgments

Built with:
- [customtkinter](https://github.com/TomSchimansky/CustomTkinter) by Tom Schimansky
- [pandas](https://pandas.pydata.org/) by the pandas development team
- [openpyxl](https://openpyxl.readthedocs.io/) by the openpyxl team

---

## ⚠️ System Requirements

- **OS:** Windows 10 or later
- **RAM:** 4GB minimum (8GB recommended for large files)
- **Disk:** 100MB free space

---

## 📝 Notes

- This is an **internal Wesco tool** — proprietary and not for external distribution
- All processing happens **100% offline** — no data leaves your machine
- For support, contact Nolan Sulpizio via Microsoft Teams or Slack

---

<div align="center">

**Built with ❤️ for the Wesco Global Accounts Team**

⭐ If this tool saves you time, give the repo a star!

</div>
