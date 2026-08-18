# Architecture Decisions

## About

This project records significant architecture decisions as **Architecture
Decision Records (ADRs)**. Each ADR is a short Markdown document stored
under [`docs/adr/`](adr/).

ADRs capture the context, decision, and consequences of choices that affect
the project's structure, technology stack, or development workflow. They
serve as a lightweight log so that future contributors understand *why*
things are the way they are.

## Decision Log

| ADR  | Title                                | Status   | Date       |
|------|--------------------------------------|----------|------------|
| [0001](adr/0001-adopt-claude-didio-framework.md) | Adopt claude-didio-config framework | accepted | 2026-08-18 |
| [0002](adr/0002-web-stack-decision.md) | Web stack decision (FastAPI) | proposed | 2026-08-18 |

## How to Add a Decision

1. Copy the template from [`docs/adr/0000-template.md`](adr/0000-template.md).
2. Number it sequentially (e.g. `0003-short-title.md`).
3. Fill in the **Context**, **Decision**, and **Consequences** sections.
4. Set the **Status** to `proposed`, then update to `accepted` after review.
5. Add a row to the Decision Log table above.
