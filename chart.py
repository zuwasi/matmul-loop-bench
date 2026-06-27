"""
Render the video end-card: a side-by-side BAR CHART comparing the final
programs by throughput (GFLOP/s, higher = better).

Bars (whichever are available):
    Baseline (naive)  |  One-shot (no loop)  |  Loop (gated, best)

Reads results/loop.csv (iter,gflops,correct,ms) and, if present,
results/oneshot.csv (gflops,correct,ms,built). Writes results/benchmark.png
and results/benchmark.svg.

Usage:
    python chart.py                      # uses results/loop.csv + oneshot.csv
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


def read_loop(path):
    rows = []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            rows.append((int(r["iter"]), float(r["gflops"]), int(r["correct"])))
    return rows


def read_oneshot(path):
    if not path.exists():
        return None
    with open(path, newline="") as f:
        r = next(csv.DictReader(f), None)
    if not r:
        return None
    return float(r["gflops"]), int(r["correct"]), int(r.get("built", 1))


def main():
    loop_csv = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else RES / "loop.csv"
    if not loop_csv.exists():
        print(f"no loop csv at {loop_csv}; run optimize_loop.ps1 first", file=sys.stderr)
        return 1

    rows = read_loop(loop_csv)
    baseline = rows[0][1] if rows else 0.0
    correct_vals = [g for (_, g, ok) in rows if ok]
    loop_best = max(correct_vals) if correct_vals else 0.0
    one = read_oneshot(RES / "oneshot.csv")

    # Build the bar set.
    labels, values, colors, notes = [], [], [], []
    labels.append("Baseline\n(naive)"); values.append(baseline); colors.append("#6b7280"); notes.append("")

    if one is not None:
        og, ok, built = one
        if built == 0:
            labels.append("One-shot\n(no loop)"); values.append(0.0); colors.append("#7c5cff"); notes.append("did not build")
        else:
            labels.append("One-shot\n(no loop)"); values.append(og); colors.append("#7c5cff")
            notes.append("WRONG result" if not ok else "")

    labels.append("Loop\n(gated, best)"); values.append(loop_best); colors.append("#00d9ff"); notes.append("")

    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(10, 6.4), dpi=160)
    x = range(len(labels))
    bars = ax.bar(x, values, color=colors, width=0.6, zorder=3, edgecolor="#0b0f1a")

    ymax = max(values + [1]) * 1.22
    ax.set_ylim(0, ymax)
    for i, (b, v, note) in enumerate(zip(bars, values, notes)):
        spd = (v / baseline) if baseline > 0 else 0
        label = f"{v:.1f} GFLOP/s"
        if baseline > 0 and i > 0:
            label += f"\n{spd:.1f}x vs baseline"
        ax.text(b.get_x() + b.get_width() / 2, v + ymax * 0.015, label,
                ha="center", va="bottom", fontsize=12, fontweight="bold", color="#eef2ff")
        if note:
            ax.text(b.get_x() + b.get_width() / 2, v / 2 if v > 0 else ymax * 0.06,
                    note, ha="center", va="center", fontsize=11,
                    fontweight="bold", color="#fbbf24", rotation=0)

    # Headline: loop vs one-shot.
    if one is not None and one[2] == 1 and one[0] > 0 and loop_best > 0:
        title = f"Loop is {loop_best / one[0]:.1f}x faster than one-shot"
    else:
        title = "Final program throughput (higher is better)"
    ax.set_title(title, fontsize=17, fontweight="bold", pad=10)
    fig.suptitle("matmul @ N=512  ·  GFLOP/s, higher is better",
                 fontsize=11, color="#9fb0d0", y=0.965)

    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontsize=12)
    ax.set_ylabel("GFLOP/s", fontsize=13)
    ax.grid(axis="y", alpha=.18)
    ax.set_axisbelow(True)
    fig.tight_layout()

    png, svg = RES / "benchmark.png", RES / "benchmark.svg"
    fig.savefig(png)
    fig.savefig(svg)
    print(f"wrote {png}")
    print(f"wrote {svg}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
