#!/usr/bin/env python3
"""
run_regression.py — MRO Parser regression gatekeeper.

Runs all 4 input files through the current engine, compares output
row-by-row against golden snapshots, enforces ratchet thresholds,
and reports every regression with row-level detail.

Usage:
    python tests/run_regression.py              # all files
    python tests/run_regression.py wesco_empty  # single file
    python tests/run_regression.py --ratchet    # update thresholds after improvement

Exit codes:
    0 — all files pass thresholds, no regressions
    1 — threshold failure or row regression detected
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

import pandas as pd
from engine.parser_core import pipeline_mfg_pn
from engine.column_mapper import map_columns

CONFIG_PATH = REPO_ROOT / "tests" / "regression_config.json"

# ── Tolerance for fill-rate comparisons (0.1% = ~2 rows on a 2684-row file) ──
FILL_RATE_TOLERANCE = 0.1


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def count_filled(series: pd.Series) -> int:
    return int(((series.notna()) & (series.astype(str).str.strip() != '')).sum())


def get_value(row, col):
    """Return normalised string value from a DataFrame row."""
    v = row.get(col, '')
    if pd.isna(v):
        return ''
    return str(v).strip().upper()


def run_engine(cfg: dict, td: dict) -> pd.DataFrame:
    path = REPO_ROOT / cfg["input"]
    df = pd.read_excel(path, engine='openpyxl')
    cm = map_columns(df, td)
    result = pipeline_mfg_pn(
        df,
        source_cols=cfg["source_cols"],
        mfg_col=cfg["mfg_col"],
        pn_col=cfg["pn_col"],
        supplier_col=cfg.get("supplier_col"),
        column_mapping=cm,
        add_sim=cfg.get("add_sim", True),
    )
    return result.df


def load_golden(cfg: dict) -> pd.DataFrame:
    path = REPO_ROOT / cfg["golden"]
    if not path.exists():
        raise FileNotFoundError(
            f"Golden snapshot missing: {path}\n"
            f"Run:  python tests/create_golden_snapshots.py"
        )
    return pd.read_excel(path, engine='openpyxl')


# ─────────────────────────────────────────────────────────────────────────────
# Per-file regression check
# ─────────────────────────────────────────────────────────────────────────────

def check_file(name: str, cfg: dict, thresholds: dict, compare_cols: list,
               td: dict, verbose: bool = True) -> dict:
    """
    Run engine on one file, compare against golden, check thresholds.
    Returns a result dict with keys: passed, regressions, improvements, stats.
    """
    print(f"\n{'─'*60}")
    print(f"  FILE: {name}")
    print(f"{'─'*60}")

    # Run current engine
    df_current = run_engine(cfg, td)

    # Load golden
    df_golden = load_golden(cfg)

    mfg_col = cfg["mfg_col"]
    pn_col  = cfg["pn_col"]
    total   = len(df_current)

    mfg_n   = count_filled(df_current[mfg_col])
    pn_n    = count_filled(df_current[pn_col])
    mfg_pct = round(mfg_n / total * 100, 1)
    pn_pct  = round(pn_n  / total * 100, 1)

    thresh = thresholds.get(name, {})
    floor_mfg = thresh.get("mfg", 0.0)
    floor_pn  = thresh.get("pn",  0.0)

    print(f"  Rows:    {total}")
    print(f"  MFG:     {mfg_n}/{total} ({mfg_pct}%)  floor={floor_mfg}%")
    print(f"  PN:      {pn_n}/{total} ({pn_pct}%)   floor={floor_pn}%")

    # ── Threshold checks ──────────────────────────────────────────────────────
    threshold_failures = []
    if mfg_pct < floor_mfg - FILL_RATE_TOLERANCE:
        threshold_failures.append(
            f"  THRESHOLD FAIL — MFG dropped: {mfg_pct}% < floor {floor_mfg}%"
        )
    if pn_pct < floor_pn - FILL_RATE_TOLERANCE:
        threshold_failures.append(
            f"  THRESHOLD FAIL — PN dropped:  {pn_pct}% < floor {floor_pn}%"
        )

    if threshold_failures:
        for msg in threshold_failures:
            print(f"\n  !!! {msg}")

    # ── Row-level diff ────────────────────────────────────────────────────────
    regressions  = []
    improvements = []

    n_rows = min(len(df_current), len(df_golden))

    # Build a source-text column for context in diff output
    source_col = cfg["source_cols"][0] if cfg["source_cols"] else None

    for i in range(n_rows):
        row_cur = df_current.iloc[i]
        row_gld = df_golden.iloc[i]

        for col in compare_cols:
            cur_val = get_value(row_cur, col)
            gld_val = get_value(row_gld, col)

            if cur_val == gld_val:
                continue

            source_text = ''
            if source_col and source_col in df_current.columns:
                raw = df_current.iloc[i][source_col]
                source_text = str(raw)[:80] if pd.notna(raw) else ''

            entry = {
                "row": i + 2,       # 1-indexed + header = spreadsheet row
                "col": col,
                "was": gld_val,
                "now": cur_val,
                "source": source_text,
            }

            # Regression: had value, lost it; or changed to wrong value
            was_filled = bool(gld_val)
            now_filled = bool(cur_val)

            if was_filled and not now_filled:
                entry["type"] = "LOST"
                regressions.append(entry)
            elif was_filled and now_filled and cur_val != gld_val:
                entry["type"] = "CHANGED"
                regressions.append(entry)
            elif not was_filled and now_filled:
                entry["type"] = "GAINED"
                improvements.append(entry)

    # ── Print diff summary ────────────────────────────────────────────────────
    if regressions:
        print(f"\n  REGRESSIONS ({len(regressions)} rows):")
        for r in regressions[:20]:     # cap at 20 for readability
            print(f"    Row {r['row']:>5}  [{r['col']}]  {r['type']}")
            print(f"           was: {r['was']!r}")
            print(f"           now: {r['now']!r}")
            if r['source']:
                print(f"           src: {r['source']!r}")
        if len(regressions) > 20:
            print(f"    ... and {len(regressions) - 20} more regressions (see full log)")
    else:
        print(f"  No row regressions.")

    if improvements:
        print(f"\n  IMPROVEMENTS ({len(improvements)} rows gained data):")
        for r in improvements[:10]:
            print(f"    Row {r['row']:>5}  [{r['col']}]  {r['now']!r}  (was blank)")
        if len(improvements) > 10:
            print(f"    ... and {len(improvements) - 10} more improvements")

    # ── Pass/fail determination ───────────────────────────────────────────────
    passed = (not threshold_failures) and (not regressions)

    status = "PASS" if passed else "FAIL"
    print(f"\n  Status: {status}")

    return {
        "name": name,
        "passed": passed,
        "mfg_pct": mfg_pct,
        "pn_pct": pn_pct,
        "floor_mfg": floor_mfg,
        "floor_pn": floor_pn,
        "regressions": regressions,
        "improvements": improvements,
        "threshold_failures": threshold_failures,
        "total": total,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Ratchet update
# ─────────────────────────────────────────────────────────────────────────────

def ratchet_update(config: dict, results: list):
    """Raise thresholds to match any improvements. Never lowers."""
    updated = False
    for r in results:
        name = r["name"]
        old_mfg = config["thresholds"].get(name, {}).get("mfg", 0.0)
        old_pn  = config["thresholds"].get(name, {}).get("pn",  0.0)
        new_mfg = r["mfg_pct"]
        new_pn  = r["pn_pct"]

        if new_mfg > old_mfg or new_pn > old_pn:
            config["thresholds"][name] = {
                "mfg": max(old_mfg, new_mfg),
                "pn":  max(old_pn,  new_pn),
            }
            print(f"  Ratchet {name}: MFG {old_mfg}→{new_mfg}  PN {old_pn}→{new_pn}")
            updated = True

    if updated:
        with open(CONFIG_PATH, "w") as f:
            json.dump(config, f, indent=2)
        print(f"  Thresholds saved to {CONFIG_PATH.name}")
    else:
        print("  No improvements — thresholds unchanged.")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="MRO Parser regression gatekeeper")
    parser.add_argument("files", nargs="*",
                        help="File keys to test (default: all). E.g., wesco_empty electrical")
    parser.add_argument("--ratchet", action="store_true",
                        help="After passing, raise thresholds to new scores.")
    parser.add_argument("--quiet", action="store_true",
                        help="Suppress per-row diff details.")
    args = parser.parse_args()

    with open(CONFIG_PATH) as f:
        config = json.load(f)

    td_path = REPO_ROOT / "training_data.json"
    with open(td_path) as f:
        td = json.load(f)

    print()
    print("=" * 65)
    print(f"  MRO PARSER REGRESSION SUITE — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 65)

    # Determine which files to test
    all_files = list(config["files"].keys())
    target_files = args.files if args.files else all_files

    unknown = [f for f in target_files if f not in config["files"]]
    if unknown:
        print(f"ERROR: Unknown file keys: {unknown}")
        print(f"Valid keys: {all_files}")
        sys.exit(1)

    results = []
    for name in target_files:
        cfg          = config["files"][name]
        thresholds   = config["thresholds"]
        compare_cols = config["compare_cols"].get(name, [cfg["mfg_col"], cfg["pn_col"]])
        r = check_file(name, cfg, thresholds, compare_cols, td,
                       verbose=not args.quiet)
        results.append(r)

    # ── Final summary ─────────────────────────────────────────────────────────
    print()
    print("=" * 65)
    print("  SUMMARY")
    print("=" * 65)
    all_passed = True
    for r in results:
        status = "PASS" if r["passed"] else "FAIL"
        reg_count  = len(r["regressions"])
        impr_count = len(r["improvements"])
        print(f"  {r['name']:<22}  {status}  "
              f"MFG={r['mfg_pct']:5.1f}%  PN={r['pn_pct']:5.1f}%  "
              f"regress={reg_count}  gains={impr_count}")
        if not r["passed"]:
            all_passed = False

    print()
    if all_passed:
        print("  ALL CHECKS PASSED")
    else:
        print("  !! FAILURES DETECTED — see details above !!")

    # ── Ratchet ───────────────────────────────────────────────────────────────
    if args.ratchet:
        if all_passed:
            print()
            print("  Ratcheting thresholds...")
            ratchet_update(config, results)
        else:
            print()
            print("  Skipping ratchet — fix failures first.")

    print()
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
