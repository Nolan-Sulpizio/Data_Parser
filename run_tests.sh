#!/bin/bash
# Quick test runner for Wesco MRO Parser
# Usage: ./run_tests.sh [quick|full]

set -e

cd "$(dirname "$0")"

if [ "$1" = "quick" ]; then
    echo "🚀 Running quick smoke tests..."
    python3 tests/test_quick.py
elif [ "$1" = "full" ]; then
    echo "🚀 Running full validation suite..."
    python3 tests/run_validation.py
else
    echo "🚀 Running quick smoke tests (use './run_tests.sh full' for complete validation)..."
    python3 tests/test_quick.py
    echo ""
    echo "✨ Quick tests complete. Run './run_tests.sh full' for comprehensive validation."
fi
