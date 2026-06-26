<#
  WITH-LOOPS agent: optimize matmul against a measured, gated benchmark.

      build -> run bench -> correct? & faster? --keep--> next iter
         ^                       |
         |  wrong / slower / won't build: REVERT to best
         +----------- Amp edits solution.hpp <-----------+

  The loop owns three things the human/one-shot does not automate:
    * correctness gate  (rejects any wrong answer -> never ships a regression)
    * "better" gate     (keeps an edit only if GFLOP/s improves)
    * next prompt        (built from the measured result)

  Output: results/loop.csv  (iter,gflops,correct,ms) for the trajectory chart.

  Agent-agnostic: works with Amp or Claude Code (-Agent amp | claude).

  Usage:  ./optimize_loop.ps1 -Iterations 6 -N 512 -Agent amp
#>
param([int] $Iterations = 6, [int] $N = 512, [string] $Std = "c++17",
      [ValidateSet("amp","claude")] [string] $Agent = "amp")

$ErrorActionPreference = "Stop"
$dir   = $PSScriptRoot
$csv   = Join-Path $dir "results\loop.csv"
$best  = Join-Path $dir "results\best_solution.hpp"
"iter,gflops,correct,ms" | Set-Content $csv

# Only agent-specific line in the whole demo: the headless invocation.
function Invoke-Agent([string] $p) {
    if ($Agent -eq "claude") { & claude -p $p --dangerously-skip-permissions | Out-Host }
    else                     { & amp   -x $p --dangerously-allow-all       | Out-Host }
}

function Invoke-Bench {
    & powershell -ExecutionPolicy Bypass -File "$dir\build.ps1" -Std $Std *> $null
    if ($LASTEXITCODE -ne 0) { return $null }                    # won't build
    $line = & "$dir\bench.exe" $N
    if ($line -match "correct=(\d+) gflops=([\d.]+) ms=([\d.]+)") {
        return @{ correct = [int]$Matches[1]; gflops = [double]$Matches[2]; ms = [double]$Matches[3] }
    }
    return $null
}

# Baseline (the naive shipped solution).
$r = Invoke-Bench
$bestGflops = if ($r -and $r.correct -eq 1) { $r.gflops } else { 0 }
Copy-Item "$dir\solution.hpp" $best -Force
"0,$bestGflops,1,$($r.ms)" | Add-Content $csv
Write-Host "[loop] baseline: $bestGflops GFLOP/s" -ForegroundColor Cyan

for ($i = 1; $i -le $Iterations; $i++) {
    Write-Host "`n[loop] iteration $i/$Iterations (best so far: $bestGflops GFLOP/s)" -ForegroundColor Cyan
    $snapshot = Get-Content "$dir\solution.hpp" -Raw

    $prompt = @"
You are optimizing C = A*B in solution.hpp. Current best is $bestGflops GFLOP/s
at N=$N (double, row-major). Make it FASTER while keeping it correct.
Edit ONLY solution.hpp. Keep the function signature. Standard headers only, no
external libraries. Try one concrete optimization (cache blocking, loop order,
restrict/alignment, register blocking, SIMD-friendly inner loop), then stop.
"@
    Invoke-Agent $prompt

    $r = Invoke-Bench
    if (-not $r)            { Write-Host "  -> won't build; reverting." -ForegroundColor Yellow; Set-Content "$dir\solution.hpp" $snapshot -NoNewline; continue }
    if ($r.correct -ne 1)  { Write-Host "  -> WRONG result; reverting." -ForegroundColor Yellow; "$i,$($r.gflops),0,$($r.ms)" | Add-Content $csv; Set-Content "$dir\solution.hpp" $snapshot -NoNewline; continue }

    if ($r.gflops -gt $bestGflops) {
        Write-Host "  -> accepted: $($r.gflops) GFLOP/s (was $bestGflops)" -ForegroundColor Green
        $bestGflops = $r.gflops
        Copy-Item "$dir\solution.hpp" $best -Force
    } else {
        Write-Host "  -> slower ($($r.gflops)); reverting to best." -ForegroundColor Yellow
        Set-Content "$dir\solution.hpp" $snapshot -NoNewline
    }
    "$i,$($r.gflops),1,$($r.ms)" | Add-Content $csv
}

Copy-Item $best "$dir\solution.hpp" -Force
Write-Host "`n[loop] FINAL best: $bestGflops GFLOP/s  (see results\loop.csv)" -ForegroundColor Green
