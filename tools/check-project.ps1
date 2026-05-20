param(
    [string]$Root = (Resolve-Path "$PSScriptRoot\..").Path
)

$ErrorActionPreference = "Stop"
$failures = New-Object System.Collections.Generic.List[string]

function Assert-True {
    param(
        [bool]$Condition,
        [string]$Message
    )

    if (-not $Condition) {
        $failures.Add($Message)
    }
}

$htmlPath = Join-Path $Root "index.html"
$legacyHtmlPath = Join-Path $Root "landing-local-ai.html"
$readmePath = Join-Path $Root "README.md"
$jsPath = Join-Path $Root "js\main.js"
$cssPath = Join-Path $Root "css\styles.css"
$packageScriptPath = Join-Path $Root "tools\package-site.ps1"
$vercelConfigPath = Join-Path $Root "vercel.json"
$netlifyConfigPath = Join-Path $Root "netlify.toml"

$html = Get-Content -Raw $htmlPath
$legacyHtml = Get-Content -Raw $legacyHtmlPath
$readme = Get-Content -Raw $readmePath
$js = Get-Content -Raw $jsPath
$css = Get-Content -Raw $cssPath

Assert-True (Test-Path (Join-Path $Root "assets\logo.svg")) "Missing assets/logo.svg"
Assert-True (Test-Path (Join-Path $Root "assets\favicon.svg")) "Missing assets/favicon.svg"
Assert-True (Test-Path (Join-Path $Root "index.html")) "Missing index.html entry point"
Assert-True (Test-Path $packageScriptPath) "Missing tools/package-site.ps1"
Assert-True (Test-Path $vercelConfigPath) "Missing vercel.json"
Assert-True (Test-Path $netlifyConfigPath) "Missing netlify.toml"

Assert-True ($html -notmatch 'http-equiv="refresh"') "index.html is still a redirect instead of the real page"
Assert-True ($html -match '<meta name="description"') "Missing meta description"
Assert-True ($html -match 'property="og:title"') "Missing Open Graph metadata"
Assert-True ($html -match 'name="twitter:card"') "Missing Twitter card metadata"
Assert-True ($html -match '<link rel="canonical"') "Missing canonical link"
Assert-True ($html -match 'application/ld\+json') "Missing schema.org JSON-LD"
Assert-True ($html -notmatch 'cdn\.jsdelivr\.net/npm/chart\.js') "Unused Chart.js CDN is still loaded"
Assert-True ($html -notmatch 'cdn\.jsdelivr\.net|fonts\.googleapis\.com|fonts\.gstatic\.com') "Page still depends on external CDN/font assets"
Assert-True ($html -notmatch 'particles\.js') "Page still depends on particles.js"
Assert-True ($html -match 'assets/logo\.svg') "HTML does not reference the local SVG logo"
Assert-True ($html -match 'assets/favicon\.svg') "HTML does not reference the local SVG favicon"
Assert-True ($html -match '<a class="cta-btn') "CTA is not a real link"
Assert-True ($html -match 'href="#demo"') "Primary CTA does not point to the demo section"
Assert-True (($html | Select-String -Pattern 'target="_blank"' -AllMatches).Matches.Count -eq ($html | Select-String -Pattern 'rel="noopener noreferrer"' -AllMatches).Matches.Count) "External blank links are missing rel=noopener noreferrer"
Assert-True ($html -match 'id="product"') "Missing product section"
Assert-True ($html -match 'id="workflow"') "Missing workflow section"
Assert-True ($html -match 'id="privacy"') "Missing privacy section"
Assert-True ($html -match 'id="demo"') "Missing demo/contact section"
Assert-True ($html -match 'Local-first') "Product positioning copy is missing"
Assert-True ($legacyHtml -match 'url=index\.html') "Legacy page does not redirect to index.html"

Assert-True ($js -notmatch 'particlesJS') "main.js still references particlesJS"
Assert-True ($js -match 'IntersectionObserver' -and $js -match 'classList\.add\("show"\)') "main.js does not preserve fade-up behavior"
Assert-True ($js -match 'demo-form') "main.js does not wire the demo form"
Assert-True ($css -match 'prefers-reduced-motion') "CSS is missing reduced-motion handling"
Assert-True ($css -match 'footer') "CSS is missing footer styling"
Assert-True ($css -match '\.container') "CSS is missing container styling"
Assert-True ($css -match '\.orbital-field') "CSS is missing local hero visual styling"

Assert-True ($readme -match 'tools/package-site\.ps1') "README does not document the package script"
Assert-True ($readme -match 'assets/logo\.svg') "README does not document logo asset"
Assert-True ($readme -match 'index\.html') "README does not document index.html"
Assert-True ($readme -match 'sin dependencias externas') "README does not document the local/offline posture"

if ($failures.Count -gt 0) {
    Write-Host "Project checks failed:" -ForegroundColor Red
    foreach ($failure in $failures) {
        Write-Host " - $failure" -ForegroundColor Red
    }
    exit 1
}

Write-Host "Project checks passed." -ForegroundColor Green
