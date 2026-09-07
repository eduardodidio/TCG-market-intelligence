# TCG Market Intelligence — UX Roadmap (F104–F110)

**Source:** Competitive scan of 40+ TCG sites/apps (2026-09-06)
**Scope:** 7 features, 38 tasks, organized by priority tier
**Execution:** each feature runs independently via `/create-feature FXX`

---

## Feature Map

| Feature | Nome | Tasks | Waves | Prioridade | Deps |
|---------|------|-------|-------|------------|------|
| F104 | Quick Win UX Polish | 8 | 2 | P1 | none |
| F105 | Portfolio & Investment Tracking | 6 | 3 | P1 | none |
| F106 | Price Alerts & Watchlist | 5 | 2 | P1 | none |
| F107 | PWA & Offline Support | 4 | 2 | P2 | none |
| F108 | Dark Mode | 3 | 2 | P2 | none |
| F109 | Gamification & Engagement | 4 | 2 | P2 | F104 (set completion) |
| F110 | Social & Trade Matching | 5 | 3 | P3 | none |

**Total:** 35 tasks across 7 features

---

## F104 — Quick Win UX Polish (ALREADY PLANNED)

**Status:** planned | **Priority:** P1 | **Tasks:** 8 | **Waves:** 2
**Path:** `tasks/features/F104-quick-win-ux-polish/`

### Wave 0 (1 task)
| Task | Descricao | Esforco |
|------|-----------|---------|
| T01 | Batch Price Trends API (`GET /api/cards/price-trends?card_ids=...&days=7`) | S |

### Wave 1 (7 tasks — todas paralelas)
| Task | Descricao | Esforco |
|------|-----------|---------|
| T02 | PriceSparkline component + integracao em CardTile/CatalogCardTile/CollectionCardTile | M |
| T03 | TrendBadge (seta verde/vermelha + % change inline ao lado do preco) | S |
| T04 | CardHoverPreview (desktop hover 200ms delay + mobile long-press 500ms, portal overlay) | M |
| T05 | SetCompletionBar (barra de progresso X/Y por set na MyCollection, endpoint `/api/collection/set-completion`) | S |
| T06 | ArbitrageBadge (best price Liga vs TCG + gap %, extend CardSummary com `tcg_price`) | S |
| T07 | Skeleton loading para card images (animate-pulse overlay + fade-in transition, CardImage shared component) | S |
| T08 | Sticky filter bar (frosted glass `sticky top-0 z-10 backdrop-blur`) + useScrollRestoration hook (sessionStorage) | S |

---

## F105 — Portfolio & Investment Tracking

**Status:** planned | **Priority:** P1 | **Tasks:** 6 | **Waves:** 3

Transforma a colecao de um inventario passivo num portfolio de investimento
com preco de aquisicao, P&L por carta, e valor total ao longo do tempo.
Referencia: EchoMTG, Collectr, Rippr, PokeFolio.

### Wave 0 — Schema + Backend (2 tasks paralelas)
| Task | Descricao | Esforco | Notas |
|------|-----------|---------|-------|
| T01 | Schema: adicionar `acquisition_price` (DECIMAL, nullable) e `acquired_at` (DATE, nullable) na tabela `user_collection`. Migration com ALTER TABLE ADD COLUMN (nullable, sem rebuild). | S | Sem breaking change |
| T02 | API endpoints: `PATCH /api/collection/{id}` para atualizar acquisition_price/acquired_at. `GET /api/collection/portfolio-summary` retorna total_invested, total_current_value, total_pnl, total_pnl_pct. `GET /api/collection/portfolio-history?days=90` retorna serie temporal do valor total da colecao (aggregate de price_observations por dia). | M | |

### Wave 1 — Frontend Components (3 tasks paralelas)
| Task | Descricao | Esforco | Notas |
|------|-----------|---------|-------|
| T03 | AcquisitionPriceInput — campo inline editavel no CollectionCardTile e CollectionCardDetail para registrar preco pago. Formato moeda, validacao >0. Salva via PATCH do T02. | S | Reusa InlineEditField pattern |
| T04 | PnlBadge component — mostra ganho/perda nao realizado por carta (preco_atual - preco_aquisicao). Verde se positivo, vermelho se negativo. Formato: "+R$ 15,30 (+23.4%)". Integrar em CollectionCardTile e CollectionCardDetail. | S | |
| T05 | PortfolioDashboard section — painel no topo da MyCollection com: KPI cards (Total Investido, Valor Atual, P&L total, P&L %), grafico de linha Recharts mostrando valor da colecao ao longo do tempo (reusa PriceChart pattern). Toggle show/hide persistido em localStorage. | M | |

### Wave 2 — Export (1 task)
| Task | Descricao | Esforco | Notas |
|------|-----------|---------|-------|
| T06 | CSV Export para IR — `GET /api/collection/export-pnl?format=csv` retorna CSV com colunas: card_name, set_code, quantity, acquisition_price, acquired_at, current_price, pnl, pnl_pct. Botao "Exportar P&L" na PortfolioDashboard section. | S | Diferencial BR |

---

## F106 — Price Alerts & Watchlist

**Status:** planned | **Priority:** P1 | **Tasks:** 5 | **Waves:** 2

Watchlist com preco-alvo e notificacoes quando atingido.
Referencia: TCGPriceAlert, TCGSniper, EchoMTG, MTGGoldfish.

### Wave 0 — Backend (2 tasks paralelas)
| Task | Descricao | Esforco | Notas |
|------|-----------|---------|-------|
| T01 | Schema: nova tabela `price_alerts` (id, user_id FK, card_id FK, target_price DECIMAL, direction ENUM(below/above), is_active BOOL, triggered_at DATETIME nullable, created_at). CRUD endpoints: `POST /api/alerts`, `GET /api/alerts`, `DELETE /api/alerts/{id}`. Max 50 alerts ativos por usuario (free tier). | M | |
| T02 | Alert checker service — funcao que roda no scan hook (apos price update): compara novo preco com target_price de todos os alerts ativos para aquele card_id. Quando triggered: marca `triggered_at`, seta `is_active=false`. Registra em `alert_notifications` table (id, alert_id FK, card_name, old_price, new_price, notified_at). | M | Reusa scan_hooks pattern |

### Wave 1 — Frontend (3 tasks paralelas)
| Task | Descricao | Esforco | Notas |
|------|-----------|---------|-------|
| T03 | AlertBell icon no header (Layout.tsx) — badge com contagem de alertas triggered nao lidos. Dropdown mostra ultimos 10 alertas triggered com card name, preco antigo → preco novo, timestamp. "Mark all read" limpa a contagem. Poll a cada 60s ou use existing refetch patterns. | M | |
| T04 | SetAlertModal — modal ativado por botao "Set Alert" no CardDetail e CollectionCardDetail. Campos: target_price (input numerico), direction (below/above toggle). Feedback: "Alert set! We'll notify you when price goes {below/above} {target}." Lista de alertas ativos para esta carta abaixo do form. | S | |
| T05 | AlertsPage — nova pagina `/alerts` listando todos os alertas do usuario. Tabs: Active / Triggered. Cada row: card name, target price, direction, status, created_at. Acoes: delete (active), dismiss (triggered). Link no sidebar nav (requer auth). | M | |

---

## F107 — PWA & Offline Support

**Status:** planned | **Priority:** P2 | **Tasks:** 4 | **Waves:** 2

Instalar como app no celular, funcionar offline para browsing da colecao.
O catalogo offline (F103) ja existe — falta o service worker.
Referencia: Droidex (open-source PWA), TCG Vision, Eyevo.

### Wave 0 — PWA Infrastructure (2 tasks paralelas)
| Task | Descricao | Esforco | Notas |
|------|-----------|---------|-------|
| T01 | manifest.json + icons — criar `public/manifest.json` com name, short_name, icons (192/512px), theme_color (#0f172a slate-900), background_color, display: standalone, start_url: "/". Gerar icones PNG a partir do logo existente. Adicionar `<link rel="manifest">` no index.html. | S | |
| T02 | Service Worker (vite-plugin-pwa) — instalar `vite-plugin-pwa` (ou workbox). Configurar strategy: NetworkFirst para API calls, CacheFirst para static assets (JS/CSS/images). Precache app shell. Register SW no main.tsx. Banner "Update available" quando nova versao detectada. | M | |

### Wave 1 — Offline Data (2 tasks paralelas)
| Task | Descricao | Esforco | Notas |
|------|-----------|---------|-------|
| T03 | Offline collection — salvar dados da colecao do usuario em IndexedDB (via idb-keyval ou Dexie). Sync strategy: write-through (save to IDB on every API response). Quando offline: ler de IDB. Banner "Offline mode — data may be outdated" no topo. Hook `useOfflineCollection`. | M | |
| T04 | Install prompt — detectar `beforeinstallprompt` event. Mostrar banner discreto "Install TEDHC Market" com botao no mobile (first visit + logged in). Dismiss persiste em localStorage por 30 dias. Nao mostrar se ja instalado (display-mode: standalone media query). | S | |

---

## F108 — Dark Mode (System-Following + Toggle)

**Status:** planned | **Priority:** P2 | **Tasks:** 3 | **Waves:** 2

O app ja e dark by default (slate-900 background). Este feature adiciona
um toggle light/dark/system e ajusta os poucos componentes que precisam.
Referencia: Moxfield (user-selectable), padrao 2026.

### Wave 0 — Theme Infrastructure (1 task)
| Task | Descricao | Esforco | Notas |
|------|-----------|---------|-------|
| T01 | ThemeProvider + useTheme hook — context provider que gerencia theme (dark/light/system). Persiste em localStorage. Quando "system": usa `prefers-color-scheme` media query. Aplica classe `dark` no `<html>` element. Configurar Tailwind `darkMode: 'class'`. | M | |

### Wave 1 — UI Adjustments (2 tasks paralelas)
| Task | Descricao | Esforco | Notas |
|------|-----------|---------|-------|
| T02 | Light theme CSS — revisar todos os componentes e adicionar variantes `dark:` onde necessario. O app ja e dark-first, entao o trabalho e criar as variantes light: backgrounds (white/gray-50), text (gray-900), borders (gray-200), cards (white shadow). Foco nos componentes mais usados: Layout, CardTile, KpiCard, PriceChart, Breadcrumb, SearchBar, FilterChips. | M | |
| T03 | ThemeToggle component — selector no sidebar (abaixo do CurrencyToggle): icones sol/lua/monitor para light/dark/system. Integrar no Layout.tsx. | S | |

---

## F109 — Gamification & Engagement

**Status:** planned | **Priority:** P2 | **Tasks:** 4 | **Waves:** 2
**Depends on:** F104-T05 (set completion data)

Achievements, badges de colecao, e milestones de onboarding para
aumentar retencao. Estudo mostra 64% mais retencao com achievements
no primeiro dia. Referencia: Trophy.so, Collectr.

### Wave 0 — Backend (1 task)
| Task | Descricao | Esforco | Notas |
|------|-----------|---------|-------|
| T01 | Schema + service: tabela `achievements` (id, user_id FK, achievement_key VARCHAR, unlocked_at DATETIME). Achievement definitions em config (nao DB): { key, title_i18n, description_i18n, icon, condition }. Service `check_achievements(user_id)` roda apos acoes (add card, complete scan, etc). API: `GET /api/achievements` (lista com unlocked status). | M | Definicoes hardcoded, nao DB |

### Wave 1 — Frontend (3 tasks paralelas)
| Task | Descricao | Esforco | Notas |
|------|-----------|---------|-------|
| T02 | AchievementToast — notificacao popup quando achievement desbloqueado. Slide-in do topo, auto-dismiss 5s, icone + titulo + descricao. Reusa UndoToast pattern visual. Hook `useAchievementNotifier` que faz poll ou recebe do response header. | S | |
| T03 | AchievementsPage — nova pagina `/achievements` com grid de todos os achievements. Unlocked: colorido com data. Locked: grayscale com "?" ou silhouette. Progress bar no topo "X/Y achievements unlocked". Link no sidebar (requer auth). | M | |
| T04 | Achievement definitions (initial set) — definir 10-15 achievements iniciais: "First Card" (add 1 card), "Deck Builder" (create 1 deck), "Scanner" (first scan), "Collector 10/50/100/500" (total cards), "Set Master" (complete 1 set), "Price Watcher" (set 1 alert, depends F106), "Treasure Hunter" (claim bonus 5x), "Early Adopter" (account created before launch date). i18n keys pt/en. | S | |

---

## F110 — Social & Trade Matching

**Status:** planned | **Priority:** P3 | **Tasks:** 5 | **Waves:** 3

Wishlist, deteccao de duplicatas, e matching automatico de trades
entre usuarios. Referencia: Deckbox, MTG Burrow, PokeHub.

### Wave 0 — Wishlist Backend (2 tasks paralelas)
| Task | Descricao | Esforco | Notas |
|------|-----------|---------|-------|
| T01 | Schema: tabela `wishlists` (id, user_id FK, card_id FK, max_price DECIMAL nullable, any_version BOOL default true, created_at). CRUD: `POST /api/wishlist`, `GET /api/wishlist`, `DELETE /api/wishlist/{id}`. Max 200 items por usuario. Constraint unique (user_id, card_id). | S | |
| T02 | Duplicates detection — `GET /api/collection/duplicates` retorna cartas onde quantity > needed (needed = sum across all decks + 1 for collection). Marca como "available for trade". Endpoint retorna lista com card_id, card_name, total_owned, total_needed, surplus. | M | |

### Wave 1 — Trade Matching (1 task)
| Task | Descricao | Esforco | Notas |
|------|-----------|---------|-------|
| T03 | Trade matcher service — `GET /api/trades/matches` cruza wishlists de todos os usuarios com duplicatas/tradelist de todos os outros. Retorna array de matches: { other_user, they_have (cards you want), you_have (cards they want), match_score }. Ordered by match_score DESC. Roda como query sob demanda (nao background job). Requer ambos os usuarios terem sharing habilitado (F69). | H | Query complexa mas read-only |

### Wave 2 — Frontend (2 tasks paralelas)
| Task | Descricao | Esforco | Notas |
|------|-----------|---------|-------|
| T04 | WishlistPage — nova pagina `/wishlist`. Add via botao "Add to Wishlist" no CardDetail. Grid de cartas desejadas com preco-alvo opcional. Remove individual ou bulk. Badge no sidebar com contagem. | M | |
| T05 | TradeMatchesPage — nova pagina `/trades/matches`. Lista de usuarios com matches. Expandir cada match mostra as cartas que cada lado tem. Botao "Contact" (link para perfil ou marketplace existente F69). Empty state quando nao ha matches. | M | |

---

## Ordem de Execucao Recomendada

```
Fase 1 (P1 — impacto imediato):
  F104  Quick Win UX Polish          ← rodar primeiro, tudo paralelo
  F105  Portfolio & Investment        ← paralelo com F104
  F106  Price Alerts & Watchlist      ← paralelo com F104/F105

Fase 2 (P2 — diferencial):
  F107  PWA & Offline                ← apos Fase 1
  F108  Dark Mode                    ← paralelo com F107
  F109  Gamification                 ← apos F104 (depende set completion)

Fase 3 (P3 — social):
  F110  Social & Trade Matching      ← apos Fase 2
```

### Execucao paralela maxima por fase

```
Fase 1:  F104 + F105 + F106 (3 features simultaneas)
Fase 2:  F107 + F108 (2 features simultaneas), depois F109
Fase 3:  F110 (1 feature)
```

---

## Metricas de Sucesso

| Metrica | Baseline | Target |
|---------|----------|--------|
| Tempo medio na pagina | — | +30% apos F104 |
| Users com acquisition_price preenchido | 0% | 20% em 30 dias (F105) |
| Alerts criados por usuario | 0 | 3+ em 30 dias (F106) |
| PWA installs | 0 | 50+ em 60 dias (F107) |
| Achievements unlocked / user | 0 | 5+ em 30 dias (F109) |
| Trade matches aceitos | 0 | 10+ em 60 dias (F110) |

---

## Resumo Tecnico

| Aspecto | Detalhes |
|---------|----------|
| Novas tabelas | 3 (price_alerts, alert_notifications, achievements, wishlists) |
| Novos endpoints | ~15 |
| Novos componentes React | ~18 |
| Novos hooks | ~8 |
| Novas paginas | 4 (/alerts, /achievements, /wishlist, /trades/matches) |
| Schema changes | 2 cols em user_collection (acquisition_price, acquired_at) |
| Deps novas | vite-plugin-pwa (F107), idb-keyval ou dexie (F107) |
| Backend changes | F104-T01, F105-T01/T02, F106-T01/T02, F107 (nenhum), F108 (nenhum), F109-T01, F110-T01/T02/T03 |
