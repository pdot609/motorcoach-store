#!/usr/bin/env python3
"""Rebuild every local coach page as a faithful replica of themotorcoachstore.com coach PDPs.

Keeps local header/footer contacts (sales@ / service@themotorcoach.store, 941 283 2516)
and the local inquiry form / mail stack.
"""

from __future__ import annotations

import html as HTML
import json
import re
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COACHES_JSON = ROOT / "data" / "coaches.json"
SCRAPE_DIR = ROOT / "data" / "coach-scrapes"
ICONS_DIR = ROOT / "tools" / "coach_icons"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

ICON_MAP = {
    "build-sheet": "mcs-icon-build-sheet.svg",
    "floor-plan": "mcs-icon-floor-plan.svg",
    "check-in-sheet": "mcs-icon-check-in-sheet.svg",
    "virtual-tour": "mcs-icon-virtual-tour.svg",
    "contact-us": "mcs-icon-contact-us.svg",
    "value-your-trade": "mcs-icon-value-your-trade.svg",
    "apply-for-finance": "mcs-icon-apply-for-finance.svg",
    "video": "mcs-icon-video.svg",
}


def money(value):
    if value in (None, "", 0):
        return ""
    try:
        return f"${int(value):,}"
    except (TypeError, ValueError):
        text = str(value).strip()
        if text.startswith("$"):
            return text
        return text


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def clean_url(url: str) -> str:
    if not url:
        return ""
    url = url.replace("&amp;", "&").strip()
    url = re.sub(r"[?#].*$", "", url)
    return url


def extract_specs(html: str) -> list[tuple[str, str]]:
    specs = []
    for m in re.finditer(
        r'class="[^"]*mc-spec[^"]*"[\s\S]*?class="spec-label"[^>]*>(.*?)</[^>]+>[\s\S]*?class="spec-val"[^>]*>(.*?)</[^>]+>',
        html,
        re.I,
    ):
        label = re.sub(r"<[^>]+>", "", m.group(1)).strip()
        val = re.sub(r"<[^>]+>", "", m.group(2)).strip()
        if label and val and (label, val) not in specs:
            specs.append((label, val))
    if specs:
        return specs
    # fallback: label/value adjacent text blocks
    for m in re.finditer(
        r'<div class="mc-spec[^"]*"[\s\S]*?</div>\s*</div>',
        html,
        re.I,
    ):
        text = re.sub(r"<[^>]+>", " ", m.group(0))
        text = re.sub(r"\s+", " ", text).strip()
        parts = text.split(" ", 1)
        if len(parts) == 2:
            specs.append((parts[0], parts[1]))
    return specs


def extract_actions(html: str) -> dict:
    actions = {
        "build": "",
        "floor": "",
        "checkin": "",
        "virtual": "",
        "video": "",
    }
    patterns = {
        "build": r'class="[^"]*action-build[^"]*"[\s\S]{0,600}?<a[^>]+href="([^"]+)"',
        "floor": r'class="[^"]*action-floor-plan[^"]*"[\s\S]{0,600}?<a[^>]+href="([^"]+)"',
        "checkin": r'class="[^"]*action-check[^"]*"[\s\S]{0,600}?<a[^>]+href="([^"]+)"',
        "virtual": r'class="[^"]*action-virtual[^"]*"[\s\S]{0,600}?<a[^>]+href="([^"]+)"',
        "video": r'class="[^"]*action-video[^"]*"[\s\S]{0,600}?<a[^>]+href="([^"]+)"',
    }
    for key, pat in patterns.items():
        m = re.search(pat, html, re.I)
        if m:
            actions[key] = m.group(1).replace("&amp;", "&")
    # Matterport from lightbox iframe
    m = re.search(r'src="(https://my\.matterport\.com/show/\?m=[^"]+)"', html)
    if m:
        actions["matterport"] = m.group(1).replace("&amp;", "&")
    elif actions["virtual"].startswith("http") and "matterport" in actions["virtual"]:
        actions["matterport"] = actions["virtual"]
    else:
        actions["matterport"] = ""
    return actions


def extract_gallery(html: str, stock: str) -> list[str]:
    html = html.replace("&amp;", "&")
    stock = str(stock or "")
    urls: list[str] = []
    if stock:
        urls = re.findall(
            rf'https://www\.themotorcoachstore\.com/hs-fs/hubfs/Inventory/{re.escape(stock)}/Images/[^"\'?\s>]+\.(?:jpg|jpeg|png|webp)',
            html,
            re.I,
        )
    if not urls:
        urls = re.findall(
            r'https://www\.themotorcoachstore\.com/hs-fs/hubfs/Inventory/[^"\'?\s>]+/Images/[^"\'?\s>]+\.(?:jpg|jpeg|png|webp)',
            html,
            re.I,
        )
    if not urls:
        # Featherlite / stacker trailers use Stacker Trailer Photos/... paths
        urls = re.findall(
            r'https://www\.themotorcoachstore\.com/hs-fs/hubfs/Inventory/Stacker(?:%20| )Trailer(?:%20| )Photos/[^"\'?\s>]+\.(?:jpg|jpeg|png|webp)',
            html,
            re.I,
        )
    skip = ("motorcoach-theme", "LOGOS", "MARKETING", "footer-logo", "Begin%20Your")
    seen = []
    for u in urls:
        u = clean_url(u)
        if any(s in u for s in skip):
            continue
        if u not in seen:
            seen.append(u)
    return seen


def extract_hero(html: str, stock: str, fallback: str) -> str:
    html = html.replace("&amp;", "&")
    m = re.search(
        rf'https://www\.themotorcoachstore\.com/hs-fs/hubfs/Inventory/{re.escape(str(stock))}/[^"\'?\s>]*HERO[^"\'?\s>]*\.(?:jpg|jpeg|png|webp)',
        html,
        re.I,
    )
    if m:
        return clean_url(m.group(0))
    m = re.search(r'class="single-main-image"[^>]+src="([^"]+)"', html, re.I)
    if m:
        return clean_url(m.group(1).replace("&amp;", "&"))
    return fallback or ""


def extract_price(html: str, fallback) -> str:
    m = re.search(r'class="mc-card-price-value"[^>]*>([^<]+)', html)
    if m:
        return m.group(1).strip()
    return money(fallback)


def extract_title(html: str, fallback: str) -> str:
    m = re.search(r"<h1[^>]*>([\s\S]*?)</h1>", html, re.I)
    if m:
        return re.sub(r"<[^>]+>", "", m.group(1)).strip()
    return fallback


def extract_page_title(html: str, fallback: str) -> str:
    m = re.search(r"<title>([\s\S]*?)</title>", html, re.I)
    if m:
        return re.sub(r"\s+", " ", m.group(1)).strip()
    return fallback


def extract_condition(html: str, fallback: str) -> str:
    m = re.search(r'data-condition="([^"]+)"', html, re.I)
    if m:
        return m.group(1).strip().lower()
    return (fallback or "").replace("_", " ").lower()


def extract_pager(html: str) -> dict:
    prev_m = re.search(
        r'class="[^"]*pager-prev[^"]*"[\s\S]*?<a[^>]+href="([^"]+)"[\s\S]*?class="pager-title"[^>]*>([^<]+)',
        html,
        re.I,
    )
    if not prev_m:
        prev_m = re.search(
            r'Previous[\s\S]{0,200}?href="([^"]+/coach/[^"]+)"[\s\S]{0,200}?pager-title[^>]*>([^<]+)|href="([^"]+/coach/[^"]+)"[^>]*>\s*Previous[\s\S]*?([A-Za-z0-9][^<]{5,80})',
            html,
            re.I,
        )
    next_m = re.search(
        r'class="[^"]*pager-next[^"]*"[\s\S]*?<a[^>]+href="([^"]+)"[\s\S]*?class="pager-title"[^>]*>([^<]+)',
        html,
        re.I,
    )
    out = {"prev": None, "next": None}
    if prev_m:
        href = prev_m.group(1) or (prev_m.group(3) if prev_m.lastindex and prev_m.lastindex >= 3 else "")
        title = prev_m.group(2) or (prev_m.group(4) if prev_m.lastindex and prev_m.lastindex >= 4 else "")
        slug = coach_slug_from_href(href)
        if slug:
            out["prev"] = {"slug": slug, "title": re.sub(r"\s+", " ", title).strip()}
    if next_m:
        href = next_m.group(1)
        title = next_m.group(2)
        slug = coach_slug_from_href(href)
        if slug:
            out["next"] = {"slug": slug, "title": re.sub(r"\s+", " ", title).strip()}
    return out


def coach_slug_from_href(href: str) -> str:
    if not href:
        return ""
    href = href.replace("&amp;", "&")
    m = re.search(r"/coach/([^/?#]+)", href)
    return m.group(1).strip("/") if m else ""


def icon_svg(name: str, filter_id: str) -> str:
    path = ICONS_DIR / ICON_MAP[name]
    svg = path.read_text()
    return svg.replace("__FILTER__", filter_id)


def action_block(cls: str, href: str, label: str, icon_name: str, filter_id: str, attrs: str = "") -> str:
    if not href:
        return f'''<div class="col action-col {cls} action-disabled">
  <span class="action-col-btn" aria-disabled="true">
    <div class="action-col-img">{icon_svg(icon_name, filter_id)}</div>
    <div class="action-col-text">{HTML.escape(label)}</div>
  </span>
</div>'''
    return f'''<div class="col action-col {cls}">
  <a href="{HTML.escape(href)}" class="action-col-btn" {attrs}>
    <div class="action-col-img">{icon_svg(icon_name, filter_id)}</div>
    <div class="action-col-text">{HTML.escape(label)}</div>
  </a>
</div>'''


def load_shell() -> tuple[str, str]:
    sample = (ROOT / "coaches" / "2024-newell-p50quad-slide-bath-and-a-half-3" / "index.html").read_text()
    header = re.search(r'(<a class="skip"[\s\S]*?</header>)', sample).group(1)
    footer = re.search(r'(<footer class="site-footer">[\s\S]*?</footer>)', sample).group(1)
    return header, footer


def scrape_coach(coach: dict) -> dict:
    slug = coach["slug"]
    stock = str(coach.get("stock") or "")
    url = f"https://www.themotorcoachstore.com/coach/{slug}?hsLang=en"
    cache = SCRAPE_DIR / f"{slug}.json"
    try:
        html = fetch(url)
    except Exception as exc:
        return {"slug": slug, "ok": False, "error": f"{type(exc).__name__}: {exc}", "url": url}

    page_title = extract_page_title(html, f"{coach.get('title')} - The Motorcoach Store")
    h1 = extract_title(html, coach.get("title") or "Coach")
    condition = extract_condition(html, coach.get("condition") or "")
    if "certified" in condition:
        condition_attr = "certified pre-owned"
    elif "pre" in condition:
        condition_attr = "pre-owned"
    elif condition == "new":
        condition_attr = "new"
    else:
        condition_attr = condition or "pre-owned"

    data = {
        "slug": slug,
        "ok": True,
        "url": url,
        "pageTitle": page_title,
        "h1": h1,
        "condition": condition_attr,
        "price": extract_price(html, coach.get("price")),
        "hero": extract_hero(html, stock, coach.get("image") or ""),
        "specs": extract_specs(html),
        "actions": extract_actions(html),
        "gallery": extract_gallery(html, stock),
        "pager": extract_pager(html),
        "stock": stock,
        "scrapedAt": int(time.time()),
    }
    # Fallback specs from coaches.json if scrape missed
    if not data["specs"]:
        mapping = [
            ("Slides", coach.get("slides")),
            ("Bath(s)", coach.get("baths")),
            ("Bunk Beds", coach.get("bunks")),
            ("Floorplan", coach.get("floorplan")),
            ("Engine", coach.get("engine")),
            ("Mileage", f"{coach.get('miles'):,}" if isinstance(coach.get("miles"), int) else coach.get("miles")),
        ]
        data["specs"] = [(k, str(v)) for k, v in mapping if v not in (None, "")]

    cache.write_text(json.dumps(data, indent=2))
    return data


def render_page(coach: dict, scraped: dict, header: str, footer: str) -> str:
    slug = coach["slug"]
    stock = scraped.get("stock") or coach.get("stock") or ""
    h1 = scraped.get("h1") or coach.get("title") or "Coach"
    page_title = scraped.get("pageTitle") or f"{h1} - The Motorcoach Store"
    condition = scraped.get("condition") or "pre-owned"
    price = scraped.get("price") or money(coach.get("price")) or "Call for price"
    hero = scraped.get("hero") or coach.get("image") or ""
    gallery = scraped.get("gallery") or []
    actions = scraped.get("actions") or {}
    specs = scraped.get("specs") or []
    pager = scraped.get("pager") or {}

    build = actions.get("build") or ""
    floor = actions.get("floor") or ""
    checkin = actions.get("checkin") or ""
    video = actions.get("video") or ""
    matterport = actions.get("matterport") or ""

    # disable empty docs
    def maybe(url: str) -> str:
        if not url or url in {"#", ""}:
            return ""
        if url.startswith("#lb-virtual") and matterport:
            return "#virtual-tour"
        if url.startswith("#"):
            return ""
        return url

    build = maybe(build)
    floor = maybe(floor)
    checkin = maybe(checkin)
    if video and video.startswith("#"):
        video = ""

    specs_html = "\n".join(
        f'<div class="mc-spec"><span class="spec-label">{HTML.escape(label)}</span><span class="spec-val">{HTML.escape(val)}</span></div>'
        for label, val in specs
    )
    gallery_html = "\n".join(
        f'<a href="{HTML.escape(u)}" class="js-lb-gallery" data-gallery="coach"><figure>'
        f'<img src="{HTML.escape(u)}?width=960" srcset="{HTML.escape(u)}?width=640 640w, {HTML.escape(u)}?width=960 960w, {HTML.escape(u)}?width=1400 1400w" '
        f'sizes="(max-width: 1500px) 100vw, 1500px" alt="{HTML.escape(h1)}" loading="lazy" decoding="async"></figure></a>'
        for u in gallery
    )

    prev = pager.get("prev")
    next_ = pager.get("next")
    prev_html = (
        f'''<div class="single-pager pager-prev">
      <a href="coaches/{HTML.escape(prev['slug'])}">
        <span><span class="pager-label">Previous</span><span class="pager-title">{HTML.escape(prev['title'])}</span></span>
      </a>
    </div>'''
        if prev
        else '<div class="single-pager pager-prev"></div>'
    )
    next_html = (
        f'''<div class="single-pager pager-next">
      <a href="coaches/{HTML.escape(next_['slug'])}">
        <span><span class="pager-label">Next</span><span class="pager-title">{HTML.escape(next_['title'])}</span></span>
      </a>
    </div>'''
        if next_
        else '<div class="single-pager pager-next"></div>'
    )

    virtual_block = ""
    virtual_action_href = "#virtual-tour" if matterport else ""
    virtual_attrs = 'data-open-virtual' if matterport else ""
    if matterport:
        virtual_block = f'''
<div id="virtual-tour" class="coach-lightbox" hidden>
  <div class="lb-frame video-frame">
    <button type="button" class="lb-close" data-close-lb aria-label="Close">×</button>
    <iframe src="about:blank" data-src="{HTML.escape(matterport)}" title="Virtual tour" allowfullscreen allow="autoplay; fullscreen; web-share; xr-spatial-tracking"></iframe>
  </div>
</div>'''

    form_coach = f"{h1} · Stock {stock}".strip(" ·")
    desc = f"{h1} at The Motorcoach Store in Bradenton, Florida. Stock {stock}."

    main = f'''<main id="content" class="coach-page showroom-single-content" data-condition="{HTML.escape(condition)}">
<section class="main-image-section">
  <div class="row row-fullw main-image-row">
    <div class="col">
      <div class="media">
        <img class="single-main-image" src="{HTML.escape(hero)}{'?width=1400' if hero and '?' not in hero else ''}" srcset="{HTML.escape(hero)}?width=800 800w, {HTML.escape(hero)}?width=1400 1400w, {HTML.escape(hero)}?width=2000 2000w" sizes="100vw" alt="{HTML.escape(h1)}" width="1400" loading="eager" fetchpriority="high" decoding="async">
      </div>
    </div>
  </div>
</section>

<section class="common-info-section">
  <div class="inner">
    <div class="row title-row"><h1>{HTML.escape(h1)}</h1></div>
    <div class="row coach-info-row">
      <div class="row row-fullw specs-bar-row">
        {specs_html}
      </div>
      <div class="row row-fullw action-bar-row two-row">
        {action_block('action-build', build, 'Build sheet', 'build-sheet', f'f{stock}a', 'target="_blank" rel="noopener noreferrer"')}
        {action_block('action-floor-plan', floor, 'Floor plan', 'floor-plan', f'f{stock}b', 'target="_blank" rel="noopener noreferrer"')}
        {action_block('action-check', checkin, 'Check in sheet', 'check-in-sheet', f'f{stock}c', 'target="_blank" rel="noopener noreferrer"')}
        {action_block('action-virtual', virtual_action_href, 'Virtual tour', 'virtual-tour', f'f{stock}d', virtual_attrs)}
        {action_block('action-call-now', '#request', 'Contact Us', 'contact-us', f'f{stock}e')}
        {action_block('action-value-trade', 'trade-rv', 'Value Your Trade', 'value-your-trade', f'f{stock}f')}
        {action_block('action-apply-finance', 'rv-financing', 'Apply for Finance', 'apply-for-finance', f'f{stock}g')}
        {action_block('action-video', video, 'Video', 'video', f'f{stock}h', 'target="_blank" rel="noopener noreferrer"' if video else '')}
      </div>
      <div class="row row-fullw foot-info-row">
        <div class="col price-wrap-col">
          <div class="mc-card-price"><span class="mc-card-price-value">{HTML.escape(price)}</span></div>
        </div>
      </div>
    </div>
  </div>
</section>

<div class="section gallery-section">
  <div class="row gallery-row">
    <div class="gallery">
{gallery_html}
    </div>
  </div>
</div>

<section class="single-pager-section">
  <div class="row pager-row">
    {prev_html}
    {next_html}
  </div>
</section>

<section class="common-info-section">
  <div class="inner">
    <div class="row coach-info-row">
      <div class="row row-fullw foot-info-row">
        <div class="col price-wrap-col">
          <div class="mc-card-price"><span class="mc-card-price-value">{HTML.escape(price)}</span></div>
          <p class="after-price-info">Get approved today by filling out a <a href="rv-financing">financing application</a>!</p>
        </div>
        <div class="links-col">
          <a class="btn" href="#request">Contact Us</a>
          <a class="btn" href="trade-rv">Value Trade</a>
        </div>
      </div>
    </div>
  </div>
</section>

<section class="ready-band" id="request">
  <h2>Ready to Make It Yours?</h2>
  <p class="lede">Have questions or want to schedule a personal walk-through? Our team is here to help you every step of the way.</p>
  <div class="ready-actions">
    <a class="btn" href="schedule-appointment">Schedule Appointment</a>
    <a class="btn btn-solid" href="#inquiry-form">Contact Us Today</a>
  </div>
  <div class="form-wrap" id="inquiry-form">
    <form class="form" novalidate>
      <input type="hidden" name="intent" value="coach-inquiry">
      <input type="hidden" name="coach" value="{HTML.escape(form_coach)}">
      <label>First name<input name="firstName" autocomplete="given-name" required><span class="error" data-for="firstName"></span></label>
      <label>Last name<input name="lastName" autocomplete="family-name" required><span class="error" data-for="lastName"></span></label>
      <label>Email<input name="email" type="email" autocomplete="email" required><span class="error" data-for="email"></span></label>
      <label>Phone<input name="phone" type="tel" autocomplete="tel" required><span class="error" data-for="phone"></span></label>
      <label class="wide">Message<textarea name="message" rows="5">I am interested in {HTML.escape(h1)} (stock {HTML.escape(str(stock))}).</textarea><span class="error" data-for="message"></span></label>
      <label class="hp" aria-hidden="true">Company<input name="company" tabindex="-1" autocomplete="off"></label>
      <p class="form-error wide" data-for="form"></p>
      <div class="wide"><button class="btn-solid" type="submit">Contact Us Today</button></div>
    </form>
  </div>
</section>
{virtual_block}
<div id="gallery-lb" class="coach-lightbox" hidden>
  <div class="lb-frame">
    <button type="button" class="lb-close" data-close-lb aria-label="Close">×</button>
    <button type="button" class="lb-prev" data-lb-prev aria-label="Previous">‹</button>
    <button type="button" class="lb-next" data-lb-next aria-label="Next">›</button>
    <img src="" alt="Coach photo">
  </div>
</div>
</main>'''

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{HTML.escape(page_title)}</title>
  <meta name="description" content="{HTML.escape(desc)}">
  <link rel="icon" href="https://www.themotorcoachstore.com/hubfs/raw_assets/public/motorcoach-theme/images/favicon/favicon-32x32.png">
  <link rel="preconnect" href="https://www.themotorcoachstore.com" crossorigin>
  <link rel="preconnect" href="https://47169059.fs1.hubspotusercontent-na1.net" crossorigin>
  <link rel="dns-prefetch" href="https://my.matterport.com">
    <script>
(function () {{
  var base = "/";
  if (/\\.github\\.io$/i.test(location.hostname)) {{
    var seg = location.pathname.split("/").filter(Boolean)[0];
    if (seg) base = "/" + seg + "/";
  }}
  document.write('<base href="' + base + '">');
  window.__SITE_BASE__ = base;
}})();
</script>
<link rel="stylesheet" href="css/site.css">
<link rel="stylesheet" href="css/coach-detail.css">
</head>
<body>
  {header}
  {main}
  {footer}
  <script defer src="js/base-path.js"></script>
  <script defer src="js/site.js"></script>
  <script defer src="js/mail-config.js"></script>
  <script defer src="js/form.js"></script>
  <script defer src="js/coach-detail.js"></script>
</body>
</html>
'''


def merge_into_coaches_json(scraped_list: list[dict]) -> None:
    coaches = json.loads(COACHES_JSON.read_text())
    by_slug = {c["slug"]: c for c in coaches}
    for scraped in scraped_list:
        if not scraped.get("ok"):
            continue
        c = by_slug.get(scraped["slug"])
        if not c:
            continue
        if scraped.get("h1"):
            c["title"] = scraped["h1"]
        if scraped.get("hero"):
            c["image"] = scraped["hero"]
        # Keep listing JSON lean — full galleries live on coach PDPs only.
        c.pop("gallery", None)
        actions = scraped.get("actions") or {}
        if actions.get("matterport"):
            c["virtual"] = True
            c["virtualTour"] = actions["matterport"]
        if actions.get("video"):
            c["video"] = actions["video"]
        docs = {}
        if actions.get("build"):
            docs["buildSheet"] = actions["build"]
        if actions.get("floor"):
            docs["floorPlan"] = actions["floor"]
        if actions.get("checkin"):
            docs["checkInSheet"] = actions["checkin"]
        if docs:
            c["documents"] = docs
        pager = scraped.get("pager") or {}
        if pager.get("prev"):
            c["prev"] = pager["prev"]
        if pager.get("next"):
            c["next"] = pager["next"]
        # sync common specs
        for label, val in scraped.get("specs") or []:
            key = {
                "slides": "slides",
                "bath(s)": "baths",
                "bunk beds": "bunks",
                "floorplan": "floorplan",
                "engine": "engine",
                "mileage": "miles",
            }.get(label.lower())
            if not key:
                continue
            if key == "miles":
                digits = re.sub(r"[^\d]", "", val)
                c[key] = int(digits) if digits else val
            else:
                c[key] = val
    COACHES_JSON.write_text(json.dumps(coaches, indent=2) + "\n")


def main():
    SCRAPE_DIR.mkdir(parents=True, exist_ok=True)
    coaches = json.loads(COACHES_JSON.read_text())
    header, footer = load_shell()

    print(f"scraping {len(coaches)} coaches…")
    scraped_list = []
    # sequential-ish with small pool to avoid hammering HubSpot
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(scrape_coach, c): c["slug"] for c in coaches}
        done = 0
        for fut in as_completed(futures):
            slug = futures[fut]
            result = fut.result()
            scraped_list.append(result)
            done += 1
            status = "OK" if result.get("ok") else f"FAIL {result.get('error')}"
            gal = len(result.get("gallery") or [])
            print(f"[{done}/{len(coaches)}] {slug[:70]} {status} gallery={gal}")

    ok = [s for s in scraped_list if s.get("ok")]
    fail = [s for s in scraped_list if not s.get("ok")]
    print(f"scrape done ok={len(ok)} fail={len(fail)}")
    if fail:
        for f in fail:
            print("  FAIL", f["slug"], f.get("error"))

    print("writing pages…")
    by_slug = {s["slug"]: s for s in scraped_list}
    written = 0
    for coach in coaches:
        scraped = by_slug.get(coach["slug"])
        if not scraped or not scraped.get("ok"):
            # keep existing page if scrape failed
            continue
        html = render_page(coach, scraped, header, footer)
        path = ROOT / "coaches" / coach["slug"] / "index.html"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(html)
        written += 1
    print(f"wrote {written} pages")
    merge_into_coaches_json(scraped_list)
    print("updated data/coaches.json")


if __name__ == "__main__":
    main()
