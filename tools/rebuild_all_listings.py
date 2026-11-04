#!/usr/bin/env python3
"""Clone inventory listing/showroom pages from the original site into the local clone."""

from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UA = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

PRICE_OVERRIDES = {
    "2912": (2272315, "$2,272,315"),
    "2841": (1755575, "$1,755,575"),
    "3022": (433333, "$433,333"),
}


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
    src = (ROOT / "pre-owned/index.html").read_text(encoding="utf-8")
    head_boot = re.search(
        r"(<script>\s*\(function \(\) \{\s*var base[\s\S]+?</script>\s*)",
        src,
    ).group(1)
    header = re.search(r"(<header class=\"site-header\">[\s\S]+?</header>)", src).group(1)
    footer = re.search(r"(<footer class=\"site-footer\">[\s\S]+?</footer>)", src).group(1)
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


def wrap_page(
    *,
    title: str,
    description: str,
    css: list[str],
    body_class: str,
    main_html: str,
    scripts: list[str],
) -> str:
    boot, skip, header, footer = chrome_parts()
    css_links = "\n".join(f'<link rel="stylesheet" href="{href}">' for href in css)
    script_tags = "\n".join(f'<script defer src="{src}"></script>' for src in scripts)
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


def extract_showroom_main(html: str) -> str:
    hero = re.search(r'<div[^>]*class="[^"]*showroom-hero-section[^"]*"', html)
    show = re.search(r'<div[^>]*class="[^"]*mc-showroom[^"]*"', html)
    if not hero or not show:
        # fallback: page-hero + mc-showroom
        hero = re.search(r'<section[^>]*class="[^"]*page-hero[^"]*"', html) or re.search(
            r'<div[^>]*class="[^"]*page-hero[^"]*"', html
        )
        if not hero or not show:
            raise RuntimeError("missing hero/showroom")
    _, hero_end = slice_div(html, hero.start()) if html[hero.start():hero.start()+10].startswith("<div") else (hero.start(), html.find("</section>", hero.start()) + len("</section>"))
    if html[hero.start() : hero.start() + 8].startswith("<section"):
        hero_end = html.find("</section>", hero.start()) + len("</section>")
    else:
        _, hero_end = slice_div(html, hero.start())
    _, show_end = slice_div(html, show.start())
    mid = html[hero_end : show.start()]
    return rewrite_content(html[hero.start() : hero_end] + mid + html[show.start() : show_end] + JOURNEY)


def apply_price_overrides(html: str) -> str:
    for stock, (raw, fmt) in PRICE_OVERRIDES.items():
        # Update data-price on matching cards/units
        html = re.sub(
            rf'(data-stock="{stock}"[^>]*data-price=")[^"]+(")',
            rf"\g<1>{raw}\2",
            html,
        )
        html = re.sub(
            rf'(data-price=")[^"]+("[^>]*data-stock="{stock}")',
            rf"\g<1>{raw}\2",
            html,
        )
        # Within article containing stock, replace visible price near that stock
        def fix_article(m, _fmt=fmt, _raw=raw, _stock=stock):
            card = m.group(0)
            if f'data-stock="{_stock}"' in card or f"Stock #{_stock}" in card or f">{_stock}</b>" in card:
                card = re.sub(r'class="mc-card-price-value">\$[0-9,]+', f'class="mc-card-price-value">{_fmt}', card)
                card = re.sub(r'class="unit__price">\$[0-9,]+', f'class="unit__price">{_fmt}', card)
                card = re.sub(rf'data-price="\d+"', f'data-price="{_raw}"', card)
            return card

        html = re.sub(r'<article class="mc-card"[\s\S]*?</article>', fix_article, html)
        html = re.sub(r'<article class="unit"[\s\S]*?</article>', fix_article, html)
    return html


def write(path: Path, page: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    page = apply_price_overrides(page)
    # cache-bust mc-showroom
    page = page.replace("js/mc-showroom.js", "js/mc-showroom.js?v=20261104")
    path.write_text(page, encoding="utf-8")
    cards = page.count('article class="mc-card"')
    units = page.count('article class="unit"')
    print(f"wrote {path.relative_to(ROOT)} cards={cards} units={units}")


def rebuild_mc_showroom(url: str, out: Path, title: str, description: str) -> None:
    html = fetch(url)
    main = extract_showroom_main(html)
    page = wrap_page(
        title=title,
        description=description,
        css=["css/site.css", "css/mc-showroom.css"],
        body_class="",
        main_html=main,
        scripts=["js/base-path.js", "js/site.js", "js/mc-showroom.js?v=20261104"],
    )
    write(out, page)


def rebuild_coaches_new() -> None:
    html = fetch("https://www.themotorcoachstore.com/coaches/new")
    start = html.find('<section class=" hero">')
    if start < 0:
        start = html.find('<section class="hero">')
    footer = html.find("<footer")
    if start < 0 or footer < 0:
        raise SystemExit("coaches/new: missing bounds")
    chunk = html[start:footer]
    last_article_end = chunk.rfind("</article>") + len("</article>")
    tail = chunk[last_article_end : last_article_end + 2500]
    close_match = re.match(r"(\s*</div>){1,12}", tail)
    end = last_article_end + (close_match.end() if close_match else 0)
    main = rewrite_content(chunk[:end])
    if "data-empty" not in main:
        main += '\n<p class="listing-empty" data-empty hidden>No coaches match these filters.</p>\n'
    page = wrap_page(
        title="New Luxury Motorcoaches for Sale | The Motorcoach Store",
        description="Explore new luxury motor coaches and stacker trailers at The Motorcoach Store in Bradenton, Florida.",
        css=["css/site.css", "css/coaches-new.css", "css/listing-grid.css"],
        body_class="page-coaches-new",
        main_html=main,
        scripts=["js/base-path.js", "js/site.js", "js/coaches-new.js"],
    )
    write(ROOT / "coaches/new/index.html", page)


def rebuild_listing_grid(url: str, out: Path, title: str, description: str, body_class: str = "") -> None:
    html = fetch(url)
    # Prefer unit grid pages like coaches/pre-owned / coaches/certified
    start = html.find('<section class=" hero">')
    if start < 0:
        start = html.find('<section class="hero">')
    if start < 0:
        start = html.find('<main')
        if start >= 0:
            start = html.find(">", start) + 1
    footer = html.find("<footer")
    if start < 0 or footer < 0:
        raise SystemExit(f"listing grid missing bounds for {url}")
    chunk = html[start:footer]
    if 'article class="unit"' in chunk:
        last_article_end = chunk.rfind("</article>") + len("</article>")
        tail = chunk[last_article_end : last_article_end + 2500]
        close_match = re.match(r"(\s*</div>){1,12}", tail)
        end = last_article_end + (close_match.end() if close_match else 0)
        main = rewrite_content(chunk[:end])
        css = ["css/site.css", "css/coaches-new.css", "css/listing-grid.css"]
        scripts = ["js/base-path.js", "js/site.js", "js/coaches-new.js"]
    elif "mc-showroom" in chunk:
        main = extract_showroom_main(html)
        css = ["css/site.css", "css/mc-showroom.css"]
        scripts = ["js/base-path.js", "js/site.js", "js/mc-showroom.js?v=20261104"]
    else:
        main = rewrite_content(chunk)
        css = ["css/site.css", "css/mc-showroom.css"]
        scripts = ["js/base-path.js", "js/site.js"]
    if "data-empty" not in main and 'article class="unit"' in main:
        main += '\n<p class="listing-empty" data-empty hidden>No coaches match these filters.</p>\n'
    page = wrap_page(
        title=title,
        description=description,
        css=css,
        body_class=body_class,
        main_html=main,
        scripts=scripts,
    )
    write(out, page)


def rebuild_explore_json() -> None:
    """Refresh explore band cards from coaches.json available new inventory by brand."""
    coaches = json.loads((ROOT / "data/coaches.json").read_text())
    path = ROOT / "data/explore-showrooms.json"
    data = json.loads(path.read_text()) if path.exists() else {"bands": []}

    def money(v):
        if not v:
            return None
        return f"${int(v):,}"

    def cards_for(pred, limit=6):
        items = [c for c in coaches if c.get("status") == "available" and pred(c)]
        items.sort(key=lambda c: (-(c.get("created") or 0), -(c.get("price") or 0)))
        out = []
        for c in items[:limit]:
            out.append(
                {
                    "href": f"/coaches/{c['slug']}",
                    "image": c.get("image") or "",
                    "alt": c.get("title") or "",
                    "title": c.get("title") or "",
                    "msrp": None,
                    "price": money(c.get("price")),
                    "monthly": None,
                }
            )
        return out

    brand_map = {
        "loki": lambda c: "loki" in f"{c.get('slug')} {c.get('title')} {c.get('model')}".lower(),
        "ogv": lambda c: "ogv" in f"{c.get('slug')} {c.get('title')}".lower()
        or "v-tour" in (c.get("slug") or ""),
        "adventure": lambda c: "showhauler" in f"{c.get('slug')} {c.get('title')}".lower()
        or "adventure" in f"{c.get('slug')} {c.get('title')}".lower(),
        "featherlite": lambda c: "featherlite" in f"{c.get('slug')} {c.get('title')}".lower()
        or "stacker" in f"{c.get('slug')} {c.get('title')}".lower(),
    }

    bands = data.get("bands") or []
    for band in bands:
        bid = band.get("id") or ""
        if bid in brand_map:
            band["cards"] = cards_for(brand_map[bid], limit=8)
    if not bands:
        data["bands"] = [
            {"id": k, "title": k.title(), "cards": cards_for(fn, limit=8)}
            for k, fn in brand_map.items()
        ]
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"updated {path.relative_to(ROOT)}")


def force_json_price_overrides() -> None:
    coaches = json.loads((ROOT / "data/coaches.json").read_text())
    changed = 0
    for c in coaches:
        stock = str(c.get("stock") or "")
        if stock in PRICE_OVERRIDES:
            raw, _ = PRICE_OVERRIDES[stock]
            if c.get("price") != raw:
                c["price"] = raw
                changed += 1
    (ROOT / "data/coaches.json").write_text(json.dumps(coaches, indent=2) + "\n")
    print(f"price overrides applied in coaches.json ({changed} changed)")


def main() -> None:
    force_json_price_overrides()

    rebuild_mc_showroom(
        "https://www.themotorcoachstore.com/motorcoach-showroom-new-prevost-loki-coach/",
        ROOT / "showrooms/prevost-loki/index.html",
        "New Prevost Loki Coaches - The Motorcoach Store",
        "Browse new Prevost Loki coaches at The Motorcoach Store in Bradenton, Florida.",
    )
    rebuild_mc_showroom(
        "https://www.themotorcoachstore.com/motorcoach-showroom-ogv/",
        ROOT / "showrooms/ogv/index.html",
        "OGV Luxury Coach Showroom - The Motorcoach Store",
        "Browse new OGV Luxury Coaches at The Motorcoach Store.",
    )
    rebuild_mc_showroom(
        "https://www.themotorcoachstore.com/motorcoach-showroom-new-adventure-showhauler/",
        ROOT / "showrooms/adventure/index.html",
        "Adventure by ShowHauler Showroom - The Motorcoach Store",
        "Browse new Adventure by ShowHauler coaches at The Motorcoach Store.",
    )
    rebuild_mc_showroom(
        "https://www.themotorcoachstore.com/motorcoach-showroom-new-featherlite-stacker-trailers/",
        ROOT / "showrooms/featherlite/index.html",
        "Featherlite Stacker Trailers - The Motorcoach Store",
        "Browse new Featherlite stacker trailers at The Motorcoach Store.",
    )

    # Pre-owned HubSpot showroom (redirect target)
    rebuild_mc_showroom(
        "https://www.themotorcoachstore.com/pre-owned-old/",
        ROOT / "pre-owned/index.html",
        "Pre-Owned Motorcoaches - The Motorcoach Store",
        "Browse pre-owned luxury motor coaches at The Motorcoach Store in Bradenton, Florida.",
    )

    # New coaches HubSpot listing
    rebuild_mc_showroom(
        "https://www.themotorcoachstore.com/new-coaches",
        ROOT / "new-coaches/index.html",
        "New Coaches - The Motorcoach Store",
        "Browse new luxury motor coaches at The Motorcoach Store.",
    )

    rebuild_coaches_new()

    rebuild_listing_grid(
        "https://www.themotorcoachstore.com/coaches/pre-owned",
        ROOT / "coaches/pre-owned/index.html",
        "Pre-Owned Luxury Motorcoaches | The Motorcoach Store",
        "Explore pre-owned luxury motor coaches at The Motorcoach Store.",
        body_class="page-coaches-preowned",
    )
    rebuild_listing_grid(
        "https://www.themotorcoachstore.com/coaches/certified",
        ROOT / "coaches/certified/index.html",
        "Certified Pre-Owned Motorcoaches | The Motorcoach Store",
        "Explore certified pre-owned luxury motor coaches at The Motorcoach Store.",
        body_class="page-coaches-certified",
    )

    # certified-pre-owned marketing/showroom page if mc-showroom present
    try:
        rebuild_listing_grid(
            "https://www.themotorcoachstore.com/certified-pre-owned/",
            ROOT / "certified-pre-owned/index.html",
            "Certified Pre-Owned (CPO) - The Motorcoach Store",
            "Certified pre-owned luxury motor coaches at The Motorcoach Store.",
        )
    except Exception as exc:
        print("certified-pre-owned skip:", exc)

    rebuild_explore_json()
    print("done")


if __name__ == "__main__":
    main()
