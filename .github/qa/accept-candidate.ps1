param(
  [Parameter(Mandatory = $true)][string]$ArtifactId,
  [Parameter(Mandatory = $true)][string]$ExpectedDigest,
  [Parameter(Mandatory = $true)][string]$ExpectedSha,
  [Parameter(Mandatory = $true)][string]$ExpectedRunId,
  [string]$Repo = $env:GITHUB_REPOSITORY
)

$ErrorActionPreference = 'Stop'
$work = Join-Path $env:RUNNER_TEMP 'qa-candidate'
$evidence = Join-Path $work 'evidence'
New-Item -ItemType Directory -Force -Path $work, $evidence | Out-Null

$result = [ordered]@{
  started_at = (Get-Date).ToString('o')
  artifact_id = $ArtifactId
  expected_digest = $ExpectedDigest
  expected_source_sha = $ExpectedSha
  expected_run_id = $ExpectedRunId
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
  $result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $evidence 'result.json') -Encoding utf8
}
function Note([string]$name, $value) {
  $result.steps[$name] = $value
  Save-Result
}

try {
  # 1) Download by exact artifact ID and verify digest.
  $zip = Join-Path $work 'artifact.zip'
  $dl = Start-Process -FilePath 'gh' -ArgumentList @('api', "repos/$Repo/actions/artifacts/$ArtifactId/zip") -RedirectStandardOutput $zip -RedirectStandardError (Join-Path $evidence 'download.err') -NoNewWindow -Wait -PassThru
  if ($dl.ExitCode -ne 0) { throw "artifact download failed exit=$($dl.ExitCode)" }
  $zipHash = (Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash.ToLower()
  $wanted = $ExpectedDigest.ToLower() -replace '^sha256:', ''
  Note 'artifact' ([ordered]@{ zip_sha256 = $zipHash; expected = $wanted; match = ($zipHash -eq $wanted); bytes = (Get-Item $zip).Length })
  if ($zipHash -ne $wanted) { throw 'artifact digest mismatch' }

  # 2) Extract and verify manifest / provenance identity.
  $bundle = Join-Path $work 'bundle'
  Expand-Archive -LiteralPath $zip -DestinationPath $bundle -Force
  $manifest = Get-Content (Join-Path $bundle 'manifest.json') -Raw | ConvertFrom-Json
  $provenance = Get-Content (Join-Path $bundle 'provenance.json') -Raw | ConvertFrom-Json
  $installer = Join-Path $bundle 'yijing-workbench-3.3.3-x64-setup.exe'
  $installerHash = (Get-FileHash -LiteralPath $installer -Algorithm SHA256).Hash.ToLower()
  $meta = [ordered]@{
    version = $manifest.version
    tag = $manifest.tag
    source_sha = $manifest.source_sha
    source_ref = $manifest.source_ref
    source_trigger = $manifest.source_trigger
    installer_bytes = (Get-Item $installer).Length
    installer_sha256 = $installerHash
    manifest_installer_sha256 = $manifest.installer.sha256.ToLower()
    sidecar_sha256_manifest = $manifest.sidecar_sha256.ToLower()
    signing_mode = $provenance.signing_mode
    provenance_run_id = $provenance.run_id
    provenance_run_attempt = $provenance.run_attempt
    provenance_workflow_sha = $provenance.workflow_sha
    provenance_workflow_ref = $provenance.workflow_ref
    pubkey_key_id = $manifest.updater_pubkey_key_id
    signature_key_id = $manifest.signature_key_id
    source_sha_match = ($manifest.source_sha -eq $ExpectedSha)
    provenance_run_match = ($provenance.run_id -eq $ExpectedRunId)
    workflow_sha_match = ($provenance.workflow_sha -eq $ExpectedSha)
    installer_sha_match = ($installerHash -eq $manifest.installer.sha256.ToLower())
  }
  Note 'metadata' $meta
  if (-not $meta.source_sha_match) { throw 'manifest source_sha mismatch' }
  if (-not $meta.provenance_run_match) { throw 'provenance run_id mismatch' }
  if (-not $meta.workflow_sha_match) { throw 'provenance workflow_sha mismatch' }
  if (-not $meta.installer_sha_match) { throw 'installer sha mismatch' }

  # 3) Attestation identity and subjects (non-fatal: local verification is authoritative).
  $attOut = Join-Path $evidence 'attestation.json'
  & gh attestation verify $installer --repo $Repo `
      --cert-identity "https://github.com/$Repo/.github/workflows/windows-rc.yml@refs/heads/main" `
      --cert-oidc-issuer https://token.actions.githubusercontent.com `
      --source-digest $ExpectedSha --source-ref refs/heads/main --signer-digest $ExpectedSha `
      --format json > $attOut 2> (Join-Path $evidence 'attestation.err')
  $attOk = ($LASTEXITCODE -eq 0)
  $subjects = @()
  if ($attOk) {
    $att = Get-Content $attOut -Raw | ConvertFrom-Json
    $subjects = @($att[0].verificationResult.statement.subject | ForEach-Object { $_.name })
  }
  Note 'attestation' ([ordered]@{ passed = $attOk; subjects = $subjects; error = (Get-Content (Join-Path $evidence 'attestation.err') -Raw -ErrorAction SilentlyContinue) })

  # 4) Static NSIS content inspection (read-only, 7-Zip).
  $seven = (Get-Command 7z -ErrorAction SilentlyContinue).Source
  if (-not $seven) { $seven = 'C:\Program Files\7-Zip\7z.exe' }
  $listing = & $seven l -slt $installer | Out-String
  $paths = @($listing -split "`n" | Where-Object { $_ -like 'Path = *' } | ForEach-Object { ($_ -replace '^Path = ', '').Trim().Replace('\', '/') })
  $main = $paths -contains 'yijing-workbench.exe'
  $sidecarEntry = $paths -contains 'binaries/yijing-backend/yijing-backend.exe'
  $verifier = @($paths | Where-Object { $_ -like '*verify-updater-signature.exe' }).Count -gt 0
  Note 'nsis' ([ordered]@{ entries = $paths.Count; main_exe = $main; sidecar = $sidecarEntry; verifier_present = $verifier })
  if (-not $main -or -not $sidecarEntry -or $verifier) { throw 'NSIS content contract failed' }

  # 5) Silent currentUser install into an isolated directory.
  $installDir = 'C:\qa\yijing-official'
  if (Test-Path $installDir) { Remove-Item -LiteralPath $installDir -Recurse -Force }
  $install = Start-Process -FilePath $installer -ArgumentList @('/S', "/D=$installDir") -Wait -PassThru
  $exe = Join-Path $installDir 'yijing-workbench.exe'
  $installedSidecar = Join-Path $installDir 'binaries\yijing-backend\yijing-backend.exe'
  $shortcutRoots = @(
    (Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs'),
    (Join-Path $env:ProgramData 'Microsoft\Windows\Start Menu\Programs')
  )
  $shortcuts = @($shortcutRoots | Where-Object { Test-Path $_ } | ForEach-Object {
      Get-ChildItem -LiteralPath $_ -Recurse -Filter *.lnk -ErrorAction SilentlyContinue | Where-Object { $_.Name -match '易经|Yijing' }
    })
  $uninstallKeys = @(Get-ChildItem 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall' -ErrorAction SilentlyContinue | ForEach-Object {
      $rp = Get-ItemProperty $_.PSPath -ErrorAction SilentlyContinue
      if ($rp.DisplayName -match '易经|Yijing') { [ordered]@{ key = $_.PSChildName; display = $rp.DisplayName; version = $rp.DisplayVersion; location = $rp.InstallLocation } }
    })
  $version = if (Test-Path $exe) { (Get-Item $exe).VersionInfo.FileVersion } else { $null }
  Note 'install' ([ordered]@{
      exit_code = $install.ExitCode
      dir = $installDir
      main_exists = (Test-Path $exe)
      sidecar_exists = (Test-Path $installedSidecar)
      verifier_exists = (Test-Path (Join-Path $installDir 'verify-updater-signature.exe'))
      file_version = $version
      sidecar_sha256 = if (Test-Path $installedSidecar) { (Get-FileHash $installedSidecar -Algorithm SHA256).Hash.ToLower() } else { $null }
      shortcuts = @($shortcuts | ForEach-Object { $_.FullName })
      uninstall_entries = $uninstallKeys
    })
  if ($install.ExitCode -ne 0 -or -not (Test-Path $exe)) { throw 'installation failed' }

  # 6) Launch and observe process, WebView2 CDP, sidecar, data dir, backend health.
  $env:WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS = '--remote-debugging-port=9222'
  $app = Start-Process -FilePath $exe -PassThru
  $cdp = $null
  $deadline = (Get-Date).AddSeconds(75)
  while ((Get-Date) -lt $deadline) {
    Start-Sleep -Milliseconds 700
    try {
      $cdp = Invoke-RestMethod -Uri 'http://127.0.0.1:9222/json/version' -TimeoutSec 2
      break
    } catch {}
  }
  $targets = @()
  $pageReady = $false
  $pageDeadline = (Get-Date).AddSeconds(45)
  while ($cdp -and (Get-Date) -lt $pageDeadline) {
    try {
      $targets = @(Invoke-RestMethod -Uri 'http://127.0.0.1:9222/json/list' -TimeoutSec 5 | ForEach-Object { [ordered]@{ type = $_.type; title = $_.title; url = $_.url } })
      if (@($targets | Where-Object { $_.type -eq 'page' -and $_.url -ne 'about:blank' -and $_.title }).Count -gt 0) { $pageReady = $true; break }
    } catch {}
    Start-Sleep -Milliseconds 800
  }
  Start-Sleep -Seconds 3
  $sidecar = Get-Process yijing-backend -ErrorAction SilentlyContinue | Select-Object -First 1
  $dataDir = Join-Path $env:LOCALAPPDATA 'cn.yijing.workbench'
  $dataFiles = @()
  if (Test-Path $dataDir) { $dataFiles = @(Get-ChildItem -LiteralPath $dataDir -Recurse -Depth 2 -Force -ErrorAction SilentlyContinue | Select-Object -First 40 | ForEach-Object { $_.FullName }) }
  $dbFiles = @()
  if (Test-Path $dataDir) { $dbFiles = @(Get-ChildItem -LiteralPath $dataDir -Filter *.sqlite3 -Force -ErrorAction SilentlyContinue | ForEach-Object { $_.FullName }) }
  $logPath = Join-Path $dataDir 'yijing-backend.log'
  $logTail = @()
  if (Test-Path $logPath) { $logTail = @(Get-Content -LiteralPath $logPath -Tail 40 -ErrorAction SilentlyContinue) }
  $sidecarPort = $null
  $healthStatus = $null
  if (Test-Path $logPath) {
    $logText = Get-Content -LiteralPath $logPath -Raw -ErrorAction SilentlyContinue
    $m = [regex]::Match([string]$logText, 'Uvicorn running on http://127\.0\.0\.1:(\d+)')
    if ($m.Success) { $sidecarPort = [int]$m.Groups[1].Value }
  }
  if ($sidecarPort) {
    try {
      $health = Invoke-WebRequest -Uri "http://127.0.0.1:$sidecarPort/api/desktop/health" -TimeoutSec 5 -SkipHttpErrorCheck
      $healthStatus = $health.StatusCode
    } catch { $healthStatus = 'error' }
  }
  Note 'launch' ([ordered]@{
      pid = $app.Id
      app_alive = [bool](Get-Process -Id $app.Id -ErrorAction SilentlyContinue)
      cdp_up = [bool]$cdp
      page_ready = $pageReady
      webview2 = if ($cdp) { $cdp.Browser } else { $null }
      targets = $targets
      sidecar_pid = if ($sidecar) { $sidecar.Id } else { $null }
      sidecar_port = $sidecarPort
      health_unauthenticated_status = $healthStatus
      data_dir_exists = (Test-Path $dataDir)
      db_files = $dbFiles
      data_files = $dataFiles
      log_tail = $logTail
    })

  # 7) Real UI test through Windows UI Automation (interactive runner session).
  $uia = [ordered]@{ available = $false; window_name = $null; text_lines = @(); nav_ok = $false; cast_ok = $false; result_excerpt = $null; error = $null }
  try {
    Add-Type -AssemblyName UIAutomationClient
    Add-Type -AssemblyName UIAutomationTypes
    function Get-UiaNames($root) {
      $all = $root.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.Condition]::TrueCondition)
      $names = @()
      for ($i = 0; $i -lt [Math]::Min($all.Count, 200); $i++) {
        $n = $all.Item($i).Current.Name
        if ($n) { $names += $n }
      }
      return $names
    }
    function Find-UiaButton($root, [string]$name) {
      $buttons = $root.FindAll([System.Windows.Automation.TreeScope]::Descendants,
        (New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty, [System.Windows.Automation.ControlType]::Button)))
      foreach ($b in $buttons) { if ($b.Current.Name -eq $name) { return $b } }
      return $null
    }
    $uiaDeadline = (Get-Date).AddSeconds(45)
    $root = $null
    while ((Get-Date) -lt $uiaDeadline) {
      $proc = Get-Process yijing-workbench -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
      if ($proc) {
        try {
          $candidate = [System.Windows.Automation.AutomationElement]::FromHandle($proc.MainWindowHandle)
          if ($candidate) {
            $names = @(Get-UiaNames $candidate)
            if ($names.Count -gt 5) { $root = $candidate; $uia.text_lines = $names; break }
          }
        } catch {}
      }
      Start-Sleep -Milliseconds 800
    }
    if ($root) {
      $uia.available = $true
      $uia.window_name = $root.Current.Name
      $navButton = Find-UiaButton $root '起卦'
      if ($navButton) {
        $navButton.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()
        $uia.nav_ok = $true
        Start-Sleep -Seconds 2
      }
      $edit = $root.FindFirst([System.Windows.Automation.TreeScope]::Descendants,
        (New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::AutomationIdProperty, 'question')))
      if ($edit) {
        $edit.GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern).SetValue('QA-RUNNER 隔离验收：起卦后历史记录必须正常。')
        Start-Sleep -Milliseconds 500
        $buttons = $root.FindAll([System.Windows.Automation.TreeScope]::Descendants,
          (New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty, [System.Windows.Automation.ControlType]::Button)))
        $startButton = $null
        foreach ($b in $buttons) { if ($b.Current.Name -like '开始起卦*') { $startButton = $b; break } }
        if ($startButton) {
          $startButton.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()
          $castDeadline = (Get-Date).AddSeconds(30)
          while ((Get-Date) -lt $castDeadline) {
            Start-Sleep -Milliseconds 800
            $text = (Get-UiaNames $root) -join "`n"
            if ($text -match '原文与说明|本卦|卦象') { $uia.cast_ok = $true; break }
          }
          $uia.text_lines = @(Get-UiaNames $root)
          $uia.result_excerpt = (@(Get-UiaNames $root) | Where-Object { $_ -match '乾|卦|原文|说明|QA-RUNNER' } | Select-Object -First 30)
        }
      }
    }
  } catch {
    $uia.error = $_.Exception.Message
  }
  Note 'uia' $uia
  $uia | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $evidence 'uia.json') -Encoding utf8

  # 8) Graceful shutdown, then observe sidecar cleanup.
  $appAliveBefore = [bool](Get-Process -Id $app.Id -ErrorAction SilentlyContinue)
  $gracefulExit = $false
  $forcedKill = $false
  if ($appAliveBefore) {
    try { $null = $app.CloseMainWindow() } catch {}
    $closeDeadline = (Get-Date).AddSeconds(20)
    while ((Get-Date) -lt $closeDeadline) {
      if (-not (Get-Process -Id $app.Id -ErrorAction SilentlyContinue)) { $gracefulExit = $true; break }
      Start-Sleep -Milliseconds 500
    }
    if (-not $gracefulExit) {
      Stop-Process -Id $app.Id -Force -ErrorAction SilentlyContinue
      $forcedKill = $true
    }
  }
  Start-Sleep -Seconds 6
  $sidecarAfter = @(Get-Process yijing-backend -ErrorAction SilentlyContinue)
  $sidecarOrphan = $sidecarAfter.Count -gt 0
  Note 'shutdown' ([ordered]@{
      app_alive_before = $appAliveBefore
      graceful_exit = $gracefulExit
      forced_kill = $forcedKill
      app_alive_after = [bool](Get-Process -Id $app.Id -ErrorAction SilentlyContinue)
      sidecar_alive_after = $sidecarOrphan
      sidecar_pids_after = @($sidecarAfter | ForEach-Object { $_.Id })
      sidecar_orphan = $sidecarOrphan
    })
  if ($sidecarOrphan) {
    $sidecarAfter | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 3
  }

  # 9) Silent uninstall (after the QA process has been cleaned up).
  $uninstaller = Join-Path $installDir 'uninstall.exe'
  $u = $null
  if (Test-Path $uninstaller) { $u = Start-Process -FilePath $uninstaller -ArgumentList '/S' -Wait -PassThru }
  Start-Sleep -Seconds 6
  $shortcutsAfter = @($shortcutRoots | Where-Object { Test-Path $_ } | ForEach-Object {
      Get-ChildItem -LiteralPath $_ -Recurse -Filter *.lnk -ErrorAction SilentlyContinue | Where-Object { $_.Name -match '易经|Yijing' }
    })
  Note 'uninstall' ([ordered]@{
      exit_code = if ($u) { $u.ExitCode } else { $null }
      main_removed = -not (Test-Path $exe)
      sidecar_removed = -not (Test-Path $installedSidecar)
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
