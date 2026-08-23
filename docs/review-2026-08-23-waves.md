# Review Waves — Execution Commands (2026-08-23)

Reference: `docs/review-2026-08-23.md`

After each wave, commit and verify before proceeding to the next.

---

## Wave A — Critical Fixes

```
Implement ALL 5 critical fixes from docs/review-2026-08-23.md TIER 1:

T1-01. Add 404 catch-all route in frontend App.tsx — create a NotFoundPage component, add <Route path="*"> at end of Routes.

T1-02. JWT secret: make TCG_JWT_SECRET required. In src/auth/jwt.py, fail fast on startup if env var is missing (raise RuntimeError). Remove random fallback generation. Update start.sh to set a default dev secret.

T1-03. Collection import endpoint (src/api/routers/collection.py ~line 832): remove hardcoded CSV path. Accept multipart file upload (UploadFile) instead.

T1-04. Remove default user_id="eduardo" from src/collection/importer.py:17. Make user_id a required parameter (no default value).

T1-05. Wrap collection import delete+insert in a proper transaction in src/collection/importer.py:71. Only commit after all entries inserted successfully. On any error, rollback so user keeps their existing collection.

Write tests for all changes. Run full test suite (backend + frontend) before finishing.
```

---

## Wave B — Reliability & Security

```
Implement the 10 HIGH severity fixes from docs/review-2026-08-23.md TIER 2:

T2-01. Scan progress persistence: store scan progress in localStorage in useCollectionRefresh hook. On page mount, check for active scan and resume polling /scans/{id}.

T2-02. Card refresh failure: when MYP fetch fails on collection card detail, show "Last known price" with timestamp + offer ManualPriceInput inline instead of just an error.

T2-03. Seed user password: read from TCG_SEED_PASSWORD env var in src/cli/main.py seed-users command. Remove hardcoded "mudar@123". If env var not set, generate random password and print it.

T2-04. CORS: in src/api/app.py, read allowed origins from TCG_CORS_ORIGINS env var (comma-separated). Default to "http://localhost:5173" for dev. Remove allow_origins=["*"].

T2-05. Null check: in src/api/routers/collection.py after repo.link_collection_entry(), add null check on reloaded entry. Return HTTPException(422) if entry or card_id is None.

T2-06. Orphan deck cards: in DeckView page, catch missing card data gracefully. Show "Card not found" placeholder tile with card name instead of crashing.

T2-07. Schedule pause visibility: show pause reason and "paused" badge on Schedules page when a schedule has status=paused. Add i18n key for pause reason.

T2-08. Back button: add a back navigation button (arrow + "Back") at the top of CardDetail, CollectionCardDetail, and DeckView pages. Use useNavigate(-1).

T2-09. Fix DeckCardTile type: add name_pt to DeckCard type in frontend/src/types/ (or wherever DeckCard is defined). Remove the `as any` cast.

T2-10. Add .catch() to fetchSets() in frontend/src/pages/Cards.tsx. Set error state on failure and show error banner.

Write tests for all changes. Run full test suite before finishing.
```

---

## Wave C — UX Consistency

```
Implement these 10 selected MEDIUM fixes from docs/review-2026-08-23.md TIER 3:

T3-01. Settings page: create /settings route with sections for Account (email, display name), Preferences (currency, language), and a placeholder for future API Keys and Data Export.

T3-02. Freshness indicator on collection page: add FreshnessIndicator component to collection page header showing last scan date.

T3-03. Breadcrumbs: add a simple Breadcrumb component. Use on CollectionCardDetail (Collection > Card Name), DeckView (Decks > Deck Name), CardDetail (Explore > Card Name).

T3-05. Dashboard trending "View All" link: add "View all" link below TrendingSection on dashboard that navigates to /market/trending.

T3-07. Deck import format help: add format example/spec text in DeckImportModal showing expected format (e.g., "1 Lightning Bolt" per line).

T3-09. Import summary: after CSV collection import completes, show a summary modal with counts (added, skipped, failed, canonized).

T3-12. Filter persistence on Explore Cards: persist search/sort/filter params in URL search params (like collection page already does).

T3-16. Decimal rounding: in src/api/routers/collection.py:541, add explicit rounding=ROUND_HALF_UP to .quantize() call.

T3-17. Database URL utility: create src/config.py with get_db_url() function. Replace all ~20 occurrences of os.environ.get("TCG_DATABASE_URL", ...) across the codebase.

T3-19. i18n gaps: replace hardcoded strings in CollectionCardDetail.tsx:171,176 with existing translation keys.

Write tests for new components. Run full test suite before finishing.
```

---

## Prioridade 3 — Backlog (requer brainstorm antes de executar)

> **Status:** Nenhum item abaixo deve ser executado sem brainstorm prévio.
> Use `/brainstorm` para explorar cada tema antes de planejar.

### Wave D — Missing Features

```
D-01. Watchlist / Price Alerts
- New model: WatchlistEntry (user_id, card_id, target_price, direction, active)
- CRUD API endpoints
- Check on scan completion (ScanHookRegistry)
- Frontend: watchlist page, "Watch" button on card detail, alert badge

D-02. Data Export
- GET /collection/export?format=csv (collection CSV download)
- GET /collection/{id}/history/export?format=csv (price history CSV)
- GET /decks/{id}/export?format=txt (deck list export)
- Frontend: export buttons on collection, card detail, deck view

D-03. Alternative Price Sources (F21 — deferred)
- Scryfall prices API integration
- TCG Player API integration (requires API key)
- Price source selector per card
- Fallback chain: MYP -> Scryfall -> TCG Player

D-04. Card Comparison Tool
- /compare route accepting 2-4 card IDs via query params
- Side-by-side price charts, stats, legality
- "Compare" button on card tiles (checkbox select mode)

D-05. Bulk Operations
- Multi-select mode on collection page (checkboxes)
- Bulk delete, bulk export, bulk refresh selected
- Select all / deselect all
```

### Ideias Futuras — Brainstorm

```
I-01. Guia de Investimento em Cards
- Ensino de investimento em cards de Magic
- Mostrar riscos, retornos e mecânicas para rendimentos
- Conteúdo focado na plataforma (educacional, não consultoria)
- Filtros por ano de tiragem do card (cartas antigas que ainda são boas se valorizam?)

I-02. Sistema de Trocas, Aluguéis e Comodato
- Trocas e aluguéis via lojas parceiras e pessoas de confiança
- Plataforma ganha pelas transações (taxa/comissão)
- Facilidade de leva-e-traz via Correios (busca em casa)
- Aluguel de decks para torneios ("faça seus cards renderem")
- Contratos a comodato para deixar nas lojas

I-03. Sistemas de Pagamento
- Pesquisar opções de gateway/pagamento integrado
- Definir modelo de cobrança (taxa por transação, assinatura, freemium)

I-04. Propaganda de Proxys
- Seção "quer esta mega carta aqui?" com proxys de alta qualidade
- Modelo de monetização (parceria com fornecedores de proxy)

I-05. Orgulho Gaúcho — Slogan + Benefícios
- Slogan gaúcho para a plataforma
- 5% de desconto em taxas para gaúchos residentes no Sul
- Verificação por DDD do celular + endereço
- Se não for DDD nacional: "tá e aí?" + perguntas gaúchas de verificação
```
