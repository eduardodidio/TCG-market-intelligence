# 01 — Fontes, coleta educada e adapters

## Hipótese inicial (a ser validada pelo SPIKE T01)
| Formato | Fonte candidata #1 | Alternativas | Observação |
|---|---|---|---|
| Commander | EDHREC (JSON público `json.edhrec.com/pages/...`: top commanders + "average deck") | Moxfield/Archidekt (API não oficial), MTGTop8 `f=EDH`/`cEDH` | Commander não tem "meta share" de torneio: rank = popularidade (nº de decks) |
| Standard, Pioneer, Modern, Legacy, Vintage, Pauper | MTGTop8 (`mtgtop8.com/format?f=ST|PI|MO|LE|VI|PAU`, export de decklist em texto) | MTGGoldfish `/metagame/<fmt>/full`, mtgdecks.net | Meta share % disponível na página de formato |

O SPIKE deve, para cada candidata: ler `robots.txt` e ToS, verificar se a URL alvo
é permitida, se há API/export oficial, formato do dado (HTML/JSON/texto), campos
disponíveis (arquétipo, %, rank, decklist, data), estabilidade, e custo em requests
por coleta. **Se o ToS proibir coleta automatizada, a fonte é descartada** mesmo que
robots permita. Registrar tudo no ADR (`docs/adr/<próximo nº>-metagame-deck-sources.md`).

Saída extra do SPIKE: **fixtures reais** (1 página de meta + 1 decklist por fonte
escolhida) salvas em `tests/fixtures/metagame/<source>/` para que os adapters sejam
testados sem rede. Se a rede do ambiente estiver bloqueada, o SPIKE escreve fixtures
sintéticas fiéis à estrutura documentada e marca no ADR "fixtures sintéticas — revalidar".

## Camada HTTP educada — `src/metagame/http.py` (T04)
```python
class PoliteFetcher:
    def __init__(self, *, cache_dir: Path = Path("data/cache/metagame"),
                 ttl_hours: int = 24, min_interval_s: float = 3.0,
                 user_agent: str = "TEDHC-Market/1.0 (+https://github.com/eduardodidio/TCG-market-intelligence)",
                 client: httpx.Client | None = None, clock=time.monotonic, sleep=time.sleep): ...
    def get_text(self, url: str, *, ttl_hours: int | None = None) -> str: ...
    def get_json(self, url: str, *, ttl_hours: int | None = None) -> dict | list: ...
class RobotsDisallowed(Exception): ...
class FetchError(Exception): ...
```
- robots.txt por host via `urllib.robotparser.RobotFileParser`, cacheado em memória;
  respeitar `Crawl-delay` se maior que `min_interval_s`. URL proibida → `RobotsDisallowed`.
- Rate limit por host (intervalo mínimo entre requests; `clock`/`sleep` injetáveis p/ teste).
- Cache em disco: chave = sha256(url); arquivo `<hash>.body` + `<hash>.meta.json`
  (`url`, `fetched_at`, `status`). Hit dentro do TTL → não faz request.
- Retry com `tenacity` (3 tentativas, backoff exponencial) apenas p/ 429/5xx/timeout.
  429 honra `Retry-After`.
- `data/cache/` NÃO está no `.gitignore` hoje; T15 adiciona. Até lá, não commitar nada de `data/cache/`.

## Protocol de fonte — `src/metagame/sources/base.py` (T04)
```python
FORMATS = ("commander", "standard", "pioneer", "modern", "legacy", "vintage", "pauper")

@dataclass(frozen=True)
class MetaCardEntry:
    name: str; quantity: int; board: Literal["main", "side", "commander"] = "main"
    set_code: str | None = None; collector_number: str | None = None

@dataclass(frozen=True)
class MetaDeckEntry:
    source: str; format: str; external_id: str; archetype: str; rank: int
    meta_share_pct: Decimal | None; deck_count: int | None; colors: str | None
    commander_name: str | None; source_url: str; event_date: date | None
    cards: tuple[MetaCardEntry, ...]

class MetaSource(Protocol):
    name: str
    formats: tuple[str, ...]
    def fetch_top_decks(self, fmt: str, *, limit: int = 20) -> list[MetaDeckEntry]: ...
```
Adapters recebem um `PoliteFetcher` no construtor (injeção → testes usam fake fetcher
que devolve fixtures). Parsing de HTML com `BeautifulSoup(html, "html.parser")`.
Parsers devem ser resilientes (lição F11): tolerar campos ausentes, logar
`structlog` warning e pular o deck em vez de abortar o formato inteiro.

## Adapters (T07, T08)
- `src/metagame/sources/edhrec.py` → `EdhrecSource` (formats=("commander",)).
- `src/metagame/sources/<constructed>.py` → default `mtgtop8.py` / `Mtgtop8Source`
  (formats = construídos). **O nome/fonte final vem do ADR**; se o ADR escolher outra
  fonte, T08 implementa aquela com a mesma interface.
- Registry: `src/metagame/sources/__init__.py` expõe
  `def get_sources(fetcher) -> dict[str, MetaSource]` e `SOURCE_FOR_FORMAT: dict[str,str]`.
  **T04 cria o arquivo com o registry vazio + TODO; T12 (CLI) popula** — T07/T08 não
  editam `__init__.py` (evita conflito entre elas).

## Collector service — `src/metagame/collector.py` (T09)
```python
@dataclass
class CollectStats: formats: int = 0; decks: int = 0; cards: int = 0; unresolved_cards: int = 0; errors: list[str] = field(default_factory=list)
def collect_metagame(repo: MetagameRepository, sources: dict[str, MetaSource],
                     formats: list[str], *, limit: int = 20, snapshot_date: date | None = None,
                     dry_run: bool = False, resolver: Callable[[MetaCardEntry], int | None] | None = None) -> CollectStats
```
- Para cada formato: escolhe a fonte via `SOURCE_FOR_FORMAT` (ou `sources` passado),
  chama `fetch_top_decks`, resolve cada carta com `resolver` (default:
  `repo.resolve_card_id`), e `repo.replace_snapshot(fmt, source, snapshot_date, decks)`.
- Erro em um formato não aborta os outros (vai para `stats.errors`).
- Idempotente: rodar 2x no mesmo dia substitui o snapshot daquele (formato, fonte, dia).

## CLI + .bat (T12)
- Novo módulo `src/cli/metagame.py` com `@click.command("collect-metagame")`:
  `--format/-f` (multiple; default todos), `--limit` (default 20),
  `--dry-run`, `--db` (mesmo padrão dos outros comandos: default `get_db_url()`),
  `--no-cache`. Imprime `CollectStats` em tabela simples; exit code 1 se todos
  os formatos falharem.
- Registro em `src/cli/main.py` feito SÓ em T15 (1 linha `cli.add_command(...)`).
- `bats/collect-metagame.bat` (novo arquivo, padrão de `bats/process-queue.bat`):
  `python -m src.cli.main collect-metagame --limit 20`. Comentário no topo:
  "Agendar semanalmente (Task Scheduler, segunda 06:00); diário opcional".
