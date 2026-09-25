# Retrospective — F173

## What worked
- Vertical-slice package isolation (`src/metagame/` owning its own models/tables via
  `Base.metadata.create_all(tables=[...])`, never touching `database/models.py` or
  `database/repository.py`) meant zero merge conflicts with sibling features landing on
  the same branch, and let the collector/valuation/repository each reach ~100% unit
  coverage in isolation.
- `PoliteFetcher` fail-closed design (treat any robots.txt fetch error — including this
  sandbox's proxy 403 — as `disallow_all=True`) meant the safety property (AC3) was
  verifiable live in a network-blocked sandbox: a real dry-run exercised the exact
  "can't reach robots.txt → refuse to fetch" path without needing live internet.
- Pairing the registration-only Wave (T15) with dedicated `test_meta_decks_registration.py`
  / `test_cli_metagame_registration.py` caught what would otherwise be an untested class
  of bug (route/command planned but never actually wired into `app.py`/`main.py`).

## What to avoid
- A file living under a `.gitignore`'d directory (`bats/`) can be fully built, tested
  locally, and marked "done" by its task while never reaching git, because `git add`
  silently skips ignored paths. This went unnoticed until a later Wave's developer
  happened to check `git status --ignored`.
- Don't trust an earlier Wave/TechLead's cached "N pre-existing failures" count without
  re-running the full suite at the QA gate — the number will drift as sibling features
  land on the same branch (this feature's QA saw 109 failures where the Wave-4 summary
  recorded 116; direction was favorable here, but the check must still be done fresh
  every time, per the F171 lesson already in `qa.md`).

## Patterns to repeat
- For any new package that talks to a third-party site under ToS/robots constraints,
  make the "can't verify permission" case fail closed by construction, and add a test
  (or live dry-run) that exercises that exact path — this makes the safety property
  independently checkable even when live network is unavailable at QA time.
- For any task whose only job is wiring an already-built module into a shared
  entrypoint (router registration, CLI command registration), require a dedicated
  `test_*_registration.py` in the same task, not just reliance on earlier unit tests.

## Propagated to learnings
- memory/agent-learnings/developer.md — gitignored-directory files need `git add -f`
  verification before a task is marked done (reinforces the same lesson already
  recorded by TechLead in the Wave-4 review; now generalized to the shared learnings
  file so future Developer runs read it up front).
- memory/agent-learnings/architect.md — registration-only Waves should mandate a
  dedicated `test_*_registration.py` task, and any task touching a `.gitignore`'d path
  should call that out explicitly in its Definition of Done.
- memory/agent-learnings/qa.md — reconfirms (does not duplicate) the existing F171
  lesson: re-run the full suite fresh at every QA gate rather than citing an earlier
  wave's failure count, even when the new count is lower.
