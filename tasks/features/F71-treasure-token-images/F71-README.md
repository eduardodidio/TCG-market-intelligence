# F71 — Treasure Token Card Images

**Status:** planned
**Created:** 2026-08-27
**Description:** Replace CSS placeholder art with real MTG Treasure Token card images in all credit/treasure components. Language-aware image selection (treasure.jpg for EN, tesouro.png for PT-BR/gaucho). Localize hardcoded type line text.

## Scope

- Move card images from `images/` to `frontend/src/assets/`
- TreasureTokenCard: replace CSS gradient + emoji with real card image, language-aware
- TreasureBalance: replace CSS circle icon with card image thumbnail
- CreditConfirmModal: inherits changes via TreasureTokenCard
- i18n: add type line keys ("Token Artifact — Treasure" / "Token Artefato — Tesouro")
- Tests: update existing tests + add image selection tests

## Tasks

| Task | Description | Wave | Depends |
|------|-------------|------|---------|
| F71-T01 | Asset setup + image utility hook | W0 | — |
| F71-T02 | TreasureTokenCard real images | W1 | T01 |
| F71-T03 | TreasureBalance image thumbnail | W1 | T01 |
| F71-T04 | i18n type line + card text | W1 | T01 |
| F71-T05 | Tests | W1 | T01 |

## Waves

- **Wave 0:** T01 (asset setup — unblocks all others)
- **Wave 1:** T02, T03, T04, T05 (all parallel, depend only on T01)

## Architecture Notes

- Vite handles image imports via `import img from './path.jpg'` — returns URL string
- LanguageContext provides `language: 'en' | 'pt-BR'` — use to select image
- Create a `useTreasureImage()` hook or simple utility for DRY image selection
- tesouro.png covers both PT-BR and any future gaucho locale
