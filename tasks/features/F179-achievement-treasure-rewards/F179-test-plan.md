# F179 — Test Plan

- **status:** drafted
- **generator:** TEA
- **generated-at:** 2026-09-24
- **source-brief:** `tasks/features/F179-achievement-treasure-rewards/_brief/00-overview.md`

## 1. Fixtures

| Fixture | Path | Domain | Owner |
|---|---|---|---|
| `repo` (SQLite temp-file `Repository(db_url=f"sqlite:///{tmp_path/'x.db'}")`, sem seed) + `user_id` (via `repo.create_user(...)`, mesmo padrão de `tests/services/test_achievements.py`) | `tests/services/test_achievement_rewards.py` | services (rewards, puro sobre DB) | F179-T02 |
| `_two_users` (dois `repo.create_user(...)`, um já com `credit_transactions` linha `reason="achievement_reward"` pré-inserida) para os cenários de backfill parcial | `tests/services/test_achievement_rewards.py` | services | F179-T02 |
| `repo`/`user_id` (mesmo padrão acima, reaproveitado) + helper `_insert_achievement_row(session, user_id, key)` para simular unlock pré-F179 sem passar pelo fluxo normal | `tests/services/test_achievements.py`, `tests/api/test_achievements_router.py` | services/api | F179-T04 |
| App FastAPI mínimo com `achievements_router` + `dependency_overrides` de `get_db`/`get_current_user` (mesmo padrão já usado em `tests/api/test_achievements_router.py`) | `tests/api/test_achievements_router.py` | api | F179-T04 |
| `click.testing.CliRunner` + `--db sqlite:///<tmp_path>/t.db` (padrão de `tests/test_cli_snapshot.py` e `tests/integration/cli/`) | `tests/integration/cli/test_achievement_rewards_cli.py` | cli | F179-T05 |
| `renderWithAchievements` (helper local que envolve `AchievementsPage` com `I18nextProvider` + mock de `../../api/achievements`, seguindo o setup já existente em `AchievementsPage.test.tsx`) com fixtures de item incluindo `reward`/`tier`/`reward_credited` | `frontend/src/pages/__tests__/AchievementsPage.test.tsx` | frontend | F179-T06 |
| `renderWithI18n` para `AchievementToast` (padrão já usado no próprio arquivo de teste) + fake timers (`vi.useFakeTimers()`) para o throttle do host | `frontend/src/components/__tests__/AchievementToast.test.tsx`, `frontend/src/hooks/__tests__/useAchievementNotifier.test.ts`, `frontend/src/components/__tests__/AchievementNotifierHost.test.tsx` | frontend | F179-T07 |
| Mock de `useAuth` (`vi.mock("../../hooks/useAuth")`) retornando usuário autenticado / guest / anônimo, e mock de `../../api/achievements` (`checkAchievements`), envolvendo o host em `MemoryRouter` | `frontend/src/components/__tests__/AchievementNotifierHost.test.tsx` | frontend | F179-T07 |
| App FastAPI completo (`achievements_router` + `credits_router` de `src/api/routers/credits.py`) + `Repository(db_url="sqlite:///" + str(tmp_path / "f179.db"))` (arquivo, não in-memory — o cenário de threads abre conexões concorrentes) + `ThreadPoolExecutor(max_workers=4)` | `tests/integration/test_f179_achievement_rewards.py` | integration | F179-T08 |
| `CliRunner` importando `backfill_achievement_rewards_cmd` direto de `src.cli.achievement_rewards` (sem depender do registro em `main.py`) | `tests/integration/test_f179_achievement_rewards.py`, `tests/integration/cli/test_f179_cli_registration.py` | integration/cli | F179-T08 / F179-T09 |
| Mock stub `data-testid` de `AchievementNotifierHost` (`vi.mock("../AchievementNotifierHost", () => ({ AchievementNotifierHost: () => null }))`) usado só se o `Layout.test.tsx` existente quebrar | `frontend/src/components/__tests__/Layout.test.tsx` | frontend | F179-T09 |

Nenhum fixture é arquivo estático (JSON/CSV/imagem) — todos são builders
Python/TS in-line reaproveitando padrões já existentes no repo
(`Repository(db_url=...)` de `tests/services/test_achievements.py`,
`dependency_overrides` de `tests/api/test_achievements_router.py`,
`CliRunner` de `tests/integration/cli/`). `feedback_no_ceremony_specs.md`:
um diretório de fixtures compartilhado entre T02/T04/T08 não se paga — cada
arquivo de teste já constrói seu próprio `repo`/`user_id` com uma linha, e
extrair isso indireciona sem eliminar retrabalho real (a única duplicação é
um `Repository(db_url=...)` de 2 linhas, já o padrão do projeto).

## 2. Harnesses por fronteira

### Unit
- **Framework:** pytest (backend, `src/services/achievement_rewards.py` é
  puro sobre SQLAlchemy, sem rede) / Vitest + React Testing Library
  (frontend, `AchievementsPage.tsx`, `AchievementToast.tsx`,
  `useAchievementNotifier.ts`, `creditsEvents.ts`).
- **Comando:** `pytest tests/services/test_achievement_rewards.py tests/services/test_achievements.py tests/api/test_achievements_router.py -v` e `cd frontend && npx vitest run src/pages/__tests__/AchievementsPage.test.tsx src/components/__tests__/AchievementToast.test.tsx src/hooks/__tests__/useAchievementNotifier.test.ts src/hooks/__tests__/useCredits.test.ts src/utils/__tests__/creditsEvents.test.ts`
- **Path padrão:** `tests/services/*.py`, `tests/api/*.py`,
  `frontend/src/{pages,components,hooks,utils}/__tests__/*.test.{ts,tsx}`

### Integration
- **Framework:** pytest + FastAPI `TestClient` sobre `Repository` real
  (SQLite em arquivo, pois o cenário de threads em T08 precisa de conexões
  concorrentes reais) + `click.testing.CliRunner` para o comando CLI.
- **Comando:** `pytest tests/integration/test_f179_achievement_rewards.py tests/integration/cli/test_achievement_rewards_cli.py tests/integration/cli/test_f179_cli_registration.py -v`
- **Path padrão:** `tests/integration/test_f179_achievement_rewards.py`,
  `tests/integration/cli/*.py`

### E2E
- **N/A.** O projeto não tem harness de E2E de browser (Playwright/Cypress)
  configurado para fluxos de UI — o Playwright do repo é só o provider Liga
  Magic (scraping). A cobertura ponta a ponta do fluxo "unlock → crédito →
  toast → saldo atualizado" é feita por `tests/integration/test_f179_achievement_rewards.py`
  (backend real, sem mock de rede) + testes de componente
  (`AchievementNotifierHost.test.tsx`, `AchievementsPage.test.tsx`) com API
  mockada — mesmo padrão já usado em F175/F176. Justificativa em 1 linha:
  montar um harness E2E de browser só para esta feature não se paga
  (`feedback_no_ceremony_specs.md`); a validação visual real (toast
  aparecendo em cima do layout, animação, z-index) fica para QA manual em
  `homol`.

## 3. Perf budgets

_Sem perf budgets aplicáveis._ F179 não introduz uma rota nova nem uma
query custosa (reaproveita `credit_balances`/`credit_transactions` já
indexados por `user_id`); o único risco de performance citado no README é
"backfill em lote" (T05/CLI), mas a feature não define um limite de tempo —
apenas paginação lógica por usuário. QA pode observar a saída de
`backfill-achievement-rewards` em produção manualmente, fora do escopo de
pytest.

## 4. Mocks vs hits real

| Componente | Decisão | Justificativa |
|---|---|---|
| `Repository`/SQLite em `test_achievement_rewards.py` (T02) | real (SQLite em arquivo via `tmp_path`) | A lógica em teste é justamente a serialização por `with_for_update()` + a checagem de existência no ledger; mockar o DB esconderia a própria garantia de idempotência que o módulo existe para prover. |
| `AchievementRow` insert / `on_conflict_do_nothing` em `test_achievements.py` (T04) | real (SQLite) | AC2/AC3 exigem provar que só o insert com `rowcount==1` credita; um mock de sessão esconderia exatamente esse ponto de serialização, que é a decisão registrada no ADR 0020. |
| `CreditService`/`get_balance` no router de `test_achievements_router.py` (T04) | real (via `Repository` real, sem mock de `src/credits/service.py`) | O contrato da AC5 é que `/check` retorna o saldo real pós-crédito; mockar o serviço de crédito esconderia uma dessincronia entre o módulo de rewards e o de créditos, que é justamente o tipo de bug que a integração F65↔F179 pode introduzir. |
| Threads concorrentes em `test_f179_achievement_rewards.py` (T08) | real (SQLite em arquivo + `ThreadPoolExecutor`, tolerando retry de `OperationalError: database is locked`) | A governance item G-D-20260924-005 pede prova de não-duplicação sob concorrência real, não apenas chamadas sequenciais; SQLite em arquivo é o único jeito de exercitar contenção real sem subir Postgres em CI. |
| `useAuth()` em `AchievementNotifierHost.test.tsx` (T07) | mock (`vi.mock("../../hooks/useAuth")`) | Autenticação é infraestrutura transversal já coberta em outros testes; o comportamento em teste é "o host chama ou não `checkAchievements` conforme o papel do usuário", não o fluxo de login em si. |
| `checkAchievements` (API) em `useAchievementNotifier.test.ts` / `AchievementNotifierHost.test.tsx` (T07) | mock (`vi.fn()`) | Teste de componente/hook, não de rede; os cenários (rewards presentes, backfill-only, erro rejeitado) são combinações de resposta que só um mock produz de forma determinística, seguindo o padrão já usado no arquivo antes de F179. |
| `../../api/achievements` em `AchievementsPage.test.tsx` (T06) | mock (`vi.fn()`, já o padrão existente do arquivo) | Página já mocka a API antes de F179; adicionar campos de reward à mesma fixture não muda a decisão. |
| Timers (`Date.now()`/throttle) em `AchievementNotifierHost.test.tsx` (T07) | mock (`vi.useFakeTimers()` / `vi.setSystemTime`) | O throttle de 30s do host precisa ser testado de forma determinística (mount → +10s → +31s); usar tempo real tornaria o teste lento e flaky. |
| Neon/Postgres real | real, mas só via revisão manual + `AC9` ("funciona em SQLite e PostgreSQL") | Não há ambiente Postgres em CI; `.with_for_update()` é no-op documentado em SQLite e lock de linha em Postgres — a suíte automatizada prova a lógica em SQLite, a paridade com Postgres é validação manual do usuário em `homol`/Neon antes da promoção a `main`. |

## 5. Test scenarios resumo

1. `REWARD_TIERS` == {50,100,250,500,1000}; todo key de `ACHIEVEMENT_DEFINITIONS` tem entrada em `ACHIEVEMENT_TIERS` (teste de cobertura, falha se um novo achievement for adicionado sem mapear) — **F179-T02**.
2. `credit_reward_in_session`: 1ª chamada credita (`first_card` → +50, ledger `reason="achievement_reward"`/`reference_id="achievement:first_card"`); 2ª chamada retorna 0, saldo inalterado, 1 única linha no ledger — **F179-T02**.
3. `credit_reward_in_session` cria `CreditBalanceRow` quando ausente; key desconhecida → 0, nenhuma linha escrita; outra `reason` com o mesmo `reference_id` (ex. `bonus_claim`) não bloqueia o crédito — **F179-T02**.
4. `backfill_user_rewards_in_session`/`backfill_all_rewards`: credita cada achievement desbloqueado uma vez; re-run → 0; `dry_run=True` retorna totais > 0 sem alterar o DB; `user_id=` filtra só aquele usuário; erro monkeypatchado em 1 usuário é contado em `errors` sem interromper os demais — **F179-T02**.
5. Boundary: usuário com as 11 conquistas → backfill soma exatamente 3400 (4×50 + 2×100 + 2×250 + 500 + 2×1000), verificado contra `sum(get_reward(k) for k in ACHIEVEMENT_TIERS)` e o literal 3400 — **F179-T02**.
6. `check_achievements_with_rewards`: unlock + crédito na mesma transação (`first_card` → reward 50, saldo 50, 1 linha de ledger); 10 cards → `first_card`+`collector_10` → total 150; 2ª chamada de `/check` → `newly_unlocked=[]`, `total_reward=0`, saldo inalterado, sem linhas duplicadas — **F179-T04**.
7. Lazy backfill: `AchievementRow` pré-existente sem ledger (inserida manualmente simulando pré-F179) → creditada no próximo `/check`, refletida em `backfilled`; roda mesmo com `earned_keys` vazio — **F179-T04**.
8. `grant_set_master`: credita 1000 na 1ª chamada; 2ª chamada → 0 crédito extra (rowcount 0) — **F179-T04**.
9. Bug fix `treasure_hunter`: 5 transações `reason="bonus_claim"` desbloqueia; 4 não desbloqueia; 5 transações `reason="achievement_reward"` não contam para o achievement — **F179-T04**.
10. `GET /achievements`: itens trazem `reward`/`tier` para bloqueados e desbloqueados, e `reward_credited=True` só para os creditados; key legado desconhecida no DB é ignorada sem erro 500 — **F179-T04**.
11. CLI `backfill-achievement-rewards`: 2 usuários com conquistas → contagens corretas e saldos atualizados; idempotente (2ª execução → 0); `--dry-run` não escreve; `--user-id` restringe escopo; `errors>0` → exit code 1; DB vazio → "0 users", exit 0 — **F179-T05**.
12. `AchievementsPage`: fixture com 3 itens (comum desbloqueado+creditado, raro bloqueado, lendário bloqueado) → chips "+50"/"+250"/"+1000" e total "50 / 1300"; item sem campo `reward` (API antiga) não quebra e não mostra chip; `tier=null` com `reward>0` mostra chip sem label de tier; desbloqueado mas `reward_credited=false` não mostra marcador de "ganho"; lista vazia → "0 / 0"; erro de API ainda renderiza o `ErrorBanner` existente — **F179-T06**.
13. `AchievementToast`: `reward=50` → linha "+50 Tesouros adicionados!"; `reward` ausente/0 → sem linha de reward — **F179-T07**.
14. `useAchievementNotifier`: mapeia `rewards` por key; dispara `notifyCreditsChanged()` só quando `(total_reward ?? 0) + (backfilled ?? 0) > 0`; resposta sem `rewards` (backend antigo) não quebra; `newly_unlocked=[]`+`backfilled=300` → um único toast de backfill + evento; nada novo → nenhum toast/evento; erro em `checkAchievements` → nenhum toast, sem throw, próxima chamada funciona — **F179-T07**.
15. `AchievementNotifierHost`: chama check no mount; navegação em +10s ainda não chama de novo; em +31s chama de novo (throttle 30s); guest e anônimo → 0 chamadas; múltiplos toasts empilham sem sobrepor; dismiss remove só aquele toast — **F179-T07**.
16. `creditsEvents`/`useCredits`: `notifyCreditsChanged()` dispara `Event("credits:changed")` no `window`; hook montado refaz fetch quando o evento dispara; após unmount, o evento não dispara mais fetch; múltiplos eventos rápidos não quebram — **F179-T03**.
17. i18n: chaves novas idênticas entre `en.json`/`pt-BR.json`; `t("achievements.reward", {amount:50})` → "+50 Tesouros" (pt-BR) / "+50 Treasures" (en); labels de tier existem para os 5 tiers em ambos os locales — **F179-T03**.
18. Integração ponta a ponta (T08): jornada completa `add card → POST /check → GET /credits/balance (+50) → GET /credits/history` contém `achievement_reward`; 5 chamadas sequenciais de `/check` → exatamente 1 linha de ledger por key; 4 threads chamando `check_achievements_with_rewards` concorrentemente para o mesmo usuário em SQLite arquivo → 1 linha de ledger por key, sem duplicar saldo (governance G-D-20260924-005); legado: inserir `AchievementRow`s manualmente → CLI `--dry-run` não altera → CLI credita → `/check` reporta `backfilled==0`; legado lazy (sem rodar CLI) → `/check` credita e reporta `backfilled` correto; usuário com todas as 11 conquistas (incl. `set_master` via `grant_set_master`) → total 3400; após reward, `CreditService.deduct(...)` continua funcionando e a soma do ledger bate com o saldo — **F179-T08**.
19. Wiring (T09): `python -m src.cli.main backfill-achievement-rewards --help` funciona via o grupo principal, sem ciclo de import; `Layout.tsx` renderiza o host (stub mockado) exatamente uma vez, inclusive para guest/anônimo (o próprio host decide não chamar a API); `--dry-run --user-id 999999` contra DB vazio → exit 0 — **F179-T09**.

## 6. Anotações para tasks

- (F179-T02, `repo`, `_two_users`)
- (F179-T03, — nenhuma fixture de DB; usa apenas `renderWithI18n`/mocks já existentes)
- (F179-T04, `repo`, `_insert_achievement_row`, App FastAPI mínimo)
- (F179-T05, `CliRunner`)
- (F179-T06, `renderWithAchievements`)
- (F179-T07, `renderWithI18n`, mock `useAuth`, fake timers)
- (F179-T08, App FastAPI completo, `ThreadPoolExecutor`, `CliRunner`)
- (F179-T09, `CliRunner`, stub de `AchievementNotifierHost`)

## Riscos para QA

- **Concorrência real em SQLite (T08) é aproximada, não uma prova formal**:
  o teste de threads tolera `OperationalError: database is locked` com
  retry — isso prova ausência de duplicação sob a contenção que o SQLite de
  teste consegue gerar, mas não é o mesmo regime de lock de linha
  (`with_for_update()`) que rodará contra Postgres/Neon em produção. QA deve
  tratar AC3 como "coberto por design + teste aproximado", não como prova
  matemática de serialização sob carga real do Neon.
- **AC9 (SQLite + PostgreSQL) não é testável em CI**: não há ambiente Neon
  disponível para os testes automatizados; a paridade de comportamento do
  `.with_for_update()` (no-op em SQLite, lock real em Postgres) é uma
  suposição documentada no ADR 0020, não uma asserção de teste. QA deve
  confirmar manualmente em `homol` com Neon antes da promoção a `main`
  (mesmo padrão de limitação já registrado no plano de F176).
- **Wave 1 roda em paralelo com contratos ainda não implementados**: T06/T07
  dependem apenas dos tipos/i18n de T03, e são escritos para tolerar campos
  `reward`/`tier` ausentes (T04 ainda não mesclado). QA deve rodar a suíte
  completa de frontend (`npm test && npm run build`) só depois que Wave 1
  inteira estiver mesclada, para pegar qualquer type mismatch real entre o
  que T04 devolve e o que T06/T07 esperam.
- **Arquivos batch-compartilhados (`main.py`, `Layout.tsx`, `README.md`)
  só são tocados por T09** — se outra feature do batch F171–F178 mesclar
  antes e mudar as linhas ao redor do ponto de inserção descrito no task
  file, o diff de T09 pode não aplicar como planejado; QA deve conferir que
  T09 releu esses arquivos antes de editar (nota já no próprio task file) e
  que o diff final ficou mínimo (1–3 linhas por arquivo, conforme README).
- **`treasure_hunter` fix (AC8) muda a semântica de um teste existente**:
  `tests/services/test_achievements.py` pode ter um teste que seedava
  `reason="bonus"` para desbloquear `treasure_hunter`; QA deve confirmar que
  o ajuste em T04 manteve esse teste passando com a correção
  (`.in_(("bonus", "bonus_claim"))`) em vez de simplesmente trocar a string
  seedada — do contrário a regressão original (`bonus_claim` nunca conta)
  pode voltar sem que nenhum teste perceba.
