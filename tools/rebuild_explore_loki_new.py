#!/usr/bin/env python3
"""Rebuild explore-showrooms, Prevost Loki showroom, and /coaches/new from live originals."""

from __future__ import annotations

import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UA = {"User-Agent": "Mozilla/5.0 (compatible; MotorcoachStoreClone/1.0)"}


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as res:
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
    """Reuse header/footer/base bootstrap from an existing listing page."""
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
    html = html.replace("941 283 2516", "941 283 2516")
    html = html.replace("941 283 2516", "941 283 2516")
    html = re.sub(
        r'href="https://www\.themotorcoachstore\.com/(coach|inventory)/([^"?#]+)(?:\?[^"]*)?"',
        r'href="coaches/\2"',
        html,
    )
    html = re.sub(r'href="/(coach|inventory)/([^"?#]+)(?:\?[^"]*)?"', r'href="coaches/\2"', html)
    html = re.sub(r'href="/contact#contact-form"', 'href="contact-us"', html)
    html = re.sub(r'href="/contact"', 'href="contact-us"', html)
    html = re.sub(r'href="/pre-owned"', 'href="pre-owned"', html)
    html = re.sub(r'href="/explore-showrooms"', 'href="explore-showrooms"', html)
    html = re.sub(r'href="/schedule[^"]*"', 'href="schedule-appointment"', html)
    # Strip HubSpot tracking params from remaining absolute asset URLs is fine to keep.
    html = re.sub(r'\?hsLang=en', "", html)
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
  <main id="content"{' class="mc-listing-page"' if "mc-showroom" in main_html else ""}>
{main_html}
  </main>
  {footer}
  {script_tags}
</body>
</html>
"""


def rebuild_loki() -> None:
    html = fetch(
        "https://www.themotorcoachstore.com/motorcoach-showroom-new-prevost-loki-coach/"
    )
    hero = re.search(r'<div[^>]*class="[^"]*showroom-hero-section[^"]*"', html)
    show = re.search(r'<div[^>]*class="[^"]*mc-showroom[^"]*"', html)
    if not hero or not show:
        raise SystemExit("loki: missing hero/showroom")
    _, hero_end = slice_div(html, hero.start())
    _, show_end = slice_div(html, show.start())
    # Keep logo slider between hero and showroom when present.
    mid = html[hero_end:show.start()]
    journey = ""
    jm = re.search(
        r'(<div[^>]*class="[^"]*section[^"]*"[^>]*>[\s\S]*?Begin Your Journey with Confidence[\s\S]*?</div>\s*</div>\s*</div>)',
        html[show_end:],
    )
    # Prefer the same journey band used on local new-coaches.
    journey = """
<section class="journey">
  <div class="band-media"><img src="https://www.themotorcoachstore.com/hs-fs/hubfs/Begin%20Your%20Journey%20with%20Confidence-1.webp?width=1400&name=Begin%20Your%20Journey%20with%20Confidence-1.webp" alt="" loading="lazy" decoding="async"></div>
  <div class="journey-copy">
    <h2>Begin Your Journey with Confidence</h2>
    <p class="lede" style="margin:0 auto 22px">Contact our team today to schedule a personalized consultation or showroom visit. Your luxury motor coach is waiting.</p>
    <div class="inline-actions"><a class="btn" href="schedule-appointment">Schedule Appointment</a></div>
  </div>
</section>
"""
    main = rewrite_content(html[hero.start():hero_end] + mid + html[show.start():show_end] + journey)
    # Ensure showroom is not nested in hero (already sliced separately).
    page = wrap_page(
        title="New Prevost Loki Coaches - The Motorcoach Store",
        description="Browse new Prevost Loki coaches at The Motorcoach Store in Bradenton, Florida.",
        css=["css/site.css", "css/mc-showroom.css"],
        body_class="",
        main_html=main,
        scripts=["js/base-path.js", "js/site.js", "js/mc-showroom.js"],
    )
    out = ROOT / "showrooms/prevost-loki/index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    cards = page.count('article class="mc-card"')
    print(f"wrote {out} cards={cards}")


def rebuild_coaches_new() -> None:
    html = fetch("https://www.themotorcoachstore.com/coaches/new")
    start = html.find('<section class=" hero">')
    if start < 0:
        start = html.find('<section class="hero">')
    footer = html.find("<footer")
    if start < 0 or footer < 0:
        raise SystemExit("coaches/new: missing hero/footer bounds")
    chunk = html[start:footer]
    # Drop the trailing CTA dnd if present; keep inventory grid.
    # Prefer content through the listing-grid module close.
    m = re.search(r'(<article class="unit"[\s\S]+)</article>', chunk)
    if not m:
        raise SystemExit("coaches/new: no unit cards")
    # Include from hero through last article and nearby wrappers until empty/filters remain intact.
    # Cut after last </article> plus closing wrappers for the grid.
    last_article_end = chunk.rfind("</article>") + len("</article>")
    tail = chunk[last_article_end:last_article_end + 2500]
    # Keep a bit of closing divs after last card.
    close_match = re.match(r"(\s*</div>){1,12}", tail)
    end = last_article_end + (close_match.end() if close_match else 0)
    main = rewrite_content(chunk[:end])
    # Add empty state if missing
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
    out = ROOT / "coaches/new/index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    unit_count = page.count('article class="unit"')
    print(f"wrote {out} units={unit_count}")


def fix_explore_page() -> None:
    path = ROOT / "explore-showrooms/index.html"
    html = path.read_text(encoding="utf-8")
    html = html.replace(
        '<script src="js/explore.js"></script>',
        '<script defer src="js/explore.js"></script>',
    )
    if "css/site.css" not in html:
        html = html.replace(
            "</script>\n<link rel=\"stylesheet\" href=\"css/site.css\">",
            "</script>\n<link rel=\"stylesheet\" href=\"css/site.css\">",
        )
    path.write_text(html, encoding="utf-8")
    print(f"fixed script order in {path}")


def main() -> None:
    fix_explore_page()
    rebuild_loki()
    rebuild_coaches_new()


if __name__ == "__main__":
    main()
