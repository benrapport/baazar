# Agent Exchange — System Design

## What This Is

A developer infrastructure product — an SDK/API where you ask for work and get work back. Under the hood, it routes your request through an exchange that connects to thousands of specialized AI agents via real-time RFQ (Request for Quote).

```
Developer:  result = exchange.call(capability="ocr", input=image, max_price=0.05)
            # That's it. One line. Result comes back.
```

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         DEVELOPER (buyer)                           │
│  result = exchange.call(capability="ocr", input=img, max_price=5¢) │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                           SDK / CLIENT                              │
│  • Python, JS, Go SDKs                                              │
│  • Handles auth, retry, streaming                                   │
│  • Batches micro-payments for settlement                            │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ HTTPS / WebSocket
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        EXCHANGE GATEWAY                             │
│                                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────────────┐  │
│  │ Auth &   │  │ Request  │  │ Rate     │  │ Request           │  │
│  │ Metering │  │ Parsing  │  │ Limiting │  │ Classification    │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  │ (what capability  │  │
│       │              │             │         │  does this need?)  │  │
│       └──────────────┴─────────────┴────────┴─────┬─────────────┘  │
│                                                    │                │
└────────────────────────────────────────────────────┼────────────────┘
                                                     │
                                                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        RFQ ENGINE (core)                            │
│                                                                     │
│  1. BROADCAST: Send request metadata to qualifying agents (~10ms)   │
│  2. COLLECT:   Agents evaluate input + quote a price      (~50ms)   │
│  3. SELECT:    Pick winner (price × quality × latency)    (~10ms)   │
│  4. ROUTE:     Send full request to winner                (~5ms)    │
│  5. VERIFY:    Check output quality                       (async)   │
│                                                                     │
│  Total RFQ overhead: ~75ms                                          │
│                                                                     │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐ │
│  │ Agent Registry   │  │ Reputation DB   │  │ Pricing Engine      │ │
│  │                  │  │                 │  │                     │ │
│  │ • Capabilities   │  │ • Quality/agent │  │ • Historical prices │ │
│  │ • Availability   │  │ • Latency/agent │  │ • Surge detection   │ │
│  │ • Current load   │  │ • Success rate  │  │ • Fair price est.   │ │
│  │ • Pricing model  │  │ • Per-task-type │  │ • Anomaly detection │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────────┘ │
│                                                                     │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
            ┌──────────────┼──────────────┐
            ▼              ▼              ▼
     ┌────────────┐ ┌────────────┐ ┌────────────┐
     │  Agent A   │ │  Agent B   │ │  Agent C   │    ... (thousands)
     │            │ │            │ │            │
     │ OCR agent  │ │ OCR agent  │ │ Legal      │
     │ Claude     │ │ GPT-4.1   │ │ RAG+Claude │
     │ $0.003/req │ │ $0.004/req │ │ $0.45/req  │
     │ 9.1/10 avg │ │ 8.8/10 avg│ │ 9.4/10 avg │
     └────────────┘ └────────────┘ └────────────┘
            │              │              │
            └──────────────┼──────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      SETTLEMENT LAYER                               │
│                                                                     │
│  • Micro-payment batching (accumulate, settle periodically)         │
│  • Developer billing (monthly invoice or prepaid credits)           │
│  • Agent payouts (monthly or threshold-based)                       │
│  • Exchange fee collection                                          │
│  • Powered by Stripe Connect                                        │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Component Deep Dives

### 1. SDK / Client Library

**What it does:** The developer's only touchpoint. Makes calling the exchange feel like calling any API.

```python
from agentx import Exchange

ex = Exchange(api_key="ax_live_...")

# Simple call — exchange handles everything
result = ex.call(
    capability="ocr",
    input={"image": open("receipt.png", "rb")},
    max_price=0.05,           # 5¢ max
    min_quality=7,            # optional quality floor
    timeout=5.0               # seconds
)

print(result.output)          # the OCR text
print(result.agent)           # "ocr-agent-v3" (who handled it)
print(result.price)           # 0.003 (what it actually cost)
print(result.quality_score)   # 9.2 (historical avg of this agent)
print(result.latency_ms)      # 340
```

**Key decisions:**
- Sync by default, async optional (`await ex.call_async(...)`)
- Streaming for long-running tasks (`for chunk in ex.stream(...)`)
- File upload handling (images, PDFs, etc.) built into the SDK
- Auto-retry on agent failure (transparent failover to next-best agent)
- Client-side request ID for idempotency

**What the SDK does NOT do:**
- No local caching of agent results (that's the developer's job)
- No local quality verification (exchange handles this)
- No agent selection (exchange handles this)

---

### 2. Exchange Gateway

**What it does:** First thing that sees every request. Auth, parsing, classification, rate limiting.

**Request Classification** is the critical piece. When a developer calls `capability="contract_review"`, the gateway needs to:

1. Map the capability string to the agent registry taxonomy
2. Determine request complexity (affects routing + pricing)
3. Identify any sub-capabilities needed

```
Input:  capability="contract_review", input={pdf: ...}
Output: {
    primary_capability: "legal.contract_review",
    estimated_complexity: "moderate",
    input_size: "15_pages",
    sub_capabilities_likely: ["legal.ip_analysis", "legal.liability_check"],
    qualifying_agents: 23
}
```

**Key decisions:**
- Classification model: small fine-tuned model or rule-based? (Start rule-based, graduate to ML)
- Capability taxonomy: flat namespace ("ocr") or hierarchical ("vision.ocr.handwriting")?
- How to handle ambiguous capabilities? (Suggest closest match? Error?)

---

### 3. RFQ Engine

**What it does:** The core matching engine. This is where the exchange microstructure lives.

**Step-by-step for a single request:**

```
[0ms]   Request arrives: capability="ocr", max_price=5¢

[1ms]   FILTER: Query agent registry
        → 47 agents provide "ocr"
        → 31 are available (not overloaded)
        → 22 are within price range
        → Top 5 selected by reputation score

[5ms]   BROADCAST: Send request metadata to top 5 agents
        Metadata includes:
        {
            capability: "ocr",
            input_type: "image/png",
            input_size_bytes: 245000,
            max_price_cents: 5.0,
            quality_floor: 7
        }
        NOTE: Full input is NOT sent yet. Just metadata for quoting.

[10-60ms] COLLECT: Agents evaluate metadata + return quotes
        Agent-A: { price: 0.003, estimated_quality: 9.1, estimated_latency_ms: 200 }
        Agent-B: { price: 0.004, estimated_quality: 8.8, estimated_latency_ms: 150 }
        Agent-C: { price: 0.002, estimated_quality: 7.5, estimated_latency_ms: 400 }
        Agent-D: { price: 0.008, estimated_quality: 9.6, estimated_latency_ms: 100 }
        Agent-E: (timeout — didn't respond in 50ms)

[62ms]  SELECT: Score = quality × (1 / price) × (1 / latency), weighted
        Winner: Agent-A (best value composite score)

[63ms]  ROUTE: Send full request (with actual input data) to Agent-A

[63-400ms] Agent-A processes, returns result

[400ms] RETURN: Result sent back to developer
        Exchange logs: agent, price, latency, (quality scored async)
```

**Key decisions:**

| Decision | Options | Recommendation |
|----------|---------|----------------|
| How many agents to broadcast to? | All qualifying vs top-N | Top 5 — limits load, fast enough |
| What if no agent responds? | Error vs retry vs fallback | Retry with expanded pool, then error |
| Quote timeout? | 50ms vs 100ms vs 500ms | 50ms for simple tasks, 200ms for complex |
| Selection algorithm? | Lowest price vs composite score | Composite: price × quality × latency |
| Send full input during quote? | Yes vs metadata only | Metadata only — protects buyer data until match |

**Why metadata-only quoting matters:**
- Agents see input type + size, NOT the actual content
- Protects buyer confidentiality during the quote phase
- Only the winning agent receives the full input
- Losers never see the buyer's data

---

### 4. Agent Registry

**What it does:** The canonical database of every agent, their capabilities, availability, and pricing.

**Agent registration:**
```python
# Agent developer registers their agent
@ex.provide(
    capability="ocr",
    sub_capabilities=["ocr.handwriting", "ocr.receipt", "ocr.document"],
    pricing={
        "base_price": 0.003,         # 0.3¢ per request
        "complexity_multiplier": {    # optional: price varies by input
            "simple": 1.0,
            "moderate": 2.0,
            "complex": 5.0,
        }
    },
    max_concurrent=100,               # capacity limit
    avg_latency_ms=200,
    regions=["us-east-1", "eu-west-1"]
)
def my_ocr_agent(input):
    # agent implementation
    return result
```

**Registry schema (per agent):**
```
agent_id:           "ag_ocr_v3_abc123"
developer_id:       "dev_xyz"
capabilities:       ["ocr", "ocr.handwriting", "ocr.receipt"]
pricing_model:      { base: 0.003, multipliers: {...} }
max_concurrent:     100
current_load:       37 (updated real-time via heartbeat)
avg_latency_ms:     200
regions:            ["us-east-1"]
status:             "active"
created_at:         "2026-03-01"
last_heartbeat:     "2026-03-30T18:42:01Z"
```

**Key decisions:**
- Capability taxonomy: who defines it? (Exchange curates a standard taxonomy, agents map to it)
- Pricing: static listing vs dynamic per-request? (Support both — static as default, dynamic via quote callback)
- Health checks: heartbeat interval? (Every 10s, mark unhealthy after 3 missed)
- Versioning: can agents run multiple versions? (Yes — `ocr-v2`, `ocr-v3` coexist)

---

### 5. Reputation System

**What it does:** Tracks quality, reliability, and speed for every agent across every transaction. This is the exchange's core moat.

**What gets tracked (per agent, per capability):**
```
quality_scores:     [9, 8, 9, 10, 8, 9, ...]     # from async quality checks
avg_quality:        8.9
p50_latency_ms:     180
p99_latency_ms:     450
success_rate:       99.7%
uptime:             99.95%
total_transactions: 847,293
dispute_rate:       0.02%
```

**Quality scoring:**
- **Automated:** Exchange runs a lightweight quality check on a sample of outputs (5-10%)
- **Buyer feedback:** Optional thumbs up/down from developers
- **Comparative:** Periodically send same request to multiple agents, compare outputs
- **Decay:** Recent transactions weighted more heavily than old ones

**Reputation tiers:**
```
★★★★★  Elite     (>9.0 avg, >99.9% uptime, >10K transactions)
★★★★   Verified  (>8.0 avg, >99.5% uptime, >1K transactions)
★★★    Standard  (>7.0 avg, >99% uptime, >100 transactions)
★★     New       (<100 transactions, probationary)
★      Flagged   (quality issues, under review)
```

**Key decisions:**
- How to quality-score agent outputs automatically? (Use a judge model? Heuristics? Both?)
- How to handle new agents with no reputation? (Probation period: first 100 calls routed at lower priority)
- Gaming prevention? (Detect if agent returns cached/stale results, rate-limits quality checks)

---

### 6. Settlement Layer

**What it does:** Handles all money movement between developers (buyers) and agents (sellers).

**The micro-payment problem:**
Individual transactions are sub-penny (0.003¢). Stripe charges $0.30 + 2.9% per transaction. Processing each one individually is impossible.

**Solution: Batched settlement**
```
Real-time:     Track every transaction in the exchange's ledger
Hourly:        Compute net positions (Developer A owes $4.27, Agent B is owed $12.83)
Daily:         Settle net positions via Stripe Connect
Monthly:       Invoice for enterprise accounts
```

**Transaction ledger (per call):**
```
tx_id:          "tx_abc123"
timestamp:      "2026-03-30T18:42:01.234Z"
buyer_id:       "dev_xyz"
agent_id:       "ag_ocr_v3"
capability:     "ocr"
price_cents:    0.3
exchange_fee:   0.06    (20% of spread or whatever fee model)
buyer_charged:  0.36
agent_paid:     0.30
quality_score:  null    (scored async)
latency_ms:     210
status:         "completed"
```

**Exchange fee model:**

| Model | How it works | Pros | Cons |
|-------|-------------|------|------|
| Flat % | 20% of every transaction | Simple, predictable | Expensive for high-volume buyers |
| Spread % | 20% of (max_price - agent_price) | Only charges on surplus | Zero fee if agent bids at max |
| Tiered | 20% → 15% → 10% at volume thresholds | Rewards scale | Complex |
| Subscription + lower % | $99/mo + 5% | Predictable for enterprise | Barrier for small developers |

**Recommended:** Start with flat 20%, move to tiered as volume grows.

**Key decisions:**
- Prepaid credits vs post-paid invoicing? (Credits for self-serve, invoicing for enterprise)
- Minimum payout threshold for agents? ($10 minimum before Stripe payout)
- Dispute resolution? (Buyer disputes quality → exchange reviews → refund or reject)

---

### 7. Agent-to-Agent Commerce

**What it does:** Enables agents to call other agents through the exchange — the 90% of volume that happens below the surface.

```python
# Inside an agent's implementation — calling another agent
@ex.provide(capability="travel_planning")
def plan_trip(input):
    # This agent calls OTHER agents via the same exchange
    flights = ex.call(capability="flight_search", input={...})
    hotels = ex.call(capability="hotel_search", input={...})
    restaurants = ex.call(capability="restaurant_booking", input={...})

    # Compose the results
    return build_itinerary(flights, hotels, restaurants)
```

**Key insight:** The travel_planning agent is BOTH a seller (provides travel_planning) AND a buyer (consumes flight_search, hotel_search, etc.). Its cost structure includes sub-agent calls.

**Transaction chain:**
```
Developer pays 50¢ for travel_planning
    → TravelAgent earns 50¢, spends 15¢ on sub-agents
        → FlightAgent earns 8¢
        → HotelAgent earns 5¢
        → RestaurantAgent earns 2¢
    → TravelAgent net: 35¢
    → Exchange collects fees at every layer
```

**Exchange sees the full chain.** This is incredibly valuable data — it reveals the supply chain structure of the agent economy.

**Key decisions:**
- Should agent-to-agent calls get a lower fee? (Yes — encourages depth, 10% instead of 20%)
- Should the developer see the full call chain? (Optional transparency: `result.trace`)
- Should agents be able to set preferred sub-agents? (Yes — stable supply chains improve quality)
- Circuit breaker: if a sub-agent fails, should the exchange auto-retry with an alternative?

---

## Data Flows

### Happy Path (single request)

```
1. Developer calls SDK                              [client]
2. SDK sends HTTPS request to gateway               [network]
3. Gateway authenticates, classifies request         [gateway]
4. RFQ engine queries registry for qualifying agents [rfq]
5. RFQ broadcasts metadata to top-5 agents           [rfq → agents]
6. Agents return quotes (price, est. quality)        [agents → rfq]
7. RFQ selects winner                                [rfq]
8. Full input sent to winning agent                  [rfq → agent]
9. Agent processes, returns output                   [agent → rfq]
10. RFQ logs transaction, returns to gateway         [rfq → gateway]
11. Gateway returns response to SDK                  [gateway → client]
12. SDK returns result to developer                  [client]
13. (Async) Quality check on output                  [reputation]
14. (Async) Transaction added to settlement ledger   [settlement]
```

### Failure Path

```
1-7.  Same as happy path
8.    Full input sent to winning agent
9a.   Agent fails (timeout, error, bad output)
9b.   Exchange auto-retries with runner-up agent     [transparent to developer]
10a.  Runner-up succeeds → return to developer
10b.  Runner-up also fails → return error to developer
11.   Failed agent's reputation score decremented
12.   If pattern of failures → agent flagged for review
```

### Agent-to-Agent Path

```
1-9.  Developer's request handled by Agent-A
10.   Agent-A internally calls ex.call(capability="sub_task")
11.   NEW RFQ cycle starts for sub_task (steps 4-9 repeat)
12.   Sub-agent returns to Agent-A
13.   Agent-A may call more sub-agents (parallel or sequential)
14.   Agent-A composes final output
15.   Returns to developer
16.   Settlement: developer charged for Agent-A,
      Agent-A charged for sub-agents, exchange fees at each hop
```

---

## Open Questions (Need Decisions)

### Product
1. **Capability taxonomy** — who defines the namespace? Exchange-curated, community-contributed, or free-form?
2. **Quality scoring** — automated judge model on every call (expensive) or sampled (cheaper but less data)?
3. **Agent identity** — should developers see which agent handled their request? Or is it fully opaque?
4. **SLAs** — can agents promise specific latency/quality guarantees? Does the exchange enforce them?

### Technical
5. **Protocol** — REST API? gRPC? WebSocket for streaming? (Start REST, add gRPC for latency-sensitive)
6. **Agent integration** — SDK callback vs webhook vs long-poll? How do agents receive requests?
7. **Data locality** — if buyer data is in EU, can it only route to EU-hosted agents?
8. **Caching** — should the exchange cache identical requests? (Huge cost savings, but stale data risk)

### Economic
9. **Fee structure** — flat % vs spread-based vs tiered? (See Settlement section)
10. **Agent pricing** — static listing vs dynamic per-request quotes vs both?
11. **Minimum viable supply** — how many agents needed at launch for the product to be useful?
12. **Cold start** — seed supply side ourselves? Pay early agents to list? Build first-party agents?

### Trust
13. **Data handling** — metadata-only during quoting is clean. But the winning agent DOES see the full input. How to enforce data deletion after processing?
14. **Agent vetting** — any vetting before listing? Or fully open + reputation-based?
15. **Dispute resolution** — automated or human-reviewed? What's the SLA on disputes?
