"""
Render the video end-card: loop trajectory vs one-shot dot.

Reads results/loop.csv (iter,gflops,correct,ms) and, if present,
results/oneshot.csv (gflops,correct,ms,built). Writes results/benchmark.png
and results/benchmark.svg.

Usage:
    python chart.py                       # uses results/loop.csv + oneshot.csv
    python chart.py results/sample_loop_run.csv
"""
import csv
import pathlib
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = pathlib.Path(__file__).parent
RES = HERE / "results"


def read_loop(path: pathlib.Path):
    iters, gflops, correct = [], [], []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            iters.append(int(row["iter"]))
            gflops.append(float(row["gflops"]))
            correct.append(int(row["correct"]))
    return iters, gflops, correct


def read_oneshot(path: pathlib.Path):
    if not path.exists():
        return None
    with open(path, newline="") as f:
        row = next(csv.DictReader(f), None)
    if not row:
        return None
    return float(row["gflops"]), int(row["correct"]), int(row.get("built", 1))


def main() -> int:
    loop_csv = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else RES / "loop.csv"
    if not loop_csv.exists():
        print(f"no loop csv at {loop_csv}; run optimize_loop.ps1 first", file=sys.stderr)
        return 1

    iters, gflops, correct = read_loop(loop_csv)
    one = read_oneshot(RES / "oneshot.csv")

    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(11, 6.2), dpi=160)

    # Loop trajectory (climbing curve).
    ax.plot(iters, gflops, "-o", color="#00d9ff", linewidth=2.6,
            markersize=9, label="Loop (gated, keeps best)", zorder=3)
    for x, y, ok in zip(iters, gflops, correct):
        if not ok:
            ax.plot(x, y, "x", color="#fbbf24", markersize=13, zorder=4)
    ax.annotate(f"{gflops[-1]:.1f}", (iters[-1], gflops[-1]),
                textcoords="offset points", xytext=(8, 8),
                color="#00d9ff", fontsize=14, fontweight="bold")

    # One-shot single dot.
    title_extra = ""
    if one is not None:
        og, ok, built = one
        if built == 0:
            title_extra = "  ·  one-shot did NOT build"
        else:
            label = "One-shot" + ("" if ok else "  (WRONG result!)")
            ax.axhline(og, color="#7c5cff", linestyle="--", linewidth=1.4, alpha=.6)
            ax.plot([0], [og], "s", color="#7c5cff", markersize=12,
                    label=label, zorder=3)
            if gflops[-1] > 0 and og > 0:
                title_extra = f"  ·  loop {gflops[-1] / og:.1f}x faster"

    base = gflops[0] if gflops else 1
    if base > 0 and gflops[-1] > 0:
        ax.set_title(f"matmul: loop vs one-shot  —  {gflops[-1] / base:.1f}x over baseline{title_extra}",
                     fontsize=16, fontweight="bold", pad=14)
    ax.set_xlabel("loop iteration", fontsize=13)
    ax.set_ylabel("throughput (GFLOP/s)  — higher is better", fontsize=13)
    ax.grid(True, alpha=.18)
    ax.legend(fontsize=12, loc="upper left")
    ax.set_xticks(iters)
    fig.tight_layout()

    png, svg = RES / "benchmark.png", RES / "benchmark.svg"
    fig.savefig(png)
    fig.savefig(svg)
    print(f"wrote {png}")
    print(f"wrote {svg}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
