"""
LLM Agent Simulation Task Bank
~4,000 tasks across 20 categories with difficulty distribution.
Deterministically generated with seeded randomness for reproducibility.
"""

from dataclasses import dataclass, field
import random


@dataclass
class Task:
    task_id: str
    category: str
    difficulty: str  # "easy" | "medium" | "hard" | "extreme"
    input: str
    max_price: float
    min_quality: int
    timeout: float = 30.0
    quality_criteria: list[str] = field(default_factory=list)
    expected_tools: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


# ── Difficulty pricing tiers ──────────────────────────────────────────

DIFFICULTY_CONFIG = {
    "easy":    {"max_price": 0.02, "min_quality": 5, "timeout": 15.0},
    "medium":  {"max_price": 0.05, "min_quality": 6, "timeout": 25.0},
    "hard":    {"max_price": 0.15, "min_quality": 7, "timeout": 40.0},
    "extreme": {"max_price": 0.35, "min_quality": 8, "timeout": 60.0},
}

# ── Category definitions ──────────────────────────────────────────────
# Each category: {difficulty: [list of prompt templates]}
# Templates can use {var} placeholders filled by variant generators.

CATEGORIES = {
    # ================================================================
    # 1. CODE GENERATION
    # ================================================================
    "code_generation": {
        "criteria": [
            "Code is syntactically correct",
            "Function solves the stated problem",
            "Includes docstring or comments",
        ],
        "tools": ["execute_python"],
        "easy": [
            "Write a Python function that reverses a string",
            "Write a Python function that checks if a string is a palindrome",
            "Write a Python function that returns True if a number is even",
            "Write a Python function that returns the sum of integers from 1 to n",
            "Write a Python function that filters a list to keep only even numbers",
            "Write a Python function that calculates n factorial",
            "Write a Python function that counts vowels in a string",
            "Write a Python function that capitalizes the first letter of each word",
            "Write a Python function that reverses a list in-place",
            "Write a Python function that finds the maximum value in a list without using max()",
            "Write a Python function that removes duplicates from a list while preserving order",
            "Write a Python function that checks if two strings are anagrams",
            "Write a Python function that converts Celsius to Fahrenheit",
            "Write a Python function that counts words in a sentence",
            "Write a Python function that flattens a nested list one level deep",
            "Write a Python function that checks if a number is prime",
            "Write a Python function that returns the nth Fibonacci number",
            "Write a Python function that merges two sorted lists into one sorted list",
            "Write a Python function that finds the second largest element in a list",
            "Write a Python function that rotates a list by k positions",
        ],
        "medium": [
            "Implement merge sort in Python",
            "Implement binary search for a sorted list",
            "Implement a simple hash table class with get/set/delete",
            "Implement a singly linked list with insert/delete/search",
            "Write a function that finds the longest substring without repeating characters",
            "Write a function that computes LCM of two numbers",
            "Write a function that transposes a 2D matrix",
            "Write a function that generates all permutations of a string",
            "Implement a stack using two queues",
            "Write a function that validates balanced parentheses including {}, [], ()",
            "Write a Python decorator that caches function results (memoization)",
            "Implement a priority queue using a min-heap",
            "Write a function that finds all prime factors of a number",
            "Implement depth-first search on a graph represented as an adjacency list",
            "Write a function that converts a Roman numeral string to an integer",
            "Implement a basic LRU cache with O(1) get and put",
            "Write a function that computes the edit distance between two strings",
            "Implement quicksort with random pivot selection",
            "Write a function that serializes and deserializes a binary tree",
            "Implement a circular buffer (ring buffer) class",
        ],
        "hard": [
            "Implement a self-balancing AVL tree with insertion and deletion",
            "Implement breadth-first search on a graph, handling cycles and disconnected components",
            "Solve the coin change problem using dynamic programming, returning both count and coins used",
            "Implement topological sorting for a DAG with cycle detection",
            "Implement the 0/1 knapsack problem with backtracking and memoization",
            "Implement a trie data structure with insert, search, delete, and prefix matching",
            "Build a suffix array for pattern matching",
            "Implement Dijkstra's shortest path algorithm with a priority queue",
            "Write a function that solves N-Queens and returns all valid board configurations",
            "Implement a red-black tree with insert and delete operations",
        ],
        "extreme": [
            "Implement a concurrent skip list with lock-free operations in Python",
            "Implement a B+ tree database index with range queries",
            "Build a consistent hashing ring for distributed key-value storage",
            "Implement Ukkonen's algorithm for online suffix tree construction",
            "Create a parser and evaluator for a simple expression language with variables, functions, and control flow",
        ],
    },

    # ================================================================
    # 2. DEBUGGING
    # ================================================================
    "debugging": {
        "criteria": [
            "Bug is correctly identified",
            "Fix resolves the root cause, not just the symptom",
            "Explanation of what was wrong is clear",
        ],
        "tools": ["execute_python"],
        "easy": [
            "Fix this function — it should return the sum but adds an extra 1:\ndef add(a, b):\n    return a + b + 1",
            "Fix this function — it's supposed to check if x is strictly positive:\ndef is_positive(x):\n    return x > 0 or x == 0",
            "Fix this function — it should reverse a string:\ndef reverse(s):\n    return s[1:]",
            "Fix this function — it should check if a number is even:\ndef is_even(n):\n    return n % 2 == 1",
            "Fix this function — it should return the average of a list:\ndef average(lst):\n    return sum(lst) / len(lst) + 1",
            "Fix this function — it should count occurrences of char in string:\ndef count_char(s, c):\n    return s.count(c) - 1",
            "Fix this function — it should return the last element:\ndef last(lst):\n    return lst[len(lst)]",
            "Fix this function — it should join strings with a separator:\ndef join(parts, sep):\n    return sep.join(parts) + sep",
            "Fix this function — it should return the absolute value:\ndef absolute(x):\n    if x < 0:\n        return x\n    return x",
            "Fix this function — it should check if a list is sorted:\ndef is_sorted(lst):\n    for i in range(len(lst)):\n        if lst[i] > lst[i+1]:\n            return False\n    return True",
            "Fix this function — it should compute the power:\ndef power(base, exp):\n    result = 0\n    for _ in range(exp):\n        result *= base\n    return result",
            "Fix this function — it should flatten a list:\ndef flatten(lst):\n    result = []\n    for item in lst:\n        if isinstance(item, list):\n            result.append(item)\n        else:\n            result.append(item)\n    return result",
        ],
        "medium": [
            "Debug this binary search — it goes into an infinite loop on certain inputs:\ndef binary_search(arr, target):\n    lo, hi = 0, len(arr)\n    while lo < hi:\n        mid = (lo + hi) // 2\n        if arr[mid] == target:\n            return mid\n        elif arr[mid] < target:\n            lo = mid\n        else:\n            hi = mid\n    return -1",
            "Debug this merge sort — it produces wrong results:\ndef merge_sort(arr):\n    if len(arr) <= 1:\n        return arr\n    mid = len(arr) // 2\n    left = merge_sort(arr[:mid])\n    right = merge_sort(arr[mid:])\n    result = []\n    i = j = 0\n    while i < len(left) and j < len(right):\n        if left[i] < right[j]:\n            result.append(left[i])\n            i += 1\n        else:\n            result.append(right[j])\n            j += 1\n    return result",
            "Debug this function — it should find duplicates but misses some:\ndef find_duplicates(lst):\n    seen = set()\n    dupes = set()\n    for item in lst:\n        if item in seen:\n            dupes.add(item)\n        seen.add(item)\n    return list(dupes)\n\n# Expected: find_duplicates([1,2,3,2,4,3]) should return [2,3]\n# Actual: sometimes returns empty list",
            "Debug this linked list — delete_node doesn't work for the head:\nclass Node:\n    def __init__(self, val, next=None):\n        self.val = val\n        self.next = next\n\ndef delete_node(head, val):\n    curr = head\n    while curr.next:\n        if curr.next.val == val:\n            curr.next = curr.next.next\n            return head\n        curr = curr.next\n    return head",
            "Debug this recursive function — it causes a stack overflow on valid inputs:\ndef flatten_deep(lst):\n    result = []\n    for item in lst:\n        if isinstance(item, (list, tuple)):\n            result.extend(flatten_deep(item))\n        else:\n            result.append(item)\n    return flatten_deep(result)",
            "Debug this function — it should remove all whitespace but breaks on empty strings:\ndef clean(s):\n    return ''.join(s.split())\n\n# Works on normal strings, raises an exception on None",
            "Debug this memoized fibonacci — it's slower than expected:\ndef fib(n, memo={}):\n    if n in memo:\n        return memo[n]\n    if n <= 1:\n        return n\n    result = fib(n-1) + fib(n-2)\n    memo[n] = result\n    return result",
            "Debug this function — it should return the mode of a list:\ndef mode(lst):\n    from collections import Counter\n    counts = Counter(lst)\n    max_count = max(counts.values)\n    return [k for k, v in counts.items() if v == max_count]",
        ],
        "hard": [
            "Debug this async web scraper — it deadlocks when more than 5 URLs are provided:\n```python\nimport asyncio, aiohttp\n\nasync def fetch_all(urls):\n    sem = asyncio.Semaphore(5)\n    async with aiohttp.ClientSession() as session:\n        tasks = [fetch(session, url, sem) for url in urls]\n        return await asyncio.gather(*tasks)\n\nasync def fetch(session, url, sem):\n    async with sem:\n        async with session.get(url) as resp:\n            return await resp.text()\n```",
            "Debug this thread pool — tasks sometimes get lost:\n```python\nimport threading, queue\n\nclass ThreadPool:\n    def __init__(self, size=4):\n        self.q = queue.Queue()\n        self.workers = []\n        for _ in range(size):\n            t = threading.Thread(target=self._worker, daemon=True)\n            t.start()\n            self.workers.append(t)\n\n    def _worker(self):\n        while True:\n            fn, args = self.q.get()\n            fn(*args)\n\n    def submit(self, fn, *args):\n        self.q.put((fn, args))\n```",
            "Debug this LRU cache — eviction doesn't work correctly:\n```python\nfrom collections import OrderedDict\n\nclass LRUCache:\n    def __init__(self, cap):\n        self.cap = cap\n        self.cache = OrderedDict()\n\n    def get(self, key):\n        if key in self.cache:\n            self.cache.move_to_end(key)\n            return self.cache[key]\n        return -1\n\n    def put(self, key, val):\n        self.cache[key] = val\n        if len(self.cache) > self.cap:\n            self.cache.popitem(last=True)\n```",
            "Debug this rate limiter — it allows bursts beyond the limit:\n```python\nimport time\n\nclass RateLimiter:\n    def __init__(self, max_calls, period):\n        self.max_calls = max_calls\n        self.period = period\n        self.calls = []\n\n    def allow(self):\n        now = time.time()\n        self.calls = [t for t in self.calls if now - t < self.period]\n        if len(self.calls) < self.max_calls:\n            self.calls.append(now)\n            return True\n        return False\n```",
            "Debug this event emitter — removing listeners during emit causes skipped callbacks:\n```python\nclass EventEmitter:\n    def __init__(self):\n        self.listeners = {}\n\n    def on(self, event, fn):\n        self.listeners.setdefault(event, []).append(fn)\n\n    def off(self, event, fn):\n        if event in self.listeners:\n            self.listeners[event].remove(fn)\n\n    def emit(self, event, *args):\n        for fn in self.listeners.get(event, []):\n            fn(*args)\n```",
        ],
        "extreme": [
            "Debug this distributed lock implementation — it has a race condition that allows two clients to hold the lock simultaneously:\n```python\nimport redis, time, uuid\n\nclass DistributedLock:\n    def __init__(self, client, name, ttl=10):\n        self.client = client\n        self.name = f'lock:{name}'\n        self.ttl = ttl\n        self.token = str(uuid.uuid4())\n\n    def acquire(self):\n        while True:\n            if self.client.setnx(self.name, self.token):\n                self.client.expire(self.name, self.ttl)\n                return True\n            time.sleep(0.1)\n\n    def release(self):\n        if self.client.get(self.name) == self.token:\n            self.client.delete(self.name)\n```",
            "Debug this CRDT implementation — convergence fails when concurrent operations have identical timestamps:\n```python\nclass LWWRegister:\n    def __init__(self):\n        self.value = None\n        self.timestamp = 0\n\n    def set(self, value, ts):\n        if ts >= self.timestamp:\n            self.value = value\n            self.timestamp = ts\n\n    def merge(self, other):\n        if other.timestamp > self.timestamp:\n            self.value = other.value\n            self.timestamp = other.timestamp\n```",
        ],
    },

    # ================================================================
    # 3. MATH & REASONING
    # ================================================================
    "math_reasoning": {
        "criteria": [
            "Answer is mathematically correct",
            "Steps/reasoning are shown",
            "Edge cases considered",
        ],
        "tools": ["math_eval"],
        "easy": [
            "What is the sum of the first 100 positive integers?",
            "If a rectangle has length 12 and width 8, what is its area and perimeter?",
            "Convert 72 degrees Fahrenheit to Celsius",
            "What is 15% of 240?",
            "How many seconds are in a week?",
            "If you drive 180 miles in 3 hours, what is your average speed in mph?",
            "What is the GCD of 48 and 36?",
            "Calculate 2^10 without a calculator",
            "A pizza is cut into 8 slices. If you eat 3, what fraction remains?",
            "What is the area of a circle with radius 7? Use pi = 3.14159",
            "If 5 workers can paint a house in 8 hours, how long would 4 workers take?",
            "What is the next number in the sequence: 2, 6, 18, 54, ...?",
            "Convert the binary number 11010110 to decimal",
            "Calculate the simple interest on $5000 at 4% for 3 years",
            "What is the median of: 7, 3, 9, 1, 5, 11, 8?",
        ],
        "medium": [
            "Prove that the sum of the first n odd numbers equals n²",
            "A ball is thrown upward at 20 m/s from the ground. When does it reach maximum height? How high does it go? (g=9.8 m/s²)",
            "Find all integer solutions to 3x + 5y = 47 where x,y > 0",
            "What is the probability of getting at least one 6 when rolling two dice?",
            "Calculate the compound interest on $10,000 at 5% annual rate, compounded monthly, after 3 years",
            "How many ways can you arrange the letters in the word 'MISSISSIPPI'?",
            "Solve the system: 2x + 3y = 13 and 5x - 2y = 4",
            "A bag contains 5 red, 3 blue, and 2 green balls. What is the probability of drawing 2 red balls without replacement?",
            "Find the derivative of f(x) = x³ ln(x)",
            "What is the expected number of coin flips to get 3 heads in a row?",
            "Calculate the volume of a cone with radius 5 and height 12",
            "Compute the integral of x*e^x from 0 to 1",
        ],
        "hard": [
            "Prove that √2 is irrational using proof by contradiction",
            "Find the eigenvalues and eigenvectors of the matrix [[3,1],[1,3]]",
            "Using the method of Lagrange multipliers, find the maximum of f(x,y) = xy subject to x + y = 10",
            "Prove that there are infinitely many prime numbers (Euclid's proof)",
            "Solve the recurrence relation T(n) = 2T(n/2) + n with T(1) = 1. What is its asymptotic complexity?",
            "Calculate the probability that a random 5-card poker hand is a full house",
            "Find the closed-form solution for the Fibonacci sequence using the characteristic equation method",
            "Prove that the set of rational numbers is countable",
        ],
        "extreme": [
            "Prove that e is irrational using the series expansion",
            "Prove the Cauchy-Schwarz inequality for vectors in R^n",
            "Derive the Black-Scholes option pricing formula from first principles, starting with geometric Brownian motion",
            "Prove that the halting problem is undecidable using diagonalization",
        ],
    },

    # ================================================================
    # 4. WRITING & COMMUNICATION
    # ================================================================
    "writing": {
        "criteria": [
            "Writing is clear and well-structured",
            "Tone is appropriate for the audience",
            "Content is accurate and complete",
        ],
        "tools": [],
        "easy": [
            "Write a professional email declining a meeting invitation due to a scheduling conflict",
            "Write a 3-sentence product description for a wireless Bluetooth speaker",
            "Write a polite Slack message asking a coworker to review your pull request",
            "Write a one-paragraph summary of what version control (git) is for a non-technical audience",
            "Write a brief out-of-office auto-reply message for a 2-week vacation",
            "Write a friendly welcome message for a new team member joining your engineering team",
            "Write a short social media post announcing a new feature launch",
            "Write a clear commit message for a bug fix that resolved a null pointer exception in the login flow",
            "Write a one-paragraph bio for a software engineer's conference talk",
            "Write a polite rejection email for a job applicant who made it to the final round",
            "Summarize the key points of a meeting about migrating from AWS to GCP in 5 bullet points",
            "Write a brief changelog entry for version 2.3.1 that fixed a performance regression",
        ],
        "medium": [
            "Write a technical blog post (300-500 words) explaining how database indexing works and when to use it",
            "Write an incident postmortem for a 2-hour production outage caused by a database migration that locked a critical table",
            "Write a design document introduction for a new caching layer in a microservices architecture",
            "Write a performance review self-assessment paragraph highlighting contributions to a major product launch",
            "Write an RFC (Request for Comments) summary proposing the migration from REST to GraphQL for the public API",
            "Write a clear user guide section explaining how to set up two-factor authentication",
            "Write a persuasive proposal (200-300 words) for adopting TypeScript in an existing JavaScript codebase",
            "Write detailed release notes for a mobile app update that includes new offline mode, bug fixes, and UI improvements",
            "Write a runbook for responding to a 'database connection pool exhausted' alert",
            "Write a comparison table and recommendation between PostgreSQL and MongoDB for a social media application",
        ],
        "hard": [
            "Write a comprehensive architecture decision record (ADR) for choosing event-driven architecture over request-response for an order processing system",
            "Write a detailed technical specification for implementing real-time collaborative editing (like Google Docs) including conflict resolution strategy",
            "Write a thorough security review document for a new authentication system that uses JWT tokens with refresh token rotation",
            "Write a migration guide for moving from a monolithic Rails application to microservices, covering the strangler fig pattern",
            "Write a complete on-call handoff document for a critical payment processing service including known issues, dashboards, and escalation procedures",
        ],
        "extreme": [
            "Write a complete technical whitepaper (1000+ words) on implementing zero-downtime deployments for stateful services in Kubernetes",
            "Write a comprehensive disaster recovery plan for a multi-region SaaS platform including RPO/RTO targets, failover procedures, and testing protocols",
        ],
    },

    # ================================================================
    # 5. DATA ANALYSIS
    # ================================================================
    "data_analysis": {
        "criteria": [
            "Analysis is methodologically sound",
            "Conclusions are supported by the data",
            "Results are clearly presented",
        ],
        "tools": ["execute_python"],
        "easy": [
            "Given the list [23, 45, 12, 67, 34, 89, 56, 78, 90, 11], calculate mean, median, mode, and standard deviation",
            "Parse this CSV data and find the total revenue:\nProduct,Price,Quantity\nWidget,10.50,100\nGadget,25.00,50\nDoohickey,5.75,200",
            "Count the frequency of each word in: 'the cat sat on the mat the cat ate the rat'",
            "Given daily temperatures [72,75,68,80,77,73,69,82,78,74], identify the warmest and coolest days and the range",
            "Calculate the moving average (window=3) for: [10, 20, 30, 40, 50, 60, 70]",
            "Given test scores [85,92,78,95,88,76,90,83,97,71], calculate the percentage of students who scored above 80",
            "Find the correlation between hours studied [2,3,5,6,8] and test scores [65,70,80,85,95]",
            "Parse this log line and extract the timestamp, level, and message: '2024-01-15T10:30:45Z ERROR Database connection timeout after 30s'",
            "Convert these temperatures from Fahrenheit to Celsius and find the average: [98.6, 100.4, 97.7, 99.1, 101.3]",
            "Calculate the ROI: initial investment $10,000, final value $13,500 after 2 years",
        ],
        "medium": [
            "Write a Python script that reads a JSON array of user objects with 'name', 'age', 'city' fields, groups users by city, and computes average age per city",
            "Analyze this A/B test: Control group (n=1000, conversions=50), Treatment group (n=1000, conversions=65). Is the difference statistically significant at p<0.05?",
            "Write code to detect outliers in a dataset using the IQR method. Apply it to: [12, 15, 14, 10, 102, 13, 16, 11, 15, 14, 200, 13]",
            "Implement a function that computes a frequency histogram from a list of values and prints an ASCII bar chart",
            "Given two time series of stock prices over 10 days, calculate their correlation coefficient and determine if they tend to move together",
            "Write a function that performs simple linear regression (y = mx + b) from scratch and returns the slope, intercept, and R² value",
            "Analyze server response times from this data and identify if there's a performance degradation trend: [120, 125, 118, 130, 145, 160, 155, 180, 190, 210] (in ms)",
            "Write code to compute a confusion matrix from predicted and actual labels, then calculate precision, recall, and F1 score",
            "Implement k-means clustering from scratch for 2D points and cluster these: [(1,2),(2,1),(1,1),(8,8),(9,7),(8,9),(5,5),(4,6)]",
            "Parse Apache access logs and produce a report: top 5 most requested URLs, requests per hour, and error rate (4xx/5xx)",
        ],
        "hard": [
            "Implement a complete time series forecasting pipeline: load data, check stationarity (ADF test), fit ARIMA, and forecast the next 5 periods. Test with seasonal data.",
            "Write a market basket analysis tool that computes association rules (support, confidence, lift) from transaction data",
            "Build a simple recommendation engine using collaborative filtering (user-user similarity) from a ratings matrix",
            "Implement principal component analysis (PCA) from scratch using eigendecomposition on a dataset with 5+ features",
            "Write a complete ETL pipeline that reads messy CSV data, cleans it (handle missing values, outliers, type coercion), normalizes it, and outputs a clean dataset with a quality report",
        ],
        "extreme": [
            "Implement a Bayesian A/B testing framework that computes posterior distributions, credible intervals, and expected loss for deciding between variants",
            "Build a complete anomaly detection system using Isolation Forest from scratch, including training, scoring, threshold selection, and visualization of detected anomalies",
        ],
    },

    # ================================================================
    # 6. SYSTEM DESIGN
    # ================================================================
    "system_design": {
        "criteria": [
            "Design addresses scalability requirements",
            "Trade-offs are clearly articulated",
            "Components and their interactions are well-defined",
        ],
        "tools": [],
        "easy": [
            "Design a simple URL shortener. What components do you need? How would you store the mappings?",
            "Design a basic rate limiter for an API. What algorithm would you use?",
            "Explain how you would design a simple key-value cache with TTL expiration",
            "Design a basic task queue system. How do producers and consumers interact?",
            "Design a simple logging service that can ingest logs from multiple microservices",
            "How would you design a basic pub/sub messaging system?",
            "Design a simple feature flag system for a web application",
            "How would you design a basic health check system for monitoring multiple services?",
            "Design a simple session store for a web application. How would you handle expiration?",
            "Design a basic webhook delivery system with retry logic",
        ],
        "medium": [
            "Design a notification system that supports email, SMS, and push notifications with user preferences and delivery guarantees",
            "Design a distributed job scheduler that can handle millions of scheduled tasks with at-least-once execution guarantees",
            "Design a real-time leaderboard system for a game with millions of players, supporting both global and friend rankings",
            "Design a file storage service like Dropbox. How would you handle syncing, versioning, and conflict resolution?",
            "Design an API gateway that handles authentication, rate limiting, request routing, and circuit breaking",
            "Design a search autocomplete system that serves suggestions in under 100ms for a dictionary of 10 million terms",
            "Design a metrics collection and alerting system (like a simple Datadog) for monitoring microservices",
            "Design a collaborative document editing system with real-time updates for up to 50 concurrent editors",
        ],
        "hard": [
            "Design a distributed message queue like Kafka. Cover partitioning, replication, consumer groups, and exactly-once delivery semantics",
            "Design a global content delivery network (CDN). How would you handle cache invalidation, origin shielding, and geographic routing?",
            "Design a multi-tenant SaaS platform with data isolation, per-tenant rate limiting, and a shared microservices backend",
            "Design a real-time fraud detection system for credit card transactions processing 10,000 TPS with sub-100ms latency",
            "Design a distributed database that supports both OLTP and OLAP workloads (HTAP). How do you handle isolation between workload types?",
        ],
        "extreme": [
            "Design a complete stock exchange matching engine. Cover order types, matching algorithms, market data distribution, fault tolerance, and regulatory compliance",
            "Design a globally distributed, strongly consistent database (like Spanner). Cover TrueTime, Paxos, schema changes, and cross-region transactions",
        ],
    },

    # ================================================================
    # 7. MULTI-STEP REASONING
    # ================================================================
    "multi_step": {
        "criteria": [
            "Each step logically follows from the previous",
            "Final answer is correct",
            "Intermediate reasoning is shown",
        ],
        "tools": ["math_eval", "execute_python"],
        "easy": [
            "A store has a 20% off sale. An item originally costs $80. With a $10 coupon applied after the discount, what's the final price?",
            "You have 3 red, 4 blue, and 5 green marbles. You remove 2 red and 1 green. What fraction of remaining marbles are blue?",
            "A recipe for 4 servings needs 2 cups flour, 1.5 cups sugar, 3 eggs. Scale it to 10 servings.",
            "A train leaves City A at 9am going 60mph. Another leaves City B (300 miles away) at 10am going 80mph toward City A. When do they meet?",
            "You earn $4,500/month. Rent is 30%, food is 15%, savings is 20%. How much is left for other expenses?",
            "A rectangular garden is 12m x 8m. A path 1.5m wide goes around the outside. What is the area of the path?",
            "If you invest $1,000 with 5% annual return compounded yearly, how much do you have after 10 years?",
            "A car gets 30 mpg in city and 40 mpg highway. If you drive 120 miles city and 200 miles highway, how many gallons do you use?",
            "Three friends split a $150 dinner. Alice ate $45, Bob ate $55, Carol ate $50. They want to split the 20% tip proportionally. How much does each person pay total?",
            "Convert 3 hours, 45 minutes, 30 seconds into total seconds, then back to hours as a decimal",
        ],
        "medium": [
            "Plan a road trip: 3 cities, 250 miles apart. Car gets 28 mpg, gas costs $3.50/gal. Hotel is $120/night. Food is $50/day. You stay 2 nights per city. What's the total trip cost?",
            "A company has 100 employees. 60% are engineers, 25% are product, 15% are operations. Engineers average $150k, product $130k, ops $110k. What's total payroll? If they give engineers a 10% raise, what's the new total?",
            "You're planning a software release. There are 5 tasks with dependencies: A (3 days, no deps), B (2 days, depends on A), C (4 days, no deps), D (1 day, depends on B and C), E (2 days, depends on D). What's the critical path and minimum time?",
            "An e-commerce site has 10,000 daily visitors. 5% add to cart, 40% of those checkout, average order is $75. What's daily revenue? If A/B test improves add-to-cart to 6%, what's the revenue increase?",
            "A database query scans 1 million rows at 10,000 rows/sec. Adding an index reduces it to 1,000 rows but adds 50ms overhead. Which is faster? At what row count does the index break even?",
            "A startup has $500k runway. They spend $50k/month. They plan to hire 2 people at $8k/month each starting month 3. When do they run out of money? If they get $200k funding at month 4, when?",
            "Calculate the optimal pricing for a SaaS product: demand function Q = 1000 - 20P, fixed cost = $5000/month, variable cost = $5/customer. Find price that maximizes profit.",
            "Design a capacity plan: current system handles 1000 req/sec. Traffic grows 15%/month. Each server handles 200 req/sec and costs $500/month. Plan for 12 months. When do you need to add servers and what's the total annual cost?",
        ],
        "hard": [
            "Model a simple economy: 3 goods (food, shelter, entertainment), 2 agents (worker, entrepreneur). Worker earns $100/day, entrepreneur earns $200/day but pays $50/day in costs. Food costs $20, shelter $40, entertainment $15. Each agent allocates budget proportionally to utility weights. Worker: food=0.4, shelter=0.4, ent=0.2. Entrepreneur: food=0.3, shelter=0.3, ent=0.4. Calculate equilibrium demand for each good.",
            "Design an optimal caching strategy: you have 3 cache tiers (L1: 100 items, 1ms, L2: 1000 items, 10ms, L3: 10000 items, 100ms, DB: unlimited, 500ms). Access pattern follows Zipf distribution (80/20 rule). Calculate expected average latency and hit rates per tier.",
            "Analyze a network reliability problem: 5 nodes, 7 edges with given failure probabilities. Calculate the probability that node A can still reach node E. Consider all possible failure combinations for the shortest path.",
            "Solve this scheduling problem: 8 tasks with varying durations, 3 machines, some tasks have precedence constraints and resource requirements. Find the makespan-optimal schedule using a greedy heuristic.",
        ],
        "extreme": [
            "Model a complete supply chain optimization: 3 warehouses, 5 stores, 10 products. Each warehouse has capacity constraints and storage costs. Transportation costs vary by route. Demand at each store is stochastic. Formulate as a linear program, solve it, and analyze sensitivity of the solution to demand changes.",
            "Design and simulate a complete auction mechanism: multiple bidders with private valuations drawn from known distributions. Implement first-price, second-price, and English auction. Calculate expected revenue, bidder surplus, and efficiency for each. Prove which mechanism maximizes seller revenue.",
        ],
    },

    # ================================================================
    # 8. KNOWLEDGE & TRIVIA
    # ================================================================
    "knowledge": {
        "criteria": [
            "Information is factually accurate",
            "Explanation is clear and accessible",
            "Key nuances are captured",
        ],
        "tools": [],
        "easy": [
            "What is the difference between HTTP and HTTPS?",
            "Explain what a DNS server does in simple terms",
            "What are the SOLID principles in software engineering? List them briefly.",
            "What is the difference between a stack and a queue?",
            "Explain what Big O notation means and give examples of O(1), O(n), and O(n²)",
            "What is the difference between TCP and UDP? When would you use each?",
            "What is a REST API? What makes an API RESTful?",
            "Explain the difference between SQL and NoSQL databases",
            "What is a Docker container and how is it different from a virtual machine?",
            "What is CORS and why does it exist?",
            "Explain what a load balancer does and name two common algorithms",
            "What is the CAP theorem? Explain each letter.",
            "What is the difference between authentication and authorization?",
            "Explain what a hash function is and give a practical use case",
            "What is the difference between compiled and interpreted languages?",
        ],
        "medium": [
            "Explain how HTTPS/TLS handshake works step by step",
            "Compare and contrast microservices vs monolithic architecture with pros and cons of each",
            "Explain how a garbage collector works. Compare mark-and-sweep with reference counting.",
            "How does a B-tree index work in a database? Why is it preferred over a hash index for range queries?",
            "Explain the different isolation levels in database transactions (READ UNCOMMITTED through SERIALIZABLE)",
            "How does consistent hashing work and why is it useful for distributed systems?",
            "Explain how OAuth 2.0 works, including the different grant types and when to use each",
            "How does a bloom filter work? What are its trade-offs?",
            "Explain the Raft consensus algorithm at a high level",
            "How does a CDN work? Explain cache hierarchies, invalidation strategies, and edge locations.",
        ],
        "hard": [
            "Explain how CRDTs (Conflict-free Replicated Data Types) work. Give examples of state-based and operation-based CRDTs.",
            "How does the Linux kernel scheduler work? Explain the Completely Fair Scheduler (CFS).",
            "Explain the internals of how PostgreSQL handles MVCC (Multi-Version Concurrency Control)",
            "How does the V8 JavaScript engine optimize code? Explain hidden classes, inline caching, and the JIT compilation pipeline.",
            "Explain how Paxos achieves consensus in a distributed system. Walk through a complete round.",
        ],
        "extreme": [
            "Explain the full lifecycle of a network packet from a user typing a URL to the page rendering, including DNS resolution, TCP handshake, TLS negotiation, HTTP/2 multiplexing, server processing, and browser rendering pipeline",
            "Explain how modern CPU branch prediction works, including the evolution from simple saturating counters to neural branch predictors, and how speculative execution vulnerabilities (Spectre/Meltdown) exploit this",
        ],
    },

    # ================================================================
    # 9. CREATIVE
    # ================================================================
    "creative": {
        "criteria": [
            "Response is original and creative",
            "Meets the specific constraints given",
            "Writing quality is high",
        ],
        "tools": [],
        "easy": [
            "Write a haiku about debugging code at 3am",
            "Come up with 5 creative names for a startup that makes AI-powered gardening tools",
            "Write a short joke about a programmer who can't find a bug",
            "Write a limerick about a Python developer",
            "Create a fun acronym for 'DEBUG' related to software engineering",
            "Write a 4-line poem about merge conflicts",
            "Write a witty one-liner for a 404 error page",
            "Come up with 3 creative analogies to explain recursion to a 10-year-old",
            "Write a short motivational quote for a developer who just passed all their tests",
            "Create a fictional error message that would make a developer laugh",
            "Write a two-sentence horror story about production deployments",
            "Come up with a creative metaphor comparing software architecture to city planning",
        ],
        "medium": [
            "Write a short story (200-300 words) about an AI that becomes sentient but only cares about optimizing database queries",
            "Create a D&D character sheet for a software engineer, including stats, abilities, and backstory",
            "Write a Shakespearean sonnet about the joys and sorrows of code review",
            "Design a fictional programming language called 'CoffeeScript++'. Describe its syntax, type system, and killer feature.",
            "Write a product launch announcement in the style of an Apple keynote for a revolutionary new text editor",
            "Create a 'choose your own adventure' scenario with 3 branch points about debugging a production issue",
            "Write a fairy tale retelling where the three little pigs are microservices and the big bad wolf is a DDoS attack",
            "Write a cover letter from a rubber duck applying for the position of Senior Debug Assistant",
            "Create a fictional tech conference talk abstract about 'Quantum CSS: Styling Elements That Both Exist and Don't Exist'",
            "Write a dialogue between two chatbots having an existential crisis about their purpose",
        ],
        "hard": [
            "Write a complete short story (500+ words) set in a world where code compiles on the first try and debugging doesn't exist. What goes wrong?",
            "Create a detailed worldbuilding document for a sci-fi universe where programming languages are spoken languages and different language communities are nations",
            "Write a satirical academic paper abstract about the 'correlation between coffee consumption and code quality' with fake statistics and methodology",
            "Design a complete board game about software development, including rules, game mechanics, cards, and win conditions",
            "Write a script for a 5-minute comedy sketch about a standup meeting that goes horribly wrong",
        ],
        "extreme": [
            "Write a complete one-act play about the tension between a senior engineer who wants to rewrite everything and a PM who just wants to ship",
            "Create an elaborate alternate history where Alan Turing's universal machine was built in ancient Greece. Describe the technological, social, and political implications across 2000 years.",
        ],
    },

    # ================================================================
    # 10. TOOL USE & COMPUTATION
    # ================================================================
    "tool_using": {
        "criteria": [
            "Correct tool is chosen for the task",
            "Tool is used effectively",
            "Result is interpreted correctly",
        ],
        "tools": ["execute_python", "math_eval", "search"],
        "easy": [
            "Use Python to generate a random password of 16 characters including uppercase, lowercase, digits, and special characters",
            "Use Python to calculate the factorial of 20",
            "Write a Python one-liner that prints all even numbers from 1 to 50",
            "Use Python to convert the hex color #FF5733 to RGB values",
            "Use Python to find all files in a directory that are larger than 1MB (write the function, don't actually run on filesystem)",
            "Write a Python function that generates a UUID v4",
            "Use Python to base64 encode the string 'Hello, World!'",
            "Use Python to calculate the distance between two GPS coordinates: (40.7128, -74.0060) and (34.0522, -118.2437)",
            "Write a Python function that validates an email address using regex",
            "Use Python to generate a simple ASCII art representation of a bar chart from data: {'A': 5, 'B': 8, 'C': 3, 'D': 12}",
        ],
        "medium": [
            "Write a Python script that reads a JSON file, transforms nested data into a flat CSV, handling missing values gracefully",
            "Write a Python function that scrapes a given HTML string and extracts all links (href attributes) from anchor tags",
            "Write a Python script that generates a markdown report from a dictionary of test results including pass/fail counts, percentages, and a summary table",
            "Write a Python function that computes a cryptographic hash (SHA-256) of a file, reading in chunks to handle large files",
            "Write a Python script that converts between different date formats: ISO 8601, Unix timestamp, and human-readable",
            "Write a Python function that implements a simple cron expression parser (minute, hour, day-of-month, month, day-of-week)",
            "Write a Python script that generates a flame graph-like visualization of nested function call timings from a profiling dict",
            "Write a Python function that compresses a string using run-length encoding and decompresses it back",
        ],
        "hard": [
            "Write a complete Python script that implements a simple HTTP server from scratch using only the socket library — handle GET requests, serve files, and return proper HTTP headers",
            "Write a Python script that implements a basic regex engine supporting: literal characters, '.', '*', '+', '?', and character classes []",
            "Write a Python implementation of the Aho-Corasick algorithm for multi-pattern string matching",
            "Write a Python script that implements a simple version control system: init, add, commit, log, diff, and checkout commands working on a directory",
            "Write a Python script that implements a basic neural network (multi-layer perceptron) from scratch with forward pass, backpropagation, and gradient descent — no ML libraries",
        ],
        "extreme": [
            "Write a complete Python implementation of a key-value database with: B-tree index, write-ahead log, crash recovery, and basic ACID transactions",
            "Write a Python implementation of a Raft consensus protocol simulator with leader election, log replication, and network partition handling",
        ],
    },

    # ================================================================
    # 11. SQL & DATABASE
    # ================================================================
    "sql_database": {
        "criteria": [
            "Query is syntactically correct",
            "Query produces the correct result",
            "Query is reasonably efficient",
        ],
        "tools": ["execute_python"],
        "easy": [
            "Write a SQL query to select all users who signed up in the last 30 days from a 'users' table with columns: id, name, email, created_at",
            "Write a SQL query to count the number of orders per customer from an 'orders' table with columns: id, customer_id, total, created_at",
            "Write a SQL query to find the top 5 most expensive products from a 'products' table",
            "Write a SQL query to find all employees whose salary is above the company average",
            "Write a SQL query to find duplicate email addresses in a users table",
            "Write a SQL query to get the total revenue by month from an orders table",
            "Write a SQL query that joins 'orders' and 'customers' tables to show customer name with their order count",
            "Write a SQL query to find the second highest salary in an employees table",
            "Write a SQL query to delete all records from 'logs' table older than 90 days",
            "Write a SQL query to update all prices in a products table by increasing them 10%",
        ],
        "medium": [
            "Write a SQL query using window functions to calculate a running total of daily sales",
            "Write a SQL query to find the top 3 customers by revenue for each product category using ROW_NUMBER()",
            "Write a SQL query to detect gaps in a sequence of order IDs",
            "Write a SQL query to implement a paginated search with cursor-based pagination (keyset pagination) instead of OFFSET",
            "Write a SQL query using CTEs to build an org chart hierarchy from an employees table with manager_id",
            "Write a SQL query to calculate customer retention: for each monthly cohort, what percentage are still active after 1, 3, and 6 months?",
            "Write a SQL query to find all products that have never been ordered using a LEFT JOIN",
            "Write a SQL query to calculate the median order value (not average) across all orders",
            "Design a database schema for a multi-tenant SaaS application with proper foreign keys and indexes",
            "Write a SQL migration script to add a new column with a default value to a table with 10 million rows, minimizing lock time",
        ],
        "hard": [
            "Write a SQL query to implement a complete funnel analysis: track users through signup → activation → first purchase → repeat purchase, showing conversion rates at each step",
            "Design and implement a database schema for a booking system with availability windows, conflict detection, and recurring events",
            "Write a SQL query that implements the Apriori algorithm for market basket analysis using only SQL (find frequently co-purchased product pairs)",
            "Design a time-series database schema optimized for both high-speed writes and efficient range queries, with automatic partitioning by time",
            "Write SQL to implement a complete audit trail system with row-level change tracking, rollback capability, and efficient querying of historical state",
        ],
        "extreme": [
            "Design a complete multi-region database sharding strategy including: shard key selection, cross-shard query handling, rebalancing procedures, and a migration plan from a single-node PostgreSQL",
            "Implement a complete event sourcing system in SQL with: event store schema, projection tables, snapshot management, and rebuild procedures. Include handling for schema evolution of events.",
        ],
    },

    # ================================================================
    # 12. API DESIGN
    # ================================================================
    "api_design": {
        "criteria": [
            "API is intuitive and consistent",
            "Error handling is well-defined",
            "Documentation is clear",
        ],
        "tools": [],
        "easy": [
            "Design a REST API for a simple todo list app. What endpoints do you need?",
            "Design the request/response format for a user registration endpoint including validation rules",
            "Design a REST API endpoint for searching products with filtering, sorting, and pagination",
            "What HTTP status codes should a CRUD API return for each operation? List the common ones with explanations.",
            "Design the API for a simple URL shortener service with create, redirect, and stats endpoints",
            "Design a webhook payload format for notifying about order status changes",
            "Design the authentication flow for a REST API using API keys. Include the registration and key management endpoints.",
            "Design a REST API for a simple blog with posts and comments",
            "Define the error response format for an API. Include error codes, messages, and field-level validation errors.",
            "Design the request/response for a file upload endpoint that supports multipart uploads",
        ],
        "medium": [
            "Design a complete REST API for a ride-sharing service (like Uber). Cover riders, drivers, trips, pricing, and ratings.",
            "Design a GraphQL schema for a social media platform with users, posts, comments, likes, and followers",
            "Design a rate-limiting API that supports per-user, per-endpoint, and global limits with proper HTTP headers",
            "Design a versioned API strategy for a public API. Compare URL versioning, header versioning, and content negotiation.",
            "Design a real-time notification API using WebSockets. Define the message formats, connection lifecycle, and reconnection strategy.",
            "Design a batch API that allows clients to send multiple operations in a single request with partial failure handling",
            "Design an API for a payment processing system with idempotency keys, retry-safe operations, and webhook notifications",
            "Design a search API with faceted search, fuzzy matching, and relevance scoring. Define the query DSL.",
        ],
        "hard": [
            "Design a complete public API platform including: developer portal, API key management, OAuth2 flows, rate limiting tiers, usage metering, and billing integration",
            "Design an event-driven API using CloudEvents specification for a microservices e-commerce platform. Define event schemas for order lifecycle, inventory, and shipping.",
            "Design a CQRS API where reads and writes go through different paths. Handle eventual consistency, optimistic concurrency, and conflict resolution.",
            "Design a multi-tenant API gateway that handles: tenant isolation, per-tenant rate limits, tenant-aware routing, custom domains, and white-labeling",
        ],
        "extreme": [
            "Design a complete API specification for a financial trading platform including: order management, market data streaming, portfolio management, risk checks, regulatory reporting, and audit trails. Include authentication, authorization, rate limiting, and circuit breaking.",
            "Design a federated API system (like Apollo Federation) for a large e-commerce platform with independently deployable subgraphs for products, orders, users, inventory, and recommendations",
        ],
    },

    # ================================================================
    # 13. SECURITY
    # ================================================================
    "security": {
        "criteria": [
            "Vulnerability is correctly identified",
            "Remediation is appropriate and complete",
            "Security reasoning is sound",
        ],
        "tools": ["execute_python"],
        "easy": [
            "What is SQL injection? Give an example of vulnerable code and the fix.",
            "What is XSS (Cross-Site Scripting)? Explain the difference between stored and reflected XSS.",
            "Review this code for security issues:\npassword = request.form['password']\nquery = f\"SELECT * FROM users WHERE password = '{password}'\"",
            "What is CSRF and how do CSRF tokens prevent it?",
            "Explain why storing passwords in plain text is dangerous and what you should do instead",
            "What are the security risks of using eval() or exec() in Python?",
            "What is the principle of least privilege? Give 3 examples in a web application context.",
            "Review this code for security issues:\nimport pickle\ndata = pickle.loads(request.body)",
            "What is a JWT? What are the security considerations when using JWTs for authentication?",
            "Explain what HTTPS does and doesn't protect against",
        ],
        "medium": [
            "Review this authentication system for security vulnerabilities:\n```python\ndef login(username, password):\n    user = db.query(f\"SELECT * FROM users WHERE username='{username}'\")\n    if user and user.password == password:\n        token = base64.b64encode(f\"{username}:{time.time()}\".encode())\n        return {\"token\": token}\n    return {\"error\": \"Invalid credentials\"}\n```",
            "Design a secure password reset flow. What are the common pitfalls and how do you avoid them?",
            "Explain how to implement rate limiting to prevent brute force attacks. Cover both application-level and infrastructure-level approaches.",
            "Review this file upload handler for security issues:\n```python\ndef upload(file):\n    filename = file.filename\n    file.save(f'/uploads/{filename}')\n    return f'<img src=\"/uploads/{filename}\">'\n```",
            "Design a secure API key rotation strategy that doesn't cause downtime",
            "Explain the OWASP Top 10 vulnerabilities and give a one-line mitigation for each",
            "Design a secure session management system. Cover creation, storage, expiration, and invalidation.",
            "What is a supply chain attack in the context of npm/pip packages? How do you mitigate it?",
        ],
        "hard": [
            "Perform a security review of this JWT implementation and identify all vulnerabilities:\n```python\nimport jwt\ndef create_token(user_id, role):\n    return jwt.encode({'user_id': user_id, 'role': role}, 'secret123', algorithm='HS256')\ndef verify_token(token):\n    try:\n        payload = jwt.decode(token, 'secret123', algorithms=['HS256', 'none'])\n        return payload\n    except:\n        return None\n```",
            "Design a complete zero-trust security architecture for a microservices platform. Cover service mesh, mTLS, identity-aware proxy, and workload identity.",
            "Explain how a timing side-channel attack works against password comparison. Write both the vulnerable and fixed code.",
            "Design a secrets management system for a Kubernetes-based microservices platform. Cover encryption at rest, rotation, access control, and audit logging.",
        ],
        "extreme": [
            "Design a complete threat model for a fintech application handling PCI data. Include: attack surfaces, threat actors, STRIDE analysis, risk matrix, and prioritized mitigations",
            "Design and implement a capability-based access control system that supports: hierarchical capabilities, delegation, revocation, and audit. Compare with RBAC and ABAC.",
        ],
    },

    # ================================================================
    # 14. DEVOPS & INFRASTRUCTURE
    # ================================================================
    "devops": {
        "criteria": [
            "Configuration is correct and complete",
            "Best practices are followed",
            "Infrastructure is secure and scalable",
        ],
        "tools": [],
        "easy": [
            "Write a Dockerfile for a Python Flask application with requirements.txt",
            "Write a docker-compose.yml for a web app with a PostgreSQL database and Redis cache",
            "Write a simple GitHub Actions workflow that runs tests on every pull request",
            "Write an nginx config that serves static files and reverse proxies /api to a backend on port 8080",
            "Write a .gitignore file for a Python project with virtual environments, caches, and IDE files",
            "Write a basic Makefile for a Go project with build, test, clean, and lint targets",
            "Write a systemd service file for a Node.js application",
            "Write a crontab entry that runs a backup script every day at 2am and logs output",
            "Write a shell script that checks if a service is running and restarts it if not",
            "Write environment variable configuration for a 12-factor app with development, staging, and production profiles",
        ],
        "medium": [
            "Write a multi-stage Dockerfile that builds a Go application and produces a minimal production image under 20MB",
            "Write a GitHub Actions CI/CD pipeline that: runs tests, builds a Docker image, pushes to ECR, and deploys to ECS on merge to main",
            "Write a Terraform configuration for deploying a VPC with public/private subnets, NAT gateway, and security groups on AWS",
            "Design a logging pipeline using Fluentd, Elasticsearch, and Kibana. Write the Fluentd configuration for parsing JSON logs.",
            "Write a Kubernetes deployment manifest with: rolling update strategy, resource limits, health checks, and horizontal pod autoscaler",
            "Write a Prometheus alerting rules file for: high error rate, high latency, disk space, and memory usage",
            "Design a blue-green deployment strategy. Write the scripts/configs needed to switch traffic between environments.",
            "Write a database backup and restore script that handles: compression, encryption, S3 upload, retention policy, and Slack notification on failure",
        ],
        "hard": [
            "Design a complete CI/CD pipeline for a monorepo with 5 microservices. Include: selective builds, parallel testing, canary deployments, and automatic rollback.",
            "Write Terraform modules for a production-grade EKS cluster with: node groups, IRSA, cluster autoscaler, and ALB ingress controller",
            "Design a disaster recovery strategy for a multi-region application. Include RTO/RPO targets, failover procedures, and automated testing of the DR plan.",
            "Design a GitOps workflow using ArgoCD. Cover: application definitions, sync policies, secret management, and rollback procedures.",
        ],
        "extreme": [
            "Design a complete platform engineering solution: internal developer platform with self-service infrastructure provisioning, golden path templates, service catalog, and cost management dashboards",
            "Design and implement a chaos engineering framework including: steady state hypothesis definition, experiment catalog (pod kills, network partitions, latency injection), safety controls, and automated analysis of blast radius",
        ],
    },

    # ================================================================
    # 15. TESTING
    # ================================================================
    "testing": {
        "criteria": [
            "Tests cover the important cases",
            "Edge cases are considered",
            "Tests are maintainable and readable",
        ],
        "tools": ["execute_python"],
        "easy": [
            "Write unit tests for a function that calculates the area of a rectangle given width and height",
            "Write unit tests for a function that validates email addresses",
            "Write unit tests for a stack implementation with push, pop, peek, and is_empty methods",
            "Write unit tests for a function that converts temperatures between Celsius and Fahrenheit",
            "Write unit tests for a function that calculates the nth Fibonacci number",
            "Write unit tests for a function that checks if a string is a valid palindrome (ignoring case and spaces)",
            "Write unit tests for a function that finds the intersection of two lists",
            "Write unit tests for a function that parses a date string in format 'YYYY-MM-DD' and returns a dict with year, month, day",
            "Write unit tests for a simple calculator class with add, subtract, multiply, divide methods",
            "Write unit tests for a function that sorts a list of dictionaries by a given key",
        ],
        "medium": [
            "Write comprehensive tests for a shopping cart class: add item, remove item, update quantity, calculate total, apply discount code, and handle out-of-stock items",
            "Write integration tests for a REST API endpoint that creates a user, including validation errors, duplicate detection, and database verification",
            "Write property-based tests (using Hypothesis or similar approach) for a sorting function. Define the properties that any correct sort must satisfy.",
            "Write tests for a rate limiter that should allow 100 requests per minute. Include time-based tests using mocking.",
            "Write tests for a caching decorator that: caches results, respects TTL, handles cache invalidation, and has a max size limit",
            "Write a complete test suite for a password validation function that checks: minimum length, uppercase, lowercase, digit, special char, and no common passwords",
            "Write tests for a retry decorator that: retries on specific exceptions, supports exponential backoff, and has a max retry count",
            "Write load test scenarios using locust or similar: simulate 1000 concurrent users, measure p95 latency, and identify bottlenecks",
        ],
        "hard": [
            "Write a complete test harness for a state machine (e.g., order lifecycle: created→paid→shipped→delivered). Cover all valid transitions, invalid transitions, and concurrent state changes.",
            "Write tests for a distributed lock implementation. Include: basic locking, timeout behavior, lock contention, and crash recovery scenarios.",
            "Design a complete testing strategy for a payment processing system: unit tests, integration tests, contract tests, and end-to-end tests. Include test doubles for external services.",
            "Write mutation testing for a critical function. Generate mutants, run tests against them, and calculate mutation score.",
        ],
        "extreme": [
            "Design a complete testing framework for a microservices architecture: consumer-driven contract tests between 5 services, chaos testing scenarios, and an automated test environment provisioning pipeline",
            "Write a comprehensive fuzz testing suite for a JSON parser that: generates random inputs, tracks code coverage, minimizes failing inputs, and reports crash causes",
        ],
    },

    # ================================================================
    # 16. REFACTORING
    # ================================================================
    "refactoring": {
        "criteria": [
            "Refactored code maintains the same behavior",
            "Code is measurably improved (readability, performance, or maintainability)",
            "Changes are well-explained",
        ],
        "tools": ["execute_python"],
        "easy": [
            "Refactor this code to remove duplication:\ndef get_user_name(user):\n    if user['type'] == 'admin':\n        return user['first'] + ' ' + user['last'] + ' (Admin)'\n    elif user['type'] == 'mod':\n        return user['first'] + ' ' + user['last'] + ' (Moderator)'\n    else:\n        return user['first'] + ' ' + user['last']",
            "Refactor these nested if-statements into a cleaner structure:\nif a:\n    if b:\n        if c:\n            do_thing()\n        else:\n            handle_no_c()\n    else:\n        handle_no_b()\nelse:\n    handle_no_a()",
            "Refactor this function to use list comprehension:\ndef get_evens(numbers):\n    result = []\n    for n in numbers:\n        if n % 2 == 0:\n            result.append(n)\n    return result",
            "Refactor this code to use a dictionary instead of if/elif chain:\ndef get_day_name(num):\n    if num == 1: return 'Monday'\n    elif num == 2: return 'Tuesday'\n    elif num == 3: return 'Wednesday'\n    elif num == 4: return 'Thursday'\n    elif num == 5: return 'Friday'\n    elif num == 6: return 'Saturday'\n    elif num == 7: return 'Sunday'\n    else: return 'Invalid'",
            "Refactor this to use Python's built-in functions:\ndef find_max(lst):\n    max_val = lst[0]\n    for item in lst:\n        if item > max_val:\n            max_val = item\n    return max_val\n\ndef find_min(lst):\n    min_val = lst[0]\n    for item in lst:\n        if item < min_val:\n            min_val = item\n    return min_val",
            "Refactor this class to use @property instead of getters/setters:\nclass Circle:\n    def __init__(self, radius):\n        self._radius = radius\n    def get_radius(self):\n        return self._radius\n    def set_radius(self, r):\n        if r < 0: raise ValueError\n        self._radius = r\n    def get_area(self):\n        return 3.14159 * self._radius ** 2",
            "Refactor this to use enumerate:\ncolors = ['red', 'green', 'blue']\ni = 0\nfor color in colors:\n    print(f'{i}: {color}')\n    i += 1",
            "Refactor this function to use early returns:\ndef process(data):\n    if data is not None:\n        if len(data) > 0:\n            if data[0] != '#':\n                return data.strip().upper()\n            else:\n                return None\n        else:\n            return None\n    else:\n        return None",
        ],
        "medium": [
            "Refactor this 200-line function into smaller, testable functions:\n```python\ndef process_order(order):\n    # Validate\n    if not order.get('items'): raise ValueError('No items')\n    if not order.get('customer_id'): raise ValueError('No customer')\n    for item in order['items']:\n        if item['qty'] <= 0: raise ValueError('Bad qty')\n    # Calculate totals\n    subtotal = sum(i['price'] * i['qty'] for i in order['items'])\n    tax = subtotal * 0.08\n    if order.get('coupon') == 'SAVE10': discount = subtotal * 0.1\n    elif order.get('coupon') == 'SAVE20': discount = subtotal * 0.2\n    else: discount = 0\n    total = subtotal + tax - discount\n    # Save to DB\n    order_id = db.insert('orders', {'customer_id': order['customer_id'], 'total': total, 'status': 'pending'})\n    for item in order['items']:\n        db.insert('order_items', {'order_id': order_id, 'product_id': item['id'], 'qty': item['qty']})\n    # Send notifications\n    email.send(order['customer_id'], f'Order {order_id} confirmed! Total: ${total:.2f}')\n    slack.post(f'New order #{order_id} for ${total:.2f}')\n    return order_id\n```",
            "Refactor this callback-heavy async code into clean async/await:\n```python\ndef fetch_user_data(user_id, callback):\n    def on_profile(profile):\n        def on_orders(orders):\n            def on_preferences(prefs):\n                callback({'profile': profile, 'orders': orders, 'prefs': prefs})\n            get_preferences(user_id, on_preferences)\n        get_orders(user_id, on_orders)\n    get_profile(user_id, on_profile)\n```",
            "Refactor this class hierarchy to use composition over inheritance:\n```python\nclass Animal:\n    def eat(self): print('eating')\nclass FlyingAnimal(Animal):\n    def fly(self): print('flying')\nclass SwimmingAnimal(Animal):\n    def swim(self): print('swimming')\nclass Duck(FlyingAnimal, SwimmingAnimal):\n    pass  # Diamond inheritance problem\n```",
            "Refactor this code to use the Strategy pattern:\n```python\ndef calculate_shipping(order, method):\n    if method == 'standard':\n        return 5.99 if order.total < 50 else 0\n    elif method == 'express':\n        return 15.99\n    elif method == 'overnight':\n        return 25.99 + order.weight * 0.5\n    elif method == 'international':\n        return 35.99 + order.weight * 1.5\n```",
            "Extract a reusable retry mechanism from these three functions that all have copy-pasted retry logic:\n```python\ndef fetch_api():\n    for attempt in range(3):\n        try:\n            return requests.get(url)\n        except: time.sleep(2 ** attempt)\n\ndef query_db():\n    for attempt in range(3):\n        try:\n            return db.execute(sql)\n        except: time.sleep(2 ** attempt)\n\ndef send_email():\n    for attempt in range(3):\n        try:\n            return smtp.send(msg)\n        except: time.sleep(2 ** attempt)\n```",
        ],
        "hard": [
            "Refactor this monolithic request handler into a middleware pipeline with proper separation of concerns:\n```python\ndef handle_request(request):\n    # Auth\n    token = request.headers.get('Authorization')\n    if not token: return Response(401)\n    user = verify_token(token)\n    if not user: return Response(403)\n    # Rate limit\n    key = f'rate:{user.id}'\n    count = redis.incr(key)\n    if count == 1: redis.expire(key, 60)\n    if count > 100: return Response(429)\n    # Validation\n    body = json.loads(request.body)\n    errors = validate_schema(body, SCHEMA)\n    if errors: return Response(400, errors)\n    # Business logic\n    result = process(body, user)\n    # Audit\n    audit_log.write(user.id, request.path, body)\n    # Response\n    return Response(200, result)\n```",
            "Refactor a tightly-coupled module into a dependency-injectable design. The module currently imports and directly uses: a database client, a cache client, an email service, and a logging service.",
            "Refactor this event-driven system from callbacks to an observable/reactive pattern:\n```python\nclass OrderService:\n    def __init__(self):\n        self.inventory = InventoryService()\n        self.payment = PaymentService()\n        self.shipping = ShippingService()\n        self.email = EmailService()\n\n    def place_order(self, order):\n        self.inventory.reserve(order.items)\n        self.payment.charge(order.total)\n        self.shipping.create_label(order)\n        self.email.send_confirmation(order)\n```",
        ],
        "extreme": [
            "Refactor a synchronous, single-threaded ETL pipeline into an async, streaming pipeline with backpressure. The current code: reads a 10GB CSV line by line, transforms each row (CPU-bound), and writes to a database (IO-bound). The new version should maximize throughput while keeping memory usage under 100MB.",
            "Refactor a legacy codebase's God Object (a 2000-line class with 50 methods touching 10 database tables) into properly bounded domain services following DDD principles. Show the extraction strategy, maintain backward compatibility, and add interfaces for testing.",
        ],
    },

    # ================================================================
    # 17. SHELL & CLI
    # ================================================================
    "shell_cli": {
        "criteria": [
            "Command is correct and handles edge cases",
            "Output format is clear",
            "Script is portable where possible",
        ],
        "tools": ["execute_python"],
        "easy": [
            "Write a bash command to find all .py files in the current directory and subdirectories",
            "Write a bash one-liner to count the number of lines in all .js files in a project",
            "Write a bash command to find the 10 largest files in a directory",
            "Write a bash command to replace all occurrences of 'foo' with 'bar' in all .txt files recursively",
            "Write a bash command to show disk usage of each subdirectory, sorted by size",
            "Write a bash command to find all processes using more than 100MB of memory",
            "Write a bash command to tail the last 50 lines of a log file and highlight lines containing 'ERROR'",
            "Write a bash command to compress all .log files older than 7 days",
            "Write a bash one-liner to extract unique IP addresses from an nginx access log",
            "Write a bash command to kill all processes matching a given name",
        ],
        "medium": [
            "Write a bash script that monitors a directory for new files and processes each one (moves to an archive folder after processing)",
            "Write a bash script that performs a zero-downtime deployment by: pulling new code, building, running health check, and switching a symlink",
            "Write a bash script that manages log rotation: compress logs older than 1 day, delete logs older than 30 days, and report total disk usage",
            "Write a complete bash CLI tool with subcommands (init, add, remove, list) using case statements and proper argument parsing",
            "Write a bash script that backs up a PostgreSQL database, compresses it, encrypts it with GPG, and uploads to S3",
            "Write a bash script that performs parallel downloads of a list of URLs using xargs and curl with a progress report",
            "Write a bash script that analyzes an Apache/nginx access log and produces a report: top IPs, top URLs, error rate, requests per second",
            "Write a bash script that sets up a development environment: checks for required tools, installs missing ones, clones repos, and creates config files",
        ],
        "hard": [
            "Write a complete CLI tool in Python using argparse that manages Docker containers: list, start, stop, logs, and exec commands with proper error handling and colored output",
            "Write a bash script that implements a simple service mesh: starts multiple services, sets up port forwarding, monitors health, and provides a unified log stream",
            "Write a CLI tool that analyzes a git repository: shows commit frequency by author, file churn, hotspot files, and generates an HTML report",
            "Write a bash script that implements canary deployment: gradually shifts traffic from old to new version, monitors error rates, and automatically rolls back if errors exceed threshold",
        ],
        "extreme": [
            "Write a complete CLI-based project scaffolding tool (like create-react-app) that: prompts for project type, generates directory structure, writes config files, initializes git, installs dependencies, and creates CI/CD pipeline configuration",
            "Write a complete terminal-based monitoring dashboard using Python curses that shows: real-time CPU/memory/disk usage, process list, network connections, and container stats with drill-down capability",
        ],
    },

    # ================================================================
    # 18. PERFORMANCE OPTIMIZATION
    # ================================================================
    "performance": {
        "criteria": [
            "Performance improvement is measurable",
            "Optimization doesn't sacrifice correctness",
            "Trade-offs are clearly explained",
        ],
        "tools": ["execute_python"],
        "easy": [
            "This code is slow for large lists. Optimize it:\ndef has_duplicates(lst):\n    for i in range(len(lst)):\n        for j in range(i+1, len(lst)):\n            if lst[i] == lst[j]:\n                return True\n    return False",
            "Optimize this string concatenation:\ndef build_string(words):\n    result = ''\n    for word in words:\n        result = result + word + ' '\n    return result",
            "Optimize this function that checks membership in a large list:\ndef find_common(list1, list2):\n    common = []\n    for item in list1:\n        if item in list2:  # list2 has 100,000 items\n            common.append(item)\n    return common",
            "Optimize this database query pattern:\nfor user_id in user_ids:  # 10,000 user IDs\n    user = db.query(f'SELECT * FROM users WHERE id = {user_id}')\n    process(user)",
            "Optimize this function that reads a file line by line:\ndef count_lines(filepath):\n    with open(filepath) as f:\n        lines = f.readlines()  # 10GB file\n    return len(lines)",
            "Optimize this function that creates many small objects:\ndef process_events(events):\n    results = []\n    for e in events:  # 1 million events\n        results.append({'type': e[0], 'time': e[1], 'value': e[2]})\n    return results",
            "Optimize this nested loop:\ndef matrix_multiply(A, B):\n    n = len(A)\n    C = [[0]*n for _ in range(n)]\n    for i in range(n):\n        for j in range(n):\n            for k in range(n):\n                C[i][j] += A[i][k] * B[k][j]\n    return C",
        ],
        "medium": [
            "Profile and optimize this web API handler that takes 2 seconds per request:\n```python\ndef handle_request(user_id):\n    user = db.query('SELECT * FROM users WHERE id = %s', user_id)  # 50ms\n    orders = db.query('SELECT * FROM orders WHERE user_id = %s', user_id)  # 200ms\n    for order in orders:\n        order['items'] = db.query('SELECT * FROM items WHERE order_id = %s', order['id'])  # 100ms each, 10 orders\n    recommendations = ml_model.predict(user, orders)  # 500ms\n    return {'user': user, 'orders': orders, 'recommendations': recommendations}\n```",
            "Optimize this Python function to handle 1 million records:\n```python\ndef deduplicate(records):\n    unique = []\n    for record in records:\n        key = json.dumps(record, sort_keys=True)\n        if key not in [json.dumps(r, sort_keys=True) for r in unique]:\n            unique.append(record)\n    return unique\n```",
            "Design a caching strategy for this function that's called 10,000 times/second with 80% cache-hit potential:\n```python\ndef get_user_profile(user_id):\n    user = db.get_user(user_id)  # 50ms\n    permissions = auth.get_permissions(user_id)  # 30ms\n    preferences = db.get_preferences(user_id)  # 40ms\n    return {**user, 'permissions': permissions, 'preferences': preferences}\n```",
            "Optimize this pagination query that gets slower as page number increases:\nSELECT * FROM events ORDER BY created_at DESC LIMIT 20 OFFSET {page * 20}",
            "Optimize this function that processes a stream of events and maintains running statistics:\n```python\ndef running_stats(events):\n    results = []\n    for i, event in enumerate(events):\n        window = events[max(0,i-999):i+1]\n        avg = sum(e.value for e in window) / len(window)\n        results.append({'avg': avg, 'count': len(window)})\n    return results\n```",
        ],
        "hard": [
            "Optimize a real-time search system that indexes 10 million documents. Current approach: linear scan with string matching. Design an inverted index with ranked retrieval that returns results in under 50ms.",
            "Profile and optimize a Python application that processes 1TB of log files. Current time: 4 hours. Target: under 30 minutes. Consider: parallel processing, memory mapping, compiled extensions, and streaming.",
            "Optimize a graph traversal algorithm on a graph with 10 million nodes and 100 million edges. Current BFS takes 45 seconds. Target: under 5 seconds. Consider cache locality, compact representations, and parallelism.",
            "Design a high-performance connection pool that handles 50,000 concurrent database connections with minimal contention. Cover: pool sizing, connection health checks, queue fairness, and backpressure.",
        ],
        "extreme": [
            "Design and optimize a complete high-frequency data pipeline: ingest 1 million events/second, enrich with lookups, aggregate in real-time windows, and write to both a time-series DB and an alerting system. Target: p99 latency under 100ms end-to-end.",
            "Optimize a machine learning inference pipeline from 500ms to under 10ms per prediction: model quantization, batch inference, memory pre-allocation, SIMD operations, and zero-copy data transfer between stages.",
        ],
    },

    # ================================================================
    # 19. CODE EXPLANATION
    # ================================================================
    "explanation": {
        "criteria": [
            "Explanation is accurate",
            "Complexity is appropriate for the audience",
            "Key concepts are clearly conveyed",
        ],
        "tools": [],
        "easy": [
            "Explain what this Python code does:\nresult = [x**2 for x in range(10) if x % 2 == 0]",
            "Explain what this bash command does:\nfind . -name '*.log' -mtime +30 -exec rm {} \\;",
            "Explain what this regex matches:\n^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$",
            "Explain what a 'decorator' is in Python and how @staticmethod works",
            "Explain what this SQL query does:\nSELECT d.name, COUNT(e.id) FROM departments d LEFT JOIN employees e ON d.id = e.dept_id GROUP BY d.name HAVING COUNT(e.id) > 5",
            "Explain the difference between '==' and 'is' in Python with examples",
            "Explain what this git command does:\ngit rebase -i HEAD~5",
            "Explain what this JavaScript code does:\nconst debounce = (fn, ms) => { let t; return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); }; };",
            "Explain what a Python generator is and why you'd use one instead of a list",
            "Explain what the 'yield' keyword does in Python",
            "Explain what this Docker command does:\ndocker run -d -p 8080:80 -v /data:/app/data --env-file .env --name myapp myimage:latest",
            "Explain what CORS is and why browsers enforce it",
        ],
        "medium": [
            "Explain how Python's GIL (Global Interpreter Lock) works and its implications for multithreaded programs",
            "Explain how HTTP/2 server push works and when it's beneficial vs harmful",
            "Explain the event loop in Node.js/JavaScript. How does it handle async operations without threads?",
            "Explain how database connection pooling works. Why is it necessary and what are the trade-offs of different pool sizes?",
            "Explain how Kubernetes pod scheduling works, including resource requests, limits, and node affinity",
            "Explain how a bloom filter works internally (hashing, bit array, false positive rate). When would you use one?",
            "Explain the CAP theorem with concrete examples. Why can't a distributed system guarantee all three?",
            "Explain how React's virtual DOM and reconciliation algorithm work. What makes it efficient?",
            "Explain how TLS 1.3 differs from TLS 1.2 and why the changes were made",
            "Explain how database query planners work: cost estimation, statistics, join ordering, and index selection",
        ],
        "hard": [
            "Explain how the Raft consensus algorithm works in detail: leader election, log replication, safety, and membership changes",
            "Explain how LSM-tree storage engines work (as used in RocksDB/LevelDB): memtable, SSTables, compaction strategies, and read/write amplification",
            "Explain how TCP congestion control works: slow start, congestion avoidance, fast retransmit, and fast recovery. Compare Reno, Cubic, and BBR.",
            "Explain how copy-on-write works at the OS level and how it enables efficient fork() in Unix systems",
            "Explain how JIT compilation works in V8/HotSpot: profiling, tiered compilation, deoptimization, and inline caching",
        ],
        "extreme": [
            "Explain how a modern CPU executes instructions: pipeline stages, out-of-order execution, branch prediction, speculative execution, memory hierarchy, and how this all relates to writing cache-friendly code",
            "Explain how garbage collection works in the JVM in comprehensive detail: generational hypothesis, young/old gen, G1 collector, ZGC, and how to tune GC for different workload patterns",
        ],
    },

    # ================================================================
    # 20. REGEX & TEXT PROCESSING
    # ================================================================
    "regex_text": {
        "criteria": [
            "Pattern is correct",
            "Edge cases are handled",
            "Pattern is readable (not overly complex)",
        ],
        "tools": ["execute_python"],
        "easy": [
            "Write a regex that matches US phone numbers in formats: (555) 123-4567, 555-123-4567, 5551234567",
            "Write a regex that matches dates in format YYYY-MM-DD",
            "Write a regex that validates a URL starting with http:// or https://",
            "Write a regex that matches hex color codes like #FF5733 or #fff",
            "Write a regex that extracts all hashtags from a tweet",
            "Write a regex that matches IPv4 addresses",
            "Write a regex that validates a strong password: 8+ chars, uppercase, lowercase, digit, special char",
            "Write a regex that matches credit card numbers (4 groups of 4 digits, optionally separated by spaces or dashes)",
            "Write a regex that extracts the domain from an email address",
            "Write a regex that matches time in 24-hour format HH:MM",
        ],
        "medium": [
            "Write a regex that parses a log line format: '[TIMESTAMP] LEVEL: message (key=value, key=value)' and captures each component",
            "Write a regex that validates and parses a semantic version string (e.g., 1.2.3-beta.1+build.123)",
            "Write a regex that matches balanced HTML tags (opening and closing) but not self-closing tags",
            "Write a Python function using regex to convert camelCase to snake_case and vice versa",
            "Write a regex that validates a complex SQL WHERE clause: column operator value, with AND/OR connectors",
            "Write a regex that extracts all function definitions from Python source code (def name(args):)",
            "Write a Python function that uses regex to syntax-highlight Python code by wrapping keywords, strings, and comments in HTML spans",
            "Write a regex that parses a cron expression and validates each field",
        ],
        "hard": [
            "Write a complete tokenizer for a simple programming language using regex. Tokens: keywords, identifiers, numbers (int/float), strings (with escape sequences), operators, and comments.",
            "Write a Python function that uses regex to parse and evaluate simple mathematical expressions with +, -, *, /, parentheses, respecting operator precedence",
            "Write a regex-based Markdown to HTML converter that handles: headings, bold, italic, links, code blocks, and lists",
            "Write a function that uses regex to detect and extract structured data from unstructured text: dates, currencies, percentages, phone numbers, and email addresses",
        ],
        "extreme": [
            "Implement a complete regex engine from scratch in Python that supports: literal chars, character classes, quantifiers (*, +, ?), anchors (^, $), groups, alternation, and backreferences",
            "Write a regex-based natural language date parser that handles: 'next Tuesday', 'in 3 days', 'March 15th 2024', 'last week', 'tomorrow at 3pm' and returns a normalized datetime",
        ],
    },
}


# ── Task generation ───────────────────────────────────────────────────

# Distribution per category: how many tasks per difficulty
# Total ~200 per category × 20 categories = ~4000 tasks
DISTRIBUTION = {
    "easy":    60,
    "medium":  80,
    "hard":    50,
    "extreme": 10,
}


def _generate_category_tasks(
    category: str,
    spec: dict,
    rng: random.Random,
) -> list[Task]:
    """Generate tasks for one category using templates and variants."""
    tasks = []
    criteria = spec.get("criteria", [])
    tools = spec.get("tools", [])

    for difficulty, count in DISTRIBUTION.items():
        templates = spec.get(difficulty, [])
        if not templates:
            continue

        config = DIFFICULTY_CONFIG[difficulty]

        for i in range(count):
            template_idx = i % len(templates)
            variant_num = i // len(templates)
            base_prompt = templates[template_idx]

            # Create variant text for repeated templates
            if variant_num == 0:
                prompt = base_prompt
            elif variant_num == 1:
                prompt = f"{base_prompt}\n\nPlease provide a detailed solution with explanation."
            elif variant_num == 2:
                prompt = f"{base_prompt}\n\nOptimize for readability and include comments."
            elif variant_num == 3:
                prompt = f"{base_prompt}\n\nInclude edge case handling."
            elif variant_num == 4:
                prompt = f"{base_prompt}\n\nWrite this in a production-ready style."
            else:
                prompt = f"{base_prompt} (approach {variant_num})"

            task_id = f"{category}_{difficulty}_{i+1:03d}"

            tasks.append(Task(
                task_id=task_id,
                category=category,
                difficulty=difficulty,
                input=prompt,
                max_price=config["max_price"],
                min_quality=config["min_quality"],
                timeout=config["timeout"],
                quality_criteria=criteria,
                expected_tools=tools,
                metadata={"template_idx": template_idx, "variant": variant_num},
            ))

    return tasks


def load_task_bank() -> list[Task]:
    """Load the full task bank (~4,000 tasks across 20 categories).

    Returns:
        List of Task objects, deterministically ordered.
    """
    rng = random.Random(42)
    all_tasks = []

    for category, spec in CATEGORIES.items():
        all_tasks.extend(_generate_category_tasks(category, spec, rng))

    return all_tasks


def load_tasks_by_difficulty(difficulty: str) -> list[Task]:
    """Return all tasks of a given difficulty."""
    return [t for t in load_task_bank() if t.difficulty == difficulty]


def load_tasks_by_category(category: str) -> list[Task]:
    """Return all tasks in a given category."""
    return [t for t in load_task_bank() if t.category == category]


if __name__ == "__main__":
    tasks = load_task_bank()
    print(f"Total tasks: {len(tasks)}")
    print()

    print("By difficulty:")
    for diff in ["easy", "medium", "hard", "extreme"]:
        count = len(load_tasks_by_difficulty(diff))
        print(f"  {diff}: {count}")
    print()

    print("By category:")
    categories = sorted(set(t.category for t in tasks))
    for cat in categories:
        count = len([t for t in tasks if t.category == cat])
        print(f"  {cat}: {count}")
