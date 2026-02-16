# Wesco MRO Parser — Test Suite

Comprehensive validation suite for the Wesco MRO Data Parser to ensure accuracy, performance, and data quality before team deployment.

## Quick Start

```bash
# From the mro-parser directory
python tests/run_validation.py

# Or specify custom data location
python tests/run_validation.py --data-dir "/path/to/test/data"

# Quick mode (skip large file tests)
python tests/run_validation.py --quick
```

## What Gets Tested

### Phase 1: Accuracy Test
Compares parser output against manually-verified ground truth data (Electrical file).
- **MFG Exact Match Rate**: Target ≥85%
- **PN Exact Match Rate**: Target ≥85%
- **Processing Time**: Target <2 seconds for ~200 rows

### Phase 2: QA Engine
Validates that quality assurance rules correctly catch data issues:
- Distributor names in MFG column: 0 expected
- Descriptor keywords in MFG: 0 expected
- Digits in MFG names: 0 expected
- Normalization violations (CROUSE-HINDS, SQUARE-D): 0 expected

### Phase 3: Unit Tests
Tests individual extraction functions with known input/output pairs:
- `extract_pn_from_text()` — labeled and heuristic PN extraction
- `extract_mfg_from_text()` — manufacturer name extraction
- `sanitize_mfg()` — validation and normalization logic

### Phase 4: Scale Test (Book25)
Tests parser on 174-row file with different schema:
- **Processing Time**: Target <5 seconds
- **Fill Rate**: MFG and PN population percentage
- **Extraction Accuracy**: Comparison against ground truth if available

### Phase 5: Normalization
Validates manufacturer normalization map integrity:
- No circular references (A→B→C→A)
- Critical normalizations work correctly
- Distributor/descriptor lists populated

### Phase 6: Edge Cases
Boundary condition testing:
- Null and empty string inputs
- Very long strings (10K+ characters)
- Special characters in part numbers
- Multiple label priority handling

## Test Data Requirements

Place test files in: `/Users/nolansulpizio/Desktop/Documents - Nolan's MacBook Pro/WESCO/Data Parse Agent/Data Context/`

Required files:
- `Electrical PN_MFG Search.XLSX` — blank input file (~200 rows)
- `Electrical PN_MFG Search_COMPLETE.xlsx` — manually verified ground truth
- `Book25.xlsx` — 174-row scale test with different schema

## Output Files

All output saved to `test_results/` in the data directory:
- `validation_report.xlsx` — Executive summary with pass/fail metrics
- `test_log.txt` — Full console output with timestamps
- `test_results.json` — Machine-readable results for CI/CD
- `electrical_parsed_output.xlsx` — Actual parser output for spot-checking
- `book25_parsed_output.xlsx` — Book25 parser output

## Interpreting Results

### ✓ PASS
Test met its acceptance threshold. No action required.

### ✗ FAIL
Test fell below threshold. Review detail message and investigate:
- Check `mismatches` in validation_report.xlsx for specifics
- Review test_log.txt for context
- Compare parser output files against ground truth manually

## Success Criteria (Gamma Presentation)

For team confidence and leadership approval:
- **Overall Pass Rate**: ≥90% (44+ of 48 tests)
- **MFG Exact Match**: ≥85%
- **PN Exact Match**: ≥85%
- **QA Engine**: 0 critical violations (distributors, descriptors, digits)
- **Processing Time**: <2s for 200 rows, <5s for 174 rows

## Known Findings

Based on initial validation (44/46 passed):

1. **12V Bare Spec** — Heuristic fallback catches bare voltage specs like "12V" as part numbers. This is a known edge case. Fix: add voltage/wattage exclusion pattern.

2. **Book25 MFG at 0%** — Expected behavior. Book25 uses a different schema without "MANUFACTURER:" labels, and short names like "3M" get filtered by the digit rejection rule. PN extraction at 66.7% is acceptable for unlabeled data.

## Running Tests in Claude CLI

The test suite is designed for easy execution via Claude CLI:

```bash
# Navigate to project
cd "/Users/nolansulpizio/Desktop/Clean Plate/Claude Code/agents/mro-parser"

# Run tests
python tests/run_validation.py
```

Claude CLI can also run tests automatically after code changes to ensure no regressions.

## Dependencies

Required Python packages (already in parent requirements.txt):
- pandas
- openpyxl

No additional dependencies needed.
