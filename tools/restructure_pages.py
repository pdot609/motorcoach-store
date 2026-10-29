#!/usr/bin/env python3
"""Align local page shells and key page bodies with the original Motorcoach Store structure."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

JOURNEY = (
    '<section class="journey"><div class="band-media">'
    '<img src="https://www.themotorcoachstore.com/hs-fs/hubfs/Begin%20Your%20Journey%20with%20Confidence-1.webp" alt="" data-fallback="media">'
    '</div><div class="journey-copy"><h2>Begin Your Journey with Confidence</h2>'
    '<p class="lede" style="margin:0 auto 22px">Contact our team today to schedule a personalized consultation or showroom visit. Your luxury motor coach is waiting.</p>'
    '<div class="inline-actions"><a class="btn" href="/schedule-appointment">Schedule Appointment</a></div></div></section>'
)

# Keep .store mailboxes; map nav to original path names where local aliases exist.
NAV = """<ul class="nav-list"><li class="nav-item"><a class="nav-link" href="/explore-showrooms">New Showrooms</a><button class="menu-toggle" type="button" aria-expanded="false">Show</button><div class="submenu"><a href="/explore-showrooms">View All New Showrooms</a><a href="/motorcoach-showroom-new-prevost-loki-coach">Prevost Loki Coach</a><a href="/motorcoach-showroom-ogv">OGV Luxury Coach</a><a href="/motorcoach-showroom-new-adventure-showhauler">Adventure by ShowHauler</a><a href="/motorcoach-showroom-new-featherlite-stacker-trailers">Featherlite Stacker Trailers</a><a href="/sold-units">New Units Sold</a></div></li><li class="nav-item"><a class="nav-link" href="/pre-owned">Pre-Owned Showrooms</a><button class="menu-toggle" type="button" aria-expanded="false">Show</button><div class="submenu"><a href="/pre-owned">Pre-Owned Showroom</a><a href="/motorcoach-showroom-sold-pre-owned">Pre-Owned Showroom Sold</a></div></li><li class="nav-item"><a class="nav-link" href="/fractionalmotorcoachownership-page">Fractional Ownership</a></li><li class="nav-item"><a class="nav-link" href="/service">Service</a><button class="menu-toggle" type="button" aria-expanded="false">Show</button><div class="submenu"><a href="/service">Service Department</a><a href="/ceramic-coating">Ceramic Coating Department</a></div></li><li class="nav-item"><a class="nav-link" href="/paint-and-body">Paint/Body</a></li><li class="nav-item"><a class="nav-link" href="/contact-us">Contact</a></li><li class="nav-item"><a class="nav-link" href="/about">More</a><button class="menu-toggle" type="button" aria-expanded="false">Show</button><div class="submenu"><a href="/about">About</a><a href="/rv-insurance">RV Insurance</a><a href="/news">News</a><a href="/sell-your-coach">Sell Your Coach</a><a href="/schedule-appointment">Schedule Appointment</a><a href="/rv-financing">Motorcoach Financing</a><a href="/certified-pre-owned">Certified Pre-Owned (CPO)</a><a href="/pre-delivery-inspection">Pre-Delivery Inspection (PDI)</a><a href="/trade-rv">Trade-in</a></div></li></ul>"""

FOOTER_LINKS = """<ul class="footer-links"><li><a href="/explore-showrooms">New Showrooms</a></li><li><a href="/pre-owned">Pre-Owned Showrooms</a></li><li><a href="/certified-pre-owned">Certified Pre-Owned (CPO)</a></li><li><a href="/pre-delivery-inspection">Pre-Delivery Inspection (PDI)</a></li><li><a href="/fractionalmotorcoachownership-page">Fractional Ownership</a></li><li><a href="/sell-your-coach">Sell Your Coach</a></li><li><a href="/trade-rv">Trade-in</a></li><li><a href="/rv-insurance">RV Insurance</a></li><li><a href="/service">Service</a></li><li><a href="/paint-and-body">Paint/Body</a></li><li><a href="/ceramic-coating">Ceramic Coating</a></li><li><a href="/rv-financing">Motorcoach Financing</a></li><li><a href="/about">About</a></li><li><a href="/news">News</a></li><li><a href="/contact-us">Contact Us</a></li></ul>"""

SHOWROOMS = {
    "showrooms/prevost-loki/index.html": {
        "title": "New Prevost Loki Coaches - The Motorcoach Store",
        "hero": "https://www.themotorcoachstore.com/hs-fs/hubfs/LokiCoach01.webp",
        "logo": "https://www.themotorcoachstore.com/hubfs/LOGOS/Loki%20Coach%20Logo.svg",
        "logo_alt": "Loki Coach",
        "brand": "prevost-loki",
        "channel": "new",
        "status": "available",
        "current": "prevost-loki",
    },
    "showrooms/adventure/index.html": {
        "title": "New Adventure by ShowHauler Coaches - The Motorcoach Store",
        "hero": "https://www.themotorcoachstore.com/hs-fs/hubfs/ShowHauler%20Adventure%20Showroom%20Hero.webp",
        "logo": "https://www.themotorcoachstore.com/hs-fs/hubfs/LOGOS/Logo%20-%20Adventure%20Series.webp",
        "logo_alt": "Adventure by ShowHauler",
        "brand": "adventure",
        "channel": "new",
        "status": "available",
        "current": "adventure",
    },
    "showrooms/featherlite/index.html": {
        "title": "Featherlite Stacker Trailers - The Motorcoach Store",
        "hero": "https://www.themotorcoachstore.com/hs-fs/hubfs/Featherlite%20Background%20(1).webp",
        "logo": "https://www.themotorcoachstore.com/hs-fs/hubfs/LOGOS/FTHRfinalLogo%20(1).webp",
        "logo_alt": "Featherlite",
        "brand": "featherlite",
        "channel": "new",
        "status": "available",
        "current": "featherlite",
    },
    "showrooms/ogv/index.html": {
        "title": "New OGV Luxury Coaches - The Motorcoach Store",
        "hero": "https://www.themotorcoachstore.com/hs-fs/hubfs/Img%20New%20OGV%20Luxury%20Coach.webp",
        "logo": "https://www.themotorcoachstore.com/hs-fs/hubfs/OGV-Logo-1.png",
        "logo_alt": "OGV",
        "brand": "ogv",
        "channel": "new",
        "status": "available",
        "current": "ogv",
    },
    "motorcoach-showroom-ogv/index.html": {
        "title": "New OGV Luxury Coaches - The Motorcoach Store",
        "hero": "https://www.themotorcoachstore.com/hs-fs/hubfs/Img%20New%20OGV%20Luxury%20Coach.webp",
        "logo": "https://www.themotorcoachstore.com/hs-fs/hubfs/OGV-Logo-1.png",
        "logo_alt": "OGV",
        "brand": "ogv",
        "channel": "new",
        "status": "available",
        "current": "ogv",
    },
    "sold/index.html": {
        "title": "Sold Motor Coaches - The Motorcoach Store",
        "hero": "https://www.themotorcoachstore.com/hs-fs/hubfs/MARKETING/Millennium%20Campaign/HI-RES%20PHOTOS/CO1A0099-HDR-Cropped1.jpg",
        "logo": "",
        "logo_alt": "",
        "brand": "",
        "channel": "new",
        "status": "sold",
        "current": "sold",
    },
    "pre-owned/sold/index.html": {
        "title": "Pre-Owned Showroom Sold - The Motorcoach Store",
        "hero": "https://www.themotorcoachstore.com/hs-fs/hubfs/MARKETING/Millennium%20Campaign/HI-RES%20PHOTOS/CO1A0099-HDR-Cropped1.jpg",
        "logo": "",
        "logo_alt": "",
        "brand": "",
        "channel": "pre-owned",
        "status": "sold",
        "current": "pre-owned-sold",
    },
}

ALIASES = {
    "motorcoach-showroom-new-prevost-loki-coach": "/showrooms/prevost-loki/",
    "motorcoach-showroom-new-adventure-showhauler": "/showrooms/adventure/",
    "motorcoach-showroom-new-featherlite-stacker-trailers": "/showrooms/featherlite/",
    "sold-units": "/sold/",
    "motorcoach-showroom-sold-pre-owned": "/pre-owned/sold/",
    "contact-us": "/contact/",
    "sell-your-coach": "/sell/",
    "trade-rv": "/trade-in/",
    "rv-financing": "/financing/",
    "rv-insurance": "/insurance/",
    "schedule-appointment": "/schedule/",
    "fractionalmotorcoachownership-page": "/fractional-ownership/",
}


def shell_from(path: Path) -> tuple[str, str, str]:
    text = path.read_text()
    head = re.search(r"(<!DOCTYPE html>.*?</header>)", text, re.S)
    foot = re.search(r"(<footer class=\"site-footer\">.*?</html>)", text, re.S)
    if not head or not foot:
        raise SystemExit(f"Could not split shell for {path}")
    return head.group(1), foot.group(1), text


PATH_MAP = {
    "/schedule": "/schedule-appointment",
    "/contact": "/contact-us",
    "/sell": "/sell-your-coach",
    "/trade-in": "/trade-rv",
    "/financing": "/rv-financing",
    "/insurance": "/rv-insurance",
    "/fractional-ownership": "/fractionalmotorcoachownership-page",
}


def rewrite_href(html: str, old: str, new: str) -> str:
    """Replace href=\"{old}\" only when old is a complete path (not a prefix of a longer path)."""
    pattern = re.compile(rf'href="{re.escape(old)}(?=["?#])')
    return pattern.sub(f'href="{new}', html)


def replace_nav_footer(html: str) -> str:
    html = re.sub(r"<ul class=\"nav-list\">.*?</ul>", NAV, html, count=1, flags=re.S)
    html = re.sub(r"<ul class=\"footer-links\">.*?</ul>", FOOTER_LINKS, html, count=1, flags=re.S)
    for old, new in PATH_MAP.items():
        html = rewrite_href(html, old, new)
    return html


def ensure_journey(main_html: str) -> str:
    # Do not stack a second CTA when explore-close (or journey) already exists.
    if 'class="journey"' in main_html or 'class="explore-close"' in main_html:
        return main_html
    if main_html.rstrip().endswith("</main>"):
        return main_html[:-7] + JOURNEY + "</main>"
    return main_html + JOURNEY


def write_page(path: Path, title: str, main: str, current_hints: list[str] | None = None):
    base = ROOT / "showrooms/ogv/index.html"
    head, foot, _ = shell_from(base)
    # Rebuild head title
    head = re.sub(r"<title>.*?</title>", f"<title>{title}</title>", head, count=1)
    head = replace_nav_footer(head)
    foot = replace_nav_footer(foot)
    # Clear aria-current then set for hints
    head = head.replace(' aria-current="page"', "")
    for hint in current_hints or []:
        head = head.replace(f'href="{hint}"', f'href="{hint}" aria-current="page"', 1)
    main = ensure_journey(main)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(head + "\n  <main id=\"content\">" + main + "</main>\n  " + foot)
    print("wrote", path.relative_to(ROOT))


def showroom_main(cfg: dict) -> str:
    logo = ""
    if cfg["logo"]:
        logo = f'<img class="showroom-logo" src="{cfg["logo"]}" alt="{cfg["logo_alt"]}">'
    brand_attr = f' data-brand="{cfg["brand"]}"' if cfg["brand"] else ""
    channel = cfg["channel"]
    status = cfg["status"]
    return (
        f'<section class="page-hero showroom-hero"><div class="hero-media">'
        f'<img src="{cfg["hero"]}" alt="" data-fallback="media"></div>'
        f'<div class="page-hero-copy">{logo}<h1>Showroom</h1></div></section>'
        f'<div id="inventory" data-channel="{channel}"{brand_attr} data-status="{status}" data-layout="showroom">'
        f'<p class="section loading">Loading the showroom…</p></div>'
    )


def update_all_shells():
    for path in ROOT.rglob("index.html"):
        if "private" in path.parts:
            continue
        text = path.read_text()
        if 'class="nav-list"' not in text:
            continue
        updated = replace_nav_footer(text)
        # Add journey before footer if missing (skip explore-close pages)
        if 'class="journey"' not in updated and 'class="explore-close"' not in updated and "</main>" in updated:
            updated = updated.replace("</main>", JOURNEY + "</main>", 1)
        if updated != text:
            path.write_text(updated)
            print("shell", path.relative_to(ROOT))


def write_showrooms():
    for rel, cfg in SHOWROOMS.items():
        hints = {
            "prevost-loki": ["/motorcoach-showroom-new-prevost-loki-coach", "/explore-showrooms"],
            "adventure": ["/motorcoach-showroom-new-adventure-showhauler", "/explore-showrooms"],
            "featherlite": ["/motorcoach-showroom-new-featherlite-stacker-trailers", "/explore-showrooms"],
            "ogv": ["/motorcoach-showroom-ogv", "/explore-showrooms"],
            "sold": ["/sold-units", "/explore-showrooms"],
            "pre-owned-sold": ["/motorcoach-showroom-sold-pre-owned", "/pre-owned"],
        }.get(cfg["current"], [])
        write_page(ROOT / rel, cfg["title"], showroom_main(cfg), hints)


def write_aliases():
    for alias, target in ALIASES.items():
        dest = ROOT / alias / "index.html"
        dest.parent.mkdir(parents=True, exist_ok=True)
        # Meta refresh + JS + link for static fallback; server also 302s.
        dest.write_text(
            "<!DOCTYPE html><html lang=\"en\"><head><meta charset=\"utf-8\">"
            f'<meta http-equiv="refresh" content="0;url={target}">'
            f"<title>Redirecting…</title>"
            f'<link rel="canonical" href="{target}">'
            f"<script>location.replace({json.dumps(target)});</script>"
            f'</head><body><p><a href="{target}">Continue</a></p></body></html>\n'
        )
        print("alias", alias, "->", target)


def contact_main() -> str:
    return """
<section class="page-hero"><div class="hero-media"><img src="https://www.themotorcoachstore.com/hs-fs/hubfs/MARKETING/Millennium%20Campaign/HI-RES%20PHOTOS/CO1A0099-HDR-Cropped1.jpg" alt="" data-fallback="media"></div><div class="page-hero-copy"><h1 class="script-title">contact</h1><p>Dreams Become Reality. Request for More Information.</p></div></section>
<section class="contact-sheet" id="request"><h2>The Motorcoach Store</h2><p>5821 24th Street East, Bradenton, FL 34203</p><p><a href="tel:+19412832516">941 283 2516</a></p><p><a href="mailto:sales@themotorcoach.store">sales@themotorcoach.store</a></p><p><a href="mailto:sales@themotorcoach.store">service@themotorcoach.store</a></p></section>
<section class="contact-ask"><h2>Get in touch</h2><p class="lede">We want to know more about your needs</p>
<form class="form" novalidate>
<input type="hidden" name="intent" value="contact">
<label>First name<input name="firstName" autocomplete="given-name" required><span class="error" data-for="firstName"></span></label>
<label>Last name<input name="lastName" autocomplete="family-name" required><span class="error" data-for="lastName"></span></label>
<label>Email<input name="email" type="email" autocomplete="email" required><span class="error" data-for="email"></span></label>
<label>Phone<input name="phone" type="tel" autocomplete="tel" required><span class="error" data-for="phone"></span></label>
<fieldset class="wide choice-set"><legend>I am interested in</legend>
<label class="choice"><input type="radio" name="interest" value="Buy a Coach" required> Buy a Coach</label>
<label class="choice"><input type="radio" name="interest" value="Sell a Coach"> Sell a Coach</label>
<label class="choice"><input type="radio" name="interest" value="Other"> Other</label>
<span class="error" data-for="interest"></span></fieldset>
<label class="wide">How Can We Be Of Service<textarea name="message" rows="5" required></textarea><span class="error" data-for="message"></span></label>
<label class="wide consent"><input type="checkbox" name="smsConsent" value="yes"> I agree to receive SMS updates about this request. Message and data rates may apply. Reply STOP to opt out.</label>
<label class="hp" aria-hidden="true">Company<input name="company" tabindex="-1" autocomplete="off"></label>
<p class="form-error wide" data-for="form"></p>
<div class="wide"><button class="btn-solid" type="submit">Submit</button></div>
</form></section>
""".strip()


def service_main() -> str:
    items = [
        ("Annual maintenance packages", "Comprehensive scheduled service to keep a coach running, protect warranty work, and catch repairs before a trip."),
        ("Engine repairs", "Diagnostics and precision repairs to restore performance and reliability."),
        ("Transmission repairs", "Diagnostics, service, and fluid work for the transmission."),
        ("Generator repairs and replacements", "Repair, maintenance, and replacement for onboard generators."),
        ("Air conditioning repairs and replacements", "Repair, replacement, and maintenance for coach climate systems."),
        ("Brake repairs and replacements", "Inspections, repairs, and full brake system replacements."),
        ("Electrical system repairs and upgrades", "Electrical troubleshooting plus upgrades such as inverters and solar."),
        ("Plumbing repairs and replacements", "Leaks, clogs, and freshwater or waste system repairs."),
        ("Hitch installation and repairs", "Installation, inspection, and repair of towing hitches."),
        ("Awning installation and repairs", "New awning installs and repairs, including fabric and motor work."),
        ("Furniture repair and replacement", "Interior furniture repair or replacement to match the coach."),
        ("Audio/visual system installation and upgrades", "Smart TVs, surround sound, satellite, and related upgrades."),
    ]
    cards = "".join(f"<section><h3>{t}</h3><p>{p}</p></section>" for t, p in items)
    return f"""
<section class="page-hero"><div class="hero-media"><img src="https://www.themotorcoachstore.com/hs-fs/hubfs/motorcoach-theme/assets/images/img%20Service%20Department.webp" alt="" data-fallback="media"></div><div class="page-hero-copy"><h1>SERVICE DEPARTMENT</h1><p>Top Professionals for Your Needs</p></div></section>
<article class="prose">
<h2>Top-tier RV &amp; Motorcoach Service</h2>
<p>RVIA-oriented repairs and maintenance for Newell, Prevost, Entegra, Newmar, Tiffin, and other luxury coaches. Email <a href="mailto:sales@themotorcoach.store">service@themotorcoach.store</a> or use the form. Messages addressed to that address are delivered to sales@themotorcoach.store.</p>
<h2>White glove service list</h2>
<div class="service-grid">{cards}</div>
<section><h2>Experience Luxury on the Road</h2><p>Every service visit is handled with the same care as a coach leaving the sales floor.</p></section>
<section><h2>Client Testimonials</h2><p class="lede">Guest reviews for the Bradenton shop are collected on Google. This page does not reprint them. <a href="https://www.google.com/maps/search/?api=1&amp;query=The+Motorcoach+Store+Bradenton">Read Google reviews</a>.</p></section>
</article>
<div class="form-wrap" id="form-section"><div><h2>Book Your Coach In For Service</h2><p class="lede">Need maintenance or repairs? Reach out today. A request is not a confirmed bay time until the shop replies.</p></div>
<form class="form" novalidate><input type="hidden" name="intent" value="service-appointment">
<label>First name<input name="firstName" autocomplete="given-name" required><span class="error" data-for="firstName"></span></label>
<label>Last name<input name="lastName" autocomplete="family-name" required><span class="error" data-for="lastName"></span></label>
<label>Email<input name="email" type="email" autocomplete="email" required><span class="error" data-for="email"></span></label>
<label>Phone<input name="phone" type="tel" autocomplete="tel" required><span class="error" data-for="phone"></span></label>
<label>Preferred date<input name="preferredDate" type="date"><span class="error" data-for="preferredDate"></span></label>
<label>Year<input name="year" inputmode="numeric"><span class="error" data-for="year"></span></label>
<label>Make<input name="make"><span class="error" data-for="make"></span></label>
<label>Model<input name="model"><span class="error" data-for="model"></span></label>
<label>Miles<input name="miles" inputmode="numeric"><span class="error" data-for="miles"></span></label>
<label class="wide">Message<textarea name="message" rows="5"></textarea><span class="error" data-for="message"></span></label>
<label class="hp" aria-hidden="true">Company<input name="company" tabindex="-1" autocomplete="off"></label>
<p class="form-error wide" data-for="form"></p>
<div class="wide"><button class="btn-solid" type="submit">Request service</button></div></form></div>
""".strip()


def paint_main() -> str:
    return """
<section class="page-hero"><div class="hero-media"><img src="https://www.themotorcoachstore.com/hs-fs/hubfs/IN%20ACTION-6--222222.webp" alt="" data-fallback="media"></div><div class="page-hero-copy"><h1>PAINT &amp; BODY</h1><p>Collision repair, restoration, and refinishing for luxury coaches.</p></div></section>
<article class="prose">
<section><h2>Collision</h2><p>Structural and cosmetic collision repair for fiberglass, gelcoat, aluminum, and stainless bodywork, including sidewalls, panels, and bay doors.</p></section>
<section><h2>Body Restoration</h2><p>Dents, scratches, bumpers, caps, lights, trim, window frames, awning housings, and moldings restored to a clean finish.</p></section>
<section><h2>Paint &amp; Refinishing</h2><p>OEM color matching for touch-up or a full repaint, plus graphics, clear coat, and decals.</p></section>
<section><h2>Insurance &amp; Support</h2><p>The shop works from an insurance estimate with documentation of the damage and the repair. Bring the claim number if you already have one.</p>
<div class="partner-row" aria-label="Insurance partners often seen with coach claims">
<img src="https://www.themotorcoachstore.com/hs-fs/hubfs/The%20Hartford%20Insurance.webp" alt="The Hartford">
<img src="https://www.themotorcoachstore.com/hs-fs/hubfs/Liberty%20Mutual.webp" alt="Liberty Mutual">
<img src="https://www.themotorcoachstore.com/hs-fs/hubfs/Auto%20Owners%20Insurance.webp" alt="Auto-Owners">
<img src="https://www.themotorcoachstore.com/hs-fs/hubfs/Good%20Sam%20Insurance%202.webp" alt="Good Sam">
<img src="https://www.themotorcoachstore.com/hs-fs/hubfs/National%20General%20Insurance%202.webp" alt="National General">
</div></section>
<section><h2>Client Testimonials</h2><p class="lede">Guest reviews for paint and body work are collected on Google. This page does not reprint them. <a href="https://www.google.com/maps/search/?api=1&amp;query=The+Motorcoach+Store+Bradenton">Read Google reviews</a>.</p></section>
</article>
<div class="form-wrap" id="request"><div><h2>Paint &amp; Body Request</h2><p class="lede">Describe the damage and where the coach is. Photos can follow by email to sales@themotorcoach.store.</p></div>
<form class="form" novalidate><input type="hidden" name="intent" value="paint-appointment">
<label>First name<input name="firstName" autocomplete="given-name" required><span class="error" data-for="firstName"></span></label>
<label>Last name<input name="lastName" autocomplete="family-name" required><span class="error" data-for="lastName"></span></label>
<label>Email<input name="email" type="email" autocomplete="email" required><span class="error" data-for="email"></span></label>
<label>Phone<input name="phone" type="tel" autocomplete="tel" required><span class="error" data-for="phone"></span></label>
<label>Preferred date<input name="preferredDate" type="date"><span class="error" data-for="preferredDate"></span></label>
<label>Year<input name="year" inputmode="numeric"><span class="error" data-for="year"></span></label>
<label>Make<input name="make"><span class="error" data-for="make"></span></label>
<label>Model<input name="model"><span class="error" data-for="model"></span></label>
<label>Miles<input name="miles" inputmode="numeric"><span class="error" data-for="miles"></span></label>
<label class="wide">Message<textarea name="message" rows="5"></textarea><span class="error" data-for="message"></span></label>
<label class="hp" aria-hidden="true">Company<input name="company" tabindex="-1" autocomplete="off"></label>
<p class="form-error wide" data-for="form"></p>
<div class="wide"><button class="btn-solid" type="submit">Request paint and body</button></div></form></div>
""".strip()


def ceramic_main() -> str:
    return """
<section class="page-hero"><div class="hero-media"><img src="https://www.themotorcoachstore.com/hs-fs/hubfs/mcs-stack_0014_In%20action-2%20%281%29-11111.webp" alt="" data-fallback="media"></div><div class="page-hero-copy"><h1>CERAMIC COATING</h1><p>Protect. Preserve. Perfect.</p></div></section>
<article class="prose">
<section><h2>Ultimate Protection</h2><p>A ceramic coating for the finish, applied by the Bradenton detail team, meant to keep a showroom gloss and shed water, dirt, and road film.</p></section>
<section><h2>Why Ceramic</h2><p>It is not a substitute for washing, and it does not make paint scratch-proof or chip-proof. It makes maintenance washes easier and helps the finish hold its look longer.</p></section>
<section><h2>Certified Technicians</h2><p>Coating work is handled by the same shop that prepares coaches for delivery, with paint correction available when an older finish needs it first.</p></section>
<section><h2>Proven Process</h2><ol class="process-list"><li>Wash and decontamination</li><li>Paint correction where the finish needs it</li><li>Coating application</li><li>Cure</li><li>Final inspection</li></ol></section>
<section><h2>Why Choose The Motorcoach Store</h2><p>The coating is applied in the same Bradenton facility as service and paint, so a coach already in for other work can be scheduled without a separate trip to an outside detailer.</p></section>
<section><h2>FAQ</h2>
<h3>How long does it last?</h3><p>With maintenance, many coatings last 3 to 5 years.</p>
<h3>Do I still wash the coach?</h3><p>Yes. Dirt still has to come off. The coating makes that wash easier. It is not wax, and it does not end washing.</p>
<h3>Can it go on an older coach?</h3><p>Yes. Older finishes often get paint correction first so the coating is not locking in swirls.</p>
<h3>Will it stop rock chips?</h3><p>No. Rock chips need paint and body work. Coating protects the finish that is already there.</p>
</section>
<section><h2>Myths</h2><p>Coating is not armor, not a polish that lasts forever, and not a reason to skip washing. It is a protective layer on a prepared finish.</p></section>
<section><h2>Client Testimonials</h2><p class="lede">Guest reviews are collected on Google. This page does not reprint them. <a href="https://www.google.com/maps/search/?api=1&amp;query=The+Motorcoach+Store+Bradenton">Read Google reviews</a>.</p></section>
</article>
<div class="form-wrap" id="request"><div><h2>Ready to Protect Your Coach?</h2><p class="lede">Include the coach year and make so the shop can estimate size and whether correction comes first.</p></div>
<form class="form" novalidate><input type="hidden" name="intent" value="ceramic">
<label>First name<input name="firstName" autocomplete="given-name" required><span class="error" data-for="firstName"></span></label>
<label>Last name<input name="lastName" autocomplete="family-name" required><span class="error" data-for="lastName"></span></label>
<label>Email<input name="email" type="email" autocomplete="email" required><span class="error" data-for="email"></span></label>
<label>Phone<input name="phone" type="tel" autocomplete="tel" required><span class="error" data-for="phone"></span></label>
<label>Year<input name="year" inputmode="numeric"><span class="error" data-for="year"></span></label>
<label>Make<input name="make"><span class="error" data-for="make"></span></label>
<label>Model<input name="model"><span class="error" data-for="model"></span></label>
<label>Miles<input name="miles" inputmode="numeric"><span class="error" data-for="miles"></span></label>
<label class="wide">Message<textarea name="message" rows="5"></textarea><span class="error" data-for="message"></span></label>
<label class="hp" aria-hidden="true">Company<input name="company" tabindex="-1" autocomplete="off"></label>
<p class="form-error wide" data-for="form"></p>
<div class="wide"><button class="btn-solid" type="submit">Request coating</button></div></form></div>
""".strip()


def fractional_main() -> str:
    return """
<section class="page-hero"><div class="hero-media"><img src="https://www.themotorcoachstore.com/hs-fs/hubfs/MARKETING/Millennium%20Campaign/HI-RES%20PHOTOS/CO1A0099-HDR-Cropped1.jpg" alt="" data-fallback="media"></div><div class="page-hero-copy"><h1>Fractional Motorcoach Ownership</h1><p>The full experience for 25% of the investment</p></div></section>
<section class="fractional-price"><h2>Starting at $449,999 for 25% or $1.8M+/- for 100%</h2>
<ul class="fractional-stats"><li><strong>25%</strong> Ownership Share</li><li><strong>$449,999</strong> Starting Purchase Price</li><li><strong>10</strong> Annual Weeks Guaranteed</li><li><strong>$1,500</strong> Est. Monthly Management Fee</li><li><strong>All</strong> Trade-Ins Accepted</li><li><strong>24/7</strong> Concierge Support</li></ul></section>
<section class="compare-grid">
<article><h3>25% Fractional Ownership</h3><p class="price">$449,999* Ownership Share</p><p class="note">*Starting at. All trade-ins accepted.</p><ul><li>25% Depreciation Exposure</li><li>Secure Storage Included</li><li>Insurance Included</li><li>Professional Pre-Trip Preparation</li><li>Maintenance &amp; Repairs Included</li><li>Fully Managed By The Motorcoach Store</li></ul></article>
<article><h3>Full Ownership</h3><p class="price">$1.8M* Purchase Price</p><p class="note">*Median MSRP</p><ul><li>100% Depreciation Exposure</li><li>Secure Storage Expenses</li><li>Insurance Expenses</li><li>Cleaning &amp; Detailing Expenses</li><li>Maintenance &amp; Repair Expenses</li><li>Coach Sits Idle for Most of the Year</li></ul></article>
</section>
<section class="section"><h2>Choose Your Coach</h2><p class="lede">Published fractional starting prices from the program sheet. Confirm availability and exact terms with the desk before planning a purchase.</p>
<div class="fractional-coaches">
<article><h3>2027 Loki Double Slide</h3><p class="price">$579,999*</p><p>25% Ownership · 10 Wks/Yr · *Starting at</p></article>
<article><h3>2027 Loki Quad Slide</h3><p class="price">$649,999*</p><p>25% Ownership · 10 Wks/Yr · *Starting at</p></article>
<article><h3>2023 Millennium Double Slide</h3><p class="price">$449,999*</p><p>25% Ownership · 10 Wks/Yr · *Starting at</p></article>
<article><h3>2026 Loki Double Slide Bunk</h3><p class="price">$539,999*</p><p>25% Ownership · 10 Wks/Yr · *Starting at</p></article>
</div>
<p class="note">Program phone line published with this offer: <a href="tel:+19417578314">941 757 8314</a>.</p></section>
<section class="section"><h2>Signature Benefits</h2>
<ul class="benefit-list"><li>24/7 Concierge Support</li><li>Personalized Trip Coordination</li><li>Secure Storage</li><li>Delivery Services Available</li><li>Insurance &amp; Maintenance Included</li><li>Personal Linens &amp; Soft Goods</li><li>Nationwide RV Resort Network</li><li>Departure-Ready, Every Time</li></ul>
<ul class="benefit-list"><li>Private Owner's Suite</li><li>Gourmet Kitchen with Premium Appliances</li><li>Multi-Zone Climate Control</li><li>Spa-Inspired Ensuite Bath</li><li>High-Speed WiFi &amp; Satellite Connectivity</li><li>Cinema-Quality Entertainment System</li></ul></section>
<div class="form-wrap"><div><h2>Request the program sheet</h2><p class="lede">Say whether you are asking about a 25% share or full ownership.</p></div>
<form class="form" novalidate><input type="hidden" name="intent" value="fractional">
<label>First name<input name="firstName" autocomplete="given-name" required><span class="error" data-for="firstName"></span></label>
<label>Last name<input name="lastName" autocomplete="family-name" required><span class="error" data-for="lastName"></span></label>
<label>Email<input name="email" type="email" autocomplete="email" required><span class="error" data-for="email"></span></label>
<label>Phone<input name="phone" type="tel" autocomplete="tel" required><span class="error" data-for="phone"></span></label>
<label class="wide">Message<textarea name="message" rows="5"></textarea><span class="error" data-for="message"></span></label>
<label class="hp" aria-hidden="true">Company<input name="company" tabindex="-1" autocomplete="off"></label>
<p class="form-error wide" data-for="form"></p>
<div class="wide"><button class="btn-solid" type="submit">Request fractional details</button></div></form></div>
""".strip()


def about_main() -> str:
    return """
<section class="page-hero"><div class="hero-media"><img src="https://www.themotorcoachstore.com/hubfs/Your-Satisfaction-Is-Our-Top-Priority%20%28cut%29.webp" alt="" data-fallback="media"></div><div class="page-hero-copy"><h1>Making Your Dreams a Reality</h1><p>A Bradenton showroom for new and pre-owned luxury motor coaches, with service and paint under the same roof.</p></div></section>
<article class="prose">
<section><h2>Our Story &amp; Mission</h2><p>The Motorcoach Store was founded in Bradenton, Florida to sell a focused collection of luxury motor coaches and back them with service. The showroom is built around coaches you can compare indoors.</p></section>
<section><h2>Meet the Founder &amp; CEO</h2><p>Bradley Twait owns the company and is the person the showroom points to for the standard a coach has to meet before it is offered. The stated aim is a coach that works as a home on the road.</p></section>
<section><h2>You’re Our Guest</h2><ul><li>Quality over quantity: find the coach that fits, rather than pushing the one that is easiest to sell.</li><li>Satisfaction is checked after the choice, not only at the signature.</li><li>Repeat service, paint, and the next coach are part of the same relationship.</li></ul></section>
<section><h2>Unique Showroom &amp; Services</h2><p>The indoor showroom holds new and pre-owned coaches from lines such as Prevost, Newell, and Newmar, plus Loki, OGV, ShowHauler, and Featherlite listings. Next to sales, the building includes a service center, a body and paint shop, and purchasing for Class A coaches.</p></section>
<section><h2>Client Testimonials</h2><p class="lede">Guest reviews are collected on Google for the Bradenton showroom. This page does not reprint them. <a href="https://www.google.com/maps/search/?api=1&amp;query=The+Motorcoach+Store+Bradenton">Read Google reviews</a>.</p></section>
</article>
""".strip()


def money(value):
    if value in (None, "", 0):
        return ""
    try:
        return f"${int(value):,}"
    except (TypeError, ValueError):
        return str(value)


def rebuild_coaches():
    coaches = json.loads((ROOT / "data/coaches.json").read_text())
    by_brand: dict[str, list] = {}
    for coach in coaches:
        by_brand.setdefault(coach.get("brand") or "other", []).append(coach)
    for brand, group in by_brand.items():
        group.sort(key=lambda c: (-int(c.get("year") or 0), c.get("stock") or ""))

    for coach in coaches:
        slug = coach["slug"]
        path = ROOT / "coaches" / slug / "index.html"
        if not path.exists():
            continue
        brand = coach.get("brand") or "other"
        group = by_brand.get(brand, [])
        idx = next((i for i, item in enumerate(group) if item["slug"] == slug), -1)
        prev_c = group[idx - 1] if idx > 0 else None
        next_c = group[idx + 1] if 0 <= idx < len(group) - 1 else None
        title = coach.get("title") or "Coach"
        floorplan = coach.get("floorplan") or ""
        if floorplan and floorplan.lower() not in title.lower():
            display_title = f"{title} {floorplan}"
        else:
            display_title = title
        price = money(coach.get("price"))
        msrp = money(coach.get("msrp"))
        monthly = money(coach.get("monthly"))
        condition = (coach.get("condition") or "").replace("-", " ").title()
        chips = []
        for label, key in (
            ("Year", "year"),
            ("Make", "make"),
            ("Model", "model"),
            ("Floorplan", "floorplan"),
            ("Slides", "slides"),
            ("Bath(s)", "baths"),
            ("Bunk Beds", "bunks"),
            ("Engine", "engine"),
            ("Mileage", "miles"),
            ("Stock #", "stock"),
        ):
            value = coach.get(key)
            if value in (None, "", "None", "none"):
                continue
            if key == "miles" and coach.get("condition") == "new" and (not value or value in (0, "0", "New")):
                value = "New"
            elif key == "miles" and isinstance(value, int):
                value = f"{value:,}"
            chips.append(f"<li><span>{label}</span><strong>{value}</strong></li>")
        actions = [
            f'<a class="btn" href="#request">Contact</a>',
            f'<a class="btn" href="/trade-rv">Value Your Trade</a>',
            f'<a class="btn" href="/rv-financing">Apply for Finance</a>',
        ]
        if coach.get("virtual"):
            actions.insert(0, f'<a class="btn" href="{coach["virtual"]}" target="_blank" rel="noreferrer">Virtual Tour</a>')
        nav = '<nav class="coach-turn" aria-label="Nearby coaches">'
        if prev_c:
            nav += f'<a class="btn" href="/coaches/{prev_c["slug"]}">Previous</a>'
        else:
            nav += '<span class="btn" aria-disabled="true">Previous</span>'
        if next_c:
            nav += f'<a class="btn" href="/coaches/{next_c["slug"]}">Next</a>'
        else:
            nav += '<span class="btn" aria-disabled="true">Next</span>'
        nav += "</nav>"
        image = coach.get("image") or ""
        form_coach = f'{coach.get("year","")} {coach.get("make","")} {coach.get("model","")} · Stock {coach.get("stock","")}'.strip()
        main = f"""
<article class="detail">
<div class="detail-top">
<p class="section-kicker">{condition or "Inventory"}</p>
<h1>{display_title}</h1>
<ul class="spec-chips">{''.join(chips)}</ul>
<div class="detail-pricing">
{f'<p class="msrp"><s>MSRP {msrp}</s></p>' if msrp else ''}
{f'<p class="detail-price">{price}</p>' if price else '<p class="detail-price">Call for price</p>'}
{f'<p class="monthly">Monthly Payment {monthly}</p>' if monthly else ''}
</div>
<div class="detail-actions">{''.join(actions)}</div>
</div>
<div class="detail-gallery"><figure><img src="{image}" alt="{display_title}" data-fallback="media"></figure></div>
{nav}
<div class="form-wrap" id="request"><div><h2>Ready to Make It Yours?</h2><p class="lede">Ask about this coach. The desk confirms it is still available before you travel.</p></div>
<form class="form" novalidate>
<input type="hidden" name="intent" value="coach-inquiry">
<input type="hidden" name="coach" value="{form_coach}">
<label>First name<input name="firstName" autocomplete="given-name" required><span class="error" data-for="firstName"></span></label>
<label>Last name<input name="lastName" autocomplete="family-name" required><span class="error" data-for="lastName"></span></label>
<label>Email<input name="email" type="email" autocomplete="email" required><span class="error" data-for="email"></span></label>
<label>Phone<input name="phone" type="tel" autocomplete="tel" required><span class="error" data-for="phone"></span></label>
<label class="wide">Message<textarea name="message" rows="5">I am interested in stock {coach.get("stock","")}.</textarea><span class="error" data-for="message"></span></label>
<label class="hp" aria-hidden="true">Company<input name="company" tabindex="-1" autocomplete="off"></label>
<p class="form-error wide" data-for="form"></p>
<div class="wide"><button class="btn-solid" type="submit">Contact Us Today</button></div>
</form></div>
</article>
""".strip()
        write_page(path, f"{display_title} - The Motorcoach Store", main)


def patch_homepage():
    path = ROOT / "index.html"
    text = path.read_text()
    text = replace_nav_footer(text)
    # Title casing for key homepage headings to match original presentation style.
    replacements = {
        "<h2>Big news for the future of luxury motor coaches</h2>": "<h2>BIG NEWS FOR THE FUTURE OF LUXURY MOTOR COACHES</h2>",
        "<h2>Exclusive Loki Coach dealer</h2>": "<h2>Exclusive Loki Coach Dealer</h2>",
        "<h2>Exceptional coaches. Unrivaled service.</h2>": "<h2>Exceptional Coaches. Unrivaled Service.</h2>",
        "<h2>The Motorcoach Store experience</h2>": "<h2>The Motorcoach Store Experience</h2>",
        "<h3>Private showroom appointments</h3>": "<h3>Private Showroom Appointments</h3>",
        "<h3>Concierge-level service</h3>": "<h3>Concierge-Level Service</h3>",
        "<h3>Comprehensive care</h3>": "<h3>Comprehensive Care</h3>",
        "<h3>Paint and body shop</h3>": "<h3>Paint &amp; Body Shop</h3>",
        "<h3>View our exclusive showrooms</h3>": "<h3>View Our Exclusive Showrooms</h3>",
        "<h3>Explore pre-owned coaches</h3>": "<h3>Explore Pre-Owned Coaches</h3>",
        "<h3>Service department</h3>": "<h3>Service Department</h3>",
        "<h3>Sell your coach</h3>": "<h3>Sell Your Coach</h3>",
        "<h2>Join our community</h2>": "<h2>Join Our Community</h2>",
        "<h2>Client testimonials</h2>": "<h2>Client Testimonials</h2>",
        "<h2>Begin your journey with confidence</h2>": "<h2>Begin Your Journey with Confidence</h2>",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    # Point panel/showroom CTAs at canonical explore and sell paths already rewritten.
    text = text.replace('href="/showrooms"', 'href="/explore-showrooms"')
    text = text.replace('href="/#buy-or-sell"', 'href="/sell-your-coach"')
    path.write_text(text)
    print("homepage updated")


def main():
    write_aliases()
    write_showrooms()
    write_page(ROOT / "contact/index.html", "Contact Us - The Motorcoach Store", contact_main(), ["/contact-us"])
    write_page(ROOT / "service/index.html", "Premium Motorcoach Service & Repairs - The Motorcoach Store", service_main(), ["/service"])
    write_page(ROOT / "paint-and-body/index.html", "Expert RV Paint & Body Repairs - The Motorcoach Store", paint_main(), ["/paint-and-body"])
    write_page(ROOT / "ceramic-coating/index.html", "Ceramic Coating for Your Motor Coach - The Motorcoach Store", ceramic_main(), ["/ceramic-coating", "/service"])
    write_page(ROOT / "fractional-ownership/index.html", "Fractional Motorcoach Ownership - The Motorcoach Store", fractional_main(), ["/fractionalmotorcoachownership-page"])
    write_page(ROOT / "about/index.html", "About The Motorcoach Store - Premium Motorcoach Dealership & Service", about_main(), ["/about"])
    rebuild_coaches()
    update_all_shells()
    patch_homepage()
    print("done")


if __name__ == "__main__":
    main()
