# Liza Kalawaia Real Estate

Private project: discovery, media pipeline, and immersive site rebuild for Liza Lehua Kalawaia / Legacy Realty LLC (Hawaii) with Nevada dual-market context.

## Contents

- `docs/` — discovery brief + media→3D pipeline notes
- `data/listings.json` — curated listings + morph text for the experience
- `media/` — headshot, logo, env plates, listing photos (GLBs are local/manual)
- `research/` — live HI scrapes + NV Wayback research
- `scripts/` — extract, download, proxy GLB, manual GLB register

## Media → 3D (manual / free tier)

```powershell
python scripts/register-manual-glbs.py --print-checklist
```

See `docs/media-3d-pipeline.md`.
