param(
  [ValidateSet('codex','claude','gemini','copilot','all')]
  [string]$Agent,
  [string]$Repo = 'BookHsu/Libro.AgentWCAG.clean',
  [string]$Ref = 'master',
  [string]$ArchivePath,
  [string]$Dest,
  [switch]$Force,
  [switch]$KeepDownloaded
)

$sourceRevisionEnvVar = 'LIBRO_AGENTWCAG_SOURCE_REVISION'

function Select-AgentInteractive {
  $choices = @('codex', 'claude', 'gemini', 'copilot', 'all')
  while ($true) {
    $value = Read-Host 'Select agent (codex/claude/gemini/copilot/all)'
    if ($choices -contains $value) {
      return $value
    }
    Write-Host 'Unsupported agent. Try again.'
  }
}

function Resolve-SourceRevision {
  param(
    [string]$Repo,
    [string]$Ref
  )
  $explicitRevision = [string]([Environment]::GetEnvironmentVariable($sourceRevisionEnvVar) ?? '')
  if ($explicitRevision) {
    return $explicitRevision
  }
  if ($Ref -match '^[0-9a-fA-F]{40}$') {
    return $Ref.ToLowerInvariant()
  }
  $apiUrl = "https://api.github.com/repos/$Repo/commits/$([uri]::EscapeDataString($Ref))"
  $payload = Invoke-RestMethod -Uri $apiUrl -Headers @{ 'User-Agent' = 'Libro.AgentWCAG bootstrap' }
  $sha = [string]$payload.sha
  if ($sha -match '^[0-9a-fA-F]{40}$') {
    return $sha.ToLowerInvariant()
  }
  throw 'unable to resolve source revision for repository archive'
}

$resolvedAgent = if ($Agent) { $Agent } else { Select-AgentInteractive }
$stageDir = Join-Path ([System.IO.Path]::GetTempPath()) ("libro-agentwcag-bootstrap-" + [guid]::NewGuid().ToString("N"))
[System.IO.Directory]::CreateDirectory($stageDir) | Out-Null

try {
  $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
  if (-not $pythonCommand) {
    throw 'python runtime is unavailable; install Python 3.12+ and ensure it is in PATH'
  }

  $pythonVersionText = & python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
  if ($LASTEXITCODE -ne 0) {
    throw "python version detection failed with code $LASTEXITCODE"
  }
  $pythonVersion = [version]($pythonVersionText.Trim())
  if ($pythonVersion -lt [version]'3.12') {
    throw "python 3.12+ is required; detected $($pythonVersion.ToString())"
  }

  $downloadedArchivePath = Join-Path $stageDir 'repo.zip'
  if ($ArchivePath) {
    $resolvedArchivePath = Resolve-Path -LiteralPath $ArchivePath -ErrorAction Stop
    $sourceArchivePath = $resolvedArchivePath.Path
  } else {
    $archiveUrl = "https://github.com/$Repo/archive/$Ref.zip"
    Invoke-WebRequest -Uri $archiveUrl -OutFile $downloadedArchivePath -UseBasicParsing | Out-Null
    $sourceArchivePath = $downloadedArchivePath
  }

  $extractDir = Join-Path $stageDir 'extract'
  Expand-Archive -Path $sourceArchivePath -DestinationPath $extractDir -Force
  $repoRoot = Get-ChildItem -Path $extractDir -Directory | Select-Object -First 1
  if (-not $repoRoot) {
    throw 'downloaded archive did not contain a repository root'
  }

  $env:LIBRO_AGENTWCAG_SOURCE_REVISION = Resolve-SourceRevision -Repo $Repo -Ref $Ref
  $arguments = @(
    (Join-Path $repoRoot.FullName 'scripts/install-agent.py'),
    '--agent', $resolvedAgent
  )
  if ($Dest) { $arguments += @('--dest', $Dest) }
  if ($Force) { $arguments += '--force' }

  & python @arguments
  if ($LASTEXITCODE -ne 0) {
    throw "install-agent.py exited with code $LASTEXITCODE"
  }

  $doctorArguments = @(
    (Join-Path $repoRoot.FullName 'scripts/doctor-agent.py'),
    '--agent', $resolvedAgent,
    '--verify-manifest-integrity'
  )
  if ($Dest) { $doctorArguments += @('--dest', $Dest) }

  & python @doctorArguments
  if ($LASTEXITCODE -ne 0) {
    throw "doctor-agent.py exited with code $LASTEXITCODE"
  }

  Write-Host 'Bootstrap install completed and doctor verification passed.'
} catch [System.Net.WebException] {
  Write-Error 'network failure while downloading repository archive'
  exit 1
} catch [System.UnauthorizedAccessException] {
  Write-Error 'insufficient filesystem permissions while staging or installing repository archive'
  exit 1
} catch {
  Write-Error $_.Exception.Message
  exit 1
} finally {
  if (-not $KeepDownloaded) {
    Remove-Item -Recurse -Force $stageDir -ErrorAction SilentlyContinue
  }
}
