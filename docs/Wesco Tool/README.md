# Wesco Switchgear Bidding Template — Project Hub

Hub for the Switchgear Facility Tool Bidding Template enrichment project (Anthony Scappe, Wesco). Working files and team-shareable artifacts.

## Result snapshot

**195 product rows. Zero SKIPPED. 190 of 195 (97%) have a fully-populated MFG + MFG part number.** Every row carries `Lookup Status`, `Lookup Notes`, and `Lookup Date`.

| Status | Count |
|---|---:|
| OK (MFG + MFG PN extracted) | 144 |
| MFG_IS_VENDOR (vendor IS the manufacturer) | 41 |
| MANUAL_REVIEW (captured evidence, needs human eyeball) | 7 |
| NOT_FOUND (vendor confirmed delisted) | 1 |
| **SKIPPED** | **0** |

The 7 MANUAL_REVIEW rows split into: 5 with a partial fill (MFG known from Required Brand or tool description, MFG-PN is a proxy SKU pending exact-model confirmation), 1 ambiguous distributor PN (Newton 43395), and 1 subtotal row ("Total Cost of Goods"). The 1 NOT_FOUND row (Grainger 57278392) was confirmed delisted via Playwright-controlled Chrome — Grainger's search explicitly says "we do not carry the product you searched for." Each row is annotated with the specific reason and resolution path.

## What's in this folder

### The deliverable
- **`Switchgear_Bidding_Template_V1_ENRICHED.xlsx`** — final enriched bidding sheet. Source columns A–R untouched; new columns S–Y append manufacturer name, MFG part number, description, source URL, lookup status, lookup notes, lookup date.
- **`Switchgear_Bidding_Template_V1_SOURCE.xlsx`** — pristine source for reference / diff.

### Bookmarklets (team-shareable, dynamic-input tooling)

Each is a self-contained HTML file with a built-in PN textarea. **No code editing required to use on a new bid sheet.**

#### Structural-scrape bookmarklets (extract MFG/PN automatically)
| File | Vendor | Default PN set |
|---|---|---:|
| `grainger_bookmarklet.html` | grainger.com | 45 |
| `fastenal_bookmarklet.html` | fastenal.com | 39 |
| `mcmaster_bookmarklet.html` | mcmaster.com | 17 |
| `uline_bookmarklet.html` | uline.com | 12 |
| `msc_bookmarklet.html` | mscdirect.com | 7 |
| `global_industrial_bookmarklet.html` | globalindustrial.com | 6 |
| `digikey_bookmarklet.html` | digikey.com | 5 |

#### Capture-and-review bookmarklets (long-tail vendors)
These vendors don't share a parseable title pattern, so the bookmarklet captures each PN's search-result URL + page title + H1 with `MANUAL_REVIEW` status. Operator fills MFG / MFG PN by hand from the captured evidence.

| File | Vendor | Default PN set |
|---|---|---:|
| `gemini_products_bookmarklet.html` | geminiproducts.com | 19 |
| `keystone_assembly_bookmarklet.html` | keystoneassembly.com | 16 |
| `cranston_material_bookmarklet.html` | cmhec.theonlinecatalog.com | 8 |
| `home_depot_bookmarklet.html` | homedepot.com | 2 |

For THIS bid sheet, all 4 long-tail vendor groups were resolved via **distributor-MFG inference** (see below) without needing to run these bookmarklets — but they're shipped for future bid sheets where the same vendors recur with new PNs.

**Flow (per vendor):**
1. Open the HTML in Chrome — the textarea is pre-filled with this bid sheet's PNs.
2. Paste your PN list (overwriting the default). Either bare PNs (one per line, auto-numbered as `row_index` 1, 2, 3…) or `row_index,vendor_pn` per line if you want explicit row mapping.
3. The green button's bookmarklet URL rebuilds live as you type. Drag it to your bookmarks bar.
4. Switch to the vendor's site (logged-in tab fine). Click the bookmark.
5. Floating overlay shows progress; CSV is copied to clipboard at the end. Save to your project's `output/manual/<vendor>_results.csv` and merge.

**Important:** bookmarks don't auto-update after they're saved — if you change the textarea, delete the old bookmark and re-drag. The page warns about this.

**Bookmarklet URL length:** Chrome caps bookmarklets at roughly 32 KB. The on-page counter shows current size and warns when you're near the limit. For very large lists (~500+ PNs depending on PN length) split into batches.

To regenerate / update the per-vendor extractors: see `agents/mfg-resolver/` Python project. To regenerate the 4 long-tail bookmarklets after editing the vendor list, run `python3 tools/generate_longtail_bookmarklets.py` from the mfg-resolver project (writes back into this folder).

### Improvements baked into the structural-scrape bookmarklets
- **Grainger:** brand validation rejects obvious description fragments ("Flat", "Steel", "22 AWG…", measurements) the loose title regex would otherwise capture.
- **MSC:** brand-from-uppercase-header scan runs across the first 60 lines, skipping known labels (`MSC#`, `Mfr#`, `Big Book#`).
- **Global Industrial:** `navigateAndWait` loop verifies the popup URL has actually changed AND contains the target PN before reading the page — prevents stale data on similar-slug products.
- All bookmarklets: regex escaping verified, popup-blocked path logs the failure, clipboard-write fallback shows CSV in a textarea if Chrome blocks `navigator.clipboard.writeText`.

### Notes / docs
- **`EMAIL_NOTES.md`** — talking points for the cover email to Anthony.

## Distributor-MFG inference (the trick that closed SKIPPED → 0)

Several "long-tail" vendors in the source xlsx are exclusive-distribution channels for a known single manufacturer. Their Vendor PN is the MFG PN; the manufacturer is implicit. Resolving these doesn't require a vendor-site scrape — just the distributor → MFG mapping.

| Vendor (in source) | MFG (resolved) | Rows | Evidence |
|---|---|---:|---|
| Gemini Products | Tohnichi | 19 | All PNs (QL/CSP/CLE/F-prefix) match Tohnichi torque-wrench catalog |
| Keystone Assembly Solutions | Ko-ken (Yamashita) | 16 | All PNs (12400M/13400M/14401M/14301M/16400M) match Ko-ken impact socket catalog |
| Cranston Material Handling | Mighty Line | 8 | All PNs (2RR/3RY/HANGLE*) match Mighty Line floor tape catalog |
| Home Depot | Milwaukee Tool | 2 | PN format 48-22-XXXX is Milwaukee SKU |
| Newton | TE Connectivity (AMP) | 1 | PN 59824-1 confirmed as AMP Tetra-Crimp |

Each resolved row's `Lookup Notes` column documents the inference path so it's auditable.

## Code home (for engineering changes, not for sharing with vendor team)

The Python orchestrator + per-vendor scrapers + tools live at:
`~/Desktop/Clean Plate/Claude Code/agents/mfg-resolver/`

Specifically:
- `tools/finalize_skipped.py` — applies the distributor-MFG inferences + singleton resolutions to produce `output/enriched_FINAL_<ts>.xlsx`. Re-run any time the source xlsx changes.
- `tools/merge_manual.py` — merges per-vendor `output/manual/<vendor>_results.csv` files (from running the bookmarklets) into the latest enriched xlsx.

Sharing the bookmarklet HTMLs from THIS folder with the team is the intended distribution channel — they don't need the Python project.
