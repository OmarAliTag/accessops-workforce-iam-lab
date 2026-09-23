from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SENSITIVE_FRAGMENTS = ("password", "secret", "token", "session", "credential")


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def request_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if any(part in key.lower() for part in SENSITIVE_FRAGMENTS) else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, tuple):
        return [redact(item) for item in value]
    return value


class AuditLog:
    """Append-only JSONL audit log with a simple SHA-256 hash chain.

    This makes accidental or casual edits detectable. It is not a replacement for a
    production SIEM, write-once storage, or cryptographic signing service.
    """

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def entries(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        rows: list[dict[str, Any]] = []
        for number, line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Audit log line {number} is not valid JSON.") from exc
        return rows

    def append(
        self,
        *,
        source_event_id: str,
        action: str,
        outcome: str,
        actor: str,
        target: str,
        request_digest: str,
        summary: dict[str, Any],
    ) -> dict[str, Any]:
        rows = self.entries()
        previous_hash = rows[-1].get("record_hash", "GENESIS") if rows else "GENESIS"
        record: dict[str, Any] = {
            "schema_version": 1,
            "audit_id": f"AUD-{uuid.uuid4()}",
            "source_event_id": source_event_id,
            "timestamp_utc": datetime.now(UTC).isoformat(),
            "action": action,
            "outcome": outcome,
            "actor": actor,
            "target": target,
            "request_hash": request_digest,
            "summary": redact(summary),
            "previous_hash": previous_hash,
        }
        record["record_hash"] = hashlib.sha256(canonical_json(record).encode("utf-8")).hexdigest()

        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(canonical_json(record) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        return record

    def events_for(self, source_event_id: str) -> list[dict[str, Any]]:
        return [row for row in self.entries() if row.get("source_event_id") == source_event_id]

    def verify_chain(self) -> dict[str, Any]:
        previous_hash = "GENESIS"
        rows = self.entries()
        for index, row in enumerate(rows, start=1):
            if row.get("previous_hash") != previous_hash:
                return {"valid": False, "records": len(rows), "failed_record": index, "reason": "link"}
            claimed = row.get("record_hash")
            unsigned = {key: value for key, value in row.items() if key != "record_hash"}
            calculated = hashlib.sha256(canonical_json(unsigned).encode("utf-8")).hexdigest()
            if claimed != calculated:
                return {"valid": False, "records": len(rows), "failed_record": index, "reason": "hash"}
            previous_hash = claimed
        return {"valid": True, "records": len(rows), "failed_record": None, "reason": None}
