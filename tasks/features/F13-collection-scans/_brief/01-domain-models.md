# F13 -- Domain Models

## ScanStatus (Enum)

```python
class ScanStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
```

## ScanType (Enum)

```python
class ScanType(str, Enum):
    COLLECTION = "collection"      # all linked collection cards
    SET = "set"                    # cards from a specific set
    FORMAT = "format"              # cards legal in a format (standard, modern, etc.)
    CUSTOM = "custom"              # explicit list of card IDs
```

## ScanFilter (dataclass)

```python
@dataclass
class ScanFilter:
    scan_type: ScanType
    set_codes: list[str] | None = None       # for SET scans
    format_name: str | None = None           # for FORMAT scans
    rarities: list[str] | None = None        # optional filter
    card_ids: list[int] | None = None        # for CUSTOM scans
    collection_only: bool = True             # restrict to user_collection
    limit: int | None = None
```

## ScanRun (dataclass)

```python
@dataclass
class ScanRun:
    id: int | None = None
    scan_type: str = "collection"
    filters_json: str = "{}"                 # serialized ScanFilter
    status: str = "pending"
    cards_total: int = 0
    cards_processed: int = 0
    cards_failed: int = 0
    observations_saved: int = 0
    error_summary: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
```

These models go in `src/domain/models.py`, following the existing pattern of
pure dataclasses with no external dependencies.
