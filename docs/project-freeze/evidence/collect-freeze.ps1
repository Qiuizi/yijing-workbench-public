$ErrorActionPreference='Stop'
$root='D:\Qiuizi\project\yijing'
$out=Join-Path $root 'docs\project-freeze\evidence'
$repo='Qiuizi/yijing-workbench-public'
function Save-Json($name,$value) { $value | ConvertTo-Json -Depth 40 | Set-Content -LiteralPath (Join-Path $out $name) -Encoding utf8 }
function Api($endpoint) { $r= & gh api $endpoint; if($LASTEXITCODE -ne 0){throw "GitHub query failed: $endpoint"}; return ($r | ConvertFrom-Json) }
function Meta($p) { $f=Get-Item -LiteralPath $p; [pscustomobject]@{path=$f.FullName;exists=$true;size=$f.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLower();modified_at=$f.LastWriteTimeUtc.ToString('o')} }
Save-Json 'audit-time.json' @{observed_at=(Get-Date -Format o);scope='Freeze inventory only; no build, installation, test execution or publication'}
$git=[ordered]@{head=(& git rev-parse HEAD);status=@(& git status --porcelain=v2 --branch);branches=@(& git branch -avv);local_refs=@(& git for-each-ref '--format=%(refname) %(objectname) %(upstream:track)' refs/heads refs/remotes);remote_refs=@(& git ls-remote --heads --tags origin);worktrees=@()}
$wtPaths=@(& git worktree list --porcelain | Where-Object {$_ -like 'worktree *'} | ForEach-Object {$_.Substring(9)})
$i=0
foreach($wt in $wtPaths){
 $i++; $status=@(& git -C $wt status --porcelain=v2 --branch); $raw=@(& git -C $wt diff --raw); $patch=@(& git -C $wt diff --binary); $staged=@(& git -C $wt diff --cached --binary)
 $cargo=Join-Path $wt 'frontend/src-tauri/Cargo.toml'; $cmeta=if(Test-Path -LiteralPath $cargo){Meta $cargo}else{$null}
 $git.worktrees+=@{path=$wt;head=(& git -C $wt rev-parse HEAD);status=$status;diff_raw=$raw;diff_patch=$patch;staged_patch=$staged;cargo=$cmeta;cargo_git_blob=(& git -C $wt rev-parse HEAD:frontend/src-tauri/Cargo.toml);cargo_worktree_blob=(& git -C $wt hash-object --no-filters frontend/src-tauri/Cargo.toml)}
 if($status | Where-Object {$_ -match 'Cargo.toml'}){ Copy-Item -LiteralPath $cargo -Destination (Join-Path $out "worktree-$i-Cargo.toml.snapshot") }
}
Save-Json 'git-audit.json' $git
$rels=@(Api "repos/$repo/releases?per_page=100")
Save-Json 'releases.json' $rels
Save-Json 'latest-release.json' (Api "repos/$repo/releases/latest")
Save-Json 'pull-requests.json' @(Api "repos/$repo/pulls?state=all&per_page=100")
Save-Json 'open-pull-requests.json' @(Api "repos/$repo/pulls?state=open&per_page=100")
Save-Json 'open-issues.json' @(Api "repos/$repo/issues?state=open&per_page=100")
$arts=@();$page=1
 do { $r=Api "repos/$repo/actions/artifacts?per_page=100&page=$page"; $arts+=@($r.artifacts);$page++ } while($r.artifacts.Count -eq 100)
Save-Json 'artifacts.json' @{observed_at=(Get-Date -Format o);total_count=$r.total_count;artifacts=$arts}
Save-Json 'workflows.json' (Api "repos/$repo/actions/workflows?per_page=100")
Save-Json 'recent-runs.json' (Api "repos/$repo/actions/runs?per_page=100")
$active=@()
foreach($s in @('queued','in_progress','waiting','pending','requested')) { $a=Api "repos/$repo/actions/runs?status=$s&per_page=100"; $active+=@($a.workflow_runs) }
Save-Json 'active-runs.json' $active
Save-Json 'cancelled-production-run.json' (Api "repos/$repo/actions/runs/42033806115")
Save-Json 'production-run-jobs.json' (Api "repos/$repo/actions/runs/42033806115/jobs?per_page=100")
Save-Json 'dry-run-jobs.json' (Api "repos/$repo/actions/runs/42032014347/jobs?per_page=100")
Save-Json 'release-environment.json' (Api "repos/$repo/environments/release")
Save-Json 'environment-secret-names.json' (Api "repos/$repo/environments/release/secrets")
Save-Json 'repository-secret-names.json' (Api "repos/$repo/actions/secrets")
Save-Json 'release-branch-policy.json' (Api "repos/$repo/environments/release/deployment-branch-policies")
Save-Json 'actions-permissions.json' (Api "repos/$repo/actions/permissions/workflow")
$keys=@();$keyDirs=@('C:\Users\123\.tauri\yijing-release',"$root\frontend\src-tauri\.updater-qa","$root\.qa-work\v3.3.2\updater-qa","$root\.workbuddy\post-release-qa\keys")
foreach($d in $keyDirs){ if(Test-Path -LiteralPath $d){foreach($f in Get-ChildItem -LiteralPath $d -File){if($f.Name -match '\.key(\.pub)?$|pubkey|password|passphrase|\.7z$|\.zip$|\.age$'){ $keys+=Meta $f.FullName }}} }
Save-Json 'security-file-metadata.json' @{files=$keys;offline_backup='SIGNING_BACKUP_UNVERIFIED';passphrase_separation='UNVERIFIED';private_content_read=$false}
$inventory=@(); $hashes=@(); $stack=[System.Collections.Generic.Stack[string]]::new();$stack.Push((Join-Path $root '.qa-work'));$errors=@()
while($stack.Count){$dir=$stack.Pop();try{$items=Get-ChildItem -LiteralPath $dir -Force -ErrorAction Stop}catch{$errors+=$dir;continue};foreach($f in $items){if($f.Attributes -band [System.IO.FileAttributes]::ReparsePoint){$inventory+=@{path=$f.FullName;kind='reparse-point-not-followed'};continue};if($f.PSIsContainer){if($f.Name -notin @('node_modules','.venv','.git','target','EBWebView','binaries','_internal')){$stack.Push($f.FullName)};continue};$inventory+=@{path=$f.FullName;size=$f.Length;modified_at=$f.LastWriteTimeUtc.ToString('o')};if($f.Name -match '(setup\.exe$|\.zip$|\.sig$|^provenance\.json$|^manifest.*\.json$|^latest\.json$|^SHA256SUMS\.txt$|timeline\.txt$|final-evidence\.json$|ACCEPTANCE-REPORT\.md$)'){$hashes+=Meta $f.FullName}}}
Save-Json 'qa-inventory.json' @{files=$inventory;errors=$errors;excluded_directories=@('node_modules','.venv','.git','target','EBWebView','binaries','_internal');note='Dependency/build/cache and installed sidecar subtrees excluded; all retained in place. No databases or private keys copied.'}
Save-Json 'qa-critical-hashes.json' $hashes
$untracked=@(& git ls-files --others --exclude-standard)
Save-Json 'untracked-files.json' @{paths=$untracked;note='Names only; contents not copied. Ignored QA inventory separately recorded.'}
Save-Json 'processes.json' @(Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'yijing|python|node|cargo|rustc|tauri' } | Select-Object ProcessId,ParentProcessId,Name,ExecutablePath)
Save-Json 'listeners.json' @(Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Select-Object LocalAddress,LocalPort,OwningProcess)
$site=Invoke-WebRequest 'https://qiuizi.github.io/yijing-workbench-public/'
$site.Content | Set-Content -LiteralPath (Join-Path $out 'website-index.html') -Encoding utf8
$scriptPaths=@([regex]::Matches($site.Content,'(?:src=")([^"]+\.js)') | ForEach-Object {$_.Groups[1].Value})
$siteAssets=@();foreach($p in $scriptPaths){$uri=[uri]::new([uri]'https://qiuizi.github.io/yijing-workbench-public/',$p);$f=Join-Path $out 'website-live.js';Invoke-WebRequest $uri.AbsoluteUri -OutFile $f;$siteAssets+=@{url=$uri.AbsoluteUri;metadata=(Meta $f)}}
Save-Json 'website-observation.json' @{status=$site.StatusCode;url='https://qiuizi.github.io/yijing-workbench-public/';assets=$siteAssets;observed_at=(Get-Date -Format o)}
Write-Output "AUDIT_SAVED $out; artifacts=$($arts.Count); QA_files=$($inventory.Count); keys=$($keys.Count); active_runs=$($active.Count)"
