param(
    [string]$OutputPath = (Join-Path (Resolve-Path "$PSScriptRoot\..").Path "local-ai-landing-ultra3d-tools.zip")
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path "$PSScriptRoot\..").Path
$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("local-ai-landing-package-" + [System.Guid]::NewGuid().ToString("N"))
$packageRoot = Join-Path $tempRoot "local-ai-landing-ultra3d-tools"

New-Item -ItemType Directory -Path $packageRoot | Out-Null

$items = @(
    "README.md",
    "index.html",
    "landing-local-ai.html",
    "css",
    "js",
    "assets",
    "vercel.json",
    "netlify.toml",
    "tools\check-project.ps1",
    "tools\package-site.ps1"
)

foreach ($item in $items) {
    $source = Join-Path $root $item
    $destination = Join-Path $packageRoot $item
    if (Test-Path $source -PathType Container) {
        Copy-Item -Recurse -Path $source -Destination $destination
    } else {
        New-Item -ItemType Directory -Path (Split-Path $destination -Parent) -Force | Out-Null
        Copy-Item -Path $source -Destination $destination
    }
}

if (Test-Path $OutputPath) {
    Remove-Item -LiteralPath $OutputPath
}

Compress-Archive -Path $packageRoot -DestinationPath $OutputPath
Remove-Item -Recurse -Force -LiteralPath $tempRoot

Write-Host "Package created: $OutputPath"
