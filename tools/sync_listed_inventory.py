#!/usr/bin/env python3
"""Prune to original active listings and rebuild pages as close replicas."""

from __future__ import annotations

import json
import re
import shutil
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UA = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

PRICE_OVERRIDES = {
    "2912": (2272315, "$2,272,315"),
    "3022": (433333, "$433,333"),
}

LISTING_SOURCES = [
    ("https://www.themotorcoachstore.com/motorcoach-showroom-new-prevost-loki-coach/", "showrooms/prevost-loki/index.html", "mc"),
    ("https://www.themotorcoachstore.com/motorcoach-showroom-ogv/", "showrooms/ogv/index.html", "mc"),
    ("https://www.themotorcoachstore.com/motorcoach-showroom-new-adventure-showhauler/", "showrooms/adventure/index.html", "mc"),
    ("https://www.themotorcoachstore.com/motorcoach-showroom-new-featherlite-stacker-trailers/", "showrooms/featherlite/index.html", "mc"),
    ("https://www.themotorcoachstore.com/new-coaches", "new-coaches/index.html", "mc"),
    ("https://www.themotorcoachstore.com/pre-owned-old/", "pre-owned/index.html", "mc"),
    ("https://www.themotorcoachstore.com/coaches/new", "coaches/new/index.html", "unit"),
    ("https://www.themotorcoachstore.com/coaches/pre-owned", "coaches/pre-owned/index.html", "unit"),
    ("https://www.themotorcoachstore.com/coaches/certified", "coaches/certified/index.html", "unit"),
]

JUNK = {"certified", "stacker-trailers", "new", "pre-owned", "inventory", "compare", "sold"}

JOURNEY = """
<section class="journey">
  <div class="band-media"><img src="https://www.themotorcoachstore.com/hs-fs/hubfs/Begin%20Your%20Journey%20with%20Confidence-1.webp?width=1400&name=Begin%20Your%20Journey%20with%20Confidence-1.webp" alt="" loading="lazy" decoding="async"></div>
  <div class="journey-copy">
    <h2>Begin Your Journey with Confidence</h2>
    <p class="lede" style="margin:0 auto 22px">Contact our team today to schedule a personalized consultation or showroom visit. Your luxury motor coach is waiting.</p>
    <div class="inline-actions"><a class="btn" href="schedule-appointment">Schedule Appointment</a></div>
  </div>
</section>
"""


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=90) as res:
        return res.read().decode("utf-8", "ignore")


def slice_div(html: str, start: int) -> tuple[int, int]:
    tag_end = html.find(">", start) + 1
    depth = 1
    i = tag_end
    while i < len(html) and depth > 0:
        if html.startswith("</div>", i):
            depth -= 1
            i += 6
        elif html.startswith("<div", i):
            depth += 1
            i += 4
        else:
            i += 1
    return start, i


def chrome_parts() -> tuple[str, str, str, str]:
    src = (ROOT / "index.html").read_text(encoding="utf-8")
    for candidate in ["index.html", "new-coaches/index.html", "pre-owned/index.html"]:
        path = ROOT / candidate
        if not path.exists():
            continue
        src = path.read_text(encoding="utf-8")
        if 'class="site-header"' in src and 'class="site-footer"' in src:
            break
    head_boot = re.search(
        r"(<script>\s*\(function \(\) \{\s*var base[\s\S]+?</script>\s*)",
        src,
    ).group(1)
    header = re.search(r'(<header class="site-header">[\s\S]+?</header>)', src).group(1)
    footer = re.search(r'(<footer class="site-footer">[\s\S]+?</footer>)', src).group(1)
    skip = '<a class="skip" href="#content">Skip to content</a>'
    return head_boot, skip, header, footer


def rewrite_content(html: str) -> str:
    html = html.replace("sales@themotorcoachstore.com", "sales@themotorcoach.store")
    html = html.replace("service@themotorcoachstore.com", "service@themotorcoach.store")
    html = html.replace("mailto:sales@themotorcoachstore.com", "mailto:sales@themotorcoach.store")
    html = html.replace("mailto:service@themotorcoachstore.com", "mailto:service@themotorcoach.store")
    html = html.replace("941-896-4819", "941 283 2516")
    html = html.replace("941.896.4819", "941 283 2516")
    html = re.sub(
        r'href="https://www\.themotorcoachstore\.com/(coach|inventory)/([^"?#]+)(?:\?[^"]*)?"',
        r'href="coaches/\2"',
        html,
    )
    html = re.sub(r'href="/(coach|inventory)/([^"?#]+)(?:\?[^"]*)?"', r'href="coaches/\2"', html)
    html = re.sub(
        r'href="https://www\.themotorcoachstore\.com/coaches/([^"?#]+)(?:\?[^"]*)?"',
        r'href="coaches/\1"',
        html,
    )
    html = re.sub(r'href="/coaches/([^"?#]+)(?:\?[^"]*)?"', r'href="coaches/\1"', html)
    html = re.sub(r'href="/contact#contact-form"', 'href="contact-us"', html)
    html = re.sub(r'href="/contact"', 'href="contact-us"', html)
    html = re.sub(r'href="/pre-owned"', 'href="pre-owned"', html)
    html = re.sub(r'href="/explore-showrooms"', 'href="explore-showrooms"', html)
    html = re.sub(r'href="/schedule[^"]*"', 'href="schedule-appointment"', html)
    html = re.sub(r'href="/new-coaches"', 'href="new-coaches"', html)
    html = re.sub(r'href="/certified-pre-owned"', 'href="certified-pre-owned"', html)
    html = re.sub(r"\?hsLang=en", "", html)
    return html


def extract_asset_links(html: str) -> tuple[list[str], list[str]]:
    css = []
    for href in re.findall(r'<link[^>]+rel=["\']stylesheet["\'][^>]+href=["\']([^"\']+)["\']', html, re.I):
        if href not in css:
            css.append(href)
    for href in re.findall(r'<link[^>]+href=["\']([^"\']+)["\'][^>]+rel=["\']stylesheet["\']', html, re.I):
        if href not in css:
            css.append(href)
    # Keep only theme/module CSS that drives listing layout responsiveness
    keep = []
    for href in css:
        h = href.lower()
        if any(
            key in h
            for key in (
                "template_main",
                "module_dev_dynamic",
                "module_site-header",
                "sal.min.css",
                "swiper",
                "glightbox",
                "listing",
                "coming_soon",
                "preowned-sec01",
            )
        ):
            if href.startswith("//"):
                href = "https:" + href
            elif href.startswith("/"):
                href = "https://www.themotorcoachstore.com" + href
            keep.append(href)
    js = []
    for src in re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', html, re.I):
        s = src.lower()
        if any(k in s for k in ("sal.min", "swiper", "glightbox")):
            if src.startswith("//"):
                src = "https:" + src
            elif src.startswith("/"):
                src = "https://www.themotorcoachstore.com" + src
            if src not in js:
                js.append(src)
    return keep, js


def extract_mc_main(html: str) -> str:
    hero = re.search(r'<div[^>]*class="[^"]*showroom-hero-section[^"]*"', html)
    show = re.search(r'<div[^>]*class="[^"]*mc-showroom[^"]*"', html)
    if show and hero:
        if html[hero.start() : hero.start() + 8].startswith("<section"):
            hero_end = html.find("</section>", hero.start()) + len("</section>")
        else:
            _, hero_end = slice_div(html, hero.start())
        _, show_end = slice_div(html, show.start())
        mid = html[hero_end : show.start()]
        return rewrite_content(html[hero.start() : hero_end] + mid + html[show.start() : show_end] + JOURNEY)
    if show:
        _, show_end = slice_div(html, show.start())
        return rewrite_content(html[show.start() : show_end] + JOURNEY)
    raise RuntimeError("mc-showroom not found")


def extract_unit_main(html: str) -> str:
    start = html.find('<section class=" hero">')
    if start < 0:
        start = html.find('<section class="hero">')
    footer = html.find("<footer")
    if start < 0 or footer < 0:
        raise RuntimeError("unit listing bounds missing")
    chunk = html[start:footer]
    last = chunk.rfind("</article>")
    if last < 0:
        raise RuntimeError("no unit articles")
    last_end = last + len("</article>")
    tail = chunk[last_end : last_end + 2500]
    close = re.match(r"(\s*</div>){1,12}", tail)
    end = last_end + (close.end() if close else 0)
    main = rewrite_content(chunk[:end])
    if "data-empty" not in main:
        main += '\n<p class="listing-empty" data-empty hidden>No coaches match these filters.</p>\n'
    return main


def apply_price_overrides(html: str) -> str:
    for stock, (raw, fmt) in PRICE_OVERRIDES.items():
        def fix(m, _stock=stock, _raw=raw, _fmt=fmt):
            card = m.group(0)
            hit = (
                f'data-stock="{_stock}"' in card
                or f"Stock #{_stock}" in card
                or f"<b>{_stock}</b>" in card
                or f"-{_stock}\"" in card
                or f"-{_stock}/" in card
                or f"-{_stock}<" in card
            )
            if not hit:
                return card
            card = re.sub(r'data-price="\d+"', f'data-price="{_raw}"', card)
            card = re.sub(r'class="mc-card-price-value">\$[0-9,]+', f'class="mc-card-price-value">{_fmt}', card)
            card = re.sub(r'class="unit__price">\$[0-9,]+', f'class="unit__price">{_fmt}', card)
            return card

        html = re.sub(r'<article class="(?:mc-card|unit)"[\s\S]*?</article>', fix, html)

    # Sync facet price min/max to actual card prices so filters cannot hide units
    prices = [int(p) for p in re.findall(r'data-price="(\d+)"', html)]
    if prices:
        pmin, pmax = min(prices), max(prices)
        html = re.sub(
            r'("price":\{"max":)\d+(,"min":)\d+(\})',
            lambda m: f"{m.group(1)}{pmax}{m.group(2)}{pmin}{m.group(3)}",
            html,
        )
        html = re.sub(
            r'("price":\{"min":)\d+(,"max":)\d+(\})',
            lambda m: f"{m.group(1)}{pmin}{m.group(2)}{pmax}{m.group(3)}",
            html,
        )
        html = re.sub(
            r'(data-price-filter[^>]*data-max=")[^"]+(")',
            rf'\g<1>{max(pmax, 2696533)}\2',
            html,
            count=1,
        )
        html = html.replace('data-max="2000000"', f'data-max="{max(pmax, 2696533)}"')
    return html


def wrap_page(
    *,
    title: str,
    description: str,
    remote_css: list[str],
    local_css: list[str],
    body_class: str,
    main_html: str,
    remote_js: list[str],
    local_js: list[str],
) -> str:
    boot, skip, header, footer = chrome_parts()
    css_links = "\n".join(f'<link rel="stylesheet" href="{href}">' for href in remote_css + local_css)
    script_tags = "\n".join(f'<script defer src="{src}"></script>' for src in remote_js + local_js)
    main_class = ' class="mc-listing-page"' if "mc-showroom" in main_html else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <meta name="description" content="{description}">
  <link rel="icon" href="https://www.themotorcoachstore.com/hubfs/raw_assets/public/motorcoach-theme/images/favicon/favicon-32x32.png">
  <link rel="preconnect" href="https://www.themotorcoachstore.com" crossorigin>
  <link rel="preconnect" href="https://47169059.fs1.hubspotusercontent-na1.net" crossorigin>
  <link rel="dns-prefetch" href="https://my.matterport.com">
  {boot}
{css_links}
</head>
<body{f' class="{body_class}"' if body_class else ""}>
  {skip}
  {header}
  <main id="content"{main_class}>
{main_html}
  </main>
  {footer}
  {script_tags}
</body>
</html>
"""


def discover_listed() -> tuple[set[str], set[str]]:
    stocks: set[str] = set()
    slugs: set[str] = set()
    for url, _, _ in LISTING_SOURCES:
        html = fetch(url)
        stocks |= set(re.findall(r'data-stock="([^"]+)"', html))
        stocks |= set(re.findall(r"Stock #(\d+)", html))
        found = set(re.findall(r"/(?:coach|inventory|coaches)/([a-z0-9][a-z0-9\-]+)", html, re.I))
        slugs |= {s for s in found if s.lower() not in JUNK and len(s) > 8}
    return stocks, slugs


def prune_coaches(listed_slugs: set[str]) -> list[dict]:
    path = ROOT / "data/coaches.json"
    coaches = json.loads(path.read_text())
    kept = []
    for c in coaches:
        if c.get("slug") in listed_slugs:
            stock = str(c.get("stock") or "")
            if stock in PRICE_OVERRIDES:
                c["price"] = PRICE_OVERRIDES[stock][0]
            # Force listed units available unless original slug/title says sold
            if "sold" not in (c.get("slug") or "").lower():
                c["status"] = "available"
            kept.append(c)
    path.write_text(json.dumps(kept, indent=2) + "\n")
    print(f"coaches.json pruned {len(coaches)} -> {len(kept)}")
    return kept


def prune_coach_dirs(listed_slugs: set[str]) -> None:
    coaches_dir = ROOT / "coaches"
    removed = 0
    for path in coaches_dir.iterdir():
        if not path.is_dir():
            continue
        if path.name in {"new", "pre-owned", "certified"}:
            continue
        if path.name not in listed_slugs:
            shutil.rmtree(path)
            removed += 1
    # scrapes
    scrape_dir = ROOT / "data/coach-scrapes"
    if scrape_dir.exists():
        for path in scrape_dir.glob("*.json"):
            if path.stem not in listed_slugs:
                path.unlink()
    print(f"removed {removed} unlisted coach directories")


def rebuild_listings() -> None:
    titles = {
        "showrooms/prevost-loki/index.html": (
            "New Prevost Loki Coaches - The Motorcoach Store",
            "Browse new Prevost Loki coaches at The Motorcoach Store in Bradenton, Florida.",
            "",
        ),
        "showrooms/ogv/index.html": (
            "OGV Luxury Coach Showroom - The Motorcoach Store",
            "Browse new OGV Luxury Coaches at The Motorcoach Store.",
            "",
        ),
        "showrooms/adventure/index.html": (
            "Adventure by ShowHauler Showroom - The Motorcoach Store",
            "Browse new Adventure by ShowHauler coaches at The Motorcoach Store.",
            "",
        ),
        "showrooms/featherlite/index.html": (
            "Featherlite Stacker Trailers - The Motorcoach Store",
            "Browse new Featherlite stacker trailers at The Motorcoach Store.",
            "",
        ),
        "new-coaches/index.html": (
            "New Coaches - The Motorcoach Store",
            "Browse new luxury motor coaches at The Motorcoach Store.",
            "",
        ),
        "pre-owned/index.html": (
            "Pre-Owned Motorcoaches - The Motorcoach Store",
            "Browse pre-owned luxury motor coaches at The Motorcoach Store in Bradenton, Florida.",
            "",
        ),
        "coaches/new/index.html": (
            "New Luxury Motorcoaches for Sale | The Motorcoach Store",
            "Explore new luxury motor coaches and stacker trailers at The Motorcoach Store.",
            "page-coaches-new",
        ),
        "coaches/pre-owned/index.html": (
            "Pre-Owned Luxury Motorcoaches | The Motorcoach Store",
            "Explore pre-owned luxury motor coaches at The Motorcoach Store.",
            "page-coaches-preowned",
        ),
        "coaches/certified/index.html": (
            "Certified Pre-Owned Motorcoaches | The Motorcoach Store",
            "Explore certified pre-owned luxury motor coaches at The Motorcoach Store.",
            "page-coaches-certified",
        ),
    }

    for url, rel, kind in LISTING_SOURCES:
        html = fetch(url)
        remote_css, remote_js = extract_asset_links(html)
        if kind == "mc":
            main = extract_mc_main(html)
            local_css = ["css/site.css", "css/mc-showroom.css"]
            local_js = ["js/base-path.js", "js/site.js", "js/mc-showroom.js?v=20261104c"]
        else:
            main = extract_unit_main(html)
            local_css = ["css/site.css", "css/coaches-new.css", "css/listing-grid.css"]
            local_js = ["js/base-path.js", "js/site.js", "js/coaches-new.js"]
        title, desc, body = titles[rel]
        page = wrap_page(
            title=title,
            description=desc,
            remote_css=remote_css,
            local_css=local_css,
            body_class=body,
            main_html=main,
            remote_js=remote_js,
            local_js=local_js,
        )
        page = apply_price_overrides(page)
        # Showrooms: show all cards (no accidental pagination hide)
        if kind == "mc" and "pre-owned" in rel:
            page = re.sub(r'data-page-size="\d+"', 'data-page-size="100"', page, count=1)
            page = re.sub(r'data-loadmore="\d+"', 'data-loadmore="0"', page, count=1)
        out = ROOT / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(page, encoding="utf-8")
        n = page.count('article class="mc-card"') + page.count('article class="unit"')
        print(f"wrote {rel} items={n} remote_css={len(remote_css)}")


def rebuild_explore(listed_slugs: set[str], coaches: list[dict]) -> None:
    path = ROOT / "data/explore-showrooms.json"
    data = json.loads(path.read_text()) if path.exists() else {"bands": []}

    def money(v):
        return f"${int(v):,}" if v else None

    def cards_for(pred, limit=8):
        items = [
            c
            for c in coaches
            if c.get("slug") in listed_slugs
            and c.get("status") == "available"
            and pred(c)
        ]
        items.sort(key=lambda c: (-(c.get("created") or 0), -(c.get("price") or 0)))
        out = []
        for c in items[:limit]:
            title = c.get("title") or ""
            model = (c.get("model") or "").upper()
            if "loki" in title.lower() and model and model.upper() not in title.upper():
                # LC026 etc already in model field
                m = re.search(r"lc0?\d+", model, re.I)
                if m and m.group(0).upper() not in title.upper():
                    title = f"{title} {m.group(0).upper()}"
            out.append(
                {
                    "href": f"/coaches/{c['slug']}",
                    "image": c.get("image") or "",
                    "alt": title,
                    "title": title,
                    "msrp": None,
                    "price": money(c.get("price")),
                    "monthly": None,
                }
            )
        return out

    brand_map = {
        "loki": lambda c: "loki" in f"{c.get('slug')} {c.get('title')} {c.get('model')}".lower(),
        "ogv": lambda c: "ogv" in f"{c.get('slug')} {c.get('title')}".lower(),
        "adventure": lambda c: "showhauler" in f"{c.get('slug')} {c.get('title')}".lower()
        or "adventure" in f"{c.get('slug')} {c.get('title')}".lower(),
        "featherlite": lambda c: "featherlite" in f"{c.get('slug')} {c.get('title')}".lower()
        or "stacker" in f"{c.get('slug')} {c.get('title')}".lower(),
    }
    for band in data.get("bands") or []:
        bid = band.get("id") or ""
        if bid in brand_map:
            band["cards"] = cards_for(brand_map[bid])
    path.write_text(json.dumps(data, indent=2) + "\n")
    print("updated explore-showrooms.json")


def patch_responsive_css() -> None:
    """Ensure showroom grids don't overflow on small screens."""
    path = ROOT / "css/mc-showroom.css"
    css = path.read_text() if path.exists() else ""
    marker = "/* replica-responsive */"
    block = f"""
{marker}
.mc-listing-page, .mc-showroom {{ overflow-x: clip; }}
.mc-showroom__grid.row, .mc-showroom__grid {{
  display: grid !important;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 320px), 1fr));
  gap: 24px;
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
}}
.mc-showroom .mc-card {{
  width: 100% !important;
  max-width: 100%;
  min-width: 0;
  box-sizing: border-box;
}}
.mc-showroom .mc-card-media img {{
  width: 100%;
  height: auto;
  max-width: 100%;
  object-fit: cover;
}}
.mc-showroom__bar, .mc-showroom__filters, .mc-filters, .mc-showroom .row {{
  max-width: 100%;
  box-sizing: border-box;
}}
@media (max-width: 767px) {{
  .mc-showroom__grid.row, .mc-showroom__grid {{
    grid-template-columns: 1fr;
    gap: 18px;
  }}
  .showroom-hero-section, .page-hero, .mc-listing-page img {{
    max-width: 100%;
  }}
  .mc-showroom__bar, .mc-filters {{
    flex-wrap: wrap;
  }}
}}
"""
    if marker in css:
        css = re.sub(r"/\* replica-responsive \*/[\s\S]*$", block.strip() + "\n", css)
    else:
        css = css.rstrip() + "\n" + block
    path.write_text(css)
    print("patched mc-showroom.css responsive rules")


def main() -> None:
    stocks, slugs = discover_listed()
    print(f"listed stocks={len(stocks)} slugs={len(slugs)}")
    (ROOT / "data/listed-slugs.json").write_text(json.dumps(sorted(slugs), indent=2) + "\n")
    coaches = prune_coaches(slugs)
    prune_coach_dirs(slugs)
    rebuild_listings()
    rebuild_explore(slugs, coaches)
    patch_responsive_css()
    # Re-apply overrides on PDPs for kept stocks
    for stock, (raw, fmt) in PRICE_OVERRIDES.items():
        for c in coaches:
            if str(c.get("stock")) != stock:
                continue
            p = ROOT / "coaches" / c["slug"] / "index.html"
            if not p.exists():
                continue
            t = p.read_text()
            t = re.sub(r'(class="mc-card-price-value">)\$[0-9,]+', rf"\g<1>{fmt}", t)
            t = re.sub(r'data-price="\d+"', f'data-price="{raw}"', t)
            p.write_text(t)
            print(f"pdp override {stock} {fmt}")
    print("done")


if __name__ == "__main__":
    main()
