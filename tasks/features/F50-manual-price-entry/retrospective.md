# Retrospective -- F50

## What worked
- Reusing `PriceObservationRow` with `source="manual"` avoided schema migration and kept the implementation simple.
- Price source priority logic (manual wins same-day, latest date wins cross-day) is clean and well-documented in the docstring.
- TechLead caught the critical B1 bug (external_id mismatch) before QA, preventing a non-functional feature from shipping.
- Test coverage significantly exceeded the test plan (90 tests vs 38 planned).
- Frontend components (`PriceSourceBadge`, `ManualPriceInput`) are clean presentational components with proper i18n integration.

## What to avoid
- Writing and reading the same logical entity with different computed keys (`manual_{entry_id}` vs `manual_{card_id}`) without a round-trip integration test. The write-side and read-side tests passed independently because each used hardcoded fixture data that matched its own key format, masking the mismatch.
- Relying on isolated unit tests when a feature involves write-then-read across different repository methods. The gap was only visible when tracing the data flow end-to-end.

## Patterns to repeat
- When a feature stores data with a computed key (like `f"manual_{x}"`), always add at least one round-trip test that writes via the write method and reads back via the read method used in production. This is the minimum viable integration test for key consistency.
- TechLead review as a bug-finding gate before QA. B1 would have shipped without the TechLead catch.
- Auto-creation of dependent records (CardRow for unlinked entries) with proper test coverage of both the auto-create path and the already-linked path.

## Propagated to learnings
- memory/agent-learnings/developer.md -- round-trip test requirement for computed key features
- memory/agent-learnings/qa.md -- verify computed key consistency via round-trip tests
