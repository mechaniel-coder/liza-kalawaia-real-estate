#!/usr/bin/env python3
"""Download Liza, environment, and curated listing photos for the 3D pipeline."""

from __future__ import annotations

import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "listings.json"
UA = "Mozilla/5.0 (compatible; LegacyRealtyPipeline/1.0; +local-research)"


def download(url: str, dest: Path, timeout: int = 60) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        return True
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "image/*,*/*"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
        if not data:
            return False
        dest.write_bytes(data)
        return True
    except Exception as e:  # noqa: BLE001
        print(f"  FAIL {url} -> {e}")
        # try alternate full-res path if thumb failed upgrade already tried
        return False


def ext_from_url(url: str) -> str:
    m = re.search(r"\.(jpe?g|png|webp|gif)(?:\?|$)", url, re.I)
    return (m.group(1).lower() if m else "jpg").replace("jpeg", "jpg")


def main() -> int:
    if not DATA.exists():
        print("Run extract-listings-media.py first")
        return 1
    payload = json.loads(DATA.read_text(encoding="utf-8"))
    manifest = {"downloaded": [], "failed": []}

    # Liza headshot(s) only — never treat brokerage logo as a portrait
    logo_url = (payload.get("brand") or {}).get("logo")
    headshots = payload.get("liza", {}).get("photos") or (payload.get("brand") or {}).get(
        "lizaHeadshot"
    ) or []
    for i, url in enumerate(headshots):
        if logo_url and url == logo_url:
            print(f"Skip logo-as-photo: {url}")
            continue
        ext = ext_from_url(url)
        dest = ROOT / "media" / "liza" / "photos" / f"profile-{i+1}.{ext}"
        print(f"Liza headshot {i+1}: {url}")
        ok = download(url, dest)
        (manifest["downloaded"] if ok else manifest["failed"]).append(str(dest.relative_to(ROOT)))

    if logo_url:
        ext = ext_from_url(logo_url)
        dest = ROOT / "media" / "brand" / f"logo-legacy-realty.{ext}"
        print(f"Brand logo: {logo_url}")
        ok = download(logo_url, dest)
        (manifest["downloaded"] if ok else manifest["failed"]).append(str(dest.relative_to(ROOT)))
        payload.setdefault("brand", {})["logoLocal"] = str(dest.relative_to(ROOT)).replace("\\", "/")

    # Environments
    for i, url in enumerate(payload.get("environments") or []):
        ext = ext_from_url(url)
        dest = ROOT / "media" / "environments" / f"plate-{i+1}.{ext}"
        print(f"Env {i+1}: {url[:90]}...")
        ok = download(url, dest)
        (manifest["downloaded"] if ok else manifest["failed"]).append(str(dest.relative_to(ROOT)))

    # Curated listings — try full then thumb
    curated = payload.get("listingsCurated") or []
    for item in curated:
        lid = item["id"]
        photos = item.get("photos") or []
        local_photos = []
        for i, ph in enumerate(photos):
            full = ph.get("full") or ph.get("thumb")
            thumb = ph.get("thumb") or full
            ext = ext_from_url(full or thumb)
            base = ROOT / "media" / "listings" / lid / "photos"
            dest_full = base / "exteriors" / f"{lid}-{i+1}.{ext}"
            print(f"Listing {lid} photo {i+1}")
            ok = download(full, dest_full)
            if not ok and thumb and thumb != full:
                ok = download(thumb, dest_full)
            if ok:
                local_photos.append(str(dest_full.relative_to(ROOT)).replace("\\", "/"))
                manifest["downloaded"].append(str(dest_full.relative_to(ROOT)))
            else:
                manifest["failed"].append(full or thumb)
            time.sleep(0.15)
        item["localPhotos"] = local_photos
        # placeholder dirs for pipeline stages
        (ROOT / "media" / "listings" / lid / "glb").mkdir(parents=True, exist_ok=True)
        (ROOT / "media" / "listings" / lid / "interiors").mkdir(parents=True, exist_ok=True)

    (ROOT / "media" / "liza" / "glb").mkdir(parents=True, exist_ok=True)

    DATA.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    man_path = ROOT / "media" / "_download-manifest.json"
    man_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Downloaded: {len(manifest['downloaded'])}  Failed: {len(manifest['failed'])}")
    print(f"Manifest: {man_path}")
    return 0 if manifest["downloaded"] else 1


if __name__ == "__main__":
    sys.exit(main())
