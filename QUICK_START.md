# Wesco MRO Parser - Quick Start

Welcome to the Wesco MRO Parser! This tool helps you extract MFG, Part Numbers, and SIM values from messy Excel data.

## 🚀 Getting Started (3 Easy Steps)

### 1. Launch the App
- Double-click `WescoMROParser.exe`
- No installation required!

### 2. Import Your Excel File
- Drag and drop your `.xlsx` file onto the import zone
- Or click "Browse" to select a file

### 3. Pick a Template
In the sidebar, choose:
- **MFG + PN Extract** → Extract manufacturer and part numbers
- **Part Number Clean** → Validate existing part numbers
- **Build SIM Values** → Generate SIM from MFG + ITEM #

Then click **▶ Run Parser** and **💾 Export** when done!

---

## 📚 Need Help?

**Full Documentation:** https://github.com/Nolan-Sulpizio/Data_Parser/blob/main/README.md

**Common Questions:**

**Q: What file types are supported?**
A: `.xlsx`, `.xls`, and `.csv` files

**Q: Do I need internet access?**
A: No! This tool works 100% offline.

**Q: Where is my data saved?**
A: Your processing history is saved locally at:
   `C:\Users\[YourName]\.wesco_mro_parser\wesco_mro_history.db`

**Q: Can I save my instructions for reuse?**
A: Yes! After running the parser, click "⚙ Save Config" to save your instruction as a template.

**Q: The parser didn't find what I needed — can I write custom instructions?**
A: Absolutely! Instead of picking a template, type your own instruction:
   - "Pull MFG and PN from Material Description"
   - "Extract manufacturer from PO Text into column A"
   - "Generate SIM using pattern C"

---

## 🛠️ Quick Templates Explained

### MFG + PN Extract
- **What it does:** Pulls manufacturer and part number from description fields
- **Source columns:** Material Description, PO Text
- **Output columns:** MFG, PN, SIM (optional)
- **Best for:** Raw MRO data that needs full extraction

### Part Number Clean
- **What it does:** Validates and cleans existing Part Number fields
- **Source columns:** Part Number 1, Description, Notes
- **Output column:** Part Number 1 (cleaned)
- **Best for:** Files that already have part numbers but need validation

### Build SIM Values
- **What it does:** Creates SIM values from existing MFG and ITEM # columns
- **Source columns:** MFG, ITEM #
- **Output column:** SIM
- **Best for:** BOM files missing SIM values

---

## 📧 Support

**Contact:** Nolan Sulpizio
- Microsoft Teams: @Nolan Sulpizio
- Slack: Global Accounts channel
- GitHub Issues: https://github.com/Nolan-Sulpizio/Data_Parser/issues

**Report a Bug:** https://github.com/Nolan-Sulpizio/Data_Parser/issues/new?template=bug_report.md

---

## ✨ Tips for Best Results

1. **Use descriptive column names** — The parser looks for columns like "Material Description", "PO Text", etc.
2. **Check the preview** — Always review the Output preview before exporting
3. **Review QA Issues** — If the app finds issues, it will create a separate "QA Issues.xlsx" file
4. **Save your configs** — If you process similar files regularly, save your instruction as a template

---

## 🔒 Privacy & Security

- All processing happens **100% offline** on your machine
- No data is sent to the internet
- No API keys or cloud services required
- All files stay on your local computer

---

<div align="center">

**Built with ❤️ for the Wesco Global Accounts Team**

v2.0.0 • Wesco International

</div>
