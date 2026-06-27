# RUNBOOK (Amp) — run the loop-vs-one-shot demo with Amp

Step-by-step instructions tuned for **Amp**. For Claude Code, see
[RUNBOOK_CLAUDE.md](./RUNBOOK_CLAUDE.md).

## 0. Prerequisites (once)

- C++ compiler on PATH: `g++` (MinGW/GCC), `clang++`, or MSVC `cl`.
  Verify: `g++ --version`
- Python 3 + matplotlib (for the chart): `pip install matplotlib`
- Amp CLI installed and logged in:
  ```powershell
  amp --version      # confirm it's installed
  amp login          # if not already authenticated
  ```
- Clone and enter the repo:
  ```powershell
  git clone https://github.com/zuwasi/matmul-loop-bench.git
  cd matmul-loop-bench
  ```

## 1. Sanity-check the harness (no agent yet)

```powershell
./build.ps1                 # compiles bench.cpp + the naive solution.hpp
./bench.exe 512             # expect: RESULT correct=1 gflops=~1-3 ms=~100-300 n=512
```
A low GFLOP/s number is correct — that's the naive baseline both runs start from.

## 2. Reset to the naive baseline before EVERY recorded run

```powershell
git checkout -- solution.hpp
```

## 3. Run the two Amp windows side by side

Two terminals, same size/machine, same `-N` and `-Std`.

**Left terminal — one-shot (no loop):**
```powershell
git checkout -- solution.hpp
./run_oneshot.ps1 -N 512 -Agent amp
```

**Right terminal — the loop:**
```powershell
git checkout -- solution.hpp
./optimize_loop.ps1 -Iterations 6 -N 512 -Agent amp
```

Start both at the same moment. The loop prints its best GFLOP/s each iteration;
the one-shot prints a single final line.

## 4. Render the end-card chart

```powershell
python chart.py
```
Writes `results/benchmark.png` and `.svg` — loop curve + one-shot dot + speedup.

## 5. (Optional) the strongest shot: catch a wrong answer

Run the one-shot a few times. If Amp ever ships `correct=0`, keep that take: the
loop's correctness gate would have rejected and reverted it — a quality win, not
just speed.

## Amp commands used here (reference)

| Purpose | Command |
|---|---|
| Headless run (used by the scripts) | `amp -x "<prompt>"` |
| Skip approval prompts (unattended) | `--dangerously-allow-all` |
| Keep context across steps | `amp threads continue <id> -x "<prompt>"` |
| Check version / log in | `amp --version` · `amp login` |

The scripts call: `amp -x "<prompt>" --dangerously-allow-all`. Use the
skip-approval flag only on code you trust — it lets Amp act without asking.

## Result files

| File | Meaning |
|---|---|
| `results/loop.csv` | iter, gflops, correct, ms — the loop trajectory |
| `results/oneshot.csv` | gflops, correct, ms, built — the one-shot result |
| `results/benchmark.png` / `.svg` | the chart |
