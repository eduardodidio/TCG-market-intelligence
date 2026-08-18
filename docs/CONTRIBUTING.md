# Contributing to TCG Market Intelligence

Thank you for your interest in contributing. This guide covers the process
for both human and AI contributors.

## Getting Started

1. Clone the repository and follow the setup instructions in
   [SETUP.md](SETUP.md).
2. Read [DEVELOPMENT.md](DEVELOPMENT.md) for day-to-day development
   workflow, commands, and coding conventions.
3. Review [SECURITY.md](SECURITY.md) for security policies and guardrails.

## Development Workflow

The project follows a structured development process. See
[DEVELOPMENT.md](DEVELOPMENT.md) for details on:

- Setting up your virtual environment
- Running tests and linting
- Database management
- CLI usage

## Feature Process

New features follow the **4-agent Waves workflow**:

1. **Trigger a feature** using the `/create-feature FXX <description>` slash
   command.
2. The **Architect** plans tasks grouped into parallel Waves.
3. The **Developer** implements each task.
4. The **Tech Lead** reviews architecture, tests, and diagrams.
5. **QA** validates end-to-end and fills test gaps.

Feature tasks live under `tasks/features/<feature-id>/`. Each task has its
own markdown file with acceptance criteria and test scenarios.

## Code Style

- The project uses **Ruff** for linting and formatting.
- Line length limit: 100 characters.
- Lint rules: `E`, `F`, `I`, `W` (pycodestyle errors/warnings, pyflakes,
  isort).
- See the `[tool.ruff]` section in `pyproject.toml` for the full
  configuration.
- See [DEVELOPMENT.md](DEVELOPMENT.md) for more on coding conventions.

## Pull Requests

A good pull request:

- Has a clear, concise title (under 70 characters).
- Includes a summary of what changed and why.
- References the relevant feature/task ID (e.g., `F01-T03`).
- Passes all tests (`pytest`) and linting (`ruff check`).
- Does not introduce new dependencies without prior discussion.
- Stages files individually -- never uses `git add -A` or `git add .`.

## Documentation

Every feature that ships **must** update the project documentation:

- **README.md**: add a short note about what was delivered. This is not
  optional.
- **ADRs**: significant architecture decisions get a new ADR under
  `docs/adr/`.
- **Diagrams**: every feature must produce or update at least two Mermaid
  diagrams under `docs/diagrams/` (architecture + user journey).
- **PRDs**: every feature has a PRD under `docs/prd/` before development
  begins.

See `CLAUDE.md` > "Documentation Maintenance Rules" for the full policy.

## Testing

- All tests live under `tests/` and use **pytest** with **pytest-asyncio**.
- Every feature must maintain or increase test coverage.
- Run the test suite before submitting a PR:

  ```bash
  python -m pytest tests/ -v
  ```

- If your change touches scraping logic, include fixture-based tests using
  saved HTML snapshots (do not hit live sites in tests).

## Questions?

Open an issue on the
[GitHub repository](https://github.com/eduardodidio/TCG-market-intelligence/issues)
or check the existing documentation under `docs/`.
