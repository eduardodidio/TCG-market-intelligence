# TechLead Learnings

(QA appends to this file at the end of every feature retrospective.
Each entry is a lesson that generalizes beyond a single bug.)

## F01 -- MYP Cards Backfill (2026-08-18)

- **Enforce lint cleanliness from the first feature.** F01 left 10 lint errors (9 unused imports, 1 line-length) that were only discovered during F02. Adding `ruff check` to the dev workflow from project setup prevents accumulation of technical debt.
- **Require QA report and retrospective for every feature, even the first.** F01 shipped without a QA report or TechLead review, so no learnings were captured. The framework ceremonies must be enforced from feature #1.

## F02 -- Reproducibility & Living Documentation (2026-08-18)

- **Spot-check relative link paths in docs-heavy features.** Three broken cross-links shipped in F02 because link hrefs didn't match actual filenames or used wrong relative paths. In any feature that delivers multiple docs, verify every cross-link resolves to a real file.
- **Verify ADR index tables are updated when new ADRs are added.** ARCHITECTURE.md's ADR table only listed ADR-0001 after ADR-0002 was delivered in a later wave. When tasks span multiple waves, check that index tables reflect all delivered artifacts.

## F03 -- Analytics Engine (2026-08-18)

- **Document statistical methodology choices in docstrings.** The choice of population std dev (`/ n`) vs. sample std dev (`/ (n-1)`) is defensible but not documented. For domain-specific decisions like this, a one-line note in the docstring prevents future confusion.
- **Flag missing dev tooling early.** `pytest-cov` was not in dev dependencies, so automated branch coverage could not be measured during review. Add coverage tooling to `pyproject.toml` dev deps as part of project setup (Wave 0) rather than discovering the gap at review time.
