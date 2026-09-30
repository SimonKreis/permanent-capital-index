# Permanent Capital Index™ — Index Methodology

**Version 4.0 — June 2026**
**Status: canonical. This document is the single source of truth for PCI eligibility, construction, and maintenance. Where any other file in this repository conflicts with this document, this document governs.**

---

## 1. Index Objective

The Permanent Capital Index (PCI) is an equal-weighted, total-return, USD-denominated
index of publicly traded companies that are **permanent capital allocators** — entities
whose primary economic activity is owning and reallocating capital across a diversified
set of assets, financed by capital that carries no redemption obligation and an
indefinite horizon.

The PCI selects constituents by **structure and governance**, not by past performance.
This is a deliberate and load-bearing choice (see 2.1). The index is designed to be a
reproducible, openly specified benchmark for the permanent-capital category, such
that any third party can rebuild the constituent list from the published rules and public
data.

---

## 2. Design Principles

### 2.1 Why selection is structural, not performance-based

Earlier drafts used a performance gate (a trailing CAGR threshold). That approach is
abandoned for one decisive reason: **an index whose inclusion rule is "has outperformed"
cannot be used as evidence that the category outperforms.** It is circular — the
conclusion is smuggled into the premise, and any backtest it produces is contaminated by
look-ahead and survivorship bias.

The PCI therefore defines membership entirely on **forward-stable structural and
governance attributes**. Performance is never an input to selection. It is measured as an
*output* and reported honestly, including in periods where the index does not outperform.
If the permanent-capital category has a genuine edge, a structurally selected index will
reveal it without curation. If it does not, that too is an honest, publishable finding.

### 2.2 The theoretical edge the structure is meant to capture

Two structural properties are the hypothesized source of any long-run advantage, and the
methodology is built to measure exactly these:

1. **Permanence of capital → no forced selling.** Capital with no redemption claim and an
   indefinite horizon allows an allocator to hold illiquid or contrarian positions through
   a full cycle and to deploy into dislocations rather than liquidate into them. This is
   the structural precondition for "be greedy when others are fearful."

2. **Owner alignment → low agency cost.** Concentrated, long-tenured ownership (family,
   foundation, founder, strategic bloc) aligns the decision-maker's horizon with
   multi-decade compounding rather than quarterly earnings management.

Diversified allocation is the *activity* that defines the category; permanence and
alignment are the *edge*. The eligibility rules operationalize all three.

---

## 3. Eligibility Criteria

A constituent should, in principle, satisfy all of: permanence of capital, owner
alignment, capital-allocation activity, diversification, and investability. In
practice only the attributes that are **reliably computable from free public
data** are enforced as an automated screen; the rest are carried as **disclosed
attributes** (see below). The screen applies **one uniform mechanical rule to every
candidate**: no per-name judgment, no manual selection, no insurer special case.

### Decisive mechanical gates (`scripts/universe_screener.py`)

- **G1: Permanence & durability.** An operating corporation (not a closed-end
  fund, ETF, BDC, SPAC, or finite-life vehicle), continuously listed **>= 3 years**.
- **G3: Allocation signature.** Investment-type assets (equity stakes,
  equity-method associates and JVs, long-term investments, and, for insurers, the
  investment portfolio) are **>= 30% of total assets**, AND property, plant &
  equipment is **<= 33% of total assets**. One rule, applied identically to
  insurers, holding companies, and trading houses. The 30% level is deliberately
  generous so that consolidated aggregators such as the *sogo shosha* and
  Brookfield qualify alongside equity-method holdings such as Investor AB.
- **G5: Investability.** Market capitalisation **>= USD 250M** (the "category"
  floor; a future investable subset uses >= USD 1B).

> **No performance gate exists**: no return, CAGR, TSR, or book-value threshold.

### Disclosed attributes (not auto-enforced)

Owner alignment (concentrated long-term ownership / dual-class / long CEO tenure)
and fine-grained diversification are part of the *conceptual* definition but are
**not reliable from free data**: public APIs badly understate family/foundation
control (they report Investor AB insider ownership at ~0.3% when the Wallenberg
sphere controls ~50% of the votes), and clean segment data is unavailable. The
only one published is reported insider ownership, best-effort and subject to that
caveat (`Insiders_raw` in `data/pci_screened_v4.csv`); no diversification measure
is published. Neither attribute is enforced as an automated filter.

### 3.1 One uniform rule, generic data normalization

Selection is purely mechanical and identical for every name. Apart from the
fund-form list described in 3.2, the only human input is a **generic field-mapping** (the canonical investment/PPE line items in the
screener), applied to all issuers alike so the rule reads the right numbers from
heterogeneous accounting labels (US GAAP, IFRS, J-GAAP, K-GAAP). This is data
plumbing (committed and auditable), **never name-by-name judgment**. We do not
hand-include "good" allocators or hand-exclude look-alikes: whatever passes the
rule is in.

### 3.2 Known limitations of the mechanical rule

A balance-sheet rule on free data has three honest failure modes, all uniform and
disclosed rather than patched by hand:

- **False negatives.** Companies that fully *consolidate* their holdings (e.g.
  Ackermans & van Haaren, HAL Trust, Power Corporation) show operating assets
  rather than an "investments" line, and can fall below the 30% threshold despite
  being genuine permanent-capital vehicles. No threshold rescues them without
  voiding the criterion; they are documented casualties of free-data limits.
- **Over-inclusion.** Any insurer or financial whose balance sheet is
  investment-dominated qualifies, including large life/diversified insurers that
  are not Buffett-style allocators. This is the accepted cost of a purely
  mechanical, no-curation rule. **If the resulting index behaves like a sector
  fund or underperforms, the response is to revisit the *criteria*, never to
  hand-pick the names.**
- **Fund-form detection.** G1 excludes closed-end funds and investment trusts, but the
  automated screen cannot infer legal form from free data (such vehicles report as
  ordinary equity). Known trust-structured vehicles (Pershing Square Holdings, RIT
  Capital) are therefore excluded through a short, committed and auditable list in the
  screener (`FORM_EXCLUDE`). It enforces the G1 form rule only, never a judgment on
  quality or returns.

### 3.3 The motivating archetypes (illustrative, not hand-enforced)

The phenomenon takes four structural forms. The examples below are *motivation*,
not a manual inclusion/exclusion list; the mechanical rule decides membership.

| Archetype | Illustrative examples |
|-----------|------------------------|
| Float allocator | Berkshire Hathaway, Fairfax, Markel |
| Portfolio-manager allocator | Brookfield |
| Industrial aggregator | Mitsubishi, Itochu, Marubeni (*sogo shosha*) |
| Family / permanent holding | Investor AB, Industrivarden, 3i Group |

## 4. Classification Tags (Disclosure Only)

Each constituent is tagged by capital source for transparency. The tag does not affect
eligibility or weight. The screener assigns it mechanically: **A** when the issuer's
reported sector or industry mentions insurance, **B/C** otherwise. The two non-insurance
forms (B, retained-earnings holding; C, structurally-leveraged) are not separated in the
published data.

| Tag | Capital source | Illustrative names |
|-----|----------------|--------------------|
| **A: Float-funded** | Insurance float allocated into ownership | Berkshire Hathaway, Markel, Fairfax |
| **B/C: Retained-earnings holding or structurally-leveraged** | Permanent equity / patient family capital, or long-term structural debt / trading capital | Investor AB, Sofina, Exor, Mitsubishi Corp, Itochu, Brookfield Corp |

---

## 5. Index Construction

| Parameter | Specification |
|-----------|---------------|
| **Weighting** | Equal weight (1/N) at each reconstitution |
| **Reconstitution & rebalance** | Semi-annual, effective June 30 and December 31 |
| **Currency** | USD |
| **Return type** | Total return (dividends reinvested) |
| **Base value** | 1,000 at inception |
| **Inception** | The earliest date on which >= 15 eligible constituents have continuous USD price history (data-limited; stated explicitly in published outputs — see 7). No inception earlier than the data supports is claimed. |
| **Constituent bounds** | Minimum 15; **no maximum** — the index is deliberately inclusive (currently 147, per `data/pci_constituents_v4.csv`) |

### 5.1 Reconstitution

At each reconstitution date, all gates are re-evaluated using data available **as of that
date** (to the extent free data permits — see 7). Newly eligible companies are added;
companies that no longer pass any gate are removed. Weights are reset to 1/N.

### 5.2 No constituent cap

The index is **deliberately uncapped**: every name that passes the mechanical rule is
included. There is no maximum-count ceiling and no ranking step. If the resulting breadth
ever proves to dilute the category, the response is to revisit the *eligibility criteria*
(Section 3), never to rank or hand-trim the names.


### 5.3 Currency consistency

All eligibility tests, returns, and the index level are computed in **USD**. Local-currency
figures are never used for selection or measurement; non-USD securities are converted at
prevailing FX at each valuation date. (This corrects a prior inconsistency in which
selection used local-currency returns while the index was USD-denominated.)

---

## 6. Benchmarks

The PCI is reported against, on a like-for-like **total-return, USD** basis:

- **S&P 500 Total Return** (`^SP500TR`) — *not* the price index `^GSPC`, to avoid a
  dividend asymmetry against a total-return PCI.
- **MSCI World**, via a total-return proxy (iShares MSCI World ETF, `URTH`, dividend-
  adjusted). Note `URTH` inception is 2012; comparisons cannot extend before its data.

---

## 7. Limitations and Honesty Protocol

Disclosed on the index outputs themselves, not buried:

1. **Survivorship.** The universe is built from currently listed entities. Companies that
   were eligible historically but have since delisted or failed are absent, because free
   data (yfinance) does not retain delisted tickers. This imparts an **upward bias** to
   historical returns. The bias is *mitigated but not eliminated* by structural selection:
   structural attributes are stable over time, so applying the current classification
   historically introduces only minor look-ahead — far less than a performance filter. It
   is not zero, and is reported as such.
2. **Point-in-time fundamentals.** Free data does not provide historical point-in-time
   balance sheets; structural classification uses the most recent available fundamentals.
   The temporal stability of structural attributes limits the resulting error.
3. **Reproducibility.** The candidate universe (`data/pci_candidate_universe.csv`), the
   normalization field-mapping (in `scripts/universe_screener.py`) and the screen output
   with the ratios behind each decision (`data/pci_screened_v4.csv`) are committed, so the
   constituent list can be regenerated mechanically from public inputs. The screen output
   reflects the June 2026 snapshot but carries no per-row data date, and a re-run reads the
   fundamentals available on the day it runs, so results can drift as issuers report.

Honest framing of the contribution: *a reproducible, structurally defined, openly
specified benchmark of the permanent-capital category, with a transparently documented
risk/return profile* — not a claim of guaranteed alpha.

---

### 7.1 Robustness — sensitivity to the allocation threshold

The G3 allocation threshold (INV_MIN, default 30%) is the one selection variable that
could plausibly be "tuned." It is deliberately **not** tuned for performance. For full
transparency, the table reports how the index behaves as the threshold is tightened
(2010–2026, equal-weight, USD total return):

| INV_MIN | Constituents | of which insurers | CAGR | Vol | Max DD | Sharpe |
|---------|--------------|-------------------|------|-----|--------|--------|
| **0.30 (index)** | 147 | 102 | **12.9%** | 16.9% | −36.1% | **0.68** |
| 0.40 | 136 | 98 | 12.7% | 17.1% | −36.8% | 0.67 |
| 0.50 | 119 | 86 | 12.5% | 17.2% | −36.8% | 0.65 |
| 0.60 | 103 | 72 | 12.2% | 17.5% | −36.6% | 0.63 |

Tightening the purity threshold **monotonically lowers return and Sharpe and raises
volatility** — the opposite of the intuition that "purer allocators compound better,"
and confirmation that the diluting insurers are not a performance drag. This disclosure
shows (a) the inclusive 0.30 setting is not chosen to flatter the backtest, and (b) the
discipline of never tuning for performance is sound: the one knob one might twist to
"improve" results in fact degrades them when moved in the thesis-aligned direction.
Differences are small and rest on a single survivorship-affected path, so none of this is
offered as proof of edge.


## 8. Maintenance & Governance

- **Semi-annual (each reconstitution):** re-evaluate all gates; add/remove; reset to 1/N.
- **Annual:** review the candidate universe for newly listed or newly qualifying entities.
- **Normalization layer:** reviewed at each reconstitution; changes versioned in git.

---

## 9. Licensing & Trademark (MSCI-style model)

The methodology is **open by design**, following established index providers (MSCI, S&P
Dow Jones, FTSE Russell): the method is published for transparency and credibility; the
protected, monetizable assets are the **brand** and the **official index data**, not
secrecy of the method.

- **Methodology, framework, whitepaper, documentation:**
  [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) — free to read, cite, reuse,
  and build upon **with attribution**, including commercially.
- **Code (`scripts/`):** [MIT](https://opensource.org/licenses/MIT).
- **Name and brand — "Permanent Capital Index", "PCI", logo:** trademark of the Index
  Sponsor. Using the name or official index data to **name, market, or benchmark a
  financial product**, or representing a product as *the* official Permanent Capital Index,
  requires a license.

A method idea is not itself copyrightable; the moat is canonical status, brand, and
reference data — which is why the method is published openly.

See [`LICENSE.md`](../LICENSE.md) for the controlling legal text.
