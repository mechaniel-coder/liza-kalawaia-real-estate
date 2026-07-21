<#
.SYNOPSIS
  Scrape a Wayback Machine snapshot into HTML, plaintext, and links JSON.

.DESCRIPTION
  Prefers the archive.org "id_" raw capture (no Wayback toolbar).
  Handles gzip responses that curl may leave compressed on disk.
  Default target: Liza NV site snapshot from the discovery brief.

.PARAMETER Url
  Full Wayback URL. Viewer or id_ forms both work; viewer URLs are normalized to id_.

.PARAMETER OutDir
  Output folder. Defaults to .\research\wayback\<timestamp-or-slug>\

.PARAMETER UserAgent
  Browser-like User-Agent (archive.org often blocks bare curl).

.EXAMPLE
  .\scripts\scrape-wayback.ps1

.EXAMPLE
  .\scripts\scrape-wayback.ps1 -Url "https://web.archive.org/web/20250221203024/https://www.homesbylizak.com/about-me/"

.EXAMPLE
  .\scripts\scrape-wayback.ps1 -Url "..." -OutDir ".\research\nv-about"
#>
[CmdletBinding()]
param(
  [Parameter(Position = 0)]
  [string] $Url = "https://web.archive.org/web/20250221203024/https://www.homesbylizak.com/",

  [string] $OutDir = "",

  [string] $UserAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function ConvertTo-WaybackIdUrl {
  param([string] $InputUrl)

  # Already id_ form
  if ($InputUrl -match 'web\.archive\.org/web/(\d{14})id_/(.+)$') {
    return "https://web.archive.org/web/$($Matches[1])id_/$($Matches[2])"
  }

  # Viewer form: /web/TIMESTAMP/https://...  or /web/TIMESTAMP if_/ ...
  if ($InputUrl -match 'web\.archive\.org/web/(\d{14})(?:[a-z]{2}_)?/(.+)$') {
    return "https://web.archive.org/web/$($Matches[1])id_/$($Matches[2])"
  }

  throw "Not a recognized Wayback Machine URL: $InputUrl"
}

function Get-WaybackStamp {
  param([string] $IdUrl)
  if ($IdUrl -match '/web/(\d{14})id_/') { return $Matches[1] }
  return (Get-Date -Format "yyyyMMddHHmmss")
}

function Get-OriginalUrl {
  param([string] $IdUrl)
  if ($IdUrl -match '/web/\d{14}id_/(.+)$') { return $Matches[1] }
  return $IdUrl
}

function Get-SlugFromUrl {
  param([string] $OriginalUrl)
  try {
    $u = [Uri]$OriginalUrl
    $hostPart = $u.Host -replace '^www\.', ''
    $path = ($u.AbsolutePath -replace '[^a-zA-Z0-9]+', '-').Trim('-')
    if ([string]::IsNullOrWhiteSpace($path)) { $path = "home" }
    return "$hostPart-$path"
  }
  catch {
    return "wayback-page"
  }
}

function Read-PossiblyGzipBytes {
  param([byte[]] $Bytes)

  if ($Bytes.Length -ge 2 -and $Bytes[0] -eq 0x1F -and $Bytes[1] -eq 0x8B) {
    $in = New-Object System.IO.MemoryStream(,$Bytes)
    try {
      $gz = New-Object System.IO.Compression.GzipStream($in, [System.IO.Compression.CompressionMode]::Decompress)
      $out = New-Object System.IO.MemoryStream
      try {
        $gz.CopyTo($out)
        return $out.ToArray()
      }
      finally {
        $gz.Dispose()
        $out.Dispose()
      }
    }
    finally {
      $in.Dispose()
    }
  }

  return $Bytes
}

function ConvertTo-PlainText {
  param([string] $Html)

  $plain = [regex]::Replace($Html, '(?is)<script[^>]*>.*?</script>', ' ')
  $plain = [regex]::Replace($plain, '(?is)<style[^>]*>.*?</style>', ' ')
  $plain = [regex]::Replace($plain, '(?is)<noscript[^>]*>.*?</noscript>', ' ')
  $plain = [regex]::Replace($plain, '(?is)<!--.*?-->', ' ')
  $plain = [regex]::Replace($plain, '(?is)<[^>]+>', ' ')
  $plain = [System.Net.WebUtility]::HtmlDecode($plain)
  $plain = [regex]::Replace($plain, '\s+', ' ').Trim()
  return $plain
}

# --- main ---

$idUrl = ConvertTo-WaybackIdUrl -InputUrl $Url
$stamp = Get-WaybackStamp -IdUrl $idUrl
$original = Get-OriginalUrl -IdUrl $idUrl
$slug = Get-SlugFromUrl -OriginalUrl $original

if ([string]::IsNullOrWhiteSpace($OutDir)) {
  # $PSScriptRoot is .../scripts → parent is repo root
  $repoRoot = Split-Path $PSScriptRoot -Parent
  $OutDir = Join-Path $repoRoot "research\wayback\${stamp}-${slug}"
}

New-Item -ItemType Directory -Path $OutDir -Force | Out-Null

$htmlPath = Join-Path $OutDir "page.html"
$plainPath = Join-Path $OutDir "page.txt"
$jsonPath = Join-Path $OutDir "links.json"
$metaPath = Join-Path $OutDir "meta.json"
$rawPath = Join-Path $OutDir "page.raw"

Write-Host "Fetching: $idUrl"
Write-Host "Output:   $OutDir"

$curl = Get-Command curl.exe -ErrorAction SilentlyContinue
if (-not $curl) {
  throw "curl.exe not found. Install curl or use Windows 10+ built-in curl.exe."
}

$httpCode = & curl.exe -sL --compressed `
  -A $UserAgent `
  -H "Accept: text/html,application/xhtml+xml;q=0.9,*/*;q=0.8" `
  -o $rawPath `
  -w "%{http_code}" `
  --max-time 90 `
  $idUrl

if ($LASTEXITCODE -ne 0) {
  throw "curl failed with exit code $LASTEXITCODE (SSL/network). Retry later or open the id_ URL in a browser and Save As."
}

if ($httpCode -notin @("200", "203")) {
  throw "HTTP $httpCode from archive.org. Try again later, or open this in a browser:`n  $idUrl"
}

$rawBytes = [System.IO.File]::ReadAllBytes($rawPath)
$decodedBytes = Read-PossiblyGzipBytes -Bytes $rawBytes
$html = [System.Text.Encoding]::UTF8.GetString($decodedBytes)

# Strip UTF-8 BOM if present
if ($html.Length -gt 0 -and [int][char]$html[0] -eq 0xFEFF) {
  $html = $html.Substring(1)
}

[System.IO.File]::WriteAllText($htmlPath, $html, [System.Text.UTF8Encoding]::new($false))

$plain = ConvertTo-PlainText -Html $html
[System.IO.File]::WriteAllText($plainPath, $plain, [System.Text.UTF8Encoding]::new($false))

$title = ""
$tm = [regex]::Match($html, '(?is)<title[^>]*>(.*?)</title>')
if ($tm.Success) {
  $title = [System.Net.WebUtility]::HtmlDecode(($tm.Groups[1].Value -replace '\s+', ' ').Trim())
}

$allHrefs = [regex]::Matches($html, '(?is)\bhref\s*=\s*["'']([^"'']+)["'']') |
  ForEach-Object { $_.Groups[1].Value.Trim() } |
  Where-Object { $_ -and $_ -notmatch '^(#|javascript:|mailto:|tel:)' } |
  Sort-Object -Unique

$socials = $allHrefs | Where-Object {
  $_ -match '(?i)(facebook|instagram|youtube|linkedin|twitter|x)\.com'
}

$internalish = $allHrefs | Where-Object {
  $_ -match '(?i)homesbylizak\.com|web\.archive\.org/web/.+homesbylizak'
}

$emails = [regex]::Matches($plain, '(?i)[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}') |
  ForEach-Object { $_.Value } | Sort-Object -Unique

$phones = [regex]::Matches($plain, '(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}') |
  ForEach-Object { $_.Value } | Sort-Object -Unique

$payload = [ordered]@{
  scrapedAt     = (Get-Date).ToString("o")
  inputUrl      = $Url
  idUrl         = $idUrl
  originalUrl   = $original
  waybackStamp  = $stamp
  httpStatus    = $httpCode
  title         = $title
  plainLength   = $plain.Length
  htmlLength    = $html.Length
  hrefCount     = @($allHrefs).Count
  hrefs         = @($allHrefs)
  socialUrls    = @($socials)
  siteUrls      = @($internalish)
  emails        = @($emails)
  phones        = @($phones)
}

$payload | ConvertTo-Json -Depth 6 | Set-Content -Path $jsonPath -Encoding utf8

$meta = [ordered]@{
  scrapedAt    = $payload.scrapedAt
  inputUrl     = $Url
  idUrl        = $idUrl
  originalUrl  = $original
  waybackStamp = $stamp
  httpStatus   = $httpCode
  title        = $title
  files        = @{
    html  = "page.html"
    text  = "page.txt"
    links = "links.json"
    raw   = "page.raw"
  }
}
$meta | ConvertTo-Json -Depth 5 | Set-Content -Path $metaPath -Encoding utf8

# raw is optional keep; leave for debugging gzip issues
Write-Host ""
Write-Host "Title:  $title"
Write-Host "Wrote:  $htmlPath"
Write-Host "        $plainPath"
Write-Host "        $jsonPath"
Write-Host "        $metaPath"
Write-Host "Hrefs:  $(@($allHrefs).Count)  |  Socials: $(@($socials).Count)"
