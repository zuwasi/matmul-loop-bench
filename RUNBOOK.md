# RUNBOOK — run the loop-vs-one-shot demo step by step

## 0. Prerequisites (once)

- A C++ compiler on PATH: `g++` (MinGW/GCC), `clang++`, or MSVC `cl`.
  Verify: `g++ --version`
- Python 3 with matplotlib (for the chart): `pip install matplotlib`
- An agent CLI, logged in — **either** works:
  - Amp: `amp --version`
  - Claude Code: `claude --version`
- Clone the repo and open a terminal in it:
  ```powershell
  git clone https://github.com/zuwasi/matmul-loop-bench.git
  cd matmul-loop-bench
  ```

## 1. Sanity-check the harness (no agent yet)

```powershell
./build.ps1                 # compiles bench.cpp + the naive solution.hpp
./bench.exe 512             # expect: RESULT correct=1 gflops=~1 ms=~250 n=512
```
You should see a low GFLOP/s number — that's the naive baseline both agents start from.

## 2. Reset to the naive baseline before every recorded run

```powershell
git checkout -- solution.hpp
```
This guarantees both windows start identical. **Do this before each run.**

## 3. Run the two agents side by side

Open two terminals, same size, same machine. Use the **same** `-N` and `-Std`
in both. Pick your agent with `-Agent amp` or `-Agent claude` (default `amp`).

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

Start them at the same moment for the video. The loop prints its best GFLOP/s
each iteration; the one-shot prints a single final line.

## 4. Render the end-card chart

```powershell
python chart.py
```
Writes `results/benchmark.png` and `.svg`: the loop's climbing curve plus the
one-shot dot, titled with the speedup factor. Use it as the closing frame.

## 5. (Optional) the strongest shot: catch a wrong answer

Run the one-shot a few times. If it ever ships `correct=0` (a subtly wrong
matmul), keep that recording: the loop's correctness gate would have rejected it
and reverted. That demonstrates a quality advantage, not just speed.

## Result files

| File | Meaning |
|---|---|
| `results/loop.csv` | iter, gflops, correct, ms — the loop trajectory |
| `results/oneshot.csv` | gflops, correct, ms, built — the single one-shot result |
| `results/benchmark.png` / `.svg` | the chart |

---

## Amp-only, or does it work on Claude too?

**It works on both.** Everything except one line is agent-agnostic — the
benchmark, the correctness gate, the build, the chart, and the loop logic are
plain PowerShell + C++ + Python. The only agent-specific part is the headless
invocation, which the scripts switch on `-Agent`:

| | Amp | Claude Code |
|---|---|---|
| Headless run | `amp -x "<prompt>"` | `claude -p "<prompt>"` |
| Skip approvals | `--dangerously-allow-all` | `--dangerously-skip-permissions` |
| Keep context across steps | `amp threads continue <id> -x …` | `claude --continue -p …` |

So:
```powershell
./optimize_loop.ps1 -Agent amp       # uses  amp -x ... --dangerously-allow-all
./optimize_loop.ps1 -Agent claude    # uses  claude -p ... --dangerously-skip-permissions
```

You can even run **Amp in the left window and Claude in the right** to compare
agents under the *same* loop and gate — the benchmark is neutral, so it's a fair
head-to-head. Use only on code you trust; the skip-permission flags let the agent
act without prompting.
