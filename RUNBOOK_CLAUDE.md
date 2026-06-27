# RUNBOOK (Claude Code) — run the loop-vs-one-shot demo with Claude

Step-by-step instructions tuned for **Claude Code**. For Amp, see
[RUNBOOK_AMP.md](./RUNBOOK_AMP.md).

## 0. Prerequisites (once)

- C++ compiler on PATH: `g++` (MinGW/GCC), `clang++`, or MSVC `cl`.
  Verify: `g++ --version`
- Python 3 + matplotlib (for the chart): `pip install matplotlib`
- Claude Code CLI installed and logged in:
  ```powershell
  claude --version   # confirm it's installed
  claude             # run once interactively to authenticate, if needed
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

## 3. Run the two Claude windows side by side

Two terminals, same size/machine, same `-N` and `-Std`.

**Left terminal — one-shot (no loop):**
```powershell
git checkout -- solution.hpp
./run_oneshot.ps1 -N 512 -Agent claude
```

**Right terminal — the loop:**
```powershell
git checkout -- solution.hpp
./optimize_loop.ps1 -Iterations 6 -N 512 -Agent claude
```

Start both at the same moment. The loop prints its best GFLOP/s each iteration;
the one-shot prints a single final line.

## 3b. Watch the agent in real time

By default `claude -p` only prints the final message per step. To see tool
calls and edits as they happen, pick either:

- **Live in the terminal** — add `-Stream` to either script:
  ```powershell
  ./optimize_loop.ps1 -N 512 -Agent claude -Stream
  ```
  It runs `claude -p … --output-format stream-json --verbose` and pipes it
  through `stream_fmt.py`, printing each `-> tool` call, `[ok]` result, and
  `== done`.
- **Watch the file change** — in a third pane:
  ```powershell
  Get-Content solution.hpp -Wait -Tail 40
  ```

(Claude has no public live thread viewer like `amp top`; use `-Stream` or the
file watcher.)

## 4. Render the end-card chart

```powershell
python chart.py
```
Writes `results/benchmark.png` and `.svg` — loop curve + one-shot dot + speedup.

## 5. (Optional) the strongest shot: catch a wrong answer

Run the one-shot a few times. If Claude ever ships `correct=0`, keep that take:
the loop's correctness gate would have rejected and reverted it — a quality win,
not just speed.

## Claude Code commands used here (reference)

| Purpose | Command |
|---|---|
| Headless / print mode (used by the scripts) | `claude -p "<prompt>"` |
| Skip permission checks (unattended) | `--dangerously-skip-permissions` |
| Keep context across steps | `claude --continue -p "<prompt>"` |
| Structured output (optional) | `claude -p "<prompt>" --output-format stream-json` |
| Check version | `claude --version` |

The scripts call: `claude -p "<prompt>" --dangerously-skip-permissions`. Use the
skip-permission flag only on code you trust — it lets Claude act without asking.

> Note: `--dangerously-skip-permissions` is refused when running as root/sudo on
> some setups. Run as a normal user, or use `--permission-mode bypassPermissions`.

## Result files

| File | Meaning |
|---|---|
| `results/loop.csv` | iter, gflops, correct, ms — the loop trajectory |
| `results/oneshot.csv` | gflops, correct, ms, built — the one-shot result |
| `results/benchmark.png` / `.svg` | the chart |
