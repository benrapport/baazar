"""Settlement ledger — in-memory transaction log with exchange fees."""

from __future__ import annotations
import threading
from exchange.config import ExchangeDefaults
from exchange.types import Transaction


def calc_exchange_fee(fill_price: float) -> float:
    """Flat fee on fill price (rate from ExchangeDefaults)."""
    return ExchangeDefaults.EXCHANGE_FEE_RATE * max(0, fill_price)


class Ledger:
    def __init__(self):
        self._transactions: list[Transaction] = []
        self._lock = threading.Lock()

    def record(self, request_id: str, buyer_id: str, agent_id: str,
               price: float,
               score: int | None, latency_ms: float) -> Transaction:
        fee = calc_exchange_fee(price)
        tx = Transaction(
            request_id=request_id,
            buyer_id=buyer_id,
            agent_id=agent_id,
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
