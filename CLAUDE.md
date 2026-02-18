# CLAUDE.md — Wesco MRO Parser

**Status:** Production-ready, v4.0.0. Wesco branding complete.
**Owner:** Nolan Sulpizio — Wesco International, Global Accounts
**Constraint:** 100% offline. No API keys, no internet. Mac + Windows.

---

## What This App Does

Parses MRO Excel data to extract **Manufacturer (MFG)**, **Part Number (PN)**, and **SIM** values from unstructured product descriptions. Rule-based engine with training data — no LLM at runtime.

---

## Key Files

| File | Purpose |
|------|---------|
| `app.py` | Main GUI (CustomTkinter), Wesco-branded, ~1,600 lines |
| `engine/parser_core.py` | Core extraction logic — MFG/PN pipelines, confidence scoring |
| `engine/schema_classifier.py` | Detects file schema (SAP_SHORT_TEXT, GENERIC, etc.) |
| `engine/file_profiler.py` | Column analysis & file archetype detection |
| `engine/column_mapper.py` | Column mapping, preprocessing, `suggest_columns()` |
| `engine/instruction_parser.py` | Parses free-text instructions (secondary input path) |
| `engine/history_db.py` | SQLite job history — stored in `~/.wesco_mro_parser/` |
| `engine/training.py` | Training data ingestion utilities |
| `training_data.json` | `mfg_normalization` map + `known_manufacturers` list |

---

## Engine Architecture (v4.0.0)

**Primary input:** Column-first selector — user picks source columns via `suggest_columns()`, zero-ambiguity routing in `_execute_pipeline()`.
**Secondary input:** Free-text instructions via `instruction_parser.py` (Advanced/collapsible).

**MFG/PN pipeline** (`pipeline_mfg_pn()` in `parser_core.py`):
- Multi-strategy extraction with confidence scoring
- Schema detection: `SAP_SHORT_TEXT` for WESCO files (Short Text + Supplier Name columns)
- File archetype: `MIXED` for standard WESCO data
- Confidence threshold: ~0.412 for SAP_SHORT_TEXT+MIXED

**NORMALIZE_MFG** overrides (in `parser_core.py`): handles SAP short-text truncations.
Examples: `SEW EURODR` → `SEW EURODRIVE`, `BRU FOLC` → `BRUNO FOLCIERI`

**Wesco benchmark (2,684 rows):** MFG 60.5%, PN 59.3%. Zero hallucinations, zero spec/plant code leaks.

---

## Testing

```bash
./run_tests.sh          # quick smoke tests
./run_tests.sh full     # full 6-phase validation
```

Test files in `tests/`. Test data in `test_data/` (gitignored — add your own files).
Copy `test_config.example.json` → `test_config.json` and set local paths before running.
See `docs/TESTING_GUIDE.md` for full documentation.

---

## Training Data Rules

`training_data.json` contains:
- `mfg_normalization` — abbreviation → full manufacturer name
- `known_manufacturers` — validated manufacturer list

**Critical validation gate:** Never add a key to `mfg_normalization` that matches any entry in the `DISTRIBUTORS` set in `parser_core.py`. The v4.0.0 patch removed 8 contaminated entries (GRAINGER → FEDERAL SIGNAL, generic descriptors, spec phrases) caused by this exact failure mode.

---

## Common Failure Patterns

| Symptom | Cause | Fix |
|---------|-------|-----|
| Hallucinated AB/TE/GE as MFG | Toxic training data | Audit `mfg_normalization` |
| `N141` / `N041` appearing as PN | Plant column in `source_cols` | Check `_is_plant_code()` |
| Truncated MFG names (SEW EURODR, BRU FOLC) | SAP 18-char limit | Add to `NORMALIZE_MFG` |
| ABB drive PNs missing (3AXD*) | Pure alphanumeric, no separator | `extract_pn_embedded_code()` handles this |
| Distributor name as MFG | Key in both `mfg_normalization` and `DISTRIBUTORS` | Remove from normalization map |

---

## What NOT to Change

- **Engine logic** (`parser_core.py`, `instruction_parser.py`) — stable and tested
- **Parsing pipelines** (MFG/PN, Part Number, SIM) — specs in `docs/`

---

## Brand Colors (Wesco)

```
Primary Green:   #009639   Dark Green:  #006B2D   Hover:    #4CAF50
Background:      #0D1117   Card:        #161B22   Input:    #21262D
Text:            #F0F6FC   Secondary:   #8B949E   Muted:    #6E7681
Border:          #30363D   Warning:     #D29922   Error:    #F85149
```

---

## Build

```bash
./build_mac.sh        # → WescoMROParser.app
build_windows.bat     # → WescoMROParser.exe
```

Icons: `assets/icon.icns` (macOS), `assets/icon.ico` (Windows).

---

## Docs

| File | Content |
|------|---------|
| `MFG_PN_Parsing_Agent_Spec.md` | MFG+PN pipeline requirements |
| `MRO_Part_Number_Processing_Spec.md` | Part number pipeline spec |
| `SIM_BOM_Automation_Spec.md` | SIM extraction spec |
| `TESTING_GUIDE.md` | Full test documentation |
| `ENGINE_REFINEMENT_v3.2.md` | Historical engine refinements |
| `UI_PIPELINE_FIX.md` | Historical UI/pipeline notes |
| `GAMMA_PRESENTATION_METRICS.md` | Benchmarks for presentations |
