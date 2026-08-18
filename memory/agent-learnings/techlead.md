# TechLead Learnings

(QA appends to this file at the end of every feature retrospective.
Each entry is a lesson that generalizes beyond a single bug.)

## F03 -- Analytics Engine (2026-08-18)

- **Document statistical methodology choices in docstrings.** The choice of population std dev (`/ n`) vs. sample std dev (`/ (n-1)`) is defensible but not documented. For domain-specific decisions like this, a one-line note in the docstring prevents future confusion.
- **Flag missing dev tooling early.** `pytest-cov` was not in dev dependencies, so automated branch coverage could not be measured during review. Add coverage tooling to `pyproject.toml` dev deps as part of project setup (Wave 0) rather than discovering the gap at review time.
