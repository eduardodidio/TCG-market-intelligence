# TCG-market-intelligence - PLAN: FOLLOW-UPS

> Gerado em 2026-10-07 via auditoria claude-didio-config
> Prioridade: melhorias, features e debito tecnico

---

## FOLLOW-01: Implementar Versionamento de Colecao [HIGH]

**Contexto:** Complemento ao FIX-01. Apos corrigir o import destrutivo, implementar sistema de versoes.
**Escopo:**
- Criar tabela `collection_archive` com FK para entries
- Snapshot automatico antes de cada import
- Endpoint para restaurar versao anterior
- ADR-0021 documentando estrategia
**Esforco estimado:** Feature completa (F193 candidata)

---

## FOLLOW-02: Implementar OAuth Callback [MEDIUM]

**Arquivo:** `src/api/routers/auth.py:218-234`
**Status atual:** Endpoint retorna 501 Not Implemented.
**Escopo:**
- Usar authlib para exchange code por tokens
- Integrar com Google/Discord OAuth providers
- Testes de integracao para flow completo
**Esforco estimado:** Feature completa

---

## FOLLOW-03: Rate Limiting em Endpoints [MEDIUM]

**Contexto:** Nao ha rate limiting nos endpoints da API. Depende de database + Liga provider para throttling.
**Escopo:**
- Implementar middleware com async-limits ou slowapi
- Rate limit por usuario/tier (credit-based)
- Proteger endpoints de colecao e portfolio especialmente
**Esforco estimado:** Feature completa

---

## FOLLOW-04: CSRF Protection [MEDIUM]

**Contexto:** API-based, entao cookie-only attacks sao menos provaveis, mas frontend deve validar.
**Escopo:**
- Validar que frontend envia state/nonce
- Adicionar CSRF middleware no backend
**Esforco estimado:** 2-3 tasks

---

## FOLLOW-05: Stress Test de Collection Import [LOW]

**Contexto:** Apos FIX-01 e FIX-04, validar performance.
**Escopo:**
- Benchmark com 10K+ cards
- Profile batch vs single-row flushing
- Otimizar queries se necessario
**Esforco estimado:** 1-2 tasks

---

## FOLLOW-06: Documentacao ADR [LOW]

**Escopo:**
- ADR-0021: Collection import versionamento
- ADR-0022: Auth bypass fix e politica de seguranca
- Atualizar README com features F180+
**Esforco estimado:** 1-2 tasks
