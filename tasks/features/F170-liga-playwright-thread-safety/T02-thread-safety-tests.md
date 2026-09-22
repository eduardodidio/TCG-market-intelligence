# T02 -- Unit tests for thread safety and browser recovery

**Status:** planned
**Wave:** 1 (depends on T01)

## User Story

As a developer, I want unit tests that verify the thread-safety fix and
browser recovery behavior, so that regressions are caught automatically.

## Dev Notes

**New file:** `tests/providers/test_liga_provider_thread_safety.py`

Follow the existing test style in `tests/providers/test_liga_provider.py`
(mock-based, no real browser needed).

### Test cases to implement

#### 1. `test_init_creates_single_thread_executor`

Instantiate `LigaMagicProvider()` and assert:
- `provider._executor` is a `ThreadPoolExecutor`
- `provider._executor._max_workers == 1`

#### 2. `test_no_asyncio_to_thread_calls`

Static analysis test: read `src/providers/liga/provider.py` source and
assert that `asyncio.to_thread` does NOT appear in the file (except
possibly in comments). Use `inspect.getsource()` or `Path.read_text()`.

#### 3. `test_open_uses_executor`

Mock `asyncio.get_running_loop()` to return a mock loop. Call
`provider.open()` on a provider with `sys.platform` patched to `"win32"`.
Assert that `loop.run_in_executor` was called with
`(provider._executor, provider._open_sync)`.

#### 4. `test_close_uses_executor_and_shuts_down`

Similar to above: mock the loop, call `provider.close()` (with
`_use_sync=True`), assert `run_in_executor` was called with `_close_sync`.
Assert `provider._executor.shutdown` was called.

#### 5. `test_reset_browser_recovers_page`

Set up a provider with `_use_sync=True`. Mock `_reset_browser_sync` and
`_open_sync`. Call `await provider._reset_browser()`. Assert both
`_reset_browser_sync` and `_open_sync` were called (recovery happened).

#### 6. `test_reset_browser_recovery_failure_logged`

Same as above but `_open_sync` raises an exception. Assert recovery failure
is logged (not raised) -- the reset itself should not fail.

#### 7. `test_fetch_page_sync_recovers_when_page_none`

Instantiate provider, set `_sync_page = None`, mock `_open_sync` to set
`_sync_page` to a mock page that returns valid HTML. Call
`_fetch_page_sync(url)` directly. Assert `_open_sync` was called and HTML
was returned.

#### 8. `test_fetch_page_sync_raises_when_recovery_fails`

Set `_sync_page = None`, mock `_open_sync` to raise. Call
`_fetch_page_sync(url)`. Assert `LigaError` is raised with message
containing "recovery failed".

### Patterns

- Use `pytest.mark.asyncio` for async tests.
- Use `unittest.mock.patch` and `unittest.mock.AsyncMock` for mocking.
- Use `unittest.mock.MagicMock` for sync mocks.
- Keep tests isolated -- no real Playwright dependency.

## Testing

- Run: `pytest tests/providers/test_liga_provider_thread_safety.py -v`
- Run: `pytest tests/providers/test_liga_provider.py -v` (existing tests still pass)
- Run: `ruff check tests/providers/test_liga_provider_thread_safety.py`
