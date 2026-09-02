# Gap Analysis — Full Journey Review (2026-09-02)

## Executive Summary

Comprehensive review of 21 pages, 78 API endpoints, 7 user journeys, and the entire data layer.
Analysis identified **34 actionable gaps** across 4 categories, consolidated into **8 feature proposals**.

---

## 1. NAVIGATION & ORIENTATION GAPS

### 1.1 Inconsistent Breadcrumbs (5 of 11 secondary pages)
| Page | Has Breadcrumb | Has Back |
|------|:-:|:-:|
| `/collection/:id` | Y | Y |
| `/cards/:id` | Y | Y |
| `/decks/:id` | Y | Y |
| `/market` | N | N |
| `/market/trending` | N | N |
| `/market/movers` | N | N |
| `/banlist` | N | N |
| `/banlist/history` | N | N |
| `/admin` | N | N |
| `/settings` | N | N |
| `/evaluations` | N | N |

### 1.2 Missing Cross-Links
- Market page has no link to Trending (separate pages, no "View All")
- Trending cards don't indicate ownership (no collection badge)
- Collection detail has no link to trending movement for same card
- Card detail (explore) has no "Add to Collection" CTA
- Non-owned deck cards are dead ends (no action available)

### 1.3 Dead-End Pages
- `/marketplace/my-trades` — only reachable from Marketplace (no nav link)
- After bulk refresh: no summary of what changed (progress bar disappears)
- After CSV import: no preview of imported cards

---

## 2. USER JOURNEY GAPS

### 2.1 New User Onboarding (Critical)
- No first-time guidance after registration
- Empty collection state has no import prompt or tutorial
- Dashboard empty states show text but no actionable CTAs
- No "Welcome" message or setup wizard

### 2.2 Credit/Token Economy Transparency
- Cost NOT visible before clicking action button (only in confirmation modal)
- Insufficient credits modal has no recovery CTA (no "claim bonus" link, no "how to earn")
- Scheduled scan failures due to credits: no notification to user
- No feedback after successful bonus claim (silent balance update)

| Action | Cost Visible Before Click | Cost in Modal | Feedback After |
|--------|:-:|:-:|:-:|
| Per-card refresh | N | Y | Toast 3s |
| Bulk refresh | N | Y | Progress bar |
| Manual price edit | Free | N/A | Badge |
| Scheduled scan | N | N/A | None |
| Web search | N | Toast | Toast + cooldown |

### 2.3 Scan-to-Insight Flow Incomplete
- No "scan complete" toast or summary card
- No drill-down to "which cards got prices" vs "which failed"
- SyncSummary tracks `not_found` and `rate_limited` but not exposed to user
- No pause/resume on bulk refresh (only cancel)

### 2.4 Deck Cards Dead Ends
- Non-owned deck cards: dimmed but no "Add to Collection" button
- No "Add Missing Cards" batch CTA on deck detail
- No path from deck view to import flow for missing cards

### 2.5 Empty/Error/Loading State Inconsistency
- Some pages: rich empty states with CTAs (DeckList, Collection)
- Others: generic text (Evaluations, Admin sections)
- No error boundaries per section (one failing section takes down page)
- Missing loading indicators on secondary sections (MetricsPanel, PriceChart)

---

## 3. API & FEATURE GAPS

### 3.1 Orphan Endpoints (backend exists, no frontend consumer)
| Endpoint | Reason |
|----------|--------|
| `PATCH /auth/me/preferences` | Settings page doesn't call it for currency/language |
| `GET /marketplace/listings/{share_code}` | Detail page not built |
| `GET /exchange-rates/history` | No chart in frontend |
| `POST /collect/backfill`, `POST /collect/update` | API-key only, not in admin |
| `GET /db/backup`, `POST /db/restore` | No admin UI |

### 3.2 CLI-Only Operations Missing from Admin
- `backfill`, `update`, `retry-failed` (data pipeline)
- `db-backup`, `db-cleanup`, `db-reset` (database management)
- `update-exchange-rate` (currency)
- `liga-sweep` (bulk Liga refresh)
- `error-cleanup` (maintenance)

### 3.3 Missing Features
- No "Forgot Password" flow (users must contact admin)
- No OpenAPI/Swagger docs exposed
- No password strength validation on register
- OAuth stubs return 501
- No admin user search/filter
- No audit log for credit adjustments

### 3.4 Pagination Inconsistency
- Collection: offset-based
- Cards (explore): cursor-based
- Banlist/Admin/Scans: offset-limit
- No uniform strategy

---

## 4. DATA INTEGRITY GAPS

### 4.1 No Foreign Key Constraints (HIGH)
- All `card_id` references are plain integers with no FK constraint
- Database cannot enforce referential integrity
- Orphan records possible on any delete
- 417 lines of manual cleanup code (`cleanup.py`) as workaround

### 4.2 Collection Deletion Doesn't Cascade (MEDIUM)
- Deleting `UserCollectionRow` leaves orphaned:
  - `DeckCardRow` (card_id still points to deleted card)
  - `PortfolioSnapshotRow` (includes deleted card's value)
  - `EvaluationEntryRow` (may reference deleted card)

### 4.3 Exchange Rate Fallback Returns None (MEDIUM)
- `CurrencyConverter.convert()` returns None if no rate exists
- No fallback to closest historical rate
- Frontend handles by falling back to BRL, but API consumers get null

### 4.4 Multi-Step Pipeline Lacks Atomicity (MEDIUM)
- Sync collection: search > match > link > store prices = 4 separate transactions
- Failure at step 3 leaves orphaned CardRow from step 2
- Retry logic exists but doesn't rollback created data

### 4.5 N+1 Query in Orphan Linking (LOW)
- `link_orphan_source_cards()` runs N individual queries for N orphans
- Should use a single JOIN query

### 4.6 Missing Composite Indexes (LOW)
- `(user_id, card_id)` on user_collection
- `(deck_id, card_id)` on deck_cards
- `observed_at` alone on price_observations

### 4.7 Conflicting Provider Prices Silent (MEDIUM)
- Liga and MYP may report different prices same day
- SOURCE_PRIORITY picks winner silently
- No user visibility into data conflict

---

## 5. FEATURE PROPOSALS (Prioritized)

### F95 — Onboarding & Empty States (P0)
- Welcome message after first login
- Empty collection: import wizard CTA
- Dashboard empty: actionable suggestions
- Consistent empty state component across all pages

### F96 — Credit Transparency & Recovery (P0)
- Show cost inline before click (badge on buttons)
- Insufficient credits modal: "Claim Bonus" link + "How to earn" info
- Bonus claim feedback (toast)
- Scheduled scan failure notification

### F97 — Navigation & Cross-Links (P1)
- Breadcrumbs on all secondary pages
- Market <> Trending cross-links
- Collection ownership badge on trending/market cards
- "Add to Collection" CTA on card detail + deck non-owned cards
- "Add Missing Cards" batch button on deck view

### F98 — Scan Results & Feedback (P1)
- Scan completion summary (cards processed, prices found, failures, rate-limited)
- Per-card error details (expandable)
- Expose SyncSummary fields in frontend
- Delete action undo toast (5s window)

### F99 — Data Integrity Hardening (P1)
- Add FK constraints with CASCADE on card_id references
- Atomic transaction wrapping for sync pipeline
- Exchange rate fallback to closest historical rate
- Composite indexes on hot paths
- Fix N+1 in orphan linking

### F100 — Admin Console Operations (P2)
- Trigger backfill/update/liga-sweep from admin panel
- DB backup download button
- Exchange rate manual refresh
- User search/filter in admin table
- Credit adjustment audit log

### F101 — Marketplace Completion (P2)
- Share code detail page (`/marketplace/listings/{code}`)
- "Copy share code" button
- Direct nav link to My Trades

### F102 — Auth Hardening (P3)
- Forgot password flow (email-based reset)
- Password strength validation
- OpenAPI/Swagger docs endpoint
- Standardized error codes
