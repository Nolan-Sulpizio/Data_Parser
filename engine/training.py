"""
training.py — Training Data Ingestion Pipeline

Processes completed/ground-truth Excel files to extract:
  - MFG normalization patterns
  - Known manufacturer names
  - Column name variants
  - PN format patterns

Outputs training_data.json for engine enhancement.
100% offline processing.
"""

import os
import json
import re
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Optional
from collections import Counter

# Import column_mapper to help identify columns in training files
from .column_mapper import map_columns


# ═══════════════════════════════════════════════════════════════
#  CONFIGURATION
# ═══════════════════════════════════════════════════════════════

DEFAULT_TRAINING_FILE = 'training_data.json'


# ═══════════════════════════════════════════════════════════════
#  TRAINING DATA EXTRACTION
# ═══════════════════════════════════════════════════════════════

def ingest_training_files(directory: str, output_path: str = DEFAULT_TRAINING_FILE) -> dict:
    """
    Process all Excel files in directory and generate training_data.json.

    Args:
        directory: Path to folder containing completed Excel files
        output_path: Where to save the JSON output

    Returns:
        The training data dict

    Algorithm:
        1. Scan directory for .xlsx/.xls/.csv files
        2. For each file, use column_mapper to identify semantic roles
        3. For rows where MFG/PN are filled, extract patterns
        4. Aggregate across all files
        5. Merge with existing training_data.json if it exists (don't lose previous data)
        6. Write output
    """
    print(f"\n{'='*60}")
    print(f"TRAINING DATA INGESTION")
    print(f"{'='*60}")
    print(f"Source directory: {directory}")

    # Initialize training data structure
    training_data = {
        'version': '1.0',
        'generated_at': datetime.now().isoformat(),
        'files_processed': 0,
        'total_rows_analyzed': 0,
        'mfg_normalization': {},
        'known_manufacturers': [],
        'column_aliases': {
            'source_description': [],
            'source_po_text': [],
            'source_notes': [],
            'mfg_output': [],
            'pn_output': [],
            'sim_output': [],
            'item_number': [],
        },
        'pn_patterns': {
            'format_frequency': {},
            'avg_length': 0.0,
            'max_valid_length': 0,
        }
    }

    # Load existing training data if it exists (for incremental updates)
    if os.path.exists(output_path):
        try:
            existing = load_training_data(output_path)
            print(f"Found existing training data: {existing.get('files_processed', 0)} files previously processed")
            training_data['mfg_normalization'] = existing.get('mfg_normalization', {})
            training_data['column_aliases'] = existing.get('column_aliases', training_data['column_aliases'])
        except Exception as e:
            print(f"Warning: Could not load existing training data: {e}")

    # Find all Excel/CSV files in directory
    directory_path = Path(directory)
    file_patterns = ['*.xlsx', '*.xls', '*.csv']
    training_files = []

    for pattern in file_patterns:
        training_files.extend(directory_path.glob(pattern))
        training_files.extend(directory_path.glob(f"**/{pattern}"))  # Recursive search

    training_files = list(set(training_files))  # Remove duplicates
    print(f"Found {len(training_files)} training files")

    # Counters for aggregation
    all_mfgs = set()
    all_pn_lengths = []
    pn_format_counter = Counter()
    total_rows = 0

    # Process each file
    for file_path in training_files:
        try:
            print(f"\nProcessing: {file_path.name}")
            df = _load_file(file_path)

            if df is None or len(df) == 0:
                print(f"  Skipped: empty or unreadable")
                continue

            # Use column mapper to identify semantic roles
            column_mapping = map_columns(df)

            # Record column names as aliases
            _record_column_aliases(training_data, column_mapping, df.columns)

            # Extract MFG and PN patterns from filled rows
            mfg_col = column_mapping.get('mfg_output')
            pn_col = column_mapping.get('pn_output')
            source_cols = (column_mapping.get('source_description', []) +
                          column_mapping.get('source_po_text', []) +
                          column_mapping.get('source_notes', []))

            if not mfg_col or not pn_col:
                print(f"  Skipped: could not identify MFG/PN columns")
                continue

            # Process each row
            rows_processed = 0
            for idx, row in df.iterrows():
                mfg_value = row.get(mfg_col)
                pn_value = row.get(pn_col)

                # Skip rows where MFG/PN are empty
                if pd.isna(mfg_value) or pd.isna(pn_value):
                    continue
                if str(mfg_value).strip() in ('', 'nan', 'None'):
                    continue
                if str(pn_value).strip() in ('', 'nan', 'None'):
                    continue

                mfg_clean = str(mfg_value).strip().upper()
                pn_clean = str(pn_value).strip().upper()

                # Collect known manufacturers
                all_mfgs.add(mfg_clean)

                # Extract MFG normalization patterns
                for source_col in source_cols:
                    if source_col in df.columns:
                        source_text = row.get(source_col)
                        if pd.notna(source_text):
                            _extract_mfg_normalization(
                                str(source_text).upper(),
                                mfg_clean,
                                training_data['mfg_normalization']
                            )

                # Analyze PN patterns
                if pn_clean:
                    all_pn_lengths.append(len(pn_clean))
                    pn_format = _classify_pn_format(pn_clean)
                    pn_format_counter[pn_format] += 1

                rows_processed += 1

            total_rows += rows_processed
            training_data['files_processed'] += 1
            print(f"  Processed {rows_processed} rows with MFG/PN data")

        except Exception as e:
            print(f"  Error processing {file_path.name}: {e}")

    # Finalize aggregated data
    training_data['total_rows_analyzed'] = total_rows
    training_data['known_manufacturers'] = sorted(list(all_mfgs))
    training_data['pn_patterns']['format_frequency'] = dict(pn_format_counter)

    if all_pn_lengths:
        training_data['pn_patterns']['avg_length'] = sum(all_pn_lengths) / len(all_pn_lengths)
        training_data['pn_patterns']['max_valid_length'] = max(all_pn_lengths)
    else:
        training_data['pn_patterns']['avg_length'] = 0.0
        training_data['pn_patterns']['max_valid_length'] = 0

    # Write output
    _save_training_data(training_data, output_path)

    # Print summary
    print(f"\n{'='*60}")
    print(f"TRAINING DATA SUMMARY")
    print(f"{'='*60}")
    print(f"Files processed: {training_data['files_processed']}")
    print(f"Total rows analyzed: {training_data['total_rows_analyzed']}")
    print(f"Known manufacturers: {len(training_data['known_manufacturers'])}")
    print(f"MFG normalizations: {len(training_data['mfg_normalization'])}")
    print(f"PN format patterns: {len(training_data['pn_patterns']['format_frequency'])}")
    print(f"Output saved to: {output_path}")
    print(f"{'='*60}\n")

    return training_data


def _load_file(file_path: Path) -> Optional[pd.DataFrame]:
    """Load an Excel or CSV file, returning None if it fails."""
    try:
        if file_path.suffix.lower() == '.csv':
            return pd.read_csv(file_path)
        else:
            return pd.read_excel(file_path)
    except Exception as e:
        print(f"  Error loading file: {e}")
        return None


def _record_column_aliases(training_data: dict, column_mapping: dict, all_columns: list):
    """Record all column names from this file as aliases for their detected roles."""
    for role, value in column_mapping.items():
        if role not in training_data['column_aliases']:
            training_data['column_aliases'][role] = []

        if isinstance(value, list):
            # Multiple columns (source_*)
            for col_name in value:
                if col_name and col_name not in training_data['column_aliases'][role]:
                    training_data['column_aliases'][role].append(col_name)
        elif value:
            # Single column (output columns)
            if value not in training_data['column_aliases'][role]:
                training_data['column_aliases'][role].append(value)


def _extract_mfg_normalization(source_text: str, final_mfg: str, normalization_map: dict):
    """
    Find MFG variants in source text and add to normalization map.

    Strategy: Look for substrings that are similar to final_mfg but not exact.
    """
    # Split source text into potential MFG tokens
    tokens = re.findall(r'\b[A-Z][A-Z0-9\-&\./\s]{2,40}\b', source_text)

    for token in tokens:
        token_clean = re.sub(r'\s+', ' ', token.strip())

        # If this token is similar but not identical to final_mfg, add it as a variant
        if token_clean != final_mfg:
            # Check if it's a plausible variant (shares some characters)
            similarity = _simple_similarity(token_clean, final_mfg)
            if similarity > 0.5:  # At least 50% similarity
                if token_clean not in normalization_map:
                    normalization_map[token_clean] = final_mfg


def _simple_similarity(s1: str, s2: str) -> float:
    """Calculate simple character overlap similarity between two strings."""
    s1_chars = set(s1.replace(' ', '').replace('-', ''))
    s2_chars = set(s2.replace(' ', '').replace('-', ''))

    if not s1_chars or not s2_chars:
        return 0.0

    intersection = len(s1_chars & s2_chars)
    union = len(s1_chars | s2_chars)

    return intersection / union if union > 0 else 0.0


def _classify_pn_format(pn: str) -> str:
    """
    Classify a part number into a format pattern.

    Examples:
        "ABC-123" → "ALPHA-NUMERIC"
        "123/ABC/456" → "NUMERIC/ALPHA/NUMERIC"
        "XYZ123" → "ALPHANUMERIC"
    """
    # Check for common separators
    if '-' in pn:
        parts = pn.split('-')
        pattern_parts = []
        for part in parts:
            if part.isalpha():
                pattern_parts.append('ALPHA')
            elif part.isdigit():
                pattern_parts.append('NUMERIC')
            else:
                pattern_parts.append('ALPHANUM')
        return '-'.join(pattern_parts)

    elif '/' in pn:
        parts = pn.split('/')
        pattern_parts = []
        for part in parts:
            if part.isalpha():
                pattern_parts.append('ALPHA')
            elif part.isdigit():
                pattern_parts.append('NUMERIC')
            else:
                pattern_parts.append('ALPHANUM')
        return '/'.join(pattern_parts)

    else:
        # No separators
        has_alpha = bool(re.search(r'[A-Z]', pn))
        has_digit = bool(re.search(r'[0-9]', pn))

        if has_alpha and has_digit:
            return 'ALPHANUMERIC'
        elif has_alpha:
            return 'ALPHA'
        elif has_digit:
            return 'NUMERIC'
        else:
            return 'UNKNOWN'


# ═══════════════════════════════════════════════════════════════
#  TRAINING DATA PERSISTENCE
# ═══════════════════════════════════════════════════════════════

def load_training_data(path: str = DEFAULT_TRAINING_FILE) -> dict:
    """Load training data, returning empty defaults if file doesn't exist."""
    if not os.path.exists(path):
        return {
            'version': '1.0',
            'generated_at': None,
            'files_processed': 0,
            'total_rows_analyzed': 0,
            'mfg_normalization': {},
            'known_manufacturers': [],
            'column_aliases': {},
            'pn_patterns': {'format_frequency': {}, 'avg_length': 0.0, 'max_valid_length': 0},
        }

    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Failed to load training data from {path}: {e}")
        return {
            'mfg_normalization': {},
            'known_manufacturers': [],
            'column_aliases': {},
            'pn_patterns': {},
        }


def _save_training_data(data: dict, path: str):
    """Save training data to JSON file."""
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error: Failed to save training data to {path}: {e}")


# ═══════════════════════════════════════════════════════════════
#  CLI INTERFACE
# ═══════════════════════════════════════════════════════════════

def main():
    """CLI entry point for training data ingestion."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m engine.training <directory> [output_path]")
        print("\nExample:")
        print("  python -m engine.training ./test_data")
        print("  python -m engine.training /path/to/completed/files custom_training.json")
        sys.exit(1)

    directory = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_TRAINING_FILE

    if not os.path.isdir(directory):
        print(f"Error: {directory} is not a valid directory")
        sys.exit(1)

    ingest_training_files(directory, output_path)


if __name__ == '__main__':
    main()
