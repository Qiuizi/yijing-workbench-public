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
  if ($manifest.source_sha -ne $CandidateSha -or $provenance.run_id -ne $CandidateRunId) { throw 'candidate identity mismatch' }

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
  if ($install331.ExitCode -ne 0 -or -not (Test-Path $exe)) { throw 'baseline installation failed' }

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
    $combo = $root.FindFirst([System.Windows.Automation.TreeScope]::Descendants,
      (New-Object System.Windows.Automation.AndCondition(
        (New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty, [System.Windows.Automation.ControlType]::ComboBox)),
        (New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::NameProperty, '默认起卦方式'))
      )))
    if ($combo) {
      $current = Get-ComboText $combo
      if ($current -ne '手动输入') {
        $ec = $combo.GetCurrentPattern([System.Windows.Automation.ExpandCollapsePattern]::Pattern)
        if ($ec.Current.ExpandCollapseState -ne [System.Windows.Automation.ExpandCollapseState]::Expanded) { $ec.Expand(); Start-Sleep -Seconds 1 }
        $lists = $root.FindAll([System.Windows.Automation.TreeScope]::Descendants,
          (New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty, [System.Windows.Automation.ControlType]::List)))
        foreach ($list in $lists) {
          $opt = $list.FindFirst([System.Windows.Automation.TreeScope]::Descendants,
            (New-Object System.Windows.Automation.AndCondition(
              (New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty, [System.Windows.Automation.ControlType]::ListItem)),
              (New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::NameProperty, '手动输入'))
            )))
          if ($opt) { $opt.GetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern).Select(); Start-Sleep -Milliseconds 800; break }
        }
      }
      Invoke-El (Find-Button $root '保存默认偏好')
      $pref331 = Wait-Text $root '应用偏好已保存' 15
    }

    $ai = Find-ButtonLike $root 'AI 辅助*'
    if ($ai) {
      $ec = $ai.GetCurrentPattern([System.Windows.Automation.ExpandCollapsePattern]::Pattern)
      if ($ec.Current.ExpandCollapseState -ne [System.Windows.Automation.ExpandCollapseState]::Expanded) { $ec.Expand(); Start-Sleep -Seconds 1 }
    }
    $keyEdit = $root.FindFirst([System.Windows.Automation.TreeScope]::Descendants,
      (New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::AutomationIdProperty, 'deepseek-key')))
    if ($keyEdit) {
      $fake = 'sk-qa-runner-' + (Get-Date -Format 'yyyyMMddHHmmss') + '-not-a-real-key'
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
  & python .github/qa/db_snapshot.py upgrade-pre-331
  $close331 = Close-App $app
  Note 'close_331' $close331

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
  if ($install333.ExitCode -ne 0 -or -not (Test-Path $exe)) { throw 'candidate overwrite failed' }

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
  try {
    Invoke-El (Find-Button $root2 '历史记录')
    Start-Sleep -Seconds 2
    $historyText = (Get-UiaNames $root2) -join "`n"
    $historyOk = $historyText -match [regex]::Escape($question)

    Invoke-El (Find-Button $root2 '设置')
    Start-Sleep -Seconds 2
    $combo2 = $root2.FindFirst([System.Windows.Automation.TreeScope]::Descendants,
      (New-Object System.Windows.Automation.AndCondition(
        (New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty, [System.Windows.Automation.ControlType]::ComboBox)),
        (New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::NameProperty, '默认起卦方式'))
      )))
    if ($combo2) { $prefKept = ((Get-ComboText $combo2) -eq '手动输入') }

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
  Note 'verify_333' ([ordered]@{
      history_preserved = $historyOk
      preference_preserved = $prefKept
      key_preserved = $keyKept
      version_3_3_3 = $versionOk
    })
  & python .github/qa/db_snapshot.py upgrade-post-333
  $close333 = Close-App $app2
  Note 'close_333' $close333

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
