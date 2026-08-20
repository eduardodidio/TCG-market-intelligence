# Brainstorm — Estrategia de atualizacao recorrente da base de dados de precos TCG

_Gerado em 2026-08-19 por /brainstorm._

## Contexto

Topic ja especifico, sem clarificacao adicional. O sistema coleta precos
de Magic: The Gathering do MYP Cards (Brasil) via CLI manual (`backfill`,
`update`). O banco tem 240 cards de 8 sets com observacoes semanais de
preco. O MYP Cards e protegido por Cloudflare e requer curl_cffi com
impersonate="chrome". Rate limiting existente: 1s entre requests,
semaphore de 3 conexoes concorrentes. A infra de coleta ja suporta
resume, retry e concorrencia. O backend e FastAPI, o frontend e React
SPA. Nao ha deploy em producao — tudo roda local por enquanto.

## Direcoes

### Direcao 1 — Cron do SO + CLI existente
**Quem ganha / Quem perde:** Ganha simplicidade e zero dependencias novas; perde observabilidade e portabilidade entre SOs
**Esforco estimado:** S
**Risco principal:** Cron silencioso — se falhar, ninguem percebe ate os dados ficarem velhos
**Pre-condicao:** Maquina do desenvolvedor ligada e com ambiente Python ativo no horario agendado

Usar crontab (Linux/Mac) ou Task Scheduler (Windows) para rodar
`python -m src.cli.main update` periodicamente. Frequencia sugerida:
1x por dia a noite (MYP atualiza precos ~1x/semana, mas coletas
diarias garantem que nao se perca a janela). Logs redirecionados para
arquivo. Sem codigo novo — apenas configuracao de infra local.

Pros:
- Zero codigo novo, zero dependencias
- Usa a infra de coleta ja testada (resume, retry, rate limiting)
- Funciona imediatamente

Contras:
- Depende da maquina estar ligada
- Sem dashboard de saude da coleta
- Nao portavel (cron config e local, nao versionada)
- Se Cloudflare bloquear, ninguem e notificado

### Direcao 2 — Scheduler in-process (APScheduler) no FastAPI
**Quem ganha / Quem perde:** Ganha coleta automatica integrada ao app; perde simplicidade do deploy
**Esforco estimado:** M
**Risco principal:** Scheduler roda na mesma thread/processo do API — se travar, o API trava junto
**Pre-condicao:** FastAPI rodando como servico persistente (nao apenas `uvicorn` manual)

Adicionar APScheduler como dependencia e registrar um job cron que
executa `run_update()` a cada N horas. O scheduler sobe junto com o
FastAPI no startup event. Adicionar endpoint `/api/v1/collect/status`
que retorna ultimo run, proximo run, erros recentes. O job roda em
background thread, respeitando o rate limiting existente.

Pros:
- Tudo em um processo — deploy simples
- Endpoint de status da visibilidade ao usuario
- Config versionada no codigo (frequencia, retry policy)
- Frontend pode mostrar "ultima atualizacao: ha 2h"

Contras:
- Nova dependencia (apscheduler)
- Se o processo cair, a coleta para
- Risco de memory leak em long-running jobs
- Precisa de processo persistente (nao serverless)

### Direcao 3 — Endpoint de trigger + cron externo leve
**Quem ganha / Quem perde:** Ganha flexibilidade de trigger (cron, webhook, CI); perde autonomia (depende de trigger externo)
**Esforco estimado:** S
**Risco principal:** Endpoint de coleta exposto pode ser abusado (precisa de auth ou rate limit)
**Pre-condicao:** O endpoint `/api/v1/collect/backfill` ja existe (F06) — precisa apenas de um trigger externo

O endpoint de coleta ja existe no FastAPI (POST /api/v1/collect/backfill).
Basta configurar um trigger externo: cron local com `curl`, GitHub
Actions scheduled workflow, ou ate um cron do Render/Railway/Fly.
Adicionar um endpoint GET `/api/v1/collect/health` que retorna metricas
de saude (ultima coleta, cards desatualizados, erros). O frontend
consome esse endpoint para mostrar status.

Pros:
- Quase zero codigo novo (health endpoint apenas)
- Trigger flexivel — troca de cron para CI sem mudar o app
- Endpoint de health resolve observabilidade
- Caminho natural para deploy futuro (CI trigger)

Contras:
- Endpoint de coleta sem auth e inseguro em producao
- Depende do backend estar rodando
- GitHub Actions tem limite de 5 min para jobs gratis
- Sem retry automatico se o trigger falhar

### Direcao 4 — Daemon dedicado com health checks e alertas
**Quem ganha / Quem perde:** Ganha robustez e observabilidade completa; perde simplicidade (over-engineering para 240 cards)
**Esforco estimado:** L
**Risco principal:** Over-engineering — complexidade desproporcional ao tamanho do dataset
**Pre-condicao:** Decisao de deploy (onde o daemon vai rodar? VPS, container, local?)

Criar um servico separado (`src/scheduler/daemon.py`) que roda como
processo independente. Usa APScheduler ou asyncio loop com sleep.
Inclui: health check endpoint, metricas Prometheus-style (cards
coletados, erros, latencia), alertas via webhook/email quando coleta
falha N vezes consecutivas, log estruturado com rotacao. O daemon
pode rodar como systemd service, Docker container, ou supervisor
process.

Pros:
- Isolamento total — se o daemon travar, a API continua
- Observabilidade completa (metricas, alertas, logs)
- Pronto para producao e deploy em container
- Retry policy sofisticada (backoff exponencial, circuit breaker)

Contras:
- Complexidade alta para 240 cards com precos semanais
- Nova infra de deploy (systemd/Docker/supervisor)
- Duas coisas para manter rodando (API + daemon)
- Premature optimization — o dataset pode nao justificar

### Direcao 5 — Coleta lazy on-demand (cache-and-refresh)
**Quem ganha / Quem perde:** Ganha eficiencia (so atualiza o que e acessado); perde cobertura completa do catalogo
**Esforco estimado:** M
**Risco principal:** Cards nao acessados nunca sao atualizados — dados ficam progressivamente stale
**Pre-condicao:** Metricas de acesso por card (quais sao consultados) para priorizar

Em vez de atualizar todos os 240 cards periodicamente, atualizar
sob demanda: quando o usuario acessa um card no frontend, o backend
verifica se o preco tem mais de N dias. Se sim, dispara um refresh
em background e serve o dado stale enquanto atualiza. Complementar
com um job leve que atualiza os "top 50 cards mais acessados" 1x/dia.

Pros:
- Eficiente — so gasta requests MYP em cards que importam
- Reduz risco de rate limiting / Cloudflare block
- UX boa — usuario sempre ve dados frescos para o que consulta
- Escala melhor conforme o catalogo cresce

Contras:
- Cards nunca acessados ficam com dados antigos
- Complexidade de cache invalidation
- Primeira visita a um card pode ser lenta
- Market movers precisa de dados frescos de TODOS os cards
