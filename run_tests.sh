#!/bin/bash
# Quick test runner for Wesco MRO Parser
# Usage: ./run_tests.sh [quick|full]
#
# Test data location is read from the TEST_DATA_DIR environment variable.
# If not set, the validation suite falls back to the developer default path
# baked into run_validation.py.
#
# Set once per machine (add to ~/.zshrc or ~/.bashrc):
#   export TEST_DATA_DIR="/path/to/your/WESCO/Data Parse Agent/Data Context"
#
# Or pass inline for a single run:
#   TEST_DATA_DIR="/your/path" ./run_tests.sh full

set -e

cd "$(dirname "$0")"

# Build --data-dir flag if TEST_DATA_DIR is set, otherwise let the script use its default
DATA_DIR_FLAG=""
if [ -n "$TEST_DATA_DIR" ]; then
    DATA_DIR_FLAG="--data-dir \"$TEST_DATA_DIR\""
fi

if [ "$1" = "quick" ]; then
    echo "🚀 Running quick smoke tests..."
    python3 tests/test_quick.py
elif [ "$1" = "full" ]; then
    echo "🚀 Running full validation suite..."
    if [ -n "$TEST_DATA_DIR" ]; then
        python3 tests/run_validation.py --data-dir "$TEST_DATA_DIR"
    else
        python3 tests/run_validation.py
    fi
else
    echo "🚀 Running quick smoke tests (use './run_tests.sh full' for complete validation)..."
    python3 tests/test_quick.py
    echo ""
    echo "✨ Quick tests complete. Run './run_tests.sh full' for comprehensive validation."
fi
