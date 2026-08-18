# PostToolUse: keep .claude/skills in sync with .agents/skills (single source).
#
# Why this exists: in a real dual-runtime project the two skill trees drifted in
# BOTH directions across 6 skills, so each runtime kept following rules the other
# had already superseded. Work built on stale rules got rejected and redone.
#
# Canonical source is .agents/skills. Anything edited there is mirrored to
# .claude/skills. Two exceptions are deliberate and must survive the mirror:
#   1. PER_TREE substitutions -- each tree names its own executor.
#   2. EXCLUDED skills -- the two copies play different roles on purpose.
# ASCII-only on purpose: PowerShell 5.1 reads BOM-less .ps1 as ANSI.

$ErrorActionPreference = "Stop"

# Rules live in a UTF8 sidecar, not in this file. Windows PowerShell 5.1 reads a
# BOM-less .ps1 as ANSI, so non-ASCII literals here get mangled and the matching
# replacement silently never fires -- which is exactly how the first version of
# this hook shipped a broken rule. Keep this script ASCII-only.
$EXCLUDED = @()
$PER_TREE = @()
try {
  $rulesPath = Join-Path $PSScriptRoot "skills-sync.rules.json"
  if (Test-Path $rulesPath) {
    $rules = (Get-Content -Raw -Encoding UTF8 $rulesPath) | ConvertFrom-Json
    if ($rules.excluded) { $EXCLUDED = @($rules.excluded) }
    if ($rules.perTree)  { $PER_TREE = @($rules.perTree | ForEach-Object { @{ From = $_.from; To = $_.to } }) }
  }
} catch { exit 0 }

function Emit($message) {
  @{ systemMessage = $message } | ConvertTo-Json -Depth 3 -Compress
  exit 0
}

try {
  $stdin   = [Console]::In.ReadToEnd()
  $payload = $stdin | ConvertFrom-Json
} catch { exit 0 }

if ($payload.tool_name -notin @("Write", "Edit", "MultiEdit")) { exit 0 }

$path = $payload.tool_input.file_path
if (-not $path) { exit 0 }

$root = $env:CLAUDE_PROJECT_DIR
if (-not $root) { exit 0 }
$norm = $path -replace '\\', '/'

# Editing the mirror directly is the drift we are trying to prevent.
if ($norm -match '/\.claude/skills/([^/]+)/') {
  $name = $Matches[1]
  if ($name -notin $EXCLUDED) {
    Emit ("[skills-sync] .claude/skills/$name is a mirror. Edit .agents/skills/$name instead, " +
          "or this change will be overwritten on the next sync.")
  }
  exit 0
}

if ($norm -notmatch '/\.agents/skills/([^/]+)/') { exit 0 }
$name = $Matches[1]
if ($name -in $EXCLUDED) { exit 0 }

$src = Join-Path $root ".agents/skills/$name"
$dst = Join-Path $root ".claude/skills/$name"
if (-not (Test-Path $src)) { exit 0 }
if (-not (Test-Path $dst)) { exit 0 }   # skill not published to Claude Code; leave alone

try {
  $copied = 0
  Get-ChildItem -Path $src -Recurse -File | ForEach-Object {
    $rel    = $_.FullName.Substring($src.Length).TrimStart('\', '/')
    $target = Join-Path $dst $rel
    $dir    = Split-Path $target -Parent
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }

    if ($_.Extension -in @(".md", ".json", ".txt", ".yaml", ".yml")) {
      $text = Get-Content -Raw -Encoding UTF8 $_.FullName
      foreach ($rule in $PER_TREE) { $text = $text.Replace($rule.From, $rule.To) }
      $existing = if (Test-Path $target) { Get-Content -Raw -Encoding UTF8 $target } else { $null }
      if ($existing -ne $text) {
        # UTF8 without BOM. Set-Content -Encoding UTF8 emits a BOM on Windows
        # PowerShell 5.1, which shows up as a phantom first-line diff forever.
        $noBom = New-Object System.Text.UTF8Encoding($false)
        [System.IO.File]::WriteAllText($target, $text, $noBom)
        $copied++
      }
    } else {
      Copy-Item -Path $_.FullName -Destination $target -Force
      $copied++
    }
  }
  if ($copied -gt 0) {
    Emit "[skills-sync] $name : .agents -> .claude ($copied file(s) mirrored)"
  }
} catch {
  # Fail open. A sync failure must never block the user's edit.
  exit 0
}
exit 0
