param(
  [Parameter(Mandatory = $true, Position = 0)]
  [ValidateSet('install','doctor','remove','audit')]
  [string]$Command,

  [Parameter(Position = 1)]
  [string]$AgentOrTarget,

  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]]$ExtraArgs
)

$script = Join-Path $PSScriptRoot 'libro.py'
$arguments = @($Command)
if ($AgentOrTarget) { $arguments += $AgentOrTarget }
if ($ExtraArgs) { $arguments += $ExtraArgs }

python $script @arguments
