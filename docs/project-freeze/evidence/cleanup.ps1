param([switch]$Apply)
$ErrorActionPreference='Stop'
$root='D:\Qiuizi\project\yijing'
$protected=@("$root\.qa-work\project-freeze-20261106","$root\docs\project-freeze")
$cacheNames=@('node_modules','.venv','target','dist','__pycache__','.pytest_cache','.mypy_cache','.ruff_cache','EBWebView','.vite','htmlcov')
function MB($items){ if(-not $items){return 0}; [math]::Round((($items|Measure-Object Length -Sum).Sum)/1MB,1) }
function DirSize($p){ $s=(Get-ChildItem -LiteralPath $p -Recurse -File -Force -ErrorAction SilentlyContinue|Measure-Object Length -Sum).Sum; [math]::Round($s/1MB,1) }
$targets=@()
# 1) cache directories (do not descend into them)
$stack=[System.Collections.Generic.Stack[string]]::new(); $stack.Push($root)
while($stack.Count){
  $dir=$stack.Pop()
  if($protected | Where-Object { $dir -eq $_ -or $dir.StartsWith($_+'\') }){ continue }
  $children=Get-ChildItem -LiteralPath $dir -Directory -Force -ErrorAction SilentlyContinue
  foreach($c in $children){
    if($c.Attributes -band [System.IO.FileAttributes]::ReparsePoint){ continue }
    if($c.Name -eq '.git'){ continue }
    if($cacheNames -contains $c.Name){ $targets += [pscustomobject]@{Path=$c.FullName;Kind='cache';MB=(DirSize $c.FullName)}; continue }
    $stack.Push($c.FullName)
  }
}
# 2) explicit install/unpack payload directories
$explicit=@(
 "$root\.qa-work\v3.3.3\install-official","$root\.qa-work\v3.3.3\install-fresh","$root\.qa-work\v3.3.3\install-upgrade",
 "$root\.qa-work\v3.3.3\updater-run\install-331","$root\.qa-work\v3.3.3\extract-331",
 "$root\.qa-work\v3.3.2\install-fixqa","$root\.qa-work\v3.3.2\updater-qa\install-3.3.1","$root\.qa-work\v3.3.2\extract-3.3.1",
 "$root\docs\review\ui-audit-node-modules-backup","$root\docs\review\ui-audit-vite-cache-backup"
)
$explicit += (Get-ChildItem "$root\.qa-work\v3.3.3\inapp-332\reconstruct-332" -Directory -Filter 'install-baseline-pristine-*' -ErrorAction SilentlyContinue).FullName
foreach($p in $explicit){ if(Test-Path -LiteralPath $p){ $targets += [pscustomobject]@{Path=$p;Kind='install/extract';MB=(DirSize $p)} } }
# 3) unpacked payload: delete only binaries/resources subdirs, keep verification json/md evidence
$payload=@("$root\.qa-work\v3.3.3\candidate\extracted","$root\.qa-work\v3.3.3\reverify-live\extracted","$root\.qa-work\v3.3.3\inapp-332\reconstruct-332\baseline-check\extracted","$root\.qa-work\v3.3.3\inapp-332\keycheck\extract-candidate")
$payload += (Get-ChildItem "$root\.qa-work\v3.3.3\inapp-332\github-audit" -Directory -ErrorAction SilentlyContinue | ForEach-Object { Join-Path $_.FullName 'extracted' })
foreach($p in $payload){ foreach($sub in 'binaries','resources'){ $q=Join-Path $p $sub; if(Test-Path -LiteralPath $q){ $targets += [pscustomobject]@{Path=$q;Kind='payload';MB=(DirSize $q)} } } }
$targets=$targets | Sort-Object Path -Unique
# drop nested targets (a parent directory will be removed as a whole)
$kept=@()
foreach($t in ($targets | Sort-Object { $_.Path.Length })){
  $nested=$false
  foreach($k in $kept){ if($t.Path.StartsWith($k.Path+'\')){ $nested=$true; break } }
  if(-not $nested){ $kept += $t }
}
$targets=$kept
$before=(Get-ChildItem $root -Recurse -File -Force -ErrorAction SilentlyContinue|Measure-Object Length -Sum).Sum
"BEFORE_MB=$([math]::Round($before/1MB,0)) TARGETS=$($targets.Count) TARGET_MB=$(($targets|Measure-Object MB -Sum).Sum)"
$targets | Format-Table Kind,MB,Path -Auto | Out-String -Width 240
if($Apply){
  foreach($t in $targets){
    $p=$t.Path
    if($p -notlike "$root\*"){ throw "outside workspace: $p" }
    if($protected | Where-Object { $p -eq $_ -or $p.StartsWith($_+'\') }){ continue }
    if($p -match '\.(exe|sqlite3?|key|pub|sig)$'){ throw "protected file: $p" }
    Remove-Item -LiteralPath $p -Recurse -Force
  }
  $after=(Get-ChildItem $root -Recurse -File -Force -ErrorAction SilentlyContinue|Measure-Object Length -Sum).Sum
  "AFTER_MB=$([math]::Round($after/1MB,0)) FREED_MB=$([math]::Round(($before-$after)/1MB,0))"
  $targets | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath "$root\docs\project-freeze\evidence\cleanup-deleted.json" -Encoding utf8
}
