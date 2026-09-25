# T03 — Rewrite setup-schedule.bat with correct paths and all schedules

**Wave:** 0
**Status:** planned

## User Story

As an operator, I want `setup-schedule.bat` to register Windows Task Scheduler entries for all 7 operational bats in `bats/`, with correct paths, so that daily automation works without manual intervention.

## Context

Current `setup-schedule.bat` has two problems:
1. **Wrong paths** — references `C:\Workspace\TCG-market-intelligence\daily-scan.bat` (root) instead of `C:\Workspace\TCG-market-intelligence\bats\daily-scan.bat`.
2. **Missing schedules** — only schedules 3 tasks (DailyScan, ProcessQueue x2) but there are now 7 bats: daily-scan, process-queue, banlist-sync, collect-metagame, daily-snapshot, deck-suggestions, fetch-news (plus push-all which is manual-only).

## Dev Notes

1. Use `%~dp0bats\<name>.bat` for all paths (setup-schedule.bat stays at root level so `%~dp0` resolves to the repo root). This makes paths relative to the script location rather than hardcoded.
2. Delete all old task names before recreating (already done for the 3 existing ones; add deletes for new names too).
3. Proposed schedule:

| Task Name | Bat File | Time | Frequency |
|-----------|----------|------|-----------|
| TEDHC_DailyScan | bats\daily-scan.bat | 09:00 | daily |
| TEDHC_ProcessQueue_14h | bats\process-queue.bat | 14:00 | daily |
| TEDHC_ProcessQueue_17h | bats\process-queue.bat | 17:00 | daily |
| TEDHC_DailySnapshot | bats\daily-snapshot.bat | 23:30 | daily |
| TEDHC_BanlistSync | bats\banlist-sync.bat | 06:00 | weekly (Monday) |
| TEDHC_CollectMetagame | bats\collect-metagame.bat | 06:30 | weekly (Monday) |
| TEDHC_DeckSuggestions | bats\deck-suggestions.bat | 03:00 | daily |
| TEDHC_FetchNews | bats\fetch-news.bat | 08:00 | daily |

4. `push-all.bat` is NOT scheduled (manual-only, user double-clicks when needed).
5. Update the summary echo block at the end to list all 8 scheduled tasks.
6. Remove any references to `TEDHC_PushAll` scheduled task (it was deleted in old version but never created; clean up the delete line).

## Testing

- Run `setup-schedule.bat` as admin; verify all 8 tasks appear in Task Scheduler.
- Verify each `/tr` path points to `bats\<name>.bat` using `%~dp0bats\` prefix.
- Verify weekly tasks use `/sc weekly /d MON`.
- Grep the file for any hardcoded `C:\Workspace` paths — should use `%~dp0` instead.
