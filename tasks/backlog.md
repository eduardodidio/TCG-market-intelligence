# Feature Backlog

> Atualizado em 2026-08-21. Renumerado a partir de F16 (F13-F15 ja entregues).

## Legenda

- **Status**: `backlog` | `planning` | `in-progress` | `done`
- **Brainstorm?**: indica se a feature precisa de brainstorm antes do planning

---

## F16 — Explore Cards: Sorting Fields

**Status:** planning
**Brainstorm?** Nao

Adicionar campos de ordenacao na tela Explore Cards. Opcoes padrao:
- Nome (A-Z, Z-A) — **default**
- Preco de compra (menor/maior)
- Preco de venda (menor/maior)
- Set / Edicao
- Numero do card
- Data de adicao (mais recente/mais antigo)

---

## F17 — Collection Filter: Set Symbol Icons

**Status:** planning
**Brainstorm?** Nao

Trocar o filtro de colecoes (sets) para exibir apenas o simbolo da edicao.
Ao passar o mouse (hover), exibir tooltip com o nome completo da colecao.
Manter funcionalidade de filtro atual, apenas mudar a representacao visual.

---

## F18 — Multi-Currency Support (BRL + USD)

**Status:** planning
**Brainstorm?** Nao

Transformar toda a base de valores para suportar Real (BRL) e Dolar (USD).
- Criar mecanica de busca diaria (1x/dia) para atualizar a cotacao do dolar (API publica do BCB ou similar)
- Armazenar cotacao historica para conversoes retroativas
- Exibir precos na moeda selecionada pelo usuario

> **Nota:** Os precos do MYP Cards ja sao em BRL. Nao ha necessidade de repensar — apenas adicionar suporte a conversao USD.

---

## F19 — Moeda "Pila" (RS)

**Status:** planning
**Brainstorm?** Nao

Criar moeda customizada chamada "Pila" com a bandeira do Rio Grande do Sul.
- Valor 1:1 com BRL (sempre)
- Tratar como uma "cotacao" interna, mas fixa em 1:1
- Formatacao por extenso: `R$ 230,21` → `230 pilas e 21 centavos` (ou similar)
- Quando exibir valores, usar o formato "pilas" no lugar de "reais"
- A configuracao da moeda padrao sera pelo login do usuario (dependencia: F22)

> **Dependencia:** F18 (multi-currency infra), F22 (login para preferencia do usuario)

---

## F20 — Card Grid Size Control

**Status:** planning
**Brainstorm?** Nao

Manter o tamanho atual da grid como padrao, mas adicionar controle no cabecalho
da grid para aumentar ou diminuir o tamanho dos cards.
- Opcoes: pequeno / medio (default) / grande
- Persistir preferencia (localStorage ou, pos-F22, no perfil do usuario)

---

## F21 — Price Fallback Sources

**Status:** backlog
**Brainstorm?** **SIM** — necessario brainstorm para escolher fonte alternativa

Criar fallback de precos para quando o MYP Cards nao retornar dados.
Candidatos a avaliar no brainstorm:
- Scryfall API (precos internacionais)
- TCG Player API
- CardMarket API (Europa)
- Ligamagic (Brasil)
- Outros agregadores

O brainstorm deve avaliar: disponibilidade de API, cobertura de cards,
frequencia de atualizacao, termos de uso, e facilidade de integracao.

---

## F22 — Authentication (Login Area)

**Status:** planning
**Brainstorm?** Nao

Criar area de login com provedores:
- Google
- Microsoft
- Apple
- Login direto (email + senha)

Regras de acesso:
- Area nao-logada: acesso a Explore Cards, precos publicos, busca
- Area logada: colecao pessoal, analises detalhadas de cards, preferencias
- Usuarios nao-logados que tentarem acessar area restrita devem ser redirecionados ao login

---

## F23 — Deck Import

**Status:** planning
**Brainstorm?** Nao

Permitir importar decks por lista (mesmo formato da importacao de colecao).
- Cards que NAO estiverem na colecao do usuario: exibir com overlay escurecido
- Hover no card sem colecao: tooltip informando "Card nao esta na sua colecao"
- Click no card: abre a aba de visualizacao detalhada
  - (Futuro: funcao de comparar cards nessa tela)

> **Dependencia:** F22 (login — decks sao por usuario)

---

## Resumo

| Feature | Titulo                        | Brainstorm? | Dependencias | Status   |
|---------|-------------------------------|-------------|--------------|----------|
| F16     | Explore Cards: Sorting        | Nao         | —            | planning |
| F17     | Set Symbol Icons              | Nao         | —            | planning |
| F18     | Multi-Currency (BRL+USD)      | Nao         | —            | planning |
| F19     | Moeda "Pila" (RS)             | Nao         | F18, F22     | planning |
| F20     | Card Grid Size Control        | Nao         | —            | planning |
| F21     | Price Fallback Sources        | **SIM**     | —            | backlog  |
| F22     | Authentication (Login)        | Nao         | —            | planning |
| F23     | Deck Import                   | Nao         | F22          | planning |
