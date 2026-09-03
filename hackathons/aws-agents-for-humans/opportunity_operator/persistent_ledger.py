from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from .models import DecisionPacket, Opportunity
from .pipeline import LedgerEntry, OpportunityLedger, material_signature, opportunity_fingerprint


class JsonOpportunityLedger(OpportunityLedger):
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        super().__init__()
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        for fingerprint, row in payload.items():
            self.entries[fingerprint] = LedgerEntry(
                fingerprint=fingerprint,
                material_signature=str(row["material_signature"]),
                last_seen_at=datetime.fromisoformat(row["last_seen_at"]),
                decision=str(row["decision"]),
            )

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        serializable = {
            key: {
                **asdict(entry),
                "last_seen_at": entry.last_seen_at.isoformat(),
            }
            for key, entry in self.entries.items()
        }
        self.path.write_text(
            json.dumps(serializable, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    def record(self, opportunity: Opportunity, packet: DecisionPacket) -> None:
        fingerprint = opportunity_fingerprint(opportunity)
        self.entries[fingerprint] = LedgerEntry(
            fingerprint=fingerprint,
            material_signature=material_signature(opportunity),
            last_seen_at=datetime.now().astimezone(),
            decision=packet.decision,
        )
        self._save()
