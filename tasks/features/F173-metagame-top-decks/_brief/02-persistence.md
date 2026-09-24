# 02 — Persistência

## Decisão: arquivos NOVOS, sem tocar `src/database/models.py` nem `repository.py`
`models.py` (666 linhas) e `repository.py` (5k+ linhas) são arquivos de alto conflito
no lote F171–F179. As tabelas novas vivem em `src/metagame/models.py` usando o MESMO
`Base` (`from src.database.models import Base`), e `MetagameRepository` garante a
criação delas com `Base.metadata.create_all(engine, tables=[...])` no `__init__`
(idempotente; funciona em SQLite e Neon PostgreSQL). Nenhuma migração/compat extra.

## Tabelas — `src/metagame/models.py` (T03)
```python
class MetaDeckRow(Base):
    __tablename__ = "meta_decks"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    format: Mapped[str] = mapped_column(String(20), nullable=False)
    source: Mapped[str] = mapped_column(String(30), nullable=False)
    external_id: Mapped[str] = mapped_column(String(200), nullable=False)
    archetype: Mapped[str] = mapped_column(String(200), nullable=False)
    commander_name: Mapped[str | None] = mapped_column(String(300))
    colors: Mapped[str | None] = mapped_column(String(10))
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    meta_share_pct: Mapped[Decimal | None] = mapped_column(Numeric(6, 3))
    deck_count: Mapped[int | None] = mapped_column(Integer)
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    event_date: Mapped[date | None] = mapped_column(Date)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    __table_args__ = (
        UniqueConstraint("source", "format", "external_id", "snapshot_date", name="uq_meta_deck_snapshot"),
        Index("ix_meta_decks_fmt_snap_rank", "format", "snapshot_date", "rank"),
    )

class MetaDeckCardRow(Base):
    __tablename__ = "meta_deck_cards"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    meta_deck_id: Mapped[int] = mapped_column(Integer, ForeignKey("meta_decks.id", ondelete="CASCADE"), nullable=False)
    card_name: Mapped[str] = mapped_column(String(300), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    board: Mapped[str] = mapped_column(String(10), nullable=False, default="main")
    card_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("cards.id", ondelete="SET NULL"))
    __table_args__ = (Index("ix_meta_deck_cards_deck", "meta_deck_id"), Index("ix_meta_deck_cards_card", "card_id"))
```

## Repository — `src/metagame/repository.py` (T03)
```python
class MetagameRepository:
    def __init__(self, engine: Engine): ...           # create_all(tables=[MetaDeckRow.__table__, MetaDeckCardRow.__table__])
    @classmethod
    def from_repo(cls, repo: Repository) -> "MetagameRepository": return cls(repo.engine)
    def replace_snapshot(self, fmt, source, snapshot_date, decks: list[MetaDeckEntry], card_ids: dict[tuple[str,str], int|None]) -> int
        # apaga (fmt, source, snapshot_date) e insere tudo numa transação; retorna nº de decks
    def latest_snapshot_date(self, fmt: str) -> date | None
    def list_decks(self, fmt: str, *, snapshot_date: date | None = None, limit=20, offset=0) -> tuple[list[MetaDeckRow], int]
        # default = snapshot mais recente do formato; ordena por rank asc
    def get_deck(self, deck_id: int) -> MetaDeckRow | None
    def get_deck_cards(self, deck_ids: list[int]) -> dict[int, list[MetaDeckCardRow]]   # batch, evita N+1 (Neon)
    def list_formats(self) -> list[dict]   # [{format, latest_snapshot_date, deck_count}]
    def resolve_card_id(self, name: str, set_code: str | None = None, collector_number: str | None = None) -> int | None
        # reusa src.decks.importer._find_card_id(session, ...); fallback: split-card "A // B" → tenta face "A"
    def owned_quantities(self, user_id: str, card_ids: list[int]) -> dict[int, int]
        # SUM(user_collection.quantity) GROUP BY card_id WHERE user_id=… AND card_id IN (…)
```
- Sessões: `with Session(self.engine) as s:` (mesmo padrão de `src/decks/importer.py`).
- Datas ISO nas respostas; `Decimal` para dinheiro.
- Cache de resolução nome→id em memória dentro de uma coleta (dict) para não repetir
  query de "Sol Ring" 50 vezes.
