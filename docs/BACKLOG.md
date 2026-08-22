# Backlog

Prioridade 1 = hotfixes (executar imediato). Prioridade 2 = features planejadas.

---

## Prioridade 1 — Hotfixes

| ID | Descricao | Status |
|----|-----------|--------|
| HF-01 | MyCollection cards nao clicaveis — todos cards devem ser clicaveis (link interno ou Scryfall) | DONE |
| HF-02 | Cards sem arte e sem preco em MyCollection e ExploreCards — fallback de imagem por nome Scryfall | DONE |

---

## Prioridade 2 — Features de Market Intelligence

| ID | Titulo | Descricao curta | Deps |
|----|--------|-----------------|------|
| F13 | Buscas por colecao | Varredura independente por colecao, edicao, formato, conjunto de cards. Cada execucao com metricas (inicio, fim, status, processados, erros). | - |
| F14 | Varredura em tempo real | Progresso visual de varredura (barra, cards processados, precos atualizados). Colecao preenche conforme dados chegam (streaming). | F13 |
| F15 | Historico de precos | Cada coleta gera snapshot historico. Periodos: 24h, 7d, 30d, 90d, 180d, 1y. Periodo padrao configuravel. | F13 |
| F16 | Metricas de historico | Variacao %, absoluta, media, maxima, minima, tendencia, volatilidade, performance por periodo. Alimentado pelos snapshots. | F15 |
| F17 | Top Decks por valor | Ranking de decks mais caros. Filtros: formato, colecao, periodo, faixa de preco, popularidade. Evolucao: maiores valorizacoes/desvalorizacoes. | F16 |
| F18 | Cards em alta e em baixa | Motor de tendencia (variacao %, absoluta, volume, consistencia, periodo). Evitar falsos trending. | F16 |
| F19 | Varredura global rotineira | Global Market Scanner periodico automatizado. Scheduler configuravel, execucao manual, registro, monitoramento de erros, reprocessamento. | F13 |
| F20 | Landing Page — Em Alta / Em Baixa | Secoes na landing com cards em alta/baixa vindos do Global Market Scanner. Dados pre-calculados. | F18, F19 |
| F21 | Ticker estilo Bolsa | Ticker horizontal no topo com cards em alta/baixa, variacao %. Animacao, atualizacao automatica, clicavel (navega para analise do card). | F18, F19 |
| F22 | Pagina global de Mercado | Area dedicada: em alta, em baixa, maiores valorizacoes/quedas, cards mais movimentados, top decks, historico, tendencias. Motor unico compartilhado. | F18, F19, F17 |
| F23 | Lista de banimentos | Banlist centralizada por formato. Card, status, data da alteracao, historico de alteracoes. | - |
| F24 | Motor de banidas em My Collection | Analise automatica da colecao contra banlist atual. Alertas de cards banidos, notificacao de alteracoes recentes. | F23 |
| F25 | Historico de banimentos | Registro historico de entradas/saidas na banlist. Analise futura de impacto de banimentos no mercado. | F23 |
| F26 | Arquitetura compartilhada de dados | Nucleo central: Market Scanner -> Historical Data -> Trend Engine -> (Ticker, Landing, Market Page, Top Decks, My Collection, Ban Engine). | F13, F15, F16, F18 |

---

## Prioridade 3 — Ecossistema de Aluguel, Trade e Marketplace - requer Brainstorm

| ID | Titulo (Epico) | Descricao curta | Deps |
|----|----------------|-----------------|------|
| E01 | Aluguel de Decks | Catalogo, cadastro de deck alugavel, reserva, historico de aluguel. Status: DISPONIVEL->RESERVADO->RETIRADO->EM USO->DEVOLVIDO->FINALIZADO. | E03 |
| E02 | Deck Library | Biblioteca publica de decks. Experimentar antes de comprar. Historico de alugueis. | E01 |
| E03 | Colecao como estoque | Status operacional por carta: disponivel, venda, trade, aluguel, reservado, em aluguel, indisponivel, vendido. Gestao de disponibilidade. | - |
| E04 | Banca / Estoque compartilhado | Conceito de banca (vendedor/colecionador/parceiro). Produtos: venda, trade, aluguel. Controle de estoque e movimentacoes. | E03 |
| E05 | Marketplace alternativo | Venda direta, compra, comparacao de vendedores. Estrutura propria de taxas transparente. | E03, E04 |
| E06 | Parceria com lojas | Cadastro de loja, ponto fisico (retirada/devolucao/trades). Modelo de comissao configuravel. | E04 |
| E07 | Rede de parceiros | Tipos: usuario, colecionador, trader, loja, organizador de eventos, parceiro comercial. Permissoes por tipo. | E06 |
| E08 | Sistema de Trade | Listas "Tenho"/"Quero", cards disponiveis para trade, matching automatico, trade presencial (local, loja, data). | E03 |
| E09 | Usuario VIP | Planos premium: mais decks, descontos, taxas reduzidas, prioridade, beneficios em lojas. Arquitetura para multiplos planos. | E07 |
| E10 | Reputacao e confianca | Avaliacoes (vendedor, comprador, locatario, proprietario, loja). Historico, indicadores, sistema de caucao, disputas. | E07 |
| E11 | Logistica de aluguel | Fluxo completo: reserva->pagamento->confirmacao->retirada->utilizacao->devolucao->conferencia->liberacao caucao->avaliacao. Retirada loja, proprietario, correios. | E01, E06, E10 |
| E12 | Decks tematicos | Decks para experiencia: casual, competitivo, tribal, personagens, iniciantes, eventos. | E02 |
| E13 | Conversao aluguel para compra | Ponte aluguel->venda. Credito parcial, desconto para quem alugou, oferta automatica apos N alugueis. | E01, E05 |
| E14 | Economia do ecossistema | Fontes de receita: comissao aluguel, comissao venda, plano VIP, lojas parceiras, destaque de anuncios, servicos premium. | E05, E06, E09 |
| E15 | Visao futura — Ecossistema | Colecao->Banca->Venda->Trade->Aluguel->Loja parceira no mesmo sistema. Arquitetura preparada desde o inicio. | todos |

---

## Notas

- Features F13-F26 formam o **Motor de Market Intelligence** — prioridade tecnica.
- Epicos E01-E15 formam o **Ecossistema de Aluguel/Trade/Marketplace** — prioridade de negocio, execucao posterior.
- F26 (Arquitetura compartilhada) e cross-cutting: deve ser planejada antes de F17-F22 para evitar duplicacao de logica.
- Hotfixes HF-01 e HF-02 ja foram implementados e estao no branch atual.
