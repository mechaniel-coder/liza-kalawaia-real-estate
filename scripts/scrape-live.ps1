<#
.SYNOPSIS
  Scrape a live page into HTML, plaintext, and links JSON.

.PARAMETER Url
  Full https URL to fetch.

.PARAMETER OutDir
  Output folder. Defaults under .\research\live\<host-slug>\

.EXAMPLE
  .\scripts\scrape-live.ps1 -Url "https://lizakalawaia.legacyrealtyhi.com/contact.php"
#>
[CmdletBinding()]
param(
  [Parameter(Mandatory = $true, Position = 0)]
  [string] $Url,

  [string] $OutDir = "",

  [string] $UserAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

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
      finally { $gz.Dispose(); $out.Dispose() }
    }
    finally { $in.Dispose() }
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
  return [regex]::Replace($plain, '\s+', ' ').Trim()
}

function Get-SlugFromUrl {
  param([string] $InputUrl)
  $u = [Uri]$InputUrl
  $hostPart = ($u.Host -replace '^www\.', '')
  $path = ($u.AbsolutePath.Trim('/') -replace '[^a-zA-Z0-9]+', '-').Trim('-')
  if ([string]::IsNullOrWhiteSpace($path)) { $path = "home" }
  $q = ""
  if ($u.Query) { $q = "-" + (($u.Query.TrimStart('?') -replace '[^a-zA-Z0-9]+', '-').Trim('-')) }
  return "$hostPart-$path$q"
}

$repoRoot = Split-Path $PSScriptRoot -Parent
$slug = Get-SlugFromUrl -InputUrl $Url
if ([string]::IsNullOrWhiteSpace($OutDir)) {
  $OutDir = Join-Path $repoRoot "research\live\$slug"
}
New-Item -ItemType Directory -Path $OutDir -Force | Out-Null

$rawPath = Join-Path $OutDir "page.raw"
$htmlPath = Join-Path $OutDir "page.html"
$plainPath = Join-Path $OutDir "page.txt"
$jsonPath = Join-Path $OutDir "links.json"
$metaPath = Join-Path $OutDir "meta.json"

Write-Host "Fetching: $Url"
$httpCode = & curl.exe -sL --compressed `
  -A $UserAgent `
  -H "Accept: text/html,application/xhtml+xml;q=0.9,*/*;q=0.8" `
  -o $rawPath `
  -w "%{http_code}" `
  --max-time 90 `
  $Url

if ($LASTEXITCODE -ne 0) { throw "curl exit $LASTEXITCODE for $Url" }
if ($httpCode -notin @("200", "203")) { throw "HTTP $httpCode for $Url" }

$rawBytes = [System.IO.File]::ReadAllBytes($rawPath)
$html = [System.Text.Encoding]::UTF8.GetString((Read-PossiblyGzipBytes -Bytes $rawBytes))
if ($html.Length -gt 0 -and [int][char]$html[0] -eq 0xFEFF) { $html = $html.Substring(1) }
[System.IO.File]::WriteAllText($htmlPath, $html, [System.Text.UTF8Encoding]::new($false))

$plain = ConvertTo-PlainText -Html $html
[System.IO.File]::WriteAllText($plainPath, $plain, [System.Text.UTF8Encoding]::new($false))

$title = ""
$tm = [regex]::Match($html, '(?is)<title[^>]*>(.*?)</title>')
if ($tm.Success) { $title = [System.Net.WebUtility]::HtmlDecode(($tm.Groups[1].Value -replace '\s+', ' ').Trim()) }

$allHrefs = [regex]::Matches($html, '(?is)\bhref\s*=\s*["'']([^"'']+)["'']') |
  ForEach-Object { $_.Groups[1].Value.Trim() } |
  Where-Object { $_ -and $_ -notmatch '^(#|javascript:|mailto:|tel:)' } |
  Sort-Object -Unique

$payload = [ordered]@{
  scrapedAt    = (Get-Date).ToString("o")
  url          = $Url
  httpStatus   = $httpCode
  title        = $title
  plainLength  = $plain.Length
  htmlLength   = $html.Length
  hrefCount    = @($allHrefs).Count
  hrefs        = @($allHrefs)
}
$payload | ConvertTo-Json -Depth 5 | Set-Content -Path $jsonPath -Encoding utf8
@{
  scrapedAt  = $payload.scrapedAt
  url        = $Url
  httpStatus = $httpCode
  title      = $title
  files      = @{ html = "page.html"; text = "page.txt"; links = "links.json"; raw = "page.raw" }
} | ConvertTo-Json -Depth 5 | Set-Content -Path $metaPath -Encoding utf8

Write-Host "Title: $title"
Write-Host "Wrote: $OutDir  (hrefs=$(@($allHrefs).Count) plain=$($plain.Length))"
