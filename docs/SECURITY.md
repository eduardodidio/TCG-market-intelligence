# Security Policy

This document describes the security practices and policies for the
TCG Market Intelligence project.

## Secrets Management

- **Never hardcode secrets** in source code. Use environment variables for all
  sensitive values (API keys, tokens, database credentials).
- Store local secrets in a `.env` file at the project root. This file is
  listed in `.gitignore` and must never be committed.
- Files that must never be committed: `.env`, `credentials.*`, `*.pem`,
  `*.key`, and any file containing tokens or private keys.

## Dependencies

- All runtime dependencies are pinned to minimum major versions in
  `pyproject.toml`.
- Do not introduce new dependencies without explicit confirmation from the
  project maintainer.
- Dev dependencies (`pytest`, `ruff`, etc.) are isolated under
  `[project.optional-dependencies] dev`.
- Periodically review dependencies for known vulnerabilities.

## Data Scraping Ethics

- **Respect `robots.txt`**: always check and comply with a site's robots.txt
  before scraping. If a user-agent is blocked, do not circumvent the block.
- **Rate limiting**: the scraper enforces configurable delays between requests
  to avoid overloading target servers. Never disable or reduce rate limits
  below reasonable thresholds.
- **No API abuse**: do not send excessive concurrent requests, bypass
  authentication mechanisms, or access endpoints explicitly disallowed by
  the site operator.
- **Data usage**: scraped data is for personal market analysis only. Do not
  redistribute raw scraped data without permission from the data source.

## Git Safety

These rules are enforced by project convention and mirror the guardrails in
`CLAUDE.md`:

- **No force push**: never run `git push --force` or `--force-with-lease`
  on shared branches (`main`, `master`, `develop`) without explicit approval.
- **No hook bypass**: never use `--no-verify` to skip pre-commit or pre-push
  hooks.
- **No destructive resets**: never run `git reset --hard` on uncommitted work.
- **No bulk staging**: never use `git add -A` or `git add .` -- stage files
  individually to avoid accidentally committing secrets or unwanted files.
- **No amending shared commits**: never amend commits that have already been
  pushed to a shared branch.
- **No rebase on shared branches**: never run `git rebase` on `main`,
  `master`, or `develop`.
- **No secrets in commits**: never commit files containing secrets (`.env`,
  `credentials.*`, private keys, tokens).

## Code Safety

- Never disable validation, authentication, or tests to "make things work."
- Validate all input at system boundaries (user input, external APIs).
- Do not modify CI/CD configuration without explicit confirmation.
- Do not run destructive operations (`rm -rf`, `DROP TABLE`, `kill -9`)
  without explicit confirmation.

## Reporting Vulnerabilities

If you discover a security vulnerability in this project:

1. **Do not open a public issue.** Security issues must be reported privately.
2. Contact the maintainer directly at the email listed in `pyproject.toml` or
   via GitHub's private vulnerability reporting feature on the
   [repository](https://github.com/eduardodidio/TCG-market-intelligence).
3. Include a clear description of the vulnerability, steps to reproduce, and
   any potential impact.
4. The maintainer will acknowledge receipt within 72 hours and provide a
   timeline for a fix.
