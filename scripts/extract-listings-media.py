#!/usr/bin/env python3
"""Extract featured listings + media URLs from the live HI home scrape."""

from __future__ import annotations

import html as html_lib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOME_RAW = ROOT / "research/live/lizakalawaia.legacyrealtyhi.com-home/page.raw"
OUT_DIR = ROOT / "data"
MEDIA_DIR = ROOT / "media"


def thumb_to_full(url: str) -> str:
    return url.replace("/thumbnails/", "/")


def slug_to_address(data_link: str) -> tuple[str, str | None, str | None]:
    """
    /property/23-202613936-1634-nuuanu-avenue-303-honolulu-HI-96817
    -> address, city, zip
    """
    path = data_link.strip()
    m = re.search(
        r"/property/\d+-(\d+)-(.+?)-([A-Za-z][A-Za-z\s]+)-([A-Z]{2})-(\d{5})\s*$",
        path,
    )
    if not m:
        # looser: after mls id, rest of slug
        m2 = re.search(r"/property/\d+-(\d+)-(.+?)\s*$", path)
        if not m2:
            return path, None, None
        rest = m2.group(2)
        parts = rest.split("-")
        # try find HI/NV state token
        city = None
        zipc = None
        addr_parts = parts
        for i, p in enumerate(parts):
            if p.upper() in ("HI", "NV") and i + 1 < len(parts) and parts[i + 1].isdigit():
                city = parts[i - 1].replace("+", " ").title() if i else None
                # city may be multi word already joined - take token before state
                zipc = parts[i + 1]
                addr_parts = parts[: i - 1] if i else parts
                break
        address = " ".join(addr_parts).replace("+", " ").title()
        return address, city, zipc

    mls_id, street, city, state, zipc = m.groups()
    street_fmt = street.replace("-", " ").title()
    city_fmt = city.strip().title()
    address = f"{street_fmt}, {city_fmt}, {state} {zipc}"
    return address, city_fmt, zipc


def parse_listing_boxes(raw: str) -> list[dict]:
    listings: list[dict] = []
    seen: set[str] = set()

    for box in re.finditer(
        r'<div class="listing-box\s*"([^>]*)>([\s\S]*?)</div>\s*(?=<div class="listing-box|</div>\s*</div>\s*</div>\s*</div>\s*</div>)',
        raw,
    ):
        attrs, body = box.group(1), box.group(2)
        # Fallback: if body truncated weirdly, still try per-box from data-link anchors
        _ = attrs

    # More reliable: split on listing-box openings
    parts = re.split(r'<div class="listing-box\s*"', raw)
    for part in parts[1:]:
        # attrs until >
        am = re.match(r'([^>]*)>([\s\S]*)$', part)
        if not am:
            continue
        attrs, rest = am.group(1), am.group(2)
        # end at next listing-box roughly — take until we've seen listing-box-content dl close
        chunk = rest[:4000]

        link_m = re.search(r'data-link="([^"]+)"', attrs + " " + chunk)
        data_link = html_lib.unescape(link_m.group(1).strip()) if link_m else ""
        mlsid_m = re.search(r'data-mlsid="(\d+)"', chunk)
        listing_id = mlsid_m.group(1) if mlsid_m else None
        if not listing_id and data_link:
            id_m = re.search(r"/property/\d+-(\d+)-", data_link)
            listing_id = id_m.group(1) if id_m else None
        if not listing_id or listing_id in seen:
            continue
        seen.add(listing_id)

        thumb_m = re.search(
            r'data-src="(https://d36xftgacqn2p\.cloudfront\.net/listingphotos[^"]+)"',
            chunk,
        )
        thumb = thumb_m.group(1) if thumb_m else None

        price_m = re.search(
            r'data-translate="currency">\s*\$?\s*([\d,]+)\s*<',
            chunk,
        )
        price = f"${price_m.group(1)}" if price_m else None

        type_m = re.search(r"<dt>\s*Type\s*</dt>\s*<dd>\s*([^<]+)", chunk, re.I)
        ptype = type_m.group(1).strip() if type_m else None
        if ptype:
            ptype = re.sub(r"\s+", " ", ptype)

        sqft_m = re.search(
            r"<dt>\s*Size\s*</dt>\s*<dd[^>]*>\s*<span>\s*([\d,]+)\s*</span>\s*SqFt",
            chunk,
            re.I,
        )
        sqft = int(sqft_m.group(1).replace(",", "")) if sqft_m else None

        rooms_m = re.search(
            r"<dt>\s*Rooms\s*</dt>\s*<dd>\s*<span>\s*([\d.]+)\s*</span>\s*Beds?\s*\+\s*<span>\s*([\d.]+)\s*</span>\s*Baths?",
            chunk,
            re.I,
        )
        beds = baths = None
        if rooms_m:
            beds_f = float(rooms_m.group(1))
            baths_f = float(rooms_m.group(2))
            beds = int(beds_f) if beds_f.is_integer() else beds_f
            baths = int(baths_f) if baths_f.is_integer() else baths_f

        city_m = re.search(r'<div class="listing-box-title">\s*<h2>\s*<a[^>]*>\s*([^<]+)\s*<', chunk)
        city = city_m.group(1).strip() if city_m else None

        address, city_from_slug, zipc = slug_to_address(data_link) if data_link else ("", None, None)
        if not city:
            city = city_from_slug

        href = None
        hm = re.search(r'href="(/property/[^"]+)"', chunk)
        if hm:
            href = "https://lizakalawaia.legacyrealtyhi.com" + html_lib.unescape(hm.group(1).strip())

        label_m = re.search(r'listing-box-image-label">([^<]+)', chunk)
        label = label_m.group(1).strip() if label_m else None

        photos = []
        if thumb:
            photos.append({"thumb": thumb, "full": thumb_to_full(thumb)})

        digits = int(re.sub(r"[^\d]", "", price or "") or "0")
        likely_rental = bool(digits and digits < 20000) or (
            ptype and "rental" in ptype.lower()
        )

        item = {
            "id": listing_id,
            "source": "lizakalawaia.legacyrealtyhi.com",
            "city": city,
            "address": address or city,
            "zip": zipc,
            "price": price,
            "propertyType": ptype,
            "bedrooms": beds,
            "bathrooms": baths,
            "sqft": sqft,
            "label": label,
            "listingUrl": href
            or (
                "https://lizakalawaia.legacyrealtyhi.com" + data_link.strip()
                if data_link
                else None
            ),
            "photos": photos,
            "mediaDir": f"media/listings/{listing_id}",
            "glb": {
                "exterior": f"media/listings/{listing_id}/glb/exterior.glb",
                "status": "pending",
            },
            "likelyRental": likely_rental,
        }
        beds_s = f"{beds} bed" if beds is not None else "? bed"
        baths_s = f"{baths} bath" if baths is not None else "? bath"
        sqft_s = f"{sqft:,} sq ft" if isinstance(sqft, int) else "? sq ft"
        item["morphText"] = f"{item['address']}, {beds_s}, {baths_s}, {sqft_s}"
        listings.append(item)

    return listings


def extract_brand_media(html: str) -> dict:
    profiles = sorted(
        set(
            re.findall(
                r"https://dtzulyujzhqiu\.cloudfront\.net/lizakalawaia15111/profiles/[^\s\"')]+",
                html,
            )
        )
    )
    heroes = sorted(
        set(
            re.findall(
                r"https://d2na8ywvtbawk2\.cloudfront\.net/[^\s\"')]+",
                html,
            )
        )
    )
    heroes = [
        u
        for u in heroes
        if any(x in u.lower() for x in ("jpg", "jpeg", "png", "webp", "beach"))
    ]
    return {"lizaProfiles": profiles, "environmentPlates": heroes[:20]}


def main() -> None:
    raw = HOME_RAW.read_text(encoding="utf-8", errors="replace")
    listings = parse_listing_boxes(raw)
    brand = extract_brand_media(raw)

    curated = [x for x in listings if not x.get("likelyRental")][:12]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (MEDIA_DIR / "liza").mkdir(parents=True, exist_ok=True)
    (MEDIA_DIR / "environments").mkdir(parents=True, exist_ok=True)
    (MEDIA_DIR / "listings").mkdir(parents=True, exist_ok=True)

    payload = {
        "sourceUrl": "https://lizakalawaia.legacyrealtyhi.com/",
        "extractedFrom": str(HOME_RAW.relative_to(ROOT)).replace("\\", "/"),
        "brand": brand,
        "counts": {"allCards": len(listings), "curatedForMorph": len(curated)},
        "liza": {
            "name": "Liza Lehua Kalawaia",
            "title": "Principal Broker & Owner",
            "brokerage": "Legacy Realty LLC",
            "tagline": "Your Legacy Starts Here.",
            "photos": brand["lizaProfiles"],
            "glb": "media/liza/glb/liza.glb",
            "glbStatus": "pending",
        },
        "environments": brand["environmentPlates"],
        "listingsAll": listings,
        "listingsCurated": curated,
        "pipeline": {
            "stages": [
                "extract",
                "download",
                "photo-to-glb-proxy",
                "ai-mesh-upgrade",
                "wire-experience",
            ],
            "notes": (
                "v1 creates textured plane GLBs from listing photos for particle/lens "
                "prototyping. Upgrade to Meshy/Tripo/etc. when API key available."
            ),
        },
    }

    out = OUT_DIR / "listings.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {out}")
    print(f"All: {len(listings)}  Curated: {len(curated)}")
    if curated:
        c0 = curated[0]
        print("Sample:", c0["id"], c0["morphText"], c0["price"], c0["listingUrl"])


if __name__ == "__main__":
    main()
