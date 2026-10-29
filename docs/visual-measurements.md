# Visual measurements — Explore Showrooms

Viewport conditions: CSS pixels, deviceScaleFactor 1, browser zoom 100%.

## 1440 × 900 (primary)

| Property | Reference | Local | Diff |
|---|---:|---:|---:|
| Page scroll height | 5868 | ~5960–6077 | ~+100–210 |
| Header / chrome height | ~114 (body pad) | 164 | +50 |
| Hero height | 522 | 522 | 0 |
| H1 font-size | 59.2941px | 59.2934px | ~0 |
| H1 treatment | gold gradient, uppercase, Bosca | gold gradient, uppercase, local serif | font family |
| Logo marquee height | 90 | 90 | 0 |
| Loki card (outer) | 685 × 620 | 685 × ~616–628 | ~0–8 |
| Loki image | 643 × 434 | 643 × 434 | 0 |
| Loki card padding | 14px 20px 20px | 14px 20px 20px | 0 |
| OGV card (outer) | 343 × 451 | 343 × ~468 | ~+17 |
| OGV image | 301 × 203 | 301 × 203 | 0 |
| Adventure / Featherlite card | 343 × 432 | 343 × ~439 | ~+7 |
| Mid band background | #2b2b2b | #2b2b2b | 0 |
| Pagination (desktop, all fit) | 1 bullet / rail | 1 bullet / rail | 0 |
| Horizontal overflow | none | none | 0 |
| Broken images | 0 | 0 | 0 |

## 768 × 1024 (tablet)

| Property | Local observation |
|---|---|
| Overflow X | none |
| Loki card width | 685 (scrolls in rail) |
| Dots | page-based (2–3 per rail) |

## 390 × 844 (mobile)

| Property | Local | Reference notes |
|---|---|---|
| Overflow X | none (scrollW = 390) | Menu present |
| Mobile menu | Menu toggle shown | Menu control shown |
| Loki card | ~359 wide (near full rail) | 2 dots when cards overflow |
| OGV / others | scroll rails, 4 dots | multi-bullet pagination |

## Screenshot artifacts

| File | Notes |
|---|---|
| `docs/screenshots/ref/1440x900-full.png` | CDP `captureBeyondViewport` — 1440×5868 |
| `docs/screenshots/local/1440x900-full.png` | CDP — 1440×6077 |
| `docs/screenshots/diff/1440x900-side-by-side-top.png` | Top-of-page side-by-side |
| `docs/screenshots/local/390x844-full.png` | Mobile local |
| `docs/screenshots/ref/390x844-full.png` | Mobile reference |
| `docs/screenshots/local/768x1024-full.png` | Tablet local |

## Pixel-diff caveat

Raw pixel difference at 1440 is high (~35–40% sampled) due to: hero video frame, marquee animation phase, `.store` vs `.com` emails (intentional), Bosca webfont vs local fallback, and footer/logo chrome height. Structural card geometry matches within ~0–17px.

## Compare workflow

```bash
# Preferred when Chromium is installed for Playwright:
node tools/compare-explore.mjs

# Fallback used in this session: Cursor browser CDP Page.captureScreenshot
# with captureBeyondViewport, then decode base64 into docs/screenshots/
```

Playwright Chromium download was aborted in this environment; CDP + Cursor browser was used instead.
