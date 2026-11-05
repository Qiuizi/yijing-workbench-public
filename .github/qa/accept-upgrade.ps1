param(
  [Parameter(Mandatory = $true)][string]$CandidateArtifactId,
  [Parameter(Mandatory = $true)][string]$CandidateDigest,
  [Parameter(Mandatory = $true)][string]$CandidateSha,
  [Parameter(Mandatory = $true)][string]$CandidateRunId,
  [Parameter(Mandatory = $true)][string]$BaselineDigest,
  [string]$Repo = $env:GITHUB_REPOSITORY
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$work = Join-Path $env:RUNNER_TEMP 'qa-upgrade'
$evidence = Join-Path $work 'evidence'
New-Item -ItemType Directory -Force -Path $work, $evidence | Out-Null
$env:QA_EVIDENCE = $evidence
$env:PYTHONIOENCODING = 'utf-8'
# Synthetic-only key used to prove same-user DPAPI round-trip; never printed or uploaded.
$env:QA_EXPECTED_DPAPI_KEY = 'sk-qa-runner-v333-upgrade-not-a-real-key'
$result = [ordered]@{
  started_at = (Get-Date).ToString('o')
  candidate_artifact_id = $CandidateArtifactId
  candidate_source_sha = $CandidateSha
  baseline_version = '3.3.1'
  runner = [ordered]@{
    os = [System.Environment]::OSVersion.VersionString
    user = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
    session = (Get-Process -Id $PID).SessionId
    interactive = [System.Environment]::UserInteractive
  }
  steps = [ordered]@{}
}
function Save-Result {
  $result.finished_at = (Get-Date).ToString('o')
  $result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $evidence 'upgrade-result.json') -Encoding utf8
}
function Note([string]$name, $value) {
  $result.steps[$name] = $value
  Save-Result
}
function Get-UiaNames($root) {
  $all = $root.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.Condition]::TrueCondition)
  $names = @()
  for ($i = 0; $i -lt [Math]::Min($all.Count, 240); $i++) {
    $n = $all.Item($i).Current.Name
    if ($n) { $names += $n }
  }
  return $names
}
function Wait-AppRoot([int]$timeoutSec = 75) {
  $deadline = (Get-Date).AddSeconds($timeoutSec)
  while ((Get-Date) -lt $deadline) {
    $p = Get-Process yijing-workbench -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
    if ($p) {
      try {
        $candidate = [System.Windows.Automation.AutomationElement]::FromHandle($p.MainWindowHandle)
        if ($candidate) {
          $names = @(Get-UiaNames $candidate)
          if ($names.Count -gt 5) { return $candidate }
        }
      } catch {}
    }
    Start-Sleep -Milliseconds 800
  }
  return $null
}
function Find-Button($root, [string]$name) {
  $buttons = $root.FindAll([System.Windows.Automation.TreeScope]::Descendants,
    (New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty, [System.Windows.Automation.ControlType]::Button)))
  foreach ($b in $buttons) { if ($b.Current.Name -eq $name) { return $b } }
  return $null
}
function Find-ButtonLike($root, [string]$pattern) {
  $buttons = $root.FindAll([System.Windows.Automation.TreeScope]::Descendants,
    (New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty, [System.Windows.Automation.ControlType]::Button)))
  foreach ($b in $buttons) { if ($b.Current.Name -like $pattern) { return $b } }
  return $null
}
function Invoke-El($el) {
  if (-not $el) { throw 'element not found' }
  $el.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()
}
function Wait-Text($root, [string]$pattern, [int]$timeoutSec = 30) {
  $deadline = (Get-Date).AddSeconds($timeoutSec)
  while ((Get-Date) -lt $deadline) {
    $text = (Get-UiaNames $root) -join "`n"
    if ($text -match $pattern) { return $true }
    Start-Sleep -Milliseconds 600
  }
  return $false
}
function Get-ComboText($combo) {
  $walker = [System.Windows.Automation.TreeWalker]::ControlViewWalker
  $sib = $walker.GetNextSibling($combo)
  while ($sib) {
    if ($sib.Current.ControlType -eq [System.Windows.Automation.ControlType]::Text -and $sib.Current.Name) { return $sib.Current.Name }
    $sib = $walker.GetNextSibling($sib)
  }
  return $null
}
function Close-App($proc) {
  $graceful = $false
  $forced = $false
  if ($proc -and (Get-Process -Id $proc.Id -ErrorAction SilentlyContinue)) {
    try { $null = $proc.CloseMainWindow() } catch {}
    $deadline = (Get-Date).AddSeconds(20)
    while ((Get-Date) -lt $deadline) {
      if (-not (Get-Process -Id $proc.Id -ErrorAction SilentlyContinue)) { $graceful = $true; break }
      Start-Sleep -Milliseconds 500
    }
    if (-not $graceful) { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue; $forced = $true }
  }
  Start-Sleep -Seconds 6
  $sidecars = @(Get-Process yijing-backend -ErrorAction SilentlyContinue)
  if ($sidecars.Count -gt 0) { $sidecars | Stop-Process -Force -ErrorAction SilentlyContinue; Start-Sleep -Seconds 2 }
  return [ordered]@{ graceful = $graceful; forced = $forced; sidecar_orphan = ($sidecars.Count -gt 0); sidecar_pids = @($sidecars | ForEach-Object { $_.Id }) }
}

try {
  # 1) Download the published v3.3.1 baseline and the candidate artifact.
  $baseline = Join-Path $work 'baseline-3.3.1.exe'
  $baselineUrl = "https://github.com/$Repo/releases/download/v3.3.1/yijing-workbench-3.3.1-x64-setup.exe"
  Invoke-WebRequest -Uri $baselineUrl -OutFile $baseline -TimeoutSec 120
  $baselineHash = (Get-FileHash -LiteralPath $baseline -Algorithm SHA256).Hash.ToLower()
  $baselineExpected = $BaselineDigest.ToLower() -replace '^sha256:', ''
  Note 'baseline' ([ordered]@{
      url = $baselineUrl
      bytes = (Get-Item $baseline).Length
      sha256 = $baselineHash
      expected = $baselineExpected
      match = ($baselineHash -eq $baselineExpected)
    })
  if ($baselineHash -ne $baselineExpected) { throw 'baseline digest mismatch' }

  $zip = Join-Path $work 'candidate.zip'
  $dl = Start-Process -FilePath 'gh' -ArgumentList @('api', "repos/$Repo/actions/artifacts/$CandidateArtifactId/zip") -RedirectStandardOutput $zip -RedirectStandardError (Join-Path $evidence 'download.err') -NoNewWindow -Wait -PassThru
  if ($dl.ExitCode -ne 0) { throw "candidate download failed exit=$($dl.ExitCode)" }
  $zipHash = (Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash.ToLower()
  $wanted = $CandidateDigest.ToLower() -replace '^sha256:', ''
  Note 'candidate' ([ordered]@{ zip_sha256 = $zipHash; expected = $wanted; match = ($zipHash -eq $wanted); bytes = (Get-Item $zip).Length })
  if ($zipHash -ne $wanted) { throw 'candidate digest mismatch' }
  $bundle = Join-Path $work 'bundle'
  Expand-Archive -LiteralPath $zip -DestinationPath $bundle -Force
  $manifest = Get-Content (Join-Path $bundle 'manifest.json') -Raw | ConvertFrom-Json
  $provenance = Get-Content (Join-Path $bundle 'provenance.json') -Raw | ConvertFrom-Json
  $candidate = Join-Path $bundle 'yijing-workbench-3.3.3-x64-setup.exe'
  Note 'candidate_metadata' ([ordered]@{
      version = $manifest.version
      source_sha = $manifest.source_sha
      source_sha_match = ($manifest.source_sha -eq $CandidateSha)
      run_id = $provenance.run_id
      run_id_match = ($provenance.run_id -eq $CandidateRunId)
      workflow_sha = $provenance.workflow_sha
      signing_mode = $provenance.signing_mode
      installer_sha256 = (Get-FileHash $candidate -Algorithm SHA256).Hash.ToLower()
      manifest_installer_sha256 = $manifest.installer.sha256.ToLower()
    })
  if ($manifest.version -ne '3.3.3' -or $manifest.source_sha -ne $CandidateSha -or $provenance.source_sha -ne $CandidateSha -or $provenance.workflow_sha -ne $CandidateSha -or $provenance.run_id -ne $CandidateRunId -or $provenance.run_attempt -ne '1' -or $provenance.signing_mode -ne 'ephemeral_candidate') { throw 'candidate identity mismatch' }
  $candidateHash = (Get-FileHash $candidate -Algorithm SHA256).Hash.ToLower()
  if ($candidateHash -ne $manifest.installer.sha256.ToLower() -or (Get-Item $candidate).Length -ne [int64]$manifest.installer.bytes) { throw 'candidate installer bytes do not match manifest' }

  # 2) Install the published v3.3.1 baseline into an isolated directory.
  $dir = 'C:\qa\yijing-upgrade'
  if (Test-Path $dir) { Remove-Item -LiteralPath $dir -Recurse -Force }
  $install331 = Start-Process -FilePath $baseline -ArgumentList @('/S', "/D=$dir") -Wait -PassThru
  $exe = Join-Path $dir 'yijing-workbench.exe'
  $sidecarPath = Join-Path $dir 'binaries\yijing-backend\yijing-backend.exe'
  Note 'install_331' ([ordered]@{
      exit_code = $install331.ExitCode
      main_exists = (Test-Path $exe)
      sidecar_exists = (Test-Path $sidecarPath)
      file_version = if (Test-Path $exe) { (Get-Item $exe).VersionInfo.FileVersion } else { $null }
    })
  if ($install331.ExitCode -ne 0 -or -not (Test-Path $exe) -or -not (Test-Path $sidecarPath)) { throw 'baseline installation failed' }
  if ((Get-Item $exe).VersionInfo.FileVersion -ne '3.3.1') { throw 'baseline version is not 3.3.1' }

  # 3) Launch v3.3.1 and seed synthetic history, preference and fake DPAPI key.
  $env:WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS = '--remote-debugging-port=9223'
  $app = Start-Process -FilePath $exe -PassThru
  $root = Wait-AppRoot 75
  Note 'launch_331' ([ordered]@{ pid = $app.Id; uia_ready = [bool]$root })
  if (-not $root) { throw 'v3.3.1 UI not ready' }
  $question = 'QA-RUNNER-UPGRADE：v3.3.1 写入，v3.3.3 必须保留。'
  $cast331 = $false
  $pref331 = $false
  $key331 = $false
  $tz331 = $null
  try {
    Invoke-El (Find-Button $root '起卦')
    Start-Sleep -Seconds 2
    $edit = $root.FindFirst([System.Windows.Automation.TreeScope]::Descendants,
      (New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::AutomationIdProperty, 'question')))
    if (-not $edit) { throw 'question input missing' }
    $edit.GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern).SetValue($question)
    Start-Sleep -Milliseconds 500
    Invoke-El (Find-ButtonLike $root '开始起卦*')
    $cast331 = Wait-Text $root '原文与说明|起卦完成' 30

    Invoke-El (Find-Button $root '设置')
    Start-Sleep -Seconds 2
    $tzEdit = $root.FindFirst([System.Windows.Automation.TreeScope]::Descendants,
      (New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::AutomationIdProperty, 'default-timezone')))
    if ($tzEdit) {
      $tzEdit.GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern).SetValue('Asia/Tokyo')
      Start-Sleep -Milliseconds 500
      Invoke-El (Find-Button $root '保存默认偏好')
      $pref331 = Wait-Text $root '应用偏好已保存' 15
      $tz331 = $tzEdit.GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern).Current.Value
    }

    $ai = Find-ButtonLike $root 'AI 辅助*'
    if ($ai) {
      $ec = $ai.GetCurrentPattern([System.Windows.Automation.ExpandCollapsePattern]::Pattern)
      if ($ec.Current.ExpandCollapseState -ne [System.Windows.Automation.ExpandCollapseState]::Expanded) { $ec.Expand(); Start-Sleep -Seconds 1 }
    }
    $keyEdit = $root.FindFirst([System.Windows.Automation.TreeScope]::Descendants,
      (New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::AutomationIdProperty, 'deepseek-key')))
    if ($keyEdit) {
      $fake = $env:QA_EXPECTED_DPAPI_KEY
      try {
        $keyEdit.GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern).SetValue($fake)
      } catch {
        $keyEdit.SetFocus()
        Start-Sleep -Milliseconds 300
        Add-Type -AssemblyName System.Windows.Forms
        [System.Windows.Forms.SendKeys]::SendWait($fake)
      }
      Start-Sleep -Milliseconds 400
      Invoke-El (Find-Button $root '保存密钥')
      Start-Sleep -Seconds 2
      $consent = Find-Button $root '知悉并继续'
      if ($consent) { Invoke-El $consent; Start-Sleep -Seconds 5 }
      $key331 = Wait-Text $root '密钥已配置' 30
    }
  } catch {
    Note 'seed_error' ([ordered]@{ message = $_.Exception.Message; stack = $_.ScriptStackTrace })
  }
  Note 'seed_331' ([ordered]@{ cast = $cast331; preference = $pref331; key_configured = $key331 })
  if (-not $cast331 -or -not $pref331 -or -not $key331) { throw 'v3.3.1 synthetic data seeding was incomplete' }
  & python .github/qa/db_snapshot.py upgrade-pre-331
  if ($LASTEXITCODE -ne 0) { throw 'pre-upgrade database snapshot failed' }
  $preDb = Get-Content (Join-Path $evidence 'upgrade-pre-331.json') -Raw | ConvertFrom-Json
  if ($preDb.integrity -ne 'ok') { throw 'v3.3.1 database integrity check failed' }
  if ($preDb.questions -notcontains $question) { throw 'v3.3.1 synthetic history row missing' }
  if (-not $preDb.key_row_present -or -not $preDb.key_decrypt_ok -or -not $preDb.key_matches_expected) { throw 'v3.3.1 DPAPI key round-trip failed' }
  $close331 = Close-App $app
  Note 'close_331' $close331
  if (-not $close331.graceful -or $close331.forced -or $close331.sidecar_orphan) { throw 'v3.3.1 app/sidecar did not shut down cleanly' }

  # 4) Overwrite upgrade to the official 3.3.3 candidate in the same directory.
  $install333 = Start-Process -FilePath $candidate -ArgumentList @('/S', "/D=$dir") -Wait -PassThru
  $sidecarHash = if (Test-Path $sidecarPath) { (Get-FileHash $sidecarPath -Algorithm SHA256).Hash.ToLower() } else { $null }
  Note 'install_333' ([ordered]@{
      exit_code = $install333.ExitCode
      main_exists = (Test-Path $exe)
      sidecar_exists = (Test-Path $sidecarPath)
      sidecar_sha256 = $sidecarHash
      sidecar_sha256_expected = $manifest.sidecar_sha256.ToLower()
      verifier_exists = (Test-Path (Join-Path $dir 'verify-updater-signature.exe'))
      file_version = if (Test-Path $exe) { (Get-Item $exe).VersionInfo.FileVersion } else { $null }
    })
  $installed333Version = if (Test-Path $exe) { (Get-Item $exe).VersionInfo.FileVersion } else { $null }
  if ($install333.ExitCode -ne 0 -or -not (Test-Path $exe) -or -not (Test-Path $sidecarPath) -or $sidecarHash -ne $manifest.sidecar_sha256.ToLower() -or (Test-Path (Join-Path $dir 'verify-updater-signature.exe')) -or $installed333Version -ne '3.3.3') { throw 'candidate overwrite content contract failed' }

  # 5) Launch 3.3.3 and verify history, preference, key, version.
  $env:WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS = '--remote-debugging-port=9224'
  $app2 = Start-Process -FilePath $exe -PassThru
  $root2 = Wait-AppRoot 75
  Note 'launch_333' ([ordered]@{ pid = $app2.Id; uia_ready = [bool]$root2 })
  if (-not $root2) { throw 'v3.3.3 UI not ready' }
  $historyOk = $false
  $prefKept = $false
  $keyKept = $false
  $versionOk = $false
  $tz333 = $null
  try {
    Invoke-El (Find-Button $root2 '历史记录')
    Start-Sleep -Seconds 2
    $historyText = (Get-UiaNames $root2) -join "`n"
    $historyOk = $historyText -match [regex]::Escape($question)

    Invoke-El (Find-Button $root2 '设置')
    Start-Sleep -Seconds 2
    $tz2 = $root2.FindFirst([System.Windows.Automation.TreeScope]::Descendants,
      (New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::AutomationIdProperty, 'default-timezone')))
    if ($tz2) { $tz333 = $tz2.GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern).Current.Value }

    $ai2 = Find-ButtonLike $root2 'AI 辅助*'
    if ($ai2) {
      $ec = $ai2.GetCurrentPattern([System.Windows.Automation.ExpandCollapsePattern]::Pattern)
      if ($ec.Current.ExpandCollapseState -ne [System.Windows.Automation.ExpandCollapseState]::Expanded) { $ec.Expand(); Start-Sleep -Seconds 1 }
    }
    $settingsText = (Get-UiaNames $root2) -join "`n"
    $keyKept = $settingsText -match '密钥已配置'

    $about = Find-ButtonLike $root2 '关于应用*'
    if ($about) {
      $ec = $about.GetCurrentPattern([System.Windows.Automation.ExpandCollapsePattern]::Pattern)
      if ($ec.Current.ExpandCollapseState -ne [System.Windows.Automation.ExpandCollapseState]::Expanded) { $ec.Expand(); Start-Sleep -Seconds 1 }
    }
    $aboutText = (Get-UiaNames $root2) -join "`n"
    $versionOk = $aboutText -match 'V3\.3\.3'
    Set-Content -LiteralPath (Join-Path $evidence 'uia-333-settings.txt') -Value $aboutText -Encoding utf8
    Set-Content -LiteralPath (Join-Path $evidence 'uia-333-history.txt') -Value $historyText -Encoding utf8
  } catch {
    Note 'verify_error' ([ordered]@{ message = $_.Exception.Message; stack = $_.ScriptStackTrace })
  }
  & python .github/qa/db_snapshot.py upgrade-post-333
  if ($LASTEXITCODE -ne 0) { throw 'post-upgrade database snapshot failed' }
  $postDb = Get-Content (Join-Path $evidence 'upgrade-post-333.json') -Raw | ConvertFrom-Json
  $prefKept = (($tz333 -eq 'Asia/Tokyo') -and ($preDb.app_preferences -eq $postDb.app_preferences))
  Note 'verify_333' ([ordered]@{
      history_preserved = $historyOk
      preference_preserved = $prefKept
      preference_value_331 = $tz331
      preference_value_333 = $tz333
      preference_db_331 = $preDb.app_preferences
      preference_db_333 = $postDb.app_preferences
      key_preserved_in_ui = $keyKept
      key_decrypt_ok_before = $preDb.key_decrypt_ok
      key_decrypt_ok_after = $postDb.key_decrypt_ok
      key_matches_expected_after = $postDb.key_matches_expected
      database_integrity_before = $preDb.integrity
      database_integrity_after = $postDb.integrity
      divinations_before = $preDb.counts.divinations
      divinations_after = $postDb.counts.divinations
      version_3_3_3 = $versionOk
    })
  if ($postDb.integrity -ne 'ok' -or -not $postDb.key_row_present -or -not $postDb.key_decrypt_ok -or -not $postDb.key_matches_expected) { throw 'post-upgrade database integrity or DPAPI round-trip failed' }
  if ($postDb.questions -notcontains $question -or $preDb.counts.divinations -ne $postDb.counts.divinations) { throw 'post-upgrade history data was not preserved' }
  if (-not $historyOk -or -not $prefKept -or -not $keyKept -or -not $versionOk) { throw 'post-upgrade UI data-preservation checks failed' }
  $close333 = Close-App $app2
  Note 'close_333' $close333
  if (-not $close333.graceful -or $close333.forced -or $close333.sidecar_orphan) { throw 'v3.3.3 app/sidecar did not shut down cleanly' }

  # 6) Uninstall and verify cleanup.
  $uninstaller = Join-Path $dir 'uninstall.exe'
  $u = $null
  if (Test-Path $uninstaller) { $u = Start-Process -FilePath $uninstaller -ArgumentList '/S' -Wait -PassThru }
  Start-Sleep -Seconds 6
  $shortcutRoots = @(
    (Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs'),
    (Join-Path $env:ProgramData 'Microsoft\Windows\Start Menu\Programs')
  )
  $shortcutsAfter = @($shortcutRoots | Where-Object { Test-Path $_ } | ForEach-Object {
      Get-ChildItem -LiteralPath $_ -Recurse -Filter *.lnk -ErrorAction SilentlyContinue | Where-Object { $_.Name -match '易经|Yijing' }
    })
  Note 'uninstall' ([ordered]@{
      exit_code = if ($u) { $u.ExitCode } else { $null }
      main_removed = -not (Test-Path $exe)
      sidecar_removed = -not (Test-Path $sidecarPath)
      shortcut_removed = ($shortcutsAfter.Count -eq 0)
    })
  if (-not $u -or $u.ExitCode -ne 0 -or (Test-Path $exe) -or (Test-Path $sidecarPath) -or $shortcutsAfter.Count -ne 0) { throw 'QA uninstall cleanup failed' }
}
catch {
  Note 'fatal' ([ordered]@{ message = $_.Exception.Message; stack = $_.ScriptStackTrace })
  Save-Result
  throw
}
finally {
  Save-Result
  $result | ConvertTo-Json -Depth 8
}
