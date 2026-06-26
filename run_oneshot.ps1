<#
  WITHOUT-LOOPS agent (baseline): a single prompt, one build, one measurement.
  Same task, same flags, same model as the loop -- the ONLY difference is method.
  No correctness gate, no retry, no "keep best": whatever it produces is the
  final answer (even if wrong or slower).

  Output: results/oneshot.csv

  Agent-agnostic: works with Amp or Claude Code (-Agent amp | claude).

  Usage:  ./run_oneshot.ps1 -N 512 -Agent amp
#>
param([int] $N = 512, [string] $Std = "c++17",
      [ValidateSet("amp","claude")] [string] $Agent = "amp")

$ErrorActionPreference = "Stop"
$dir = $PSScriptRoot
$csv = Join-Path $dir "results\oneshot.csv"
"gflops,correct,ms,built" | Set-Content $csv

function Invoke-Agent([string] $p) {
    if ($Agent -eq "claude") { & claude -p $p --dangerously-skip-permissions | Out-Host }
    else                     { & amp   -x $p --dangerously-allow-all       | Out-Host }
}

$prompt = @"
Optimize the matrix multiply in solution.hpp (C = A*B, double, row-major, N x N)
to run as fast as possible at N=$N. It MUST stay numerically correct. Edit only
solution.hpp, keep the function signature, standard headers only, no external
libraries. This is your one and only attempt -- do your best in a single pass.
"@
Invoke-Agent $prompt

& powershell -ExecutionPolicy Bypass -File "$dir\build.ps1" -Std $Std *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "[oneshot] DID NOT BUILD" -ForegroundColor Red
    "0,0,0,0" | Set-Content $csv
    exit 0
}
$line = & "$dir\bench.exe" $N
Write-Host "[oneshot] $line"
if ($line -match "correct=(\d+) gflops=([\d.]+) ms=([\d.]+)") {
    "$($Matches[2]),$($Matches[1]),$($Matches[3]),1" | Set-Content $csv
}
