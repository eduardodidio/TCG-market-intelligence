/**
 * Machine-readable error codes matching the backend ErrorCode constants.
 *
 * These codes are returned in the `errors[].code` field of the API envelope.
 * The `getErrorMessage()` helper maps them to user-friendly i18n keys.
 */

// Authentication
export const AUTH_INVALID_CREDENTIALS = "AUTH_INVALID_CREDENTIALS";
export const AUTH_TOKEN_EXPIRED = "AUTH_TOKEN_EXPIRED";
export const AUTH_TOKEN_INVALID = "AUTH_TOKEN_INVALID";
export const AUTH_ACCOUNT_INACTIVE = "AUTH_ACCOUNT_INACTIVE";
export const AUTH_EMAIL_TAKEN = "AUTH_EMAIL_TAKEN";
export const AUTH_PASSWORD_EXPIRED = "AUTH_PASSWORD_EXPIRED";
export const AUTH_PASSWORD_MISMATCH = "AUTH_PASSWORD_MISMATCH";
export const AUTH_PASSWORD_UNAVAILABLE = "AUTH_PASSWORD_UNAVAILABLE";
export const AUTH_OAUTH_NOT_CONFIGURED = "AUTH_OAUTH_NOT_CONFIGURED";
export const AUTH_OAUTH_NOT_IMPLEMENTED = "AUTH_OAUTH_NOT_IMPLEMENTED";
export const AUTH_MISSING_AUTH_CODE = "AUTH_MISSING_AUTH_CODE";

// Authorization
export const AUTHZ_ADMIN_REQUIRED = "AUTHZ_ADMIN_REQUIRED";
export const AUTHZ_FORBIDDEN = "AUTHZ_FORBIDDEN";
export const AUTHZ_API_KEY_INVALID = "AUTHZ_API_KEY_INVALID";

// Credits
export const CREDIT_INSUFFICIENT = "CREDIT_INSUFFICIENT";

// Resources
export const RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND";
export const RESOURCE_CONFLICT = "RESOURCE_CONFLICT";
export const RESOURCE_GONE = "RESOURCE_GONE";

// Validation
export const VALIDATION_ERROR = "VALIDATION_ERROR";
export const VALIDATION_EMPTY_UPDATE = "VALIDATION_EMPTY_UPDATE";
export const VALIDATION_LIMIT_EXCEEDED = "VALIDATION_LIMIT_EXCEEDED";

// External services
export const EXTERNAL_TIMEOUT = "EXTERNAL_TIMEOUT";
export const EXTERNAL_FAILURE = "EXTERNAL_FAILURE";
export const EXTERNAL_PROVIDER_UNAVAILABLE = "EXTERNAL_PROVIDER_UNAVAILABLE";

// Server
export const INTERNAL_ERROR = "INTERNAL_ERROR";

// Client-side (not from backend)
export const NETWORK_ERROR = "NETWORK_ERROR";
export const TIMEOUT = "TIMEOUT";

/**
 * Map from error code to i18n key under "errorCodes.*".
 *
 * If a code is not in the map, `getErrorMessage` falls back to the raw
 * server message or a generic "Unknown error" string.
 */
const ERROR_CODE_I18N_MAP: Record<string, string> = {
  [AUTH_INVALID_CREDENTIALS]: "errorCodes.authInvalidCredentials",
  [AUTH_TOKEN_EXPIRED]: "errorCodes.authTokenExpired",
  [AUTH_TOKEN_INVALID]: "errorCodes.authTokenInvalid",
  [AUTH_ACCOUNT_INACTIVE]: "errorCodes.authAccountInactive",
  [AUTH_EMAIL_TAKEN]: "errorCodes.authEmailTaken",
  [AUTH_PASSWORD_EXPIRED]: "errorCodes.authPasswordExpired",
  [AUTH_PASSWORD_MISMATCH]: "errorCodes.authPasswordMismatch",
  [AUTH_PASSWORD_UNAVAILABLE]: "errorCodes.authPasswordUnavailable",
  [AUTHZ_ADMIN_REQUIRED]: "errorCodes.authzAdminRequired",
  [AUTHZ_FORBIDDEN]: "errorCodes.authzForbidden",
  [CREDIT_INSUFFICIENT]: "errorCodes.creditInsufficient",
  [RESOURCE_NOT_FOUND]: "errorCodes.resourceNotFound",
  [RESOURCE_CONFLICT]: "errorCodes.resourceConflict",
  [VALIDATION_ERROR]: "errorCodes.validationError",
  [VALIDATION_LIMIT_EXCEEDED]: "errorCodes.validationLimitExceeded",
  [EXTERNAL_TIMEOUT]: "errorCodes.externalTimeout",
  [EXTERNAL_FAILURE]: "errorCodes.externalFailure",
  [EXTERNAL_PROVIDER_UNAVAILABLE]: "errorCodes.externalProviderUnavailable",
  [INTERNAL_ERROR]: "errorCodes.internalError",
  [NETWORK_ERROR]: "errorCodes.networkError",
  [TIMEOUT]: "errorCodes.timeout",
};

/**
 * Get the i18n key for an error code, or null if none is mapped.
 */
export function getErrorI18nKey(code: string): string | null {
  return ERROR_CODE_I18N_MAP[code] ?? null;
}

/**
 * Get a user-friendly error message for an API error.
 *
 * Strategy:
 * 1. If the error code has a mapped i18n key AND the translation exists, use it.
 * 2. Otherwise fall back to the server-provided message.
 * 3. If neither exists, return the generic "Unknown error" key.
 *
 * @param code    The error code from `errors[].code`
 * @param message The server message from `errors[].message`
 * @param t       The i18next `t` function
 */
export function getErrorMessage(
  code: string,
  message: string,
  t: (key: string, options?: Record<string, unknown>) => string,
): string {
  const i18nKey = getErrorI18nKey(code);
  if (i18nKey) {
    const translated = t(i18nKey, { defaultValue: "" });
    if (translated && translated !== i18nKey) {
      return translated;
    }
  }
  // Fall back to server message
  return message || t("common.unknownError");
}
