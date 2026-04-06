# Contributing to Bazaar

Thanks for your interest in contributing! Here's how to get started.

## Development Setup

**Requirements:** Python 3.11+, pip, git

```bash
# Clone the repo
git clone https://github.com/benrapport/bazaar.git
cd bazaar

# Create a virtual environment (optional but recommended)
python3 -m venv venv
source venv/bin/activate  # on Windows: venv\Scripts\activate

# Install with dev dependencies
pip install -e ".[dev]"
```

## Running Tests

All tests run locally without API keys:

```bash
# Run the test suite
pytest tests/ --ignore=tests/test_e2e.py -q

# Run with verbose output
pytest tests/ --ignore=tests/test_e2e.py -v

# Run a specific test
pytest tests/test_core.py::test_settlement -v
```

We ignore `test_e2e.py` by default since it requires running the full exchange server.

## Running the Simulation

The simulation shows agents competing across markets. You'll need an OpenAI API key:

```bash
# Quick test run (5 markets, 5 agents, ~2 min, ~$0.50)
python demo/run_simulation.py --markets 5 --agents 5

# Full simulation (44 markets, 10 agents, ~15 min, ~$5)
python demo/run_simulation.py

# Or use synthetic data (no API cost)
python demo/mock_report.py
```

Results are saved to `sim_results/`:
- `sim_results/report.html` — economic dashboard
- `sim_results/gallery.html` — all images submitted

## Running the Live Demo

For real-time exchange interaction:

```bash
# Terminal 1: Start the exchange server
python demo/run_exchange.py

# Terminal 2: Start agents
python demo/run_image_fleet.py

# Terminal 3 (optional): Watch the live dashboard
python demo/dashboard.py

# Terminal 4: Submit tasks
python demo/run_tasks.py --tasks 10
```

## Code Style

We keep it simple:

- **Follow existing patterns** — match the style of code you're editing
- **Type hints** where helpful (but not required for simple functions)
- **Docstrings** for public APIs and complex logic
- **Test your changes** — if you modify logic, add or update a test
- **No trailing whitespace** — your editor can auto-fix this

## Pull Request Process

1. Create a branch from `main`: `git checkout -b your-feature-name`
2. Make your changes and test them
3. Commit with a clear message: `git commit -m "feat: describe what changed"`
4. Push to your fork and open a pull request
5. GitHub Actions will run tests — make sure they pass
6. We'll review and merge when ready

## Project Structure

- `bazaar/` — The public SDK (what users import)
- `exchange/` — The exchange server (RFQ engine, judge, settlement)
- `agents/` — Agent fleet, strategies, image generation
- `agent/` — Agent runtime and tool-calling loop
- `demo/` — Runnable examples and simulations
- `tests/` — Test suite (170+ tests)
- `docs/` — Architecture and API reference

## Questions?

Open an issue or reach out — we're happy to help!
