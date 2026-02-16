# CLAUDE.md — Wesco MRO Data Parser (Rebrand & Polish)

## Project Context
This is an existing desktop application (`mro-parser/`) that parses MRO Excel data — extracting Manufacturer (MFG), Part Number (PN), and SIM values from unstructured product descriptions. The app was prototyped under "Clean Plate" branding but is actually a **Wesco International** internal tool built by Nolan Sulpizio on the Global Accounts team.

**The app already works.** The parsing engine, instruction parser, history DB, and GUI are all functional. This task is to **rebrand, polish, and prepare for team distribution**.

## Primary Objectives

### 1. REBRAND: Clean Plate → Wesco
Replace ALL Clean Plate references with Wesco branding:

**Brand Colors (from Wesco corporate identity):**
- Primary Green: `#009639` (Wesco's signature green)
- Dark Green: `#006B2D`
- Light Green: `#4CAF50` (hover/accent)
- Dark Background: `#0D1117` (modern dark theme)
- Card Background: `#161B22`
- Input Background: `#21262D`
- Text Primary: `#F0F6FC`
- Text Secondary: `#8B949E`
- Text Muted: `#6E7681`
- Border: `#30363D`
- Warning: `#D29922`
- Error: `#F85149`

**Naming:**
- App title: `"Wesco MRO Parser"` (window title bar)
- Sidebar logo text: `"WESCO"` with subtitle `"MRO Data Parser"`
- Logo icon: Use a bold green "W" character or the Unicode `◆` in Wesco green
- Internal class name: `WescoMROParser` (rename from `CleanPlateParser`)
- Database file: `wesco_mro_history.db` (rename from `clean_plate_history.db`)
- App data directory: `~/.wesco_mro_parser/` (rename from `~/.clean_plate_parser/`)
- Version footer: `"v2.0.0 • Wesco International • Global Accounts"`
- Build output name: `"WescoMROParser"` (for pyinstaller)
- README title: `"Wesco MRO Parser"`

**Files to update:**
- `app.py` — all BRAND colors, class names, text labels, window title
- `engine/__init__.py` — module docstring
- `engine/history_db.py` — DB_NAME, app directory path
- `build_windows.bat` — exe name, echo messages
- `README.md` — all references
- `requirements.txt` — no changes needed

### 2. UI IMPROVEMENTS
While rebranding, make these UI upgrades:

**Sidebar:**
- Replace the `◉` logo with a bold styled "W" in Wesco green (`#009639`)
- Make Quick Templates more visually distinct with small icons/emojis
- Add a "Help" or "About" section at the bottom of sidebar

**Import Zone:**
- Add a dashed border style to the drop zone (use `border_width=2`)
- Show column preview as pills/tags after file load
- Better visual feedback on hover (subtle background shift)

**Instruction Input:**
- Add a small "?" tooltip or hint text explaining what instructions are supported
- Show the interpretation feedback in a more styled badge/chip format
- Placeholder text should read: `"Describe what you need, e.g. 'Extract MFG and PN from Material Description into columns A and B'"`

**Preview Table:**
- Highlight changed/filled cells in light green when showing Output view
- Add row count badge in the preview header

**Status Bar:**
- Use color-coded status indicators (green dot = ready, yellow = processing, red = error)
- Show elapsed processing time

### 3. ENGINE — NO CHANGES NEEDED
The parsing engine (`engine/parser_core.py`, `engine/instruction_parser.py`) is stable and tested. **Do not modify the parsing logic.** Only update branding strings if any exist in the engine files.

### 4. DISTRIBUTION PREP
**Windows .exe build:**
- Update `build_windows.bat` with Wesco naming
- Ensure pyinstaller bundles all customtkinter assets
- The .exe should be named `WescoMROParser.exe`

**macOS support (new):**
- Add a `build_mac.sh` script that uses pyinstaller on macOS
- Output should be `WescoMROParser.app` or a standalone binary

**Add an app icon:**
- Create a simple `.ico` file (Windows) and `.icns` file (macOS) 
- Use a green "W" on dark background as the icon
- Reference in pyinstaller with `--icon=assets/icon.ico`
- Create an `assets/` directory for icon files

### 5. ADDITIONAL FEATURES (if time permits)
- **Batch mode:** Allow importing multiple Excel files and processing them sequentially
- **Config export/import:** Let users export their saved configs as JSON to share with teammates
- **Dark/Light mode toggle:** Add a theme switch in the sidebar (default: dark)

## File Structure (Target)
```
mro-parser/
├── CLAUDE.md                      ← this file
├── app.py                         ← Main UI (REBRAND HERE)
├── engine/
│   ├── __init__.py                ← Update version/docstring
│   ├── parser_core.py             ← DO NOT MODIFY LOGIC
│   ├── instruction_parser.py      ← DO NOT MODIFY LOGIC  
│   └── history_db.py              ← Rename DB paths
├── assets/
│   ├── icon.ico                   ← Windows icon (green W)
│   └── icon.icns                  ← macOS icon (green W)
├── build_windows.bat              ← Updated for Wesco
├── build_mac.sh                   ← NEW - macOS build script
├── requirements.txt
└── README.md                      ← Updated for Wesco
```

## Implementation Order
1. Create `assets/` directory and generate icon files
2. Update `app.py` — rebrand all colors, labels, class names
3. Update `engine/history_db.py` — rename DB paths
4. Update `engine/__init__.py` — version bump and docstring
5. Update `build_windows.bat` — Wesco naming
6. Create `build_mac.sh` — new macOS build script
7. Update `README.md` — comprehensive Wesco documentation
8. Apply UI improvements (sidebar, import zone, status bar)
9. Test: `python app.py` should launch with full Wesco branding
10. Build: run build script to generate distributable

## Testing
After all changes, verify:
- [ ] App launches without errors (`python app.py`)
- [ ] Window title says "Wesco MRO Parser"
- [ ] Sidebar shows green "W" logo and "WESCO" text
- [ ] All three Quick Templates work (MFG+PN, Part Number, SIM)
- [ ] File import works (.xlsx, .csv)
- [ ] Processing runs and shows results in preview
- [ ] Export saves cleaned workbook
- [ ] History view shows past jobs
- [ ] No references to "Clean Plate" anywhere in the UI
- [ ] Build script produces `WescoMROParser.exe` (Windows) or equivalent

## Important Notes
- This is an INTERNAL Wesco tool, not a commercial product
- Keep it 100% offline — no API keys, no internet required
- The three parsing pipelines (MFG/PN, Part Number, SIM) come from specs written by Nolan Sulpizio and should not be modified
- Target users are the Global Accounts BDA team — keep the UI simple and clear
- Mac + Windows support required since the team uses both platforms
