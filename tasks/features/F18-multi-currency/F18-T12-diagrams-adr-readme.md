# F18-T12: Diagrams, ADR, README Update

- **Wave:** 4
- **Status:** done
- **Depends on:** F18-T08, F18-T10
- **Description:**
  Documentation deliverables required by project conventions:

  1. **Architecture diagram** (`docs/diagrams/F18-architecture.mmd`):
     Mermaid diagram showing the currency conversion data flow:
     BCB API -> BCB Client -> Repository -> ExchangeRateRow ->
     CurrencyConverter -> API endpoints -> Frontend.

  2. **User journey diagram** (`docs/diagrams/F18-journey.mmd`):
     BPMN-style Mermaid diagram showing:
     - User opens page -> frontend reads localStorage currency ->
       API call with ?currency param -> backend converts prices ->
       response displayed in selected currency.
     - User toggles currency -> localStorage updated -> API re-fetched ->
       prices re-rendered.

  3. **ADR** (`docs/adr/NNNN-multi-currency-read-time-conversion.md`):
     Document the decision to use read-time conversion instead of
     storing duplicate prices. Include context, decision, consequences.

  4. **README.md update**:
     Add a section describing multi-currency support: how to set up
     exchange rate fetching (cron), how to backfill historical rates,
     and how users toggle currency in the UI.

- **Acceptance Criteria:**
  - [ ] Architecture diagram created with correct data flow
  - [ ] User journey diagram created with toggle flow
  - [ ] ADR follows project numbering convention
  - [ ] ADR documents read-time conversion decision and alternatives
  - [ ] README updated with F18 feature description
  - [ ] All diagram files render valid Mermaid syntax

- **Files to touch:**
  - `docs/diagrams/F18-architecture.mmd` (new)
  - `docs/diagrams/F18-journey.mmd` (new)
  - `docs/adr/NNNN-multi-currency-read-time-conversion.md` (new)
  - `README.md` (modify)
