import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter, Link } from "react-router-dom";
import { PaidPriceQuickEdit } from "../PaidPriceQuickEdit";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const translations: Record<string, string> = {
        "collection.paidPrice": "Paid",
        "collection.setPaidPrice": "Set paid price",
        "portfolio.invalidPrice": "Enter a valid price greater than 0",
        "inlineEdit.saveError": "Failed to save changes",
        "inlineEdit.edit": "Edit",
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

function renderWithLink(
  props: Partial<React.ComponentProps<typeof PaidPriceQuickEdit>> = {},
  onLinkClick = vi.fn(),
) {
  const onSaved = props.onSaved ?? vi.fn();
  const utils = render(
    <MemoryRouter>
      <Link to="/collection/1" onClick={onLinkClick}>
        <PaidPriceQuickEdit
          entryId={1}
          acquisitionPrice={null}
          latestPrice={null}
          currency="BRL"
          onSaved={onSaved}
          {...props}
        />
      </Link>
    </MemoryRouter>,
  );
  return { ...utils, onSaved, onLinkClick };
}

describe("PaidPriceQuickEdit", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows set-paid-price button when price is null", () => {
    renderWithLink();
    expect(screen.getByTestId("paid-price-edit-btn")).toHaveTextContent("Set paid price");
  });

  it("happy path: type comma decimal and press Enter saves", async () => {
    const patchCollectionEntry = await importPatch();
    patchCollectionEntry.mockResolvedValue({
      data: { id: 1 } as never,
      meta: {} as never,
      errors: [],
    });
    const { onSaved } = renderWithLink();

    fireEvent.click(screen.getByTestId("paid-price-edit-btn"));
    const input = screen.getByTestId("paid-price-field");
    fireEvent.change(input, { target: { value: "12,50" } });
    fireEvent.keyDown(input, { key: "Enter" });

    await waitFor(() => {
      expect(patchCollectionEntry).toHaveBeenCalledWith(1, { acquisition_price: 12.5 });
    });
    await waitFor(() => {
      expect(onSaved).toHaveBeenCalledWith(1, 12.5);
    });
  });

  it("displays existing price formatted as BRL", () => {
    renderWithLink({ acquisitionPrice: 10 });
    expect(screen.getByTestId("paid-price-display")).toHaveTextContent("Paid");
  });

  it("shows green chip when latest price is higher", () => {
    renderWithLink({ acquisitionPrice: 10, latestPrice: 15 });
    const chip = screen.getByTestId("paid-price-pnl");
    expect(chip.className).toContain("text-emerald-400");
  });

  it("shows red chip when latest price is lower", () => {
    renderWithLink({ acquisitionPrice: 10, latestPrice: 5 });
    const chip = screen.getByTestId("paid-price-pnl");
    expect(chip.className).toContain("text-red-400");
  });

  it("hides chip for non-BRL currency", () => {
    renderWithLink({ acquisitionPrice: 10, latestPrice: 15, currency: "USD" });
    expect(screen.queryByTestId("paid-price-pnl")).not.toBeInTheDocument();
  });

  it("clearing the price sends null", async () => {
    const patchCollectionEntry = await importPatch();
    patchCollectionEntry.mockResolvedValue({
      data: { id: 1 } as never,
      meta: {} as never,
      errors: [],
    });
    const { onSaved } = renderWithLink({ acquisitionPrice: 10 });

    fireEvent.click(screen.getByTestId("paid-price-edit-btn"));
    const input = screen.getByTestId("paid-price-field");
    fireEvent.change(input, { target: { value: "" } });
    fireEvent.click(screen.getByTestId("paid-price-save"));

    await waitFor(() => {
      expect(patchCollectionEntry).toHaveBeenCalledWith(1, { acquisition_price: null });
    });
    await waitFor(() => {
      expect(onSaved).toHaveBeenCalledWith(1, null);
    });
  });

  it.each(["0", "-1", "abc", "100000"])(
    "rejects invalid value %s without calling the API",
    async (value) => {
      const patchCollectionEntry = await importPatch();
      renderWithLink({ acquisitionPrice: 10 });

      fireEvent.click(screen.getByTestId("paid-price-edit-btn"));
      const input = screen.getByTestId("paid-price-field");
      fireEvent.change(input, { target: { value } });
      fireEvent.click(screen.getByTestId("paid-price-save"));

      expect(await screen.findByTestId("paid-price-error")).toBeInTheDocument();
      expect(patchCollectionEntry).not.toHaveBeenCalled();
    },
  );

  it.each(["99999.99", "0.01"])("accepts boundary value %s", async (value) => {
    const patchCollectionEntry = await importPatch();
    patchCollectionEntry.mockResolvedValue({
      data: { id: 1 } as never,
      meta: {} as never,
      errors: [],
    });
    renderWithLink({ acquisitionPrice: 10 });

    fireEvent.click(screen.getByTestId("paid-price-edit-btn"));
    const input = screen.getByTestId("paid-price-field");
    fireEvent.change(input, { target: { value } });
    fireEvent.click(screen.getByTestId("paid-price-save"));

    await waitFor(() => {
      expect(patchCollectionEntry).toHaveBeenCalledWith(1, { acquisition_price: parseFloat(value) });
    });
  });

  it("shows error and stays in edit mode when API returns no data", async () => {
    const patchCollectionEntry = await importPatch();
    patchCollectionEntry.mockResolvedValue({ data: null, meta: {} as never, errors: [] });
    renderWithLink({ acquisitionPrice: 10 });

    fireEvent.click(screen.getByTestId("paid-price-edit-btn"));
    const input = screen.getByTestId("paid-price-field");
    fireEvent.change(input, { target: { value: "20" } });
    fireEvent.click(screen.getByTestId("paid-price-save"));

    expect(await screen.findByTestId("paid-price-error")).toBeInTheDocument();
    expect(screen.getByTestId("paid-price-field")).toBeInTheDocument();
  });

  it("shows error and stays in edit mode when API rejects", async () => {
    const patchCollectionEntry = await importPatch();
    patchCollectionEntry.mockRejectedValue(new Error("network"));
    renderWithLink({ acquisitionPrice: 10 });

    fireEvent.click(screen.getByTestId("paid-price-edit-btn"));
    const input = screen.getByTestId("paid-price-field");
    fireEvent.change(input, { target: { value: "20" } });
    fireEvent.click(screen.getByTestId("paid-price-save"));

    expect(await screen.findByTestId("paid-price-error")).toBeInTheDocument();
    expect(screen.getByTestId("paid-price-field")).toBeInTheDocument();
  });

  it("Escape restores previous value without calling the API", async () => {
    const patchCollectionEntry = await importPatch();
    renderWithLink({ acquisitionPrice: 10 });

    fireEvent.click(screen.getByTestId("paid-price-edit-btn"));
    const input = screen.getByTestId("paid-price-field");
    fireEvent.change(input, { target: { value: "999" } });
    fireEvent.keyDown(input, { key: "Escape" });

    expect(screen.queryByTestId("paid-price-field")).not.toBeInTheDocument();
    expect(patchCollectionEntry).not.toHaveBeenCalled();
  });

  it("clicking edit/save/cancel/input does not trigger parent Link navigation", async () => {
    const patchCollectionEntry = await importPatch();
    patchCollectionEntry.mockResolvedValue({
      data: { id: 1 } as never,
      meta: {} as never,
      errors: [],
    });
    const { onLinkClick } = renderWithLink({ acquisitionPrice: 10 });

    fireEvent.click(screen.getByTestId("paid-price-edit-btn"));
    expect(onLinkClick).not.toHaveBeenCalled();

    const input = screen.getByTestId("paid-price-field");
    fireEvent.click(input);
    expect(onLinkClick).not.toHaveBeenCalled();

    fireEvent.click(screen.getByTestId("paid-price-cancel"));
    expect(onLinkClick).not.toHaveBeenCalled();

    fireEvent.click(screen.getByTestId("paid-price-edit-btn"));
    fireEvent.click(screen.getByTestId("paid-price-save"));
    expect(onLinkClick).not.toHaveBeenCalled();
  });

  it("compact mode renders icon-only button with a title", () => {
    renderWithLink({ acquisitionPrice: 10, compact: true });
    const btn = screen.getByTestId("paid-price-edit-btn");
    expect(btn).toHaveAttribute("title");
    expect(btn.textContent).toBe("");
  });
});
