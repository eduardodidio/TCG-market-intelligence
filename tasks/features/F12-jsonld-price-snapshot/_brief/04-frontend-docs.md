# F12 Brief -- Frontend and Documentation (T06, T10)

## Frontend Sparse Data (T06)

File: `frontend/src/components/PriceChart.tsx`

Changes:
1. Detect sparse data: `observations.length > 0 && observations.length < 7`
2. Show info banner: "Building price history -- N data point(s) so far."
3. Show dots on Line components when sparse (so single points are visible)
4. No API changes -- same data, better UX for early days of snapshot collection

## Documentation (T10)

Files:
- `docs/prd/F12-jsonld-price-snapshot.md` -- PRD
- `docs/diagrams/F12-architecture.mmd` -- data flow diagram
- `docs/diagrams/F12-journey.mmd` -- operator journey diagram
- `README.md` -- delivery note for F12

Architecture diagram: collection DB -> source_cards -> fetch product page ->
parse JSON-LD -> store observation -> dashboard chart

Journey diagram: cron/CLI/API trigger -> load entries -> idempotency check ->
fetch -> parse -> store -> log summary
