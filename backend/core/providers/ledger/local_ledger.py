from typing import Dict, List
from core.interfaces.base_ledger import BaseLedger

class LocalLedger(BaseLedger):
    def __init__(self):
        self._transactions: List[Dict] = []
        self._balances: Dict[str, float] = {}

    def initialize(self) -> bool:
        return True

    async def record(self, transaction: Dict) -> str:
        tx_id = f"tx_{len(self._transactions)}"
        self._transactions.append({"id": tx_id, **transaction})
        account = transaction.get("account_id", "default")
        self._balances[account] = self._balances.get(account, 0) + transaction.get("amount", 0)
        return tx_id

    async def query(self, filters: Dict) -> List[Dict]:
        return [t for t in self._transactions if all(t.get(k) == v for k, v in filters.items())]

    async def approve(self, transaction_id: str, approver_id: str) -> bool:
        for t in self._transactions:
            if t["id"] == transaction_id:
                t["approved_by"] = approver_id
                return True
        return False

    async def reject(self, transaction_id: str, reason: str) -> bool:
        for t in self._transactions:
            if t["id"] == transaction_id:
                t["rejected"] = True
                t["rejection_reason"] = reason
                return True
        return False

    async def audit_trail(self, entity_id: str) -> List[Dict]:
        return [t for t in self._transactions if t.get("entity_id") == entity_id]

    async def balance(self, account_id: str) -> float:
        return self._balances.get(account_id, 0.0)
