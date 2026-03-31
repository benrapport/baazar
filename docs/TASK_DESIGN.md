# Task Generation & Difficulty Design for 1,000-Task Agent Simulation

**Date:** March 31, 2026
**Audience:** Design review, Thinker 6
**Scope:** Task taxonomy, difficulty metrics, schema, cost estimation

---

## 1. TASK CATEGORIES & TAXONOMY

### Core Categories (10 categories × ~100 tasks each)

#### 1.1 **Code Generation** (100 tasks)
Tasks where agents write executable code.

- **Easy (25%):** Implement simple functions, fix obvious bugs
  - "Write a Python function that counts vowels in a string"
  - "Create a function to validate email format"
  - Source: HumanEval subset (easy), custom simple functions

- **Medium (40%):** Multi-step algorithms, data structure manipulation
  - "Implement binary search with edge case handling"
  - "Write a function to find the longest palindromic substring"
  - Source: LeetCode easy-medium, HumanEval (original)

- **Hard (25%):** Complex algorithms, optimization, tool use
  - "Implement a graph algorithm (topological sort with cycle detection)"
  - "Write a Python script that uses APIs to fetch data and process"
  - Requires: code execution tool to verify

- **Extreme (10%):** Multi-file refactoring, performance optimization
  - "Optimize this O(n²) algorithm to O(n log n) with proof of equivalence"
  - "Design a caching layer for a database query system"
  - Tools needed: file I/O, code execution, reasoning

**Difficulty signals:**
- Branching logic (if statements > 3)
- Nested loops (depth > 2)
- Data structure selection matters
- Tool usage required (exec, file I/O)
- Need to verify correctness via test execution

---

#### 1.2 **Debugging & Root Cause Analysis** (100 tasks)
Agents find and fix bugs in provided code.

- **Easy (30%):** Off-by-one errors, obvious null checks
  - "Find the bug: this function returns `count - 1` instead of `count`"
  - Simple test case provided

- **Medium (45%):** Logic errors, wrong algorithm, edge cases
  - "Debug: Why does this quicksort fail on duplicate values?"
  - Multiple test cases, agent must trace execution

- **Hard (20%):** Race conditions, memory leaks, async bugs
  - "Debug this async/await code that deadlocks under concurrency"
  - Tools: code execution with trace output, thread/timing analysis

- **Extreme (5%):** Subtle state machine bugs, compiler-level issues
  - "Find the bug in this state machine that fails under specific event sequences"
  - Tools: full execution trace, state visualization

**Difficulty signals:**
- Number of lines of code to read (100 → 500+)
- Test cases that expose the bug (1 → 5+)
- Requires execution trace to find bug
- Involves concurrency/timing

---

#### 1.3 **Math & Logic Problems** (100 tasks)
Symbolic reasoning, proofs, mathematical problem-solving.

- **Easy (25%):** Arithmetic, basic algebra
  - "What is the derivative of 3x² + 2x + 1?"
  - "Solve: 2x + 5 = 13"

- **Medium (40%):** Calculus, probability, combinatorics
  - "Prove that the sum of first n odd numbers is n²"
  - "Find the probability that a random 3-card hand contains at least one ace"

- **Hard (25%):** Graph theory, advanced proofs, optimization
  - "Find the maximum spanning tree weight for this graph. Prove your algorithm."
  - "Show that the given recurrence solves T(n) = O(n log n)"

- **Extreme (10%):** Novel theorems, non-obvious proofs
  - "Prove or disprove: every even number > 2 is the sum of two primes"
  - "Derive a closed form for this complex recurrence relation"

**Difficulty signals:**
- Requires proof (not just answer)
- Multiple approaches must be considered
- Tool use: symbolic math (SymPy), numerical verification
- Agent must explain reasoning, not just output

---

#### 1.4 **Writing & Reasoning** (100 tasks)
Essays, explanations, creative writing, structured analysis.

- **Easy (30%):** Summaries, straightforward explanations
  - "Explain the difference between lists and tuples in Python"
  - "Write a 2-paragraph summary of X concept"

- **Medium (40%):** Multi-paragraph essays, structured arguments
  - "Write a 500-word essay: Why is documentation important in software?"
  - "Create an outline for a research paper on climate policy"

- **Hard (20%):** Nuanced arguments, counterargument handling
  - "Argue both sides: Should AI be regulated? Address the strongest counterarguments."
  - "Compare 3 design patterns; recommend one with cost/benefit analysis"

- **Extreme (10%):** Novel synthesis, creative problem-solving
  - "Design a novel teaching method for programming. Justify all choices."
  - "Write a short story (1000 words) that demonstrates 3 literary devices"

**Difficulty signals:**
- Length requirement (100 words → 2000+ words)
- Number of supporting points required (1 → 5+)
- Requires external knowledge (not provided)
- Requires style/tone matching
- Multi-criteria grading

---

#### 1.5 **Data Analysis & SQL** (100 tasks)
Query writing, data transformation, statistical analysis.

- **Easy (25%):** Simple SELECT queries
  - "Write a SQL query to get all users born after 1990"
  - "Aggregate: count rows grouped by category"

- **Medium (40%):** JOINs, aggregations, subqueries
  - "Find the top 3 customers by total spending (JOIN orders + customers)"
  - "Write a query that finds users with no orders in the last 90 days"

- **Hard (25%):** Complex window functions, recursive CTEs
  - "Write a query that ranks customers by spending, then finds the top 10%"
  - "Use a recursive CTE to find all subordinates in an org hierarchy"

- **Extreme (10%):** Query optimization, explain plans, performance tuning
  - "Optimize this query (currently 45s); prove it now runs < 1s"
  - "Design the right index strategy for this table. Justify with cost analysis."

**Difficulty signals:**
- Number of JOINs (0 → 5+)
- Use of window functions / CTEs / recursion
- Optimization required
- Tools: SQL execution, EXPLAIN ANALYZE output

---

#### 1.6 **System Design & Architecture** (100 tasks)
Design high-level systems, make architectural decisions.

- **Easy (25%):** Simple architecture choices
  - "Design a URL shortener. What data structure?"
  - "How would you structure a simple note-taking app?"

- **Medium (40%):** Trade-off analysis, multi-component design
  - "Design a rate limiter for an API. Compare 3 approaches (token bucket, sliding window, etc.)"
  - "Design a caching layer for a microservices architecture. Address consistency."

- **Hard (25%):** Large-scale systems, failure modes, optimization
  - "Design a distributed cache with replication. Handle node failures."
  - "Design a messaging system for 1M concurrent users. Justify all choices."

- **Extreme (10%):** Novel systems, hidden complexity
  - "Design a system that auto-scales ML inference workloads. Handle model versioning."
  - "Design a blockchain-like system (not crypto) that achieves X guarantees"

**Difficulty signals:**
- Number of components (1–2 → 5–7+)
- Failure mode analysis required
- Scale considerations (1K → 1B+ operations)
- Need to trade off multiple dimensions (cost, latency, consistency)

---

#### 1.7 **Multi-Step Reasoning & Planning** (100 tasks)
Tasks requiring breaking down a goal into steps, planning, and execution.

- **Easy (25%):** Simple multi-step instructions
  - "Plan a day trip. Provide a 3-step itinerary with timings."
  - "How would you test if a light bulb works? List 3 steps."

- **Medium (40%):** Conditional planning, decision trees
  - "Create a decision tree for debugging a slow database query"
  - "Plan a software migration from System A to System B. Address risks."

- **Hard (25%):** Complex plans with dependencies and iteration
  - "Design a 6-month project plan for building a microservices platform"
  - "Create a strategy to refactor a 100K-line monolith. Justify phases."

- **Extreme (10%):** Novel plans with unknown unknowns, adaptive strategies
  - "You have 3 months to launch a product in an unfamiliar market. Plan it."
  - "Design a research plan to investigate a novel hypothesis"

**Difficulty signals:**
- Number of steps (2 → 10+)
- Conditional branches / decision points
- Risk analysis required
- Interdependencies between steps
- Agent must justify ordering

---

#### 1.8 **Knowledge Integration** (100 tasks)
Tasks requiring knowledge from multiple domains.

- **Easy (25%):** Single-domain knowledge
  - "Explain Newton's Laws in simple terms"
  - "What is the capital of France?"

- **Medium (40%):** Two domains, simple integration
  - "How does the physics of a pendulum relate to timekeeping?"
  - "Compare CPUs vs GPUs for machine learning. Which is better for training?"

- **Hard (25%):** Multiple domains, non-obvious connections
  - "Design a medical device that uses ML. Address both medical and software risks."
  - "How do economic principles apply to open-source project sustainability?"

- **Extreme (10%):** Deep cross-domain synthesis
  - "Design an educational system that applies neuroscience, psychology, and pedagogy"
  - "Propose a novel approach to X that combines ideas from Y and Z fields"

**Difficulty signals:**
- Number of domains (1 → 3+)
- Depth required in each domain
- Non-obvious connections
- Tools: web search (to access domain knowledge)

---

#### 1.9 **Creative & Generative** (100 tasks)
Tasks requiring creativity, original output, style matching.

- **Easy (25%):** Simple generation with clear format
  - "Generate 5 creative names for a coffee shop"
  - "Write a haiku about programming"

- **Medium (40%):** Structured creative output
  - "Write a 10-line poem in iambic pentameter about technology"
  - "Design a fictional product marketing pitch (2 pages)"

- **Hard (25%):** Complex creative constraints
  - "Write a 500-word sci-fi short story that explores the concept of memory"
  - "Compose song lyrics with a specific rhyme scheme and theme"

- **Extreme (10%):** Artistic synthesis, novel creative forms
  - "Design a new art installation that comments on AI ethics"
  - "Create a narrative that spans multiple media (text, code, visual description)"

**Difficulty signals:**
- Creativity constraints (rhyme, meter, style)
- Length requirement
- Quality of originality (judge must evaluate novelty)
- Requires taste / aesthetic judgment

---

#### 1.10 **Tool-Using & Execution** (100 tasks)
Tasks that require agents to use tools (code execution, file I/O, web search).

- **Easy (25%):** Single tool use
  - "Execute this Python code and tell me the output: `print(sum([1,2,3]))`"
  - "Fetch the current Bitcoin price (use web search)"

- **Medium (40%):** Multiple tools, simple orchestration
  - "Download a CSV file, run analysis code, return results"
  - "Search for info about X, summarize findings"

- **Hard (25%):** Complex tool orchestration, error recovery
  - "Search for data, download it, execute custom code, validate results, retry on failure"
  - "Create a file, write code, execute it, capture output, modify based on result"

- **Extreme (10%):** Novel tool chains, handling partial failures
  - "Orchestrate 3+ tools: search → download → execute → verify → refactor"
  - "Handle an API that flakes 10% of the time; retry logic must be robust"

**Difficulty signals:**
- Number of tools (1 → 5+)
- Error handling required
- Async/concurrent tool use
- Tools not available to cheaper models

---

## 2. DIFFICULTY METRICS & DEFINITIONS

### What Makes a Task "Hard" for LLM Agents?

1. **Reasoning Depth**: Multi-step logical inference, not pattern matching
   - Easy: ≤ 1 step of reasoning
   - Medium: 2–3 steps
   - Hard: 4–6 steps
   - Extreme: 7+ steps, unknown unknowns

2. **Domain Knowledge**: Does the agent need facts/skills it doesn't have?
   - Easy: General knowledge (pre-training covers it)
   - Medium: Domain-specific but well-covered (ML, web dev, math)
   - Hard: Niche domain or recent knowledge cutoff
   - Extreme: Requires real-time data, cross-domain synthesis

3. **Tool Dependency**: How essential are tools?
   - Easy: No tools needed
   - Medium: One tool optional (code exec, search)
   - Hard: One tool required; failure if not available
   - Extreme: Multiple tools required; orchestration complexity

4. **Output Complexity**: Size and structure of output
   - Easy: < 100 tokens, simple format
   - Medium: 100–500 tokens, 1–2 formats
   - Hard: 500–2K tokens, complex structure
   - Extreme: 2K+ tokens, multi-format, must be verifiable

5. **Verification Difficulty**: How hard is it for the judge to score?
   - Easy: Objective answer (code runs, math checks out)
   - Medium: Clear rubric (meets X criteria)
   - Hard: Subjective but defensible (essay quality, design trade-offs)
   - Extreme: Requires domain expertise or novel evaluation

6. **Edge Cases & Error Handling**:
   - Easy: No edge cases
   - Medium: 1–2 obvious edge cases
   - Hard: 3–5 subtle edge cases
   - Extreme: Unknown unknowns, graceful degradation required

### Composite Difficulty Score

```
difficulty = 0.2 * reasoning_depth
           + 0.2 * domain_knowledge
           + 0.2 * tool_dependency
           + 0.2 * output_complexity
           + 0.1 * verification_difficulty
           + 0.1 * edge_case_handling

Range: 1–10
- Easy: 1–3
- Medium: 4–6
- Hard: 7–8
- Extreme: 9–10
```

---

## 3. TASK SCHEMA

```python
from enum import Enum
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

class TaskCategory(str, Enum):
    CODE_GENERATION = "code_generation"
    DEBUGGING = "debugging"
    MATH_LOGIC = "math_logic"
    WRITING_REASONING = "writing_reasoning"
    DATA_ANALYSIS = "data_analysis"
    SYSTEM_DESIGN = "system_design"
    MULTI_STEP_REASONING = "multi_step_reasoning"
    KNOWLEDGE_INTEGRATION = "knowledge_integration"
    CREATIVE = "creative"
    TOOL_USING = "tool_using"

class DifficultyLevel(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EXTREME = "extreme"

class ToolRequirement(BaseModel):
    tool_name: str  # "code_exec", "file_io", "web_search", "symbolic_math"
    required: bool  # True = task fails without it
    estimated_calls: int = 1

class Task(BaseModel):
    task_id: str = Field(..., description="Unique identifier, e.g. 'task_001_code_fib'")

    # Content
    category: TaskCategory
    title: str = Field(..., max_length=200)
    description: str = Field(..., description="Full task description, 50–500 chars")
    input: str = Field(..., description="Input data or context for the task")

    # Metadata
    difficulty_level: DifficultyLevel
    difficulty_score: float = Field(..., ge=1, le=10, description="Composite 1–10")

    # Tools & Requirements
    tool_requirements: List[ToolRequirement] = []
    max_output_tokens: int = 1000

    # Evaluation
    quality_criteria: List[str] = [
        "Correctness: Does it solve the task?",
        "Completeness: Nothing missing?",
        "Clarity: Easy to understand?",
        "Efficiency: Optimal approach?",
    ]

    # Expected Outputs (for judge calibration)
    expected_output: str = Field(..., description="Gold standard or exemplar output")
    evaluation_rubric: dict = Field(
        default={
            "correctness": {"weight": 0.4, "notes": "..."},
            "completeness": {"weight": 0.3, "notes": "..."},
            "clarity": {"weight": 0.2, "notes": "..."},
            "efficiency": {"weight": 0.1, "notes": "..."},
        }
    )

    # Cost Estimation
    estimated_judge_time_ms: int = Field(default=2000, description="Judge latency")
    estimated_judge_tokens: int = Field(default=500, description="Tokens for judging")

    # Source & Tracking
    source: str = Field(default="", description="HumanEval, custom, etc.")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    verified: bool = False  # Has this task been tested with real agents?

    # Optional: Variations
    parent_task_id: Optional[str] = None  # For task variants
    variants: List[str] = []  # Easy variant, hard variant, etc.
```

---

## 4. DIFFICULTY DISTRIBUTION (1,000 tasks)

Target allocation:

| Difficulty | Count | % | Notes |
|------------|-------|---|-------|
| Easy | 300 | 30% | Cheap models compete here; differentiation limited |
| Medium | 400 | 40% | Mid-tier models show strength |
| Hard | 250 | 25% | Premium models essential; clear separation |
| Extreme | 50 | 5% | Only top models succeed; judge must be smart |
| **Total** | **1,000** | **100%** | |

**Rationale:**
- **Easy (30%)**: Ensure we see baseline performance and cost. Most agents should pass.
- **Medium (40%)**: Sweet spot for differentiation. Most action happens here.
- **Hard (25%)**: Clear separation of cheap vs. premium agents. Prize pool effects emerge.
- **Extreme (5%)**: Edge cases, novel situations. Only very smart agents (GPT-5.4, o1) succeed. Keep small to manage cost.

**Distribution across categories:**
- Each of 10 categories gets ~100 tasks
- Within each category: 30% easy, 40% medium, 25% hard, 5% extreme

---

## 5. PRE-GENERATION VS. ON-THE-FLY

### Decision: **Hybrid Approach**

**Pre-generate 800 tasks (80%)**:
- Categories 1–8 (Code, Debugging, Math, Writing, Data, Design, Multi-Step, Knowledge)
- Reason: Consistency, reproducibility, testability, cost control
- Generate once, reuse 1,000 times
- Store in SQLite or JSON file
- Version controlled (git)

**On-the-fly generation 200 tasks (20%)**:
- Category 9 (Creative) and 10 (Tool-Using)
- Reason: Infinite variety, harder for agents to memorize/overfit
- Use template + random seed
- Example: "Describe this random concept in 3 sentences" (concept changes each run)

---

## 6. ENSURING DIFFERENTIATION (Hard → Extreme)

### Problem
Cheap models might get lucky on hard tasks if the distribution isn't right. How do we ensure separation?

### Solution: Task Design Principles

1. **Require Multiple Reasoning Steps**
   - Hard: 4+ steps, each non-obvious
   - Judge scores 0 for partial solutions (all-or-nothing)
   - Example: "Optimize algorithm X. Prove it's still correct. Show time complexity."
   - Cheap models: skip the proof, lose points

2. **Tool Use as Gating**
   - Hard tasks may require code execution
   - Judge verifies output against `actual` execution result
   - Cheap models might guess right once, but:
     - Can't iterate (if tool failures happen)
     - Can't handle edge cases (would need execution trace)

3. **Domain Knowledge Cutoff**
   - Use facts that are recent (2024+) or niche
   - Example: "Explain how diffusion models improve over GANs"
   - Cheap models have shallower knowledge

4. **Subjective Criteria with Clear Rubric**
   - For writing/design tasks, use **specific** criteria, not "is it good?"
   - Rubric: "Address all 5 stated constraints. Justify trade-offs."
   - Expensive judges (GPT-5.4-mini or gpt-5.4) grade fairly; cheap judges (nano) may miss nuance

5. **Composite Tasks**
   - Easy: "Write code"
   - Hard: "Write code + explain time complexity + handle 3 edge cases + propose optimization"
   - Cheap models succeed at #1, fail #2–4

### Example Task Progression

**Easy (Same Base):**
```
Input: "Write a function that checks if a string is a palindrome"
Expected: 20-line function
Score: Check if code runs, test on 2 examples
```

**Medium (Harder):**
```
Input: "Write an optimized function that checks if a string is a palindrome (case-insensitive).
        Handle non-alphabetic characters. Justify your approach."
Expected: ~30-line function + explanation
Score: Correctness (60%), efficiency (20%), explanation (20%)
```

**Hard (Multiple Criteria):**
```
Input: "Implement an O(n) palindrome checker using two-pointer technique.
        Handle unicode characters. Explain space/time trade-offs.
        Provide unit tests for 5 edge cases."
Expected: Implementation + explanation + tests
Score: Correctness (40%), efficiency (30%), tests (20%), explanation (10%)
Judge: Must execute code to verify correctness
```

---

## 7. JUDGE SPECIFICATION

### Single Judge Model for All Tasks?
**No.** Use tiered judging:

1. **Gpt-5.4-nano (default)**: 80% of tasks
   - Easy, Medium, straightforward Hard
   - Fast (1–2s), cheap ($0.0001–0.0005)
   - Criteria: correctness, completeness, clarity

2. **Gpt-5.4-mini (optional upgrade)**: 15% of tasks
   - Complex Hard, all Extreme
   - Slower (3–5s), moderate cost ($0.0005–0.002)
   - Criteria: includes edge case handling, efficiency analysis

3. **gpt-4.1 (premium)**: 5% of tasks
   - Extreme tasks requiring deep reasoning
   - Expensive ($0.003–0.01), slow
   - For research-grade evaluation

**Buyer Control**: Allow `judge_model` override in `CallRequest`
```python
call = CallRequest(
    input="...",
    max_price=0.10,
    judge_model="gpt-5.4-mini",  # Upgrade judge for this task
    ...
)
```

### Judge Calibration
Before running 1,000 tasks, sample:
- 10 easy tasks → judge should score 8–10
- 10 medium tasks → judge should score 4–7
- 10 hard tasks → judge should score 2–6
- 5 extreme tasks → judge should score 1–4

Sanity check: expensive agents score higher on hard tasks.

---

## 8. COST ESTIMATION (1,000 tasks × 3 agents)

### Assumptions
- **3 agents**: cheap (mini), mid (4.1-mini), premium (4.1)
- **Average task cost**: $0.001–0.010 (agent) + $0.0005–0.003 (judge)
- **Tool usage**: Code exec adds ~$0.0001 per call

### Breakdown

| Task Type | Count | Agent Cost | Judge Cost | Total |
|-----------|-------|-----------|-----------|-------|
| Easy | 300 | $0.30 | $0.15 | $0.45 |
| Medium | 400 | $0.40 | $0.20 | $0.60 |
| Hard | 250 | $0.50 | $0.38 | $0.88 |
| Extreme | 50 | $0.25 | $0.15 | $0.40 |
| **Total** | **1,000** | **$1.45** | **$0.88** | **$2.33** |

**Per-agent costs** (3 agents × 1,000 tasks):
- Cheap agent: $0.30 (easy) + $0.40 (medium) + $0.20 (hard) + $0.05 (extreme) = ~$1.00
- Mid agent: $0.45 (easy) + $0.60 (medium) + $0.50 (hard) + $0.15 (extreme) = ~$1.70
- Premium agent: $0.60 (easy) + $0.80 (medium) + $0.75 (hard) + $0.25 (extreme) = ~$2.40

**Total simulation cost**: ~$2.33 + $1.00 + $1.70 + $2.40 = **~$7.43 USD**

---

## 9. TASK GENERATION PIPELINE

### Phase 1: Pre-generate 800 Tasks (1-2 weeks)
1. **Categories 1–8**: Use templates + manual curation
   - HumanEval for Code (100 tasks)
   - Custom generation for Debugging (100 tasks)
   - Symbolic math + MATH dataset for Math (100 tasks)
   - Writing templates for Writing (100 tasks)
   - SQL templates + real DB schema for Data (100 tasks)
   - System design prompts for Design (100 tasks)
   - Planning tree templates for Multi-Step (100 tasks)
   - Fact-checking + synthesis for Knowledge (100 tasks)

2. **Store in SQLite**
   ```
   CREATE TABLE tasks (
       task_id TEXT PRIMARY KEY,
       category TEXT,
       difficulty_level TEXT,
       difficulty_score REAL,
       input TEXT,
       expected_output TEXT,
       quality_criteria JSON,
       tool_requirements JSON,
       created_at TIMESTAMP
   );
   ```

3. **Verify**: Run 3 agents on sample (10 tasks per difficulty) → sanity check judge

### Phase 2: On-the-fly Generation (200 tasks)
1. **Creative**: Use GPT-4 template + seed to generate variants
2. **Tool-Using**: Randomize API endpoints, data sources, error injection

---

## 10. HANDLING ALL-AGENT FAILURE

### Problem
What if no agent meets `min_quality` threshold on a task?

### Solution

**Option A: Relax Criteria**
- Buyer sets `min_quality = 5` instead of 6
- Auto-trigger if no submission within 30s of first qualifying attempt
- Trade: Lower expected quality, but order gets filled

**Option B: Use Second-Best Agent**
- Judge all submissions
- Pick highest-scoring agent even if score < min_quality
- Log this as "degraded completion"
- Buyer charged reduced fee (e.g., 50% discount)

**Option C: Refund**
- Task times out
- No winner declared
- Buyer refunded (no charge, no transaction)
- Good for rare cases (truly unsolvable task)

**Recommended**: Option A
- Auto-degrade `min_quality` by 1 after 45s
- Ensures marketplace keeps moving
- Agents still compete (cheaper still cheaper)

---

## SUMMARY: KEY DESIGN DECISIONS

| Decision | Choice | Rationale |
|----------|--------|-----------|
| # Categories | 10 | Breadth + depth; covers agent capabilities |
| Difficulty Distribution | 30/40/25/5 | 30% easy for baseline, 40% medium for main competition, 25% hard for separation, 5% extreme for edge |
| Pre-gen vs. On-the-fly | 80/20 | Reproducibility + variety |
| Judge Tiers | nano (80%), mini (15%), 4.1 (5%) | Cost control + quality for hard tasks |
| Task Schema | Pydantic BaseModel | Type-safe, versionable, JSON serializable |
| Failure Handling | Auto-degrade min_quality | Marketplace keeps moving |
| Cost Estimate | ~$7.43 total | Acceptable for research simulation |

---

## NEXT STEPS

1. **Implement task schema** (types.py)
2. **Generate 100-task sample** across all categories
3. **Run 1-task test** with each agent → calibrate judge
4. **Generate 800 remaining tasks** using templates
5. **Run 10-task pilot** → verify differentiation
6. **Execute full 1,000-task simulation** with monitoring
