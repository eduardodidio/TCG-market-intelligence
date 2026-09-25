import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { ImportPurchasesPage } from "../ImportPurchasesPage";

// react-i18next is configured globally in tests/setup.ts with EN translations

// Mock the API
vi.mock("../../api/purchases", () => ({
  uploadForPreview: vi.fn(),
  applyPurchases: vi.fn(),
}));

import { uploadForPreview, applyPurchases } from "../../api/purchases";

const mockUpload = vi.mocked(uploadForPreview);
const mockApply = vi.mocked(applyPurchases);

const MOCK_PREVIEW = {
  total_files: 1,
  total_orders: 1,
  total_items_parsed: 2,
  total_items_matched: 2,
  total_items_unmatched: 1,
  total_sealed_skipped: 0,
  matches: [
    {
      id: "match_1_#9117259",
      card_name_parsed: "Fogo do Dragao / Dragon's Fire",
      card_name_collection: "Dragon's Fire",
      set_code_parsed: "AFR",
      set_code_collection: "afr",
      collector_number: "139",
      quantity_parsed: 3,
      quantity_collection: 3,
      unit_price: "0.20",
      order_date: "2025-08-25",
      order_number: "#9117259",
      store_name: "Nerdz Cards",
      confidence: 1.0,
      match_method: "exact",
      collection_entry_id: 1,
      already_has_price: false,
      current_acquisition_price: null,
      selected: true,
    },
    {
      id: "match_2_#9117259",
      card_name_parsed: "Terror of the Peaks",
      card_name_collection: "Terror of the Peaks",
      set_code_parsed: "M21",
      set_code_collection: "m21",
      collector_number: "164",
      quantity_parsed: 1,
      quantity_collection: 1,
      unit_price: "179.90",
      order_date: "2025-08-25",
      order_number: "#9117259",
      store_name: "Nerdz Cards",
      confidence: 0.7,
      match_method: "name_only",
      collection_entry_id: 2,
      already_has_price: false,
      current_acquisition_price: null,
      selected: false,
    },
  ],
  unmatched: [
    {
      card_name_parsed: "Kit Inicial",
      set_code_parsed: null,
      unit_price: "199.90",
      order_number: "#5282134",
      skip_reason: "Sealed product (no set code)",
    },
  ],
  warnings: ["Order #11809236 has no expanded card data"],
};

const MOCK_APPLY_RESULT = {
  total_applied: 1,
  total_skipped: 0,
  applied: [
    {
      collection_entry_id: 1,
      card_name: "Dragon's Fire",
      acquisition_price: "0.20",
      acquired_at: "2025-08-25",
    },
  ],
  skipped: [],
};

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/import-purchases"]}>
      <ImportPurchasesPage />
    </MemoryRouter>,
  );
}

function createHtmlFile(name = "order.html", content = "<html></html>") {
  return new File([content], name, { type: "text/html" });
}

/** Simulate selecting files on the file input. */
function uploadFile(input: HTMLInputElement, file: File) {
  // Create a FileList-like object
  Object.defineProperty(input, "files", {
    value: [file],
    writable: false,
    configurable: true,
  });
  fireEvent.change(input);
}

describe("ImportPurchasesPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  /* ---- Upload state ---- */

  it("renders upload state with drop zone and button", () => {
    renderPage();
    expect(screen.getByTestId("upload-state")).toBeDefined();
    expect(screen.getByTestId("drop-zone")).toBeDefined();
    expect(screen.getByTestId("upload-button")).toBeDefined();
    expect(
      (screen.getByTestId("upload-button") as HTMLButtonElement).disabled,
    ).toBe(true);
  });

  it("shows file names after selection", () => {
    renderPage();
    const input = screen.getByTestId("file-input") as HTMLInputElement;
    uploadFile(input, createHtmlFile("order.html"));
    expect(screen.getByTestId("file-list")).toBeDefined();
    expect(screen.getByText(/order\.html/)).toBeDefined();
  });

  it("rejects non-HTML files", () => {
    renderPage();
    const input = screen.getByTestId("file-input") as HTMLInputElement;
    const txtFile = new File(["hello"], "test.txt", { type: "text/plain" });
    uploadFile(input, txtFile);
    expect(screen.getByTestId("error-message")).toBeDefined();
  });

  it("enables upload button when files are selected", () => {
    renderPage();
    const input = screen.getByTestId("file-input") as HTMLInputElement;
    uploadFile(input, createHtmlFile());
    expect(
      (screen.getByTestId("upload-button") as HTMLButtonElement).disabled,
    ).toBe(false);
  });

  /* ---- Upload triggers API ---- */

  it("calls uploadForPreview on upload button click", async () => {
    mockUpload.mockResolvedValueOnce(MOCK_PREVIEW);
    renderPage();

    const input = screen.getByTestId("file-input") as HTMLInputElement;
    uploadFile(input, createHtmlFile());

    await act(async () => {
      fireEvent.click(screen.getByTestId("upload-button"));
    });

    await waitFor(() => {
      expect(mockUpload).toHaveBeenCalledTimes(1);
    });
  });

  /* ---- Preview state ---- */

  it("renders preview state after successful upload", async () => {
    mockUpload.mockResolvedValueOnce(MOCK_PREVIEW);
    renderPage();

    const input = screen.getByTestId("file-input") as HTMLInputElement;
    uploadFile(input, createHtmlFile());

    await act(async () => {
      fireEvent.click(screen.getByTestId("upload-button"));
    });

    await waitFor(() => {
      expect(screen.getByTestId("preview-state")).toBeDefined();
    });
    expect(screen.getByTestId("matches-table")).toBeDefined();
  });

  it("shows confidence badges with correct text", async () => {
    mockUpload.mockResolvedValueOnce(MOCK_PREVIEW);
    renderPage();

    const input = screen.getByTestId("file-input") as HTMLInputElement;
    uploadFile(input, createHtmlFile());

    await act(async () => {
      fireEvent.click(screen.getByTestId("upload-button"));
    });

    await waitFor(() => {
      const badges = screen.getAllByTestId("confidence-badge");
      expect(badges.length).toBe(2);
      expect(badges[0].textContent).toContain("Exact");
      expect(badges[1].textContent).toContain("Partial");
    });
  });

  it("pre-checks high-confidence matches", async () => {
    mockUpload.mockResolvedValueOnce(MOCK_PREVIEW);
    renderPage();

    const input = screen.getByTestId("file-input") as HTMLInputElement;
    uploadFile(input, createHtmlFile());

    await act(async () => {
      fireEvent.click(screen.getByTestId("upload-button"));
    });

    await waitFor(() => {
      const checkboxes = screen.getAllByRole("checkbox");
      // confidence 1.0 should be checked, 0.7 should not
      expect((checkboxes[0] as HTMLInputElement).checked).toBe(true);
      expect((checkboxes[1] as HTMLInputElement).checked).toBe(false);
    });
  });

  it("select all / deselect all toggles all checkboxes", async () => {
    mockUpload.mockResolvedValueOnce(MOCK_PREVIEW);
    renderPage();

    const input = screen.getByTestId("file-input") as HTMLInputElement;
    uploadFile(input, createHtmlFile());

    await act(async () => {
      fireEvent.click(screen.getByTestId("upload-button"));
    });

    await waitFor(() => {
      expect(screen.getByTestId("select-all")).toBeDefined();
    });

    fireEvent.click(screen.getByTestId("select-all"));
    const allChecked = screen.getAllByRole("checkbox");
    expect(allChecked.every((c) => (c as HTMLInputElement).checked)).toBe(true);

    fireEvent.click(screen.getByTestId("deselect-all"));
    const noneChecked = screen.getAllByRole("checkbox");
    expect(noneChecked.every((c) => !(c as HTMLInputElement).checked)).toBe(
      true,
    );
  });

  it("allows editing price in the table", async () => {
    mockUpload.mockResolvedValueOnce(MOCK_PREVIEW);
    renderPage();

    const input = screen.getByTestId("file-input") as HTMLInputElement;
    uploadFile(input, createHtmlFile());

    await act(async () => {
      fireEvent.click(screen.getByTestId("upload-button"));
    });

    await waitFor(() => {
      expect(screen.getAllByTestId("price-input").length).toBeGreaterThan(0);
    });

    const priceInput = screen.getAllByTestId("price-input")[0] as HTMLInputElement;
    fireEvent.change(priceInput, { target: { value: "1.50" } });
    expect(priceInput.value).toBe("1.50");
  });

  it("shows warnings section when warnings exist", async () => {
    mockUpload.mockResolvedValueOnce(MOCK_PREVIEW);
    renderPage();

    const input = screen.getByTestId("file-input") as HTMLInputElement;
    uploadFile(input, createHtmlFile());

    await act(async () => {
      fireEvent.click(screen.getByTestId("upload-button"));
    });

    await waitFor(() => {
      expect(screen.getByTestId("warnings-section")).toBeDefined();
    });
  });

  it("shows unmatched section", async () => {
    mockUpload.mockResolvedValueOnce(MOCK_PREVIEW);
    renderPage();

    const input = screen.getByTestId("file-input") as HTMLInputElement;
    uploadFile(input, createHtmlFile());

    await act(async () => {
      fireEvent.click(screen.getByTestId("upload-button"));
    });

    await waitFor(() => {
      expect(screen.getByTestId("unmatched-section")).toBeDefined();
    });
  });

  it("shows already-has-price indicator", async () => {
    const previewWithPrice = {
      ...MOCK_PREVIEW,
      matches: [
        {
          ...MOCK_PREVIEW.matches[0],
          already_has_price: true,
          current_acquisition_price: "5.00",
        },
      ],
    };
    mockUpload.mockResolvedValueOnce(previewWithPrice);
    renderPage();

    const input = screen.getByTestId("file-input") as HTMLInputElement;
    uploadFile(input, createHtmlFile());

    await act(async () => {
      fireEvent.click(screen.getByTestId("upload-button"));
    });

    await waitFor(() => {
      expect(screen.getByTestId("has-price-indicator")).toBeDefined();
    });
  });

  it("shows empty state when no matches", async () => {
    const emptyPreview = {
      ...MOCK_PREVIEW,
      matches: [],
      total_items_matched: 0,
    };
    mockUpload.mockResolvedValueOnce(emptyPreview);
    renderPage();

    const input = screen.getByTestId("file-input") as HTMLInputElement;
    uploadFile(input, createHtmlFile());

    await act(async () => {
      fireEvent.click(screen.getByTestId("upload-button"));
    });

    await waitFor(() => {
      expect(screen.getByTestId("empty-matches")).toBeDefined();
    });
  });

  /* ---- Apply ---- */

  it("calls applyPurchases on apply button click", async () => {
    mockUpload.mockResolvedValueOnce(MOCK_PREVIEW);
    mockApply.mockResolvedValueOnce(MOCK_APPLY_RESULT);
    renderPage();

    const input = screen.getByTestId("file-input") as HTMLInputElement;
    uploadFile(input, createHtmlFile());

    await act(async () => {
      fireEvent.click(screen.getByTestId("upload-button"));
    });

    await waitFor(() => {
      expect(screen.getByTestId("apply-button")).toBeDefined();
    });

    await act(async () => {
      fireEvent.click(screen.getByTestId("apply-button"));
    });

    await waitFor(() => {
      expect(mockApply).toHaveBeenCalledTimes(1);
    });
  });

  /* ---- Result state ---- */

  it("shows result state after apply", async () => {
    mockUpload.mockResolvedValueOnce(MOCK_PREVIEW);
    mockApply.mockResolvedValueOnce(MOCK_APPLY_RESULT);
    renderPage();

    const input = screen.getByTestId("file-input") as HTMLInputElement;
    uploadFile(input, createHtmlFile());

    await act(async () => {
      fireEvent.click(screen.getByTestId("upload-button"));
    });

    await waitFor(() => {
      expect(screen.getByTestId("apply-button")).toBeDefined();
    });

    await act(async () => {
      fireEvent.click(screen.getByTestId("apply-button"));
    });

    await waitFor(() => {
      expect(screen.getByTestId("result-state")).toBeDefined();
      expect(screen.getByText(/1 acquisition price/)).toBeDefined();
    });
  });

  it("import more button returns to upload state", async () => {
    mockUpload.mockResolvedValueOnce(MOCK_PREVIEW);
    mockApply.mockResolvedValueOnce(MOCK_APPLY_RESULT);
    renderPage();

    const input = screen.getByTestId("file-input") as HTMLInputElement;
    uploadFile(input, createHtmlFile());

    await act(async () => {
      fireEvent.click(screen.getByTestId("upload-button"));
    });

    await waitFor(() => {
      expect(screen.getByTestId("apply-button")).toBeDefined();
    });

    await act(async () => {
      fireEvent.click(screen.getByTestId("apply-button"));
    });

    await waitFor(() => {
      expect(screen.getByTestId("import-more-button")).toBeDefined();
    });

    fireEvent.click(screen.getByTestId("import-more-button"));
    expect(screen.getByTestId("upload-state")).toBeDefined();
  });

  /* ---- Currency conversion badge ---- */

  it("shows a converted-currency badge only for USD rows", async () => {
    const previewWithConversion = {
      ...MOCK_PREVIEW,
      matches: [
        {
          ...MOCK_PREVIEW.matches[0],
          original_unit_price: "0.05",
          original_currency: "USD",
          exchange_rate: "5.00",
        },
        {
          ...MOCK_PREVIEW.matches[1],
          original_unit_price: "179.90",
          original_currency: "BRL",
          exchange_rate: null,
        },
      ],
    };
    mockUpload.mockResolvedValueOnce(previewWithConversion);
    renderPage();

    const input = screen.getByTestId("file-input") as HTMLInputElement;
    uploadFile(input, createHtmlFile());

    await act(async () => {
      fireEvent.click(screen.getByTestId("upload-button"));
    });

    await waitFor(() => {
      const badges = screen.getAllByTestId("purchase-converted-badge");
      expect(badges.length).toBe(1);
    });
  });

  it("does not show a badge when original_currency is absent (legacy response)", async () => {
    mockUpload.mockResolvedValueOnce(MOCK_PREVIEW);
    renderPage();

    const input = screen.getByTestId("file-input") as HTMLInputElement;
    uploadFile(input, createHtmlFile());

    await act(async () => {
      fireEvent.click(screen.getByTestId("upload-button"));
    });

    await waitFor(() => {
      expect(screen.getByTestId("preview-state")).toBeDefined();
    });
    expect(screen.queryByTestId("purchase-converted-badge")).toBeNull();
  });

  it("shows the badge without a rate tooltip when exchange_rate is null", async () => {
    const previewWithConversion = {
      ...MOCK_PREVIEW,
      matches: [
        {
          ...MOCK_PREVIEW.matches[0],
          original_unit_price: "0.05",
          original_currency: "USD",
          exchange_rate: null,
        },
      ],
    };
    mockUpload.mockResolvedValueOnce(previewWithConversion);
    renderPage();

    const input = screen.getByTestId("file-input") as HTMLInputElement;
    uploadFile(input, createHtmlFile());

    await act(async () => {
      fireEvent.click(screen.getByTestId("upload-button"));
    });

    await waitFor(() => {
      const badge = screen.getByTestId("purchase-converted-badge");
      expect(badge).toBeDefined();
      expect(badge.getAttribute("title")).not.toContain("5.00");
    });
  });

  it("shows the reason for an unmatched currency-conversion-failed row", async () => {
    const previewWithFailedConversion = {
      ...MOCK_PREVIEW,
      unmatched: [
        {
          card_name_parsed: "Mana Drain",
          set_code_parsed: "VMA",
          unit_price: "0.00",
          order_number: "#5282199",
          skip_reason: "currency_conversion_failed",
        },
      ],
    };
    mockUpload.mockResolvedValueOnce(previewWithFailedConversion);
    renderPage();

    const input = screen.getByTestId("file-input") as HTMLInputElement;
    uploadFile(input, createHtmlFile());

    await act(async () => {
      fireEvent.click(screen.getByTestId("upload-button"));
    });

    await waitFor(() => {
      expect(screen.getByTestId("unmatched-section")).toBeDefined();
    });
    expect(screen.getByText(/currency_conversion_failed/)).toBeDefined();
  });

  /* ---- Back to upload ---- */

  it("back button returns to upload state from preview", async () => {
    mockUpload.mockResolvedValueOnce(MOCK_PREVIEW);
    renderPage();

    const input = screen.getByTestId("file-input") as HTMLInputElement;
    uploadFile(input, createHtmlFile());

    await act(async () => {
      fireEvent.click(screen.getByTestId("upload-button"));
    });

    await waitFor(() => {
      expect(screen.getByTestId("back-button")).toBeDefined();
    });

    fireEvent.click(screen.getByTestId("back-button"));
    expect(screen.getByTestId("upload-state")).toBeDefined();
  });
});
