# ===================================================================================
#
# STEP 4: STATISTICAL TREND ANALYSIS
#
# This script executes the longitudinal statistical tests and generates visualizations.
#
# Actions:
# 1. Aggregates the fully analyzed dataset by year (Mean/Median/Std Dev).
# 2. Applies Mann-Kendall Trend Tests to detect statistically significant temporal shifts.
# 3. Computes Sen’s Slope to quantify the rate of change (e.g., BPM increase per year).
# 4. Calculates Pearson and Spearman correlations between Year and Acoustic Features.
# 5. Generates publication-ready visualizations:
#    - Boxplots (Distribution over time)
#    - Regression Plots (Long-term trends)
#    - Correlation Heatmaps
#
# Citation:
# @misc{lau_2026_yd6ys-m6e87,
#   author       = {Lau, kaikwan},
#   title        = {{Are Vocaloid Songs Getting denser? A Longitudinal
#                    Audio Analysis of 1,900 Hatsune Miku Songs (2007--
#                    2025)}},
#   month        = mar,
#   year         = 2026,
#   publisher    = {Knowledge Commons},
#   doi          = {10.17613/yd6ys-m6e87},
#   url          = {https://doi.org/10.17613/yd6ys-m6e87}
# }
#
# ===================================================================================

import os
import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats

warnings.filterwarnings("ignore")
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.size": 10,
    "figure.dpi": 150,
    "savefig.dpi": 200,
    "savefig.bbox": "tight",
})

INPUT_EXCEL = "miku_fully_analyzed.xlsx"
OUTPUT_STATS = "miku_trend_statistics.xlsx"
CHART_DIR = "charts"

SPEED_METRICS = {
    "BPM":                  "Tempo (BPM)",
    "Onset_Density":        "Note Density (onsets/sec)",
    "Duration (Seconds)":   "Song Duration (sec)",
    "Spectral_Flux_Mean":   "Spectral Flux",
    "Spectral_Centroid_Hz": "Brightness (Hz)",
    "RMS_Energy":           "Loudness (RMS)",
    "Harmonic_Change_Rate": "Chord Change Speed",
    "Tempo_Stability":      "Tempo Stability",
    "Rhythm_Complexity":    "Rhythm Complexity",
    "Zero_Crossing_Rate":   "Waveform Oscillation",
    "Dynamic_Range_dB":     "Dynamic Range (dB)",
    "Avg_Note_Duration_s":  "Avg Note Duration (s)",
}

ERAS = {
    "Early\n(2007–11)": (2007, 2011),
    "Golden\n(2012–16)": (2012, 2016),
    "Stream\n(2017–20)": (2017, 2020),
    "Short Video\n(2021–25)": (2021, 2025),
}


def mann_kendall(x):
    n = len(x)
    if n < 4:
        return "insufficient", 1.0, 0.0
    s = sum(np.sign(x[j] - x[i]) for i in range(n - 1) for j in range(i + 1, n))
    var_s = n * (n - 1) * (2 * n + 5) / 18
    z = (s - np.sign(s)) / np.sqrt(var_s) if var_s > 0 else 0
    p = 2 * (1 - stats.norm.cdf(abs(z)))
    tau = s / (n * (n - 1) / 2)
    trend = ("increasing" if s > 0 else "decreasing") if p < 0.05 else "no trend"
    return trend, round(p, 6), round(tau, 4)


def sens_slope(x, y):
    slopes = [(y[j] - y[i]) / (x[j] - x[i])
              for i in range(len(x)) for j in range(i + 1, len(x)) if x[j] != x[i]]
    if not slopes:
        return 0, np.median(y)
    med = np.median(slopes)
    return round(med, 6), round(np.median(y) - med * np.median(x), 4)


def yearly_stats(df, metric):
    g = df.groupby("Year")[metric].agg(["mean", "median", "std", "count",
        lambda x: x.quantile(0.25), lambda x: x.quantile(0.75)]).reset_index()
    g.columns = ["Year", "Mean", "Median", "Std", "N", "Q25", "Q75"]
    return g

COLORS = {"main": "#2563eb", "trend": "#ef4444", "fill": "#2563eb", "bg": "#fafafa"}


def plot_trend(df, metric, label, ax):
    ys = yearly_stats(df, metric).dropna(subset=["Mean"])
    if len(ys) < 3:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        ax.set_title(label)
        return

    x, m = ys["Year"].values, ys["Mean"].values
    ax.plot(x, m, "o-", color=COLORS["main"], lw=2, ms=4, zorder=3)
    ax.fill_between(x, ys["Q25"].values, ys["Q75"].values, alpha=0.15, color=COLORS["fill"])

    sl, ic = sens_slope(x.astype(float), m)
    ax.plot(x, sl * x + ic, "--", color=COLORS["trend"], lw=1.5, zorder=4)

    trend, p, tau = mann_kendall(m)
    sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "ns"
    ax.set_title(f"{label}\nMK: {trend} (p={p:.3f}{sig}, τ={tau:.2f})", fontsize=9, fontweight="bold")
    ax.set_xlabel("Year", fontsize=8)
    ax.grid(True, alpha=0.2)
    ax.tick_params(labelsize=7)


def plot_violin(df, metric, label, ax):
    tmp = df[[metric, "Year"]].dropna()
    if len(tmp) < 10:
        return
    era_order = []
    for name, (s, e) in ERAS.items():
        mask = (tmp["Year"] >= s) & (tmp["Year"] <= e)
        tmp.loc[mask, "Era"] = name
        era_order.append(name)
    tmp = tmp.dropna(subset=["Era"])
    if len(tmp) < 10:
        return
    sns.violinplot(data=tmp, x="Era", y=metric, order=era_order, ax=ax,
                   palette="coolwarm", inner="quartile", cut=0, linewidth=0.7, scale="width")
    ax.set_title(label, fontsize=9, fontweight="bold")
    ax.set_xlabel("")
    ax.tick_params(labelsize=7)
    ax.grid(True, alpha=0.2, axis="y")

def main():
    print("=" * 70)
    print("  STEP 4: Trend Analysis & Visualization")
    print("=" * 70)

    if not os.path.exists(INPUT_EXCEL):
        print(f"\n[ERROR] {INPUT_EXCEL} not found. Run step3 first.")
        return

    df = pd.read_excel(INPUT_EXCEL)
    print(f"\n[INFO] Loaded {len(df)} songs")
    os.makedirs(CHART_DIR, exist_ok=True)

    available = {m: l for m, l in SPEED_METRICS.items()
                 if m in df.columns and pd.to_numeric(df[m], errors="coerce").notna().sum() > 20}
    print(f"[INFO] Metrics with data: {len(available)}")

    if not available:
        print("[ERROR] No metrics have data. Check step3 output.")
        return

    print("\n[1/4] Computing trend statistics...")
    records = []
    for metric, label in available.items():
        ys = yearly_stats(df, metric).dropna(subset=["Mean"])
        if len(ys) < 4:
            continue
        x = ys["Year"].values.astype(float)
        m = ys["Mean"].values
        mk_trend, mk_p, mk_tau = mann_kendall(m)
        sl, _ = sens_slope(x, m)
        pr, pp = stats.pearsonr(x, m)
        sr, sp = stats.spearmanr(x, m)
        pct = ((m[-1] - m[0]) / (abs(m[0]) + 1e-10)) * 100
        records.append({
            "Metric": label, "Column": metric,
            "Mean": round(df[metric].mean(), 4), "Std": round(df[metric].std(), 4),
            "MK_Trend": mk_trend, "MK_p": mk_p, "MK_Tau": mk_tau,
            "Sens_Slope/yr": sl, "Pearson_r": round(pr, 4), "Pearson_p": round(pp, 6),
            "Spearman_r": round(sr, 4), "Spearman_p": round(sp, 6),
            "First_Yr_Mean": round(m[0], 4), "Last_Yr_Mean": round(m[-1], 4),
            "Total_%_Change": round(pct, 2),
        })

    stats_df = pd.DataFrame(records)
    print(f"\n  {'Metric':<30} {'Trend':<18} {'p':>8} {'Δ%':>9}")
    print(f"  {'─'*68}")
    for _, r in stats_df.iterrows():
        sig = "***" if r["MK_p"] < 0.001 else "**" if r["MK_p"] < 0.01 else "*" if r["MK_p"] < 0.05 else ""
        print(f"  {r['Metric']:<30} {r['MK_Trend']:<18} {r['MK_p']:>8.4f} {r['Total_%_Change']:>+8.1f}% {sig}")

    print("\n[2/4] Generating trend charts...")
    n = len(available)
    nc = 3
    nr = (n + nc - 1) // nc
    fig, axes = plt.subplots(nr, nc, figsize=(16, 4.5 * nr))
    axes = axes.flatten() if nr > 1 else [axes] if nc == 1 else axes.flatten()
    for i, (m, l) in enumerate(available.items()):
        plot_trend(df, m, l, axes[i])
    for j in range(i + 1, len(axes)):
        axes[j].set_visible(False)
    fig.suptitle("Miku Song Speed Metrics: Yearly Trends (2007–2025)",
                 fontsize=14, fontweight="bold", y=1.01)
    plt.tight_layout()
    fig.savefig(os.path.join(CHART_DIR, "01_trends.png"))
    plt.close()
    print("  ✓ 01_trends.png")

    print("[3/4] Generating era comparisons...")
    fig, axes = plt.subplots(nr, nc, figsize=(16, 4.5 * nr))
    axes = axes.flatten() if nr > 1 else [axes] if nc == 1 else axes.flatten()
    for i, (m, l) in enumerate(available.items()):
        plot_violin(df, m, l, axes[i])
    for j in range(i + 1, len(axes)):
        axes[j].set_visible(False)
    fig.suptitle("Speed Metric Distributions by Era", fontsize=14, fontweight="bold", y=1.01)
    plt.tight_layout()
    fig.savefig(os.path.join(CHART_DIR, "02_era_violins.png"))
    plt.close()
    print("  ✓ 02_era_violins.png")

    print("[4/4] Generating heatmap & overlay...")

    valid = [m for m in available if df[m].notna().sum() > 20]
    if len(valid) >= 2:
        fig, ax = plt.subplots(figsize=(12, 10))
        corr = df[valid].corr(method="spearman")
        labels = [SPEED_METRICS.get(m, m).split("(")[0].strip() for m in valid]
        sns.heatmap(corr, annot=True, fmt=".2f", cmap="RdBu_r", center=0,
                    xticklabels=labels, yticklabels=labels, ax=ax,
                    vmin=-1, vmax=1, linewidths=0.3, annot_kws={"size": 7})
        ax.set_title("Spearman Correlations Between Speed Metrics", fontweight="bold")
        ax.tick_params(labelsize=7)
        plt.tight_layout()
        fig.savefig(os.path.join(CHART_DIR, "03_correlation.png"))
        plt.close()
        print("  ✓ 03_correlation.png")

    fig, ax = plt.subplots(figsize=(14, 7))
    cmap = plt.cm.tab10(np.linspace(0, 1, min(len(available), 10)))
    for i, (m, l) in enumerate(available.items()):
        ys = yearly_stats(df, m).dropna(subset=["Mean"])
        if len(ys) < 3:
            continue
        v = ys["Mean"].values
        z = (v - v.mean()) / (v.std() + 1e-10)
        ax.plot(ys["Year"].values, z, "o-", label=l.split("(")[0].strip(),
                color=cmap[i % len(cmap)], lw=1.5, ms=3)
    ax.set_title("All Metrics Normalized (Z-score) Over Time", fontsize=13, fontweight="bold")
    ax.set_xlabel("Year")
    ax.set_ylabel("Z-score")
    ax.legend(fontsize=7, loc="center left", bbox_to_anchor=(1, 0.5))
    ax.grid(True, alpha=0.2)
    ax.axhline(0, color="gray", lw=0.5)
    plt.tight_layout()
    fig.savefig(os.path.join(CHART_DIR, "04_normalized.png"))
    plt.close()
    print("  ✓ 04_normalized.png")

    heat = []
    hlabels = []
    for m, l in available.items():
        ys = yearly_stats(df, m).dropna(subset=["Mean"])
        if len(ys) < 3:
            continue
        v = ys.set_index("Year")["Mean"]
        z = (v - v.mean()) / (v.std() + 1e-10)
        heat.append(z)
        hlabels.append(l.split("(")[0].strip())
    if heat:
        fig, ax = plt.subplots(figsize=(16, 8))
        hdf = pd.DataFrame(heat, index=hlabels)
        sns.heatmap(hdf, annot=True, fmt=".1f", cmap="RdYlBu_r", center=0,
                    ax=ax, linewidths=0.3, annot_kws={"size": 7})
        ax.set_title("Speed Metrics by Year (Z-score)", fontsize=13, fontweight="bold")
        plt.tight_layout()
        fig.savefig(os.path.join(CHART_DIR, "05_heatmap.png"))
        plt.close()
        print("  ✓ 05_heatmap.png")

    with pd.ExcelWriter(OUTPUT_STATS, engine="openpyxl") as w:
        stats_df.to_excel(w, sheet_name="Trend_Tests", index=False)
        for m in available:
            ys = yearly_stats(df, m)
            ys.to_excel(w, sheet_name=m[:31], index=False)

    print(f"\n{'═' * 70}")
    print(f"  STEP 4 COMPLETE — ALL ANALYSIS DONE!")
    print(f"{'═' * 70}")
    print(f"  Charts:     {CHART_DIR}/")
    print(f"  Statistics: {OUTPUT_STATS}")

    sig = stats_df[stats_df["MK_p"] < 0.05]
    if len(sig) > 0:
        print(f"\n  🔬 SIGNIFICANT TRENDS (p < 0.05):")
        for _, r in sig.iterrows():
            d = "↑ FASTER" if r["Total_%_Change"] > 0 else "↓ SLOWER"
            if r["Column"] in ("Duration (Seconds)", "Avg_Note_Duration_s", "Dynamic_Range_dB"):
                d = "↓ SHORTER" if r["Total_%_Change"] < 0 else "↑ LONGER"
            print(f"    {d} {r['Metric']}: {r['Total_%_Change']:+.1f}% (p={r['MK_p']:.4f})")
    else:
        print(f"\n  No significant trends at p < 0.05")

    print(f"\n{'═' * 70}\n")


if __name__ == "__main__":
    main()
