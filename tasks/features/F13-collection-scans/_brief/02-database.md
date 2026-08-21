# F13 -- Database Layer

## New Table: `scan_runs`

```python
class ScanRunRow(Base):
    __tablename__ = "scan_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    scan_type: Mapped[str] = mapped_column(String(50), nullable=False)
    filters_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    cards_total: Mapped[int] = mapped_column(Integer, default=0)
    cards_processed: Mapped[int] = mapped_column(Integer, default=0)
    cards_failed: Mapped[int] = mapped_column(Integer, default=0)
    observations_saved: Mapped[int] = mapped_column(Integer, default=0)
    error_summary: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    __table_args__ = (
        Index("ix_scan_runs_status", "status"),
        Index("ix_scan_runs_type_date", "scan_type", "created_at"),
    )
```

## Repository Methods

Add to `src/database/repository.py`:

- `create_scan_run(scan_type, filters_json) -> int` -- insert, return id
- `update_scan_run(run_id, **fields)` -- partial update (status, counts, timestamps)
- `get_scan_run(run_id) -> dict | None`
- `list_scan_runs(limit=20, offset=0, scan_type=None, status=None) -> list[dict]`
- `get_cards_for_scan(scan_filter: ScanFilter) -> list[dict]` -- unified card
  query that applies filters (set_code, format, rarity, card_ids, collection_only)

The `get_cards_for_scan` method is the key new query. It must join
`user_collection` + `source_cards` to produce a list of
`{external_id, slug, card_id, set_code, name_en}` entries matching the filter.
