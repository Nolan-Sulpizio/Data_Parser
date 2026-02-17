# Session Log — Wesco MRO Parser

This file records development sessions chronologically. Each entry captures work completed, decisions made, and priorities for the next session. Maintained for context continuity across sessions.

---

## Session: 2026-02-17

### Session Summary
Implemented 7 targeted precision refinements to the Wesco MRO Parser engine (v3.0.0 → v3.1.0), driven by production testing against a real 2,684-row WESCO.xlsx file. The fixes address specific false-positive and false-negative failure patterns identified in that dataset, yielding measurable accuracy improvements without regression on the labeled Data Set 1 benchmark.

### Goals Addressed
- Primary: Eliminate GE substring false positives (201 affected rows) — COMPLETED
- Primary: Reduce descriptor token MFG captures (75+ affected rows) — COMPLETED
- Primary: Reject descriptor-pattern tokens from PN output (23 affected rows) — COMPLETED
- Primary: Support McMaster dash-separated catalog format (8 affected rows) — COMPLETED
- Primary: Graduate heuristic confidence scoring to reduce noise — COMPLETED
- Primary: Clean `training_data.json` of false manufacturer entries — COMPLETED
- Primary: Bump version to v3.1.0 and update CHANGELOG — COMPLETED

### Work Completed
- [x] Fix 1 — Word-boundary regex in `extract_mfg_known()` (eliminates 201 GE false positives)
- [x] Fix 2 — `MFG_BLOCKLIST` set (35+ tokens) added to `sanitize_mfg()`; extended `DESCRIPTOR_KEYWORDS`
- [x] Fix 3 — 11 normalization entries added; 21 real manufacturers added to `KNOWN_MANUFACTURERS`
- [x] Fix 4 — `PN_DESCRIPTOR_PATTERNS` regex rejecting NUMBER-DESCRIPTOR tokens (3-WAY, 4-BOLT, etc.)
- [x] Fix 5 — New `extract_pn_dash_catalog()` strategy for McMaster-style `CATALOG# - Description` rows
- [x] Fix 6 — `_score_heuristic_pn()` replaces flat 0.35 confidence with graduated 0.10–0.65 scoring
- [x] Fix 7 — Cleaned `training_data.json`: removed 18 false manufacturer entries, added 18 real ones
- [x] Updated `engine/file_profiler.py` with `dash_catalog` strategy weights for all archetypes
- [x] Bumped `engine/__init__.py` version from 3.0.0 to 3.1.0
- [x] Added v3.1.0 entry to `CHANGELOG.md`
- [x] Created `tests/test_v31_refinement.py` — 97-test suite covering all 7 fixes (97/97 passed)

### Code Changes

| File | Change Type | Description |
|------|-------------|-------------|
| `engine/parser_core.py` | Modified | All 7 precision fixes: word-boundary regex, MFG_BLOCKLIST, normalization additions, PN_DESCRIPTOR_PATTERNS, dash_catalog strategy, graduated heuristic confidence |
| `engine/file_profiler.py` | Modified | Added `dash_catalog` key to `STRATEGY_WEIGHTS` for all four archetypes |
| `engine/__init__.py` | Modified | Version bump: `3.0.0` → `3.1.0` |
| `training_data.json` | Modified | Removed 18 false manufacturer entries; added 18 real manufacturers; removed 7 bad normalization entries |
| `CHANGELOG.md` | Modified | Added v3.1.0 section with full fix documentation and test results |
| `tests/test_v31_refinement.py` | Created | 97-test suite covering all 7 fixes and regression benchmarks |

### Decisions Made

- **Word-boundary matching is now the universal standard for `extract_mfg_known()`**: Used `(?<![A-Z0-9])NAME(?![A-Z0-9])` regex rather than `name in text` substring matching. This was implemented as a general change, not a GE-specific patch, so all short manufacturer names (ABB, SKF, etc.) benefit. Rationale: the substring approach was fundamentally wrong for short tokens — the regex is the correct solution.

- **`MFG_BLOCKLIST` overridden by `KNOWN_MANUFACTURERS`**: The blocklist check is `if x in MFG_BLOCKLIST and x not in KNOWN_MANUFACTURERS`. This means adding a token to `KNOWN_MANUFACTURERS` is the explicit override mechanism for any future edge case where a blocklist token is also a valid manufacturer name. Rationale: keeps the override path unambiguous and avoids hidden conflicts.

- **Normalization entries added in-code, not solely in `training_data.json`**: Entries like `SEW EURODR → SEW EURODRIVE` and `ALN BRDLY → ALLEN BRADLEY` are hardcoded in `parser_core.py` in addition to any training data entries. Rationale: `training_data.json` may be stale or missing in distribution builds; in-code entries are always reliable.

- **Graduated heuristic confidence range capped at 0.65**: The maximum graduated score (0.65) stays below the `label` source confidence (0.95) and `known_mfg` confidence (0.85). Rationale: heuristic extractions should never outcompete higher-confidence sources even when the token looks strong.

- **`tests/test_v31_refinement.py` covers regression benchmarks inline**: The test file includes accuracy thresholds for Data Set 1 (MFG ≥ 95%, PN ≥ 95%) as part of the 97-test suite. Rationale: prevents any future fix from silently regressing benchmark accuracy.

### Issues and Blockers
- [ ] WESCO.xlsx MFG fill rate is 41.7% (1,120 / 2,684) — still room to improve. Status: Open, not a blocker.
- [ ] WESCO.xlsx PN fill rate is 50.6% (1,358 / 2,684) — meaningful blank-row volume remains. Status: Open, not a blocker.
- [ ] `tests/test_v3_upgrades.py` and `tests/test_engine_hardening.py` (v3.0.0 tests) were not run this session to confirm no regressions. Status: Needs verification next session.
- [ ] Session changes have not been committed to git — the branch is dirty with all 6 modified/created files. Status: Commit pending.

### Technical Notes

- The GE fix (Fix 1) was the highest-impact single change: 201 rows were producing `MFG=GE` because "GE" appeared as a substring in words like GEARED, EMERGENCY, SQUEEGEE, GEARBOX, GAUGE, LEGEND. The regex lookbehind/lookahead approach is O(n) and has no meaningful performance cost.

- `PN_DESCRIPTOR_PATTERNS` (Fix 4) uses the pattern `r'^\d+-(WAY|BOLT|POINT|WIRE|POLE|PORT|POS|SPC|HOUR|STAGE|GANG|LINE|DIO|DI/O)$'` (or similar) to catch the NUMBER-DESCRIPTOR format. These tokens look like part numbers but are product attribute descriptions.

- `extract_pn_dash_catalog()` (Fix 5) targets the specific McMaster-Carr format where the full cell value is `ALPHANUMERIC_CODE - Description text`. The strategy gives confidence 0.80, which is high enough to win the multi-strategy best-pick competition against heuristic matches.

- `_score_heuristic_pn()` (Fix 6) rescued approximately 778 previously-below-threshold heuristic rows that contained genuinely long alphanumeric strings (e.g., `3AXD50000731121`). These were being discarded at the flat 0.35 threshold but are high-quality extraction targets.

- The `training_data.json` cleanup (Fix 7) is a one-time correction. Tokens like `AB`, `TE`, `CTRL`, `DISCONNECT`, `FIBRE OPTIC` had accumulated in `known_manufacturers` from prior incremental learning sessions and were producing false MFG extractions at scale.

- The git log shows the last committed version was v2.1.2. All v3.x work (v3.0.0, v2.2.0, v2.0.4 patches, and now v3.1.0) appears to be uncommitted working-tree changes as of this session.

### Next Session Priorities

1. **Run full regression suite** — execute `tests/test_v3_upgrades.py` and `tests/test_engine_hardening.py` to confirm v3.0.0 tests still pass under v3.1.0 changes. Then run `tests/test_v31_refinement.py` as the canonical v3.1.0 gate.
2. **Commit v3.1.0** — stage and commit all modified files (`engine/parser_core.py`, `engine/file_profiler.py`, `engine/__init__.py`, `training_data.json`, `CHANGELOG.md`, `tests/test_v31_refinement.py`) with a `Release v3.1.0` commit message.
3. **Investigate WESCO.xlsx fill-rate gap** — the 41.7% MFG and 50.6% PN fill rates suggest a large volume of rows where no extraction strategy fires. Profiling which description patterns are in the blank-output rows would identify the next high-yield fix (candidate: BRUNO FOLCIERI 316-row supplier cluster and AMUT 197-row cluster).
4. **Supplier-name-to-manufacturer mapping** — rows where the `Supplier Name` column contains a real manufacturer name (BRUNO FOLCIERI, AMUT) but the description doesn't yield an extraction. The supplier fallback in v2.2.0 only applies when MFG extraction fails; verify these rows are actually reaching that fallback and that BRUNO FOLCIERI / AMUT are in the distributor exclusion list correctly.
5. **Confirm `app.py` still launches cleanly** — the engine changes should be transparent to the GUI, but a smoke test (`python app.py`) is worth doing before distribution.

### Open Questions

- Are BRUNO FOLCIERI and AMUT currently in the distributor exclusion list, or are they in `KNOWN_MANUFACTURERS` as manufacturer names? If in `KNOWN_MANUFACTURERS`, the supplier fallback won't trigger for those rows — need to verify the code path.
- Should `tests/test_v31_refinement.py` be integrated into `run_tests.sh` so it runs automatically as part of `./run_tests.sh full`?
- Is there a target fill-rate threshold for WESCO.xlsx production data, or is the accuracy benchmark (≥95% on labeled Data Set 1) the only formal success criterion?

### Session Context Tags
`#engine` `#precision-refinement` `#v3.1.0` `#parser_core` `#false-positives` `#training-data` `#production-testing`
