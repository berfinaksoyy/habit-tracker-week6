from datetime import date, timedelta

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
    assert "yyyy-mm-dd" in r.text.lower()


def test_checkin_rejects_missing_day():
    hid = client.post("/habits", json={"name": "Hydrate"}).json()["id"]
    r = client.post(f"/habits/{hid}/checkin", json={})
    assert r.status_code == 422


def error_message(response):
    """The message of the first validation error, as the client sees it."""
    return response.json()["detail"][0]["msg"]


def test_empty_name_message_has_no_value_error_prefix():
    r = client.post("/habits", json={"name": "   "})
    assert r.status_code == 422
    assert error_message(r) == "Habit name cannot be empty"


def test_create_habit_rejects_too_long_name():
    r = client.post("/habits", json={"name": "x" * 101})
    assert r.status_code == 422
    assert error_message(r) == "Habit name must be at most 100 characters"


def test_create_habit_accepts_name_at_limit():
    r = client.post("/habits", json={"name": "x" * 100})
    assert r.status_code == 200


@pytest.mark.parametrize("not_real", ["2026-02-30", "2026-13-01", "2026-00-10", "2025-02-29"])
def test_checkin_rejects_day_that_does_not_exist(not_real):
    hid = client.post("/habits", json={"name": "Hydrate"}).json()["id"]
    r = client.post(f"/habits/{hid}/checkin", json={"day": not_real})
    assert r.status_code == 422
    assert error_message(r) == f"'{not_real}' is not a real calendar date"


def test_checkin_accepts_leap_day():
    hid = client.post("/habits", json={"name": "Hydrate"}).json()["id"]
    r = client.post(f"/habits/{hid}/checkin", json={"day": "2024-02-29"})
    assert r.status_code == 200


def test_checkin_rejects_future_day():
    hid = client.post("/habits", json={"name": "Hydrate"}).json()["id"]
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    r = client.post(f"/habits/{hid}/checkin", json={"day": tomorrow})
    assert r.status_code == 422
    assert error_message(r) == "Day cannot be in the future"


def test_checkin_accepts_today():
    hid = client.post("/habits", json={"name": "Hydrate"}).json()["id"]
    r = client.post(f"/habits/{hid}/checkin", json={"day": date.today().isoformat()})
    assert r.status_code == 200
