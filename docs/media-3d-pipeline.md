# Media → 3D Pipeline

## Run

```powershell
.\scripts\run-media-3d-pipeline.ps1
```

Or step by step:

1. `python scripts/extract-listings-media.py` — parse live scrape → `data/listings.json`
2. `python scripts/download-listing-media.py` — download Liza / env / curated listing photos → `media/`
3. `python scripts/generate-proxy-glb.py` — textured plane GLBs for lens/orbit prototype
4. `python scripts/generate-ai-mesh.py` — upgrades to true meshes when `MESHY_API_KEY` is set

## Outputs

| Path | Purpose |
|------|---------|
| `data/listings.json` | Morph text, beds/baths/sqft, URLs, GLB paths |
| `media/liza/` | Profile photos + `glb/liza.glb` |
| `media/environments/` | Beach / area plates |
| `media/listings/{id}/photos/` | Listing photos |
| `media/listings/{id}/glb/exterior.glb` | Current 3D asset (proxy plane until AI mesh) |

## Manual generation (free Meshy / Tripo / etc.)

API automation needs a paid key. Free accounts work fine if you export GLBs by hand.

### Steps
1. Open the source photo (paths in checklist below).
2. Generate Image-to-3D in your free tool.
3. Download/export **GLB**.
4. Drop it into the matching path.
5. Run:

```powershell
python scripts/register-manual-glbs.py
```

Or copy in one shot:

```powershell
python scripts/register-manual-glbs.py --copy-from "$env:USERPROFILE\Downloads\model.glb" --kind exterior --listing 202613936
python scripts/register-manual-glbs.py --copy-from "$env:USERPROFILE\Downloads\liza.glb" --kind liza
python scripts/register-manual-glbs.py
```

Print drop targets anytime:

```powershell
python scripts/register-manual-glbs.py --print-checklist
```

### Suggested order
1. `media/liza/glb/liza.glb` — hero (source photo: `media/liza/photos/profile-1.png` only)
2. First 3 curated exteriors (sales homes, not rentals)
3. Optional `interior.glb` per listing for portal scenes

**Do not** use `media/brand/logo-legacy-realty.png` for Liza 3D — that file is the Legacy Realty LLC logo, not her portrait.

Proxy planes stay in place until you overwrite them — the site can keep prototyping meanwhile.

## Status notes

- **proxy-plane**: photo textured onto a 3D quad — enough for particle sampling, hover lens, and orbit prototype.
- **manual**: you dropped a real GLB from a free image-to-3D tool.
- **AI mesh (API)**: optional later if you get a paid key.
- MLS photo rights: confirm IDX/MLS reuse before public production use of generated 3D.
