#!/usr/bin/env python3
"""
Build textured plane GLBs from listing/Liza photos (pipeline v1 proxy meshes).

These are valid orbitable GLBs for the hover-lens / particle prototype.
Replace with AI mesh results later via generate-ai-mesh.py when an API key exists.
"""

from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "listings.json"

try:
    from PIL import Image
except ImportError:
    Image = None  # type: ignore


def pad4(n: int) -> int:
    return (4 - (n % 4)) % 4


def build_textured_plane_glb(image_path: Path, out_path: Path, max_size: int = 1024) -> None:
    """Minimal glTF 2.0 binary: textured quad facing +Z."""
    if Image is None:
        raise RuntimeError("Pillow required: pip install pillow")

    img = Image.open(image_path).convert("RGBA")
    w, h = img.size
    scale = min(1.0, max_size / max(w, h))
    if scale < 1.0:
        img = img.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.Resampling.LANCZOS)
        w, h = img.size

    # Aspect-correct plane (width = aspect, height = 1)
    aspect = w / h
    hw, hh = aspect * 0.5, 0.5

    # positions (4) + normals (4) + uvs (4) + indices (6)
    positions = [
        -hw, -hh, 0.0,
         hw, -hh, 0.0,
         hw,  hh, 0.0,
        -hw,  hh, 0.0,
    ]
    normals = [
        0.0, 0.0, 1.0,
        0.0, 0.0, 1.0,
        0.0, 0.0, 1.0,
        0.0, 0.0, 1.0,
    ]
    uvs = [
        0.0, 1.0,
        1.0, 1.0,
        1.0, 0.0,
        0.0, 0.0,
    ]
    indices = [0, 1, 2, 0, 2, 3]

    pos_b = b"".join(struct.pack("<f", f) for f in positions)
    norm_b = b"".join(struct.pack("<f", f) for f in normals)
    uv_b = b"".join(struct.pack("<f", f) for f in uvs)
    idx_b = b"".join(struct.pack("<H", i) for i in indices)
    idx_pad = pad4(len(idx_b))
    idx_b_padded = idx_b + (b"\x00" * idx_pad)

    # PNG image bytes
    import io

    bio = io.BytesIO()
    img.save(bio, format="PNG")
    img_b = bio.getvalue()
    img_pad = pad4(len(img_b))
    img_b_padded = img_b + (b"\x00" * img_pad)

    bin_blob = pos_b + norm_b + uv_b + idx_b_padded + img_b_padded

    def o(name: int) -> int:
        return name

    pos_len = len(pos_b)
    norm_off = pos_len
    uv_off = norm_off + len(norm_b)
    idx_off = uv_off + len(uv_b)
    img_off = idx_off + len(idx_b_padded)

    gltf = {
        "asset": {"version": "2.0", "generator": "liza-pipeline-proxy-glb"},
        "buffers": [{"byteLength": len(bin_blob)}],
        "bufferViews": [
            {"buffer": 0, "byteOffset": 0, "byteLength": pos_len, "target": 34962},
            {"buffer": 0, "byteOffset": norm_off, "byteLength": len(norm_b), "target": 34962},
            {"buffer": 0, "byteOffset": uv_off, "byteLength": len(uv_b), "target": 34962},
            {"buffer": 0, "byteOffset": idx_off, "byteLength": len(idx_b), "target": 34963},
            {"buffer": 0, "byteOffset": img_off, "byteLength": len(img_b)},
        ],
        "accessors": [
            {
                "bufferView": 0,
                "componentType": 5126,
                "count": 4,
                "type": "VEC3",
                "max": [hw, hh, 0.0],
                "min": [-hw, -hh, 0.0],
            },
            {"bufferView": 1, "componentType": 5126, "count": 4, "type": "VEC3"},
            {
                "bufferView": 2,
                "componentType": 5126,
                "count": 4,
                "type": "VEC2",
            },
            {
                "bufferView": 3,
                "componentType": 5123,
                "count": 6,
                "type": "SCALAR",
            },
        ],
        "images": [{"bufferView": 4, "mimeType": "image/png"}],
        "samplers": [{"magFilter": 9729, "minFilter": 9729, "wrapS": 10497, "wrapT": 10497}],
        "textures": [{"sampler": 0, "source": 0}],
        "materials": [
            {
                "name": "photo",
                "pbrMetallicRoughness": {
                    "baseColorTexture": {"index": 0},
                    "metallicFactor": 0.0,
                    "roughnessFactor": 0.9,
                },
                "doubleSided": True,
                "alphaMode": "OPAQUE",
            }
        ],
        "meshes": [
            {
                "name": "photo_plane",
                "primitives": [
                    {
                        "attributes": {"POSITION": 0, "NORMAL": 1, "TEXCOORD_0": 2},
                        "indices": 3,
                        "material": 0,
                    }
                ],
            }
        ],
        "nodes": [{"name": "PhotoProxy", "mesh": 0}],
        "scenes": [{"nodes": [0]}],
        "scene": 0,
    }

    import json as _json

    json_bytes = _json.dumps(gltf, separators=(",", ":")).encode("utf-8")
    json_pad = pad4(len(json_bytes))
    json_chunk = json_bytes + (b" " * json_pad)

    total_len = 12 + 8 + len(json_chunk) + 8 + len(bin_blob)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("wb") as f:
        f.write(struct.pack("<4sII", b"glTF", 2, total_len))
        f.write(struct.pack("<I4s", len(json_chunk), b"JSON"))
        f.write(json_chunk)
        f.write(struct.pack("<I4s", len(bin_blob), b"BIN\x00"))
        f.write(bin_blob)


def first_local_photo(item: dict) -> Path | None:
    for p in item.get("localPhotos") or []:
        path = ROOT / p
        if path.exists():
            return path
    # fallback scan
    d = ROOT / "media" / "listings" / item["id"] / "photos" / "exteriors"
    if d.exists():
        files = sorted(d.glob("*"))
        if files:
            return files[0]
    return None


def main() -> int:
    if Image is None:
        print("Installing pillow...")
        import subprocess

        subprocess.check_call([sys.executable, "-m", "pip", "install", "pillow", "-q"])
        from PIL import Image as _Image

        globals()["Image"] = _Image

    payload = json.loads(DATA.read_text(encoding="utf-8"))
    results = []

    # Liza
    liza_photos = list((ROOT / "media" / "liza" / "photos").glob("*"))
    if liza_photos:
        out = ROOT / "media" / "liza" / "glb" / "liza.glb"
        build_textured_plane_glb(liza_photos[0], out)
        payload["liza"]["glbStatus"] = "proxy-plane"
        payload["liza"]["proxySource"] = str(liza_photos[0].relative_to(ROOT)).replace("\\", "/")
        results.append(str(out.relative_to(ROOT)))
        print(f"Liza GLB: {out}")

    for item in payload.get("listingsCurated") or []:
        src = first_local_photo(item)
        if not src:
            item["glb"]["status"] = "missing-photo"
            continue
        out = ROOT / item["glb"]["exterior"]
        build_textured_plane_glb(src, out)
        item["glb"]["status"] = "proxy-plane"
        item["glb"]["proxySource"] = str(src.relative_to(ROOT)).replace("\\", "/")
        results.append(str(out.relative_to(ROOT)))
        print(f"Listing {item['id']} GLB: {out}")

    DATA.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Created {len(results)} proxy GLBs")
    return 0 if results else 1


if __name__ == "__main__":
    sys.exit(main())
