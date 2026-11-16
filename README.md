# Starter — Habit Tracker

A tiny FastAPI + SQLite service for habits and daily check-ins. You'll add two features
on branches, open PRs, and run an AI reviewer.

## Setup
```bash
pip install -r requirements.txt
pytest                      # 3 tests should pass
uvicorn main:app --reload   # http://localhost:8000  (docs at /docs)
```

## Endpoints
- `POST /habits` `{ "name": ... }`
- `GET /habits`
- `POST /habits/{id}/checkin` `{ "day": "2026-09-22" }`
- `GET /habits/{id}/checkins`

## Files
- `main.py` — the app
- `test_main.py` — pytest suite
- `docs/TASKS.md` — the two features to implement

## Guardrails (lint, format, tests)

Install the dev tools once:
```bash
pip install -r requirements-dev.txt     # app deps + black + ruff
```

| Command | Tool | What it catches |
|---|---|---|
| `ruff check .` | ruff | unused imports/variables, undefined names, wrong import order, common bug patterns (bugbear), outdated syntax |
| `black --check .` | black | any file that is not formatted the agreed way (100-char lines) |
| `pytest` | pytest | broken behaviour: a failing or erroring test exits non-zero |
| `./scripts/check.sh` | all three | runs the three in order and stops at the first failure |

Auto-fix locally: `ruff check --fix .` and `black .`

**CI:** `.github/workflows/ci.yml` runs the same three steps on every push to `main` and on
every pull request. If ruff, black or any test fails, the job fails and the PR shows a red ✗.
