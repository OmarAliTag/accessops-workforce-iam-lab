from pathlib import Path

from accessops.review import write_review
from tests.fakes import FakeIdentityProvider


def test_access_review_exports_csv_and_json(tmp_path: Path) -> None:
    provider = FakeIdentityProvider()
    provider.create_user(
        username="nour.helpdesk",
        email="nour.helpdesk@example.test",
        first_name="Nour",
        last_name="Haddad",
        department="Helpdesk",
        groups=("Employees", "Helpdesk"),
    )
    csv_path = tmp_path / "review.csv"
    json_path = tmp_path / "review.json"
    report = write_review(provider, csv_path, json_path)
    assert report["identity_count"] == 1
    assert report["exception_count"] == 0
    assert "nour.helpdesk" in csv_path.read_text(encoding="utf-8-sig")
    assert json_path.exists()
