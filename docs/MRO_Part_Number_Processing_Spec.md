# Part Number Extraction & Cleansing — Implementation Playbook

**Owner:** Sulpizio, Nolan  
**Last updated:** 2026-02-16

---

## 1) Source Sheet & Key Columns

**Relevant columns (common headers):**
- `Manufacturer 1` (Column H)
- `Part Number 1` (Column I — target to fill/clean)
- `Manufacturer 2`, `Part Number 2/3/4`
- Text/Context fields: `MATERIAL DESCRIPTION`, `MATERIAL DESCRIPTION 2..5`, `INFORECTXT1/2`, `Notes`

> **A "correct" PN** is a short, structured alphanumeric token often containing dashes `/` and `-` with **no spaces**. Must contain **at least one letter** and **at least one digit**.

---

## 2) Processing Steps

### A. Initial Fill (Heuristic Extraction)
1. For blank `Part Number 1` rows, search across description/notes fields for candidate tokens.
2. Filter out internal/legacy inventory codes by prefix (`N0`, `N7`, `CNVL`, `T7`, etc.).
3. Prioritize candidates near cues: `MFR PART NUMBER`, `MFR NUMBER`, `MFG NUMBER`.
4. Write best candidate to `Part Number 1`.

### B. Cleaning Pass (Format Enforcement)
- Strict PN format: uppercase alphanumeric with optional `-` or `/`, **no spaces**.
- Remove clearly descriptive entries (`500W`, `12V`, phrases with spaces).

### C. Reprocessing Pass (Stricter for Lamps/Specs)
- Require at least one slash or dash in token to prefer structured PNs.
- Example: `500W` → `500T3Q/CL/130V`, `12V` → `50MR16T/SP10C/EXT12V`

### D. Secondary Part Numbers
- Check `Part Number 2/3/4` for valid PNs, append to primary separated by `, `.

---

## 3) Rules & Patterns

### Valid PN Pattern
```regex
^[A-Z0-9]+(?:[\-/][A-Z0-9]+)*$
```

### Candidate Extraction (prefer structured tokens)
```regex
\b([A-Z0-9]+(?:[\-/][A-Z0-9]+)+)\b
```

### Excluded Internal/Legacy Prefixes
```
N0, N7, N71, N72, N73, CNVL, T7, T71, T72, T76, T77, T78, T79
```

### Confidence Boosters
- Structural cues: `MFR PART NUMBER`, `MFR NUMBER`, `MFG NUMBER`
- Brand cues: manufacturer names in-row (EATON, EDWARDS, SIEMENS, TURCK, etc.)
- Tie-breaker: prefer **longest structured** token

---

## 4) Quality Gates
1. Every PN matches `^[A-Z0-9]+(?:[\-/][A-Z0-9]+)*$`
2. No spaces, no pure words — reject tokens without both digits & letters
3. Prefix blacklist enforced
4. Spot audit: PNs plausible for manufacturer and item type
5. Duplicate removal when combining secondaries

---

## 5) Known Edge Cases
- Some catalog numbers include spaces legitimately (narrow whitelist per vendor if needed)
- Manufacturer strings may reference alternates or cross-refs
- Mixed-case inputs normalized to **UPPERCASE**

---

*Reference implementation: `engine/parser_core.py` → `pipeline_part_number()`*
