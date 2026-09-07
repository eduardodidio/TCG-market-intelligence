import { describe, it, expect, vi } from "vitest";
import {
  getErrorI18nKey,
  getErrorMessage,
  AUTH_INVALID_CREDENTIALS,
  AUTH_TOKEN_EXPIRED,
  AUTH_EMAIL_TAKEN,
  AUTH_PASSWORD_MISMATCH,
  AUTHZ_FORBIDDEN,
  CREDIT_INSUFFICIENT,
  RESOURCE_NOT_FOUND,
  VALIDATION_ERROR,
  EXTERNAL_TIMEOUT,
  INTERNAL_ERROR,
  NETWORK_ERROR,
  TIMEOUT,
} from "../errorCodes";

describe("getErrorI18nKey", () => {
  it("returns the i18n key for known error codes", () => {
    expect(getErrorI18nKey(AUTH_INVALID_CREDENTIALS)).toBe(
      "errorCodes.authInvalidCredentials",
    );
    expect(getErrorI18nKey(AUTH_TOKEN_EXPIRED)).toBe(
      "errorCodes.authTokenExpired",
    );
    expect(getErrorI18nKey(AUTH_EMAIL_TAKEN)).toBe(
      "errorCodes.authEmailTaken",
    );
    expect(getErrorI18nKey(AUTH_PASSWORD_MISMATCH)).toBe(
      "errorCodes.authPasswordMismatch",
    );
    expect(getErrorI18nKey(AUTHZ_FORBIDDEN)).toBe(
      "errorCodes.authzForbidden",
    );
    expect(getErrorI18nKey(CREDIT_INSUFFICIENT)).toBe(
      "errorCodes.creditInsufficient",
    );
    expect(getErrorI18nKey(RESOURCE_NOT_FOUND)).toBe(
      "errorCodes.resourceNotFound",
    );
    expect(getErrorI18nKey(VALIDATION_ERROR)).toBe(
      "errorCodes.validationError",
    );
    expect(getErrorI18nKey(EXTERNAL_TIMEOUT)).toBe(
      "errorCodes.externalTimeout",
    );
    expect(getErrorI18nKey(INTERNAL_ERROR)).toBe(
      "errorCodes.internalError",
    );
    expect(getErrorI18nKey(NETWORK_ERROR)).toBe(
      "errorCodes.networkError",
    );
    expect(getErrorI18nKey(TIMEOUT)).toBe("errorCodes.timeout");
  });

  it("returns null for unknown error codes", () => {
    expect(getErrorI18nKey("UNKNOWN_CODE")).toBeNull();
    expect(getErrorI18nKey("HTTP_500")).toBeNull();
    expect(getErrorI18nKey("")).toBeNull();
  });
});

describe("getErrorMessage", () => {
  it("returns the translated message when the i18n key exists", () => {
    const t = vi.fn((key: string) => {
      if (key === "errorCodes.authInvalidCredentials") {
        return "Invalid email or password.";
      }
      return key;
    });

    const result = getErrorMessage(
      AUTH_INVALID_CREDENTIALS,
      "Bad credentials",
      t,
    );
    expect(result).toBe("Invalid email or password.");
    expect(t).toHaveBeenCalledWith("errorCodes.authInvalidCredentials", {
      defaultValue: "",
    });
  });

  it("falls back to the server message when translation is empty", () => {
    const t = vi.fn((_key: string, opts?: Record<string, unknown>) => {
      return (opts?.defaultValue as string) ?? "";
    });

    const result = getErrorMessage(
      AUTH_INVALID_CREDENTIALS,
      "Server-side message",
      t,
    );
    expect(result).toBe("Server-side message");
  });

  it("falls back to the server message for unknown codes", () => {
    const t = vi.fn(
      (key: string) => key,
    );

    const result = getErrorMessage(
      "SOME_UNKNOWN_CODE",
      "Something went wrong",
      t,
    );
    expect(result).toBe("Something went wrong");
  });

  it("returns generic error when both code and message are missing", () => {
    const t = vi.fn((key: string) => {
      if (key === "common.unknownError") return "Unknown error";
      return key;
    });

    const result = getErrorMessage("UNKNOWN", "", t);
    expect(result).toBe("Unknown error");
  });

  it("falls back to server message when translation equals the key", () => {
    // This simulates when i18next returns the key itself (no translation found)
    const t = vi.fn((key: string) => key);

    const result = getErrorMessage(
      CREDIT_INSUFFICIENT,
      "Not enough credits",
      t,
    );
    // The translated value equals the key, so it falls back
    expect(result).toBe("Not enough credits");
  });
});
