import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { CsvImportModal } from "../../src/components/CsvImportModal";

// Mock the API module
vi.mock("../../src/api/collection", async () => {
  const actual = await vi.importActual<typeof import("../../src/api/collection")>(
    "../../src/api/collection",
  );
  return {
    ...actual,
    importCollectionCsv: vi.fn(),
  };
});

import { importCollectionCsv } from "../../src/api/collection";
const mockImport = vi.mocked(importCollectionCsv);

const emptyMeta = { cursor: null, total: null, offset: null, request_id: "" };

function createTestFile(name = "collection.csv"): File {
  return new File(["name,qty\nLightning Bolt,4"], name, { type: "text/csv" });
}

describe("CsvImportModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("does not render when isOpen is false", () => {
    render(<CsvImportModal isOpen={false} onClose={vi.fn()} onSuccess={vi.fn()} />);
    expect(screen.queryByTestId("csv-import-modal")).not.toBeInTheDocument();
  });

  it("renders file input and warning text when open", () => {
    render(<CsvImportModal isOpen={true} onClose={vi.fn()} onSuccess={vi.fn()} />);
    expect(screen.getByTestId("csv-import-modal")).toBeInTheDocument();
    expect(screen.getByTestId("csv-file-input")).toBeInTheDocument();
    expect(screen.getByTestId("csv-import-warning")).toBeInTheDocument();
  });

  it("import button is disabled when no file is selected", () => {
    render(<CsvImportModal isOpen={true} onClose={vi.fn()} onSuccess={vi.fn()} />);
    const btn = screen.getByTestId("csv-import-btn");
    expect(btn).toBeDisabled();
  });

  it("import button is enabled after file is selected", () => {
    render(<CsvImportModal isOpen={true} onClose={vi.fn()} onSuccess={vi.fn()} />);
    const input = screen.getByTestId("csv-file-input");
    fireEvent.change(input, { target: { files: [createTestFile()] } });
    const btn = screen.getByTestId("csv-import-btn");
    expect(btn).not.toBeDisabled();
  });

  it("import button is disabled while uploading", async () => {
    // Never resolve to keep in uploading state
    mockImport.mockReturnValue(new Promise(() => {}));

    render(<CsvImportModal isOpen={true} onClose={vi.fn()} onSuccess={vi.fn()} />);
    const input = screen.getByTestId("csv-file-input");
    fireEvent.change(input, { target: { files: [createTestFile()] } });
    fireEvent.click(screen.getByTestId("csv-import-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("csv-import-btn")).toBeDisabled();
    });
  });

  it("shows success stats after successful upload", async () => {
    mockImport.mockResolvedValue({
      data: {
        imported: 10,
        skipped: 2,
        linked: 8,
        total_csv_rows: 12,
        new_entry_ids: [1, 2, 3],
        canonize_scheduled: true,
      },
      meta: emptyMeta,
      errors: [],
    });

    render(<CsvImportModal isOpen={true} onClose={vi.fn()} onSuccess={vi.fn()} />);
    const input = screen.getByTestId("csv-file-input");
    fireEvent.change(input, { target: { files: [createTestFile()] } });
    fireEvent.click(screen.getByTestId("csv-import-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("csv-import-success")).toBeInTheDocument();
    });
    expect(screen.getByTestId("csv-import-stats")).toBeInTheDocument();
  });

  it("shows error message on failure", async () => {
    mockImport.mockResolvedValue({
      data: null,
      meta: emptyMeta,
      errors: [{ code: "PARSE_ERROR", message: "Invalid CSV format" }],
    });

    render(<CsvImportModal isOpen={true} onClose={vi.fn()} onSuccess={vi.fn()} />);
    const input = screen.getByTestId("csv-file-input");
    fireEvent.change(input, { target: { files: [createTestFile()] } });
    fireEvent.click(screen.getByTestId("csv-import-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("csv-import-error")).toBeInTheDocument();
    });
    expect(screen.getByText("Invalid CSV format")).toBeInTheDocument();
  });

  it("calls onSuccess callback after successful import and close", async () => {
    mockImport.mockResolvedValue({
      data: {
        imported: 5,
        skipped: 0,
        linked: 3,
        total_csv_rows: 5,
        new_entry_ids: [1, 2],
        canonize_scheduled: false,
      },
      meta: emptyMeta,
      errors: [],
    });

    const onSuccess = vi.fn();
    const onClose = vi.fn();
    render(<CsvImportModal isOpen={true} onClose={onClose} onSuccess={onSuccess} />);

    const input = screen.getByTestId("csv-file-input");
    fireEvent.change(input, { target: { files: [createTestFile()] } });
    fireEvent.click(screen.getByTestId("csv-import-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("csv-import-success")).toBeInTheDocument();
    });

    // Click the close button (which shows "Close" text in success state)
    fireEvent.click(screen.getByTestId("csv-cancel-btn"));
    expect(onSuccess).toHaveBeenCalled();
    expect(onClose).toHaveBeenCalled();
  });

  it("handles network error gracefully", async () => {
    mockImport.mockRejectedValue(new Error("Network error"));

    render(<CsvImportModal isOpen={true} onClose={vi.fn()} onSuccess={vi.fn()} />);
    const input = screen.getByTestId("csv-file-input");
    fireEvent.change(input, { target: { files: [createTestFile()] } });
    fireEvent.click(screen.getByTestId("csv-import-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("csv-import-error")).toBeInTheDocument();
    });
  });
});
