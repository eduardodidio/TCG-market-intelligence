# EDHREC fixtures

- **Capture date:** 2026-09-24
- **Status:** synthetic (hand-built, network blocked in sandbox) — revalidate on
  the first real collection and replace with the real payload trimmed to ≤ 200 KB.

| File | Origin URL | Notes |
|---|---|---|
| `top_commanders.json` | `https://json.edhrec.com/pages/commanders/year.json` | `container.json_dict.cardlists[].cardviews[]` with `name`, `sanitized`, `url`, `num_decks`, `label`, `color_identity`. Last entry has **no `name`** (edge case: adapter must skip it with a warning). |
| `decklist_atraxa-praetors-voice.json` | `https://json.edhrec.com/pages/average-decks/atraxa-praetors-voice.json` | `deck[]` = `"<qty> <name>"` lines, 100 cards, commander is the first line and matches `commander`. Contains split cards (`Fire // Ice`, `Wear // Tear`, `Commit // Memory`). |
| `decklist_krenko-mob-boss.json` | `https://json.edhrec.com/pages/average-decks/krenko-mob-boss.json` | Same shape; mono-red, 100 cards. |
