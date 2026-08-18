# AI Context

This document provides the essential context any AI agent or LLM needs to
work effectively on the TCG Market Intelligence project. It distills
information from `CLAUDE.md`, `pyproject.toml`, and project memory into a
single reference.

## Project Summary

TCG Market Intelligence is a historical price data collector for trading
card games, starting with Magic: The Gathering. It scrapes pricing data
from Brazilian marketplace MYP Cards (mypcards.com), stores it in a local
SQLite database, and provides a CLI for backfill and update operations. The
goal is to build a time-series dataset of card prices for market analysis.

## Tech Stack

| Component       | Technology                          |
|-----------------|-------------------------------------|
| Language        | Python >= 3.11 (targeting 3.14)     |
| Database        | SQLite via SQLAlchemy >= 2.0        |
| HTTP Client     | curl_cffi >= 0.16 (Cloudflare bypass) |
| HTML Parsing    | beautifulsoup4 >= 4.12              |
| CLI Framework   | Click >= 8.1                        |
| Logging         | structlog >= 24.1                   |
| Retry Logic     | tenacity >= 8.2                     |
| Linter/Formatter| Ruff >= 0.5                         |
| Testing         | pytest >= 8.0, pytest-asyncio >= 0.23 |
| Build System    | setuptools >= 68                    |

## Key Files

- `CLAUDE.md` -- project conventions, guardrails, agent workflow
- `pyproject.toml` -- dependencies, build config, tool settings
- `src/domain/models.py` -- domain dataclasses (Card, PriceObservation, etc.)
- `src/domain/interfaces.py` -- CardSourceProvider ABC
- `src/providers/myp/provider.py` -- MYP Cards async provider (curl_cffi, rate-limited)
- `src/parsers/myp.py` -- HTML/JSON-LD/JS parsing for MYP Cards
- `src/database/` -- SQLAlchemy models + repository (upsert/idempotency)
- `src/collectors/backfill.py` -- orchestration (backfill, update, retry-failed)
- `src/cli/main.py` -- Click CLI entry point
- `tests/` -- 27 unit tests with HTML fixture files

## Architecture

The codebase follows a layered architecture. See
[ARCHITECTURE.md](ARCHITECTURE.md) for the full breakdown.

- **Domain Layer** (`src/domain/`) -- pure dataclasses and interfaces; no
  framework dependencies.
- **Provider Layer** (`src/providers/`) -- implements CardSourceProvider for
  each data source. Currently only MYP Cards. Handles HTTP, rate limiting,
  and Cloudflare bypass.
- **Parser Layer** (`src/parsers/`) -- extracts structured data from HTML
  pages (JSON-LD, embedded JS variables).
- **Database Layer** (`src/database/`) -- SQLAlchemy ORM models and a
  repository with idempotent upsert logic.
- **Collector Layer** (`src/collectors/`) -- orchestrates end-to-end flows
  (backfill a set, update prices, retry failures).
- **CLI Layer** (`src/cli/`) -- Click commands that wire everything together.

## Current State

- **F01 (MVP)**: shipped. MYP Cards backfill working -- successfully
  collected 277 price observations from Dominaria Remastered. Idempotency
  verified (re-runs insert 0 new rows). 27 tests passing.
- **F02 (Reproducibility Docs)**: in progress. Adding SETUP.md,
  DEVELOPMENT.md, ARCHITECTURE.md, SECURITY.md, CONTRIBUTING.md, and
  AI_CONTEXT.md.

## Conventions

- **Linting**: Ruff with rules `E`, `F`, `I`, `W`; line length 100.
- **Testing**: pytest with pytest-asyncio (`asyncio_mode = "auto"`). Tests
  under `tests/`. Use HTML fixture files for scraping tests -- never hit
  live sites.
- **Commits**: conventional commit style. Stage files individually.
- **Workflow**: 4-agent Waves workflow (Architect, Developer, Tech Lead, QA).
  Features are triggered with `/create-feature FXX <description>`.
- **Documentation**: every feature updates README.md, produces ADRs as
  needed, and maintains Mermaid diagrams under `docs/diagrams/`.

## What NOT to Do

These guardrails are enforced across the project (see `CLAUDE.md` and
[SECURITY.md](SECURITY.md) for the full list):

- **No force push** on shared branches (`main`, `master`, `develop`).
- **No `--no-verify`** to skip git hooks.
- **No `git add -A` or `git add .`** -- stage files individually.
- **No hardcoded secrets** -- use environment variables and `.env` files.
- **No committing secrets** (`.env`, `credentials.*`, `*.pem`, `*.key`).
- **No disabling tests or validation** to make things work.
- **No new dependencies** without explicit confirmation from the maintainer.
- **No destructive operations** (`rm -rf`, `DROP TABLE`, `git reset --hard`)
  without confirmation.
- **No CI/CD modifications** without explicit approval.

## Common Tasks

### Run tests

```bash
python -m pytest tests/ -v
```

### Run linter

```bash
ruff check src/ tests/
```

### Backfill a set (example: Dominaria Remastered)

```bash
collector backfill --set dmr --limit 5
```

### Update prices for existing cards

```bash
collector update
```

### Add a new provider

1. Create a new directory under `src/providers/<name>/`.
2. Implement `CardSourceProvider` from `src/domain/interfaces.py`.
3. Add a parser under `src/parsers/<name>.py`.
4. Register the provider in the CLI.
5. Add tests with HTML fixture files under `tests/`.
