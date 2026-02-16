# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 2.0.x   | :white_check_mark: |
| 1.0.x   | :x:                |

## Security Considerations

### Data Privacy

This application is designed for **internal Wesco use only** and processes potentially sensitive MRO data:

- ✅ **100% Offline** — No internet connectivity required
- ✅ **No External APIs** — All processing happens locally
- ✅ **Local Storage Only** — Data stored in `~/.wesco_mro_parser/` on user's machine
- ✅ **No Telemetry** — No usage data collected or transmitted

### Data Handling Best Practices

When using this tool:

1. **Don't commit Excel files** — `.gitignore` excludes `.xlsx`/`.xls`/`.csv` files
2. **Don't share processing history DB** — SQLite database contains file names and stats
3. **Review QA reports before sharing** — May contain client-specific data
4. **Don't expose output files publicly** — Cleaned data may still contain sensitive info

### Known Limitations

- **No input validation on Excel cell content** — Assumes data is non-malicious
- **No encryption of local database** — History DB stored in plaintext SQLite
- **No user authentication** — Anyone with access to the `.exe` can run it

These are acceptable for internal use but should be considered if expanding scope.

## Reporting a Vulnerability

If you discover a security vulnerability in this application:

### Internal Reporting (Wesco Employees)

1. **Do NOT open a public GitHub issue**
2. Contact **Nolan Sulpizio** directly via:
   - Microsoft Teams (preferred)
   - Email (Wesco corporate email)
   - Slack (Global Accounts channel - DM)

3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if you have one)

### Response Timeline

- **Initial Response:** Within 2 business days
- **Status Update:** Within 1 week
- **Resolution Target:** Based on severity
  - Critical: 1-2 weeks
  - High: 2-4 weeks
  - Medium: 4-8 weeks
  - Low: Next minor release

### After Resolution

Once fixed:
- Patch will be released as a minor/patch version
- Fix will be documented in `CHANGELOG.md`
- Reporter will be credited (if desired)

## Security Best Practices for Users

### Before Installing
- Verify the `.exe` came from an official Wesco source
- Check file hash if provided
- Don't run untrusted builds

### During Use
- Only import Excel files from trusted Wesco sources
- Review output before sharing externally
- Don't store sensitive files in the app's working directory

### After Use
- Exported files may contain client data — handle appropriately
- Processing history contains file names — clear if sharing your machine

## Compliance

This tool is designed to comply with:
- Wesco Information Security Policy
- Internal data handling guidelines
- GDPR considerations (no PII collection)

For compliance questions, contact your manager or the Wesco IT Security team.

---

**Last Updated:** 2026-02-16
**Security Contact:** Nolan Sulpizio (Global Accounts)
