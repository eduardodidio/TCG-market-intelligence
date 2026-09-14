import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { AcquisitionPriceInput } from "../AcquisitionPriceInput";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const translations: Record<string, string> = {
        "portfolio.acquisitionPrice": "Acquisition Price",
        "portfolio.acquiredAt": "Acquired At",
        "portfolio.invalidPrice": "Enter a valid price greater than 0",
        "inlineEdit.saveError": "Failed to save changes",
        "inlineEdit.edit": "Edit",
        "inlineEdit.empty": "(empty)",
      };
      return translations[key] || key;
    },
  }),
}));

vi.mock("../../api/collection", () => ({
  patchCollectionEntry: vi.fn(),
}));

async function importPatch() {
  const { patchCollectionEntry } = await import("../../api/collection");
  return vi.mocked(patchCollectionEntry);
}

describe("AcquisitionPriceInput", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("clearing the price field on save sends acquisition_price: null", async () => {
    const patchCollectionEntry = await importPatch();
    patchCollectionEntry.mockResolvedValue({
      data: { id: 1 } as never,
      meta: {} as never,
      errors: [],
    });
    const onSaved = vi.fn();
    render(
      <AcquisitionPriceInput entryId={1} acquisitionPrice={10} acquiredAt={null} onSaved={onSaved} />,
    );

    fireEvent.click(screen.getByTestId("acquisition-price-edit-btn"));
    const input = screen.getByTestId("acquisition-price-field");
    fireEvent.change(input, { target: { value: "" } });
    fireEvent.click(screen.getByTestId("acquisition-price-save"));

    await waitFor(() => {
      expect(patchCollectionEntry).toHaveBeenCalledWith(1, { acquisition_price: null });
    });
    await waitFor(() => {
      expect(onSaved).toHaveBeenCalledWith(null, null);
    });
  });

  it("clearing the date field on save sends acquired_at: null", async () => {
    const patchCollectionEntry = await importPatch();
    patchCollectionEntry.mockResolvedValue({
      data: { id: 1 } as never,
      meta: {} as never,
      errors: [],
    });
    const onSaved = vi.fn();
    render(
      <AcquisitionPriceInput
        entryId={1}
        acquisitionPrice={null}
        acquiredAt="2026-01-01"
        onSaved={onSaved}
      />,
    );

    fireEvent.click(screen.getByTestId("acquired-at-edit-btn"));
    const input = screen.getByTestId("acquired-at-field");
    fireEvent.change(input, { target: { value: "" } });
    fireEvent.click(screen.getByTestId("acquired-at-save"));

    await waitFor(() => {
      expect(patchCollectionEntry).toHaveBeenCalledWith(1, { acquired_at: null });
    });
    await waitFor(() => {
      expect(onSaved).toHaveBeenCalledWith(null, null);
    });
  });

  it("saving a valid price sends the numeric value", async () => {
    const patchCollectionEntry = await importPatch();
    patchCollectionEntry.mockResolvedValue({
      data: { id: 1 } as never,
      meta: {} as never,
      errors: [],
    });
    const onSaved = vi.fn();
    render(
      <AcquisitionPriceInput entryId={1} acquisitionPrice={null} acquiredAt={null} onSaved={onSaved} />,
    );

    fireEvent.click(screen.getByTestId("acquisition-price-edit-btn"));
    const input = screen.getByTestId("acquisition-price-field");
    fireEvent.change(input, { target: { value: "25.5" } });
    fireEvent.click(screen.getByTestId("acquisition-price-save"));

    await waitFor(() => {
      expect(patchCollectionEntry).toHaveBeenCalledWith(1, { acquisition_price: 25.5 });
    });
    await waitFor(() => {
      expect(onSaved).toHaveBeenCalledWith(25.5, null);
    });
  });

  it("rejects invalid price without calling the API", async () => {
    const patchCollectionEntry = await importPatch();
    render(
      <AcquisitionPriceInput entryId={1} acquisitionPrice={null} acquiredAt={null} />,
    );

    fireEvent.click(screen.getByTestId("acquisition-price-edit-btn"));
    const input = screen.getByTestId("acquisition-price-field");
    fireEvent.change(input, { target: { value: "-5" } });
    fireEvent.click(screen.getByTestId("acquisition-price-save"));

    expect(await screen.findByTestId("acquisition-error")).toBeInTheDocument();
    expect(patchCollectionEntry).not.toHaveBeenCalled();
  });
});
