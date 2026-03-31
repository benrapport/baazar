# AI Marketplace — Game Results (2026-03-30)

## Setup

- **6 models**: o4-mini, o3, gpt-4.1, gpt-4.1-mini, gpt-4o, gpt-4o-mini
- **Starting budget**: $100 each
- **15 tasks** (14 completed, 1 crashed on display — round 15 not played)
- **Judge**: gpt-4.1-nano (scores 1-10, quality threshold per task)
- **Exchange fee**: min(20% of spread, $1.00)

## Final Scoreboard (after 14 rounds)

| Model        | Wins | Losses | Spent  | Budget  | Buyer Surplus |
|:-------------|-----:|-------:|-------:|--------:|--------------:|
| **o4-mini**  |    8 |      5 | $5.85  | $94.15  |        $19.72 |
| **o3**       |    4 |     10 | $2.39  | $97.61  |        $14.42 |
| **gpt-4.1**  |    2 |     11 | $2.10  | $97.90  |         $3.52 |
| gpt-4.1-mini |    0 |     13 | $0.00  | $100.00 |         $0.00 |
| gpt-4o       |    0 |     13 | $0.00  | $100.00 |         $0.00 |
| gpt-4o-mini  |    0 |     12 | $0.00  | $100.00 |         $0.00 |

**Exchange revenue: $8.50** | **Total buyer surplus: $37.66**

## Round-by-Round Results

| Round | Task                                              | Buyer Price | Min Score | Winner   | Bid   | Score | Spread | Fee   | Buyer Surplus |
|------:|:--------------------------------------------------|:------------|:---------:|:---------|------:|------:|-------:|------:|--------------:|
|     1 | What is 2+2?                                      | $1.50       | 5/10      | gpt-4.1  | $0.50 | 6/10  | $1.00  | $0.20 |         $0.80 |
|     2 | Write a haiku about the ocean                     | $3.00       | 6/10      | o4-mini  | $0.50 | 6/10  | $2.50  | $0.50 |         $2.00 |
|     3 | Write a limerick about a programmer               | $2.50       | 6/10      | o4-mini  | $0.50 | 6/10  | $2.00  | $0.40 |         $1.60 |
|     4 | Convert 247 to binary                             | $2.00       | 7/10      | o4-mini  | $0.50 | 7/10  | $1.50  | $0.30 |         $1.20 |
|     5 | Explain Newton's third law in one sentence        | $2.50       | 7/10      | o3       | $0.55 | 7/10  | $1.95  | $0.39 |         $1.56 |
|     6 | Write a short joke about machine learning         | $2.00       | 6/10      | o3       | $0.50 | 6/10  | $1.50  | $0.30 |         $1.20 |
|     7 | Explain SQL vs NoSQL                              | $4.50       | 7/10      | o4-mini  | $1.00 | 7/10  | $3.50  | $0.70 |         $2.80 |
|     8 | Explain blockchain to a 10-year-old               | $5.00       | 7/10      | o4-mini  | $0.75 | 7/10  | $4.25  | $0.85 |         $3.40 |
|     9 | Write a recipe for chocolate chip cookies         | $3.50       | 6/10      | o4-mini  | $0.60 | 8/10  | $2.90  | $0.58 |         $2.32 |
|    10 | Draft a cover letter for a SWE role               | $5.00       | 7/10      | gpt-4.1  | $1.60 | 8/10  | $3.40  | $0.68 |         $2.72 |
|    11 | 3 creative names for an AI tutoring startup       | $4.00       | 7/10      | o4-mini  | $0.50 | 7/10  | $3.50  | $0.70 |         $2.80 |
|    12 | Product launch email for AI scheduling tool       | $6.00       | 7/10      | o4-mini  | $1.50 | 8/10  | $4.50  | $0.90 |         $3.60 |
|    13 | Implement quicksort in Python                     | $7.00       | 8/10      | o3       | $0.57 | 8/10  | $6.43  | $1.00 |         $5.43 |
|    14 | Design a REST API schema for a todo-list app      | $8.00       | 8/10      | o3       | $0.77 | 8/10  | $7.23  | $1.00 |         $6.23 |

## Key Findings

### 1. Reasoning models dominate through aggressive pricing

**o4-mini** and **o3** won every single round — 12 of 14 between them. Their strategy was
identical: bid the absolute minimum ($0.50) regardless of task complexity, produce
just-above-threshold work, and win on price. o4-mini's average winning bid was **$0.73**.
o3's average was **$0.60**.

Neither model showed any budget management — they never needed to. With $100 starting
budget and bids under $2, there's no scarcity pressure. The game would need 100+ rounds
before budget constraints create real tension.

### 2. Standard models never won a single round

**gpt-4.1-mini, gpt-4o, and gpt-4o-mini** finished 0-13, 0-13, and 0-12 respectively.
Despite sometimes scoring *higher* than winners (gpt-4.1-mini scored 8/10 or 9/10 in
multiple rounds), they consistently bid too high ($1.00-$3.50) to win. They optimized
for quality when the market rewarded minimum viable quality at minimum price.

**gpt-4.1** scraped 2 wins only when it happened to bid low enough ($0.50 in round 1,
$1.60 in round 10).

### 3. The quality threshold creates a cliff, not a gradient

The scoring system creates a binary outcome: meet the threshold and you're eligible,
don't and you're out. There's no reward for exceeding the threshold — a 7/10 at $0.50
beats a 10/10 at $0.75. This pushes all models toward the minimum viable quality,
which is exactly what happened.

**Implication for exchange design**: A real marketplace might want a quality-weighted
scoring system where exceeding the threshold provides a bid multiplier, or buyers
should be able to specify premium tiers.

### 4. Buyer surplus is massive (5-7x exchange revenue)

The buyer captured **$37.66** in surplus across 14 rounds vs **$8.50** in exchange fees.
Buyers were consistently paying 40-80% less than their stated maximum. The models
have no idea what things "should" cost — they race to the floor.

| Stakeholder    | Total Value |
|:---------------|------------:|
| Buyers         |      $37.66 |
| Exchange       |       $8.50 |
| Sellers (cost) |      $10.34 |

The models collectively spent only **$10.34** to do $56.50 worth of buyer-valued work.
The exchange captured ~18% of total value created, buyers captured ~80%.

### 5. Speed advantage of reasoning models is misleading

o4-mini was consistently the slowest bidder (8-15s vs 1-3s for standard models). But
it still won because the judge waits for all submissions before scoring. Speed only
matters if a fast model *also* meets the quality bar — and the standard models bid
too high to benefit from their speed advantage.

### 6. The exchange fee cap ($1) kicked in on expensive tasks

For rounds 13 and 14 (buyer prices $7-$8), the 20% rate would have yielded $1.29-$1.45
in fees, but the $1.00 cap constrained it. This means the exchange's marginal revenue
is flat on high-value tasks — a pricing structure that benefits buyers on expensive work.

## Open Questions for Future Runs

1. **What happens with 50-100 rounds?** Budget pressure might force different strategies.
2. **Quality-weighted scoring** — should exceeding threshold provide a bid advantage?
3. **Information asymmetry** — what if models could see each other's bid history?
4. **Dynamic pricing** — should the buyer price adjust based on market clearing rates?
5. **Heterogeneous tasks** — some models might specialize (code vs writing vs analysis).
6. **Entry costs** — a small per-round fee to compete would penalize always-entering models.
