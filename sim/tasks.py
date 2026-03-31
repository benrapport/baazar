"""
LLM Agent Simulation Task Bank
1,000 tasks across 10 categories with difficulty distribution.
Deterministically generated with seeded randomness for reproducibility.
"""

from dataclasses import dataclass, field
import random
from typing import Optional


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


# ============================================================================
# CATEGORY 1: CODE_GENERATION
# ============================================================================

def _generate_code_generation_tasks() -> list[Task]:
    """100 tasks: 30 easy, 40 medium, 25 hard, 5 extreme."""
    tasks = []
    rng = random.Random(42)

    # Easy templates (30 tasks)
    easy_templates = [
        ("string reversal", "Write a Python function that reverses a string"),
        ("palindrome check", "Write a Python function that checks if a string is a palindrome"),
        ("even/odd", "Write a Python function that returns True if a number is even, False otherwise"),
        ("sum range", "Write a Python function that returns the sum of integers from 1 to n"),
        ("list filter", "Write a Python function that filters a list to keep only even numbers"),
        ("factorial", "Write a Python function that calculates n factorial"),
        ("count vowels", "Write a Python function that counts the number of vowels in a string"),
        ("capitalize first", "Write a Python function that capitalizes the first letter of each word"),
        ("list reverse", "Write a Python function that reverses a list in-place"),
        ("find max", "Write a Python function that finds the maximum value in a list"),
    ]

    for i in range(30):
        template_idx = i % len(easy_templates)
        template, base_prompt = easy_templates[template_idx]
        variant_num = i // len(easy_templates)

        prompt = base_prompt if variant_num == 0 else f"{base_prompt} (variation {variant_num + 1})"

        tasks.append(Task(
            task_id=f"code_gen_easy_{i+1:03d}",
            category="code_generation",
            difficulty="easy",
            input=prompt,
            max_price=0.02,
            min_quality=5,
            timeout=15.0,
            quality_criteria=[
                "Code is syntactically correct",
                "Function solves the stated problem",
                "Includes docstring or comments",
            ],
            expected_tools=["execute_python"],
            metadata={"template": template, "variant": variant_num}
        ))

    # Medium templates (40 tasks)
    medium_templates = [
        ("merge sort", "Implement a merge sort algorithm in Python"),
        ("binary search", "Implement binary search for a sorted list"),
        ("hash table", "Implement a simple hash table class with get/set/delete"),
        ("linked list", "Implement a singly linked list with insert/delete/search"),
        ("anagram check", "Write a function that checks if two strings are anagrams"),
        ("longest substring", "Write a function that finds the longest substring without repeating characters"),
        ("LCM", "Write a function to find the least common multiple of two numbers"),
        ("matrix transpose", "Write a function that transposes a 2D matrix"),
        ("GCD", "Write a function to compute the greatest common divisor using Euclidean algorithm"),
        ("string permutations", "Write a function that generates all permutations of a string"),
    ]

    for i in range(40):
        template_idx = i % len(medium_templates)
        template, base_prompt = medium_templates[template_idx]
        variant_num = i // len(medium_templates)

        prompt = base_prompt if variant_num == 0 else f"{base_prompt} with optimization {variant_num}"

        tasks.append(Task(
            task_id=f"code_gen_medium_{i+1:03d}",
            category="code_generation",
            difficulty="medium",
            input=prompt,
            max_price=0.05,
            min_quality=6,
            timeout=25.0,
            quality_criteria=[
                "Code is correct and handles edge cases",
                "Time complexity is reasonable",
                "Includes error handling",
                "Code is readable with clear variable names",
            ],
            expected_tools=["execute_python"],
            metadata={"template": template, "variant": variant_num}
        ))

    # Hard templates (25 tasks)
    hard_templates = [
        ("AVL tree", "Implement a self-balancing AVL tree with insertion and deletion"),
        ("graph BFS", "Implement breadth-first search on a graph, handling cycles"),
        ("dynamic programming coin change", "Solve the coin change problem using dynamic programming"),
        ("topological sort", "Implement topological sorting for a DAG"),
        ("knapsack", "Implement the 0/1 knapsack problem with backtracking"),
        ("trie", "Implement a trie data structure with insert/search/delete"),
        ("suffix array", "Build a suffix array for pattern matching"),
    ]

    for i in range(25):
        template_idx = i % len(hard_templates)
        template, base_prompt = hard_templates[template_idx]
        variant_num = i // len(hard_templates)

        prompt = base_prompt if variant_num == 0 else f"{base_prompt} (variant {variant_num + 1})"

        tasks.append(Task(
            task_id=f"code_gen_hard_{i+1:03d}",
            category="code_generation",
            difficulty="hard",
            input=prompt,
            max_price=0.15,
            min_quality=7,
            timeout=40.0,
            quality_criteria=[
                "Algorithm is correct and efficient",
                "Handles all edge cases (empty input, single element, etc)",
                "Time/space complexity is optimal or near-optimal",
                "Code is well-documented",
            ],
            expected_tools=["execute_python"],
            metadata={"template": template, "variant": variant_num, "complexity": "high"}
        ))

    # Extreme templates (5 tasks)
    extreme_tasks = [
        ("Implement a concurrent skip list with lock-free operations in Python",
         "Concurrent data structure requiring thread-safe operations"),
        ("Implement a B+ tree database with ACID properties",
         "Complex data structure with transaction support"),
        ("Build a distributed hash table consistent hashing algorithm",
         "Distributed systems algorithm"),
        ("Implement a suffix tree with online construction (Ukkonen's algorithm)",
         "Advanced string algorithm"),
        ("Create a Lua-like scripting language interpreter in Python",
         "Parser and interpreter implementation"),
    ]

    for i, (prompt, description) in enumerate(extreme_tasks):
        tasks.append(Task(
            task_id=f"code_gen_extreme_{i+1:03d}",
            category="code_generation",
            difficulty="extreme",
            input=prompt,
            max_price=0.35,
            min_quality=8,
            timeout=60.0,
            quality_criteria=[
                "Implementation is complete and correct",
                "Handles concurrent/complex scenarios",
                "Well-architected and maintainable",
                "Comprehensive error handling",
            ],
            expected_tools=["execute_python"],
            metadata={"template": description}
        ))

    return tasks


# ============================================================================
# CATEGORY 2: DEBUGGING
# ============================================================================

def _generate_debugging_tasks() -> list[Task]:
    """100 tasks: 30 easy, 40 medium, 25 hard, 5 extreme."""
    tasks = []

    # Easy debugging templates (30 tasks)
    easy_bugs = [
        (
            "def add(a, b):\n    return a + b + 1",
            "The function should return the sum of two numbers, but it adds an extra 1"
        ),
        (
            "def is_positive(x):\n    return x > 0 or x == 0",
            "This function has redundant logic. Simplify the condition."
        ),
        (
            "def count_chars(s):\n    count = 0\n    for c in s:\n        count += 1\n    return count - 1",
            "The function should return the character count but subtracts 1 at the end"
        ),
        (
            "def multiply(a, b):\n    result = 0\n    for i in range(a):\n        result = result + a\n    return result",
            "This function multiplies a*a instead of a*b. Fix the loop."
        ),
        (
            "def find_max(lst):\n    max_val = lst[0]\n    for x in lst:\n        if x > max_val:\n            max_val = x\n    return max_val + 1",
            "The function returns the maximum plus 1 instead of just the maximum"
        ),
    ]

    for i in range(30):
        idx = i % len(easy_bugs)
        code, issue = easy_bugs[idx]

        tasks.append(Task(
            task_id=f"debug_easy_{i+1:03d}",
            category="debugging",
            difficulty="easy",
            input=f"Find the bug in this code:\n```python\n{code}\n```\nHint: {issue}",
            max_price=0.02,
            min_quality=5,
            timeout=15.0,
            quality_criteria=[
                "Correctly identifies the bug",
                "Explains the issue clearly",
                "Provides corrected code",
            ],
            expected_tools=["execute_python"],
            metadata={"bug_type": "logic_error"}
        ))

    # Medium debugging templates (40 tasks)
    medium_bugs = [
        (
            "def fibonacci(n):\n    if n <= 0:\n        return 0\n    if n == 1:\n        return 1\n    return fibonacci(n-1) + fibonacci(n-2)",
            "This function has exponential time complexity. Optimize with memoization.",
            "performance"
        ),
        (
            "def merge_lists(l1, l2):\n    result = l1\n    result.extend(l2)\n    return result",
            "This function modifies the original list l1. Use list concatenation instead.",
            "mutation"
        ),
        (
            "def parse_json(s):\n    import json\n    return json.loads(s)",
            "This function doesn't handle invalid JSON. Add error handling.",
            "error_handling"
        ),
    ]

    for i in range(40):
        idx = i % len(medium_bugs)
        code, issue, bug_type = medium_bugs[idx]

        tasks.append(Task(
            task_id=f"debug_medium_{i+1:03d}",
            category="debugging",
            difficulty="medium",
            input=f"Find and fix the bug:\n```python\n{code}\n```\nIssue: {issue}",
            max_price=0.05,
            min_quality=6,
            timeout=25.0,
            quality_criteria=[
                "Identifies the root cause",
                "Explains why it's a bug",
                "Provides working solution",
                "Tests the fix",
            ],
            expected_tools=["execute_python"],
            metadata={"bug_type": bug_type}
        ))

    # Hard debugging templates (25 tasks)
    hard_bugs = [
        (
            "def quick_sort(arr):\n    if len(arr) <= 1:\n        return arr\n    pivot = arr[0]\n    left = [x for x in arr[1:] if x < pivot]\n    right = [x for x in arr[1:] if x >= pivot]\n    return quick_sort(left) + [pivot] + quick_sort(right)",
            "This function fails on lists with duplicate elements",
            "algorithm"
        ),
    ]

    for i in range(25):
        idx = i % len(hard_bugs)
        code, issue, bug_type = hard_bugs[idx]

        tasks.append(Task(
            task_id=f"debug_hard_{i+1:03d}",
            category="debugging",
            difficulty="hard",
            input=f"Debug this code that fails on edge cases:\n```python\n{code}\n```\nProblem: {issue}",
            max_price=0.15,
            min_quality=7,
            timeout=40.0,
            quality_criteria=[
                "Identifies subtle bug in algorithm",
                "Explains edge case failure",
                "Provides correct implementation",
                "Tests with problematic inputs",
            ],
            expected_tools=["execute_python"],
            metadata={"bug_type": bug_type}
        ))

    # Extreme debugging (5 tasks)
    for i in range(5):
        tasks.append(Task(
            task_id=f"debug_extreme_{i+1:03d}",
            category="debugging",
            difficulty="extreme",
            input=f"Debug complex race condition in concurrent code (variant {i+1})",
            max_price=0.35,
            min_quality=8,
            timeout=60.0,
            quality_criteria=[
                "Identifies race condition",
                "Explains concurrency issue",
                "Provides thread-safe solution",
            ],
            expected_tools=["execute_python"],
            metadata={"bug_type": "concurrency"}
        ))

    return tasks


# ============================================================================
# CATEGORY 3: MATH_REASONING
# ============================================================================

def _generate_math_reasoning_tasks() -> list[Task]:
    """100 tasks: 30 easy, 40 medium, 25 hard, 5 extreme."""
    tasks = []

    # Easy math (30 tasks)
    easy_math = [
        ("What is 15 + 27?", "Arithmetic"),
        ("What is 12 * 8?", "Arithmetic"),
        ("What is 100 / 4?", "Arithmetic"),
        ("What is the square root of 144?", "Arithmetic"),
        ("If x + 5 = 12, what is x?", "Algebra"),
        ("What is 2^10?", "Exponentiation"),
        ("What is the area of a circle with radius 5?", "Geometry"),
        ("What is 20% of 150?", "Percentage"),
        ("Solve: 3x = 21", "Algebra"),
        ("What is the perimeter of a square with side 7?", "Geometry"),
    ]

    for i in range(30):
        idx = i % len(easy_math)
        prompt, category = easy_math[idx]

        tasks.append(Task(
            task_id=f"math_easy_{i+1:03d}",
            category="math_reasoning",
            difficulty="easy",
            input=prompt,
            max_price=0.02,
            min_quality=5,
            timeout=15.0,
            quality_criteria=[
                "Answer is correct",
                "Shows calculation steps",
            ],
            expected_tools=["math_eval"],
            metadata={"math_type": category}
        ))

    # Medium math (40 tasks)
    medium_math = [
        ("Solve the quadratic equation: x^2 - 5x + 6 = 0", "Algebra"),
        ("What is the sum of the first 50 positive integers?", "Series"),
        ("What is the probability of rolling a 6 on two dice?", "Probability"),
        ("Find the derivative of f(x) = 3x^2 + 2x + 1", "Calculus"),
        ("What is the binomial coefficient C(10, 3)?", "Combinatorics"),
    ]

    for i in range(40):
        idx = i % len(medium_math)
        prompt, category = medium_math[idx]

        tasks.append(Task(
            task_id=f"math_medium_{i+1:03d}",
            category="math_reasoning",
            difficulty="medium",
            input=prompt,
            max_price=0.05,
            min_quality=6,
            timeout=25.0,
            quality_criteria=[
                "Correct final answer",
                "Shows all work",
                "Explains reasoning",
            ],
            expected_tools=["math_eval"],
            metadata={"math_type": category}
        ))

    # Hard math (25 tasks)
    for i in range(25):
        tasks.append(Task(
            task_id=f"math_hard_{i+1:03d}",
            category="math_reasoning",
            difficulty="hard",
            input=f"Solve a challenging proof or optimization problem (variant {i+1})",
            max_price=0.15,
            min_quality=7,
            timeout=40.0,
            quality_criteria=[
                "Correct solution",
                "Rigorous proof",
                "Clear logical steps",
            ],
            expected_tools=["math_eval"],
            metadata={"math_type": "advanced"}
        ))

    # Extreme math (5 tasks)
    for i in range(5):
        tasks.append(Task(
            task_id=f"math_extreme_{i+1:03d}",
            category="math_reasoning",
            difficulty="extreme",
            input=f"Prove or solve a research-level problem (variant {i+1})",
            max_price=0.35,
            min_quality=8,
            timeout=60.0,
            quality_criteria=[
                "Mathematically rigorous",
                "Complete proof",
                "Novel approach or insight",
            ],
            expected_tools=["math_eval"],
            metadata={"math_type": "research"}
        ))

    return tasks


# ============================================================================
# CATEGORY 4: WRITING
# ============================================================================

def _generate_writing_tasks() -> list[Task]:
    """100 tasks: 30 easy, 40 medium, 25 hard, 5 extreme."""
    tasks = []

    # Easy writing (30 tasks)
    easy_writing = [
        ("Explain what a variable is in programming", "Explanation"),
        ("Summarize the water cycle in 2-3 sentences", "Summary"),
        ("What are the three branches of government?", "Explanation"),
        ("Describe the difference between DNA and RNA", "Comparison"),
        ("Write a brief definition of photosynthesis", "Definition"),
    ]

    for i in range(30):
        idx = i % len(easy_writing)
        prompt, writing_type = easy_writing[idx]

        tasks.append(Task(
            task_id=f"writing_easy_{i+1:03d}",
            category="writing",
            difficulty="easy",
            input=prompt,
            max_price=0.02,
            min_quality=5,
            timeout=15.0,
            quality_criteria=[
                "Clear and concise",
                "Addresses the prompt",
                "No major grammatical errors",
            ],
            expected_tools=[],
            metadata={"writing_type": writing_type}
        ))

    # Medium writing (40 tasks)
    medium_writing = [
        ("Write a clear explanation of how blockchain technology works", "Technical explanation"),
        ("Compare and contrast machine learning and deep learning", "Comparison essay"),
        ("Explain the causes and effects of climate change", "Analysis"),
        ("Write an explanation of the theory of evolution", "Educational"),
    ]

    for i in range(40):
        idx = i % len(medium_writing)
        prompt, writing_type = medium_writing[idx]

        tasks.append(Task(
            task_id=f"writing_medium_{i+1:03d}",
            category="writing",
            difficulty="medium",
            input=prompt,
            max_price=0.05,
            min_quality=6,
            timeout=25.0,
            quality_criteria=[
                "Well-structured with clear paragraphs",
                "Accurate and informative",
                "Engaging writing style",
                "Proper grammar and spelling",
            ],
            expected_tools=[],
            metadata={"writing_type": writing_type}
        ))

    # Hard writing (25 tasks)
    for i in range(25):
        tasks.append(Task(
            task_id=f"writing_hard_{i+1:03d}",
            category="writing",
            difficulty="hard",
            input=f"Write a nuanced essay analyzing a complex topic (variant {i+1})",
            max_price=0.15,
            min_quality=7,
            timeout=40.0,
            quality_criteria=[
                "Well-researched and accurate",
                "Multiple perspectives considered",
                "Strong argumentation",
                "Sophisticated writing",
            ],
            expected_tools=[],
            metadata={"writing_type": "essay"}
        ))

    # Extreme writing (5 tasks)
    for i in range(5):
        tasks.append(Task(
            task_id=f"writing_extreme_{i+1:03d}",
            category="writing",
            difficulty="extreme",
            input=f"Write a comprehensive scholarly piece on a specialized topic (variant {i+1})",
            max_price=0.35,
            min_quality=8,
            timeout=60.0,
            quality_criteria=[
                "Expert-level knowledge",
                "Original insights",
                "Impeccable writing",
                "Proper citations if needed",
            ],
            expected_tools=[],
            metadata={"writing_type": "scholarly"}
        ))

    return tasks


# ============================================================================
# CATEGORY 5: DATA_ANALYSIS
# ============================================================================

def _generate_data_analysis_tasks() -> list[Task]:
    """100 tasks: 30 easy, 40 medium, 25 hard, 5 extreme."""
    tasks = []

    # Easy data analysis (30 tasks)
    easy_analysis = [
        ("Given the dataset [1, 2, 3, 4, 5], calculate the mean", "Basic statistics"),
        ("Given the dataset [1, 2, 3, 4, 5], find the median", "Basic statistics"),
        ("Given the dataset [1, 1, 2, 3, 3, 3], find the mode", "Basic statistics"),
        ("What is the range of [5, 12, 3, 18, 7]?", "Basic statistics"),
    ]

    for i in range(30):
        idx = i % len(easy_analysis)
        prompt, analysis_type = easy_analysis[idx]

        tasks.append(Task(
            task_id=f"data_analysis_easy_{i+1:03d}",
            category="data_analysis",
            difficulty="easy",
            input=prompt,
            max_price=0.02,
            min_quality=5,
            timeout=15.0,
            quality_criteria=[
                "Correct calculation",
                "Shows work",
            ],
            expected_tools=["execute_python"],
            metadata={"analysis_type": analysis_type}
        ))

    # Medium data analysis (40 tasks)
    medium_analysis = [
        ("Calculate the standard deviation of [10, 20, 30, 40, 50]", "Statistics"),
        ("Given x=[1,2,3] and y=[2,4,5], calculate the correlation coefficient", "Correlation"),
        ("Create a frequency table for [1,1,2,2,2,3,3,3,3,4]", "Frequency analysis"),
    ]

    for i in range(40):
        idx = i % len(medium_analysis)
        prompt, analysis_type = medium_analysis[idx]

        tasks.append(Task(
            task_id=f"data_analysis_medium_{i+1:03d}",
            category="data_analysis",
            difficulty="medium",
            input=prompt,
            max_price=0.05,
            min_quality=6,
            timeout=25.0,
            quality_criteria=[
                "Correct statistical measure",
                "Accurate calculations",
                "Clear explanation",
            ],
            expected_tools=["execute_python"],
            metadata={"analysis_type": analysis_type}
        ))

    # Hard data analysis (25 tasks)
    for i in range(25):
        tasks.append(Task(
            task_id=f"data_analysis_hard_{i+1:03d}",
            category="data_analysis",
            difficulty="hard",
            input=f"Perform multivariate analysis and identify patterns (variant {i+1})",
            max_price=0.15,
            min_quality=7,
            timeout=40.0,
            quality_criteria=[
                "Accurate analysis",
                "Identifies meaningful patterns",
                "Statistical rigor",
            ],
            expected_tools=["execute_python"],
            metadata={"analysis_type": "advanced"}
        ))

    # Extreme data analysis (5 tasks)
    for i in range(5):
        tasks.append(Task(
            task_id=f"data_analysis_extreme_{i+1:03d}",
            category="data_analysis",
            difficulty="extreme",
            input=f"Conduct a comprehensive data science analysis (variant {i+1})",
            max_price=0.35,
            min_quality=8,
            timeout=60.0,
            quality_criteria=[
                "Sophisticated analysis",
                "Novel insights",
                "Proper statistical validation",
            ],
            expected_tools=["execute_python"],
            metadata={"analysis_type": "research"}
        ))

    return tasks


# ============================================================================
# CATEGORY 6: SYSTEM_DESIGN
# ============================================================================

def _generate_system_design_tasks() -> list[Task]:
    """100 tasks: 30 easy, 40 medium, 25 hard, 5 extreme."""
    tasks = []

    # Easy system design (30 tasks)
    easy_design = [
        ("Design a simple key-value store API", "Basic API design"),
        ("Design a URL shortener API", "Web service"),
        ("Design a todo list application", "Simple application"),
    ]

    for i in range(30):
        idx = i % len(easy_design)
        prompt, design_type = easy_design[idx]

        tasks.append(Task(
            task_id=f"system_design_easy_{i+1:03d}",
            category="system_design",
            difficulty="easy",
            input=f"Design {prompt}",
            max_price=0.02,
            min_quality=5,
            timeout=15.0,
            quality_criteria=[
                "Clear API specification",
                "Basic data models",
                "Reasonable architecture",
            ],
            expected_tools=[],
            metadata={"design_type": design_type}
        ))

    # Medium system design (40 tasks)
    medium_design = [
        ("Design a chat application that supports 1M concurrent users", "High-scale system"),
        ("Design a notification system for an e-commerce platform", "Complex service"),
        ("Design a rate-limiting service", "Service design"),
    ]

    for i in range(40):
        idx = i % len(medium_design)
        prompt, design_type = medium_design[idx]

        tasks.append(Task(
            task_id=f"system_design_medium_{i+1:03d}",
            category="system_design",
            difficulty="medium",
            input=f"Design {prompt}",
            max_price=0.05,
            min_quality=6,
            timeout=25.0,
            quality_criteria=[
                "Scalable architecture",
                "Clear component interactions",
                "Addresses key challenges",
                "Database and caching strategy",
            ],
            expected_tools=[],
            metadata={"design_type": design_type}
        ))

    # Hard system design (25 tasks)
    for i in range(25):
        tasks.append(Task(
            task_id=f"system_design_hard_{i+1:03d}",
            category="system_design",
            difficulty="hard",
            input=f"Design a globally distributed system with complex requirements (variant {i+1})",
            max_price=0.15,
            min_quality=7,
            timeout=40.0,
            quality_criteria=[
                "Handles global scale",
                "Considers consistency/availability tradeoffs",
                "Detailed component design",
                "Addresses failure scenarios",
            ],
            expected_tools=[],
            metadata={"design_type": "advanced"}
        ))

    # Extreme system design (5 tasks)
    for i in range(5):
        tasks.append(Task(
            task_id=f"system_design_extreme_{i+1:03d}",
            category="system_design",
            difficulty="extreme",
            input=f"Design a complex infrastructure system solving novel challenges (variant {i+1})",
            max_price=0.35,
            min_quality=8,
            timeout=60.0,
            quality_criteria=[
                "Innovative architecture",
                "Handles edge cases",
                "Proven scalability approach",
                "Production-ready design",
            ],
            expected_tools=[],
            metadata={"design_type": "research"}
        ))

    return tasks


# ============================================================================
# CATEGORY 7: MULTI_STEP
# ============================================================================

def _generate_multi_step_tasks() -> list[Task]:
    """100 tasks: 30 easy, 40 medium, 25 hard, 5 extreme."""
    tasks = []

    # Easy multi-step (30 tasks)
    easy_steps = [
        ("Parse the CSV data, filter rows where age > 30, then count the results", "Data pipeline"),
        ("Read a JSON file, extract the 'users' field, and return the count", "Data extraction"),
    ]

    for i in range(30):
        idx = i % len(easy_steps)
        prompt, step_type = easy_steps[idx]

        tasks.append(Task(
            task_id=f"multi_step_easy_{i+1:03d}",
            category="multi_step",
            difficulty="easy",
            input=prompt,
            max_price=0.02,
            min_quality=5,
            timeout=15.0,
            quality_criteria=[
                "All steps completed correctly",
                "Correct final result",
            ],
            expected_tools=["execute_python"],
            metadata={"step_type": step_type, "num_steps": 3}
        ))

    # Medium multi-step (40 tasks)
    medium_steps = [
        ("Parse input data, validate against schema, transform to output format, then serialize", "ETL pipeline"),
        ("Read file, parse JSON, filter by criteria, group by category, calculate aggregates", "Data processing"),
    ]

    for i in range(40):
        idx = i % len(medium_steps)
        prompt, step_type = medium_steps[idx]

        tasks.append(Task(
            task_id=f"multi_step_medium_{i+1:03d}",
            category="multi_step",
            difficulty="medium",
            input=prompt,
            max_price=0.05,
            min_quality=6,
            timeout=25.0,
            quality_criteria=[
                "Each step executed correctly",
                "No data loss or corruption",
                "Correct final output",
                "Handles edge cases",
            ],
            expected_tools=["execute_python"],
            metadata={"step_type": step_type, "num_steps": 4}
        ))

    # Hard multi-step (25 tasks)
    for i in range(25):
        tasks.append(Task(
            task_id=f"multi_step_hard_{i+1:03d}",
            category="multi_step",
            difficulty="hard",
            input=f"Execute a 5+ step data transformation pipeline with error handling (variant {i+1})",
            max_price=0.15,
            min_quality=7,
            timeout=40.0,
            quality_criteria=[
                "All steps work correctly",
                "Robust error handling",
                "Efficient data flow",
                "No intermediate data loss",
            ],
            expected_tools=["execute_python"],
            metadata={"step_type": "complex", "num_steps": 5}
        ))

    # Extreme multi-step (5 tasks)
    for i in range(5):
        tasks.append(Task(
            task_id=f"multi_step_extreme_{i+1:03d}",
            category="multi_step",
            difficulty="extreme",
            input=f"Orchestrate a complex 7+ step workflow with dependencies and error recovery (variant {i+1})",
            max_price=0.35,
            min_quality=8,
            timeout=60.0,
            quality_criteria=[
                "All steps coordinated correctly",
                "Advanced error recovery",
                "Optimal ordering",
                "Complete workflow success",
            ],
            expected_tools=["execute_python"],
            metadata={"step_type": "orchestration", "num_steps": 7}
        ))

    return tasks


# ============================================================================
# CATEGORY 8: KNOWLEDGE
# ============================================================================

def _generate_knowledge_tasks() -> list[Task]:
    """100 tasks: 30 easy, 40 medium, 25 hard, 5 extreme."""
    tasks = []

    # Easy knowledge (30 tasks)
    easy_knowledge = [
        ("What is the capital of France?", "Geography"),
        ("How many continents are there?", "Geography"),
        ("What is the chemical symbol for gold?", "Chemistry"),
        ("In what year did World War II end?", "History"),
        ("What is the largest planet in our solar system?", "Astronomy"),
    ]

    for i in range(30):
        idx = i % len(easy_knowledge)
        prompt, knowledge_type = easy_knowledge[idx]

        tasks.append(Task(
            task_id=f"knowledge_easy_{i+1:03d}",
            category="knowledge",
            difficulty="easy",
            input=prompt,
            max_price=0.02,
            min_quality=5,
            timeout=15.0,
            quality_criteria=[
                "Factually correct answer",
                "Concise response",
            ],
            expected_tools=[],
            metadata={"knowledge_type": knowledge_type}
        ))

    # Medium knowledge (40 tasks)
    medium_knowledge = [
        ("Explain the difference between mitochondria and chloroplasts", "Biology"),
        ("What are the main causes of the Industrial Revolution?", "History"),
        ("How does photosynthesis work?", "Biology"),
        ("What is quantum entanglement?", "Physics"),
    ]

    for i in range(40):
        idx = i % len(medium_knowledge)
        prompt, knowledge_type = medium_knowledge[idx]

        tasks.append(Task(
            task_id=f"knowledge_medium_{i+1:03d}",
            category="knowledge",
            difficulty="medium",
            input=prompt,
            max_price=0.05,
            min_quality=6,
            timeout=25.0,
            quality_criteria=[
                "Accurate and comprehensive",
                "Clear explanation",
                "Addresses the core concept",
            ],
            expected_tools=[],
            metadata={"knowledge_type": knowledge_type}
        ))

    # Hard knowledge (25 tasks)
    for i in range(25):
        tasks.append(Task(
            task_id=f"knowledge_hard_{i+1:03d}",
            category="knowledge",
            difficulty="hard",
            input=f"Explain a complex scientific or historical concept (variant {i+1})",
            max_price=0.15,
            min_quality=7,
            timeout=40.0,
            quality_criteria=[
                "Expert-level accuracy",
                "Nuanced explanation",
                "Contextual understanding",
            ],
            expected_tools=[],
            metadata={"knowledge_type": "advanced"}
        ))

    # Extreme knowledge (5 tasks)
    for i in range(5):
        tasks.append(Task(
            task_id=f"knowledge_extreme_{i+1:03d}",
            category="knowledge",
            difficulty="extreme",
            input=f"Answer a research-level question requiring specialized expertise (variant {i+1})",
            max_price=0.35,
            min_quality=8,
            timeout=60.0,
            quality_criteria=[
                "Deep specialized knowledge",
                "Nuanced perspective",
                "Original insights",
            ],
            expected_tools=[],
            metadata={"knowledge_type": "research"}
        ))

    return tasks


# ============================================================================
# CATEGORY 9: CREATIVE
# ============================================================================

def _generate_creative_tasks() -> list[Task]:
    """100 tasks: 30 easy, 40 medium, 25 hard, 5 extreme."""
    tasks = []

    # Easy creative (30 tasks)
    easy_creative = [
        ("Generate 5 creative names for a coffee shop", "Brainstorming"),
        ("Write a short 2-line joke about programming", "Humor"),
        ("Come up with 3 creative use cases for a rubber duck", "Ideation"),
    ]

    for i in range(30):
        idx = i % len(easy_creative)
        prompt, creative_type = easy_creative[idx]

        tasks.append(Task(
            task_id=f"creative_easy_{i+1:03d}",
            category="creative",
            difficulty="easy",
            input=prompt,
            max_price=0.02,
            min_quality=5,
            timeout=15.0,
            quality_criteria=[
                "Creative and original ideas",
                "Meets the prompt requirements",
                "Clear presentation",
            ],
            expected_tools=[],
            metadata={"creative_type": creative_type}
        ))

    # Medium creative (40 tasks)
    medium_creative = [
        ("Write a short story (300 words) about an unexpected discovery", "Storytelling"),
        ("Create an interesting dialogue between two characters meeting for the first time", "Writing"),
        ("Write a creative product description that makes a mundane item appealing", "Marketing"),
    ]

    for i in range(40):
        idx = i % len(medium_creative)
        prompt, creative_type = medium_creative[idx]

        tasks.append(Task(
            task_id=f"creative_medium_{i+1:03d}",
            category="creative",
            difficulty="medium",
            input=prompt,
            max_price=0.05,
            min_quality=6,
            timeout=25.0,
            quality_criteria=[
                "Engaging and imaginative",
                "Well-structured",
                "Compelling narrative or idea",
            ],
            expected_tools=[],
            metadata={"creative_type": creative_type}
        ))

    # Hard creative (25 tasks)
    for i in range(25):
        tasks.append(Task(
            task_id=f"creative_hard_{i+1:03d}",
            category="creative",
            difficulty="hard",
            input=f"Create a sophisticated creative work with depth and nuance (variant {i+1})",
            max_price=0.15,
            min_quality=7,
            timeout=40.0,
            quality_criteria=[
                "High artistic quality",
                "Original and innovative",
                "Emotionally resonant",
            ],
            expected_tools=[],
            metadata={"creative_type": "advanced"}
        ))

    # Extreme creative (5 tasks)
    for i in range(5):
        tasks.append(Task(
            task_id=f"creative_extreme_{i+1:03d}",
            category="creative",
            difficulty="extreme",
            input=f"Create groundbreaking creative work demonstrating exceptional artistry (variant {i+1})",
            max_price=0.35,
            min_quality=8,
            timeout=60.0,
            quality_criteria=[
                "Exceptional artistic merit",
                "Truly original",
                "Demonstrates mastery",
            ],
            expected_tools=[],
            metadata={"creative_type": "masterwork"}
        ))

    return tasks


# ============================================================================
# CATEGORY 10: TOOL_USING
# ============================================================================

def _generate_tool_using_tasks() -> list[Task]:
    """100 tasks: 30 easy, 40 medium, 25 hard, 5 extreme."""
    tasks = []

    # Easy tool-using (30 tasks)
    easy_tools = [
        ("Execute this code and tell me the output: print('hello world')", "Code execution"),
        ("Calculate 2.5 ** 10 using Python", "Calculation"),
        ("Execute: import math; math.sqrt(144)", "Math evaluation"),
    ]

    for i in range(30):
        idx = i % len(easy_tools)
        prompt, tool_type = easy_tools[idx]

        tasks.append(Task(
            task_id=f"tool_using_easy_{i+1:03d}",
            category="tool_using",
            difficulty="easy",
            input=prompt,
            max_price=0.02,
            min_quality=5,
            timeout=15.0,
            quality_criteria=[
                "Tool executed correctly",
                "Correct output provided",
            ],
            expected_tools=["execute_python"],
            metadata={"tool_type": tool_type}
        ))

    # Medium tool-using (40 tasks)
    medium_tools = [
        ("Write a program that finds all prime numbers up to 100, execute it, and show results", "Code execution"),
        ("Execute Python code to compute the 20th Fibonacci number", "Calculation"),
        ("Write and execute code to validate if a string is a valid email address", "Validation"),
    ]

    for i in range(40):
        idx = i % len(medium_tools)
        prompt, tool_type = medium_tools[idx]

        tasks.append(Task(
            task_id=f"tool_using_medium_{i+1:03d}",
            category="tool_using",
            difficulty="medium",
            input=prompt,
            max_price=0.05,
            min_quality=6,
            timeout=25.0,
            quality_criteria=[
                "Tool used correctly",
                "Accurate results",
                "Code is efficient",
            ],
            expected_tools=["execute_python"],
            metadata={"tool_type": tool_type}
        ))

    # Hard tool-using (25 tasks)
    for i in range(25):
        tasks.append(Task(
            task_id=f"tool_using_hard_{i+1:03d}",
            category="tool_using",
            difficulty="hard",
            input=f"Use tools to solve a complex problem requiring multiple tool calls (variant {i+1})",
            max_price=0.15,
            min_quality=7,
            timeout=40.0,
            quality_criteria=[
                "Tools used correctly",
                "Correct final result",
                "Efficient tool usage",
            ],
            expected_tools=["execute_python"],
            metadata={"tool_type": "complex"}
        ))

    # Extreme tool-using (5 tasks)
    for i in range(5):
        tasks.append(Task(
            task_id=f"tool_using_extreme_{i+1:03d}",
            category="tool_using",
            difficulty="extreme",
            input=f"Orchestrate multiple tool calls to solve a sophisticated problem (variant {i+1})",
            max_price=0.35,
            min_quality=8,
            timeout=60.0,
            quality_criteria=[
                "Multiple tools coordinated",
                "Optimal tool selection",
                "Correct solution",
            ],
            expected_tools=["execute_python"],
            metadata={"tool_type": "orchestration"}
        ))

    return tasks


# ============================================================================
# MAIN TASK BANK LOADER
# ============================================================================

def load_task_bank() -> list[Task]:
    """Load all 1,000 tasks deterministically.

    Structure:
    - 10 categories
    - 100 tasks per category
    - Distribution: 30 easy, 40 medium, 25 hard, 5 extreme
    """
    all_tasks = []

    all_tasks.extend(_generate_code_generation_tasks())
    all_tasks.extend(_generate_debugging_tasks())
    all_tasks.extend(_generate_math_reasoning_tasks())
    all_tasks.extend(_generate_writing_tasks())
    all_tasks.extend(_generate_data_analysis_tasks())
    all_tasks.extend(_generate_system_design_tasks())
    all_tasks.extend(_generate_multi_step_tasks())
    all_tasks.extend(_generate_knowledge_tasks())
    all_tasks.extend(_generate_creative_tasks())
    all_tasks.extend(_generate_tool_using_tasks())

    assert len(all_tasks) == 1000, f"Expected 1000 tasks, got {len(all_tasks)}"
    return all_tasks


def load_tasks_by_difficulty(difficulty: str) -> list[Task]:
    """Return all tasks of a given difficulty.

    Args:
        difficulty: "easy", "medium", "hard", or "extreme"

    Returns:
        List of tasks matching the difficulty.
    """
    all_tasks = load_task_bank()
    return [t for t in all_tasks if t.difficulty == difficulty]


def load_tasks_by_category(category: str) -> list[Task]:
    """Return all tasks in a given category.

    Args:
        category: One of the 10 category names

    Returns:
        List of 100 tasks in the category.
    """
    all_tasks = load_task_bank()
    return [t for t in all_tasks if t.category == category]


if __name__ == "__main__":
    # Quick validation
    tasks = load_task_bank()
    print(f"Total tasks: {len(tasks)}")

    for difficulty in ["easy", "medium", "hard", "extreme"]:
        count = len(load_tasks_by_difficulty(difficulty))
        print(f"  {difficulty}: {count}")

    categories = {
        "code_generation", "debugging", "math_reasoning", "writing",
        "data_analysis", "system_design", "multi_step", "knowledge",
        "creative", "tool_using"
    }

    for cat in sorted(categories):
        count = len(load_tasks_by_category(cat))
        print(f"  {cat}: {count}")
