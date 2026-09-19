# UX Journey Audit — 2026-09-18

10 jornadas end-to-end tracadas pelo codigo. 4 P1, 18 P2, 16 P3.

---

## P1 — Flow Breaking (4 issues)

### 1. Web search "Added" sem link para colecao
- `Cards.tsx`: `handleAddToCollection()` adiciona card mas nao navega nem mostra link
- Usuario tem que ir manualmente para `/collection` para achar o card
- **Fix**: toast com "View in Collection" link apos add

### 2. Alert notifications nao sao clicaveis
- `AlertBell` mostra notificacoes como texto puro, sem link
- Usuario ve "preco caiu!" mas nao consegue navegar direto para o card
- **Fix**: fazer notification items linkarem para `/cards/{cardId}`

### 3. Admin operations sem confirmacao/progresso
- Botoes de scan no AdminPanel executam sem confirmacao
- Scan de 5+ min nao mostra progresso — pagina parece congelada
- **Fix**: modal de confirmacao + progress bar com contagem de cards

### 4. Back button mobile ausente em paginas de detalhe
- CollectionCardDetail, CardDetail, DeckView usam Breadcrumb
- No mobile, breadcrumb e pequeno e nao tem botao de voltar obvio
- **Fix**: chevron "← Back" visivel no header mobile

---

## P2 — Friction (18 issues, top highlights)

| Issue | Jornada | Fix |
|-------|---------|-----|
| MyCollection filtros nao persistem na URL | J3/J8 | Sync searchParams como Cards.tsx ja faz |
| BetaRoute mostra bloqueio sem explicacao | J2 | Texto "Contact admin" + motivo |
| AcquisitionPriceInput salva silenciosamente | J3 | Inline "Saved ✓" feedback |
| ImportPurchasesPage sem link para cards importados | J6 | Botao "View Imported Cards" |
| NotFoundPage/Login hardcoded dark | J7 | Adicionar dark: variants |
| Offline collection sem timestamp | J9 | "Last synced: X ago" |
| Sticky filter bar ocupa 40-50% da tela mobile | J8 | Colapsar em drawer no mobile |
| Admin credit adjustment sem confirmacao | J10 | Inline "Saving..." → "Saved ✓" |
| Overwrite checkbox no import sem explicacao | J6 | Label + tooltip |
| UpdatePrompt nao explica quando atualiza | J9 | "Takes effect after reload" |
| DeckBuildWizard sem botao "Back" entre steps | J5 | "← Previous" nos steps 2-4 |
| Deck generation loading sem progresso | J5 | Spinner + estimated time |

---

## P3 — Polish (16 issues, destaques)

- Commander search sem preview de imagem do card
- Budget input no deck builder sem unidade (BRL? per card? total?)
- Guest user sem indicacao visual de que ve dados do admin
- Admin audit log limitado
- Offline write operations completamente bloqueadas (sem queue)
- Navegacao sem warning de unsaved changes em forms
- Card detail nao linka para Market/Trending relacionados
- DeckView nao mostra quais cards o user ja tem

---

## Padroes Cross-Journey

### Links faltantes entre entidades
- Card ↔ Market (sem "See on Market" no card detail)
- Alert ↔ Card (notificacao nao linka)
- Import result ↔ Collection (sem navegacao pos-import)
- Deck cards ↔ Owned status (sem badge de posse no deck)

### Error recovery fraco
- Maioria das paginas mostra erro sem botao "Retry"
- 402 (creditos insuficientes) nao indica como resolver
- Network errors nao oferecem retry com backoff

### Confirmacao ausente em mutacoes
- Saves silenciosos (acquisition price, settings, credit adjustment)
- Deletes sem UndoToast (deck, alert — apenas collection tem)
- Navegacao nao avisa sobre edits nao salvos

---

**Conclusao**: Fluxos core funcionam bem, mas conectividade entre paginas e fraca.
15-20h de trabalho focado nos 4 P1 + top P2 traria melhoria significativa.
