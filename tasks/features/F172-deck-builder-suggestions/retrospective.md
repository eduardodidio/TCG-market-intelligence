# Retrospective — F172

## What worked
- Isolating the new `deck_suggestions` package (own models/repository, `checkfirst` table create) kept the diff of `src/database/models.py` at zero, exactly as the architect mandated — no migration risk introduced.
- Deferring all shared/high-conflict files (`app.py`, `cli/main.py`, `.bat`, `.env.example`, `README.md`, both locale JSONs) to Wave 4 (T17/T18) avoided any cross-task stomping across an 18-task, 5-wave feature run in parallel with F171/F173–F179.
- The CLI-vs-API runner abstraction (`get_runner()`) let the team honor the "no new dependency" constraint (no `anthropic` SDK) cleanly — `ClaudeApiRunner` reused the existing `httpx` dependency instead of prompting a fresh approval mid-feature.
- Soft-filtering legality (`banned`/`not_legal` only) instead of requiring a positive legal row fixed AC1 without needing a data backfill of `card_legalities`.

## What to avoid
- A later Wave (T18, doing i18n) found that an earlier component (`SuggestionRequestList.tsx`, T12) used a different key namespace (`deckSuggestions.*`) than every sibling component (`deckSuggest.*`), and patched around it by adding keys under **both** namespaces instead of fixing the source component. This leaves permanent dead keys in `en.json`/`pt-BR.json`.
- Wave summaries reported work as "uncommitted in the worktree" at hand-off between Waves, which weakens `git diff --stat HEAD~1..HEAD`-style verification for the next Wave/TechLead.

## Patterns to repeat
- Reserve genuinely shared/high-conflict files for a dedicated final wave, and have the Architect name them explicitly in the task manifest (as done here) rather than leaving overlap detection to the Developer.
- When a constraint says "no new dependency," design the abstraction boundary (here, `get_runner()`) so an alternate implementation can reuse an existing dependency instead of needing a new one.

## Propagated to learnings
- memory/agent-learnings/developer.md — namespace-drift fix-at-source lesson (from TechLead's IMPORTANT finding)
- memory/agent-learnings/techlead.md — treat cross-task naming drift as IMPORTANT, not MINOR, since patch-around fixes leave permanent dead code
- memory/agent-learnings/architect.md — consider requiring a Wave-end commit as a hard gate before the next Wave starts
