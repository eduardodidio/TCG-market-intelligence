export const API_BASE_URL: string =
  (typeof import.meta !== "undefined" &&
    import.meta.env?.VITE_API_BASE_URL as string) ||
  "";

export const DEFAULT_PAGE_LIMIT = 24;
