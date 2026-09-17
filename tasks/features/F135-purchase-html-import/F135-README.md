# F135 -- Purchase HTML Import

**Status:** planned
**Branch:** homol

## Problem Statement

The user has 25 saved HTML files from purchase orders on two Brazilian MTG
stores (Nerdz Cards and Liga Magic via the "Meus Pedidos" page). These files
contain the actual purchase prices paid for each card, but there is no way to
bulk-import this data into the `user_collection.acquisition_price` and
`acquired_at` fields. Currently the only option is manual per-card editing via
`PATCH /api/v1/collection/{entry_id}`, which is impractical for hundreds of
cards.

## Goal

Parse the HTML files, extract card purchase data (name, set, quantity, unit
price, order date), match each parsed card to an existing `user_collection`
entry, and bulk-update `acquisition_price` + `acquired_at`.

## HTML Format Analysis

### Nerdz Cards (24 individual order pages)

Each file is a single order page (`Pedido #XXXXXXX _ Nerdz Cards.html`).

**Key selectors:**
- **Order date**: `div.panel-body.panel-order--number > div > i` (text like
  `25/08/2025 17:01`)
- **Order number**: `h3` inside `div.panel-order--number` (text like
  `#9117259`)
- **Card items**: `article.panel-order--content.layout-standard` (each card
  is one article)
  - **Quantity**: `span.bold` before the link (text like `4x`)
  - **Card name PT/EN**: `a.link-produto` contains `span.bold` (PT name)
    followed by ` / English Name`. Some cards are EN-only (e.g. `Belladonna
    Took` with no PT). The `font.input-infoaux` contains set code + collector
    number: `(Codigo: AFR139)` or `(Codigo: PRMID390)`.
  - **Unit price**: sibling `div.col-xs-6.col-sm-3 > p` with text like
    `R$ 9,90 (unid.)`
  - **Subtotal**: next sibling with `R$ 39,60 (subtotal)`
  - **Set name**: `img.icon-edicao` `title` attribute (e.g.
    `Adventures in the Forgotten Realms`)
  - **Set code**: extracted from `(Codigo: AFR139)` -- the letters before the
    bold number, or from the edition icon filename (e.g. `AFR_C.gif`)
  - **Collector number**: the bold number inside `(Codigo: AFR<b>139</b>)`
  - **Language**: `img[alt]` in the language div (`Portugues`, `Ingles`) with
    label `PT`/`EN`
  - **Quality**: `div.icon_qualid` `title` attribute (e.g.
    `Praticamente Nova (NM)`)
  - **Extras**: `span.extras-pedido` (e.g. `Promo`, `Foil`)

**Non-card items** (sealed products like boosters, kits): These appear in the
same structure but have no `icon-edicao` and no `(Codigo: ...)` pattern.
The parser must skip these.

### Liga Magic ("Meus Pedidos" aggregate page, 1 file)

Single file containing ALL orders. Each order is expanded inline with card
details already loaded for some orders.

**Key selectors:**
- **Order groups**: `div.boxshadow.conteudo.box-interna` -- one per order
- **Order date**: `font.titledate` (text like
  `(30 dias atras - 18/08/2026 22:01)`)
- **Order number**: `font.titleorder` (text like `#11722459` or `#MP1247013`)
- **Store name**: `label.title` inside `div.venda-store`
- **Card items** (when expanded): `div#meucarrinho > div.itens > div.row`
  - **Card name**: `p.cardtitle a` (text like
    `Tempestade Dragonica / Dragon Tempest` or just `Belladonna Took`)
  - **Set code**: `td[editioncard] a` href contains `ed=DTK` or `ed=HOB`;
    also `img.icon-edicao` filename like `DTK_R.gif`
  - **Set name**: `td.label.hidden-md a` text or `img` `title` attr
  - **Language**: `td[languagecard] img` `alt` attribute (`Ingles`,
    `Portugues`) with label `EN`/`PT`
  - **Quality**: `td[qualitycard]` text (e.g. `NM`)
  - **Quantity**: `div.item-estoque` (text like `1 unid.`)
  - **Unit price**: `div.item-subpreco` (text like `R$ 9,75`)
  - **Total**: `div.preco-total.item-total` (text like `R$ 9,75`)

**Note**: Not all orders in the Liga file have their items expanded. Orders
that show "Exibir Detalhes" / "Visualizar Itens" with a loading spinner have
NO card data in the HTML -- they require JavaScript execution. The parser
should only extract data from orders that have card items already rendered.

## Acceptance Criteria

1. HTML parser correctly extracts card data from both Nerdz Cards and Liga
   Magic HTML formats
2. Sealed products (kits, boosters, bundles) are automatically skipped
3. Card matcher finds the corresponding `user_collection` entry by normalized
   name + set code, with confidence scoring
4. Preview endpoint lets the user see all matches before applying
5. Apply endpoint bulk-updates `acquisition_price` and `acquired_at`
6. Frontend provides drag-and-drop file upload, preview table with confidence
   indicators, and per-card edit/skip controls
7. All 25 HTML files are processed to populate acquisition prices

## Wave Strategy

### Wave 0 -- Backend Services (2 tasks, parallel)

Both are independent pure-logic modules with no API dependency.

| Task | Description |
|------|-------------|
| T01  | HTML parser service -- parse Nerdz + Liga formats |
| T02  | Card matching service -- match parsed cards to user_collection |

### Wave 1 -- API + Frontend (2 tasks, parallel with each other, depend on W0)

| Task | Description |
|------|-------------|
| T03  | Backend endpoints -- import-purchases + apply-purchases |
| T04  | Frontend import UI -- file upload, preview table, apply flow |

### Wave 2 -- Bulk Processing (1 task, depends on W1)

| Task | Description |
|------|-------------|
| T05  | Process all 25 HTML files via CLI or frontend |

## Key Files

### New files
- `src/services/purchase_parser.py` -- HTML parsing logic
- `src/services/purchase_matcher.py` -- card matching logic
- `src/api/routers/purchases.py` -- import endpoints (or extend collection.py)
- `frontend/src/pages/ImportPurchasesPage.tsx` (or modal component)
- `frontend/src/api/purchases.ts` -- API client
- `tests/services/test_purchase_parser.py`
- `tests/services/test_purchase_matcher.py`
- `tests/api/test_import_purchases.py`

### Modified files
- `src/api/app.py` -- register new router
- `frontend/src/App.tsx` -- add route (if page, not modal)
- `frontend/src/components/Layout.tsx` -- add nav item (if page)

## Constraints

- BeautifulSoup4 already in requirements -- no new dependency needed
- `unidecode` may be needed for accent-insensitive matching -- confirm if
  already installed or request user approval
- Liga Magic "Meus Pedidos" file is 11,006 lines -- parser must handle large
  files efficiently
- Some orders in the Liga file have no card data (not expanded) -- skip them
- Sealed products must be filtered out (no set code / collector number)
- User must preview and confirm before any data is written
- `acquisition_price` and `acquired_at` may already have values -- the
  import should NOT overwrite existing values unless the user explicitly
  chooses to
