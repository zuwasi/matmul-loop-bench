<#  Build the benchmark. Same flags for BOTH agents (fairness).
    STD defaults to the best your compiler supports; bump to c++26 when you
    have GCC 14+/Clang 18+ for an on-camera "-std=c++26".  #>
param([string] $Std = "c++17")

$ErrorActionPreference = "Stop"
$dir = $PSScriptRoot
$args = @("-std=$Std", "-O3", "-march=native", "-funroll-loops",
          "$dir\bench.cpp", "-o", "$dir\bench.exe")
& g++ @args
if ($LASTEXITCODE -ne 0) { Write-Host "BUILD FAILED" -ForegroundColor Red; exit 1 }
Write-Host "build ok (-std=$Std -O3 -march=native)" -ForegroundColor Green
