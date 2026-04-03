"""Centralized exchange configuration — single source of truth.

All exchange-wide constants and defaults live here.
Import from this module instead of hardcoding values.
"""


class ExchangeDefaults:
    """Exchange-wide constants and defaults."""

    # Fee model (RFQ: flat % of fill price)
    EXCHANGE_FEE_RATE: float = 0.015  # 1.5%

    # Timing
    DEFAULT_TIMEOUT: float = 30.0  # seconds
    HARD_TIMEOUT: float = 60.0  # absolute max game duration
    CHECK_INTERVAL: float = 0.025  # 25ms poll interval for winner check

    # Quality
    DEFAULT_MIN_QUALITY: int = 6  # 1-10 scale

    # Judge
    JUDGE_MODEL: str = "gpt-4o-mini"

    # Top-N selection
    DEFAULT_TOP_N: int = 1  # how many winners per request
