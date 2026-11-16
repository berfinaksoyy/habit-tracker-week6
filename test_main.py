from datetime import date, timedelta

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
    today = date.today()
    client.post(f"/habits/{hid}/checkin", json={"day": today.isoformat()})
    r = client.get(f"/habits/{hid}/streak")
    assert r.status_code == 200
    assert r.json() == {"streak": 1}


def test_streak_consecutive_days_including_today():
    hid = client.post("/habits", json={"name": "Drink water"}).json()["id"]
    today = date.today()
    for i in range(4):
        day = today - timedelta(days=i)
        client.post(f"/habits/{hid}/checkin", json={"day": day.isoformat()})
    r = client.get(f"/habits/{hid}/streak")
    assert r.status_code == 200
    assert r.json() == {"streak": 4}


def test_streak_yesterday_not_today():
    hid = client.post("/habits", json={"name": "Code"}).json()["id"]
    today = date.today()
    client.post(f"/habits/{hid}/checkin", json={"day": (today - timedelta(days=1)).isoformat()})
    client.post(f"/habits/{hid}/checkin", json={"day": (today - timedelta(days=2)).isoformat()})
    r = client.get(f"/habits/{hid}/streak")
    assert r.status_code == 200
    assert r.json() == {"streak": 2}


def test_streak_broken():
    hid = client.post("/habits", json={"name": "Sleep early"}).json()["id"]
    today = date.today()
    client.post(f"/habits/{hid}/checkin", json={"day": (today - timedelta(days=2)).isoformat()})
    client.post(f"/habits/{hid}/checkin", json={"day": (today - timedelta(days=3)).isoformat()})
    r = client.get(f"/habits/{hid}/streak")
    assert r.status_code == 200
    assert r.json() == {"streak": 0}


def test_streak_gap_with_today():
    hid = client.post("/habits", json={"name": "Journal"}).json()["id"]
    today = date.today()
    client.post(f"/habits/{hid}/checkin", json={"day": today.isoformat()})
    client.post(f"/habits/{hid}/checkin", json={"day": (today - timedelta(days=2)).isoformat()})
    r = client.get(f"/habits/{hid}/streak")
    assert r.status_code == 200
    assert r.json() == {"streak": 1}


def test_streak_duplicate_and_future():
    hid = client.post("/habits", json={"name": "Floss"}).json()["id"]
    today = date.today()
    # Duplicate check-in today
    client.post(f"/habits/{hid}/checkin", json={"day": today.isoformat()})
    client.post(f"/habits/{hid}/checkin", json={"day": today.isoformat()})
    # Future check-in tomorrow
    client.post(f"/habits/{hid}/checkin", json={"day": (today + timedelta(days=1)).isoformat()})
    r = client.get(f"/habits/{hid}/streak")
    assert r.status_code == 200
    assert r.json() == {"streak": 1}
