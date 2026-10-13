$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$python = Join-Path $repoRoot '.venv\Scripts\python.exe'
$tauriDir = Join-Path $repoRoot 'frontend\src-tauri'
$workDir = Join-Path $tauriDir 'target\pyinstaller'
$binaryDir = Join-Path $tauriDir 'binaries'

if (-not (Test-Path -LiteralPath $python)) {
    throw "未找到项目虚拟环境 Python：$python。请先创建 .venv 并安装 requirements.txt、requirements-build.txt。"
}
& $python -m PyInstaller --version | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw '当前 Python 环境未安装 PyInstaller。请执行 pip install -r requirements-build.txt。'
}

New-Item -ItemType Directory -Force -Path $workDir, $binaryDir | Out-Null
$hexagramData = Join-Path $repoRoot 'backend\data\hexagrams.json'
$entrypoint = Join-Path $repoRoot 'backend\sidecar_main.py'
$vcRedistDir = $env:YIJING_VC_REDIST_DIR
if (-not $vcRedistDir -or -not (Test-Path -LiteralPath $vcRedistDir -PathType Container)) {
    throw '请将 YIJING_VC_REDIST_DIR 指向已安装的 Visual Studio x64 Microsoft.VC143.CRT REDIST 目录。'
}

$redistributableBinaries = @()
foreach ($name in @('vcruntime140.dll', 'vcruntime140_1.dll')) {
    $source = Join-Path $vcRedistDir $name
    if (-not (Test-Path -LiteralPath $source -PathType Leaf)) {
        throw "Microsoft REDIST 目录缺少 $name：$source"
    }
    $signature = Get-AuthenticodeSignature -FilePath $source
    if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'O=Microsoft Corporation') {
        throw "Microsoft REDIST 文件签名无效：$source"
    }
    $redistributableBinaries += @('--add-binary', "$source;.")
}

$pyInstallerArgs = @(
    '-m', 'PyInstaller',
    '--noconfirm',
    '--clean',
    '--onedir',
    '--name', 'yijing-backend',
    '--distpath', $binaryDir,
    '--workpath', $workDir,
    '--specpath', $workDir,
    '--paths', $repoRoot,
    '--add-data', "$hexagramData;backend\data",
    '--collect-all', 'tzdata',
    '--collect-all', 'lunar_python',
    '--hidden-import', 'uvicorn.logging',
    '--hidden-import', 'uvicorn.loops.auto',
    '--hidden-import', 'uvicorn.protocols.http.auto',
    '--hidden-import', 'uvicorn.lifespan.on',
    '--exclude-module', 'pytest',
    '--exclude-module', '_pytest',
    '--exclude-module', 'pygments',
    '--exclude-module', 'setuptools',
    '--exclude-module', '_distutils_hack'
)
$pyInstallerArgs += $redistributableBinaries
$pyInstallerArgs += $entrypoint

# Keep unrelated vendor application folders out of PyInstaller's DLL search
# path. Python, Windows system directories and explicit Microsoft REDIST files
# are the only native runtime sources for this build.
$basePrefix = (& $python -c 'import sys; print(sys.base_prefix)').Trim()
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $basePrefix -PathType Container)) {
    throw '无法解析当前虚拟环境的 CPython 基础目录。'
}
$originalPath = $env:PATH
try {
    $env:PATH = @(
        (Join-Path $basePrefix 'DLLs'),
        $basePrefix,
        (Join-Path $env:WINDIR 'System32'),
        $env:WINDIR
    ) -join [System.IO.Path]::PathSeparator
    & $python @pyInstallerArgs
    $pyInstallerExitCode = $LASTEXITCODE
}
finally {
    $env:PATH = $originalPath
}
if ($pyInstallerExitCode -ne 0) {
    throw "PyInstaller sidecar 构建失败，退出码 $pyInstallerExitCode。"
}

$outputDir = Join-Path $binaryDir 'yijing-backend'
$built = Join-Path $outputDir 'yijing-backend.exe'
if (-not (Test-Path -LiteralPath $built)) {
    throw "PyInstaller 没有生成预期 sidecar：$built"
}

# Windows supplies UCRT and API-set contracts. Do not ship copies discovered
# from unrelated software on the build host (Stable contained Honor PCManager copies).
$hostRuntimeResidues = @(
    Get-ChildItem -LiteralPath $outputDir -File -Recurse |
        Where-Object { $_.Name -ieq 'ucrtbase.dll' -or $_.Name -match '^api-ms-win-.*\.dll$' }
)
foreach ($residue in $hostRuntimeResidues) {
    Remove-Item -LiteralPath $residue.FullName -Force
}

foreach ($name in @('vcruntime140.dll', 'vcruntime140_1.dll')) {
    $sourceHash = (Get-FileHash -LiteralPath (Join-Path $vcRedistDir $name) -Algorithm SHA256).Hash
    $builtCopies = @(Get-ChildItem -LiteralPath $outputDir -File -Recurse -Filter $name)
    if ($builtCopies.Count -ne 1 -or (Get-FileHash -LiteralPath $builtCopies[0].FullName -Algorithm SHA256).Hash -ne $sourceHash) {
        throw "打包后的 $name 与官方 REDIST 源文件不一致。"
    }
}
Write-Output "Sidecar 构建完成：$built"
