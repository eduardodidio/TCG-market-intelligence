# F180 -- Reality Fracture (FRA) Catalog Seed & Explore Cards

**Feature ID:** F180
**Status:** planned
**Date:** 2026-09-28

## Problem

Reality Fracture (FRA) releases 2026-10-02. Users want to browse FRA cards
on the Cards page and see Liga prices before/at launch. The existing catalog
infrastructure handles this automatically once Scryfall publishes bulk data,
but we need an operational script and a re-seed to include the new set.

## Goal

Seed FRA + FRC (Commander) + TFRA (Tokens) + TFRC (Commander Tokens) into
the card catalog via Scryfall bulk data, scan FRA/FRC prices via Liga Magic,
and provide a one-click bat script for the entire operation.

## Scope IN

- Re-run `catalog seed` to pick up FRA and related sets from Scryfall bulk
  data.
- Create `bats/catalog-seed-fra.bat` that orchestrates seed + scan in one
  step.
- Scan FRA and FRC prices via Liga (`catalog scan --set fra`, `--set frc`).
- Update README with delivery note.

## Scope OUT

- No schema changes.
- No new API endpoints.
- No frontend changes (existing Cards page handles new sets automatically
  via the set filter).
- No scanning of token sets (TFRA, TFRC) -- Liga does not list token cards.

## Success Metrics

- FRA cards appear in the `/cards` set filter after running the bat.
- `catalog stats` shows `fra` and `frc` sets with card counts.
- The bat script runs end-to-end without errors.

## Architecture

Uses existing infrastructure only:

- `src/catalog/scryfall.py` -- downloads Scryfall bulk data (~600MB JSONL.gz)
- `src/catalog/seeder.py` -- batch upsert cards + source_cards
- `src/collectors/liga_sweep.py` -- catalog scan mode fetches Liga prices
- `src/cli/main.py` -- `catalog seed` and `catalog scan` CLI commands
