# Contributing to Wesco MRO Data Parser

## Team Guidelines

This is an internal Wesco tool maintained by the Global Accounts team. Contributions are welcome from any team member.

### Getting Started

1. **Clone the repo:**
   ```bash
   git clone https://github.com/Nolan-Sulpizio/Data_Parser.git
   cd Data_Parser
   ```

2. **Set up your environment:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the app:**
   ```bash
   python app.py
   ```

### Making Changes

**Branch naming:**
- `feature/<description>` — new capabilities
- `fix/<description>` — bug fixes
- `docs/<description>` — documentation updates

**Workflow:**
1. Create a branch from `main`
2. Make your changes
3. Test locally (`python app.py`)
4. Push and open a Pull Request
5. Tag Nolan Sulpizio for review

### Code Structure

| File | Purpose | Modify? |
|------|---------|---------|
| `app.py` | GUI layer — layout, interactions, theming | ✅ Yes |
| `engine/parser_core.py` | Parsing logic — extraction, normalization, QA | ⚠️ Carefully |
| `engine/instruction_parser.py` | NL instruction → pipeline config | ⚠️ Carefully |
| `engine/history_db.py` | SQLite storage for history/configs | ✅ Yes |

> **Important:** Changes to `parser_core.py` affect all parsing output. Test against known-good Excel files before merging.

### Adding a New Manufacturer to the Normalization Map

1. Open `engine/parser_core.py`
2. Add the entry to the `NORMALIZE_MFG` dictionary:
   ```python
   NORMALIZE_MFG = {
       ...
       'NEW_ABBREV': 'CANONICAL NAME',
   }
   ```
3. If it's a new distributor, add to the `DISTRIBUTORS` set instead

### Adding a New QA Rule

1. Open `engine/parser_core.py`
2. Add a tuple to the `QA_RULES` list:
   ```python
   ('rule_key', lambda r, mc: <your_condition>, 'Human-readable description'),
   ```

### Testing

Currently testing is manual:
1. Import a known Excel file
2. Run each of the 3 pipelines
3. Verify output matches expected results
4. Check QA report for false positives

### Questions?

Reach out to **Nolan Sulpizio** on Teams or via the Global Accounts channel.
