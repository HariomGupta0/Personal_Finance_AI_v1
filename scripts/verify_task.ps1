param(
    [string]$BaseCommit = "HEAD~1"
)

$ErrorActionPreference = "Continue"

$repoRoot = (Get-Item $PSScriptRoot).Parent.FullName
Set-Location $repoRoot

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$moneyChecksDir = Join-Path $repoRoot "..\money_checks"
if (-not (Test-Path $moneyChecksDir)) {
    New-Item -ItemType Directory -Path $moneyChecksDir -Force | Out-Null
}
$resolvedMoneyChecks = (Resolve-Path $moneyChecksDir).Path
$outFile = Join-Path $resolvedMoneyChecks "verify_$timestamp.txt"

$pythonExe = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
    $pythonExe = "python"
}

$env:PYTHONPATH = $repoRoot

"=== TASK VERIFICATION RUN [$timestamp] ===" | Out-File -FilePath $outFile -Encoding utf8
"Repository Root: $repoRoot" | Out-File -FilePath $outFile -Append -Encoding utf8
"Base Commit for Diff: $BaseCommit" | Out-File -FilePath $outFile -Append -Encoding utf8
"" | Out-File -FilePath $outFile -Append -Encoding utf8

"--- 1. RESEED DATABASE ---" | Out-File -FilePath $outFile -Append -Encoding utf8
& $pythonExe -m backend.scripts.seed_db 2>&1 | Out-File -FilePath $outFile -Append -Encoding utf8
"" | Out-File -FilePath $outFile -Append -Encoding utf8

"--- 2. FULL PYTEST SUITE ---" | Out-File -FilePath $outFile -Append -Encoding utf8
$pytestOutput = & $pythonExe -m pytest -q 2>&1
$pytestOutput | Out-File -FilePath $outFile -Append -Encoding utf8
"" | Out-File -FilePath $outFile -Append -Encoding utf8

# Extract pytest summary line (e.g. "544 passed, 13 warnings in 24.88s")
$pytestSummary = ($pytestOutput | Where-Object { $_ -match "\d+ passed" }) | Select-Object -Last 1
if (-not $pytestSummary) {
    $pytestSummary = ($pytestOutput | Select-Object -Last 2) -join " "
}

"--- 3. GIT LOG ---" | Out-File -FilePath $outFile -Append -Encoding utf8
git log --oneline -5 2>&1 | Out-File -FilePath $outFile -Append -Encoding utf8
"" | Out-File -FilePath $outFile -Append -Encoding utf8

"--- 4. PYTEST SUMMARY ---" | Out-File -FilePath $outFile -Append -Encoding utf8
$pytestSummary | Out-File -FilePath $outFile -Append -Encoding utf8
"" | Out-File -FilePath $outFile -Append -Encoding utf8

"--- 5. GIT STATUS ---" | Out-File -FilePath $outFile -Append -Encoding utf8
$rawStatus = (git status --short 2>&1)
$statusText = if ($rawStatus) { ($rawStatus | Out-String).Trim() } else { "" }
if ($statusText -eq "") {
    "CLEAN" | Out-File -FilePath $outFile -Append -Encoding utf8
} else {
    $rawStatus | Out-File -FilePath $outFile -Append -Encoding utf8
}
"" | Out-File -FilePath $outFile -Append -Encoding utf8

"--- 6. GIT DIFF STAT ---" | Out-File -FilePath $outFile -Append -Encoding utf8
git diff --stat $BaseCommit 2>&1 | Out-File -FilePath $outFile -Append -Encoding utf8
"" | Out-File -FilePath $outFile -Append -Encoding utf8

Write-Host "Output file: $outFile"
Write-Host "Pytest summary: $pytestSummary"
