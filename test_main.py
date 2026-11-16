import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_create_and_list_habit():
    r = client.post("/habits", json={"name": "Read 20 minutes"})
    assert r.status_code == 200
    hid = r.json()["id"]
    r2 = client.get("/habits")
    assert r2.status_code == 200
    assert any(h["id"] == hid for h in r2.json())


@pytest.mark.parametrize("empty_name", ["", "   ", " \t \n "])
def test_create_habit_rejects_empty_name(empty_name):
    r = client.post("/habits", json={"name": empty_name})
    assert r.status_code == 422
    assert "empty" in r.text.lower()


def test_create_habit_rejects_missing_name():
    r = client.post("/habits", json={})
    assert r.status_code == 422


def test_create_habit_strips_surrounding_whitespace():
    r = client.post("/habits", json={"name": "  Meditate  "})
    assert r.status_code == 200
    assert r.json()["name"] == "Meditate"


def test_checkin_flow():
    hid = client.post("/habits", json={"name": "Stretch"}).json()["id"]
    r = client.post(f"/habits/{hid}/checkin", json={"day": "2026-09-22"})
    assert r.status_code == 200
    r2 = client.get(f"/habits/{hid}/checkins")
    assert r2.json() == ["2026-09-22"]


def test_checkin_unknown_habit_404():
    r = client.post("/habits/99999/checkin", json={"day": "2026-09-22"})
    assert r.status_code == 404


@pytest.mark.parametrize(
    "invalid_day",
    [
        "not-a-date",
        "2026-02-30",
        "2026-13-01",
        "2026/09/22",
        "2026-9-22",
        "",
        "   ",
        "2026-09-22T00:00:00",
        "20260922",
    ],
)
def test_checkin_rejects_malformed_day(invalid_day):
    hid = client.post("/habits", json={"name": "Hydrate"}).json()["id"]
    r = client.post(f"/habits/{hid}/checkin", json={"day": invalid_day})
    assert r.status_code == 422
    assert "invalid date format" in r.text.lower() or "expected yyyy-mm-dd" in r.text.lower()


def test_checkin_rejects_missing_day():
    hid = client.post("/habits", json={"name": "Hydrate"}).json()["id"]
    r = client.post(f"/habits/{hid}/checkin", json={})
    assert r.status_code == 422
