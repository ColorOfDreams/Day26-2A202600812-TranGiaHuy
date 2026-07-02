$ErrorActionPreference = "Stop"

$ProjectDir = Split-Path -Parent $PSScriptRoot
$Python = (Get-Command python).Source
$Server = Join-Path $PSScriptRoot "mcp_server.py"
$Cache = Join-Path $ProjectDir ".npm-cache"

New-Item -ItemType Directory -Force $Cache | Out-Null
$env:NPM_CONFIG_CACHE = $Cache
npx -y @modelcontextprotocol/inspector $Python $Server
