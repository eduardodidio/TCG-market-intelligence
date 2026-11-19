# T03 — Fix Config DB URL Env Override (2 tests)

**Status:** planned
**Wave:** 0
**Estimate:** S

## User Story

As a developer, I want `get_db_url()` tests to work correctly regardless of
whether a `.env` file exists in the project root.

## Problem

`tests/unit/test_config_db_url.py` — 2 tests fail:
- `test_database_url_takes_priority`
- `test_database_url_wins_over_render_dir`

The `.env` file (with real Neon DATABASE_URL) is loaded by `python-dotenv`
inside `get_db_url()` or at module import time, overriding the monkeypatched
env vars.

## Dev Notes

### Root Cause
`src/config.py` calls `load_dotenv()` which reads `.env` and sets env vars.
When the test monkeypatches `DATABASE_URL`, the dotenv loading may happen
after the monkeypatch (or the value is cached).

### Fix Strategy
1. Read `src/config.py` to understand when `load_dotenv()` is called.
2. In the test, monkeypatch `dotenv.load_dotenv` to be a no-op, OR
   monkeypatch `os.environ` AFTER the dotenv load, OR use
   `monkeypatch.setenv()` and also clear any module-level cache.
3. Alternative: if `get_db_url()` calls `load_dotenv()` internally, mock
   `load_dotenv` to prevent `.env` from being read during tests.

### Files to Modify
- `tests/unit/test_config_db_url.py` — fix monkeypatching approach

## Testing

- Run: `pytest tests/unit/test_config_db_url.py --override-ini="addopts=" -q`
- Expected: all 7 tests pass (5 already passing + 2 fixed)
