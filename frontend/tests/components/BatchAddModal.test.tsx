import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { BatchAddModal } from "../../src/components/BatchAddModal";

// Mock the API module
vi.mock("../../src/api/collection", async () => {
  const actual = await vi.importActual<typeof import("../../src/api/collection")>(
    "../../src/api/collection",
  );
  return {
    ...actual,
    parseBatchText: vi.fn(),
    addBatchEntries: vi.fn(),
  };
});

import { parseBatchText, addBatchEntries } from "../../src/api/collection";
const mockParse = vi.mocked(parseBatchText);
const mockAdd = vi.mocked(addBatchEntries);

const emptyMeta = { cursor: null, total: null, offset: null, request_id: "" };

const parsedEntries = [
  {
    line_number: 1,
    raw_text: "2 Lightning Bolt",
    quantity: 2,
    name: "Lightning Bolt",
    set_code: null,
    quality: null,
    language: null,
    extras: null,
    error: null,
  },
  {
    line_number: 2,
    raw_text: "bad line",
    quantity: 1,
    name: "",
    set_code: null,
    quality: null,
    language: null,
    extras: null,
    error: "Could not parse",
  },
];

describe("BatchAddModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("does not render when isOpen is false", () => {
    render(<BatchAddModal isOpen={false} onClose={vi.fn()} onSuccess={vi.fn()} />);
    expect(screen.queryByTestId("batch-add-modal")).not.toBeInTheDocument();
  });

  it("renders textarea and Preview button when open", () => {
    render(<BatchAddModal isOpen={true} onClose={vi.fn()} onSuccess={vi.fn()} />);
    expect(screen.getByTestId("batch-add-modal")).toBeInTheDocument();
    expect(screen.getByTestId("batch-textarea")).toBeInTheDocument();
    expect(screen.getByTestId("batch-preview-btn")).toBeInTheDocument();
  });

  it("Preview button calls parse API", async () => {
    mockParse.mockResolvedValue({
      data: { entries: parsedEntries },
      meta: emptyMeta,
      errors: [],
    });

    render(<BatchAddModal isOpen={true} onClose={vi.fn()} onSuccess={vi.fn()} />);

    fireEvent.change(screen.getByTestId("batch-textarea"), {
      target: { value: "2 Lightning Bolt\nbad line" },
    });
    fireEvent.click(screen.getByTestId("batch-preview-btn"));

    await waitFor(() => {
      expect(mockParse).toHaveBeenCalledWith("2 Lightning Bolt\nbad line");
    });
  });

  it("displays parsed results in table after preview", async () => {
    mockParse.mockResolvedValue({
      data: { entries: parsedEntries },
      meta: emptyMeta,
      errors: [],
    });

    render(<BatchAddModal isOpen={true} onClose={vi.fn()} onSuccess={vi.fn()} />);

    fireEvent.change(screen.getByTestId("batch-textarea"), {
      target: { value: "2 Lightning Bolt\nbad line" },
    });
    fireEvent.click(screen.getByTestId("batch-preview-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("batch-preview-table")).toBeInTheDocument();
    });
    expect(screen.getByText("Lightning Bolt")).toBeInTheDocument();
  });

  it("error rows highlighted with error message", async () => {
    mockParse.mockResolvedValue({
      data: { entries: parsedEntries },
      meta: emptyMeta,
      errors: [],
    });

    render(<BatchAddModal isOpen={true} onClose={vi.fn()} onSuccess={vi.fn()} />);

    fireEvent.change(screen.getByTestId("batch-textarea"), {
      target: { value: "test input" },
    });
    fireEvent.click(screen.getByTestId("batch-preview-btn"));

    await waitFor(() => {
      const errorRow = screen.getByTestId("preview-row-2");
      expect(errorRow.className).toContain("bg-red-900");
    });
  });

  it("remove button removes row from preview", async () => {
    mockParse.mockResolvedValue({
      data: { entries: [parsedEntries[0]] },
      meta: emptyMeta,
      errors: [],
    });

    render(<BatchAddModal isOpen={true} onClose={vi.fn()} onSuccess={vi.fn()} />);

    fireEvent.change(screen.getByTestId("batch-textarea"), {
      target: { value: "2 Lightning Bolt" },
    });
    fireEvent.click(screen.getByTestId("batch-preview-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("preview-row-1")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("remove-row-1"));
    expect(screen.queryByTestId("preview-row-1")).not.toBeInTheDocument();
  });

  it("Add N Cards button calls batch add API with valid entries only", async () => {
    mockParse.mockResolvedValue({
      data: { entries: parsedEntries },
      meta: emptyMeta,
      errors: [],
    });
    mockAdd.mockResolvedValue({
      data: { added: 1, errors: [] },
      meta: emptyMeta,
      errors: [],
    });

    render(<BatchAddModal isOpen={true} onClose={vi.fn()} onSuccess={vi.fn()} />);

    fireEvent.change(screen.getByTestId("batch-textarea"), {
      target: { value: "test" },
    });
    fireEvent.click(screen.getByTestId("batch-preview-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("batch-add-btn")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("batch-add-btn"));

    await waitFor(() => {
      expect(mockAdd).toHaveBeenCalledWith([
        {
          name_en: "Lightning Bolt",
          set_code: undefined,
          quantity: 2,
          quality: undefined,
          language: undefined,
          extras: undefined,
        },
      ]);
    });
  });

  it("success shows result and close button", async () => {
    mockParse.mockResolvedValue({
      data: { entries: [parsedEntries[0]] },
      meta: emptyMeta,
      errors: [],
    });
    mockAdd.mockResolvedValue({
      data: { added: 1, errors: [] },
      meta: emptyMeta,
      errors: [],
    });

    render(<BatchAddModal isOpen={true} onClose={vi.fn()} onSuccess={vi.fn()} />);

    fireEvent.change(screen.getByTestId("batch-textarea"), {
      target: { value: "test" },
    });
    fireEvent.click(screen.getByTestId("batch-preview-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("batch-add-btn")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("batch-add-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("batch-result")).toBeInTheDocument();
    });

    expect(screen.getByTestId("batch-close-btn")).toBeInTheDocument();
  });

  it("partial error shows summary with error details", async () => {
    mockParse.mockResolvedValue({
      data: { entries: [parsedEntries[0]] },
      meta: emptyMeta,
      errors: [],
    });
    mockAdd.mockResolvedValue({
      data: {
        added: 1,
        errors: [{ line: 1, text: "Bad Card", error: "not found" }],
      },
      meta: emptyMeta,
      errors: [],
    });

    render(<BatchAddModal isOpen={true} onClose={vi.fn()} onSuccess={vi.fn()} />);

    fireEvent.change(screen.getByTestId("batch-textarea"), {
      target: { value: "test" },
    });
    fireEvent.click(screen.getByTestId("batch-preview-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("batch-add-btn")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("batch-add-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("batch-result")).toBeInTheDocument();
    });

    expect(screen.getByText(/not found/)).toBeInTheDocument();
  });

  it("format help section is toggleable", () => {
    render(<BatchAddModal isOpen={true} onClose={vi.fn()} onSuccess={vi.fn()} />);

    expect(screen.queryByTestId("format-help-content")).not.toBeInTheDocument();

    fireEvent.click(screen.getByTestId("format-help-toggle"));
    expect(screen.getByTestId("format-help-content")).toBeInTheDocument();
  });

  it("shows max 500 lines warning when over limit", () => {
    render(<BatchAddModal isOpen={true} onClose={vi.fn()} onSuccess={vi.fn()} />);

    // Generate 501 non-empty lines
    const lines = Array.from({ length: 501 }, (_, i) => `Card ${i + 1}`).join("\n");

    fireEvent.change(screen.getByTestId("batch-textarea"), {
      target: { value: lines },
    });

    expect(screen.getByTestId("over-limit-warning")).toBeInTheDocument();
    expect(screen.getByTestId("batch-preview-btn")).toBeDisabled();
  });

  it("close button on result calls onSuccess when cards were added", async () => {
    mockParse.mockResolvedValue({
      data: { entries: [parsedEntries[0]] },
      meta: emptyMeta,
      errors: [],
    });
    mockAdd.mockResolvedValue({
      data: { added: 1, errors: [] },
      meta: emptyMeta,
      errors: [],
    });

    const onSuccess = vi.fn();
    const onClose = vi.fn();
    render(<BatchAddModal isOpen={true} onClose={onClose} onSuccess={onSuccess} />);

    fireEvent.change(screen.getByTestId("batch-textarea"), {
      target: { value: "test" },
    });
    fireEvent.click(screen.getByTestId("batch-preview-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("batch-add-btn")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("batch-add-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("batch-close-btn")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("batch-close-btn"));
    expect(onSuccess).toHaveBeenCalled();
  });
});
