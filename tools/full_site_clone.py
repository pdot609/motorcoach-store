#!/usr/bin/env python3
"""Full visual clone of themotorcoachstore.com for static hosting.

Keeps original HubSpot chrome/theme/CSS. Rewrites contacts for the clone
domain and preserves a small set of custom inventory prices.
"""

from __future__ import annotations

import json
import re
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT
CACHE = Path("/tmp/mcs-full/pages")
IP = "199.60.103.226"
HOST = "www.themotorcoachstore.com"

# Site-specific prices that must not be overwritten by the live original.
PRICE_OVERRIDES = {
    "2955": (57999, "$57,999"),  # 2014 Prevost Liberty H3 45
    "2953": (144444, "$144,444"),  # 2015 Tiffin Allegro Bus 45 LP
    "3039": (599999, "$599,999"),  # 2021 Prevost Marathon H3-45
    "2969": (222222, "$222,222"),  # 2021 Newmar Dutch Star 4369
    "2854": (199999, "$199,999"),  # 2020 Newmar Mountain Aire 4551
    "2767": (299999, "$299,999"),  # 2009 Prevost Featherlite H3 45
    "2912": (2272315, "$2,272,315"),  # 2027 Prevost Loki H3 45
}

# Miles override for Liberty (also customized on this site)
MILES_OVERRIDES = {
    "2955": (73114, "73,114"),
}

CORE_PAGES = [
    "/",
    "/about",
    "/accessibility",
    "/ceramic-coating",
    "/certified-pre-owned/",
    "/coaches",
    "/coaches/new",
    "/coaches/pre-owned",
    "/coaches/certified",
    "/contact",
    "/contact-us",
    "/explore-showrooms",
    "/explore-showrooms/",
    "/faq",
    "/financing",
    "/fractional-ownership",
    "/fractionalmotorcoachownership-page",
    "/incoming-inventory",
    "/insurance",
    "/inventory",
    "/motorcoach-showroom-new-adventure-showhauler/",
    "/motorcoach-showroom-new-featherlite-stacker-trailers/",
    "/motorcoach-showroom-new-prevost-loki-coach/",
    "/motorcoach-showroom-ogv/",
    "/motorcoach-showroom-sold-pre-owned/",
    "/new-coaches/",
    "/news",
    "/news-from-the-road",
    "/paint-and-body",
    "/pre-delivery-inspection/",
    "/pre-owned/",
    "/pre-owned-old/",
    "/privacy",
    "/rv-financing",
    "/rv-insurance/",
    "/schedule",
    "/schedule-appointment",
    "/sell",
    "/sell-your-coach/",
    "/service",
    "/social-media",
    "/sold",
    "/sold-units",
    "/terms",
    "/trade-rv/",
    "/website-accessibility",
    "/media",
    "/videos",
    "/blog",
]


def curl_fetch(url: str) -> str:
    cmd = [
        "curl",
        "-fsSL",
        "-m",
        "120",
        "--compressed",
        "--resolve",
        f"{HOST}:443:{IP}",
        "-A",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "-H",
        "Accept-Language: en-US,en;q=0.9",
        url,
    ]
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(f"curl fail {url}: {r.stderr.decode('utf-8', 'replace')[:240]}")
    return r.stdout.decode("utf-8", "replace")


def path_for_url(url: str) -> Path:
    parsed = urlparse(url)
    path = parsed.path or "/"
    if path.endswith("/"):
        path = path + "index.html"
    elif "." not in Path(path).name:
        path = path.rstrip("/") + "/index.html"
    # Coach detail pages live under /coaches/<slug>/ locally
    if path.startswith("/coach/"):
        path = "/coaches/" + path[len("/coach/") :]
    if path.startswith("/inventory/") and "/coach/" not in path:
        # inventory listing stays; coach inventory URLs map similarly if slug-like
        slug = path.strip("/").split("/")[-1]
        if re.match(r"^(19|20)\d{2}-", slug):
            path = f"/coaches/{slug}/index.html"
    if path == "/index.html":
        return OUT / "index.html"
    return OUT / path.lstrip("/")


def rewrite_contacts(html: str) -> str:
    html = html.replace("sales@themotorcoachstore.com", "sales@themotorcoach.store")
    html = html.replace("service@themotorcoachstore.com", "service@themotorcoach.store")
    html = html.replace("mailto:sales@themotorcoachstore.com", "mailto:sales@themotorcoach.store")
    html = html.replace("mailto:service@themotorcoachstore.com", "mailto:service@themotorcoach.store")
    # Phone → clone phone
    replacements = [
        ("(941) 896-4819", "941 283 2516"),
        ("941-896-4819", "941 283 2516"),
        ("941.896.4819", "941 283 2516"),
        ("941 896 4819", "941 283 2516"),
        ("9418964819", "9412832516"),
        ("tel:+19418964819", "tel:+19412832516"),
        ("tel:19418964819", "tel:+19412832516"),
        ("tel:9418964819", "tel:+19412832516"),
    ]
    for a, b in replacements:
        html = html.replace(a, b)
    return html


def rewrite_links(html: str) -> str:
    # Absolute page links → root-relative. NEVER rewrite HubSpot CDN asset hosts
    # (/hubfs, /hs-fs, raw theme assets) — those must stay on themotorcoachstore.com.
    html = re.sub(
        r'https://www\.themotorcoachstore\.com/(coach|inventory)/([^"?#]+)(?:\?[^"#]*)?',
        r"/coaches/\2",
        html,
    )
    html = re.sub(r'href="/(coach|inventory)/([^"?#]+)(?:\?[^"]*)?"', r'href="/coaches/\2"', html)

    def _page_only(m: re.Match) -> str:
        path = m.group(1)
        if path.startswith(("hubfs/", "hs-fs/", "_hcms/", "hs/")):
            return m.group(0)
        return f"/{path}"

    html = re.sub(
        r'https://www\.themotorcoachstore\.com/([^"\'\s?#]+)(?:\?hsLang=en)?',
        _page_only,
        html,
    )
    html = html.replace("?hsLang=en", "")
    html = html.replace("&hsLang=en", "")
    # Map pre-owned-old → pre-owned for nav consistency
    html = html.replace('href="/pre-owned-old/"', 'href="/pre-owned/"')
    html = html.replace('href="/pre-owned-old"', 'href="/pre-owned"')
    html = html.replace('href="/website-accessibility"', 'href="/accessibility"')
    html = html.replace('href="/website-accessibility/"', 'href="/accessibility/"')
    return html


def apply_price_overrides(html: str) -> str:
    for stock, (raw, fmt) in PRICE_OVERRIDES.items():
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

        def fix_block(m, _stock=stock, _raw=raw, _fmt=fmt):
            block = m.group(0)
            if (
                f'data-stock="{_stock}"' in block
                or f"Stock #{_stock}" in block
                or f"stock {_stock}" in block.lower()
                or f"/{_stock}/" in block
                or block.endswith(_stock)
                or f"-{_stock}" in block
            ):
                block = re.sub(r'data-price="\d+"', f'data-price="{_raw}"', block)
                block = re.sub(
                    r'class="mc-card-price-value">\$[0-9,]+',
                    f'class="mc-card-price-value">{_fmt}',
                    block,
                )
                block = re.sub(
                    r'class="unit__price">\$[0-9,]+',
                    f'class="unit__price">{_fmt}',
                    block,
                )
                # Generic price spans near stock on PDPs
                if f"Stock {_stock}" in block or f"stock {_stock}" in block.lower() or f'data-stock="{_stock}"' in block:
                    # replace first few $X,XXX patterns carefully — only if single price value likely
                    pass
            return block

        html = re.sub(r"<article[\s\S]*?</article>", fix_block, html)

        # PDP pages: replace displayed price values when this stock is clearly the subject
        if f"Stock {stock}" in html or f"stock {stock}" in html.lower() or f'Inventory/{stock}/' in html:
            # Replace HubSpot price value blocks
            html = re.sub(
                r'(class="mc-card-price-value">)\$[0-9,]+',
                rf"\g<1>{fmt}",
                html,
                count=4,
            )

    for stock, (raw, disp) in MILES_OVERRIDES.items():
        html = re.sub(
            rf'(data-stock="{stock}"[^>]*data-miles=")[^"]+(")',
            rf"\g<1>{raw}\2",
            html,
        )
        html = re.sub(
            rf'(data-miles=")[^"]+("[^>]*data-stock="{stock}")',
            rf"\g<1>{raw}\2",
            html,
        )

        def fix_miles(m, _stock=stock, _raw=raw, _disp=disp):
            block = m.group(0)
            if f'data-stock="{_stock}"' in block or f"Stock #{_stock}" in block:
                block = re.sub(r'data-miles="\d+"', f'data-miles="{_raw}"', block)
                block = re.sub(r'data-mileage="\d+"', f'data-mileage="{_raw}"', block)
                block = re.sub(
                    r"(Mileage</span><b>)[0-9,]+",
                    rf"\g<1>{_disp}",
                    block,
                )
                block = re.sub(
                    r'(class="spec-val">)[0-9,]+(\s*mi)?',
                    lambda mm: f'{mm.group(1)}{_disp}{" mi" if mm.group(2) else ""}'
                    if "Mileage" in block[max(0, mm.start() - 80) : mm.start()]
                    else mm.group(0),
                    block,
                )
            return block

        html = re.sub(r"<article[\s\S]*?</article>", fix_miles, html)
        if f"Inventory/{stock}/" in html or f"Stock {stock}" in html:
            html = re.sub(
                r'(spec-label">Mileage</span><span class="spec-val">)[0-9,]+(\s*mi)?',
                rf"\g<1>{disp}\2",
                html,
            )
            html = re.sub(
                r"(Mileage</span><b>)[0-9,]+",
                rf"\g<1>{disp}",
                html,
            )
    return html


def inject_base(html: str) -> str:
    """Ensure root-relative resolution on static host."""
    if "<base " in html.lower():
        return html
    boot = """<script>
(function () {
  var base = "/";
  if (/\\.github\\.io$/i.test(location.hostname)) {
    var seg = location.pathname.split("/").filter(Boolean)[0];
    if (seg) base = "/" + seg + "/";
  }
  document.write('<base href="' + base + '">');
  window.__SITE_BASE__ = base;
})();
</script>
"""
    return re.sub(r"(<head[^>]*>)", r"\1\n" + boot, html, count=1, flags=re.I)


def process_html(html: str) -> str:
    html = rewrite_contacts(html)
    html = rewrite_links(html)
    html = apply_price_overrides(html)
    html = inject_base(html)
    # Drop HubSpot tracking beacons that break offline feel (keep theme CSS/JS)
    html = re.sub(
        r'<script[^>]+src="[^"]*js\.hs-analytics[^"]*"[^>]*></script>',
        "",
        html,
        flags=re.I,
    )
    return html


def save_page(url: str, html: str) -> Path:
    path = path_for_url(url)
    # Special aliases
    parsed = urlparse(url)
    if parsed.path.rstrip("/") in ("/pre-owned-old", "/pre-owned"):
        # Always publish as pre-owned/
        path = OUT / "pre-owned" / "index.html"
    if parsed.path.rstrip("/") == "/website-accessibility":
        path = OUT / "accessibility" / "index.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(process_html(html), encoding="utf-8")
    return path


def discover_active_coach_urls() -> list[str]:
    listing_urls = [
        f"https://{HOST}/pre-owned-old/?hsLang=en",
        f"https://{HOST}/new-coaches/?hsLang=en",
        f"https://{HOST}/certified-pre-owned/?hsLang=en",
        f"https://{HOST}/motorcoach-showroom-new-prevost-loki-coach/?hsLang=en",
        f"https://{HOST}/motorcoach-showroom-ogv/?hsLang=en",
        f"https://{HOST}/motorcoach-showroom-new-adventure-showhauler/?hsLang=en",
        f"https://{HOST}/motorcoach-showroom-new-featherlite-stacker-trailers/?hsLang=en",
        f"https://{HOST}/coaches/new",
        f"https://{HOST}/coaches/pre-owned",
        f"https://{HOST}/coaches/certified",
        f"https://{HOST}/?hsLang=en",
    ]
    slugs: dict[str, None] = {}
    for url in listing_urls:
        try:
            html = curl_fetch(url)
        except Exception as exc:
            print("listing fail", url, exc)
            continue
        for m in re.finditer(
            r'href="(?:https://www\.themotorcoachstore\.com)?/coach/([a-z0-9][a-z0-9\-]+)/?',
            html,
            re.I,
        ):
            slugs[m.group(1)] = None
        # cache listing html for later save
        CACHE.mkdir(parents=True, exist_ok=True)
        key = urlparse(url).path.strip("/").replace("/", "-") or "home"
        (CACHE / f"{key}.html").write_text(html, encoding="utf-8")
        try:
            save_page(url, html)
            print("saved listing", urlparse(url).path or "/")
        except Exception as exc:
            print("save listing fail", url, exc)
    return [f"https://{HOST}/coach/{slug}/?hsLang=en" for slug in sorted(slugs)]


def build_coaches_json(coach_html_by_slug: dict[str, str]) -> None:
    """Lightweight inventory JSON from cloned cards/PDPs, preserving overrides."""
    coaches = []
    for slug, html in coach_html_by_slug.items():
        stock_m = re.search(r'data-stock="(\d+)"', html) or re.search(r"Stock\s*#?(\d{3,5})", html)
        stock = stock_m.group(1) if stock_m else (re.search(r"-(\d{4})$", slug) or [None, ""])[1]
        title_m = re.search(r"<h1[^>]*>([\s\S]*?)</h1>", html, re.I)
        title = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", title_m.group(1))).strip() if title_m else slug
        price_m = re.search(r'class="mc-card-price-value"[^>]*>([^<]+)', html)
        price_txt = price_m.group(1).strip() if price_m else ""
        digits = re.sub(r"[^\d]", "", price_txt)
        price = int(digits) if digits else None
        if stock in PRICE_OVERRIDES:
            price = PRICE_OVERRIDES[stock][0]
        year_m = re.search(r'data-year="(\d+)"', html) or re.search(r"^(20\d{2}|19\d{2})", slug)
        year = int(year_m.group(1)) if year_m else None
        make_m = re.search(r'data-make="([^"]+)"', html)
        model_m = re.search(r'data-model="([^"]+)"', html)
        cond_m = re.search(r'data-condition="([^"]+)"', html)
        miles_m = re.search(r'data-miles="(\d+)"', html)
        miles = int(miles_m.group(1)) if miles_m else None
        if stock in MILES_OVERRIDES:
            miles = MILES_OVERRIDES[stock][0]
        hero_m = re.search(
            rf'https://www\.themotorcoachstore\.com/hs-fs/hubfs/Inventory/{stock}/[^"\']*HERO[^"\']*\.(?:jpg|jpeg|png|webp)',
            html,
            re.I,
        )
        hero = re.sub(r"[?#].*$", "", hero_m.group(0)) if hero_m else ""
        condition = (cond_m.group(1) if cond_m else "pre-owned").lower()
        if "certified" in condition:
            condition = "certified"
        elif condition.startswith("pre"):
            condition = "pre-owned"
        elif "new" in condition:
            condition = "new"
        coaches.append(
            {
                "slug": slug,
                "stock": str(stock),
                "title": title,
                "year": year,
                "make": (make_m.group(1) if make_m else "").lower(),
                "model": (model_m.group(1) if model_m else "").lower(),
                "condition": condition,
                "status": "available",
                "price": price,
                "miles": miles,
                "image": hero,
            }
        )
    coaches.sort(key=lambda c: (-(c.get("year") or 0), c.get("title") or ""))
    (OUT / "data").mkdir(parents=True, exist_ok=True)
    (OUT / "data" / "coaches.json").write_text(json.dumps(coaches, indent=2) + "\n", encoding="utf-8")
    (OUT / "data" / "listed-slugs.json").write_text(
        json.dumps([c["slug"] for c in coaches], indent=2) + "\n", encoding="utf-8"
    )
    print(f"wrote coaches.json ({len(coaches)})")


def fetch_one(url: str) -> tuple[str, str | None, str | None]:
    try:
        return url, curl_fetch(url), None
    except Exception as exc:
        return url, None, str(exc)


def main() -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    print("=== cloning core pages ===")
    for path in CORE_PAGES:
        url = f"https://{HOST}{path}"
        if not path.endswith("/") and path != "/" and "." not in Path(path).name:
            # try both
            pass
        try:
            html = curl_fetch(url if path != "/" else f"https://{HOST}/?hsLang=en")
            dest = save_page(url if path != "/" else f"https://{HOST}/", html)
            print("OK", dest.relative_to(OUT))
            time.sleep(0.05)
        except Exception as exc:
            print("FAIL", path, exc)

    print("=== discovering active inventory ===")
    coach_urls = discover_active_coach_urls()
    print(f"active coaches: {len(coach_urls)}")

    print("=== cloning coach PDPs ===")
    coach_html: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=6) as pool:
        futs = [pool.submit(fetch_one, u) for u in coach_urls]
        done = 0
        for fut in as_completed(futs):
            url, html, err = fut.result()
            done += 1
            slug = urlparse(url).path.strip("/").split("/")[-1]
            if err or not html:
                print(f"[{done}/{len(coach_urls)}] FAIL {slug}: {err}")
                continue
            save_page(url, html)
            coach_html[slug] = html
            if done % 10 == 0 or done == len(coach_urls):
                print(f"[{done}/{len(coach_urls)}]")

    build_coaches_json(coach_html)

    # Ensure alias pages exist
    aliases = {
        "pre-owned/index.html": "pre-owned/index.html",
        "contact-us/index.html": "contact/index.html",
        "accessibility/index.html": "accessibility/index.html",
    }
    # If paint-and-body missing, try paint-and-body-old
    pab = OUT / "paint-and-body" / "index.html"
    if not pab.exists():
        try:
            html = curl_fetch(f"https://{HOST}/paint-and-body-old")
            save_page(f"https://{HOST}/paint-and-body/", html)
            print("OK paint-and-body from old")
        except Exception as exc:
            print("paint-and-body fail", exc)

    print("done")


if __name__ == "__main__":
    main()
