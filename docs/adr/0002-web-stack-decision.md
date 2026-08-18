# ADR-0002: Use FastAPI for REST API

**Status:** proposed
**Date:** 2026-08-18
**Deciders:** Eduardo Rutkoski Didio

## Context

TCG Market Intelligence currently operates as a CLI-driven data collection
pipeline. The next evolution is exposing the collected price data through a
REST API so that external consumers (dashboards, bots, other services) can
query cards, price history, and market statistics programmatically.

We need to choose a Python web framework to serve this API. The choice must
align with the existing codebase, which is:

- **Async-first** -- providers use `async/await` with `curl_cffi`, tests run
  under `pytest-asyncio`.
- **SQLAlchemy-based** -- the database layer already uses SQLAlchemy ORM with
  SQLite.
- **Domain-model driven** -- pure dataclasses define the domain; the API layer
  should validate and serialize these cleanly.
- **Documentation-oriented** -- an auto-generated API reference (OpenAPI /
  Swagger) is highly desirable for a data API.

The planned API surface is documented in [`docs/API.md`](../API.md) and
includes endpoints for cards, sets, market movers, aggregate stats, and
admin-triggered collection jobs.

## Decision

Use [FastAPI](https://fastapi.tiangolo.com/) as the web framework for the
REST API, with [Uvicorn](https://www.uvicorn.org/) as the ASGI server.

Reasons:

1. **Async-native** -- FastAPI is built on Starlette and supports
   `async def` handlers natively, matching our existing async provider and
   collector code without adaptation.
2. **Automatic OpenAPI documentation** -- FastAPI generates interactive
   `/docs` (Swagger UI) and `/redoc` endpoints from type annotations, which
   is critical for a data API that external consumers will integrate with.
3. **Pydantic validation** -- request and response models are defined as
   Pydantic classes with automatic validation, serialization, and error
   messages. Pydantic models can mirror or wrap the existing domain
   dataclasses with minimal boilerplate.
4. **SQLAlchemy integration** -- well-documented patterns for dependency
   injection of database sessions, compatible with both sync and async
   SQLAlchemy engines.
5. **Mature ecosystem** -- large community, extensive middleware (CORS,
   authentication, rate limiting), and battle-tested in production at scale.
6. **Dependency injection** -- FastAPI's `Depends()` system cleanly handles
   cross-cutting concerns (database sessions, authentication, pagination)
   without global state.

## Consequences

**Easier:**

- Async route handlers can call existing async provider methods directly
  without wrapping or thread-pool delegation.
- Auto-generated OpenAPI/Swagger docs eliminate the need to maintain a
  separate API reference manually.
- Pydantic response models can share structure with domain dataclasses,
  reducing duplication between layers.
- Large ecosystem of middleware covers CORS, authentication, rate limiting,
  and other common API concerns out of the box.
- Type-checked request parameters catch invalid input before it reaches
  business logic.

**Harder:**

- Adds new dependencies to the project (`fastapi`, `uvicorn`, `pydantic`).
- Contributors unfamiliar with FastAPI must learn its patterns (dependency
  injection, Pydantic models, lifespan events).
- Pydantic v2 is the current default; care must be taken to use v2 patterns
  consistently and avoid deprecated v1 APIs.
- Running an ASGI server introduces deployment considerations (process
  management, reverse proxy, health checks) that the CLI-only tool did not
  have.

## Alternatives considered

- **Flask** -- the most widely used Python micro-framework. Mature, simple,
  and well-documented. However, Flask is sync-first; async support was added
  in 2.0 but is not idiomatic. Integrating with our async providers would
  require `asyncio.run()` wrappers or running under an async adapter like
  `asgiref`. Flask also lacks built-in OpenAPI generation, requiring
  extensions like `flask-smorest` or `apispec`.

- **Django REST Framework (DRF)** -- a full-featured, batteries-included
  framework for building APIs. DRF excels at CRUD-heavy applications with
  complex permissions and serialization. However, it brings the full Django
  ORM and middleware stack, which is heavy for a project already using
  SQLAlchemy. Django's async story is improving but still incomplete
  (async views, but sync ORM). The additional boilerplate and learning curve
  are not justified for this project's scope.

- **Litestar** -- a modern async Python framework (successor to Starlite)
  with OpenAPI generation, dependency injection, and SQLAlchemy integration.
  Architecturally similar to FastAPI and technically capable. However,
  Litestar has a significantly smaller community, fewer tutorials, and less
  third-party middleware. Choosing it would trade ecosystem maturity for
  marginal technical differences.

- **No framework (raw ASGI)** -- building directly on the ASGI spec using
  Starlette or a bare ASGI application. This maximizes control but requires
  implementing routing, validation, serialization, error handling, and
  documentation generation manually. The boilerplate cost is not justified
  when FastAPI provides all of this out of the box.
