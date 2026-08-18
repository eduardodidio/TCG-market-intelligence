# QA Learnings

(QA appends to this file at the end of every feature retrospective.
Each entry is a lesson that generalizes beyond a single bug.)

## F03 -- Analytics Engine (2026-08-18)

- **Always run smoke tests against a real database when one exists.** The live `analyze list` + `analyze card` smoke tests caught nothing that unit tests missed this time, but they validated the full stack (SQLite -> Repository -> Analytics -> CLI output) in a way mocked tests cannot. Make this a standard step.
- **When `pytest-cov` is unavailable, do a manual branch audit.** Walk through each function's conditionals and verify each branch has a corresponding test. This is slower but sufficient for a QA verdict. However, advocate for adding `pytest-cov` to dev deps so future QA runs can automate this.
