param(
  [Parameter(Mandatory = $true)]
  [ValidateSet('codex','claude','gemini','copilot','all')]
  [string]$Agent,
  [string]$Dest,
  [switch]$Force
)

$script = Join-Path $PSScriptRoot 'install-agent.py'
$arguments = @('--agent', $Agent)
if ($Dest) { $arguments += @('--dest', $Dest) }
if ($Force) { $arguments += '--force' }

python $script @arguments
