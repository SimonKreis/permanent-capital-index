# AGENTS.md — working on this repository

Operational guide for anyone (human or agent) modifying the Permanent Capital Index.
For what the index *is*, read [`README.md`](README.md); for the rules that define it, read
[`methodology/pci-index-methodology.md`](methodology/pci-index-methodology.md).

---

## 1. The two invariants

### 1.1 No performance gate — ever

Membership is decided by **one uniform mechanical balance-sheet rule** (G1 form + age,
G3 allocation, G5 size). Nothing about past returns enters selection.

Earlier drafts used a performance gate (a trailing CAGR threshold). **It was abandoned and
must never be reintroduced.** An index that selects winners cannot honestly be used to argue
that the category wins — the conclusion would be smuggled into the premise. The methodology
states it plainly: *"No performance gate exists"* — no return, CAGR, TSR or book-value
threshold.

If you find a document describing a "performance gate" or a "Gate 2", it describes a
superseded methodology. `methodology/` is the single source of truth. **When code and
methodology disagree, the code is wrong** — that is exactly what happened to the rebalancing
logic (see §7.2).

### 1.2 Honest figures

The backtest is **not a claim of alpha**: the PCI sits between MSCI World and the S&P 500, and
the figure carries an **upward survivorship bias** (delisted names are absent from free data).
Every presentation of the numbers must keep that caveat. Do not quietly improve a figure.

---

## 2. Setup

```bash
pip install -r scripts/requirements.txt
```

Python 3.14 is the validated version. Dependencies: `yfinance`, `pandas`, `numpy`,
`matplotlib` — all four are used. No API key, no environment variable, no secret: the code
only calls public Yahoo Finance and SEC EDGAR endpoints. **Network access is required** for
any real run; without it only the offline checks in §4 can run.

---

## 3. Architecture

```
data/pci_candidate_universe.csv --(scripts/universe_screener.py)--> data/pci_screened_v4.csv
data/pci_constituents_v4.csv    --(scripts/simulator.py)---------->  data/historical/pci_levels.csv
                                                                     charts/pci_main.png
data/pci_constituents_v4.csv    --(scripts/compare_countries.py)-->  charts/{period}/*.png
```

- **`data/pci_constituents_v4.csv` is the authoritative list** (147 rows), the default input
  of the simulator and of `compare_countries.py`. Columns:
  `Ticker, Name, Country, Tag, Industry, MarketCap, InvRatio, PPERatio`
  (`Tag == "A"` marks an insurer; `InvRatio` drives the sensitivity table in methodology §7.1).
- Construction: **drifting equal weight with semi-annual reconstitution** — weights reset to
  1/N on June 30 and December 31 (methodology §5), total return, USD.
- `data/` and `charts/` hold **committed outputs**. Regenerate them in the same pass as the
  code that produces them, never separately.

---

## 4. Verification — there is no test suite

That is deliberate. "The script exited without an error" is not a verification. Run these
three levels, cheapest first, from the **repository root**.

```bash
# 1. the three scripts import (offline)
py -c "import sys; sys.path.insert(0,'scripts'); import compare_countries, simulator, universe_screener; print('3/3 OK')"

# 2. argument wiring answers (offline)
py scripts/simulator.py --help
```

```bash
# 3. index math (offline) — REQUIRED whenever compute_index changes.
# X compounds +10%/week, Y is flat, reconstitution at t2. The hand-computed
# final level is exactly 1160.25, and it must DIFFER from a weekly rebalance
# (1157.625) — that difference is what proves reconstitution is semi-annual.
py -c "
import sys; sys.path.insert(0,'scripts')
import pandas as pd
from simulator import compute_index
idx = pd.to_datetime(['2010-05-07','2010-05-14','2010-06-30','2010-07-07'])
px  = pd.DataFrame({'X':[100,110,121,133.1], 'Y':[100,100,100,100]}, index=idx)
got = round(compute_index(px, [pd.Timestamp('2010-06-30')], 1000.0).iloc[-1], 4)
weekly = round((1+px.pct_change().mean(axis=1).fillna(0)).cumprod().iloc[-1]*1000, 4)
assert abs(got-1160.25) < 0.01, f'drift+reset math wrong: {got}'
assert abs(got-weekly)  > 1.0,  'identical to weekly rebalance -> reconstitution not applied'
print(f'OK: semi-annual {got} != weekly {weekly}')
"
```

A change to the simulator or the screener is then verified by **re-running it** and comparing
the metrics against the published table in the README.

---

## 5. Commands

All from the **repository root** (see §7.1):

```bash
# Backtest — RUN OF RECORD (--end pinned, see §7.2)
py scripts/simulator.py --start 2010-01-01 --end 2026-06-30

# Structural screen (resumable: re-running continues where it stopped)
py scripts/universe_screener.py --universe csv:data/pci_candidate_universe.csv

# Per-country charts (slow: 17 countries with a mapped benchmark x 2 periods)
py scripts/compare_countries.py --period both
```

**Run of record:** `--start 2010-01-01 --end 2026-06-30`, effective period
2010-01-08 → 2026-07-03, **145 of 147** constituents priced.
PCI CAGR **12.9%**, MaxDD −36.1%, Vol 16.9%, Sharpe 0.68.

---

## 6. Reproducing the published figures

The same metrics appear in **five places**. Missing one leaves the repository publishing a
number it can no longer reproduce — which has happened before.

1. `README.md` — backtest table
2. `README.md` — the "run of record" note under it
3. `whitepaper/pci-whitepaper.md` — the table **and** three prose passages (opening summary,
   methodological section, and the "reality check" that contrasts the figure with the 20% myth)
4. `methodology/pci-index-methodology.md` §7.1 — the sensitivity table
5. This file, §5 — the run-of-record line

For §7.1, regenerate **all four rows**, never just the 0.30 row: the section's argument rests
on the *monotonicity* between rows (CAGR and Sharpe fall, volatility rises, as the threshold
tightens). Download once and subset by `InvRatio` rather than running four backtests; the 0.30
row must reproduce the main run exactly. If monotonicity ever breaks, do not publish — the
section's text has become false and must be rewritten.

---

## 7. Known traps

**7.1 — Scripts use relative paths.** Run them from the **repository root**. Running
`py simulator.py` from inside `scripts/` fails with
`FileNotFoundError: data/pci_constituents_v4.csv`.

**7.2 — `--end` defaults to *today*, so figures drift.** Three consecutive runs produced
12.8%, 13.1% and 12.9% purely because the period kept extending. **Always pin `--end`** to a
reconstitution date (June 30 / December 31) for any publishable number.

The same section of code once hid a subtler version of this bug: a `rebals` block computed the
semi-annual dates but was never wired into `compute_index`, *and* was itself broken —
`pd.date_range(freq="6MS")` yields months {1, 7}, which the `month in (6, 12)` filter then
discarded entirely, leaving an empty list. The index was silently rebalancing weekly while the
documentation described semi-annual reconstitution. Do not restore that block as-is.

**7.3 — yfinance randomly drops 1–2 names in bulk downloads.** The same ticker fetched alone
works. Before concluding a delisting, retest it in isolation:

```bash
py -c "import yfinance as yf; print(len(yf.download('CS.PA', start='2010-01-01', end='2026-06-30', progress=False, auto_adjust=True)))"
```

**7.4 — `PRA` and `IAC` genuinely return no data** (verified in isolation — not flakiness):
ProAssurance was acquired, IAC was renamed "People Inc". Hence 145/147. Do **not** patch
`data/pci_constituents_v4.csv` casually: changing the list changes the index, and belongs to a
reconstitution decision. This is also a live illustration of the survivorship bias that
methodology §7 discloses.

**7.5 — `compute_index(px_usd, rebal_dates, base=1000.0)`**: `rebal_dates` is a **required**
positional argument. A single-argument call raises `TypeError`.

**7.6 — Windows encoding.** Piping Unicode out of Python fails under `cp1252`. Prefix with
`PYTHONIOENCODING=utf-8` when printing accents or arrows.

---

## 8. Conventions

- **Never reintroduce a performance criterion** (§1.1). This invariant outranks everything.
- **Methodology precedes code.** If the code diverges from `methodology/`, the code is the bug.
- **Deletion over addition.** Two similar-looking lists of balance-sheet keys do not justify a
  shared module while their callers apply different gates.
