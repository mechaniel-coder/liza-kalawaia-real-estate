#!/usr/bin/env python3
"""
Register manually generated GLBs into data/listings.json.

Workflow:
  1. Generate mesh on Meshy/Tripo/etc. (free tier is fine)
  2. Export GLB
  3. Save as:
       media/liza/glb/liza.glb
       media/listings/{id}/glb/exterior.glb
       media/listings/{id}/glb/interior.glb   (optional)
  4. Run:  python scripts/register-manual-glbs.py

Optional: pass --copy-from PATH to copy a downloaded file into the right slot.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "listings.json"


def looks_like_manual_mesh(path: Path) -> bool:
    """Proxy photo-planes from generate-proxy-glb.py are typically well under ~1.5MB."""
    return path.stat().st_size >= 1_500_000


def register(payload: dict, *, promote_all: bool = False) -> list[str]:
    notes: list[str] = []

    liza_glb = ROOT / "media" / "liza" / "glb" / "liza.glb"
    if liza_glb.exists() and liza_glb.stat().st_size > 0:
        payload["liza"]["glb"] = "media/liza/glb/liza.glb"
        if promote_all or looks_like_manual_mesh(liza_glb) or payload["liza"].get("_promote"):
            payload["liza"]["glbStatus"] = "manual"
            payload["liza"].pop("_promote", None)
            notes.append(f"liza.glb -> manual ({liza_glb.stat().st_size} bytes)")
        else:
            notes.append(
                f"liza.glb still proxy-sized ({liza_glb.stat().st_size} bytes) — overwrite then re-run"
            )
    else:
        notes.append("MISSING media/liza/glb/liza.glb")

    for item in payload.get("listingsCurated") or []:
        lid = item["id"]
        ext = ROOT / "media" / "listings" / lid / "glb" / "exterior.glb"
        interior = ROOT / "media" / "listings" / lid / "glb" / "interior.glb"
        item.setdefault("glb", {})
        if ext.exists() and ext.stat().st_size > 0:
            item["glb"]["exterior"] = f"media/listings/{lid}/glb/exterior.glb"
            if promote_all or looks_like_manual_mesh(ext) or item["glb"].get("_promote"):
                prev = item["glb"].get("status")
                item["glb"]["status"] = "manual"
                item["glb"].pop("_promote", None)
                notes.append(f"{lid} exterior ({prev} -> manual, {ext.stat().st_size} bytes)")
            else:
                notes.append(f"{lid} exterior still proxy-sized ({ext.stat().st_size} bytes)")
        else:
            notes.append(f"{lid} MISSING exterior.glb")
        if interior.exists() and interior.stat().st_size > 0:
            item["glb"]["interior"] = f"media/listings/{lid}/glb/interior.glb"
            item["glb"]["interiorStatus"] = "manual"
            notes.append(f"{lid} interior -> manual")

    return notes


def copy_into_slot(src: Path, kind: str, listing_id: str | None) -> Path:
    if kind == "liza":
        dest = ROOT / "media" / "liza" / "glb" / "liza.glb"
    elif kind == "exterior":
        if not listing_id:
            raise SystemExit("--listing required for exterior/interior")
        dest = ROOT / "media" / "listings" / listing_id / "glb" / "exterior.glb"
    elif kind == "interior":
        if not listing_id:
            raise SystemExit("--listing required for exterior/interior")
        dest = ROOT / "media" / "listings" / listing_id / "glb" / "interior.glb"
    else:
        raise SystemExit("kind must be liza|exterior|interior")
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    print(f"Copied {src} -> {dest}")
    return dest


def main() -> int:
    parser = argparse.ArgumentParser(description="Register manually generated GLBs")
    parser.add_argument("--copy-from", type=Path, help="Source GLB file to copy into a slot")
    parser.add_argument("--kind", choices=["liza", "exterior", "interior"], help="Slot for --copy-from")
    parser.add_argument("--listing", help="Listing MLS id for exterior/interior")
    parser.add_argument("--print-checklist", action="store_true", help="Print drop paths for curated listings")
    parser.add_argument(
        "--promote",
        action="store_true",
        help="Mark existing GLBs as manual even if small (after you overwrite proxies)",
    )
    args = parser.parse_args()

    payload = json.loads(DATA.read_text(encoding="utf-8"))

    if args.print_checklist:
        print("Manual GLB drop checklist")
        print("  media/liza/glb/liza.glb")
        for item in payload.get("listingsCurated") or []:
            print(f"  media/listings/{item['id']}/glb/exterior.glb")
            print(f"    # {item.get('morphText')}")
            print(f"    # photo: {(item.get('localPhotos') or ['?'])[0]}")
        return 0

    if args.copy_from:
        if not args.kind:
            raise SystemExit("--kind required with --copy-from")
        if not args.copy_from.exists():
            raise SystemExit(f"File not found: {args.copy_from}")
        copy_into_slot(args.copy_from, args.kind, args.listing)
        if args.kind == "liza":
            payload["liza"]["_promote"] = True
        else:
            hit = next(
                (x for x in payload.get("listingsCurated") or [] if x["id"] == args.listing),
                None,
            )
            if hit is not None:
                hit.setdefault("glb", {})["_promote"] = True

    notes = register(payload, promote_all=args.promote)
    DATA.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print("Registered:")
    for n in notes:
        print(" ", n)
    print(f"Updated {DATA}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
