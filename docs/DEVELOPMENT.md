# Development Guide

Conventions, tooling, and workflows for contributing to TCG Market Intelligence.

## Project Structure

```
src/
  analytics/        Pure analytics engine (no I/O, Decimal-only)
    indicators.py   MA, ATH/ATL, volatility, momentum functions
  cli/              Click CLI entry point
    main.py         Commands: backfill, update, analyze card/list
  collectors/       Orchestration layer
    backfill.py     Backfill, update, retry-failed logic
  database/         Persistence layer (SQLAlchemy + SQLite)
    models.py       ORM models
    repository.py   Upsert/query with idempotency + price series
  domain/           Pure domain layer (no I/O)
    models.py       Dataclasses (Card, PriceObservation, analytics)
    interfaces.py   CardSourceProvider ABC
  parsers/          HTML/JSON-LD parsing
    myp.py          MYP Cards-specific parser
  providers/        Data source implementations
    myp/
      provider.py   Async provider (curl_cffi, rate-limited)
tests/
  unit/
    test_analytics_models.py   Domain model tests (11 tests)
    test_backfill.py           Concurrency/resume tests (11 tests)
    test_cli_analytics.py      CLI analyze commands (8 tests)
    test_indicators.py         Analytics functions (48 tests)
    test_parsers.py            HTML/JSON-LD parsing (18 tests)
    test_repository.py         DB upsert/batch tests (12 tests)
    test_repository_queries.py Price series queries (10 tests)
  integration/
    test_collector_pipeline.py Full pipeline tests (10 tests)
```

For a deeper architectural overview, see [ARCHITECTURE.md](ARCHITECTURE.md) and the
diagrams under [docs/diagrams/](./diagrams/).

## Coding Style

The project uses **ruff** for both linting and formatting. Configuration lives
in `pyproject.toml`:

```toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "W"]
```

Key rules:
- Line length: **100 characters**
- Target: **Python 3.11+**
- Enabled rule sets: pycodestyle errors (E), pyflakes (F), isort (I), pycodestyle warnings (W)

## Testing

**Framework:** pytest + pytest-asyncio

```bash
make test
```

Conventions:
- Tests live under `tests/unit/` (integration tests will go in `tests/integration/`)
- Async test functions are detected automatically (`asyncio_mode = "auto"` in pyproject.toml)
- Fixtures with real HTML samples go in `tests/fixtures/`
- Name test files `test_<module>.py` and test functions `test_<behavior>()`
- Keep unit tests fast -- mock network calls, use in-memory SQLite for DB tests

Running a single test file:

```bash
.venv/bin/python -m pytest tests/unit/test_parsers.py -v
```

Running tests matching a keyword:

```bash
.venv/bin/python -m pytest -k "price" -v
```

## Linting and Formatting

```bash
# Check for lint errors (does not modify files)
make lint

# Auto-format code
make format
```

Both commands run ruff against `src/` and `tests/`.

Fix lint errors automatically (when possible):

```bash
.venv/bin/ruff check src/ tests/ --fix
```

## Adding a New Provider

To add a new card data source (e.g., LigaMagic, TCGPlayer):

1. **Create the provider module** at `src/providers/<name>/provider.py`
2. **Implement `CardSourceProvider`** -- the ABC defined in `src/domain/interfaces.py`
3. **Create a parser** at `src/parsers/<name>.py` for site-specific HTML/JSON parsing
4. **Register the provider** in the CLI or collector so it can be selected at runtime
5. **Add tests** under `tests/unit/test_<name>_parser.py` with fixture HTML files
6. **Update docs** -- add a note in README.md about the new data source

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/) style:

```
<type>(<scope>): <short description>

<optional body>
```

Types:
- `feat` -- new feature
- `fix` -- bug fix
- `docs` -- documentation only
- `test` -- adding or updating tests
- `refactor` -- code change that neither fixes a bug nor adds a feature
- `chore` -- build, CI, tooling changes

Examples:
```
feat(providers): add LigaMagic price scraper
fix(parsers): handle missing JSON-LD on MYP card pages
docs: add SETUP.md and DEVELOPMENT.md
test(repository): add idempotency edge-case tests
```

## Branch Strategy

Currently using **main-only** workflow:
- All work happens on `main`
- When the team grows, switch to short-lived feature branches with PR review

## Useful Make Targets

| Target           | Description                                       |
|------------------|---------------------------------------------------|
| `make help`      | Show all available targets with descriptions       |
| `make setup`     | Create venv and install deps (dev + prod)          |
| `make test`      | Run pytest with verbose output                     |
| `make lint`      | Run ruff check on `src/` and `tests/`              |
| `make format`    | Run ruff format on `src/` and `tests/`             |
| `make clean`     | Remove `__pycache__`, `.pytest_cache`, egg-info, dist, build, db |
| `make run-backfill` | Run backfill collector (use `SET=` and `LIMIT=` to customize) |
| `make run-update`   | Run incremental update collector                 |

Run `make help` at any time to see the full list with descriptions.
