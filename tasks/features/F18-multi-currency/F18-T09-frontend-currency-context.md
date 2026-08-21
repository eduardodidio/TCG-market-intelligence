# F18-T09: Currency Context + Toggle Component

- **Wave:** 3
- **Status:** done
- **Depends on:** F18-T07, F18-T08
- **Description:**
  Create the frontend infrastructure for currency selection:

  1. **`CurrencyContext`** (`frontend/src/contexts/CurrencyContext.tsx`):
     - React context providing `{ currency, setCurrency }`.
     - Reads initial value from `localStorage` key `tcg_currency`
       (default: `"BRL"`).
     - Persists changes to `localStorage` on every update.
     - Wraps the entire app in `App.tsx`.

  2. **`CurrencyToggle`** (`frontend/src/components/CurrencyToggle.tsx`):
     - A two-button toggle (BRL | USD) styled to match the existing
       dark theme (slate/cyan palette).
     - Uses `useCurrency()` hook from the context.
     - Active currency highlighted with `bg-cyan-600`, inactive with
       `bg-slate-700`.
     - Accessible: proper ARIA labels, keyboard navigation.

  3. **`useCurrency()` hook** (`frontend/src/hooks/useCurrency.ts`):
     - Convenience hook wrapping `useContext(CurrencyContext)`.

  4. **Layout integration**:
     - Add `CurrencyToggle` to the header bar in `Layout.tsx`,
       positioned next to existing nav items.

  5. **Format utility update** (`frontend/src/utils/format.ts`):
     - Add `formatCurrency(value, currency)` that formats as BRL
       (`R$ 1.234,56`) or USD (`$ 1,234.56`) based on the currency
       parameter.
     - Keep `formatBRL()` as a backward-compatible alias.

- **Acceptance Criteria:**
  - [ ] CurrencyContext provides currency and setCurrency
  - [ ] Initial value read from localStorage, defaults to BRL
  - [ ] setCurrency persists to localStorage
  - [ ] CurrencyToggle renders BRL/USD buttons with correct styling
  - [ ] Toggle appears in Layout header on all pages
  - [ ] `formatCurrency("BRL", 100)` returns `R$ 100,00`
  - [ ] `formatCurrency("USD", 100)` returns `$ 100.00`
  - [ ] `formatCurrency` handles null/undefined (returns "--")
  - [ ] Unit tests for context, toggle, and format function
  - [ ] Vitest tests: 10+ new test cases

- **Files to touch:**
  - `frontend/src/contexts/CurrencyContext.tsx` (new)
  - `frontend/src/hooks/useCurrency.ts` (new)
  - `frontend/src/components/CurrencyToggle.tsx` (new)
  - `frontend/src/utils/format.ts` (modify)
  - `frontend/src/components/Layout.tsx` (modify)
  - `frontend/src/App.tsx` (wrap with provider)
  - `frontend/src/types/api.ts` (add currency fields)
  - `frontend/tests/components/CurrencyToggle.test.tsx` (new)
  - `frontend/tests/utils/format.test.ts` (extend)
  - `frontend/tests/contexts/CurrencyContext.test.tsx` (new)
