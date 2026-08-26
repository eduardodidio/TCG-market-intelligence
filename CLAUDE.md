# CLAUDE.md

Project: **TEDHC Market** (Trading Elder Dragon Highlander Cards)
Stack: **Blank / custom**
Framework: [claude-didio-config](https://github.com/eduardodidio/claude-didio-config)

## Mission

TBD — fill in after kickoff.

## Architecture

No stack assumptions. Edit CLAUDE.md and agents/prompts/*.md to match
your project conventions.

## Commands

- **Build:** `echo 'configure build command in CLAUDE.md'`
- **Test:** `echo 'configure test command in CLAUDE.md'`
- **Run:** `echo 'configure run command in CLAUDE.md'`

## Agent Workflow

This project uses the **4-agent Waves workflow** from claude-didio-config:

1. **Architect** — plans minimal tasks grouped in parallel Waves.
   Wave 0 front-loads permissions/setup.
2. **Developer** — implements each task in a clean bash context.
3. **Tech Lead** — reviews architecture, tests, diagrams.
4. **QA** — validates end-to-end and fills test gaps.

All agents run via `didio spawn-agent <role>` in isolated bash processes.
Logs: `logs/agents/*.jsonl`. Dashboard: `didio dashboard` (phase 2).

### Trigger a feature

```
/create-feature F01 <short description of the feature>
```

See `agents/orchestrator.md` for the full pipeline and
`agents/workflows/feature-workflow.md` for the quality gates.

## Project Layout

```
.
├── CLAUDE.md                    (this file)
├── docs/
│   ├── adr/                     Architecture Decision Records
│   ├── prd/                     Product Requirements Documents
│   ├── diagrams/                Mermaid flowcharts (live docs)
│   └── README.md                Docs index
├── tasks/
│   └── features/                Per-feature task manifests + task files
├── agents/
│   ├── orchestrator.md
│   ├── workflows/feature-workflow.md
│   └── prompts/                 Role prompts (architect, developer, techlead, qa)
├── logs/agents/                 Agent run logs (gitignored)
└── .claude/
    ├── settings.json            Claude Code settings
    ├── commands/                Slash commands (/create-feature, /dashboard, ...)
    └── agents/                  Subagent definitions
```

## Documentation Maintenance Rules

- **ADRs**: every significant architecture decision creates a new ADR under
  `docs/adr/`. Number them sequentially (`0001-*.md`, `0002-*.md`).
- **PRDs**: every feature has a PRD under `docs/prd/` before Architect runs.
- **Diagrams**: every feature MUST produce (or update) at least two Mermaid
  diagrams under `docs/diagrams/`:
  1. **Architecture** (`<FXX>-architecture.mmd`) — component / data-flow
  2. **User Journey** (`<FXX>-journey.mmd`) — BPMN-style user flow
  Diagrams are living documentation — keep them in sync with code.
- **README.md auto-update**: every feature that ships MUST update the
  project `README.md` with a short note of what was delivered (new
  endpoints, new views, new commands, changed behavior). This is not
  optional — if the feature doesn't change the README, either the README
  is stale or the feature shouldn't have shipped.

## Agent Learnings (Retrospective)

At the end of every feature, QA runs a retrospective ceremony and appends
lessons per role to `memory/agent-learnings/<role>.md`. Each agent reads
its own learnings file at the start of every run — the agents improve
with every feature that ships. Do NOT edit these files manually unless
you are clearly adding a durable lesson.

## Guardrails de Seguranca

Regras que o Claude Code DEVE seguir neste projeto. Nenhuma excecao sem
confirmacao explicita do usuario.

**Git**
- NUNCA rodar `git rebase` em branches compartilhadas (`main`, `master`,
  `develop`)
- NUNCA rodar `git push --force` ou `--force-with-lease` sem pedir
- NUNCA rodar `git reset --hard` sobre trabalho nao commitado
- NUNCA usar `--no-verify` para pular hooks (pre-commit, pre-push)
- NUNCA usar `git add -A` ou `git add .` — stage arquivo por arquivo
- NUNCA commitar arquivos com segredos (`.env`, `credentials.*`, chaves
  privadas, tokens, `*.pem`, `*.key`)
- NUNCA amendar commits ja pushados a uma branch compartilhada

**Codigo**
- NUNCA desabilitar validacao, auth ou testes "so pra fazer funcionar"
- NUNCA hardcodear secrets — sempre variaveis de ambiente
- Validar input nas fronteiras do sistema (user input, APIs externas)
- Nao introduzir dependencias novas sem confirmacao

**Infra / operacoes destrutivas**
- NUNCA modificar CI/CD sem confirmacao explicita
- NUNCA rodar `rm -rf`, `DROP TABLE`, `kill -9` sem confirmar
- Mudancas em estado compartilhado (Slack, PRs, GitHub Issues,
  infraestrutura) exigem confirmacao explicita antes de cada acao

**Quando em duvida: pare e pergunte ao usuario.** O custo de uma pausa e
baixo; o custo de uma acao destrutiva nao autorizada e alto.

