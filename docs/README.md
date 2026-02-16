# Wesco MRO Parser — Documentation

## Overview
This directory contains technical specifications and user guides for the Wesco MRO Parser.

## Technical Specifications
These documents define the parsing algorithms and business rules:

- **[MFG_PN_Parsing_Agent_Spec.md](MFG_PN_Parsing_Agent_Spec.md)** — Manufacturer and Part Number extraction logic
- **[MRO_Part_Number_Processing_Spec.md](MRO_Part_Number_Processing_Spec.md)** — Part number validation and cleaning rules
- **[SIM_BOM_Automation_Spec.md](SIM_BOM_Automation_Spec.md)** — SIM (Standard Item Marker) generation

## User Guides

- **[TESTING_GUIDE.md](TESTING_GUIDE.md)** — Complete testing reference for developers
- **[GAMMA_PRESENTATION_METRICS.md](GAMMA_PRESENTATION_METRICS.md)** — Validated metrics for leadership presentations

## Quick Links

### For Users
- [Quick Start Guide](../QUICK_START.md) — Get started in 5 minutes
- [User README](../README.md) — Complete user documentation

### For Developers
- [Testing Guide](TESTING_GUIDE.md) — How to run and interpret tests
- [Contributing Guide](../CONTRIBUTING.md) — Development guidelines
- [CLAUDE.md](../CLAUDE.md) — Project context and instructions

### For Leadership
- [Gamma Metrics](GAMMA_PRESENTATION_METRICS.md) — Validated performance numbers
- [Release Notes](../RELEASE_NOTES_v2.0.0.md) — Version history and features

## Running Tests

```bash
# Quick smoke tests
./run_tests.sh

# Full validation
./run_tests.sh full

# Or use the test suite directly
python tests/run_validation.py
```

See [tests/README.md](../tests/README.md) for complete testing documentation.
