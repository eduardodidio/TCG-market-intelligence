# TCG Market Intelligence — Script de prompts para o Lovable (só layout)

> Escopo do Lovable: **interface, apenas**. Design system, telas, componentes,
> estados visuais e gráficos. Nada de endpoints, contrato de API, cliente HTTP,
> autenticação ou fetching — isso resolvemos no repositório depois.

---

## Como usar

1. **Projeto novo no Lovable.** Não importe o repositório — o backend Python só
   confunde o gerador. Nome sugerido: `tcg-market-intelligence-ui`.
2. Cole a **PARTE 0** em **Project Settings → Knowledge**. Ela fica valendo para
   todos os prompts seguintes e é o que mantém a consistência visual.
3. Rode os prompts **na ordem**, um por vez, esperando o build ficar verde.
   Prompt gigante = resultado pior.
4. Use o botão **Edit** (seleção direta no preview) para ajustes visuais
   pequenos, em vez de gastar um prompt inteiro.
5. Quando errar, use **Revert** no histórico em vez de pedir "conserta".

Blocos ```` ```prompt ```` são para copiar e colar literalmente.

---

## PARTE 0 — Briefing (colar em Knowledge)

```prompt
# TCG Market Intelligence — briefing de interface

Interface de um app que trata cartas de Magic: The Gathering como ativos
financeiros. O usuário acompanha cotações, variação, histórico e o valor da
própria coleção como quem acompanha uma carteira de investimentos.

## Escopo deste projeto
APENAS a camada de interface. Não construa backend, autenticação, banco,
Supabase, integração com API, cliente HTTP ou qualquer camada de rede. Todo
conteúdo exibido vem de dados estáticos de exemplo. A integração real será
feita fora do Lovable.

## Regra de arquitetura (única, e importante)
Todo dado de exemplo mora em `src/data/sample.ts`, exportado como constantes
tipadas. Nenhum componente inventa dado internamente: todo componente de tela
recebe seu conteúdo por PROPS e é puro em relação a isso. As páginas importam
de `src/data/sample.ts` e repassam por props. Isso é o que vai permitir trocar
a fonte de dados depois sem reescrever componente nenhum.

Os dados de exemplo devem ser realistas e determinísticos:
- ~120 cartas de Magic em 8 coleções (DMR, MH3, LTR, BRO, ONE, MOM, WOE, LCI)
- preços em BRL de R$ 0,50 a R$ 900, com distribuição desigual (muitas baratas,
  poucas caras)
- série histórica SEMANAL de até 3 anos por carta, com tendência, ruído e
  alguns saltos bruscos
- uma coleção de usuário com ~60 linhas, quantidades 1 a 4, qualidades NM/SP/MP,
  idiomas PT/EN
- inclua propositalmente alguns registros com preço ausente e algumas cartas
  sem histórico, para que os estados vazios sejam visíveis no preview

## Stack
Vite + React + TypeScript, Tailwind + shadcn/ui, Recharts para TODO gráfico
(não use outra lib), react-router-dom, lucide-react. Sem @tanstack/react-query,
sem axios, sem SWR.

## Idioma e formatos
Interface 100% em PORTUGUÊS DO BRASIL.
- Moeda: R$ 1.234,56 (pt-BR). Valor ausente exibe "—", nunca "R$ null".
- Datas: DD/MM/AAAA. Tempo relativo: "há 2 dias".
- Percentual: +12,3% / -5,7% / 0,0%.
- Números em colunas de tabela e eixos: font-variant-numeric: tabular-nums.

## Vocabulário da interface
Use "cotação", "variação no período", "alta", "baixa", "carteira", "coleção",
"observação". NUNCA escreva "variação diária" — a série é semanal, e isso
aparece como um rótulo discreto perto dos gráficos.

## Imagens de carta
Cada carta de exemplo tem um campo `imageUrl`. Use imagens placeholder
(retângulos com o código da coleção e o nome) — não tente buscar arte real.
O componente de imagem sempre respeita proporção 63/88, carrega com skeleton e
tem fallback próprio quando a imagem falha.

## Regras visuais não negociáveis
- Alta/baixa NUNCA é comunicada só por cor: sempre seta (▲/▼) + sinal (+/−).
- Nenhum gráfico com dois eixos Y.
- Todo gráfico tem uma alternativa em tabela acessível por um botão real.
- Toda tela tem os quatro estados: carregando (skeleton, nunca spinner de
  página inteira), vazio, erro (com "Tentar novamente") e sucesso. Como não há
  rede, exponha os estados via uma prop `state` nos componentes de tela, para
  que dê para visualizar cada um.
- Sem gradiente decorativo, sem glassmorphism, sem sombra colorida, sem
  animação em loop. A cor carrega significado, não enfeita.
```

---

## PROMPT 1 — Design system e shell

O prompt mais importante. Não corte nada.

```prompt
Construa a fundação visual do app "TCG Market Intelligence". Nesta etapa NÃO
construa as páginas de conteúdo: só o design system, o shell de navegação e os
componentes reutilizáveis.

## 1. Direção estética
Um terminal de mercado financeiro aplicado a cartas colecionáveis. Denso em
dados, calmo, silencioso. Bordas hairline de 1px em vez de sombra. Superfícies
chapadas. A hierarquia vem de tamanho e espaçamento, não de cor.

## 2. Tokens (CSS custom properties em src/index.css, mapeadas no tailwind.config.ts)
Dark é o tema padrão. Light existe e é uma versão selecionada, não uma inversão.

DARK:
  --bg-base        #0b0e11   plano da página
  --bg-surface     #12161b   cards, painéis, superfície dos gráficos
  --bg-surface-2   #171c22   hover, linha zebrada, campos
  --border         #232a32
  --border-strong  #2f3944
  --text-primary   #f2f5f8
  --text-secondary #9aa7b4
  --text-muted     #6b7684   eixos e labels de gráfico
  --grid           #1c2129   gridlines hairline
  --accent         #3987e5   série principal, links, anel de foco
  --up             #0ca30c
  --down           #d03b3b
  --flat           #6b7684
  --warning        #fab219

LIGHT:
  --bg-base #f7f8f9  --bg-surface #ffffff  --bg-surface-2 #f1f3f5
  --border #e3e6ea   --border-strong #cdd3da
  --text-primary #0b0e11  --text-secondary #525961  --text-muted #6b7684
  --grid #e9ecef  --accent #2a78d6  --up #0a7f0a  --down #c0392b
  --flat #6b7684  --warning #b07d00

## 3. Paleta de gráficos — fixa, nunca ciclar
  série 1   dark #3987e5   light #2a78d6
  série 2   dark #d95926   light #eb6834
  série 3   dark #199e70   light #1baf7a
Essa tripla foi validada para daltonismo contra a superfície #12161b. Não
troque as cores e não gere uma quarta: se precisar de mais uma série, ela vira
outro gráfico ou outra aba, não uma cor nova.

## 4. Tipografia e densidade
Inter (Google Fonts) para tudo. JetBrains Mono APENAS para códigos de coleção,
números de colecionador e ticks de eixo. Base 14px.
Linha de tabela 40px · padding de card 16px · raio 8px (12px em painéis
grandes) · borda 1px. Compacto, sem apertado.

## 5. Utilitários de formatação (src/lib/format.ts)
formatBRL, formatCompactBRL ("R$ 1,2 mil" / "R$ 3,4 mi"), formatPercent,
formatDate, formatRelativeTime, e deltaTone(v) devolvendo "up" | "down" | "flat"
(flat quando |v| < 0,05).

## 6. Shell (src/components/layout/)
Sidebar fixa de 240px, colapsável para 64px só-ícones, virando drawer abaixo de
1024px:
- Logo: monograma "TCG" numa caixa quadrada com borda accent, seguido do
  wordmark "Market Intelligence" em text-secondary
- Itens: Visão Geral (/), Mercado (/mercado), Cartas (/cartas),
  Minha Carteira (/carteira), Coleta (/coleta)
- Item ativo: barra accent de 2px à esquerda + fundo --bg-surface-2

Topbar de 56px:
- Busca global usando o componente Command do shadcn, atalho Ctrl/Cmd+K,
  buscando nas cartas de exemplo
- Indicador de frescor: bolinha de status + "Atualizado há 2 horas"
- Toggle de tema (sol/lua)

Rotas com react-router-dom, incluindo /cartas/:id. Cada rota renderiza por
enquanto um `<PageStub title="..." />`. Layout com Outlet, conteúdo com largura
máxima de 1440px e padding de 24px.

## 7. Componentes reutilizáveis (src/components/ui-ext/)
- StatTile — rótulo, valor grande (figuras proporcionais), delta opcional,
  sparkline opcional à direita, linha de contexto em text-muted, tooltip de ajuda
- DeltaBadge — recebe um número e renderiza "▲ +12,3%" / "▼ -5,7%" / "— 0,0%".
  Seta e sinal são obrigatórios; a cor é reforço, nunca o único canal.
- Sparkline — AreaChart do Recharts sem eixos e sem tooltip, traço de 2px,
  altura 32px, cor derivada do sinal da variação
- CardThumb — imagem com proporção 63/88, skeleton no carregamento, fallback
  próprio no erro, atributo loading="lazy"
- SetChip — código da coleção em mono, caixa alta, borda hairline
- PeriodTabs — grupo segmentado de períodos
- EmptyState, ErrorState (com botão de retry), TableSkeleton, ChartSkeleton
- DataTable — tabela base com header sticky, linhas zebradas, ordenação por
  coluna e slot para rodapé de totais

Crie também `src/data/sample.ts` com os dados de exemplo descritos no briefing.

Entregue o shell navegável, os stubs e uma rota /styleguide (não linkada na
sidebar) exibindo todos os tokens e componentes acima em ambos os temas.
```

---

## PROMPT 2 — Visão Geral

```prompt
Implemente a página "Visão Geral" na rota "/". NÃO altere o shell nem os
componentes já criados; reutilize-os.

Grid de 12 colunas, nesta ordem:

1) FAIXA DE KPIs — quatro StatTile lado a lado (2x2 no mobile):
   "Cartas monitoradas", "Observações de preço", "Preço médio do mercado" e
   "Valor da minha carteira". O último tem sublinha "X cartas · Y coleções".
   Cada tile traz, abaixo do valor, uma linha discreta de contexto em
   text-muted — por exemplo "janela: 20/08/2023 – 16/08/2026".

2) GRÁFICO PRINCIPAL — "Índice TCG-BR", ocupando 8 colunas.
   Curva de um índice de mercado em base 100, derivado da média das cartas mais
   valiosas dos dados de exemplo.
   - AreaChart do Recharts, gradiente vertical do accent de 18% para 0%
   - Linha de 2px na cor da série 1
   - Eixo Y à direita, gridlines só horizontais em --grid, sem gridline vertical
   - Crosshair vertical + tooltip com data por extenso, valor do índice e
     variação acumulada no período
   - PeriodTabs no header do card: 30d / 90d / 180d / 1a / 3a (padrão 90d)
   - Header também exibe o valor atual do índice e um DeltaBadge do período
   - Rótulo discreto no rodapé do card: "resolução semanal"
   - Estado vazio próprio quando a série do período não tiver pontos suficientes

3) COLUNA LATERAL (4 colunas), empilhada ao lado do gráfico:
   - "Saúde da coleta": status com ÍCONE + rótulo textual (nunca só cor),
     última coleta, próxima esperada, nº de cartas desatualizadas, nº de erros
     recentes. Quando o status for de erro, borda esquerda vermelha de 2px.
   - "Coleções em destaque": as 6 maiores, com barra horizontal proporcional
     em um único tom (opacidade variável, jamais arco-íris) e o código em mono.

4) MOVERS — dois painéis lado a lado, "Maiores altas" e "Maiores baixas",
   8 linhas cada. Cada linha: CardThumb de 32px, nome, SetChip, cotação à
   direita e DeltaBadge. Linha inteira clicável, levando a /cartas/:id.
   Hover em --bg-surface-2. PeriodTabs 7d / 30d / 90d no header, padrão 30d.
   Quando o período selecionado resultar em variação zero para todas as linhas,
   mostre um aviso inline explicando que a série é semanal e sugerindo 30d.

5) RODAPÉ — linha discreta: "Fonte: MYP Cards · Preços em BRL ·
   Resolução semanal · Últimos dados: 16/08/2026".

Cada seção tem seu próprio skeleton: a página nunca fica inteira em branco.
```

---

## PROMPT 3 — Cartas

```prompt
Implemente "/cartas" — um screener de cartas. Não altere as telas existentes.

Barra de filtros sticky no topo do conteúdo, em uma linha (quebra em duas no
tablet):
- Campo de busca por nome com ícone de lupa
- Select de coleção, exibindo "DMR — 30 cartas"
- Select de jogo
- Toggle de visualização Grade / Tabela, com a escolha persistida em localStorage
- Contador "N cartas" alinhado à direita

MODO GRADE — grid responsivo auto-fill minmax(180px, 1fr). Cada card: imagem em
proporção 63/88 com cantos de 8px, faixa inferior em gradiente escuro com o
nome sobreposto, e abaixo da imagem uma linha com SetChip + número do
colecionador à esquerda e cotação à direita. Hover: translateY(-2px) e borda
accent. Sem tilt, sem efeito 3D.

MODO TABELA — colunas: Carta (thumb de 28px + nome, com o nome em inglês em
text-muted quando diferente), Coleção, Nº, Cotação (tabular, alinhada à
direita) e Ações. Linhas de 40px, zebradas, header sticky, ordenação por nome
e por cotação com setas no header.

PAGINAÇÃO — controles "Anterior" / "Próxima" com o texto "Exibindo X–Y de N".
Seletor de itens por página: 24 / 48 / 96, padrão 24. Implemente a paginação
sobre o array de exemplo, mas mantenha o componente de paginação genérico e
controlado por props (página atual, total, callbacks) — a lógica real entra
depois.

Estados: skeleton no formato do modo ativo; estado vazio com sugestão de limpar
os filtros; estado de erro com retry.

Clicar em qualquer carta navega para /cartas/:id.
```

---

## PROMPT 4 — Detalhe da carta

```prompt
Implemente "/cartas/:id" — a tela mais importante do produto. Ela deve parecer
a página de um ativo numa corretora.

CABEÇALHO — grid de duas colunas (imagem de 280px | conteúdo):
- Esquerda: imagem grande com cantos de 12px e borda hairline. Abaixo dela,
  botão primário "Ver na loja" (com ícone de link externo) e botão secundário
  "Adicionar à carteira".
- Direita:
  - Breadcrumb: Cartas / DMR / Nome da carta
  - Nome em destaque; quando o nome em inglês for diferente, abaixo em
    text-secondary
  - Linha de chips: coleção, número do colecionador, jogo, fonte
  - COTAÇÃO: valor em 40px com figuras proporcionais, moeda em text-secondary,
    e ao lado o DeltaBadge com o texto "no período"
  - Grade de quatro mini-métricas: Máxima histórica (valor + data), Mínima
    histórica (valor + data), Volatilidade 30d (em %) e Momentum 7d
    (variação % + rótulo Alta / Baixa / Estável). Cada uma com tooltip
    explicando o cálculo em uma frase.

GRÁFICO DE HISTÓRICO — card de largura total:
- Header: PeriodTabs 30d / 90d / 180d / 1a / 3a (padrão 90d) à esquerda; à
  direita, checkboxes de série: "Cotação mediana" (série 1, sempre ativa),
  "Referência internacional" (série 2), "Última venda" (série 3)
- ComposedChart do Recharts, EIXO Y ÚNICO, altura de 380px
- Série 1 como área com gradiente e linha de 2px; séries 2 e 3 como linha de
  2px, sendo a 3 tracejada (4 2) para reforçar a identidade além da cor
- Marcadores de 8px apenas nos pontos de máxima e mínima do período, com label
  direto — nunca rotule todos os pontos
- Gridlines horizontais hairline; eixo X com ticks a cada ~6 semanas em DD/MM;
  eixo Y em R$ compacto
- Crosshair vertical + tooltip com a data, cada série ativa com seu quadradinho
  de cor, e a quantidade disponível quando houver
- Legenda sempre presente quando houver duas ou mais séries
- Brush do Recharts abaixo do gráfico quando o período for 1a ou 3a
- Botão "Gráfico / Tabela": a tabela lista data, cotação mediana, referência,
  última venda e quantidade — é o equivalente acessível e existe sempre
- Estado vazio dedicado: "Sem histórico de cotação para esta carta", com uma
  linha explicando que cartas com poucos vendedores podem não ter série

BLOCO "FONTES" — tabela pequena com origem, identificador, SKU e link.

BLOCO "CARTAS DA MESMA COLEÇÃO" — carrossel horizontal com 12 cartas,
reaproveitando o card de grade da tela anterior.

RODAPÉ — "Primeira observação em 20/08/2023 · Atualizado em 16/08/2026".
```

---

## PROMPT 5 — Mercado

```prompt
Implemente "/mercado" — a visão agregada do mercado.

1) PeriodTabs 7d / 30d / 90d no topo (padrão 30d), controlando a página inteira.

2) Faixa de quatro StatTile: cartas em alta, cartas em baixa, maior alta do
   período (nome + %), maior baixa do período (nome + %).

3) DUAS TABELAS COMPLETAS lado a lado — "Maiores altas" e "Maiores baixas",
   50 linhas cada, empilhando no mobile. Colunas: #, Carta (thumb + nome),
   Coleção, Cotação inicial, Cotação atual, Variação (DeltaBadge) e Sparkline
   do período. Header sticky, linhas de 44px, ordenação por qualquer coluna
   numérica, clique navega para o detalhe.

4) PAINEL "Distribuição de cotações" — histograma (BarChart) por faixa:
   R$ 0–5, 5–15, 15–50, 50–150, 150–500, 500+. Barras finas com topo
   arredondado de 4px, gap de 2px entre elas, uma cor só (accent), rótulo
   direto no topo de cada barra. Eixo Y = número de cartas.

5) PAINEL "Cobertura por coleção" — tabela com código em mono, nome legível,
   número de cartas e barra proporcional. Ordenável.

Cada painel tem no header um botão discreto "Exportar CSV" que baixa o conteúdo
da tabela gerado no client.
```

---

## PROMPT 6 — Minha Carteira

```prompt
Implemente "/carteira" — a coleção do usuário tratada como portfólio.

CABEÇALHO DE PORTFÓLIO — quatro StatTile:
- "Valor total da carteira", com o valor em 40px
- "Cartas únicas"
- "Total de cartas"
- "Cobertura de cotação": percentual com barra de progresso e tooltip
  explicando que só cartas com cotação conhecida entram no valor total
Abaixo, alerta inline em âmbar quando a cobertura for menor que 80%:
"X cartas ainda não têm cotação — o valor total está subestimado."

CONTROLES: busca por nome, select de coleção exibindo
"DMR — Dominaria Remastered (30)", toggle Grade / Tabela, e botão
"Importar coleção" que abre um diálogo de upload de CSV. O diálogo é só
interface: área de arrastar-e-soltar, estado de processando, e uma tela de
resultado mostrando "N importadas, N vinculadas, N ignoradas de N linhas".

MODO GRADE: cards com imagem, selo de quantidade no canto superior direito
("x3"), nome, chips de qualidade (NM/SP/MP) e idioma (PT/EN), cotação unitária
e valor da linha (cotação × quantidade) em destaque.

MODO TABELA: Carta, Coleção, Nº, Qtd, Qualidade, Idioma, Raridade, Cotação
unitária e Valor total (tabular, à direita), com linha de TOTAIS fixa no rodapé
da tabela. Ordenável por valor total — é o uso real da tela.

PAINÉIS ANALÍTICOS, duas colunas:
- "Concentração por coleção": BarChart horizontal das 8 coleções de maior valor
  acumulado, cor única, rótulo de valor na ponta de cada barra.
- "Composição por raridade": nada de pizza. Use uma única barra empilhada
  horizontal de 100%, com gap de 2px entre segmentos e legenda embaixo com
  valor e percentual. Mais de 5 raridades: agrupe o excedente em "Outras".

Cartas sem cotação aparecem com 60% de opacidade e um ícone de alerta com
tooltip "sem cotação disponível".
```

---

## PROMPT 7 — Coleta

```prompt
Implemente "/coleta" — painel operacional, só interface.

- Card grande de status: ícone + rótulo textual (Saudável / Desatualizado /
  Com erros), borda esquerda de 2px na cor do status, e quatro métricas:
  última coleta (data + "há X"), próxima esperada, cartas desatualizadas sobre
  o total, e erros recentes.
- Timeline vertical das últimas execuções, com horário, duração, número de
  cartas processadas e resultado. Inclua uma execução com falha para que o
  estado de erro apareça.
- Bloco "Disparar coleta": dois formulários lado a lado, "Backfill" e
  "Atualização". Backfill tem select de coleção, campo de limite opcional e
  campo de profundidade do histórico em dias (padrão 1095). Ambos têm um campo
  de chave de acesso do tipo senha no topo do bloco, com os botões desabilitados
  e tooltip explicativo enquanto ele estiver vazio. Ao enviar, mostre um toast
  informando que a execução é assíncrona.
- Bloco "Ambiente": lista de leitura com o endereço do serviço, versão e último
  healthcheck, mais um botão "Testar conexão" com estados de carregando,
  sucesso e falha.
```

---

## PROMPT 8 — Polimento

```prompt
Passe de polimento em todo o app. Não adicione telas nem funcionalidades novas.

1) MOVIMENTO: 150ms ease-out em hover e foco. Entrada de página com fade e
   slide de 8px. Valores de KPI com contagem crescente de 600ms na primeira
   renderização. Tudo respeitando prefers-reduced-motion. Nenhuma animação
   em loop.

2) ACESSIBILIDADE:
   - Anel de foco visível de 2px em accent em todo elemento interativo
   - Toda tabela com <caption> sr-only e escopo de header correto
   - Todo gráfico com aria-label descritivo e alternativa em tabela alcançável
     por um botão com texto, não só ícone
   - text-secondary sobre --bg-surface precisa passar 4.5:1 nos dois temas
   - Navegação completa por teclado, incluindo o Command palette

3) RESPONSIVO: valide em 390px, 768px, 1280px e 1920px. Sidebar vira drawer
   abaixo de 1024px. Abaixo de 768px, tabelas viram lista de cards — não use
   scroll horizontal. Gráficos com altura mínima de 240px.

4) ESTADOS: confirme que toda seção tem skeleton, vazio e erro com retry, e que
   dá para visualizar cada um pela prop `state`.

5) META: título dinâmico por rota ("Ilha · DMR — TCG Market Intelligence"),
   favicon com o monograma TCG, meta description.

6) Rode a verificação de TypeScript e corrija tudo. Zero `any`.

7) README.md curto: como rodar, onde ficam os dados de exemplo
   (src/data/sample.ts) e o mapa de componentes por tela.
```

---

## Anexo A — Checklist de aceite visual

- [ ] `/styleguide` mostra todos os tokens e componentes nos dois temas
- [ ] Alta/baixa sempre com seta + sinal, nunca só cor
- [ ] Nenhum gráfico com dois eixos Y
- [ ] Todo gráfico tem alternativa em tabela
- [ ] Valor ausente exibe "—", nunca "R$ null"
- [ ] Cartas sem histórico mostram o estado vazio do gráfico
- [ ] Movers em 7d zerados exibem o aviso de resolução semanal
- [ ] Nenhum componente de tela lê `sample.ts` direto — tudo por props
- [ ] `tsc --noEmit` limpo, zero `any`
- [ ] 390px e 1920px sem overflow horizontal

---

## Anexo B — Erros comuns do Lovable

| Sintoma | Causa | Como evitar |
|---|---|---|
| Inventa Supabase e login | "usuário", "salvar", "importar" sem contexto | Reforce: "apenas interface, sem backend, sem Supabase" |
| Usa outra lib de gráfico | Não repetiu Recharts | Escreva "Recharts" em todo prompt que tenha gráfico |
| Refaz telas prontas | Prompt amplo demais | Comece com "não altere as telas existentes; implemente apenas X" |
| Perde os tokens de cor | Pedido visual genérico depois | Diga "usando os tokens já definidos em index.css" |
| Gráficos viram arco-íris | Default do Recharts | Reforce a paleta fixa de 3 séries do Prompt 1 |
| Espalha dado mockado nos componentes | Não reforçou o contrato de props | Repita a regra de arquitetura da Parte 0 no prompt |

---

## Anexo C — O que fazemos depois, aqui dentro

Fora do escopo do Lovable, para resolvermos no repositório:

1. Substituir `src/data/sample.ts` pela camada de dados real, mantendo as mesmas
   formas de props — é por isso que a regra de arquitetura da Parte 0 existe.
2. Definir como o app fala com a API (proxy do Vite ou base URL por env).
3. Cache e revalidação (react-query ou o que decidirmos).
4. Reconciliar versões: o `frontend/` atual está em React 19 e React Router 7,
   o Lovable gera React 18 e Router 6.
5. Portar os testes de componente que ainda fizerem sentido antes de aposentar
   o `frontend/` antigo.
6. Seguindo o CLAUDE.md: isso vira uma feature (F10 — Front-end v2), com PRD em
   `docs/prd/`, dois diagramas Mermaid em `docs/diagrams/` e nota no README.
