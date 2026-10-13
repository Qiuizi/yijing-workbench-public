param(
    [string]$OutputDirectory
)

$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$frontendDir = Join-Path $repoRoot 'frontend'
$sourceSvg = Join-Path $repoRoot 'frontend\src-tauri\icons-source\yijing-workbench.svg'
if (-not $OutputDirectory) {
    $OutputDirectory = Join-Path $repoRoot 'frontend\src-tauri\icons-project'
}
$OutputDirectory = [System.IO.Path]::GetFullPath($OutputDirectory)

if (-not (Test-Path -LiteralPath $sourceSvg -PathType Leaf)) {
    throw "Icon source is missing: $sourceSvg"
}
$npm = Get-Command npm.cmd -ErrorAction Stop

Push-Location -LiteralPath $frontendDir
try {
    & $npm.Source exec -- tauri icon $sourceSvg --output $OutputDirectory
    if ($LASTEXITCODE -ne 0) {
        throw "Tauri icon generation failed with exit code $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}

$requiredFiles = @('32x32.png', '128x128.png', '128x128@2x.png', 'icon.png', 'icon.ico', 'icon.icns')
foreach ($name in $requiredFiles) {
    $path = Join-Path $OutputDirectory $name
    if (-not (Test-Path -LiteralPath $path -PathType Leaf) -or (Get-Item -LiteralPath $path).Length -eq 0) {
        throw "Tauri icon generator did not produce a required file: $path"
    }
}

Write-Output "Generated icon set from $sourceSvg into $OutputDirectory"
