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
      [ValidateSet("amp","claude")] [string] $Agent = "amp",
      [switch] $Stream)

$ErrorActionPreference = "Stop"
$dir = $PSScriptRoot
$csv = Join-Path $dir "results\oneshot.csv"
"gflops,correct,ms,built" | Set-Content $csv

# -Stream shows the agent's tool calls / edits live via stream_fmt.py.
function Invoke-Agent([string] $p) {
    if ($Stream) {
        if ($Agent -eq "claude") { & claude -p $p --dangerously-skip-permissions --output-format stream-json --verbose | python -u "$dir\stream_fmt.py" }
        else                     { & amp   -x $p --dangerously-allow-all --stream-json                                 | python -u "$dir\stream_fmt.py" }
    } else {
        if ($Agent -eq "claude") { & claude -p $p --dangerously-skip-permissions | Out-Host }
        else                     { & amp   -x $p --dangerously-allow-all       | Out-Host }
    }
}

# Remember the original (naive) solution so we can leave the tree clean on exit.
$original = Get-Content "$dir\solution.hpp" -Raw

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
    Copy-Item "$dir\solution.hpp" "$dir\results\oneshot_solution.hpp" -Force
    Set-Content "$dir\solution.hpp" $original -NoNewline   # leave tree clean
    exit 0
}
$line = & "$dir\bench.exe" $N
Write-Host "[oneshot] $line"
if ($line -match "correct=(\d+) gflops=([\d.]+) ms=([\d.]+)") {
    "$($Matches[2]),$($Matches[1]),$($Matches[3]),1" | Set-Content $csv
}

# Save the one-shot's attempt, then restore the naive baseline so the tracked
# solution.hpp is never dirtied.
Copy-Item "$dir\solution.hpp" "$dir\results\oneshot_solution.hpp" -Force
Set-Content "$dir\solution.hpp" $original -NoNewline
Write-Host "[oneshot] solution.hpp left at naive baseline; attempt saved to results\oneshot_solution.hpp." -ForegroundColor DarkGray
