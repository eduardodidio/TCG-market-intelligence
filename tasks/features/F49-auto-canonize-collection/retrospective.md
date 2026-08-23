# Retrospective -- F49 Auto-Canonize Collection

## What worked
- Clean separation between service layer (`bulk_canonize.py`) and API/CLI consumers. The service is reusable across all three entry points (API endpoint, background task from import, CLI command).
- Test plan was thorough (33 scenarios) and all scenarios were implemented (61 tests). Developer exceeded the plan estimate of ~28 tests.
- TechLead BLOCKING documentation items (diagrams, README) were fixed before QA review, unblocking the verdict.
- Backend-to-frontend contract alignment was exact -- Pydantic schema and TypeScript interface fields matched perfectly.
- The `BulkCanonizeButton` component is self-contained with clear props and managed state machine (idle/loading/result/error). Easy to test and reason about.

## What to avoid
- Calling async `provider.close()` from synchronous CLI context without `asyncio.run()`. The API layer consistently uses `await provider.close()` in async context, but the CLI forgot that `close()` is async. This is the second time a provider cleanup issue has been flagged (see F45 retrospective seed).
- Test plan text that specifies HTTP status codes (e.g., "returns 202") when the implementation uses a different code (200). The plan should describe behavior ("returns immediately with result"), not prescribe status codes that may change during implementation.

## Patterns to repeat
- Using `BackgroundTasks` for post-import canonization with a boolean flag (`canonize_scheduled`) in the response. This pattern cleanly communicates to the frontend whether background work was triggered without blocking the response.
- The `try/finally` provider cleanup pattern in API endpoints. Every endpoint that creates a `MypCardsProvider` wraps it in `try/finally` with `await provider.close()`. This should be a hard rule for all provider-consuming code paths.
- i18n test pattern using `it.each(KEYS)` with a `getNestedValue` helper to validate all keys exist in both locales. Compact, exhaustive, and easy to extend.

## Propagated to learnings
- memory/agent-learnings/qa.md -- async provider cleanup verification in CLI commands
- memory/agent-learnings/developer.md -- async close() calls from sync context require asyncio.run()
