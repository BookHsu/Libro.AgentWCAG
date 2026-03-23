param(
  [Parameter(Mandatory = $true)]
  [string]$ReleaseBase,
  [ValidateSet('codex','claude','gemini','copilot')]
  [string]$Agent = 'codex',
  [string]$Version,
  [string]$Dest,
  [switch]$Force,
  [switch]$KeepDownloaded
)

function Test-IsUrl {
  param([string]$Value)
  return $Value -match '^(https?|file)://'
}

function Read-ReleaseText {
  param(
    [string]$Base,
    [string]$Name
  )
  if (Test-IsUrl $Base) {
    $baseUri = $Base.TrimEnd('/') + '/'
    return (Invoke-WebRequest -Uri ($baseUri + $Name) -UseBasicParsing).Content
  }
  return Get-Content -Raw -Path (Join-Path $Base $Name)
}

function Copy-ReleaseAsset {
  param(
    [string]$Base,
    [string]$Name,
    [string]$Destination
  )
  if (Test-IsUrl $Base) {
    $baseUri = $Base.TrimEnd('/') + '/'
    Invoke-WebRequest -Uri ($baseUri + $Name) -OutFile $Destination -UseBasicParsing | Out-Null
  } else {
    Copy-Item -Path (Join-Path $Base $Name) -Destination $Destination -Force
  }
}

function Get-ChecksumMap {
  param([string]$Content)
  $map = @{}
  foreach ($line in ($Content -split "`r?`n")) {
    if ([string]::IsNullOrWhiteSpace($line)) {
      continue
    }
    $parts = $line -split ' \*', 2
    $map[$parts[1]] = $parts[0]
  }
  return $map
}

$stageDir = Join-Path ([System.IO.Path]::GetTempPath()) ("libro-agentwcag-install-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $stageDir | Out-Null

try {
  if ($Version) {
    $manifestName = "libro-agent-wcag-$Version-release-manifest.json"
  } else {
    $latest = Read-ReleaseText -Base $ReleaseBase -Name 'latest-release.json' | ConvertFrom-Json
    $manifestName = [string]$latest.release_manifest
  }

  $manifest = Read-ReleaseText -Base $ReleaseBase -Name $manifestName | ConvertFrom-Json
  $checksumName = [string]$manifest.checksum_file
  $checksums = Get-ChecksumMap -Content (Read-ReleaseText -Base $ReleaseBase -Name $checksumName)
  $bundleAsset = $manifest.assets | Where-Object { $_.kind -eq 'bundle' -and $_.agent -eq $Agent } | Select-Object -First 1
  if (-not $bundleAsset) {
    throw "Release manifest does not contain a bundle for agent: $Agent"
  }

  $bundlePath = Join-Path $stageDir ([string]$bundleAsset.filename)
  Copy-ReleaseAsset -Base $ReleaseBase -Name ([string]$bundleAsset.filename) -Destination $bundlePath

  $actualHash = (Get-FileHash -Algorithm SHA256 -Path $bundlePath).Hash.ToLowerInvariant()
  if ($checksums[[System.IO.Path]::GetFileName($bundlePath)] -ne $actualHash) {
    throw 'bundle checksum verification failed'
  }
  if ([string]$bundleAsset.sha256 -ne $actualHash) {
    throw 'bundle hash does not match release manifest'
  }

  $extractDir = Join-Path $stageDir 'extract'
  Expand-Archive -Path $bundlePath -DestinationPath $extractDir -Force
  $bundleRoot = Join-Path $extractDir ([string]$bundleAsset.bundle_root)

  $env:LIBRO_AGENTWCAG_SOURCE_REVISION = [string]$manifest.source_revision
  if ($manifest.PSObject.Properties.Name -contains 'build_timestamp') {
    $env:LIBRO_AGENTWCAG_BUILD_TIMESTAMP = [string]$manifest.build_timestamp
  }

  $arguments = @(
    (Join-Path $bundleRoot 'scripts/install-agent.py'),
    '--agent', $Agent
  )
  if ($Dest) { $arguments += @('--dest', $Dest) }
  if ($Force) { $arguments += '--force' }

  & python @arguments
  exit $LASTEXITCODE
} finally {
  if (-not $KeepDownloaded) {
    Remove-Item -Recurse -Force $stageDir -ErrorAction SilentlyContinue
  }
}
