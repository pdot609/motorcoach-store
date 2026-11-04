#!/usr/bin/env python3
"""Sync every coach from themotorcoachstore.com into coaches.json + PDPs + listings."""

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
UA = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html",
}

JUNK = {
    "certified",
    "stacker-trailers",
    "new",
    "pre-owned",
    "inventory",
    "compare",
    "sold",
}

# Keep user-requested overrides even if live scrape differs.
PRICE_OVERRIDES = {
    "2912": 2272315,
    "2841": 1755575,
    "3022": 433333,
}

MAKE_ALIASES = {
    "prevost": "prevost",
    "newell": "newell",
    "newmar": "newmar",
    "tiffin": "tiffin",
    "foretravel": "foretravel",
    "entegra": "entegra",
    "ogv": "ogv",
    "featherlite": "featherlite",
    "showhauler": "showhauler",
    "renegade": "renegade",
    "american": "american coach",
    "grand": "grand design",
    "cargo": "cargo mate",
    "loki": "prevost",
}


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=90) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def discover_slugs() -> list[str]:
    sm = fetch("https://www.themotorcoachstore.com/sitemap.xml")
    locs = re.findall(r"<loc>([^<]+)</loc>", sm)
    slugs: dict[str, None] = {}
    for loc in locs:
        m = re.search(r"/(?:coach|inventory|coaches)/([a-z0-9][a-z0-9\-]+)/?$", loc, re.I)
        if not m:
            continue
        slug = m.group(1)
        if slug.lower() in JUNK or len(slug) < 8:
            continue
        slugs[slug] = None
    return sorted(slugs)


def parse_money(text: str | None) -> int | None:
    if not text:
        return None
    digits = re.sub(r"[^\d]", "", str(text))
    if not digits:
        return None
    try:
        return int(digits)
    except ValueError:
        return None


def spec_map(specs: list) -> dict[str, str]:
    out = {}
    for item in specs or []:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            out[str(item[0]).strip().lower()] = str(item[1]).strip()
        elif isinstance(item, dict):
            out[str(item.get("label", "")).strip().lower()] = str(item.get("value", "")).strip()
    return out


def infer_make(slug: str, title: str, model: str) -> str:
    hay = f"{slug} {title} {model}".lower()
    for key, make in MAKE_ALIASES.items():
        if key in hay:
            return make
    return "other"


def infer_channels(condition: str, status: str, slug: str, title: str) -> list[str]:
    channels = []
    cond = (condition or "").lower()
    if "certified" in cond:
        channels.append("certified")
        channels.append("pre-owned")
    elif "pre" in cond:
        channels.append("pre-owned")
    elif cond == "new":
        channels.append("new")
    else:
        # sold Loki conversions etc.
        if "sold" in slug.lower() or status == "sold":
            channels.append("new")
        else:
            channels.append("pre-owned")
    # brand showrooms
    hay = f"{slug} {title}".lower()
    if "loki" in hay:
        channels.append("prevost-loki")
    if "ogv" in hay or "v-tour" in hay or "vcruise" in hay or "vsport" in hay:
        channels.append("ogv")
    if "featherlite" in hay or "stacker" in hay:
        channels.append("featherlite")
    if "showhauler" in hay or "adventure" in hay:
        channels.append("adventure")
    # unique preserve order
    seen = []
    for c in channels:
        if c not in seen:
            seen.append(c)
    return seen


def extract_data_attrs(html: str) -> dict:
    attrs = {}
    for key in (
        "stock",
        "price",
        "make",
        "model",
        "year",
        "condition",
        "status",
        "horsepower",
        "miles",
        "created",
        "hs_id",
    ):
        m = re.search(rf'data-{key}="([^"]*)"', html, re.I)
        if m:
            attrs[key] = m.group(1).strip()
    return attrs


def extract_specs_from_html(html: str) -> list[tuple[str, str]]:
    specs = []
    for m in re.finditer(
        r'<div class="mc-spec[^"]*"[^>]*>\s*<span[^>]*>(.*?)</span>\s*<b[^>]*>(.*?)</b>',
        html,
        re.I | re.S,
    ):
        label = re.sub(r"<[^>]+>", "", m.group(1)).strip()
        val = re.sub(r"<[^>]+>", "", m.group(2)).strip()
        if label and val:
            specs.append((label, val))
    if specs:
        return specs
    for m in re.finditer(
        r'class="[^"]*mc-spec[^"]*"[\s\S]*?class="spec-label"[^>]*>(.*?)</[^>]+>[\s\S]*?class="spec-val"[^>]*>(.*?)</[^>]+>',
        html,
        re.I,
    ):
        label = re.sub(r"<[^>]+>", "", m.group(1)).strip()
        val = re.sub(r"<[^>]+>", "", m.group(2)).strip()
        if label and val:
            specs.append((label, val))
    return specs


def extract_price_text(html: str) -> str:
    m = re.search(r'class="mc-card-price-value"[^>]*>([^<]+)', html)
    if m:
        return m.group(1).strip()
    m = re.search(r'class="unit__price"[^>]*>([^<]+)', html)
    if m:
        return m.group(1).strip()
    return ""


def extract_title(html: str, fallback: str) -> str:
    m = re.search(r"<h1[^>]*>([\s\S]*?)</h1>", html, re.I)
    if m:
        return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m.group(1))).strip()
    return fallback


def extract_hero(html: str, stock: str) -> str:
    html = html.replace("&amp;", "&")
    if stock:
        m = re.search(
            rf'https://www\.themotorcoachstore\.com/hs-fs/hubfs/Inventory/{re.escape(stock)}/[^"\'?\s>]*HERO[^"\'?\s>]*\.(?:jpg|jpeg|png|webp)',
            html,
            re.I,
        )
        if m:
            return re.sub(r"[?#].*$", "", m.group(0))
    m = re.search(r'class="single-main-image"[^>]+src="([^"]+)"', html, re.I)
    if m:
        return re.sub(r"[?#].*$", "", m.group(1).replace("&amp;", "&"))
    m = re.search(
        r'(https://www\.themotorcoachstore\.com/hs-fs/hubfs/Inventory/[^"\']+\.(?:jpg|jpeg|png|webp))',
        html,
        re.I,
    )
    if m:
        return re.sub(r"[?#].*$", "", m.group(1).replace("&amp;", "&"))
    return ""


def extract_virtual(html: str) -> tuple[bool, str]:
    m = re.search(r'src="(https://my\.matterport\.com/show/\?m=[^"]+)"', html)
    if m:
        return True, m.group(1).replace("&amp;", "&")
    m = re.search(r'href="(https://my\.matterport\.com/show/\?m=[^"]+)"', html)
    if m:
        return True, m.group(1).replace("&amp;", "&")
    return False, ""


def scrape_to_record(slug: str, existing: dict | None = None) -> dict | None:
    urls = [
        f"https://www.themotorcoachstore.com/coach/{slug}",
        f"https://www.themotorcoachstore.com/inventory/{slug}",
        f"https://www.themotorcoachstore.com/coaches/{slug}",
    ]
    html = ""
    used = ""
    for url in urls:
        try:
            html = fetch(url)
            used = url
            if "mc-card-price" in html or "<h1" in html or "data-stock=" in html:
                break
        except Exception:
            continue
    if not html:
        return None

    attrs = extract_data_attrs(html)
    specs = extract_specs_from_html(html)
    smap = spec_map(specs)
    title = extract_title(html, (existing or {}).get("title") or slug.replace("-", " ").title())
    stock = attrs.get("stock") or (existing or {}).get("stock") or ""
    if not stock:
        m = re.search(r"(\d{3,5})$", slug)
        if m:
            stock = m.group(1)
    price_text = extract_price_text(html)
    price = parse_money(price_text) or parse_money(attrs.get("price")) or (existing or {}).get("price")
    if stock in PRICE_OVERRIDES:
        price = PRICE_OVERRIDES[stock]

    year = None
    if attrs.get("year"):
        try:
            year = int(attrs["year"])
        except ValueError:
            year = None
    if year is None:
        m = re.search(r"^(19|20)\d{2}", slug)
        if m:
            year = int(m.group(0))

    condition_raw = (attrs.get("condition") or smap.get("condition") or "").lower()
    if not condition_raw:
        # Infer from page badges / sold slug
        if re.search(r"certified", html, re.I):
            condition_raw = "certified"
        elif re.search(r"\bnew\b", title, re.I) and year and year >= 2025:
            condition_raw = "new"
        elif "sold" in slug.lower():
            condition_raw = "new"
        else:
            condition_raw = (existing or {}).get("condition") or "pre-owned"

    if "certified" in condition_raw:
        condition = "certified"
    elif "pre" in condition_raw:
        condition = "pre-owned"
    elif condition_raw == "new":
        condition = "new"
    else:
        condition = condition_raw or "pre-owned"

    status = (attrs.get("status") or "").lower()
    if not status:
        status = "sold" if "sold" in slug.lower() or "sold" in title.lower() else "available"
    if "call for" in (price_text or "").lower() and "sold" in slug.lower():
        status = "sold"

    model = attrs.get("model") or smap.get("model") or (existing or {}).get("model") or ""
    make = attrs.get("make") or (existing or {}).get("make") or infer_make(slug, title, model)
    make = make.lower().strip()

    miles = None
    miles_raw = attrs.get("miles") or smap.get("mileage") or smap.get("miles")
    if miles_raw:
        miles = parse_money(str(miles_raw).replace("mi", ""))
    if isinstance(miles_raw, str) and "new" in miles_raw.lower():
        miles = None

    created = None
    if attrs.get("created"):
        try:
            created = int(attrs["created"])
        except ValueError:
            created = None
    if created is None:
        created = (existing or {}).get("created") or int(time.time() * 1000)

    hero = extract_hero(html, stock) or (existing or {}).get("image") or ""
    virtual, virtual_tour = extract_virtual(html)

    engine = smap.get("engine") or (existing or {}).get("engine") or ""
    floorplan = smap.get("floorplan") or (existing or {}).get("floorplan") or ""
    slides = smap.get("slides") or (existing or {}).get("slides") or ""
    baths = smap.get("bath(s)") or smap.get("baths") or (existing or {}).get("baths") or ""
    bunks = smap.get("bunk beds") or smap.get("bunks") or (existing or {}).get("bunks") or ""

    record = {
        "slug": slug,
        "stock": str(stock),
        "title": title,
        "year": year,
        "make": make,
        "model": model.lower() if model else "",
        "condition": condition,
        "status": status,
        "channels": infer_channels(condition, status, slug, title),
        "price": price,
        "miles": miles,
        "engine": engine,
        "floorplan": floorplan,
        "slides": slides,
        "baths": baths,
        "bunks": bunks,
        "image": hero,
        "virtual": virtual,
        "created": created,
        "featured": bool((existing or {}).get("featured")),
        "virtualTour": virtual_tour or (existing or {}).get("virtualTour") or "",
        "video": (existing or {}).get("video") or "#",
        "documents": (existing or {}).get("documents")
        or {"buildSheet": "#", "floorPlan": "#", "checkInSheet": "#"},
        "_source": used,
        "_priceText": price_text,
        "_specs": specs,
    }
    return record


def build_coaches_json(slugs: list[str]) -> list[dict]:
    existing_list = json.loads(COACHES_JSON.read_text()) if COACHES_JSON.exists() else []
    by_slug = {c["slug"]: c for c in existing_list}
    results: dict[str, dict] = {}
    fails = []

    def work(slug: str):
        try:
            return slug, scrape_to_record(slug, by_slug.get(slug)), None
        except Exception as exc:
            return slug, None, f"{type(exc).__name__}: {exc}"

    print(f"scraping {len(slugs)} coaches…")
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(work, s) for s in slugs]
        done = 0
        for fut in as_completed(futures):
            slug, rec, err = fut.result()
            done += 1
            if done % 10 == 0 or done == len(slugs):
                print(f"  {done}/{len(slugs)}")
            if rec:
                results[slug] = rec
            else:
                fails.append((slug, err or "empty"))

    # Keep existing coaches not in sitemap only if still useful? Prefer original inventory only.
    coaches = []
    for slug in slugs:
        if slug in results:
            coaches.append(results[slug])
        elif slug in by_slug:
            # keep existing if scrape failed
            coaches.append(by_slug[slug])
            fails.append((slug, "kept existing after scrape fail"))

    # Apply price overrides again
    for c in coaches:
        if str(c.get("stock")) in PRICE_OVERRIDES:
            c["price"] = PRICE_OVERRIDES[str(c["stock"])]

    # Strip private scrape helpers before write, but stash scrapes
    SCRAPE_DIR.mkdir(parents=True, exist_ok=True)
    lean = []
    for c in coaches:
        specs = c.pop("_specs", [])
        source = c.pop("_source", "")
        price_text = c.pop("_priceText", "")
        SCRAPE_DIR.joinpath(f"{c['slug']}.json").write_text(
            json.dumps(
                {
                    "slug": c["slug"],
                    "ok": True,
                    "url": source,
                    "h1": c["title"],
                    "condition": c["condition"],
                    "price": price_text or (f"${c['price']:,}" if c.get("price") else ""),
                    "hero": c.get("image") or "",
                    "specs": specs,
                    "stock": c.get("stock") or "",
                    "scrapedAt": int(time.time()),
                },
                indent=2,
            )
        )
        lean.append(c)

    COACHES_JSON.write_text(json.dumps(lean, indent=2) + "\n")
    print(f"wrote {len(lean)} coaches; fails={len(fails)}")
    for slug, err in fails[:30]:
        print(f"  FAIL {slug}: {err}")
    if len(fails) > 30:
        print(f"  … {len(fails) - 30} more")
    return lean


def main():
    slugs = discover_slugs()
    print(f"discovered {len(slugs)} inventory slugs")
    Path("/tmp/orig_slugs.txt").write_text("\n".join(slugs) + "\n")
    build_coaches_json(slugs)


if __name__ == "__main__":
    main()
