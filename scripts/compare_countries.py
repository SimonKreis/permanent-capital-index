#!/usr/bin/env python3
"""
PCI Country-Level Benchmark Comparison

For each country with PCI constituents, generates a dark-themed chart
plotting all PCI constituents against the local benchmark index.
Two periods: 2000–2025 and 2010–2025.

Input:  data/pci_constituents_v4.csv (every row is a constituent)
Output: charts/2000-2025/{Country}_vs_{Benchmark}.png
        charts/2010-2025/{Country}_vs_{Benchmark}.png
"""

import argparse
import sys
import warnings
from pathlib import Path
from typing import Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore", category=FutureWarning)

# ── Dark theme ──────────────────────────────────────────────────────────────
plt.rcParams.update({
    "figure.facecolor": "#1a1a1a",
    "axes.facecolor": "#1a1a1a",
    "axes.edgecolor": "#444444",
    "axes.labelcolor": "#cccccc",
    "text.color": "#cccccc",
    "xtick.color": "#888888",
    "ytick.color": "#888888",
    "grid.color": "#333333",
    "legend.facecolor": "#252525",
    "legend.edgecolor": "#444444",
})

# ── Country → Benchmark mapping ─────────────────────────────────────────────
BENCHMARKS: dict[str, dict[str, str]] = {
    "Australia":     {"primary": "^AXJO", "fallback": "^AORD"},
    "Belgium":       {"primary": "^BFX", "fallback": None},
    "Brazil":        {"primary": "^BVSP", "fallback": "EWZ"},
    "Canada":        {"primary": "^GSPTSE", "fallback": "^TSX"},
    "France":        {"primary": "^FCHI", "fallback": None},
    "India":         {"primary": "^BSESN", "fallback": "^NSEI"},
    "Italy":         {"primary": "FTSEMIB.MI", "fallback": None},
    "Japan":         {"primary": "^N225", "fallback": "^TOPX"},
    "Luxembourg":    {"primary": "^MSER", "fallback": None},
    "Mexico":        {"primary": "^MXX", "fallback": None},
    "Netherlands":   {"primary": "^AEX", "fallback": None},
    "New Zealand":   {"primary": "^NZ50", "fallback": None},
    "Norway":        {"primary": "^OSEAX", "fallback": None},
    "Philippines":   {"primary": "^PSEI", "fallback": None},
    "Portugal":      {"primary": "^PSI20", "fallback": None},
    "South Africa":  {"primary": "^J203.JO", "fallback": "^JALSH"},
    "Spain":         {"primary": "^IBEX", "fallback": None},
    "Sweden":        {"primary": "^OMXS30", "fallback": None},
    "United States": {"primary": "^GSPC", "fallback": "SPY"},
    "Hong Kong":     {"primary": "^HSI", "fallback": None},
    "Bermuda":       {"primary": "^GSPC", "fallback": "SPY"},
}

COLORS = ["#3498db", "#e74c3c", "#2ecc71", "#f39c12", "#9b59b6",
          "#1abc9c", "#e67e22", "#2980b9", "#c0392b", "#27ae60"]


def load_constituents(path: str) -> pd.DataFrame:
    """Load the final constituents (all rows are constituents in v4)."""
    df = pd.read_csv(path)
    return df


def get_benchmark(country: str) -> Optional[str]:
    """Get the benchmark ticker for a country, trying primary then fallback."""
    bm = BENCHMARKS.get(country)
    if not bm:
        return None
    return bm["primary"] or bm["fallback"]


def download_series(ticker: str, start: str, end: str) -> Optional[pd.Series]:
    """Download adjusted close for a ticker, return None on failure."""
    try:
        data = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True)
        if data.empty or "Close" not in data:
            # Try fallback for benchmarks
            return None
        series = data["Close"].resample("W-FRI").last().dropna()
        if isinstance(series, pd.DataFrame):
            series = series.squeeze()
        if len(series) < 2:
            return None
        return series
    except Exception:
        return None


def compute_cagr(series: pd.Series) -> float:
    """Annualized return as percentage."""
    if isinstance(series, pd.DataFrame):
        series = series.squeeze()
    if len(series) < 2:
        return 0
    years = (series.index[-1] - series.index[0]).days / 365.25
    if years <= 0:
        return 0
    return ((series.iloc[-1] / series.iloc[0]) ** (1 / years) - 1) * 100


def generate_country_chart(
    country: str,
    benchmark_name: str,
    benchmark: pd.Series,
    pcvs: list[tuple[str, pd.Series]],
    period_label: str,
    output_path: str,
):
    """Generate a single country chart."""
    fig, ax = plt.subplots(figsize=(12, 7))

    # Benchmark line
    benchmark_norm = benchmark / benchmark.iloc[0] * 100
    bm_cagr = compute_cagr(benchmark)
    ax.plot(
        benchmark_norm.index, benchmark_norm.values,
        label=f"{benchmark_name} ({bm_cagr:.1f}%)",
        color="#ffffff", linewidth=2.5, solid_capstyle="round", alpha=0.95,
    )

    # PCV lines
    for i, (name, series) in enumerate(pcvs):
        color = COLORS[i % len(COLORS)]
        series_norm = series / series.iloc[0] * 100
        cagr = compute_cagr(series)
        ax.plot(
            series_norm.index, series_norm.values,
            label=f"{name} ({cagr:.1f}%)",
            color=color, linewidth=1.8, alpha=0.90,
        )

    ax.set_title(
        f"{country}: Permanent Capital Vehicles vs {benchmark_name}\n{period_label}",
        fontsize=13, fontweight="bold", pad=12,
    )
    ax.set_ylabel("Indexed to 100", fontsize=10)
    ax.grid(True, alpha=0.3)

    # Legend outside plot
    ax.legend(
        loc="upper left", bbox_to_anchor=(1.01, 1.0),
        fontsize=8, framealpha=0.85, borderpad=0.5,
    )

    fig.tight_layout()
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180, bbox_inches="tight", facecolor="#1a1a1a")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description="PCI Country-Level Benchmark Charts")
    parser.add_argument("--input", default="data/pci_constituents_v4.csv", help="Screened CSV input")
    parser.add_argument("--period", choices=["2000", "2010", "both"], default="both",
                        help="Period: 2000-2025, 2010-2025, or both")
    parser.add_argument("--output-dir", default="charts/", help="Output directory")
    args = parser.parse_args()

    constituents = load_constituents(args.input)
    if len(constituents) == 0:
        print("ERROR: No Pass constituents found.")
        sys.exit(1)

    # Group by country
    countries = constituents.groupby("Country")

    periods = []
    if args.period in ("2000", "both"):
        periods.append(("2000-01-01", "2025-12-31", "2000-2025", "2000–2025"))
    if args.period in ("2010", "both"):
        periods.append(("2010-01-01", "2025-12-31", "2010-2025", "2010–2025"))

    total_charts = 0

    for country, group in countries:
        country = country.strip()
        benchmark_ticker = get_benchmark(country)
        if not benchmark_ticker:
            print(f"⚠️  {country}: No benchmark mapping — SKIPPED")
            continue

        for start, end, subdir, label in periods:
            # Download benchmark
            bm_series = download_series(benchmark_ticker, start, end)
            if bm_series is None:
                # Try fallback
                fallback = BENCHMARKS.get(country, {}).get("fallback")
                if fallback and fallback != benchmark_ticker:
                    bm_series = download_series(fallback, start, end)
            if bm_series is None:
                print(f"⚠️  {country}: Benchmark {benchmark_ticker} no data — SKIPPED")
                continue

            # Download PCV data
            pcvs = []
            for _, row in group.iterrows():
                ticker = row["Ticker"]
                name = row.get("Name", ticker)
                series = download_series(ticker, start, end)
                if series is not None and len(series) >= 104:  # ~2 years weekly
                    pcvs.append((name, series))
                else:
                    if series is None or len(series) < 104:
                        status = "no data" if series is None else f"short ({len(series)}w)"
                        print(f"  ⚠️  {ticker} ({name}): {status} — SKIPPED")

            if not pcvs:
                print(f"⚠️  {country}: No PCVs with sufficient data — SKIPPED")
                continue

            # Generate chart
            output_path = f"{args.output_dir}/{subdir}/{country.replace(' ', '_')}_vs_{benchmark_ticker.replace('^', '')}.png"
            benchmark_name = benchmark_ticker.replace("^", "")
            generate_country_chart(country, benchmark_name, bm_series, pcvs, label, output_path)
            print(f"✅ {country}: {len(pcvs)} PCVs vs {benchmark_name} | {label}")
            total_charts += 1

    print(f"\n═══ Done: {total_charts} charts generated ═══")


if __name__ == "__main__":
    main()
