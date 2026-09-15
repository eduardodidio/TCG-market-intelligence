# T06 -- Frontend Error Code Handling

**Wave:** 2
**Depends on:** T04 (error codes applied to backend)
**Estimated effort:** small

## User Story

As a user, I want to see clear, localized error messages when something
goes wrong (e.g., "Incorrect password" instead of a generic "Request
failed") so that I know exactly what to fix.

## What to Build

### 1. Error code mapping utility

Create `frontend/src/utils/errorCodes.ts`:

```typescript
export const ERROR_MESSAGES: Record<string, { en: string; "pt-BR": string }> = {
  AUTH_INVALID_CREDENTIALS: {
    en: "Invalid email or password.",
    "pt-BR": "Email ou senha invalidos.",
  },
  AUTH_TOKEN_EXPIRED: {
    en: "Your session has expired. Please log in again.",
    "pt-BR": "Sua sessao expirou. Faca login novamente.",
  },
  AUTH_TOKEN_INVALID: {
    en: "Invalid authentication token.",
    "pt-BR": "Token de autenticacao invalido.",
  },
  AUTH_ACCOUNT_INACTIVE: {
    en: "This account has been deactivated.",
    "pt-BR": "Esta conta foi desativada.",
  },
  AUTH_EMAIL_TAKEN: {
    en: "This email is already registered.",
    "pt-BR": "Este email ja esta registrado.",
  },
  AUTH_PASSWORD_MISMATCH: {
    en: "Current password is incorrect.",
    "pt-BR": "A senha atual esta incorreta.",
  },
  CREDIT_INSUFFICIENT: {
    en: "Not enough credits for this action.",
    "pt-BR": "Creditos insuficientes para esta acao.",
  },
  RESOURCE_NOT_FOUND: {
    en: "The requested resource was not found.",
    "pt-BR": "O recurso solicitado nao foi encontrado.",
  },
  AUTHZ_FORBIDDEN: {
    en: "You don't have permission for this action.",
    "pt-BR": "Voce nao tem permissao para esta acao.",
  },
  EXTERNAL_TIMEOUT: {
    en: "The external service timed out. Please try again.",
    "pt-BR": "O servico externo expirou. Tente novamente.",
  },
  EXTERNAL_FAILURE: {
    en: "An external service error occurred. Please try again.",
    "pt-BR": "Ocorreu um erro no servico externo. Tente novamente.",
  },
  INTERNAL_ERROR: {
    en: "An unexpected error occurred. Please try again later.",
    "pt-BR": "Ocorreu um erro inesperado. Tente novamente mais tarde.",
  },
};

export function getErrorMessage(
  code: string,
  language: string,
  fallbackMessage?: string,
): string {
  const entry = ERROR_MESSAGES[code];
  if (entry) {
    return entry[language as keyof typeof entry] || entry.en;
  }
  return fallbackMessage || code;
}
```

### 2. Update AuthContext

In `frontend/src/contexts/AuthContext.tsx`, update error handling in
`login()`, `register()`, and `changePassword()` to use `getErrorMessage`:

```typescript
if (resp.errors.length > 0) {
  const err = resp.errors[0];
  const msg = getErrorMessage(err.code, language, err.message);
  setError(msg);
  return;
}
```

### 3. Add i18n keys (optional, if using i18n system instead)

If the project prefers using the existing i18n system (`en.json`,
`pt-BR.json`) instead of the inline mapping, add the error messages
under an `errors` namespace:

```json
{
  "errors": {
    "AUTH_INVALID_CREDENTIALS": "Invalid email or password.",
    "AUTH_TOKEN_EXPIRED": "Your session has expired. Please log in again.",
    ...
  }
}
```

Choose whichever approach is more consistent with the existing codebase.
The inline mapping is self-contained; the i18n approach integrates with
`useTranslation()`.

### 4. Auto-logout on AUTH_TOKEN_EXPIRED

In the API client or AuthContext, detect `AUTH_TOKEN_EXPIRED` or
`AUTH_TOKEN_INVALID` error codes and trigger automatic logout + redirect
to login page. This replaces any current handling that checks HTTP status
codes.

## Dev Notes

- The `ApiError` type in `frontend/src/types/api.ts` already has a `code`
  field -- no type changes needed.
- Currently `AuthContext.tsx` reads `resp.errors[0].message` as a raw
  string. After this change, it will prefer the localized message from
  the error code map, falling back to the server message.
- Do NOT change the API response shape. The frontend just interprets the
  existing `code` field differently.

## Testing

Create `frontend/src/utils/__tests__/errorCodes.test.ts`:

1. Test `getErrorMessage` returns English message for known code.
2. Test `getErrorMessage` returns pt-BR message when language is "pt-BR".
3. Test `getErrorMessage` returns fallback message for unknown code.
4. Test `getErrorMessage` returns code string when no fallback provided.

Update `frontend/src/contexts/__tests__/AuthContext.test.tsx`:

5. Test that login error displays localized message based on error code.
6. Test that AUTH_TOKEN_EXPIRED triggers logout.

Expected: ~8-10 tests.
