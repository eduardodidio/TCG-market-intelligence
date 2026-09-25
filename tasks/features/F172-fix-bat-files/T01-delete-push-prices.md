# T01 — Delete deprecated push-prices.bat

**Wave:** 0
**Status:** planned

## User Story

As a developer, I want `push-prices.bat` removed from the repo so that a hardcoded API key is no longer checked into version control.

## Context

`push-prices.bat` at the repo root:
- Is self-declared as DEPRECATED (line 3: "DEPRECADO").
- Contains a hardcoded API key on line 12: `SET TCG_API_KEY=nr4g916Y_hjMfSBfG6_lcGcsCq7rQm1bHzHfM32tdcU`.
- References the `push-prices` CLI command which is no longer needed (Neon direct write replaced it).
- The file already prints a deprecation warning telling users to use `push-all.bat` instead.

## Dev Notes

1. `git rm push-prices.bat` (stage the deletion).
2. Verify no other file references `push-prices.bat` (grep the codebase).
3. If `setup-schedule.bat` references it, that will be fixed in T03.

## Testing

- Confirm file no longer exists after the change.
- `grep -r "push-prices.bat"` returns no hits (except possibly T03 cleanup or git history).
