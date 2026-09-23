import json
from pathlib import Path

from accessops.audit import AuditLog


def add_event(log: AuditLog) -> None:
    log.append(
        source_event_id="EVT-AUDIT-1001",
        action="lifecycle.joiner",
        outcome="success",
        actor="tester",
        target="synthetic.user",
        request_digest="abc123",
        summary={"password": "must-not-appear", "safe": "visible"},
    )


def test_sensitive_values_are_redacted_and_chain_is_valid(tmp_path: Path) -> None:
    log = AuditLog(tmp_path / "audit.jsonl")
    add_event(log)
    entry = log.entries()[0]
    assert entry["summary"]["password"] == "[REDACTED]"
    assert log.verify_chain()["valid"] is True


def test_tampering_is_detected(tmp_path: Path) -> None:
    path = tmp_path / "audit.jsonl"
    log = AuditLog(path)
    add_event(log)
    row = json.loads(path.read_text(encoding="utf-8"))
    row["target"] = "tampered.user"
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")
    result = log.verify_chain()
    assert result["valid"] is False
    assert result["reason"] == "hash"
