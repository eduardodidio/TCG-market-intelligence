# TCG-market-intelligence - PLAN: FIXES

> Gerado em 2026-10-07 via auditoria claude-didio-config
> Prioridade: correcoes de bugs e problemas de seguranca

---

## FIX-01: Collection Import Deleta Todos os Dados Sem Confirmacao [CRITICAL]

**Arquivo:** `src/collection/importer.py:238`
**Problema:** `import_collection_csv()` deleta TODOS os dados da colecao do usuario antes do import sem backup/versionamento. Se o import falhar no meio, dados anteriores sao perdidos permanentemente.
**Codigo atual:**
```python
session.query(UserCollectionRow).filter(UserCollectionRow.user_id == user_id).delete()
```
**Impacto:** Perda de dados irreversivel para usuarios que re-importam colecoes.
**Solucao proposta:**
- Implementar tabela de arquivo/versionamento antes do delete
- Adicionar confirmacao explicita para imports destrutivos
- Considerar estrategia merge/update em vez de full replace
- Adicionar audit logging para delecoes de colecao
**Esforco estimado:** Wave 1 (2-3 tasks)

---

## FIX-02: Auth Bypass em Dev Mode Permite Acesso Sem API Key [HIGH/SECURITY]

**Arquivo:** `src/auth/dependencies.py:176-185`
**Problema:** Em dev mode, se `TCG_API_KEY` nao estiver setada, o sistema silenciosamente bypassa autenticacao:
```python
if expected is None and not token:
    _log.warning("dev_mode_auth_bypass", path=str(request.url.path))
    return "api_key_user"
```
**Impacto:** Em producao, se `TCG_API_KEY` nao estiver configurada, qualquer request passa sem auth.
**Solucao proposta:**
- Forcar check de `TCG_API_KEY` em ambientes nao-dev durante startup
- Remover bypass silencioso; checar `TCG_ENV` explicitamente
- Fail fast se env var critica estiver faltando em producao
**Esforco estimado:** 1 task

---

## FIX-03: Null Check Ausente no Liga Provider [HIGH]

**Arquivo:** `src/providers/liga/provider.py:921-931`
**Problema:** `_select_edition_sync()` nao verifica se `self._sync_page` e None antes de usar:
```python
def _select_edition_sync(self, edition_value: str) -> str:
    page = self._sync_page  # Pode ser None
    page.evaluate(...)
```
**Impacto:** Crash com AttributeError se page nao foi inicializada.
**Solucao proposta:** Adicionar null check e raise LigaError com mensagem descritiva.
**Esforco estimado:** 1 task

---

## FIX-04: Validacao de FK Antes do Import de Colecao [MEDIUM]

**Arquivo:** `src/collection/importer.py:236-276`
**Problema:** Collection importer usa `session.flush()` por row individualmente. Se `card_id` for None (FK constraint violation), flush falha mid-transaction e estado parcial e perdido.
**Solucao proposta:**
- Validar todas as FKs existem antes de iniciar transacao de import
- Usar batch inserts em vez de flush-per-row
- Adicionar NULL checks explicitos para `card_id` antes de inserir
**Esforco estimado:** 1 task

---

## FIX-05: Error Handling Silencioso no Liga Provider Browser Reset [LOW]

**Arquivo:** `src/providers/liga/provider.py:191-204, 263-278`
**Problema:** Bare `except Exception: pass` em `_close_sync()` e `_reset_browser_sync()` engole erros silenciosamente.
**Solucao proposta:** Logar excecoes antes de ignorar.
**Esforco estimado:** 1 task

---

## FIX-06: Password Change Nao Valida Tipo de Usuario [LOW]

**Arquivo:** `src/api/routers/auth.py:171`
**Problema:** `getattr(user_row, "password_expires_at", None)` no change_password nao valida se usuario e guest.
**Solucao proposta:** Adicionar check explicito de role guest.
**Esforco estimado:** 1 task

---

## FIX-07: __import__() Dinamico no CLI [LOW]

**Arquivo:** `src/cli/main.py:1285, 2372, 2717`
**Problema:** Usa `__import__()` em vez de imports normais, reduzindo type checking e rastreabilidade.
**Solucao proposta:** Converter para imports estaticos.
**Esforco estimado:** 1 task
