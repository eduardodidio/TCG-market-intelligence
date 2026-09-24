import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { CsvImportModal } from "../CsvImportModal";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, opts?: Record<string, unknown>) => {
      if (opts && Object.keys(opts).length > 0) {
        return `${key}:${JSON.stringify(opts)}`;
      }
      return key;
    },
  }),
}));

vi.mock("../../api/collection", () => ({
  importCollectionCsv: vi.fn(),
}));

import { importCollectionCsv } from "../../api/collection";

const mockImportCollectionCsv = vi.mocked(importCollectionCsv);

function createCsvFile(name = "collection.csv", content = "a,b\n1,2") {
  return new File([content], name, { type: "text/csv" });
}

function selectFile(input: HTMLInputElement, file: File) {
  Object.defineProperty(input, "files", {
    value: [file],
    writable: false,
    configurable: true,
  });
  fireEvent.change(input);
}

function renderModal(onSuccess = vi.fn(), onClose = vi.fn()) {
  render(<CsvImportModal isOpen onClose={onClose} onSuccess={onSuccess} />);
}

describe("CsvImportModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("triggers exactly one dry-run call when a file is selected", async () => {
    mockImportCollectionCsv.mockResolvedValueOnce({
      data: {
        imported: 0,
        skipped: 0,
        linked: 0,
        total_csv_rows: 3,
        new_entry_ids: [],
        canonize_scheduled: false,
        detected_currency: "BRL",
        currency_source: "symbol",
        currency_confidence: "high",
      } as never,
      meta: {} as never,
      errors: [],
    });

    renderModal();
    const input = screen.getByTestId("csv-file-input") as HTMLInputElement;
    selectFile(input, createCsvFile());

    await waitFor(() => {
      expect(mockImportCollectionCsv).toHaveBeenCalledTimes(1);
    });
    expect(mockImportCollectionCsv).toHaveBeenCalledWith(
      expect.any(File),
      { dryRun: true },
    );
  });

  it("shows the detected currency and source", async () => {
    mockImportCollectionCsv.mockResolvedValueOnce({
      data: {
        imported: 0,
        skipped: 0,
        linked: 0,
        total_csv_rows: 3,
        new_entry_ids: [],
        canonize_scheduled: false,
        detected_currency: "BRL",
        currency_source: "symbol",
        currency_confidence: "high",
      } as never,
      meta: {} as never,
      errors: [],
    });

    renderModal();
    const input = screen.getByTestId("csv-file-input") as HTMLInputElement;
    selectFile(input, createCsvFile());

    await waitFor(() => {
      expect(screen.getByTestId("csv-currency-detected")).toBeDefined();
    });
    expect(screen.queryByTestId("csv-currency-warning")).toBeNull();
  });

  it("shows the low-confidence warning when currency_source is default", async () => {
    mockImportCollectionCsv.mockResolvedValueOnce({
      data: {
        imported: 0,
        skipped: 0,
        linked: 0,
        total_csv_rows: 3,
        new_entry_ids: [],
        canonize_scheduled: false,
        detected_currency: "BRL",
        currency_source: "default",
        currency_confidence: "low",
      } as never,
      meta: {} as never,
      errors: [],
    });

    renderModal();
    const input = screen.getByTestId("csv-file-input") as HTMLInputElement;
    selectFile(input, createCsvFile());

    await waitFor(() => {
      expect(screen.getByTestId("csv-currency-warning")).toBeDefined();
    });
  });

  it("selecting a new file resets detection", async () => {
    mockImportCollectionCsv.mockResolvedValueOnce({
      data: {
        imported: 0,
        skipped: 0,
        linked: 0,
        total_csv_rows: 3,
        new_entry_ids: [],
        canonize_scheduled: false,
        detected_currency: "BRL",
        currency_source: "symbol",
        currency_confidence: "high",
      } as never,
      meta: {} as never,
      errors: [],
    });

    renderModal();
    const input = screen.getByTestId("csv-file-input") as HTMLInputElement;
    selectFile(input, createCsvFile());

    await waitFor(() => {
      expect(screen.getByTestId("csv-currency-detected")).toBeDefined();
    });

    // Second file selection: dry-run pending -> detection cleared immediately
    mockImportCollectionCsv.mockImplementationOnce(() => new Promise(() => {}));
    selectFile(input, createCsvFile("other.csv"));

    expect(screen.queryByTestId("csv-currency-detected")).toBeNull();
  });

  it("sends currency=USD on import when the user overrides the select", async () => {
    mockImportCollectionCsv.mockResolvedValueOnce({
      data: {
        imported: 0,
        skipped: 0,
        linked: 0,
        total_csv_rows: 3,
        new_entry_ids: [],
        canonize_scheduled: false,
        detected_currency: "BRL",
        currency_source: "symbol",
        currency_confidence: "high",
      } as never,
      meta: {} as never,
      errors: [],
    });

    renderModal();
    const input = screen.getByTestId("csv-file-input") as HTMLInputElement;
    selectFile(input, createCsvFile());

    await waitFor(() => {
      expect(screen.getByTestId("csv-currency-select")).toBeDefined();
    });

    fireEvent.change(screen.getByTestId("csv-currency-select"), {
      target: { value: "USD" },
    });

    mockImportCollectionCsv.mockResolvedValueOnce({
      data: {
        imported: 1,
        skipped: 0,
        linked: 0,
        total_csv_rows: 1,
        new_entry_ids: [1],
        canonize_scheduled: false,
        priced: 1,
        converted: 1,
        exchange_rate: "5.20",
        price_warnings: [],
      } as never,
      meta: {} as never,
      errors: [],
    });

    fireEvent.click(screen.getByTestId("csv-import-btn"));

    await waitFor(() => {
      expect(mockImportCollectionCsv).toHaveBeenLastCalledWith(
        expect.any(File),
        { currency: "USD" },
      );
    });
  });

  it("shows priced/converted counts on the success screen", async () => {
    mockImportCollectionCsv.mockResolvedValueOnce({
      data: {
        imported: 0,
        skipped: 0,
        linked: 0,
        total_csv_rows: 3,
        new_entry_ids: [],
        canonize_scheduled: false,
        detected_currency: "BRL",
        currency_source: "symbol",
        currency_confidence: "high",
      } as never,
      meta: {} as never,
      errors: [],
    });

    renderModal();
    const input = screen.getByTestId("csv-file-input") as HTMLInputElement;
    selectFile(input, createCsvFile());

    await waitFor(() => {
      expect(screen.getByTestId("csv-import-btn")).toBeDefined();
    });

    mockImportCollectionCsv.mockResolvedValueOnce({
      data: {
        imported: 3,
        skipped: 0,
        linked: 0,
        total_csv_rows: 3,
        new_entry_ids: [1, 2, 3],
        canonize_scheduled: false,
        priced: 3,
        converted: 2,
        exchange_rate: "5.20",
        price_warnings: [],
      } as never,
      meta: {} as never,
      errors: [],
    });

    fireEvent.click(screen.getByTestId("csv-import-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("csv-import-price-stats")).toBeDefined();
    });
    expect(screen.getByTestId("csv-import-rate")).toBeDefined();
  });

  it("hides the rate line when converted is 0", async () => {
    mockImportCollectionCsv.mockResolvedValueOnce({
      data: {
        imported: 0,
        skipped: 0,
        linked: 0,
        total_csv_rows: 3,
        new_entry_ids: [],
        canonize_scheduled: false,
        detected_currency: "BRL",
        currency_source: "symbol",
        currency_confidence: "high",
      } as never,
      meta: {} as never,
      errors: [],
    });

    renderModal();
    const input = screen.getByTestId("csv-file-input") as HTMLInputElement;
    selectFile(input, createCsvFile());

    await waitFor(() => {
      expect(screen.getByTestId("csv-import-btn")).toBeDefined();
    });

    mockImportCollectionCsv.mockResolvedValueOnce({
      data: {
        imported: 3,
        skipped: 0,
        linked: 0,
        total_csv_rows: 3,
        new_entry_ids: [1, 2, 3],
        canonize_scheduled: false,
        priced: 3,
        converted: 0,
        exchange_rate: null,
        price_warnings: [],
      } as never,
      meta: {} as never,
      errors: [],
    });

    fireEvent.click(screen.getByTestId("csv-import-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("csv-import-price-stats")).toBeDefined();
    });
    expect(screen.queryByTestId("csv-import-rate")).toBeNull();
  });

  it("truncates price_warnings to 5 items", async () => {
    mockImportCollectionCsv.mockResolvedValueOnce({
      data: {
        imported: 0,
        skipped: 0,
        linked: 0,
        total_csv_rows: 3,
        new_entry_ids: [],
        canonize_scheduled: false,
        detected_currency: "BRL",
        currency_source: "symbol",
        currency_confidence: "high",
      } as never,
      meta: {} as never,
      errors: [],
    });

    renderModal();
    const input = screen.getByTestId("csv-file-input") as HTMLInputElement;
    selectFile(input, createCsvFile());

    await waitFor(() => {
      expect(screen.getByTestId("csv-import-btn")).toBeDefined();
    });

    const warnings = Array.from({ length: 8 }, (_, i) => `warning ${i + 1}`);
    mockImportCollectionCsv.mockResolvedValueOnce({
      data: {
        imported: 3,
        skipped: 0,
        linked: 0,
        total_csv_rows: 8,
        new_entry_ids: [1, 2, 3],
        canonize_scheduled: false,
        priced: 3,
        converted: 0,
        exchange_rate: null,
        price_warnings: warnings,
      } as never,
      meta: {} as never,
      errors: [],
    });

    fireEvent.click(screen.getByTestId("csv-import-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("csv-import-price-warnings")).toBeDefined();
    });
    const items = screen.getByTestId("csv-import-price-warnings").querySelectorAll("li");
    expect(items.length).toBe(5);
  });

  it("keeps the selector and import usable when the dry-run fails", async () => {
    mockImportCollectionCsv.mockRejectedValueOnce(new Error("network"));

    renderModal();
    const input = screen.getByTestId("csv-file-input") as HTMLInputElement;
    selectFile(input, createCsvFile());

    await waitFor(() => {
      expect(mockImportCollectionCsv).toHaveBeenCalledTimes(1);
    });

    expect(screen.getByTestId("csv-currency-select")).toBeDefined();
    expect((screen.getByTestId("csv-import-btn") as HTMLButtonElement).disabled).toBe(false);

    mockImportCollectionCsv.mockResolvedValueOnce({
      data: {
        imported: 1,
        skipped: 0,
        linked: 0,
        total_csv_rows: 1,
        new_entry_ids: [1],
        canonize_scheduled: false,
      } as never,
      meta: {} as never,
      errors: [],
    });

    fireEvent.click(screen.getByTestId("csv-import-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("csv-import-success")).toBeDefined();
    });
  });

  it("shows an error state when import returns errors", async () => {
    mockImportCollectionCsv.mockResolvedValueOnce({
      data: {
        imported: 0,
        skipped: 0,
        linked: 0,
        total_csv_rows: 3,
        new_entry_ids: [],
        canonize_scheduled: false,
        detected_currency: "BRL",
        currency_source: "symbol",
        currency_confidence: "high",
      } as never,
      meta: {} as never,
      errors: [],
    });

    renderModal();
    const input = screen.getByTestId("csv-file-input") as HTMLInputElement;
    selectFile(input, createCsvFile());

    await waitFor(() => {
      expect(screen.getByTestId("csv-import-btn")).toBeDefined();
    });

    mockImportCollectionCsv.mockResolvedValueOnce({
      data: null as never,
      meta: {} as never,
      errors: [{ message: "Invalid file", code: "invalid" } as never],
    });

    fireEvent.click(screen.getByTestId("csv-import-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("csv-import-error")).toBeDefined();
    });
  });
});
