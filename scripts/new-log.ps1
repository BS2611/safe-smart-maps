# Usage: scripts/new-log.ps1 "short title"   (Windows PowerShell; same result as new-log.sh)
param([string]$Title = "change")
$root = Split-Path -Parent $PSScriptRoot
$name = ""
try { $name = (git -C $root config user.name 2>$null) } catch {}
if (-not $name) { $name = $env:USERNAME }
$person = (($name.ToLower() -replace ' ','-') -replace '[^a-z0-9-]','')
if (-not $person) { $person = "unknown" }
$slug = (($Title.ToLower() -replace ' ','-') -replace '[^a-z0-9-]','')
if ($slug.Length -gt 40) { $slug = $slug.Substring(0,40) }
$ts = Get-Date -Format "yyyyMMdd-HHmmss"
$branch = "no-git"
try { $b = (git -C $root symbolic-ref --short -q HEAD 2>$null); if ($b) { $branch = $b } } catch {}
$file = Join-Path $root "docs/agent-context/log/$ts-$person-$slug.md"
$lines = Get-Content (Join-Path $root "docs/agent-context/log/_TEMPLATE.md") -Encoding UTF8
$lines[0] = "# $Title"
$text = ($lines -join "`n")
$text = $text.Replace("<YYYY-MM-DD HH:MM PT>", (Get-Date -Format "yyyy-MM-dd HH:mm"))
$text = $text.Replace("<branch> / <short hash>", "$branch / uncommitted")
Set-Content -Path $file -Value $text -Encoding UTF8
$file
"Now open it and fill in every field."
