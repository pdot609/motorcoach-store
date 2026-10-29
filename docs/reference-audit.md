# Reference audit — Explore Showrooms

**Target:** https://www.themotorcoachstore.com/explore-showrooms  
**Inspected:** 2026-10-28  
**Platform evidence:** HubSpot CMS (`hubspot`, `hs-script`, HubSpot CTA track URLs, portal `47169059`). Not WordPress.  
**Local stack:** Static HTML + `css/site.css` + `js/explore.js` + Python `server.py` on `127.0.0.1:3460`. No `package.json`.  
**Constraint:** Do not change the email / SMTP inquiry system.

## Page title

`Explore Motorcoach Showrooms - The Motorcoach Store`

## Section order (top → bottom)

1. **Header contacts** — sales@…, service@…, address, phone  
2. **Utility / logo row** — phone · logo · sales email  
3. **Primary nav** — New Showrooms, Pre-Owned Showrooms, Fractional Ownership, Service, Paint/Body, Contact, More  
4. **Hero** — looping video + H1 `EXPLORE SHOWROOMS`  
5. **Logo marquee / brand strip** — OGV, Adventure, Featherlite, Loki, MTCS, Prevost, Millennium (scrolling)  
6. **Prevost Loki Coach band** — brand logo, Enter CTA, rail (2 coaches), View All, dots, Enter CTA again  
7. **OGV Luxury Coach band** (mid gray `#2b2b2b`) — logo, Enter, rail (4 coaches), View All, dots, Enter  
8. **Adventure by ShowHauler band** — logo, Enter, rail (4 coaches), View All, dots, Enter  
9. **Featherlite Stacker Trailers band** (mid gray `#2b2b2b`) — logo, Enter, rail (4 coaches), View All, dots, Enter  
10. **Begin Your Journey with Confidence** — copy + Schedule Appointment + side image  
11. **Footer** — brand, links, social, legal  

Reference has **one** journey block. Local previously duplicated `explore-close` + `.journey`.

## Exact visible inventory (at inspection)

### Loki (2)

| Title | Price |
|---|---|
| 2027 Prevost Loki H3 45 | $2,596,533 |
| 2027 Prevost Loki H3 45 | $2,315,272 |

### OGV (4)

| Title | MSRP | Price | Monthly |
|---|---|---|---|
| 2026 OGV Luxury Coach V-Cruise 8OBA | — | $149,999 | — |
| 2027 OGV Luxury Coach V-Cruise 10OBW | $266,424 | $199,795 | $1,616 |
| 2026 OGV Luxury Coach V-Tour 5RL4A | $231,212 | $167,522 | $1,457 |
| 2026 OGV Luxury Coach V-Sport 9RB7 | $209,162 | $156,872 | $1,269 |

### Adventure (4)

| Title | MSRP | Price |
|---|---|---|
| 2026 ShowHauler Adventure A4501 | $968,568 | $699,999 |
| 2026 SHOWHAULER ADVENTURE A4502 | $975,244 | $699,999 |
| 2026 SHOWHAULER ADVENTURE A4502 | $975,244 | $699,999 |
| 2026 SHOWHAULER ADVENTURE A4502 | $975,244 | $699,999 |

### Featherlite (4)

| Title | MSRP | Price |
|---|---|---|
| 2026 Featherlite 26' Stacker Trailer 4414 | $124,990 | $112,491 |
| 2026 Featherlite 24' Stacker Trailer 4414 | $116,668 | $100,800 |
| 2026 Featherlite 24' Stacker Trailer 4414 | $114,071 | $102,664 |
| 2026 Featherlite 26' Stacker Trailer 4414 | $123,640 | $111,276 |

## CTA copy (exact)

- `Enter Prevost Loki Coach Showroom`
- `Enter OGV Luxury Coach Showroom`
- `Enter Adventure by ShowHauler Showroom`
- `Enter Featherlite Stacker Trailers Showroom`
- `Learn More`
- `View All`
- `SCHEDULE APPOINTMENT`
- Journey body: `Contact our team today to schedule a personalized consultation or showroom visit. Your luxury motor coach is waiting.`

## Destinations (observable)

Enter / View All CTAs on HubSpot use tracked CTA URLs that resolve to brand showroom pages (`/motorcoach-showroom-new-prevost-loki-coach/`, `/motorcoach-showroom-ogv/`, etc.). Local maps those to the same showroom routes via aliases. Schedule on reference also appears as `/tmcs-schedule-appointment-7.1.26` and `/schedule-appointment`; local uses `/schedule-appointment`.

## What remains inaccessible

- HubSpot private theme SCSS source  
- Exact CTA redirect targets behind tracking URLs without clicking each  
- Cookie/session-only personalization (none observed for inventory)  
