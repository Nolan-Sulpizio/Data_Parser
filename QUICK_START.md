# Wesco MRO Parser — Quick Start

Welcome! This tool extracts MFG, Part Numbers, and SIM values from messy MRO Excel data in three steps.

---

## 🚀 Getting Started

### 1. Launch the App
- **Windows:** Double-click `WescoMROParser.exe`
- **macOS:** Double-click `WescoMROParser.app`

No installation required.

### 2. Drop Your File
Drag and drop your `.xlsx`, `.xls`, or `.csv` file onto the import zone (or click to browse).

The app scans the file instantly and highlights the best source column automatically.

### 3. Confirm and Parse
- Review the auto-selected source column — the smart preview shows 3–5 sample parsed rows so you can confirm the engine is reading the right data.
- Adjust the column selection if needed.
- Click **▶ PARSE FILE**.

That's it. Results save automatically to the same folder as your source file:
- `YourFile_parsed.xlsx` — cleaned data with MFG and PN columns appended
- `YourFile_QA.csv` — rows flagged for review (missing values, anomalies)

---

## ❓ Common Questions

**Q: What file types are supported?**
A: `.xlsx`, `.xls`, and `.csv`

**Q: Do I need internet access?**
A: No. This tool works 100% offline — no API keys, no cloud services.

**Q: Where do my output files go?**
A: Automatically saved to the same directory as your source file. Click **Open File Location** after parsing to go there directly.

**Q: The wrong column was auto-selected — what do I do?**
A: The column panel shows all relevant columns scored by the engine. Uncheck the auto-selected one and check the correct column. The parse preview will update instantly.

**Q: A manufacturer name is wrong or abbreviated (e.g., "SEW EURODR")?**
A: These are handled automatically by the normalization map. If you find one that isn't corrected, open a [Normalization Request](https://github.com/Nolan-Sulpizio/Data_Parser/issues/new?template=normalization_request.md).

---

## 💡 Tips for Best Results

- **Files with a "Short Text" or "Material Description" column** work out of the box — the engine recognizes these automatically.
- **Files with unnamed columns** — the engine peeks at row content and shows sample values so you can identify the right column visually.
- **Check the QA file** — rows flagged as `PN_NOT_IN_SOURCE` are worth reviewing manually. They indicate the engine extracted a value that wasn't clearly visible in the source text.
- **Supplier column** — if your file has a Supplier Name column, the engine auto-detects it and uses it as an MFG fallback for rows where the description alone isn't enough.

---

## 🔒 Privacy & Security

- All processing is **100% local** — no data leaves your machine
- No internet connection required
- No API keys or accounts needed

---

## 📧 Support

**Contact:** Nolan Sulpizio
- Microsoft Teams: @Nolan Sulpizio
- GitHub Issues: [github.com/Nolan-Sulpizio/Data_Parser/issues](https://github.com/Nolan-Sulpizio/Data_Parser/issues)

**Full documentation:** [README.md](README.md)

---

<div align="center">

v5.0.0 · Wesco International · Global Accounts

</div>
