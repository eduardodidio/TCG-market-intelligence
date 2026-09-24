# 03 — TrendingService: não guardar erro no cache

Arquivo: `src/services/trending.py`.

## Mudança
- Guardar um flag `query_failed = True` no `except` de `get_trending`.
- Se `query_failed` → **não** gravar em `self._cache`. Retornar a resposta vazia normalmente
  (o router continua sem nunca devolver 500, como no F165).
- Opcional (recomendado): se a query deu certo mas o resultado ranqueado está vazio, guardar no
  cache com TTL curto (`self._empty_cache_ttl = timedelta(minutes=2)`) em vez de 30 min. Guarde
  o TTL junto da entrada (`dict[str, tuple[datetime, TrendingResponse, timedelta]]`) ou
  verifique `len(cached_response.cards) == 0` na leitura.
- Adicionar um log estruturado `trending_computed` com `scope`, `direction`, `period_days`,
  `cards_with_prices=len(price_data)`, `ranked=len(ranked)`, para facilitar o diagnóstico em produção.

## Compatibilidade
- A assinatura de `get_trending` e `invalidate_cache` não muda.
- Testes existentes que tocam o cache: `tests/unit/services/test_trending_service.py`
  (`test_cache_hit_returns_cached`, `test_cache_miss_after_ttl`,
  `test_different_cache_keys_for_different_params`),
  `tests/test_trending_error_resilience.py`, `tests/unit/services/test_trending_collection_only.py`.
  Rode todos; ajuste apenas se algum afirmar explicitamente que erros ficam em cache.
