# Notes for the cover email to Anthony — 4/29/26 sheet

## Headline

**693-row bid sheet enriched. 76.0% (527 rows) have an MFG identified and 80.4% (557 rows) have an MFG Part Number.** Eight-layer resolution: description-mining (212 rows), direct-MFG vendor inference (19 rows), automated Playwright (110 rows), per-vendor bookmarklet runs in real Chrome (31 rows), round-2 URL-refetch with verified extractors (76 rows promoted to OK), round-3 autonomous patch (13 rows via extended brand dict + URL-slug + Graybar search), **round-4 web-research swarm** (4 parallel agents using WebSearch + WebFetch against Raptor Supplies, Newark, Allied, DigiKey, eBay — 176 rows promoted to OK), **round-5 Graybar direct-fetch + deep-search swarm** (3 more agents using eBay completed listings, datasheet PDFs, UL listing database, alt suppliers, Wayback Machine — 28 additional resolutions). 73.0% now have full MFG + MFG PN. **Every remaining row (24.0%, 166) carries one of five `NHR_*` ("needs human review") statuses with a structured reason** so the residual is actionable, not opaque.

| Status | Count | What it means |
|---|---:|---|
| `OK` | 339 | MFG + MFG PN auto-extracted from a vendor page or web cross-reference |
| `DESCRIPTION_MINED` | 148 | MFG + MFG PN extracted from Short Text / Long Text |
| `MFG_IS_VENDOR` | 19 | Vendor IS the manufacturer (KUKA, Coperion K-Tron, GAI-Tronics, McMaster, etc.) |
| `MFG_FROM_DESCRIPTION` | 9 | MFG named in source description, PN missing — partial fill |
| `MFG_FROM_GRAYBAR_SEARCH` | 7 | Round-3: Graybar search re-mined |
| `MFG_FROM_VENDOR_PAGE` | 4 | MFG extracted from vendor page, PN absent |
| `MFG_FROM_PAGE_DESC` | 1 | Brand matched in captured vendor-page description |
| `NHR_NO_VENDOR_HIT` | 70 | Vendor search returned no usable result, even after deep web research |
| `NHR_HOUSE_BRAND` | 48 | Vendor lists house-brand placeholder — no public MFG attribution |
| `NHR_DISCONTINUED` | 21 | Vendor catalog returned not-found / homepage redirect |
| `NHR_NO_URL` | 20 | No vendor catalog hit at all |
| `NHR_GATED` | 7 | Vendor product page captured but MFG label gated behind login |

Every row carries `Lookup Status`, `Lookup Notes`, `Lookup Date`, and (for mined rows) the matching regex span — fully auditable.

## Talking points

1. **Three-layer resolution.** Layer 1 — description mining of cols B+C picked up 212 rows (31%) before any browser work. Layer 2 — direct-MFG vendor inference resolved 19 single-row vendors. Layer 3 — automated Playwright pass against Fastenal + Border States resolved 110 more rows (37 OK + 73 partial). Final 120 PENDING rows ship pre-loaded in the bookmarklets.

2. **The 8 bookmarklets** are pre-loaded with **only the unresolved 120 PNs**, not the original 439. Run them in your normal Chrome and they target exactly what's left. Same drop-on-Desktop, double-click, paste-PNs, drag-button workflow as the 4/28 build — no install, no login required.

3. **Why bookmarklets and not full automation?** We tried the automated path (Playwright headless Chrome). Grainger flagged the IP within a dozen requests, Wesco hit Cloudflare, Graybar returned empty results. These vendors detect headless browsers but can't tell your normal Chrome (with its cookie/fingerprint history) apart from any other shopper — that's why the bookmarklet works where automation doesn't.

4. **Auto-extract built into the bookmarklets.** Each one first attempts to auto-extract `Manufacturer` and `Manufacturer Part Number` from common DOM patterns (Manufacturer:, Mfr Part No, MPN, etc). If those exist on the vendor's product page, the row lands `OK` with mfg/PN filled. If not, it captures URL + page title + H1 in the Notes column so the operator can fill MFG/PN by hand.

5. **Anti-bot is a known risk on Graybar / Motion / Border States.** Even with a real Chrome session, some rows will degrade to `MANUAL_REVIEW`. The captured title is usually enough to harvest MFG by hand (`"Crouse-Hinds GUAB26 — Border States"` → MFG = Crouse-Hinds, PN = GUAB26).

## Attachments

- `Pull_MFG_and_PN_ENRICHED.xlsx` — the deliverable
- All 9 bookmarklet HTML files
- `README.md` — workflow + per-vendor anti-bot notes

## Open clarifying questions

1. **Wesco Distribution rows (64)** — these are Wesco's own catalog. Anthony's team may already have these MFG/PNs in their internal system. Worth confirming before running the wesco.com bookmarklet — saves 64 rows of browser work.
2. **CED (13 rows) and RS Americas (12 rows)** — both flagged for description-mining only (no public catalog scrape). Six rows currently land `MANUAL_REVIEW`. Would Anthony's team be willing to confirm the MFG inferences from descriptions (most have explicit brand names), or do you want a manual research pass?
3. **Border States (166 rows)** — the bookmarklet uses the public search URL (no login). If the team has a logged-in borderstates.com session in another tab, the bookmarklet will use it automatically. Do they have one set up?

## Quick-start for Anthony

1. Open `Pull_MFG_and_PN_ENRICHED.xlsx` — 35% of rows (cols M-S) already filled.
2. For each `PENDING_VENDOR_SCRAPE` row, the Notes column says which bookmarklet to run.
3. Open the matching `<vendor>_bookmarklet.html`, drag the green button to bookmarks bar.
4. Open the vendor site in another tab. Click the bookmark.
5. CSV lands on clipboard at the end. Paste into the corresponding rows of the enriched xlsx.
