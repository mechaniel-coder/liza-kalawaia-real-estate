# Run full media -> 3D proxy pipeline
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..
python scripts\extract-listings-media.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python scripts\download-listing-media.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python scripts\generate-proxy-glb.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python scripts\generate-ai-mesh.py
Write-Output "Pipeline complete. See data/listings.json and media/"
