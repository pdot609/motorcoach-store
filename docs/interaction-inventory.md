# Interaction inventory — Explore Showrooms

| Control | Initial | Appearance | Behavior | Destination / result | Mobile | Test |
|---|---|---|---|---|---|---|
| Header sales/service/phone | Idle | Gold text links | Click opens mailto/tel | sales@ / service@ display; local service mailto → sales mailbox | Contacts row compresses | Click each |
| Logo | Idle | Center logo | Navigate home | `/` | Same | Click |
| Nav New Showrooms | Collapsed | Uppercase link + submenu | Hover/tap opens submenu | Explore + brand showrooms + sold | Menu toggle | Open submenu |
| Enter * Showroom (×2 per band) | Idle | Framed white button | Navigate to brand showroom | Local aliases to `/showrooms/*` | Full width-ish | Click each |
| Vehicle card / image / title | Idle | Product card | Navigate to coach detail | `/coaches/{slug}` | Horizontal scroll | Click card |
| Learn More | Idle | Full-width under card; gold fill on hover | Navigate to coach | Same as card | Same | Hover + click |
| View All | Idle | Dark panel + gold “VIEW ALL” + chevron | Navigate to brand showroom | Brand showroom | Hidden ≤760px | Click |
| Slide dots | First selected | 12px squares | Scroll rail to card index | Updates `aria-selected` | Same | Click dots + scroll |
| Logo marquee | Auto-scroll | White logos on dark | Continuous loop; reduced-motion disables | Decorative | Same | Observe |
| Hero video | Autoplay muted loop | Full-bleed under title | Plays if browser allows | N/A | Same | Confirm playing |
| Schedule Appointment | Idle | Gold outlined uppercase | Navigate schedule | `/schedule-appointment` | Stack in close section | Click |
| Footer links | Idle | Text links | Navigate | Footer destinations | Stack | Spot-check |

**Not present on reference:** cookie banner was not observed during this inspection. No forms on this page (email system untouched).
