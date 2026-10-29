# Implementation status — Explore Showrooms

| Stage | Status | Notes |
|---|---|---|
| A Inspect project + reference | Done | Static HTML/CSS/JS; HubSpot reference; server `:3460` |
| B Screenshots + audit docs | Done | Audit docs + CDP full-page captures |
| C Assets + interactions | Done | HubSpot inventory/logo URLs; interaction inventory |
| D Implement | Done | Wide Loki 2-up, gold H1, mid bands, journey CTA, dynamic dots |
| E Verify sections | Done | 4 bands + marquee + journey; inventory text matches live |
| F Screenshot compare | Done | 1440 / 768 / 390 via Cursor browser CDP (Playwright Chromium install aborted) |
| G Correct gaps | Done | Card geometry aligned to live 685/343; pagination page-based |
| H Responsive retest | Done | Mobile menu; no horizontal overflow at 390/768/1440 |
| I Report | Done | See below |

## De-duplication pass (follow-up)

- Explore page is data-driven from `data/explore-showrooms.json` via `js/explore.js` (one CTA close section; no stacked `.journey`).
- `/showrooms/` redirects to `/explore-showrooms/` (removed duplicate journey + near-clone page).
- `/motorcoach-showroom-ogv/` is a stub redirect to `/showrooms/ogv/` (was a full duplicate).
- Unused `form.js` / `inventory.js` / `explore.js` tags removed from pages that do not need them.
- Email / SMTP path untouched.

## Explicit non-goals (honored)

- **Email system untouched** — `server.py` SMTP, `private/mail.env`, and form mail behavior were not modified.
- Display addresses remain `sales@themotorcoach.store` / `service@themotorcoach.store` (intentional vs live `.com`).
- No invented coaches, prices, or logos.

## Accepted matches

- Section order: hero → logo marquee → Loki → OGV → Adventure → Featherlite → Begin Your Journey → footer
- Inventory titles, MSRP, sale prices, monthly payments match live at inspection time
- Loki cards ~685×620 with 643×434 images; other brands ~343 with 301×203 images
- Alternating `#0e0e0e` / `#2b2b2b` bands
- Dual Enter Showroom CTAs per band; View All overlays; Learn More
- Desktop pagination collapses to 1 bullet when the rail does not overflow

## Remaining discrepancies

| Item | Detail |
|---|---|
| Email domain in chrome | Local `.store` vs live `.com` — by product requirement |
| H1 / body fonts | Live uses Bosca / Riviera Nights webfonts; local uses stack substitutes |
| Page height | Local ~100–210px taller (header contacts + footer brand block) |
| Card copy height | OGV/Adventure cards ~7–17px taller (font metrics / line boxes) |
| Hero media | Live HubSpot banner video; frame differs each capture |
| Footer density | Local footer taller (~561 vs live ~364) due to logo + contact block |
| Playwright automation | Chromium install aborted; `tools/compare-explore.mjs` ready once browsers install |

## How to re-verify

1. `python3 server.py` (port 3460)
2. Open `/explore-showrooms/`
3. Optional: `npx playwright install chromium && node tools/compare-explore.mjs`
