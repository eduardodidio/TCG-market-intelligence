# F180 -- Reality Fracture (FRA) Catalog Seed & Explore Cards

**Status:** done

## Goal

Add the Reality Fracture set (FRA, released 2026-10-02) and its related
sets (FRC Commander, TFRA Tokens, TFRC Commander Tokens) to the card
catalog so they appear on the Cards/explore page with prices from Liga
Magic.

## Architecture Impact

No schema changes, no new modules, no new endpoints. This feature uses
existing infrastructure:

- `src/catalog/scryfall.py` + `src/catalog/seeder.py` -- bulk data
  already handles new sets automatically once Scryfall publishes them.
- `src/collectors/liga_sweep.py` -- catalog scan mode
  (`collection_only=False`) fetches Liga prices for catalog cards.
- `bats/` -- new operational script to seed + scan FRA in one step.

## Parallel Compatibility

FULLY INDEPENDENT from F181, F182, F183. Zero file overlap.

Files touched:
- `docs/prd/F180-reality-fracture-catalog.md` (new)
- `docs/diagrams/F180-architecture.mmd` (new)
- `docs/diagrams/F180-journey.mmd` (new)
- `bats/catalog-seed-fra.bat` (new)
- `README.md` (append delivery note)

## Waves

- **Wave 0**: F180-T01              (docs: PRD + diagrams)
- **Wave 1**: F180-T02, F180-T03    (bat script + README update, parallel)

## Acceptance Criteria

- [ ] PRD exists at `docs/prd/F180-reality-fracture-catalog.md`
- [ ] Architecture diagram at `docs/diagrams/F180-architecture.mmd`
- [ ] Journey diagram at `docs/diagrams/F180-journey.mmd`
- [ ] `bats/catalog-seed-fra.bat` exists and runs `catalog seed` then
      `catalog scan --set fra` + `catalog scan --set frc`
- [ ] README.md updated with F180 delivery note
- [ ] After running the bat, FRA cards appear on `/cards` with set filter
