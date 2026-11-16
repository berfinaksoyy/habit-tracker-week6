from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

import main
from main import app, calculate_streak, get_db

client = TestClient(app)

# Freeze "today" for the endpoint and the tests, so a run that crosses midnight
# cannot change the result (raised by CodeRabbit on PR #1).
FROZEN_TODAY = date(2026, 3, 10)


class FrozenDate(date):
    @classmethod
    def today(cls):
        return FROZEN_TODAY


@pytest.fixture(autouse=True)
def frozen_clock(monkeypatch):
    monkeypatch.setattr(main, "date", FrozenDate)


def test_create_and_list_habit():
    r = client.post("/habits", json={"name": "Read 20 minutes"})
    assert r.status_code == 200
    hid = r.json()["id"]
    r2 = client.get("/habits")
    assert r2.status_code == 200
    assert any(h["id"] == hid for h in r2.json())


def test_checkin_flow():
    hid = client.post("/habits", json={"name": "Stretch"}).json()["id"]
    r = client.post(f"/habits/{hid}/checkin", json={"day": "2026-09-22"})
    assert r.status_code == 200
    r2 = client.get(f"/habits/{hid}/checkins")
    assert r2.json() == ["2026-09-22"]


def test_checkin_unknown_habit_404():
    r = client.post("/habits/99999/checkin", json={"day": "2026-09-22"})
    assert r.status_code == 404


def test_streak_unknown_habit_404():
    r = client.get("/habits/99999/streak")
    assert r.status_code == 404


def test_streak_empty():
    hid = client.post("/habits", json={"name": "Meditate"}).json()["id"]
    r = client.get(f"/habits/{hid}/streak")
    assert r.status_code == 200
    assert r.json() == {"streak": 0}


def test_streak_today_only():
    hid = client.post("/habits", json={"name": "Walk dog"}).json()["id"]
    today = FROZEN_TODAY
    client.post(f"/habits/{hid}/checkin", json={"day": today.isoformat()})
    r = client.get(f"/habits/{hid}/streak")
    assert r.status_code == 200
    assert r.json() == {"streak": 1}


def test_streak_consecutive_days_including_today():
    hid = client.post("/habits", json={"name": "Drink water"}).json()["id"]
    today = FROZEN_TODAY
    for i in range(4):
        day = today - timedelta(days=i)
        client.post(f"/habits/{hid}/checkin", json={"day": day.isoformat()})
    r = client.get(f"/habits/{hid}/streak")
    assert r.status_code == 200
    assert r.json() == {"streak": 4}


def test_streak_yesterday_not_today():
    hid = client.post("/habits", json={"name": "Code"}).json()["id"]
    today = FROZEN_TODAY
    client.post(f"/habits/{hid}/checkin", json={"day": (today - timedelta(days=1)).isoformat()})
    client.post(f"/habits/{hid}/checkin", json={"day": (today - timedelta(days=2)).isoformat()})
    r = client.get(f"/habits/{hid}/streak")
    assert r.status_code == 200
    assert r.json() == {"streak": 2}


def test_streak_broken():
    hid = client.post("/habits", json={"name": "Sleep early"}).json()["id"]
    today = FROZEN_TODAY
    client.post(f"/habits/{hid}/checkin", json={"day": (today - timedelta(days=2)).isoformat()})
    client.post(f"/habits/{hid}/checkin", json={"day": (today - timedelta(days=3)).isoformat()})
    r = client.get(f"/habits/{hid}/streak")
    assert r.status_code == 200
    assert r.json() == {"streak": 0}


def test_streak_gap_with_today():
    hid = client.post("/habits", json={"name": "Journal"}).json()["id"]
    today = FROZEN_TODAY
    client.post(f"/habits/{hid}/checkin", json={"day": today.isoformat()})
    client.post(f"/habits/{hid}/checkin", json={"day": (today - timedelta(days=2)).isoformat()})
    r = client.get(f"/habits/{hid}/streak")
    assert r.status_code == 200
    assert r.json() == {"streak": 1}


def test_streak_duplicate_and_future():
    hid = client.post("/habits", json={"name": "Floss"}).json()["id"]
    today = FROZEN_TODAY
    # Duplicate check-in today
    client.post(f"/habits/{hid}/checkin", json={"day": today.isoformat()})
    client.post(f"/habits/{hid}/checkin", json={"day": today.isoformat()})
    # Future check-in tomorrow
    client.post(f"/habits/{hid}/checkin", json={"day": (today + timedelta(days=1)).isoformat()})
    r = client.get(f"/habits/{hid}/streak")
    assert r.status_code == 200
    assert r.json() == {"streak": 1}


# --- calculate_streak with a fixed "today", so the result never depends on the clock ---

FIXED_TODAY = date(2026, 3, 10)


def days_ago(*offsets):
    return {FIXED_TODAY - timedelta(days=n) for n in offsets}


def test_calculate_streak_fixed_date_including_today():
    assert calculate_streak(days_ago(0, 1, 2), today=FIXED_TODAY) == 3


def test_calculate_streak_fixed_date_ending_yesterday():
    assert calculate_streak(days_ago(1, 2), today=FIXED_TODAY) == 2


def test_calculate_streak_fixed_date_broken():
    assert calculate_streak(days_ago(2, 3), today=FIXED_TODAY) == 0


def test_calculate_streak_across_month_boundary():
    today = date(2026, 3, 1)
    checkins = {date(2026, 3, 1), date(2026, 2, 28), date(2026, 2, 27)}
    assert calculate_streak(checkins, today=today) == 3


def test_streak_ignores_malformed_day_in_database():
    hid = client.post("/habits", json={"name": "Bad data"}).json()["id"]
    client.post(f"/habits/{hid}/checkin", json={"day": FROZEN_TODAY.isoformat()})
    with get_db() as conn:  # bypass the API: simulate a bad row already in the DB
        conn.execute("INSERT INTO checkins (habit_id, day) VALUES (?, ?)", (hid, "hello"))
    r = client.get(f"/habits/{hid}/streak")
    assert r.status_code == 200
    assert r.json() == {"streak": 1}
