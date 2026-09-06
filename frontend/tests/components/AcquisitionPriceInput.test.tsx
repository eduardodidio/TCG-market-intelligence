import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { AcquisitionPriceInput } from "../../src/components/AcquisitionPriceInput";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const map: Record<string, string> = {
        "portfolio.acquisitionPrice": "Acquisition Price",
        "portfolio.acquiredAt": "Acquired On",
        "portfolio.invalidPrice": "Enter a valid price",
        "inlineEdit.edit": "Edit",
        "inlineEdit.empty": "(empty)",
        "inlineEdit.saveError": "Failed to save",
      };
      return map[key] || key;
    },
  }),
}));

vi.mock("../../src/utils/format", () => ({
  formatCurrency: (value: number | null, _currency: string) => {
    if (value == null) return "--";
    return `R$ ${value.toFixed(2)}`;
  },
}));

const mockPatchCollectionEntry = vi.fn();

vi.mock("../../src/api/collection", () => ({
  patchCollectionEntry: (...args: unknown[]) => mockPatchCollectionEntry(...args),
}));

beforeEach(() => {
  vi.clearAllMocks();
});

describe("AcquisitionPriceInput", () => {
  it("renders empty state when no price", () => {
    render(
      <AcquisitionPriceInput
        entryId={1}
        acquisitionPrice={null}
        acquiredAt={null}
      />,
    );
    const emptyLabels = screen.getAllByText("(empty)");
    expect(emptyLabels.length).toBe(2); // price and date both empty
    expect(screen.getByText("Acquisition Price")).toBeInTheDocument();
    expect(screen.getByText("Acquired On")).toBeInTheDocument();
  });

  it("renders formatted price when set", () => {
    render(
      <AcquisitionPriceInput
        entryId={1}
        acquisitionPrice={12.50}
        acquiredAt="2026-01-15"
      />,
    );
    expect(screen.getByText("R$ 12.50")).toBeInTheDocument();
    expect(screen.getByText("2026-01-15")).toBeInTheDocument();
  });

  it("enters edit mode when pencil clicked", () => {
    render(
      <AcquisitionPriceInput
        entryId={1}
        acquisitionPrice={null}
        acquiredAt={null}
      />,
    );
    fireEvent.click(screen.getByTestId("acquisition-price-edit-btn"));
    expect(screen.getByTestId("acquisition-price-field")).toBeInTheDocument();
  });

  it("saves price on save button click", async () => {
    mockPatchCollectionEntry.mockResolvedValue({
      data: { acquisition_price: 25.0 },
      errors: [],
    });

    const onSaved = vi.fn();
    render(
      <AcquisitionPriceInput
        entryId={1}
        acquisitionPrice={null}
        acquiredAt={null}
        onSaved={onSaved}
      />,
    );

    fireEvent.click(screen.getByTestId("acquisition-price-edit-btn"));
    const input = screen.getByTestId("acquisition-price-field");
    fireEvent.change(input, { target: { value: "25.00" } });
    fireEvent.click(screen.getByTestId("acquisition-price-save"));

    await waitFor(() => {
      expect(mockPatchCollectionEntry).toHaveBeenCalledWith(1, { acquisition_price: 25.0 });
      expect(onSaved).toHaveBeenCalledWith(25.0, null);
    });
  });

  it("shows error for invalid price", async () => {
    render(
      <AcquisitionPriceInput
        entryId={1}
        acquisitionPrice={null}
        acquiredAt={null}
      />,
    );

    fireEvent.click(screen.getByTestId("acquisition-price-edit-btn"));
    const input = screen.getByTestId("acquisition-price-field");
    fireEvent.change(input, { target: { value: "-5" } });
    fireEvent.click(screen.getByTestId("acquisition-price-save"));

    expect(screen.getByText("Enter a valid price")).toBeInTheDocument();
    expect(mockPatchCollectionEntry).not.toHaveBeenCalled();
  });
});
