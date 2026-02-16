#!/usr/bin/env python3
"""
Quick smoke tests for Wesco MRO Parser.
Run these for fast validation during development.
"""

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.parser_core import (
    extract_pn_from_text,
    extract_mfg_from_text,
    sanitize_mfg,
    build_sim
)


def test_pn_extraction():
    """Test basic PN extraction."""
    cases = [
        ("PN: ABC-123", "ABC-123"),
        ("PART NUMBER: XYZ789", "XYZ789"),
        ("MODEL NUMBER: TEST456", "TEST456"),
        (None, None),
        ("", None),
    ]

    print("Testing PN extraction...")
    passed = 0
    for text, expected in cases:
        result, method = extract_pn_from_text(text)
        if (result or '').strip().upper() == (expected or '').strip().upper():
            print(f"  ✓ {text or 'None'} → {result}")
            passed += 1
        else:
            print(f"  ✗ {text or 'None'} → expected {expected}, got {result}")

    print(f"PN extraction: {passed}/{len(cases)} passed\n")
    return passed == len(cases)


def test_mfg_extraction():
    """Test basic MFG extraction."""
    cases = [
        ("MANUFACTURER: PANDUIT PART NUMBER: ABC", "PANDUIT"),
        ("MANUFACTURER: FERRAZ SHAWMUT MODEL: XYZ", "FERRAZ SHAWMUT"),
        (None, None),
        ("", None),
    ]

    print("Testing MFG extraction...")
    passed = 0
    for text, expected in cases:
        result, method = extract_mfg_from_text(text, None, set())
        if result:
            result = result.strip().upper()
        if expected:
            expected = expected.strip().upper()
        if result == expected:
            print(f"  ✓ {text or 'None'} → {result}")
            passed += 1
        else:
            print(f"  ✗ {text or 'None'} → expected {expected}, got {result}")

    print(f"MFG extraction: {passed}/{len(cases)} passed\n")
    return passed == len(cases)


def test_sanitization():
    """Test MFG sanitization."""
    cases = [
        ("PANDUIT", "PANDUIT"),
        ("GRAYBAR", None),  # distributor
        ("TEST123", None),  # has digits
        ("PANDT", "PANDUIT"),  # normalization
        ("CROUSE-HINDS", "CROUSE HINDS"),  # hyphen removal
        (None, None),
        ("", None),
    ]

    print("Testing MFG sanitization...")
    passed = 0
    for input_val, expected in cases:
        result = sanitize_mfg(input_val)
        if result == expected:
            print(f"  ✓ {input_val or 'None'} → {result}")
            passed += 1
        else:
            print(f"  ✗ {input_val or 'None'} → expected {expected}, got {result}")

    print(f"Sanitization: {passed}/{len(cases)} passed\n")
    return passed == len(cases)


def test_sim_builder():
    """Test SIM generation."""
    cases = [
        ("PANDUIT", "ABC-123", "space", "PANDUIT ABC-123"),
        ("APPLETON", "XYZ789", "dash", "APPLETON-XYZ789"),
        ("SQUARE D", "TEST456", "compact", "SQUARE DTEST456"),
        ("", "ABC", "space", "ABC"),
        ("MFG", "", "space", "MFG"),
    ]

    print("Testing SIM builder...")
    passed = 0
    for mfg, pn, pattern, expected in cases:
        result = build_sim(mfg, pn, pattern)
        if result == expected:
            print(f"  ✓ {mfg}|{pn}|{pattern} → {result}")
            passed += 1
        else:
            print(f"  ✗ {mfg}|{pn}|{pattern} → expected {expected}, got {result}")

    print(f"SIM builder: {passed}/{len(cases)} passed\n")
    return passed == len(cases)


def main():
    """Run all quick tests."""
    print("=" * 60)
    print("WESCO MRO PARSER — QUICK SMOKE TESTS")
    print("=" * 60)
    print()

    results = []
    results.append(("PN Extraction", test_pn_extraction()))
    results.append(("MFG Extraction", test_mfg_extraction()))
    results.append(("Sanitization", test_sanitization()))
    results.append(("SIM Builder", test_sim_builder()))

    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  [{status}]  {name}")

    print(f"\nOverall: {passed}/{total} test suites passed")
    print("=" * 60)

    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
