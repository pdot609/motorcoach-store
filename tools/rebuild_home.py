#!/usr/bin/env python3
"""Rebuild homepage main content from themotorcoachstore.com, keeping local chrome/contacts."""

from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UA = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# Import rewrite helpers from rebuild_all_listings
import sys
sys.path.insert(0, str(ROOT / "tools"))
from rebuild_all_listings import (  # type: ignore
    apply_price_overrides,
    chrome_parts,
    rewrite_content,
)


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=90) as res:
        return res.read().decode("utf-8", "ignore")


def extract_main(html: str) -> str:
    # Prefer <main>…</main>
    m = re.search(r"<main[^>]*>([\s\S]*?)</main>", html, re.I)
    if m:
        return m.group(1).strip()
    # Fallback: first hero section through footer
    start = html.find('<section class=" hero">')
    if start < 0:
        start = html.find('<section class="hero">')
    footer = html.find("<footer")
    if start < 0 or footer < 0:
        raise RuntimeError("cannot find home main bounds")
    return html[start:footer].strip()


def localize_links(html: str) -> str:
    html = rewrite_content(html)
    # Home-specific absolute paths used by the redesigned theme
    replacements = [
        (r'href="/"', 'href="./"'),
        (r'href="/\?[^"]*"', 'href="./"'),
        (r'href="/explore-showrooms[^"]*"', 'href="explore-showrooms"'),
        (r'href="/pre-owned[^"]*"', 'href="pre-owned"'),
        (r'href="/new-coaches[^"]*"', 'href="new-coaches"'),
        (r'href="/certified-pre-owned[^"]*"', 'href="certified-pre-owned"'),
        (r'href="/fractional[^"]*"', 'href="fractional-ownership"'),
        (r'href="/sell[^"]*"', 'href="sell-your-coach"'),
        (r'href="/service[^"]*"', 'href="service"'),
        (r'href="/paint[^"]*"', 'href="paint-and-body"'),
        (r'href="/contact[^"]*"', 'href="contact-us"'),
        (r'href="/about[^"]*"', 'href="about"'),
        (r'href="/news[^"]*"', 'href="news"'),
        (r'href="/financing[^"]*"', 'href="financing"'),
        (r'href="/insurance[^"]*"', 'href="insurance"'),
        (r'href="/rv-financing[^"]*"', 'href="rv-financing"'),
        (r'href="/rv-insurance[^"]*"', 'href="rv-insurance"'),
        (r'href="/schedule[^"]*"', 'href="schedule-appointment"'),
        (r'href="/motorcoach-showroom-new-prevost-loki-coach[^"]*"', 'href="motorcoach-showroom-new-prevost-loki-coach"'),
        (r'href="/motorcoach-showroom-ogv[^"]*"', 'href="motorcoach-showroom-ogv"'),
        (r'href="/motorcoach-showroom-new-adventure-showhauler[^"]*"', 'href="motorcoach-showroom-new-adventure-showhauler"'),
        (r'href="/motorcoach-showroom-new-featherlite-stacker-trailers[^"]*"', 'href="motorcoach-showroom-new-featherlite-stacker-trailers"'),
        (r'href="/privacy[^"]*"', 'href="privacy"'),
        (r'href="/terms[^"]*"', 'href="terms"'),
        (r'href="/accessibility[^"]*"', 'href="accessibility"'),
    ]
    for pat, repl in replacements:
        html = re.sub(pat, repl, html)
    # Coach detail links already rewritten by rewrite_content to coaches/...
    return html


def refresh_latest_arrivals(html: str) -> str:
    """Optional: leave HubSpot arrivals as-is after price overrides."""
    return html


def main() -> None:
    remote = fetch("https://www.themotorcoachstore.com/?hsLang=en")
    main_html = localize_links(extract_main(remote))
    main_html = apply_price_overrides(main_html)
    main_html = refresh_latest_arrivals(main_html)

    boot, skip, header, footer = chrome_parts()

    # Pull theme CSS used by original homepage modules so layout matches.
    css_hrefs = re.findall(r'<link[^>]+href="([^"]+\.css[^"]*)"', remote)
    # Prefer local site + showroom CSS, plus remote theme overrides for home modules.
    local_css = [
        "css/site.css?v=20261111a",
        "css/mc-showroom.css?v=20261111a",
        "css/home-theme.css?v=20261111a",
    ]
    remote_css = []
    for href in css_hrefs:
        if "template_" in href or "module_" in href or "theme" in href.lower():
            if href.startswith("//"):
                href = "https:" + href
            elif href.startswith("/"):
                href = "https://www.themotorcoachstore.com" + href
            if href not in remote_css:
                remote_css.append(href)
    # Cap remote CSS to avoid pulling entire HubSpot stack twice
    remote_css = remote_css[:8]

    css_links = "\n".join(f'<link rel="stylesheet" href="{h}">' for h in local_css + remote_css)

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Luxury Motorcoaches for Sale, New &amp; Pre-Owned | The Motorcoach Store</title>
  <meta name="description" content="The Motorcoach Store in Bradenton, Florida sells new and pre-owned luxury motor coaches and provides service, paint, and financing.">
  <link rel="icon" href="https://www.themotorcoachstore.com/hubfs/raw_assets/public/motorcoach-theme/images/favicon/favicon-32x32.png">
  <link rel="preconnect" href="https://www.themotorcoachstore.com" crossorigin>
  <link rel="preconnect" href="https://47169059.fs1.hubspotusercontent-na1.net" crossorigin>
  <link rel="dns-prefetch" href="https://my.matterport.com">
  {boot}
{css_links}
</head>
<body class="page-home">
  {skip}
  {header}
  <main id="content" class="home-main">
{main_html}
  </main>
  {footer}
  <script defer src="js/base-path.js"></script>
  <script defer src="js/site.js"></script>
  <script defer src="js/mail-config.js"></script>
  <script defer src="js/form.js"></script>
</body>
</html>
"""
    out = ROOT / "index.html"
    out.write_text(page, encoding="utf-8")
    print(f"wrote {out} ({len(page)} bytes, remote css={len(remote_css)})")


if __name__ == "__main__":
    main()
