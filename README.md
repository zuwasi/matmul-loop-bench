# matmul-loop-bench — a *definite* benchmark: loop vs. one-shot

A side-by-side demo that proves "write loops, not prompts" produces a
**measurably better program**, not just a faster workflow.

Both agents get the **same task, same model, same machine, same compiler flags,
same starting code**. The only variable is method:

| | `run_oneshot.ps1` (no loop) | `optimize_loop.ps1` (loop) |
|---|---|---|
| Attempts | 1 | N, gated |
| Correctness | un-checked | enforced every iteration |
| Keeps regressions? | yes (whatever it emits) | never — reverts if wrong/slower |
| Proof artifact | one number | a climbing GFLOP/s trajectory |

## The task

Optimize a double-precision matrix multiply `C = A*B` in
[`solution.hpp`](./solution.hpp). It ships **deliberately naive**
(cache-unfriendly inner loop). [`bench.cpp`](./bench.cpp) is the gate — agents
may not edit it. It checks the answer against an independent reference and prints:

```
RESULT correct=1 gflops=20.649 ms=13.0 maxrelerr=8.9e-10 n=512
```

## The tangible metrics (this is the point)

Speed of *development* is not the claim. The claim is the **final program is
better**, measured definitely:

1. **Throughput — GFLOP/s** at fixed `N` (headline number). `2·N³ / time`.
2. **Speedup factor** = loop_best / one-shot.
3. **Correctness** — max relative error vs. reference (< 1e-9 = pass). The loop
   *guarantees* it; the one-shot can silently ship a wrong answer.
4. **Optimization trajectory** — `results/loop.csv` (iter vs GFLOP/s) plots as a
   rising curve; the one-shot is a single dot. The most convincing video shot.

### Real recorded run (this machine, GCC 6.3, `-O3 -march=native`, N=512)

```
iter,gflops,correct,ms        <- results/sample_loop_run.csv
0,  2.284, 1, 117.5           naive baseline
1, 11.666, 1,  23.0           i-k-j reorder + __restrict   (5.1x)
2, 20.649, 1,  13.0           + register blocking (4 rows) (9.0x)
```

A hand-tuned reference reached ~12–22 GFLOP/s; a one-shot pass typically lands
at the first rung (cache reorder) and stops. Headroom remains (alignment, SIMD
intrinsics, multithreading) — the loop keeps climbing it, the one-shot doesn't.

## Run it

```powershell
# Window A (left) — baseline
./run_oneshot.ps1 -N 512

# Window B (right) — loop
./optimize_loop.ps1 -Iterations 6 -N 512
```

Then compare `results/oneshot.csv` vs `results/loop.csv`.

## Side-by-side video protocol

1. Two terminals, identical size, same machine, **same** `-Std` and `-N`.
2. Reset both to the naive `solution.hpp` (git checkout) before recording.
3. Start both at once. Left runs `run_oneshot.ps1`; right runs `optimize_loop.ps1`.
4. End card: final GFLOP/s of each + speedup factor + a line chart from
   `loop.csv`. Optionally overlay the correctness column.
5. For a stronger result, also record a run where the one-shot ships a
   subtly-wrong answer (`correct=0`) — the loop's gate would have caught it.

## Fairness notes (so the benchmark is credible)

- Same model and same prompt intent for both ("optimize, stay correct"). The
  loop is *not* given better hints — only measured feedback and a gate.
- Same flags via `build.ps1`; pin `-N` and the RNG seed (fixed in `bench.cpp`).
- Best-of-3 timing inside `bench.exe` reduces noise. Close other CPU load.

## Why C++ (and a word on "C++26")

C++ is the right *family* for this proof because the optimization surface is
enormous and measurement is precise:

- Naive vs. tuned differs **10–100×** (cache layout, blocking, SIMD, alignment,
  register reuse) — a large, unambiguous on-camera delta.
- Deterministic timing: no GC pauses or JIT warmup (unlike Java/JS) and no
  interpreter floor (unlike Python, where NumPy hides the agent's code anyway).
- `-O3 -march=native` exposes the hardware, so the agent's algorithmic choices
  actually move the number.

The **standard version barely matters to the proof** — C++17/20/23/26 all expose
the same optimization surface. Use `-std=c++26` (`build.ps1 -Std c++26`) if you
want it on screen, but that needs **GCC 14+/Clang 18+/recent MSVC**. This repo
was verified with GCC 6.3 at `-std=c++17`; bump the flag when you have a newer
compiler. (Rust would also work; C++ gives the widest, most familiar headroom.)

## Files

- `solution.hpp` — the editable target (ships naive)
- `bench.cpp` — correctness gate + timer (do not edit)
- `build.ps1` — shared build (`-O3 -march=native`, `-Std` selectable)
- `optimize_loop.ps1` — the loop (correctness + "faster" gated, keeps best)
- `run_oneshot.ps1` — the one-shot baseline
- `results/sample_loop_run.csv` — a real recorded trajectory
