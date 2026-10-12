#!/usr/bin/env python3
"""
PCI Universe Screener (v4) -- bottom-up, structural, no performance gate.

One UNIFORM mechanical rule for every candidate. No per-name judgment, no
manual selection. Owner alignment is a DISCLOSED ATTRIBUTE, not a gate (free
ownership data is unreliable for family-controlled vehicles). "Normalization"
here means a GENERIC field-mapping applied identically to all issuers so the
mechanical rule reads the right balance-sheet numbers -- it is data plumbing,
never name selection.

Gates (uniform, methodology v4):
  G1 form+age : operating corporation, listed >= MIN_AGE_YEARS
  G3 alloc    : investment-type assets (incl. equity-method associates) >= INV_MIN
                of total assets, AND PPE <= PPE_MAX
  G5 size     : market cap >= MCAP_MIN

Status: CONSTITUENT (passes) | DATA_GAP (size/age ok, allocation uncomputable
from free data) | REJECT. DATA_GAP names are flagged, never silently dropped.

Universe (--universe, comma-unioned): csv:<path> | sec
Resumable: appends to --output, skips done tickers, honors --max-seconds.
"""
from __future__ import annotations
import argparse, csv as csv_mod, json, time, urllib.request, warnings
from pathlib import Path
from typing import Optional
import pandas as pd
import yfinance as yf
warnings.filterwarnings("ignore")

MIN_AGE_YEARS = 3.0
INV_MIN = 0.30
PPE_MAX = 0.33
MCAP_MIN = 250e6
# Closed-end funds / investment trusts: G1a excludes them, but free data cannot
# infer legal form (they report as EQUITY). This committed, auditable list enforces
# the rule where automation cannot. Form-curation (methodology-mandated), not selection.
FORM_EXCLUDE = {"PSH.L", "RCP.L"}

TOTAL_ASSETS = ["Total Assets", "totalAssets"]
# umbrella aggregate (use the largest single one present)
AGG = ["Investments And Advances", "Total Investments", "Long Term Investments"]
# equity-method associates / JV stakes (the allocator signal for consolidated holdcos)
ASSOC = ["Long Term Equity Investment", "Investmentsin Associatesat Cost",
         "Investment In Associates And Joint Ventures", "Investments in Subsidiaries"]
# portfolio securities (the allocator signal for insurers) + misc
OTHER = ["Other Investments", "Available For Sale Securities",
         "Held To Maturity Securities", "Trading Securities"]
FIN = ["Investmentin Financial Assets"]
PROP = ["Investment Properties"]
PPE = ["Net PPE", "Gross PPE", "Property Plant And Equipment",
       "Net Property Plant Equipment", "propertyPlantAndEquipment"]
OUT_COLS = ["Ticker", "Name", "Country", "Sector", "Industry", "Tag", "Status",
            "MarketCap", "InvRatio", "PPERatio", "AgeYrs",
            "G1_age", "G3_alloc", "G5_size", "Insiders_raw", "Note"]


def _first(col, idx, keys) -> Optional[float]:
    for k in keys:
        if k in idx:
            v = col.get(k)
            if v is not None and not pd.isna(v):
                return float(v)
    return None


def _sum(col, idx, keys) -> float:
    tot = 0.0
    for k in keys:
        if k in idx:
            v = col.get(k)
            if v is not None and not pd.isna(v) and v > 0:
                tot += float(v)
    return tot


def invest_total(col, idx, ta) -> Optional[float]:
    """Generic, de-duplicated investment-asset total. Avoids double-counting an
    umbrella aggregate against its components by taking the larger of the two."""
    agg = _first(col, idx, AGG) or 0.0
    assoc = _first(col, idx, ASSOC) or 0.0     # one associate line (dups are equal)
    other = _sum(col, idx, OTHER)
    fin = _first(col, idx, FIN) or 0.0
    prop = _first(col, idx, PROP) or 0.0
    components = assoc + other + fin
    base = max(agg, components)
    if base <= 0 and prop <= 0:
        return None
    return min(base + prop, ta)  # cap at total assets


def analyze(ticker: str) -> dict:
    out = {"Ticker": ticker, "Status": "REJECT", "Note": ""}
    if ticker in FORM_EXCLUDE:
        out["Note"] = "closed-end fund / investment trust excluded (G1a)"
        return out
    try:
        t = yf.Ticker(ticker)
        info = t.info or {}
        mcap = info.get("marketCap")
        out["Name"] = info.get("longName") or info.get("shortName") or ""
        out["Country"] = info.get("country", "")
        out["Sector"] = info.get("sector", "")
        out["Industry"] = info.get("industry", "")
        out["MarketCap"] = mcap
        out["Insiders_raw"] = info.get("heldPercentInsiders")
        if not mcap:
            out["Note"] = "no marketcap / no data"
            return out
        ind = (out["Industry"] + " " + out["Sector"]).lower()
        out["Tag"] = "A" if ("insurance" in ind or "reinsurance" in ind) else "B/C"
        g5 = mcap >= MCAP_MIN
        age = None
        epoch = info.get("firstTradeDateEpochUtc")
        if epoch:
            age = (time.time() - epoch) / (365.25 * 86400)
        out["AgeYrs"] = round(age, 1) if age else None
        g1 = (age is None) or (age >= MIN_AGE_YEARS)
        inv_ratio = ppe_ratio = None
        bs = t.balance_sheet
        if bs is not None and not bs.empty:
            col = bs.iloc[:, 0]; idx = bs.index
            ta = _first(col, idx, TOTAL_ASSETS)
            if ta and ta > 0:
                inv = invest_total(col, idx, ta)
                ppe = _first(col, idx, PPE)
                inv_ratio = inv / ta if inv else None
                ppe_ratio = ppe / ta if ppe else None
        out["InvRatio"] = round(inv_ratio, 3) if inv_ratio is not None else None
        out["PPERatio"] = round(ppe_ratio, 3) if ppe_ratio is not None else None
        if inv_ratio is not None:
            g3 = (inv_ratio >= INV_MIN) and (ppe_ratio is None or ppe_ratio <= PPE_MAX)
        else:
            g3 = None
        out["G1_age"] = g1; out["G3_alloc"] = g3; out["G5_size"] = g5
        if g5 and g1 and g3 is True:
            out["Status"] = "CONSTITUENT"
        elif g5 and g1 and g3 is None:
            out["Status"] = "DATA_GAP"
        else:
            out["Status"] = "REJECT"
        return out
    except Exception as e:
        out["Note"] = repr(e)[:120]
        return out


def _sec_us() -> list:
    req = urllib.request.Request("https://www.sec.gov/files/company_tickers.json",
                                 headers={"User-Agent": "pci-research contact@example.com"})
    data = json.load(urllib.request.urlopen(req, timeout=30))
    return [row["ticker"] for row in data.values()]


def load_universe(spec: str) -> list:
    tickers = []
    for part in spec.split(","):
        part = part.strip()
        if part == "sec":
            tickers += _sec_us()
        elif part.startswith("csv:"):
            tickers += pd.read_csv(part[4:])["Ticker"].dropna().astype(str).tolist()
        elif part:
            tickers.append(part)
    seen, uniq = set(), []
    for t in tickers:
        if t not in seen:
            seen.add(t); uniq.append(t)
    return uniq


def main():
    ap = argparse.ArgumentParser(description="PCI bottom-up structural screener (v4)")
    ap.add_argument("--universe", default="csv:data/pci_candidate_universe.csv")
    ap.add_argument("--output", default="data/pci_screened_v4.csv")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--delay", type=float, default=0.0)
    ap.add_argument("--max-seconds", type=float, default=0.0)
    args = ap.parse_args()
    universe = load_universe(args.universe)
    if args.limit:
        universe = universe[:args.limit]
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if out.exists():
        try:
            done = set(pd.read_csv(out)["Ticker"].astype(str))
        except Exception:
            pass
    todo = [t for t in universe if t not in done]
    print(f"Universe: {len(universe)} | done: {len(done)} | todo: {len(todo)}")
    write_header = (not out.exists()) or out.stat().st_size == 0
    t0 = time.time(); n = 0
    with out.open("a", newline="") as fh:
        w = csv_mod.DictWriter(fh, fieldnames=OUT_COLS, extrasaction="ignore")
        if write_header:
            w.writeheader()
        for tk in todo:
            w.writerow(analyze(tk)); fh.flush(); n += 1
            if n % 20 == 0:
                print(f"  +{n} (elapsed {time.time() - t0:.0f}s)")
            if args.max_seconds and (time.time() - t0) >= args.max_seconds:
                print(f"  [time budget hit at {n} new rows -- re-run to resume]"); break
            time.sleep(args.delay)
    df = pd.read_csv(out)
    print("\n--- Cumulative ---"); print(df["Status"].value_counts().to_string())
    print(f"CONSTITUENT: {(df['Status']=='CONSTITUENT').sum()} | "
          f"DATA_GAP: {(df['Status']=='DATA_GAP').sum()} | of {len(df)}")


if __name__ == "__main__":
    main()
