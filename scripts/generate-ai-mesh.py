#!/usr/bin/env python3
"""
Upgrade proxy GLBs to AI meshes when MESHY_API_KEY (or similar) is available.

Usage:
  set MESHY_API_KEY=...
  python scripts/generate-ai-mesh.py --listing 202613936
  python scripts/generate-ai-mesh.py --liza
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "listings.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--listing", help="MLS listing id")
    parser.add_argument("--liza", action="store_true")
    parser.add_argument("--provider", default="meshy", choices=["meshy"])
    args = parser.parse_args()

    key = os.environ.get("MESHY_API_KEY") or os.environ.get("TRIPO_API_KEY")
    if not key:
        print(
            "No MESHY_API_KEY / TRIPO_API_KEY in environment.\n"
            "Proxy GLBs from generate-proxy-glb.py remain the active 3D assets.\n"
            "Add an API key, then re-run this script to upgrade to true meshes."
        )
        return 2

    payload = json.loads(DATA.read_text(encoding="utf-8"))
    print("API key detected — Meshy integration stub ready for wiring.")
    print("Provider:", args.provider)
    if args.liza:
        print("Would submit:", payload["liza"].get("proxySource") or payload["liza"]["photos"])
    if args.listing:
        hit = next((x for x in payload.get("listingsCurated", []) if x["id"] == args.listing), None)
        print("Would submit listing:", args.listing, hit.get("localPhotos") if hit else None)
    print("TODO: implement Meshy image-to-3D POST + poll + download GLB.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
