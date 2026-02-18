#!/usr/bin/env python3
"""
create_golden_snapshots.py — Generate v4.0.3 baseline golden outputs.

Run this ONCE to capture the current engine output as ground truth.
After running, commit tests/golden/ to git. Never re-run unless you
intentionally want to reset the baseline (e.g., after a major version bump).

Usage:
    python tests/create_golden_snapshots.py
"""

import sys
import json
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

import pandas as pd
from engine.parser_core import pipeline_mfg_pn
from engine.column_mapper import map_columns

CONFIG_PATH = REPO_ROOT / "tests" / "regression_config.json"


def count_filled(series: pd.Series) -> int:
    return int(((series.notna()) & (series.astype(str).str.strip() != '')).sum())


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


def main():
    with open(CONFIG_PATH) as f:
        config = json.load(f)

    td_path = REPO_ROOT / "training_data.json"
    with open(td_path) as f:
        td = json.load(f)

    golden_dir = REPO_ROOT / "tests" / "golden"
    golden_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 65)
    print("  CREATE GOLDEN SNAPSHOTS — MRO Parser Engine v4.0.3")
    print("=" * 65)

    summary = {}

    for name, cfg in config["files"].items():
        golden_path = REPO_ROOT / cfg["golden"]
        print(f"\n[{name}]")
        print(f"  Input:  {cfg['input']}")
        print(f"  Golden: {cfg['golden']}")

        df_out = run_engine(cfg, td)

        mfg_col = cfg["mfg_col"]
        pn_col  = cfg["pn_col"]
        total   = len(df_out)
        mfg_n   = count_filled(df_out[mfg_col])
        pn_n    = count_filled(df_out[pn_col])
        mfg_pct = round(mfg_n / total * 100, 1)
        pn_pct  = round(pn_n  / total * 100, 1)

        df_out.to_excel(golden_path, index=False, engine='openpyxl')
        print(f"  Rows:   {total}")
        print(f"  MFG:    {mfg_n}/{total} ({mfg_pct}%)")
        print(f"  PN:     {pn_n}/{total} ({pn_pct}%)")
        print(f"  Saved → {golden_path.name}")

        summary[name] = {"mfg": mfg_pct, "pn": pn_pct, "rows": total}

    # Update thresholds in config to match actual output
    config["thresholds"] = {
        name: {"mfg": vals["mfg"], "pn": vals["pn"]}
        for name, vals in summary.items()
    }
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)
    print(f"\n  Thresholds updated in {CONFIG_PATH.name}")

    print("\n" + "=" * 65)
    print("  GOLDEN SNAPSHOTS CREATED — commit tests/golden/ to git")
    print("=" * 65)
    print()
    for name, vals in summary.items():
        print(f"  {name:<22}  MFG={vals['mfg']:5.1f}%  PN={vals['pn']:5.1f}%  ({vals['rows']} rows)")
    print()


if __name__ == "__main__":
    main()
