"""Settlement ledger — in-memory transaction log with exchange fees."""

from __future__ import annotations
import threading
from exchange.types import Transaction

EXCHANGE_FEE_RATE = 0.20
EXCHANGE_FEE_CAP = 0.01  # $0.01 cap


def calc_exchange_fee(buyer_max: float, agent_price: float) -> float:
    """20% of spread, capped at $0.01."""
    spread = max(0, buyer_max - agent_price)
    return min(EXCHANGE_FEE_RATE * spread, EXCHANGE_FEE_CAP)


class Ledger:
    def __init__(self):
        self._transactions: list[Transaction] = []
        self._lock = threading.Lock()

    def record(self, request_id: str, buyer_id: str, agent_id: str,
               capability: str, price: float, buyer_max: float,
               score: int | None, latency_ms: float) -> Transaction:
        fee = calc_exchange_fee(buyer_max, price)
        tx = Transaction(
            request_id=request_id,
            buyer_id=buyer_id,
            agent_id=agent_id,
            capability=capability,
            price=price,
            exchange_fee=fee,
            buyer_charged=price + fee,
            score=score,
            latency_ms=latency_ms,
        )
        with self._lock:
            self._transactions.append(tx)
        return tx

    def get_transactions(self, buyer_id: str | None = None,
                         agent_id: str | None = None) -> list[Transaction]:
        with self._lock:
            txns = list(self._transactions)
        if buyer_id:
            txns = [t for t in txns if t.buyer_id == buyer_id]
        if agent_id:
            txns = [t for t in txns if t.agent_id == agent_id]
        return txns

    def get_totals(self) -> dict:
        with self._lock:
            txns = list(self._transactions)
        return {
            "total_transactions": len(txns),
            "total_volume": sum(t.price for t in txns),
            "exchange_revenue": sum(t.exchange_fee for t in txns),
            "total_buyer_charged": sum(t.buyer_charged for t in txns),
        }
