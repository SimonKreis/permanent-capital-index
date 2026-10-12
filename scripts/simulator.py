#!/usr/bin/env python3
"""
PCI Simulator (v4) -- honest historical backtest.

Builds the equal-weight, total-return, USD Permanent Capital Index from the
current constituent list and compares it to total-return benchmarks.

HONESTY / LIMITATIONS (see methodology section 7):
  * Survivorship: the constituent list is the CURRENT structurally-selected set.
    Names that delisted/failed are absent (free data does not retain them), so
    historical returns carry an UPWARD bias. Structural selection makes the bias
    smaller than a performance filter would, but it is not zero. Reported as-is.
  * Point-in-time fundamentals are unavailable on free data; the current
    structural classification is applied historically (structural attributes are
    stable, so look-ahead is minor).
  * A name contributes only once it has price history (post-IPO), via dropna.

Construction: drifting equal weight (1/N at each semi-annual rebalance, weights
drift between rebalances). Benchmarks are TOTAL RETURN: ^SP500TR and URTH
(iShares MSCI World, dividend-adjusted).
"""
from __future__ import annotations
import argparse, warnings
from datetime import datetime
from pathlib import Path
from typing import Optional
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import yfinance as yf
warnings.filterwarnings("ignore")

SUFFIX_TO_FX = {
    ".TO": "CADUSD=X", ".V": "CADUSD=X",
    ".ST": "SEKUSD=X", ".CO": "DKKUSD=X", ".OL": "NOKUSD=X", ".HE": "EURUSD=X",
    ".PA": "EURUSD=X", ".AS": "EURUSD=X", ".DE": "EURUSD=X", ".MI": "EURUSD=X",
    ".BR": "EURUSD=X", ".LS": "EURUSD=X", ".MC": "EURUSD=X", ".VI": "EURUSD=X",
    ".SW": "CHFUSD=X", ".L": "GBPUSD=X",
    ".AX": "AUDUSD=X", ".NZ": "NZDUSD=X",
    ".T": "JPYUSD=X", ".HK": "HKDUSD=X", ".SI": "SGDUSD=X",
    ".KS": "KRWUSD=X", ".KQ": "KRWUSD=X", ".TW": "TWDUSD=X", ".TWO": "TWDUSD=X",
    ".JO": "ZARUSD=X", ".SA": "BRLUSD=X", ".MX": "MXNUSD=X",
    ".NS": "INRUSD=X", ".BO": "INRUSD=X", ".WA": "PLNUSD=X",
    ".SS": "CNYUSD=X", ".SZ": "CNYUSD=X",
}


def fx_for(ticker: str) -> Optional[str]:
    for suf, fx in SUFFIX_TO_FX.items():
        if ticker.endswith(suf):
            return fx
    return None


def weekly(df):
    df.index = pd.to_datetime(df.index)
    return df.resample("W-FRI").last()


def dl_prices(tickers, start, end):
    data = yf.download(tickers, start=start, end=end, progress=False,
                       auto_adjust=True, group_by="ticker")
    if len(tickers) == 1:
        px = data["Close"].to_frame(name=tickers[0])
    else:
        try:
            px = data.xs("Close", axis=1, level=1)
        except Exception:
            px = data["Close"]
    return weekly(px)


def dl_one(ticker, start, end):
    d = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True)
    if d is None or d.empty or "Close" not in d:
        return pd.Series(dtype=float)
    s = d["Close"]
    if isinstance(s, pd.DataFrame):
        s = s.squeeze()
    return weekly(s.to_frame("x"))["x"].dropna()


def to_usd(px, tickers, start, end):
    fx_pairs = sorted({fx_for(t) for t in tickers if fx_for(t)})
    if fx_pairs:
        fx = sanitize(dl_prices(fx_pairs, start, end)).ffill()
    else:
        fx = pd.DataFrame()
    out = px.copy()
    for t in tickers:
        fp = fx_for(t)
        if t in out.columns and fp and not fx.empty and fp in fx.columns:
            out[t] = out[t] * fx[fp].reindex(out.index).ffill()
    return out



def sanitize(px):
    """Remove single-point data glitches (a price that spikes >3x then reverts).
    Such prints are yfinance artifacts; left in, one name wrecks an equal-weight
    index. Real weekly equity moves for these large/mid caps stay well under 3x."""
    px = px.copy()
    for c in px.columns:
        s = px[c]
        up = s / s.shift(1)
        down_next = s.shift(-1) / s
        bad = ((up > 3) & (down_next < 0.5)) | ((up < 1/3) & (down_next > 2))
        if bad.any():
            px.loc[bad.fillna(False), c] = float("nan")
    return px


def compute_index(px_usd, rebal_dates, base=1000.0):
    """Drifting equal-weight, total-return index with semi-annual reconstitution.

    Weights are reset to 1/N across the available constituents on each
    reconstitution date (methodology section 5: effective June 30 / December 31),
    and drift with prices in between -- the published construction. A name enters
    at the first reconstitution after its price history begins; the current list
    is held fixed historically (see the survivorship note). Handles IPO entry and
    missing prints gracefully and cannot be hijacked by a single name.
    """
    r = px_usd.pct_change()
    rebal_rows = {px_usd.index[px_usd.index >= d][0]
                  for d in rebal_dates if (px_usd.index >= d).any()}
    w = pd.Series(0.0, index=px_usd.columns)
    level, out = base, []
    for i, dt in enumerate(px_usd.index):
        avail = px_usd.loc[dt].notna()
        if i > 0:                                   # book the week's return on drifted weights
            growth = w * (1.0 + r.loc[dt].where(avail, 0.0).fillna(0.0))
            g = growth.sum()
            if g > 0:
                level *= g
                w = growth / g
        if i == 0 or dt in rebal_rows:              # reset to equal weight after booking
            n = int(avail.sum())
            w = (avail / n) if n else pd.Series(0.0, index=px_usd.columns)
        out.append(level)
    return pd.Series(out, index=px_usd.index).dropna()


def metrics(s):
    s = s.dropna()
    if len(s) < 3:
        return dict(cagr=0, vol=0, max_dd=0, sharpe=0)
    yrs = (s.index[-1] - s.index[0]).days / 365.25
    cagr = (s.iloc[-1] / s.iloc[0]) ** (1 / yrs) - 1 if yrs > 0 else 0
    r = s.pct_change().dropna()
    vol = r.std() * np.sqrt(52)
    dd = ((s - s.cummax()) / s.cummax()).min()
    sharpe = (r.mean() - 0.02 / 52) / r.std() * np.sqrt(52) if r.std() > 0 else 0
    return dict(cagr=cagr * 100, vol=vol * 100, max_dd=dd * 100, sharpe=sharpe)


def main():
    ap = argparse.ArgumentParser(description="PCI v4 backtest")
    ap.add_argument("--input", default="data/pci_constituents_v4.csv")
    ap.add_argument("--start", default="2010-01-01")
    ap.add_argument("--end", default=datetime.now().strftime("%Y-%m-%d"))
    ap.add_argument("--out-dir", default="data/historical")
    args = ap.parse_args()

    cons = pd.read_csv(args.input)
    tickers = cons["Ticker"].astype(str).tolist()
    print(f"Constituents: {len(tickers)} | {args.start} -> {args.end}")

    px = dl_prices(tickers, args.start, args.end)
    px = px[[t for t in tickers if t in px.columns]]
    px_usd = to_usd(px, tickers, args.start, args.end)
    px_usd = sanitize(px_usd).ffill()  # carry last price on non-trading weeks (avoid sparse-week artifacts)
    cov = px_usd.notna().sum(axis=1)
    print(f"Names with data: {px_usd.notna().any().sum()}/{len(tickers)} | "
          f"weekly rows: {len(px_usd)}")

    start_ts, end_ts = pd.Timestamp(args.start), pd.Timestamp(args.end)
    rebals = [pd.Timestamp(y, m, d)
              for y in range(start_ts.year, end_ts.year + 1)
              for m, d in ((6, 30), (12, 31))]
    rebals = [d for d in rebals if start_ts <= d <= end_ts]
    pci = compute_index(px_usd, rebals)
    # start index when at least 15 names are present
    first = cov[cov >= 15].index.min()
    if pd.notna(first):
        pci = pci[pci.index >= first]
    pci = pci / pci.iloc[0] * 1000

    spx = dl_one("^SP500TR", args.start, args.end).reindex(pci.index).ffill()
    wld = dl_one("URTH", args.start, args.end).reindex(pci.index).ffill()
    spx = spx / spx.dropna().iloc[0] * 1000 if spx.notna().any() else spx
    wld = wld / wld.dropna().iloc[0] * 1000 if wld.notna().any() else wld

    mp, ms, mw = metrics(pci), metrics(spx), metrics(wld)
    out = Path(args.out_dir); out.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame({"PCI": pci, "S&P 500 TR": spx, "MSCI World TR": wld})
    df.to_csv(out / "pci_levels.csv", float_format="%.2f")

    eff0, eff1 = pci.index[0].date(), pci.index[-1].date()
    fig, ax = plt.subplots(figsize=(13, 7))
    ax.plot(pci.index, pci.values, color="#c0392b", lw=2.2, label=f"PCI ({mp['cagr']:.1f}%)")
    if spx.notna().any():
        ax.plot(spx.index, spx.values, color="#2980b9", lw=2.0, label=f"S&P 500 TR ({ms['cagr']:.1f}%)")
    if wld.notna().any():
        ax.plot(wld.index, wld.values, color="#7f8c8d", lw=2.0, ls="--", label=f"MSCI World TR ({mw['cagr']:.1f}%)")
    cov_dt = pd.Timestamp("2020-03-20")
    if pci.index[0] <= cov_dt <= pci.index[-1]:
        ax.axvline(cov_dt, color="gray", alpha=0.3, lw=0.8, ls="--")
        ax.annotate("COVID-19", xy=(cov_dt, pci.iloc[(pci.index - cov_dt).map(abs).argmin()]),
                    xytext=(20, -30), textcoords="offset points", fontsize=8, color="gray",
                    arrowprops=dict(arrowstyle="->", color="gray", alpha=0.5))
    ax.set_yscale("log"); ax.yaxis.set_major_formatter(mticker.ScalarFormatter())
    ax.set_title(f"Permanent Capital Index vs Total-Return Benchmarks | {eff0} to {eff1}\n"
                 f"{len(tickers)} constituents, equal-weight, USD TR (survivorship-biased -- see methodology)",
                 fontsize=12, fontweight="bold")
    ax.set_ylabel("Index (log, base 1000)"); ax.legend(loc="upper left"); ax.grid(alpha=0.3)
    stat = (f"CAGR  PCI {mp['cagr']:.1f}%  S&P {ms['cagr']:.1f}%  MSCI {mw['cagr']:.1f}%\n"
            f"MaxDD PCI {mp['max_dd']:.1f}%  S&P {ms['max_dd']:.1f}%  MSCI {mw['max_dd']:.1f}%\n"
            f"Vol   PCI {mp['vol']:.1f}%  S&P {ms['vol']:.1f}%  MSCI {mw['vol']:.1f}%")
    ax.text(0.015, 0.02, stat, transform=ax.transAxes, fontsize=8.5, family="monospace",
            va="bottom", bbox=dict(boxstyle="round,pad=0.4", facecolor="white", alpha=0.85))
    fig.tight_layout(); Path("charts").mkdir(exist_ok=True)
    fig.savefig("charts/pci_main.png", dpi=160); plt.close(fig)

    print(f"\nEffective period: {eff0} -> {eff1}")
    for nm, m in [("PCI", mp), ("S&P 500 TR", ms), ("MSCI World TR", mw)]:
        print(f"  {nm:14s} CAGR {m['cagr']:5.1f}%  MaxDD {m['max_dd']:6.1f}%  "
              f"Vol {m['vol']:4.1f}%  Sharpe {m['sharpe']:.2f}")
    print(f"\nSaved: {out/'pci_levels.csv'} , charts/pci_main.png")


if __name__ == "__main__":
    main()
