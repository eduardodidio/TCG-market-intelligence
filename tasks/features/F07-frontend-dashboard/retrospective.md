# Retrospective -- F07

## What worked
- Component hierarchy is clean and conventional -- easy to navigate and test
- Centralized API client with typed envelopes made testing straightforward
- Fixture factory functions (`mockCardSummaries`, `mockApiError`, etc.) prevented duplication across 20 test files
- Code splitting via `React.lazy()` was implemented from the start, not retrofitted
- TechLead review was thorough and caught all minor issues before QA

## What to avoid
- Configuring features you do not use (path alias `@/` was set up but never adopted) -- creates confusion about project conventions
- Shipping without `@vitest/coverage-v8` in devDependencies when coverage reporting is expected
- Exporting constants that no consumer imports (`PERIOD_OPTIONS`) -- dead code that accumulates over time

## Patterns to repeat
- Dark theme utility classes via Tailwind -- consistent, easy to maintain
- `useApi` hook with `AbortController` cleanup -- prevents memory leaks and stale responses
- Mocking `ResponsiveContainer` from Recharts in jsdom tests -- correct approach since jsdom has no layout engine
- TEA-generated test plan with fixture definitions aligned to tasks -- QA could validate coverage against a checklist

## Propagated to learnings
- memory/agent-learnings/architect.md -- unused configuration creates confusion
- memory/agent-learnings/developer.md -- always include coverage tooling in scaffolding, avoid unused exports
- memory/agent-learnings/qa.md -- install coverage tooling early, act() warnings are cosmetic in React 19
- memory/agent-learnings/techlead.md -- minor notes become QA quick-wins when actionable
