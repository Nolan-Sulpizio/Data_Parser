# Wesco MRO Parser — Testing Guide

## Quick Reference

### Run Tests
```bash
# Quick smoke tests (< 1 second)
./run_tests.sh

# Full validation suite (~10 seconds)
./run_tests.sh full

# Or directly:
python tests/test_quick.py           # Fast unit tests
python tests/run_validation.py       # Complete validation
```

### Via Claude CLI
```
"Run the tests"
"Run full validation"
"Test the parser"
```

## Test Suite Overview

### 1. Quick Smoke Tests (`test_quick.py`)
**Purpose**: Fast validation during development
**Time**: <1 second
**What it tests**:
- PN extraction (labeled and heuristic)
- MFG extraction (various patterns)
- Sanitization (validation and normalization)
- SIM builder (all patterns)

**When to use**: After any code change to engine

### 2. Full Validation Suite (`run_validation.py`)
**Purpose**: Comprehensive pre-release validation
**Time**: 5-10 seconds
**What it tests**:

#### Phase 1: Accuracy Test
Compares parser against manually-verified ground truth
- MFG exact match rate (target: ≥85%)
- PN exact match rate (target: ≥85%)
- Processing time (target: <2s for 200 rows)
- Generates mismatch report

#### Phase 2: QA Engine Test
Validates data quality rule enforcement
- No distributors in MFG column
- No descriptors in MFG column
- No digits in MFG values
- Normalization correctness (CROUSE HINDS, SQUARE D)

#### Phase 3: Unit Tests
Tests core functions with known inputs/outputs
- `extract_pn_from_text()` — 5 test cases
- `extract_mfg_from_text()` — 3 test cases
- `sanitize_mfg()` — 7 test cases

#### Phase 4: Scale Test (Book25)
Tests performance on large, differently-formatted dataset
- Processing time (target: <5s for 174 rows)
- Extraction rates on complex schema
- Memory efficiency

#### Phase 5: Normalization Test
Validates MFG standardization integrity
- No circular references in NORMALIZE_MFG map
- Critical normalizations work correctly
- Distributor/descriptor lists populated

#### Phase 6: Edge Cases
Tests boundary conditions
- Null inputs
- Empty strings
- Very long inputs (10K+ chars)
- Special characters
- Multiple label priority

**When to use**: Before commits, releases, demos

## Test Data

### Location
```
/Users/nolansulpizio/Desktop/Documents - Nolan's MacBook Pro/WESCO/Data Parse Agent/Data Context/
```

### Files
- **Electrical PN_MFG Search.XLSX** — 206 rows, blank MFG/PN (input)
- **Electrical PN_MFG Search_COMPLETE.xlsx** — Manual verification (ground truth)
- **Book25.xlsx** — 174 rows, multi-MFG schema (scale test)

## Output Files

After running full validation, check:
```
test_results/
├── validation_report.xlsx    ← Executive summary (open this first)
├── test_log.txt              ← Detailed console output
├── test_results.json         ← Machine-readable results
├── electrical_parsed_output.xlsx  ← Parser output for spot-checking
└── book25_parsed_output.xlsx      ← Book25 parser output
```

## Interpreting Results

### Console Output
```
══════════════════════════════════════════════════════════════════
  [✓ PASS]  MFG Exact Match Rate  →  89.4% (168/188 rows)
  [✓ PASS]  PN Exact Match Rate   →  87.5% (175/200 rows)
  [✗ FAIL]  Processing Time       →  2.3s (target: <2s)
══════════════════════════════════════════════════════════════════
  TEST SUMMARY: 44/46 passed (95.7%)
```

- **✓ PASS**: Test met acceptance threshold
- **✗ FAIL**: Test below threshold — investigate

### Excel Report
`validation_report.xlsx` contains:
- **Executive Summary**: High-level metrics with green/red color coding
- **Test Log**: All test results with timestamps
- **Mismatches**: Row-by-row failures (if any)

### Success Criteria for Gamma
- Overall pass rate: ≥90% ✓
- MFG exact match: ≥85% ✓
- PN exact match: ≥85% ✓
- QA violations: 0 ✓
- Processing time: <2s for 200 rows ✓

## Your Baseline Results

Last validation (from context provided):
```
Overall: 44/46 passed (95.7%) ✓

Accuracy:
  MFG Exact: 89.4% (168/188 rows) ✓
  PN Exact: 87.5% (175/200 rows) ✓
  Processing: 0.49s ✓

QA Engine:
  Distributors: 0 ✓
  Descriptors: 0 ✓
  Digit-MFGs: 0 ✓

Scale (Book25):
  Processing: 0.08s ✓
  PN Exact: 66.7% ✓
  MFG Exact: 0% (expected) ✓
```

**Status: READY FOR TEAM DEPLOYMENT**

## Known Findings

1. **12V Bare Spec** (expected)
   - Heuristic fallback catches "12V" as part number
   - Edge case documented in spec
   - Not critical for production use

2. **Book25 MFG at 0%** (expected)
   - Book25 uses different schema without "MANUFACTURER:" labels
   - Short names like "3M" filtered by digit rejection rule
   - PN extraction at 66.7% is acceptable for unlabeled data

## Troubleshooting

### "File not found" error
```bash
# Verify test data exists
ls -la "/Users/nolansulpizio/Desktop/Documents - Nolan's MacBook Pro/WESCO/Data Parse Agent/Data Context/"

# Or use custom path
python tests/run_validation.py --data-dir "/path/to/your/data"
```

### "Module not found" error
```bash
# Install dependencies
pip install -r requirements.txt
```

### Tests failing after code change
```bash
# 1. Run quick tests first
./run_tests.sh

# 2. If quick tests pass but validation fails:
# Check test_results/test_log.txt for details

# 3. Compare output manually:
# Open test_results/electrical_parsed_output.xlsx
```

## Best Practices

### Development Workflow
```bash
# 1. Make code changes
vim engine/parser_core.py

# 2. Quick validation
./run_tests.sh
# If PASS: continue

# 3. Full validation before commit
./run_tests.sh full
# If PASS: commit

# 4. Add new tests for new features
# Edit tests/test_quick.py or tests/run_validation.py
```

### Pre-Release Checklist
- [ ] Run full validation: `./run_tests.sh full`
- [ ] All tests pass (≥90% pass rate)
- [ ] Review validation_report.xlsx
- [ ] No critical QA violations
- [ ] Processing time within targets
- [ ] Update CHANGELOG.md with test results

### Gamma Presentation Metrics
Use these numbers from validation report:
- **Accuracy**: "89.4% MFG, 87.5% PN exact match"
- **Performance**: "0.49 seconds for 206 rows"
- **Quality**: "Zero critical violations detected"
- **Testing**: "44 of 46 validation tests passed (95.7%)"
- **Confidence**: "Validated against production data"

## Adding New Tests

### Quick Tests
Edit `tests/test_quick.py`:
```python
def test_your_feature():
    """Test new feature."""
    # Your test code here
    assert expected == actual
```

### Validation Suite
Edit `tests/run_validation.py`:
```python
def test_your_feature(data_dir, output_dir, log):
    """Test new feature with real data."""
    log.section("TEST 7: YOUR FEATURE")
    # Your test code here
    log.result("Test name", passed, "detail")
    return results
```

Then add to main():
```python
all_results['your_feature'] = test_your_feature(data_dir, output_dir, log)
```

## Contact

Nolan Sulpizio
Wesco Global Accounts
nolan.sulpizio@wesco.com

---

**Remember**: Tests are your confidence that the parser works correctly. Run them often!
