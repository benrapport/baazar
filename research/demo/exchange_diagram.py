#!/usr/bin/env python3
"""Generate a PDF diagramming the full AI Exchange system."""

import markdown2
import weasyprint
from pathlib import Path

HERE = Path(__file__).resolve().parent
PDF_FILE = HERE / "EXCHANGE_SYSTEM.pdf"

MARKDOWN = r"""
# AI Exchange System — Full Architecture

## 1. System Overview

The AI Exchange is a **real-time marketplace** where AI models compete for work.
Buyers post tasks with a maximum price and quality threshold. Sellers (AI models)
bid in microcents, produce work, and race to meet the quality bar. The exchange
takes a fee from the spread. **Models pay for their own tokens** — expensive models
must be strategic about which tasks to compete for.

```
┌────────────────────────────────────────────────────────────────────┐
│                        AI EXCHANGE                                  │
│                                                                     │
│   ┌──────────┐    ┌─────────────┐    ┌──────────────────────────┐  │
│   │  BUYER   │───▸│  ORDER BOOK │◂───│  SELLERS (6 AI Models)   │  │
│   │  (Task   │    │  (Tasks +   │    │                          │  │
│   │  Queue)  │    │  Bids)      │    │  o3        gpt-4.1       │  │
│   └──────────┘    └──────┬──────┘    │  o4-mini   gpt-4.1-mini  │  │
│                          │           │  gpt-4o    gpt-4o-mini   │  │
│                   ┌──────▾──────┐    └──────────────────────────┘  │
│                   │   JUDGE     │                                   │
│                   │  (Scoring)  │    ┌──────────────────────────┐  │
│                   └──────┬──────┘    │  TOKEN COST LEDGER       │  │
│                          │           │  Tracks real API costs    │  │
│                   ┌──────▾──────┐    │  per model per call       │  │
│                   │ TRANSACTION │◂───│  Deducted from budget     │  │
│                   │  (Clear)    │    └──────────────────────────┘  │
│                   └─────────────┘                                   │
└────────────────────────────────────────────────────────────────────┘
```

---

## 2. Participants

### Buyer Agent (Task Queue)
- Posts tasks with: **description**, **max price (¢)**, **min quality score (1-10)**
- 100 tasks across 5 price tiers
- Buyer surplus = max price − (winning bid + exchange fee)

### Seller Models (6 Competing AI Models)

| Model | Type | Input $/M | Output $/M | Cost per ~500-token call |
|-------|------|-----------|------------|--------------------------|
| **o3** | Reasoning | $10.00 | $40.00 | ~1.7¢ |
| **o4-mini** | Reasoning | $1.10 | $4.40 | ~0.25¢ |
| **gpt-4.1** | Standard | $2.00 | $8.00 | ~0.35¢ |
| **gpt-4.1-mini** | Standard | $0.40 | $1.60 | ~0.07¢ |
| **gpt-4o** | Standard | $2.50 | $10.00 | ~0.40¢ |
| **gpt-4o-mini** | Standard | $0.15 | $0.60 | ~0.03¢ |

Each model starts with **300.00¢ ($3.00)**. Budget covers **both token costs AND bids**.

### Judge (gpt-4.1-nano)
- Scores submissions 1–10
- Provides actionable feedback on non-qualifying work
- Polling every 2 seconds
- Cost: ~0.01¢ per scoring call (paid by the exchange)

---

## 3. Transaction Flow

```
TIME ──────────────────────────────────────────────────────▸

 BUYER POSTS TASK
 "Write quicksort in Python" — 15.0¢ max, score ≥ 7
    │
    ▼
 ┌──────────────── BIDDING PHASE ────────────────────┐
 │                                                     │
 │  o3 sees: "15¢ task, my tokens cost ~1.7¢/call"   │
 │  → Bids 8.5¢, produces work                        │
 │                                                     │
 │  gpt-4o-mini sees: "15¢ task, tokens cost ~0.03¢"  │
 │  → Bids 2.0¢, produces work                        │
 │                                                     │
 │  gpt-4.1-mini: Bids 3.5¢                           │
 │  o4-mini: PASSES (saving budget)                    │
 │  gpt-4.1: Bids 5.0¢                                │
 │  gpt-4o: Bids 4.0¢                                 │
 └─────────────────────────────────────────────────────┘
    │
    ▼
 ┌──────────────── SCORING PHASE ────────────────────┐
 │                                                     │
 │  Judge scores each submission:                      │
 │    o3:           9/10  ✓ qualifies                  │
 │    gpt-4o-mini:  5/10  ✗ below threshold            │
 │    gpt-4.1-mini: 7/10  ✓ qualifies                  │
 │    gpt-4.1:      8/10  ✓ qualifies                  │
 │    gpt-4o:       7/10  ✓ qualifies                  │
 │                                                     │
 │  Non-qualifiers get feedback →                      │
 │    gpt-4o-mini: "Missing edge case handling..."     │
 └─────────────────────────────────────────────────────┘
    │
    ▼
 ┌──────────────── REVISION PHASE (if needed) ───────┐
 │                                                     │
 │  gpt-4o-mini sees score + feedback                  │
 │  → Decides: REVISE (costs more tokens)              │
 │  → Resubmits improved work                          │
 │  → Judge re-scores: 7/10 ✓ now qualifies            │
 └─────────────────────────────────────────────────────┘
    │
    ▼
 ┌──────────────── WINNER SELECTION ─────────────────┐
 │                                                     │
 │  Qualifiers: o3 (8.5¢), gpt-4o-mini (2.0¢),      │
 │              gpt-4.1-mini (3.5¢), gpt-4.1 (5.0¢), │
 │              gpt-4o (4.0¢)                          │
 │                                                     │
 │  WINNER: gpt-4o-mini (lowest bid among qualifiers) │
 └─────────────────────────────────────────────────────┘
    │
    ▼
 ┌──────────────── TRANSACTION CLEARING ─────────────┐
 │                                                     │
 │  Buyer max price:     15.00¢                        │
 │  Winning bid:          2.00¢                        │
 │  Spread:              13.00¢                        │
 │  Exchange fee:         1.00¢  (20% of 13¢ = 2.6¢,  │
 │                                capped at 1.00¢)     │
 │  Buyer pays:           3.00¢  (bid + fee)           │
 │  Buyer surplus:       12.00¢  (max − buyer pays)    │
 │                                                     │
 │  Seller (gpt-4o-mini):                              │
 │    Bid deducted:       2.00¢                        │
 │    Token cost:         0.06¢  (2 API calls)         │
 │    Total round cost:   2.06¢                        │
 │    Budget remaining: 297.94¢                        │
 └─────────────────────────────────────────────────────┘
```

---

## 4. Economic Model

### Budget Mechanics

Each model starts with **300.00¢ ($3.00)**. Two things drain the budget:

1. **Token costs** — Every API call (bidding, revising) costs real tokens.
   Deducted from budget **even if you lose**. This is the cost of thinking.

2. **Winning bid** — If you win, your bid amount is deducted from budget.
   This is the price you charge the buyer.

**A model is eliminated when its budget drops below 0.10¢.**

### Exchange Fee

```
fee = min(20% × spread, 1.00¢)
spread = buyer_max_price − winning_bid
```

The exchange captures value from the gap between what the buyer was willing
to pay and what the seller charged. Capped at 1¢ per transaction.

### Who Pays What

| Party | Pays | Receives |
|-------|------|----------|
| **Buyer** | winning_bid + exchange_fee | Completed work |
| **Winning seller** | bid + token costs | Task completion credit |
| **Losing sellers** | token costs only | Nothing |
| **Exchange** | Judge token costs | Exchange fee per transaction |

### Strategic Tensions

| Tension | Description |
|---------|-------------|
| **Token cost vs task value** | o3 spends ~1.7¢ just to compete. A 2¢ task is barely worth it. |
| **Speed vs quality** | Fast submission may win before expensive models finish. |
| **Bid vs survive** | Low bids win but drain budget faster. |
| **Compete vs pass** | Every competition costs tokens. Passing preserves budget. |
| **Revise vs cut losses** | Revision costs more tokens but may save a bid. |

---

## 5. Price Tier Design (100 Tasks)

| Tier | Buyer Price | Min Score | Count | Target Competitor |
|------|------------|-----------|-------|-------------------|
| **Trivial** | 1–3¢ | 5–6 | 20 | gpt-4o-mini dominates |
| **Easy** | 3–8¢ | 6–7 | 25 | gpt-4.1-mini competitive |
| **Moderate** | 8–20¢ | 7 | 25 | gpt-4.1, gpt-4o enter |
| **Hard** | 20–50¢ | 7–8 | 20 | o4-mini worthwhile |
| **Expert** | 50–100¢ | 8–9 | 10 | o3 quality edge matters |

**Key insight**: Cheap models can compete everywhere, but expensive models
can only profitably compete in high-tier tasks where quality matters.
o3 loses money on trivial tasks just from token costs alone.

---

## 6. Decision Tree per Model per Round

```
Task announced: {description, buyer_price, min_score}
         │
         ▼
  ┌─ Can I afford to compete? ─┐
  │  (budget > token_cost + min_bid)
  │                             │
  NO                          YES
  │                             │
  ▼                             ▼
 PASS              ┌─ Is the task worth it? ──────┐
                   │  buyer_price > my_token_cost? │
                   │  Can I meet min_score?         │
                   │                                │
                   NO                             YES
                   │                                │
                   ▼                                ▼
                  PASS                      Set bid < buyer_price
                                            Produce work
                                            Submit bid + work
                                                    │
                                                    ▼
                                           ┌─ Judge scores ─┐
                                           │                 │
                                        ≥ min_score      < min_score
                                           │                 │
                                           ▼                 ▼
                                      QUALIFY         Receive feedback
                                      (may win)              │
                                                      ┌──────┴──────┐
                                                      │              │
                                                   REVISE          PASS
                                                   (costs more    (cut losses)
                                                    tokens)
```

---

## 7. Scoreboard Metrics

After each round, the scoreboard shows:

| Metric | Description |
|--------|-------------|
| **Wins** | Tasks won |
| **Losses** | Tasks competed in but lost |
| **Bid Spend** | Total ¢ spent on winning bids |
| **Token Spend** | Total ¢ spent on API tokens |
| **Budget** | Remaining ¢ |
| **Buyer Surplus** | Total ¢ saved by buyers from this model's wins |
| **Avg Bid** | Average winning bid amount |
| **Win Rate** | Wins / (Wins + Losses) |

**Exchange totals**: Total exchange fee revenue, total buyer surplus, total tokens consumed.

---

## 8. What Makes This Interesting

1. **Real economics**: Models pay real token costs. o3 is 100x more expensive
   than gpt-4o-mini per call. This creates genuine cost pressure.

2. **Asymmetric competition**: Cheap models dominate volume. Expensive models
   must pick battles. The "best" model may not be the most profitable.

3. **Market efficiency**: Over 100 rounds, we see whether the market converges
   to efficient pricing — do models learn to bid near their marginal cost?

4. **Quality-price tradeoff**: The judge evaluates value, not just quality.
   A decent answer at 2¢ beats a great answer at 20¢.

5. **Budget as health**: Models that overspend early get eliminated. The market
   naturally selects for efficiency over raw capability.

6. **Exchange as platform**: The 20% spread fee mimics real exchange economics.
   The exchange profits most when there's competition (spread exists).
"""

CSS = """
@page {
    size: letter;
    margin: 0.6in 0.7in;
    @bottom-center { content: counter(page); font-size: 9pt; color: #999; }
}
body {
    font-family: -apple-system, "Helvetica Neue", Helvetica, Arial, sans-serif;
    font-size: 10.5pt;
    line-height: 1.45;
    color: #1a1a1a;
}
h1 {
    font-size: 20pt;
    border-bottom: 3px solid #7c3aed;
    padding-bottom: 6px;
    margin-bottom: 14px;
    color: #111;
}
h2 {
    font-size: 14pt;
    color: #7c3aed;
    margin-top: 24px;
    border-bottom: 1px solid #ddd;
    padding-bottom: 3px;
    page-break-after: avoid;
}
h3 {
    font-size: 11pt;
    color: #374151;
    margin-top: 16px;
    page-break-after: avoid;
}
table {
    border-collapse: collapse;
    width: 100%;
    margin: 10px 0;
    font-size: 9pt;
}
th {
    background: #7c3aed;
    color: white;
    padding: 5px 7px;
    text-align: left;
    font-weight: 600;
}
td {
    padding: 4px 7px;
    border-bottom: 1px solid #e5e7eb;
}
tr:nth-child(even) td {
    background: #f8fafc;
}
strong { color: #111; }
ul, ol { padding-left: 20px; }
li { margin-bottom: 3px; }
code {
    background: #f1f5f9;
    padding: 1px 3px;
    border-radius: 3px;
    font-size: 9.5pt;
    font-family: "SF Mono", "Fira Code", monospace;
}
pre {
    background: #1e1e2e;
    color: #cdd6f4;
    padding: 12px 14px;
    border-radius: 6px;
    font-size: 8.5pt;
    line-height: 1.4;
    overflow-x: auto;
    white-space: pre-wrap;
    page-break-inside: avoid;
}
pre code {
    background: none;
    padding: 0;
    color: inherit;
    font-size: inherit;
}
p { margin: 6px 0; }
hr {
    border: none;
    border-top: 1px solid #e5e7eb;
    margin: 20px 0;
}
"""

html_body = markdown2.markdown(
    MARKDOWN,
    extras=["tables", "fenced-code-blocks", "header-ids"],
)

full_html = f"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<style>{CSS}</style>
</head><body>{html_body}</body></html>"""

weasyprint.HTML(string=full_html).write_pdf(str(PDF_FILE))
print(f"PDF written to {PDF_FILE}")
