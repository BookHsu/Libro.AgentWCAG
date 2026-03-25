param(
  [Parameter(Mandatory = $true, Position = 0)]
  [ValidateSet('install','doctor','remove')]
  [string]$Command,

  [Parameter(Mandatory = $true, Position = 1)]
  [ValidateSet('codex','claude','gemini','copilot','all')]
  [string]$Agent,

  [string]$Dest,
  [string]$WorkspaceRoot,
  [string[]]$EmitMcpConfig,
  [switch]$VerifyManifestIntegrity,
  [switch]$Force
)

$script = Join-Path $PSScriptRoot 'libro.py'
$arguments = @($Command, $Agent)
if ($Dest) { $arguments += @('--dest', $Dest) }
if ($WorkspaceRoot) { $arguments += @('--workspace-root', $WorkspaceRoot) }
if ($EmitMcpConfig) {
  foreach ($client in $EmitMcpConfig) {
    $arguments += @('--emit-mcp-config', $client)
  }
}
if ($VerifyManifestIntegrity) { $arguments += '--verify-manifest-integrity' }
if ($Force) { $arguments += '--force' }

python $script @arguments
