# F53 — Pila Easter Eggs (Gaucho Chimarrao + Dialogues)

**Status:** done
**Priority:** low (engagement/fun)
**Dependencies:** none

## Summary

When the user has PILA currency selected, a small pulsing chimarrao (mate)
icon appears in the bottom-right corner of the screen. Clicking it triggers
a page-specific gaucho dialogue with clickable response options. After the
interaction completes, the icon disappears (script-like single interaction,
reappears on page navigation).

### Dialogue Map

| Page | Message | Options | Replies |
|------|---------|---------|---------|
| Dashboard (`/`) | "Bah meu, ta tri a plataforma ne?! Os guris se puxaram!" | "ahaaam!" | *(dismiss)* |
| Collection (`/collection`) | "Tche, que ta o Luxo do gaucho esta colecao?" | "to estorado" / "me caiu os butias do bolso!" | "Dale!" / "Que barbaridade! Na proxima na rateia meu, fica experto nas trocas de realese e cards muitos roubados" |
| Ban List (`/banlist`) | "Olhou os bans recentes? Tudo em ordem?" | "Deu bom!" / "Deu ruim!" | "Ai sim!" / "Ai nao!" |
| Decks empty (`/decks`, 0 decks) | "Bah, mas nenhum deckzinho aqui eihn! Nem te apresenta" | *(none, auto-dismiss after 4s)* | — |
| Decks with decks (`/decks`, 1+ decks) | "E este deckzinho ai? O luxo do gaucho?" | "sim" / "nao" | "dale!" / "ta te michando p importar o ouro aqui!?" |

## Waves

### Wave 0 (parallel)
- **F53-T01** — ChimarraoIcon component with pulse animation — **done**
- **F53-T02** — GauchoDialog component (dialogue bubble + options + replies) — **done**

### Wave 1
- **F53-T03** — Page integration + dialogue data + i18n keys — **done**
