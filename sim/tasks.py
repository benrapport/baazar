"""
LLM Agent Simulation Task Bank
~4,000 tasks across 20 categories with difficulty distribution.
Mix of code/technical + business/creative/real-world tasks.
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
# ~8 code/technical + ~12 business/creative/real-world = 20 categories

CATEGORIES = {
    # ================================================================
    # CODE / TECHNICAL (8 categories)
    # ================================================================

    "code_generation": {
        "criteria": ["Code is syntactically correct", "Function solves the stated problem", "Includes docstring or comments"],
        "tools": ["execute_python"],
        "easy": [
            "Write a Python function that reverses a string",
            "Write a Python function that checks if a string is a palindrome",
            "Write a Python function that returns True if a number is even",
            "Write a Python function that calculates n factorial",
            "Write a Python function that counts vowels in a string",
            "Write a Python function that removes duplicates from a list while preserving order",
            "Write a Python function that checks if a number is prime",
            "Write a Python function that returns the nth Fibonacci number",
            "Write a Python function that merges two sorted lists into one sorted list",
            "Write a Python function that rotates a list by k positions",
        ],
        "medium": [
            "Implement merge sort in Python",
            "Implement binary search for a sorted list",
            "Implement a singly linked list with insert/delete/search",
            "Write a function that validates balanced parentheses including {}, [], ()",
            "Write a Python decorator that caches function results (memoization)",
            "Implement a priority queue using a min-heap",
            "Write a function that converts a Roman numeral string to an integer",
            "Implement a basic LRU cache with O(1) get and put",
            "Implement quicksort with random pivot selection",
            "Implement a circular buffer (ring buffer) class",
        ],
        "hard": [
            "Implement a self-balancing AVL tree with insertion and deletion",
            "Solve the coin change problem using dynamic programming, returning both count and coins used",
            "Implement the 0/1 knapsack problem with backtracking and memoization",
            "Implement Dijkstra's shortest path algorithm with a priority queue",
            "Write a function that solves N-Queens and returns all valid board configurations",
        ],
        "extreme": [
            "Implement a B+ tree database index with range queries",
            "Build a consistent hashing ring for distributed key-value storage",
            "Create a parser and evaluator for a simple expression language with variables, functions, and control flow",
        ],
    },

    "debugging": {
        "criteria": ["Bug is correctly identified", "Fix resolves the root cause", "Explanation is clear"],
        "tools": ["execute_python"],
        "easy": [
            "Fix this function — it should return the sum but adds an extra 1:\ndef add(a, b):\n    return a + b + 1",
            "Fix this function — it should reverse a string:\ndef reverse(s):\n    return s[1:]",
            "Fix this function — it should check if a number is even:\ndef is_even(n):\n    return n % 2 == 1",
            "Fix this function — it should return the last element:\ndef last(lst):\n    return lst[len(lst)]",
            "Fix this function — it should check if a list is sorted:\ndef is_sorted(lst):\n    for i in range(len(lst)):\n        if lst[i] > lst[i+1]:\n            return False\n    return True",
            "Fix this function — it should compute the power:\ndef power(base, exp):\n    result = 0\n    for _ in range(exp):\n        result *= base\n    return result",
        ],
        "medium": [
            "Debug this binary search — it goes into an infinite loop on certain inputs:\ndef binary_search(arr, target):\n    lo, hi = 0, len(arr)\n    while lo < hi:\n        mid = (lo + hi) // 2\n        if arr[mid] == target: return mid\n        elif arr[mid] < target: lo = mid\n        else: hi = mid\n    return -1",
            "Debug this merge sort — it produces wrong results (missing the remaining elements after the while loop):\ndef merge_sort(arr):\n    if len(arr) <= 1: return arr\n    mid = len(arr) // 2\n    left = merge_sort(arr[:mid])\n    right = merge_sort(arr[mid:])\n    result, i, j = [], 0, 0\n    while i < len(left) and j < len(right):\n        if left[i] < right[j]: result.append(left[i]); i += 1\n        else: result.append(right[j]); j += 1\n    return result",
            "Debug this linked list — delete_node doesn't work for the head node:\nclass Node:\n    def __init__(self, val, next=None): self.val, self.next = val, next\ndef delete_node(head, val):\n    curr = head\n    while curr.next:\n        if curr.next.val == val: curr.next = curr.next.next; return head\n        curr = curr.next\n    return head",
            "Debug this memoized fibonacci — recursive calls don't pass the memo dict:\ndef fib(n, memo={}):\n    if n in memo: return memo[n]\n    if n <= 1: return n\n    result = fib(n-1) + fib(n-2)\n    memo[n] = result\n    return result",
        ],
        "hard": [
            "Debug this LRU cache — eviction pops the wrong end (should pop the oldest, not newest):\nfrom collections import OrderedDict\nclass LRUCache:\n    def __init__(self, cap): self.cap, self.cache = cap, OrderedDict()\n    def get(self, key):\n        if key in self.cache: self.cache.move_to_end(key); return self.cache[key]\n        return -1\n    def put(self, key, val):\n        self.cache[key] = val\n        if len(self.cache) > self.cap: self.cache.popitem(last=True)",
            "Debug this event emitter — removing listeners during emit causes skipped callbacks:\nclass EventEmitter:\n    def __init__(self): self.listeners = {}\n    def on(self, event, fn): self.listeners.setdefault(event, []).append(fn)\n    def off(self, event, fn): self.listeners[event].remove(fn) if event in self.listeners else None\n    def emit(self, event, *args):\n        for fn in self.listeners.get(event, []): fn(*args)",
            "Debug this rate limiter — it allows bursts beyond the limit due to floating-point precision:\nimport time\nclass RateLimiter:\n    def __init__(self, max_calls, period): self.max_calls, self.period, self.calls = max_calls, period, []\n    def allow(self):\n        now = time.time()\n        self.calls = [t for t in self.calls if now - t < self.period]\n        if len(self.calls) < self.max_calls: self.calls.append(now); return True\n        return False",
        ],
        "extreme": [
            "Debug this distributed lock — it has a TOCTOU race between setnx and expire:\nimport redis, time, uuid\nclass DistributedLock:\n    def __init__(self, client, name, ttl=10):\n        self.client, self.name, self.ttl, self.token = client, f'lock:{name}', ttl, str(uuid.uuid4())\n    def acquire(self):\n        while True:\n            if self.client.setnx(self.name, self.token):\n                self.client.expire(self.name, self.ttl)\n                return True\n            time.sleep(0.1)\n    def release(self):\n        if self.client.get(self.name) == self.token: self.client.delete(self.name)",
        ],
    },

    "data_analysis": {
        "criteria": ["Analysis is methodologically sound", "Conclusions are supported by data", "Results are clearly presented"],
        "tools": ["execute_python"],
        "easy": [
            "Given [23, 45, 12, 67, 34, 89, 56, 78, 90, 11], calculate mean, median, mode, and standard deviation",
            "Parse this CSV and find total revenue:\nProduct,Price,Qty\nWidget,10.50,100\nGadget,25.00,50\nDoohickey,5.75,200",
            "Count the frequency of each word in: 'the cat sat on the mat the cat ate the rat'",
            "Calculate the moving average (window=3) for: [10, 20, 30, 40, 50, 60, 70]",
            "Find the correlation between hours studied [2,3,5,6,8] and test scores [65,70,80,85,95]",
            "Calculate ROI: initial investment $10,000, final value $13,500 after 2 years",
        ],
        "medium": [
            "Analyze this A/B test: Control (n=1000, conversions=50), Treatment (n=1000, conversions=65). Is the difference significant at p<0.05?",
            "Write code to detect outliers using IQR method. Apply to: [12, 15, 14, 10, 102, 13, 16, 11, 15, 14, 200, 13]",
            "Write a function that performs simple linear regression from scratch and returns slope, intercept, and R²",
            "Implement k-means clustering from scratch for 2D points: [(1,2),(2,1),(1,1),(8,8),(9,7),(8,9),(5,5),(4,6)]",
            "Write code to compute a confusion matrix from predicted and actual labels, then calculate precision, recall, F1",
        ],
        "hard": [
            "Build a simple recommendation engine using collaborative filtering from a user-item ratings matrix",
            "Write a complete ETL pipeline: read messy CSV, clean (handle missing values, outliers, type coercion), normalize, output clean dataset with quality report",
            "Implement principal component analysis (PCA) from scratch using eigendecomposition",
        ],
        "extreme": [
            "Build a complete anomaly detection system using Isolation Forest from scratch: training, scoring, threshold selection, visualization",
        ],
    },

    "system_design": {
        "criteria": ["Design addresses scalability", "Trade-offs are articulated", "Components are well-defined"],
        "tools": [],
        "easy": [
            "Design a simple URL shortener. What components do you need?",
            "Design a basic rate limiter for an API. What algorithm would you use?",
            "Design a simple key-value cache with TTL expiration",
            "Design a basic task queue system. How do producers and consumers interact?",
            "Design a simple feature flag system for a web application",
            "Design a basic health check system for monitoring multiple services",
        ],
        "medium": [
            "Design a notification system supporting email, SMS, and push with delivery guarantees",
            "Design a real-time leaderboard for a game with millions of players",
            "Design a file storage service like Dropbox with syncing, versioning, and conflict resolution",
            "Design a search autocomplete system serving suggestions in under 100ms for 10M terms",
            "Design a metrics collection and alerting system for monitoring microservices",
        ],
        "hard": [
            "Design a distributed message queue like Kafka with partitioning, replication, and consumer groups",
            "Design a real-time fraud detection system for credit card transactions at 10,000 TPS with sub-100ms latency",
            "Design a multi-tenant SaaS platform with data isolation and per-tenant rate limiting",
        ],
        "extreme": [
            "Design a complete stock exchange matching engine with order types, matching algorithms, market data distribution, and fault tolerance",
        ],
    },

    "sql_database": {
        "criteria": ["Query is syntactically correct", "Query produces correct results", "Query is efficient"],
        "tools": ["execute_python"],
        "easy": [
            "Write SQL to select all users who signed up in the last 30 days",
            "Write SQL to count orders per customer",
            "Write SQL to find the top 5 most expensive products",
            "Write SQL to find all employees whose salary is above the company average",
            "Write SQL to find duplicate email addresses in a users table",
            "Write SQL to get total revenue by month from an orders table",
        ],
        "medium": [
            "Write SQL using window functions to calculate a running total of daily sales",
            "Write SQL using CTEs to build an org chart hierarchy from an employees table with manager_id",
            "Write SQL to calculate customer retention: for each monthly cohort, what % are still active after 1, 3, 6 months?",
            "Write SQL to implement cursor-based pagination instead of OFFSET",
            "Design a database schema for a multi-tenant SaaS application",
        ],
        "hard": [
            "Write SQL to implement complete funnel analysis: signup → activation → first purchase → repeat purchase with conversion rates",
            "Design a time-series DB schema optimized for high-speed writes and efficient range queries with auto-partitioning",
            "Write SQL to implement a complete audit trail with row-level change tracking and rollback capability",
        ],
        "extreme": [
            "Design a complete multi-region sharding strategy: shard key selection, cross-shard queries, rebalancing, migration plan",
        ],
    },

    "security": {
        "criteria": ["Vulnerability is correctly identified", "Remediation is appropriate", "Security reasoning is sound"],
        "tools": ["execute_python"],
        "easy": [
            "What is SQL injection? Give an example of vulnerable code and the fix.",
            "What is XSS? Explain stored vs reflected XSS.",
            "Review this code:\npassword = request.form['password']\nquery = f\"SELECT * FROM users WHERE password = '{password}'\"",
            "What is CSRF and how do CSRF tokens prevent it?",
            "Explain why storing passwords in plain text is dangerous and what to do instead",
            "What are the security risks of using eval() in Python?",
        ],
        "medium": [
            "Design a secure password reset flow. What are common pitfalls?",
            "Review this file upload handler for security issues:\ndef upload(file):\n    filename = file.filename\n    file.save(f'/uploads/{filename}')\n    return f'<img src=\"/uploads/{filename}\">'",
            "Design a secure API key rotation strategy that doesn't cause downtime",
            "Explain the OWASP Top 10 vulnerabilities with a one-line mitigation for each",
            "Design a secure session management system covering creation, storage, expiration, invalidation",
        ],
        "hard": [
            "Design a complete zero-trust security architecture for a microservices platform",
            "Explain how a timing side-channel attack works against password comparison. Write both vulnerable and fixed code.",
            "Design a secrets management system for Kubernetes: encryption at rest, rotation, access control, audit",
        ],
        "extreme": [
            "Design a complete threat model for a fintech application handling PCI data: STRIDE analysis, risk matrix, prioritized mitigations",
        ],
    },

    "devops": {
        "criteria": ["Configuration is correct", "Best practices followed", "Infrastructure is secure and scalable"],
        "tools": [],
        "easy": [
            "Write a Dockerfile for a Python Flask application",
            "Write a docker-compose.yml for a web app with PostgreSQL and Redis",
            "Write a GitHub Actions workflow that runs tests on every PR",
            "Write an nginx config that serves static files and reverse proxies /api to port 8080",
            "Write a systemd service file for a Node.js application",
            "Write a crontab entry that runs a backup script every day at 2am",
        ],
        "medium": [
            "Write a multi-stage Dockerfile producing a minimal Go production image under 20MB",
            "Write a Kubernetes deployment with rolling updates, health checks, and HPA",
            "Design a blue-green deployment strategy with traffic switching scripts",
            "Write a database backup script: compress, encrypt with GPG, upload to S3, retention policy, Slack notification on failure",
            "Write Prometheus alerting rules for: high error rate, high latency, disk space, memory usage",
        ],
        "hard": [
            "Design a CI/CD pipeline for a monorepo with 5 microservices: selective builds, parallel testing, canary deploys, auto-rollback",
            "Design a disaster recovery strategy for a multi-region app with RTO/RPO targets and automated DR testing",
        ],
        "extreme": [
            "Design a complete internal developer platform with self-service provisioning, golden path templates, service catalog, and cost dashboards",
        ],
    },

    "testing": {
        "criteria": ["Tests cover important cases", "Edge cases considered", "Tests are readable"],
        "tools": ["execute_python"],
        "easy": [
            "Write unit tests for a function that calculates rectangle area given width and height",
            "Write unit tests for a stack with push, pop, peek, is_empty",
            "Write unit tests for a function that checks if a string is a valid palindrome",
            "Write unit tests for a simple calculator class with add, subtract, multiply, divide",
            "Write unit tests for a function that parses date strings 'YYYY-MM-DD'",
            "Write unit tests for a function that validates email addresses",
        ],
        "medium": [
            "Write comprehensive tests for a shopping cart: add, remove, update qty, total, discount codes, out-of-stock",
            "Write property-based tests for a sorting function. Define properties any correct sort must satisfy.",
            "Write tests for a rate limiter: 100 requests/minute with time-based mocking",
            "Write tests for a retry decorator: specific exceptions, exponential backoff, max retries",
        ],
        "hard": [
            "Write a test harness for a state machine (order lifecycle: created→paid→shipped→delivered). Cover all valid/invalid transitions.",
            "Design a complete testing strategy for a payment system: unit, integration, contract, and e2e tests with test doubles",
        ],
        "extreme": [
            "Write a comprehensive fuzz testing suite for a JSON parser: random inputs, coverage tracking, input minimization, crash reporting",
        ],
    },

    # ================================================================
    # BUSINESS / REAL-WORLD (12 categories)
    # ================================================================

    "ecommerce": {
        "criteria": ["Content is compelling and accurate", "Targets the right audience", "Follows ecommerce best practices"],
        "tools": [],
        "easy": [
            "Write a product title and 3-bullet description for a stainless steel insulated water bottle",
            "Write a product title and description for a wireless Bluetooth speaker under $50",
            "Write 5 compelling product titles for a set of organic cotton bed sheets",
            "Write a short product comparison between two laptops: a $999 MacBook Air and a $799 Dell XPS 13",
            "Write a 'Frequently Bought Together' recommendation blurb for a camera, memory card, and carrying case",
            "Write a product return policy for a small online clothing store (clear, customer-friendly, 30-day window)",
            "Write 3 variations of a 'Free Shipping' promotional banner headline",
            "Write a size guide description for a unisex t-shirt brand (S through XXL)",
            "Write a compelling 'About Us' section for an artisan coffee roaster that sources beans directly from farmers",
            "Write a product description for a $29 portable phone charger (10,000 mAh) that emphasizes value",
            "Write an abandoned cart email subject line and 2-sentence body copy",
            "Write a thank-you email for a first-time customer who just placed their order",
            "Write a product listing for a handmade leather wallet on Etsy",
            "Write 5 SEO-friendly category page titles for a pet supplies store",
            "Write a seasonal promotion email for a 'Back to School' sale at an office supply store",
        ],
        "medium": [
            "Write a complete product detail page for a $149 robot vacuum: title, key features, description, specs table, and 3 FAQ answers",
            "Create a pricing strategy document for a SaaS tool that wants to introduce a freemium tier alongside existing $29/mo and $99/mo plans",
            "Write a complete email drip campaign (3 emails over 7 days) for re-engaging customers who haven't purchased in 90 days",
            "Design a loyalty program for an online grocery delivery service. Define tiers, rewards, earning rules, and expiration policy.",
            "Write product descriptions for 5 items in a curated 'Gift Guide for Tech Lovers Under $75'",
            "Create an A/B test plan for a checkout flow: define hypothesis, variants, metrics, sample size, and success criteria",
            "Write a complete category landing page for 'Women's Running Shoes' including SEO meta description, hero copy, and filter suggestions",
            "Design the information architecture for a furniture ecommerce site: main categories, subcategories, and filter taxonomy",
            "Write a competitive analysis comparing Shopify, WooCommerce, and BigCommerce for a small business selling handmade jewelry",
            "Create an inventory management SOP for handling low-stock alerts, reorder points, and seasonal demand fluctuations",
        ],
        "hard": [
            "Design a complete marketplace launch plan: seller onboarding, buyer acquisition, trust & safety policies, fee structure, and first 90-day milestones",
            "Create a comprehensive international expansion plan for a US-based DTC brand entering the UK market: logistics, payments, localization, regulatory, tax",
            "Design a dynamic pricing algorithm strategy for a hotel booking platform: factors to consider, implementation approach, guardrails, and A/B testing framework",
            "Write a complete RFP (Request for Proposal) for selecting a new ecommerce platform, including requirements, evaluation criteria, and vendor scorecard",
            "Design a fraud prevention system for an ecommerce marketplace: order screening rules, seller verification, chargeback handling, and appeal process",
        ],
        "extreme": [
            "Design a complete omnichannel commerce strategy for a mid-size retailer: online, mobile app, in-store POS, BOPIS, curbside pickup, social commerce. Include tech stack, data architecture, and phased rollout plan.",
            "Create a comprehensive unit economics model for a subscription box business: CAC, LTV, churn, margins, break-even analysis, and sensitivity scenarios",
        ],
    },

    "image_generation": {
        "criteria": ["Prompt is specific and detailed", "Style and composition are well-defined", "Output is usable for stated purpose"],
        "tools": [],
        "easy": [
            "Write a detailed image generation prompt for a product photo of a minimalist ceramic coffee mug on a wooden table with morning light",
            "Write an image prompt for a social media post announcing a summer sale — bright, energetic, beach vibes",
            "Write an image prompt for a professional headshot background: clean, modern office with soft bokeh",
            "Write an image prompt for a food blog hero image: rustic sourdough bread on a cutting board with olive oil and herbs",
            "Write a prompt for generating a flat-design icon set: shopping cart, heart, star, arrow, and settings gear",
            "Write a prompt for a children's book illustration: a friendly dragon reading a book in a cozy library",
            "Write an image prompt for an app store screenshot background: gradient purple-to-blue with floating geometric shapes",
            "Write a prompt for a stock photo: diverse team of 4 people collaborating around a whiteboard in a bright office",
            "Write a prompt for a logo concept: a sustainable fashion brand called 'Evergreen' — leaf motif, earth tones",
            "Write a prompt for a banner image: a cozy autumn scene with coffee, books, and fall leaves",
            "Write a prompt for an email header image: celebrating 10,000 customers with confetti and a milestone badge",
            "Write a prompt for a thumbnail: a YouTube video about '5 Python Tips' with bold text and a snake graphic",
        ],
        "medium": [
            "Create a complete visual brief for a brand photoshoot: 10 shots needed for a new athleisure clothing line. Specify mood, lighting, models, settings, and props for each shot.",
            "Write 5 image generation prompts for a real estate listing: exterior, living room, kitchen, bedroom, and backyard — each optimized for Zillow-style listings",
            "Design a social media visual content calendar for one week (7 posts) for a coffee shop. Specify each image prompt, platform dimensions, and text overlay.",
            "Write detailed prompts for a set of 4 seasonal product photos for a candle company: spring, summer, fall, winter — each with appropriate styling and mood",
            "Create an image prompt sequence for a 5-slide Instagram carousel explaining 'How Our Sustainable Packaging Works' — each slide described in detail",
            "Write prompts for 3 hero banner variations for A/B testing on a meal kit delivery homepage",
            "Design a complete set of UI illustration prompts for a fintech app's onboarding flow: welcome, connect bank, set budget, first insight, celebration",
            "Write prompts for a series of 6 blog post feature images for articles about remote work, each with a distinct but cohesive style",
        ],
        "hard": [
            "Create a complete brand identity visual system: write detailed prompts for logo (3 variations), color palette mood boards, typography pairing examples, iconography set, and brand pattern/texture",
            "Design a complete pitch deck visual template (12 slides). Write the image/illustration prompt for each slide background: title, problem, solution, market size, product, traction, team, business model, competition, financials, ask, closing.",
            "Create a comprehensive product photography style guide with example prompts for 6 different product categories (electronics, food, fashion, furniture, cosmetics, toys). Define lighting setup, composition rules, and post-processing style.",
            "Write detailed prompts for a complete children's picture book (8 pages/scenes). Maintain consistent character design, art style, and world-building across all pages.",
        ],
        "extreme": [
            "Design a complete visual identity system for a fictional luxury hotel chain. Write prompts for: 20 brand photography shots, 10 marketing collateral pieces, 5 social media templates, architectural visualization, and environmental design elements. Include a style guide document.",
            "Create a comprehensive visual asset library spec for a mobile game: character designs (5 characters with 3 poses each), environment art (4 worlds), UI elements, promotional materials, and app store assets. Write detailed prompts for each.",
        ],
    },

    "marketing": {
        "criteria": ["Copy is compelling and on-brand", "Strategy is sound", "Targets the right audience"],
        "tools": [],
        "easy": [
            "Write 5 subject lines for an email promoting a 30% off Black Friday sale at an online shoe store",
            "Write a 280-character tweet announcing the launch of a new project management tool",
            "Write a Google Ads headline and description for a local plumber (max 30 chars headline, 90 chars description)",
            "Write 3 Instagram caption variations for a photo of a new menu item at a brunch restaurant",
            "Write a short 'About' section for a LinkedIn company page for a B2B data analytics startup",
            "Write a push notification for a food delivery app: 'Your favorite restaurant has a new dish'",
            "Write a call-to-action button text and surrounding copy for a free trial signup page",
            "Write a referral program invitation message: 'Give $10, Get $10' for a subscription box service",
            "Write a brief press release headline and opening paragraph for a Series A funding announcement ($12M)",
            "Write 3 variations of a value proposition statement for a password manager app",
            "Write a Google My Business post for a new yoga studio offering a free first class",
            "Write an SMS marketing message (under 160 chars) for a flash sale ending tonight",
            "Write a TikTok video hook (first 3 seconds script) for a cooking gadget demonstration",
            "Write a podcast ad read (30 seconds) for a mattress company",
            "Write a testimonial request email to send to happy customers",
        ],
        "medium": [
            "Create a complete content marketing strategy for a B2B cybersecurity company targeting mid-market CISOs. Include: content pillars, formats, distribution channels, and 3-month editorial calendar.",
            "Write a complete landing page: headline, subhead, 3 benefit sections with copy, social proof section, FAQ, and CTA — for a time-tracking app aimed at freelancers",
            "Design a complete email marketing funnel for a SaaS product: welcome email, feature highlight series (3 emails), trial expiring reminder, and win-back sequence",
            "Create a social media launch strategy for a new plant-based protein bar: pre-launch teasers, launch day posts, influencer outreach templates, and first-week engagement plan",
            "Write a complete case study (500 words) about how a fictional mid-size retailer increased online sales by 40% using your analytics platform",
            "Create a competitive positioning document: compare your project management tool against Asana, Monday.com, and ClickUp. Define your unique selling points and objection handlers.",
            "Design a webinar marketing campaign: topic, title, landing page copy, 3 promotional emails, social posts, and follow-up sequence",
            "Write a complete brand messaging framework: mission, vision, brand promise, elevator pitch, key messages for 3 audience segments",
            "Create an influencer marketing brief for a skincare brand launch: target influencer profiles, content requirements, talking points, and compensation structure",
            "Design a customer re-engagement campaign using email, SMS, and retargeting ads for an ecommerce store with 30% of customers inactive for 6+ months",
        ],
        "hard": [
            "Create a comprehensive go-to-market strategy for launching a new fintech app in a crowded market: positioning, pricing, channel strategy, partnerships, PR plan, and first-year milestones with budget allocation",
            "Design a complete brand refresh strategy for a 20-year-old B2B software company that needs to modernize. Cover: research plan, messaging architecture, visual identity direction, rollout plan, and internal change management.",
            "Write a detailed marketing attribution analysis framework: define the models (first-touch, last-touch, linear, time-decay, data-driven), implementation requirements, and how to use insights to optimize channel spend",
            "Create a comprehensive international marketing localization guide for expanding a US consumer brand to Japan, Germany, and Brazil. Cover cultural adaptation, messaging, channel mix, and compliance per market.",
        ],
        "extreme": [
            "Design a complete product-led growth (PLG) engine: viral loops, in-product upsells, usage-based triggers, referral mechanics, community strategy, and growth metrics framework with benchmarks",
            "Create a year-long integrated marketing plan for a $50M ARR B2B SaaS company: brand, demand gen, product marketing, customer marketing, partner marketing, and analyst relations — with quarterly goals, budget allocation, and team structure",
        ],
    },

    "customer_support": {
        "criteria": ["Response is helpful and empathetic", "Solution is actionable", "Tone is appropriate"],
        "tools": [],
        "easy": [
            "Write a customer support response to: 'I ordered a blue shirt but received a red one. I want a replacement.'",
            "Write a support reply to: 'My password reset email never arrived. I've checked spam.'",
            "Write a friendly response to: 'When will my order arrive? Tracking says it's been in transit for 5 days.'",
            "Write a support response to: 'I was charged twice for my subscription this month.'",
            "Write a reply to: 'How do I cancel my account? I can't find the option in settings.'",
            "Write a response to a 1-star review: 'Terrible product, broke after one week. Total waste of money.'",
            "Write a support reply to: 'I need to change the shipping address on an order I placed 2 hours ago.'",
            "Write a response to: 'Your app keeps crashing on my iPhone. This is very frustrating.'",
            "Write a reply to: 'Can I get a refund? I bought this 45 days ago and your policy says 30 days.'",
            "Write a proactive email to customers affected by a 2-hour service outage that has been resolved",
            "Write a response to: 'I'm a premium subscriber but I'm not getting premium features.'",
            "Write a chat support response to: 'I forgot what email I signed up with. Can you help me find my account?'",
        ],
        "medium": [
            "Write a complete escalation response for a customer threatening legal action over a data privacy concern",
            "Create a template response library (5 templates) for the most common support tickets at a SaaS company: billing issues, feature requests, bug reports, account access, and cancellation",
            "Write a detailed troubleshooting guide for customers experiencing 'payment failed' errors — cover the 5 most common causes and step-by-step resolutions",
            "Draft a customer communication for a security breach notification: what happened, what we're doing, what the customer should do, and ongoing protection measures",
            "Write a series of 3 de-escalation messages for an increasingly angry customer who has been bounced between 4 support agents over a billing dispute",
            "Create a complete knowledge base article: 'How to Set Up Two-Factor Authentication' with step-by-step instructions for web, iOS, and Android",
            "Write a product recall notification email: a batch of wireless earbuds has a battery safety issue. Include: what happened, who's affected, what to do, compensation offered.",
            "Create a customer satisfaction survey (CSAT) email with 5 targeted questions and a friendly intro/outro",
        ],
        "hard": [
            "Design a complete customer support operations playbook for a Series B startup scaling from 5 to 25 support agents: hiring criteria, training program, quality assurance, escalation paths, tooling stack, and KPI targets",
            "Create a comprehensive crisis communication plan for a major service outage: internal escalation, status page updates, customer emails, social media responses, post-mortem template, and SLA credit process",
            "Design a support chatbot conversation flow for handling returns: gather order info, determine eligibility, offer resolution options (refund/exchange/credit), process the return, and seamlessly escalate to human when needed",
            "Write a detailed analysis and improvement plan for a support team with these metrics: CSAT 72% (target 85%), first response time 4h (target 1h), resolution time 48h (target 24h), ticket volume growing 20%/month",
        ],
        "extreme": [
            "Design a complete omnichannel customer experience strategy: unify support across email, chat, phone, social, and in-app. Define routing logic, agent workflows, handoff protocols, knowledge management, and predictive support using product usage data.",
            "Create a comprehensive VoC (Voice of Customer) program: feedback collection across all touchpoints, sentiment analysis framework, insight-to-action pipeline, cross-functional sharing cadence, and measurable impact tracking",
        ],
    },

    "business_strategy": {
        "criteria": ["Analysis is rigorous", "Recommendations are actionable", "Assumptions are stated"],
        "tools": [],
        "easy": [
            "What are Porter's Five Forces? Apply them briefly to the ride-sharing industry.",
            "Explain the difference between a red ocean and blue ocean strategy with one example each",
            "What is a SWOT analysis? Create one for a local independent bookstore competing with Amazon",
            "Explain the concept of product-market fit. How do you know when you've achieved it?",
            "What is the difference between a moat and a competitive advantage? Give 3 examples of moats.",
            "Explain the Lean Startup methodology in 5 key principles",
            "What is a TAM/SAM/SOM analysis? Calculate for a dog-walking app in the US.",
            "Explain the freemium business model. What metrics determine if it's working?",
            "What is customer acquisition cost (CAC) and why does the CAC:LTV ratio matter?",
            "Explain the 'jobs to be done' framework with an example for a meal delivery service",
            "What is a value chain analysis? Apply it briefly to a coffee shop",
            "Explain network effects with examples of direct vs indirect network effects",
        ],
        "medium": [
            "Analyze whether a direct-to-consumer mattress company should open physical retail stores. Cover: financial model, cannibalization risk, brand impact, and recommendation.",
            "Create a business case for a SaaS company to move from monthly to annual billing. Include: revenue impact, churn implications, cash flow, and transition plan.",
            "Analyze the subscription vs one-time purchase model for a premium productivity app. Which maximizes 5-year revenue? Include assumptions and sensitivity analysis.",
            "Write a market entry analysis for a US-based fintech company considering expansion to India: market size, regulatory landscape, competition, and go-to-market approach",
            "Create a pricing strategy for a new B2B API product. Analyze: per-call pricing, tiered plans, usage-based, and hybrid models. Recommend one with rationale.",
            "Analyze the buy vs build decision for adding AI features to a CRM product. Cover: cost, time-to-market, competitive risk, and strategic alignment.",
            "Write a competitive response plan: your #2 competitor just raised $100M and is cutting prices 30%. What should you do?",
            "Design a partnership strategy for a health & wellness app: potential partner types, value exchange, deal structure, and success metrics",
        ],
        "hard": [
            "Create a comprehensive 3-year strategic plan for a $20M ARR B2B SaaS company looking to reach $100M. Cover: market expansion, product strategy, GTM, team scaling, and capital requirements.",
            "Analyze the strategic implications of AI on the management consulting industry. Who wins, who loses, and what new business models emerge?",
            "Design a complete M&A integration playbook for a SaaS company acquiring a competitor: due diligence checklist, Day 1 plan, product integration roadmap, customer communication, and team retention strategy",
            "Create a detailed platform strategy analysis: should a vertical SaaS company build a marketplace/platform ecosystem? Analyze network effects, economics, competitive dynamics, and execution risk.",
        ],
        "extreme": [
            "Design a complete business model for a two-sided marketplace in healthcare (connecting patients with specialists). Cover: value propositions for both sides, monetization, regulatory strategy, cold start problem, unit economics, and path to profitability.",
            "Write a comprehensive disruption analysis for the traditional banking industry: identify the most vulnerable segments, emerging competitors, technological enablers, regulatory catalysts, and build a scenario-planning framework with 4 possible futures.",
        ],
    },

    "finance": {
        "criteria": ["Calculations are correct", "Financial reasoning is sound", "Assumptions are clearly stated"],
        "tools": ["math_eval"],
        "easy": [
            "Calculate compound interest: $10,000 at 5% annually for 10 years, compounded monthly",
            "A company has revenue of $500K and expenses of $380K. Calculate the profit margin percentage.",
            "Calculate the break-even point: fixed costs $50,000/month, price per unit $25, variable cost per unit $10",
            "What is the present value of $100,000 received 5 years from now at a 7% discount rate?",
            "Calculate the monthly payment on a $300,000 mortgage at 6.5% APR for 30 years",
            "A stock costs $150 and pays a $3 annual dividend. What is the dividend yield?",
            "Calculate the debt-to-equity ratio: total debt $2M, total equity $5M. Is this healthy?",
            "If a company's P/E ratio is 25 and EPS is $4, what is the stock price?",
            "Calculate the payback period: investment of $100,000, annual cash flow of $30,000",
            "What is the gross margin? Revenue $1.2M, COGS $480K.",
            "Calculate the Rule of 72: how long to double money at 8% annual return?",
            "A portfolio has $50K in stocks (return 10%), $30K in bonds (return 4%), $20K in cash (return 1%). What's the weighted average return?",
        ],
        "medium": [
            "Build a DCF (Discounted Cash Flow) model: free cash flows of $1M growing 15% for 5 years, then 3% terminal growth. WACC = 10%. What is the enterprise value?",
            "Analyze a SaaS company's unit economics: CAC $500, monthly price $99, gross margin 80%, monthly churn 3%. Calculate LTV, LTV:CAC ratio, and months to payback.",
            "Create a financial model for a startup raising a $5M Series A at $20M pre-money. Model dilution through Series A, Series B ($15M at $80M pre), and an exit at $500M. What do founders and each investor receive?",
            "Analyze this P&L and identify the 3 biggest concerns:\nRevenue: $10M (+25% YoY)\nGross Margin: 55% (was 65%)\nOpex: $8M (+40% YoY)\nNet Income: -$2.5M (was -$1M)\nBurn Rate: $600K/month\nCash: $4M",
            "Compare leasing vs buying a $50,000 piece of equipment: 5-year lease at $1,100/month vs purchase with $10K down + $800/month loan at 6%. Include tax depreciation benefits.",
            "Build a revenue forecast model for a marketplace: 1,000 sellers, avg 50 listings each, 5% sell-through rate, $40 average order value, 15% take rate. Project monthly revenue for 12 months with 10% monthly seller growth.",
            "Calculate the optimal pricing for a product using price elasticity: current price $50, demand 1000 units. Price elasticity = -1.5. What price maximizes revenue?",
            "Analyze a real estate investment: purchase price $400K, rental income $2,800/month, expenses (taxes, insurance, maintenance) $800/month, 25% down, 7% mortgage rate, 30 years. Calculate cash-on-cash return and cap rate.",
        ],
        "hard": [
            "Build a complete three-statement financial model (income statement, balance sheet, cash flow) for a SaaS company with these assumptions: $5M ARR growing 50%, 70% gross margin, $8M opex, $3M cash. Project 3 years.",
            "Design a venture capital fund model: $100M fund, 2% management fee, 20% carry over 8% hurdle. Model deployment over 4 years, 30 investments, power law returns, and calculate GP economics.",
            "Analyze the financial impact of switching from perpetual licenses to subscription pricing for an enterprise software company with $50M in license revenue and 18% maintenance stream.",
            "Create a complete budget and financial plan for a startup's first 18 months: headcount plan, burn rate, cash runway, fundraising timeline, and key financial milestones for next raise.",
        ],
        "extreme": [
            "Build a complete LBO (Leveraged Buyout) model: acquire a $200M revenue company at 10x EBITDA, 60% leverage at 6% interest, 5-year hold. Model debt paydown, operational improvements (margin expansion from 20% to 25%), and calculate IRR at various exit multiples.",
            "Design a comprehensive treasury management strategy for a $500M revenue company: cash management, FX hedging, investment policy, credit facility structure, and scenario analysis for interest rate and currency movements.",
        ],
    },

    "product_management": {
        "criteria": ["Requirements are clear and complete", "User needs are centered", "Prioritization is justified"],
        "tools": [],
        "easy": [
            "Write a user story for a customer who wants to save items to a wishlist on an ecommerce site",
            "Write 3 acceptance criteria for a 'forgot password' feature",
            "Prioritize these 5 features using the RICE framework: dark mode, export to PDF, team collaboration, mobile app, SSO integration",
            "Write a brief product requirements document for adding a 'sort by' dropdown to a product listing page",
            "Define success metrics (KPIs) for a new onboarding flow for a project management tool",
            "Write a problem statement for: 'Users are abandoning the checkout flow at the payment step (60% drop-off)'",
            "Create a simple feature comparison matrix: your product vs 2 competitors across 8 features",
            "Write a release note for a feature that lets users schedule email sends for a specific date and time",
            "Define the MVP scope for a habit-tracking mobile app. What's in V1 and what's deferred?",
            "Write a one-pager product brief for adding Stripe payment processing to an existing SaaS app",
            "Create a user persona for the primary user of a B2B expense management tool",
            "Write a product FAQ for a new feature: automatic invoice generation from time tracking entries",
        ],
        "medium": [
            "Write a complete PRD (Product Requirements Document) for a real-time collaboration feature in a document editor. Include: problem, goals, user stories, requirements, design considerations, and success metrics.",
            "Create a product roadmap for Q3-Q4 with 3 themes, 8 features, and clear prioritization rationale. The product is a CRM for small businesses.",
            "Design a complete experimentation framework for a consumer app: hypothesis format, experiment design template, statistical rigor requirements, and decision framework",
            "Write a product strategy document for adding AI features to an existing note-taking app: use cases, build vs buy analysis, data requirements, and phased rollout plan",
            "Create a complete user research plan for understanding why trial-to-paid conversion is only 5%: research questions, methodology, participant criteria, interview guide, and analysis framework",
            "Design a notification system product spec: channels (email, push, in-app, SMS), user preferences, frequency capping, and do-not-disturb rules",
            "Write a product brief for migrating a monolithic web app to a micro-frontend architecture. Frame it in terms of user and business impact, not just technical benefits.",
            "Create a pricing page strategy document: define tiers, feature gating approach, upgrade triggers, and A/B testing plan for a B2B SaaS product",
        ],
        "hard": [
            "Design a complete product-led onboarding experience for a complex B2B analytics tool: activation milestones, tooltip tours, sample data, in-app guidance, email nurture, and measurement framework",
            "Create a comprehensive platform API strategy: identify which internal features to expose, design the developer experience, plan the ecosystem, define rate limits and monetization, and write the first 3 pages of developer documentation",
            "Write a detailed product strategy for entering the enterprise segment as a product that currently serves SMBs. Cover: feature gaps, pricing changes, sales motion, security/compliance, and migration path.",
            "Design a complete marketplace trust & safety system: content moderation, user verification, dispute resolution, fraud detection, and appeals process with escalation tiers",
        ],
        "extreme": [
            "Create a comprehensive product vision and 3-year strategy for a new vertical SaaS company targeting the restaurant industry. Cover: market analysis, jobs-to-be-done, product architecture, go-to-market, competitive positioning, and key bets.",
            "Design a complete data platform product: define the user personas (analyst, data engineer, business user), core workflows, data governance framework, collaboration features, and ecosystem integrations. Include a phased roadmap from MVP to platform maturity.",
        ],
    },

    "sales": {
        "criteria": ["Message is personalized and relevant", "Value proposition is clear", "CTA is compelling"],
        "tools": [],
        "easy": [
            "Write a cold email to a VP of Engineering introducing a developer productivity tool. Keep it under 100 words.",
            "Write a LinkedIn connection request message to a potential customer you met at a conference",
            "Write 3 variations of a cold call opening line for selling HR software to a mid-size company",
            "Write a follow-up email after a product demo where the prospect said 'looks interesting, let me think about it'",
            "Write a short case study summary (3 sentences) that a sales rep can paste into an email",
            "Write a 'break-up' email — the final touch in a sequence when a prospect hasn't responded to 4 previous emails",
            "Write an upsell email to an existing customer on the Basic plan, encouraging them to upgrade to Pro",
            "Write a voicemail script (30 seconds) for a first outreach to a Director of Marketing",
            "Write a referral request email to a happy customer asking them to introduce you to peers",
            "Write a short ROI statement: 'Companies like yours save $X by using our platform because...'",
            "Write a one-paragraph 'Why Us' section for a sales proposal",
            "Write a congratulatory email to a prospect whose company just announced a funding round — tie it to your product",
        ],
        "medium": [
            "Write a complete 5-email outbound sales sequence for selling a data analytics platform to a CFO. Each email should have a different angle (pain point, social proof, ROI, urgency, breakup).",
            "Create a sales battlecard for competing against your #1 competitor: their strengths, weaknesses, common objections, win themes, and killer questions to ask prospects",
            "Write a complete sales proposal executive summary (1 page) for a $150K annual contract for an enterprise security platform",
            "Design a discovery call framework: 10 questions to ask, what to listen for, qualification criteria, and next-step recommendations based on answers",
            "Create a complete demo script for a 30-minute product demo of a project management tool. Include: agenda, hook, 3 key use cases to show, handling questions, and closing.",
            "Write a mutual action plan (MAP) for a 60-day enterprise sales cycle: key milestones, stakeholders to engage, deliverables, and decision criteria",
            "Create an objection handling guide for the top 5 objections your sales team hears: 'too expensive', 'happy with current solution', 'not a priority right now', 'need to talk to my boss', 'can we get a longer trial?'",
            "Write a customer expansion playbook: identify upsell/cross-sell triggers, talk tracks, timing, and success metrics",
        ],
        "hard": [
            "Design a complete sales enablement program for a team of 20 reps selling a new product line: training curriculum, certification process, content library, deal support model, and effectiveness measurement",
            "Create a comprehensive territory planning model: segment accounts by ICP fit and intent signals, assign to reps, set quotas, and define account-based strategies for top 20 accounts",
            "Write a detailed win/loss analysis framework: interview guide, analysis methodology, pattern identification, and process for turning insights into sales improvements",
            "Design a partner/channel sales program from scratch: partner types, tiers, incentives, enablement, deal registration, and co-selling playbook",
        ],
        "extreme": [
            "Create a complete sales operations playbook for scaling from $5M to $50M ARR: org structure evolution, compensation plan design, tech stack, forecasting methodology, pipeline management, and performance management framework",
            "Design a comprehensive enterprise account-based sales strategy for winning a Fortune 100 company: stakeholder mapping, multi-threading plan, executive engagement strategy, proof of concept design, procurement navigation, and 12-month account plan",
        ],
    },

    "education": {
        "criteria": ["Content is accurate and age-appropriate", "Pedagogy is sound", "Learning objectives are clear"],
        "tools": [],
        "easy": [
            "Explain photosynthesis to a 10-year-old using a simple analogy",
            "Create 5 multiple-choice quiz questions about the solar system for 6th graders",
            "Write a simple explanation of how the internet works for someone who has never used a computer",
            "Create a vocabulary list of 10 words with definitions and example sentences for an ESL intermediate student",
            "Explain the water cycle using only words a 5-year-old would understand",
            "Write 3 discussion questions for a high school class reading 'To Kill a Mockingbird'",
            "Create a simple lesson outline for teaching fractions using pizza slices as a visual aid",
            "Explain the difference between weather and climate to a middle school student",
            "Write a parent-friendly summary of what students learned this week: basic Python programming concepts",
            "Create a 5-minute warm-up activity for a college statistics class to review standard deviation",
            "Write a study guide checklist for a high school student preparing for a US History exam on the Civil War",
            "Explain machine learning to a high school student using the analogy of learning to cook",
        ],
        "medium": [
            "Design a complete 1-hour lesson plan for teaching high school students about supply and demand. Include: learning objectives, hook activity, main instruction, practice exercise, and assessment.",
            "Create a rubric for evaluating college-level persuasive essays: 5 criteria, 4 levels each, with specific descriptors",
            "Write a complete unit plan (5 lessons) for teaching introductory data literacy to 8th graders: reading charts, understanding statistics, spotting misleading data, creating visualizations, and presenting findings",
            "Design a project-based learning assignment for a college business class: students must create a business plan for a sustainable product. Include: deliverables, milestones, team roles, and grading criteria.",
            "Create a differentiated lesson plan for a mixed-ability 4th grade math class learning multiplication: activities for below-grade, at-grade, and above-grade students",
            "Write a complete training module for onboarding new employees at a tech company: 'Understanding Our Product' — learning objectives, pre-work, presentation outline, hands-on exercise, and quiz",
            "Design a flipped classroom lesson on the American Revolution: pre-class video outline, in-class debate activity, and assessment rubric",
            "Create a comprehensive assessment strategy for a 10-week online course: mix of formative and summative assessments, peer review, self-reflection, and final project",
        ],
        "hard": [
            "Design a complete online course curriculum for 'Introduction to Data Science' (8 weeks): weekly topics, learning objectives, readings, coding labs, projects, and assessment plan. Include accessibility considerations.",
            "Create a comprehensive professional development program for teachers learning to integrate AI tools in their classroom: 5 workshop sessions, practice activities, observation protocol, and impact measurement",
            "Design a competency-based assessment framework for a software engineering bootcamp: define competencies, create rubrics, design practical assessments, and build a student progress dashboard spec",
            "Write a detailed proposal for a new interdisciplinary course combining economics and environmental science: course description, weekly topics, team-teaching approach, unique assignments, and program integration plan",
        ],
        "extreme": [
            "Design a complete adaptive learning system for teaching mathematics K-12: define the knowledge graph, diagnostic assessment approach, content sequencing algorithm, intervention triggers, and teacher dashboard. Include equity and accessibility analysis.",
            "Create a comprehensive university program proposal for a new 'AI Ethics and Society' degree: curriculum map (4 years), core and elective courses, capstone requirements, industry partnerships, faculty hiring plan, and accreditation preparation",
        ],
    },

    "legal_compliance": {
        "criteria": ["Legal reasoning is sound", "Requirements are correctly identified", "Advice is practical"],
        "tools": [],
        "easy": [
            "Write a basic terms of service outline for a mobile fitness app. What sections must be included?",
            "Explain the difference between a contractor and an employee for US tax purposes",
            "Write a simple privacy policy summary (plain language) for a weather app that collects location data",
            "What is GDPR? Explain the 5 most important requirements for a US company with EU users.",
            "Write a basic NDA (Non-Disclosure Agreement) template for sharing business ideas with a potential partner",
            "Explain what 'at-will employment' means and name 3 exceptions",
            "Write a cookie consent banner message that complies with GDPR requirements",
            "What is the difference between copyright, trademark, and patent? Give one example of each.",
            "Write a simple freelancer contract template covering: scope, payment, IP ownership, and termination",
            "Explain what SOC 2 compliance means and why SaaS companies need it",
            "Write a basic refund policy for a digital product (online course)",
            "Explain the CAN-SPAM Act: what are the 5 main requirements for commercial emails?",
        ],
        "medium": [
            "Write a comprehensive privacy policy for a SaaS application that: collects user data, uses analytics, stores data in the cloud, and shares data with third-party integrations. Cover GDPR, CCPA, and general best practices.",
            "Create a GDPR compliance checklist for a startup: data mapping, legal basis for processing, consent management, data subject rights, DPA requirements, breach notification procedures",
            "Write an employee handbook section on intellectual property: what the company owns, open source contribution policy, side project policy, and invention assignment",
            "Draft a data processing agreement (DPA) outline for a SaaS vendor relationship: parties, scope, security measures, sub-processors, audit rights, and breach notification",
            "Create a compliance training outline for employees: topics to cover (data privacy, security, harassment, insider trading), delivery format, frequency, and testing requirements",
            "Write a terms of service section covering user-generated content: content ownership, license grant, moderation rights, DMCA takedown process, and liability limitations",
            "Analyze the legal risks of using AI-generated content for marketing: copyright, FTC disclosure, liability, and bias. Provide recommendations.",
            "Draft an acceptable use policy for a cloud platform: prohibited uses, enforcement procedures, account termination, and appeal process",
        ],
        "hard": [
            "Create a comprehensive regulatory compliance roadmap for a fintech startup: money transmission licenses, KYC/AML requirements, state-by-state analysis, compliance team hiring plan, and technology requirements",
            "Design a complete data governance framework for a healthcare tech company: HIPAA compliance, data classification, access controls, audit procedures, incident response, and vendor management",
            "Write a detailed analysis of Section 230 implications for a social media platform implementing AI content moderation: legal risks, editorial vs platform distinction, and recommended policies",
            "Create a comprehensive open source compliance program: license identification, compatibility analysis, contribution policy, and audit procedures for a company using 200+ open source dependencies",
        ],
        "extreme": [
            "Design a complete privacy engineering framework for a global company: privacy by design principles, data flow mapping methodology, privacy impact assessment template, cross-border transfer mechanisms, and automated compliance monitoring",
            "Create a comprehensive regulatory strategy for launching a crypto/DeFi product in the US: SEC, CFTC, FinCEN analysis, state licensing requirements, legal entity structuring, and ongoing compliance operations plan",
        ],
    },

    "operations": {
        "criteria": ["Process is efficient and clear", "Roles are well-defined", "Metrics are measurable"],
        "tools": [],
        "easy": [
            "Write a standard operating procedure (SOP) for processing customer refunds: steps, decision criteria, approvals needed",
            "Create a meeting agenda template for a weekly team standup (15 minutes, 8 people)",
            "Write an onboarding checklist for a new employee's first week: IT setup, meetings, accounts, training",
            "Design a simple ticket triage process: how to categorize, prioritize, and route incoming support tickets",
            "Write a work-from-home policy covering: eligibility, expectations, equipment, communication, and time tracking",
            "Create a vendor evaluation scorecard with 8 criteria and a 1-5 rating scale",
            "Write an incident response checklist for when the website goes down: first 5 minutes, first hour, post-resolution",
            "Design a simple approval workflow for purchase orders: thresholds, approvers, and escalation",
            "Write a quarterly business review (QBR) agenda template with sections and time allocations",
            "Create a project status report template: RAG status, milestones, risks, blockers, next steps",
            "Write a document retention policy: what to keep, how long, and destruction procedures",
            "Design a simple capacity planning worksheet for a customer support team based on ticket volume projections",
        ],
        "medium": [
            "Design a complete incident management process for a SaaS company: severity levels, response times, communication cadence, escalation paths, and post-mortem requirements",
            "Create a change management framework for rolling out a new CRM system to a 200-person sales team: stakeholder analysis, communication plan, training schedule, go-live support, and adoption metrics",
            "Design an OKR (Objectives & Key Results) framework for a 50-person product engineering organization: company-level, team-level, and individual OKR examples with alignment structure",
            "Create a comprehensive employee performance review process: self-assessment, peer feedback, manager review, calibration, and development planning. Include templates.",
            "Design a disaster recovery plan for business operations (not IT): key business functions, RPO/RTO for each, manual workarounds, communication tree, and testing schedule",
            "Create a vendor management framework: procurement process, contract management, performance monitoring, risk assessment, and renewal/termination criteria",
            "Design a knowledge management system for a growing company: content types, ownership, review cadence, search/discovery, and migration plan from current wiki",
            "Create a complete sprint retrospective format that's engaging and actionable: pre-work, facilitation guide, voting mechanism, and action item tracking",
        ],
        "hard": [
            "Design a complete operations scaling playbook for a company going from 50 to 200 employees in 12 months: hiring ops, onboarding, office/remote infrastructure, internal communications, and culture preservation",
            "Create a comprehensive supply chain optimization plan for a DTC brand: demand forecasting, inventory management, warehouse operations, shipping carrier strategy, and cost reduction targets",
            "Design an engineering on-call program: rotation structure, escalation policies, compensation, runbook requirements, alert tuning process, and burnout prevention measures",
            "Create a detailed annual planning process for a $30M company: timeline, inputs, cross-functional alignment, resource allocation, and tracking cadence",
        ],
        "extreme": [
            "Design a complete operating model for a fully remote company of 500 people across 15 time zones: organizational structure, communication architecture, meeting culture, async-first workflows, tool stack, and culture/belonging programs",
            "Create a comprehensive post-merger integration plan for combining two 200-person SaaS companies: day 1 checklist, 30/60/90 plans, organizational design, system consolidation, culture integration, and customer communication strategy",
        ],
    },

    "creative_writing": {
        "criteria": ["Writing is original and engaging", "Meets the specific constraints", "Quality is high"],
        "tools": [],
        "easy": [
            "Write a haiku about debugging code at 3am",
            "Come up with 5 creative names for a startup that makes AI-powered gardening tools",
            "Write a short joke about a programmer who can't find a bug",
            "Write a witty one-liner for a 404 error page",
            "Write 3 creative analogies to explain cloud computing to a grandparent",
            "Write a two-sentence horror story about production deployments",
            "Write a limerick about a data scientist",
            "Come up with 10 creative team names for a hackathon",
            "Write a motivational quote for someone who just deployed to production on a Friday",
            "Write a short poem about the joy of a green CI build",
            "Write a creative 'out of stock' message for a popular product that's both apologetic and builds excitement",
            "Write 5 creative loading screen messages for a travel booking app",
        ],
        "medium": [
            "Write a short story (200-300 words) about an AI that becomes sentient but only cares about optimizing database queries",
            "Create a D&D character sheet for a startup founder, including stats, abilities, and backstory",
            "Write a Shakespearean sonnet about the joys and sorrows of code review",
            "Write a product launch announcement in the style of an Apple keynote for a revolutionary new text editor",
            "Write a fairy tale retelling where the three little pigs are microservices and the big bad wolf is a DDoS attack",
            "Write a cover letter from a rubber duck applying for Senior Debug Assistant",
            "Write a dialogue between two chatbots having an existential crisis about their purpose",
            "Create a fictional tech conference talk abstract: 'Quantum CSS: Styling Elements That Both Exist and Don't Exist'",
            "Write a short satirical news article: 'Local Developer Claims They'll Refactor Legacy Code This Sprint'",
            "Write the opening chapter (300 words) of a thriller where the protagonist discovers their smart home is gaslighting them",
        ],
        "hard": [
            "Write a complete short story (500+ words) set in a world where code compiles on the first try. What goes wrong?",
            "Design a complete board game about startup life: rules, mechanics, cards, and win conditions",
            "Write a script for a 5-minute comedy sketch about a standup meeting that goes horribly wrong",
            "Create a detailed worldbuilding document for a sci-fi universe where programming languages are spoken languages and communities are nations",
            "Write a satirical academic paper abstract about 'Correlation Between Coffee Consumption and Code Quality'",
        ],
        "extreme": [
            "Write a complete one-act play about the tension between a senior engineer who wants to rewrite everything and a PM who just wants to ship",
            "Create an elaborate alternate history where the printing press was invented in ancient China 1000 years earlier. Describe the technological, social, and political implications.",
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
