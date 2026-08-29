import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { BatchPreviewTable, type ParsedEntry } from "../../src/components/BatchPreviewTable";

const validEntry: ParsedEntry = {
  line_number: 1,
  raw_text: "2 Lightning Bolt [MH2]",
  quantity: 2,
  name: "Lightning Bolt",
  set_code: "MH2",
  quality: "NM",
  language: "EN",
  extras: null,
  error: null,
};

const errorEntry: ParsedEntry = {
  line_number: 2,
  raw_text: "bad line",
  quantity: 1,
  name: "",
  set_code: null,
  quality: null,
  language: null,
  extras: null,
  error: "Could not parse card name",
};

describe("BatchPreviewTable", () => {
  it("renders rows with correct data", () => {
    render(
      <BatchPreviewTable
        entries={[validEntry]}
        onRemove={vi.fn()}
        onUpdateEntry={vi.fn()}
      />,
    );

    expect(screen.getByTestId("preview-row-1")).toBeInTheDocument();
    expect(screen.getByText("Lightning Bolt")).toBeInTheDocument();
    expect(screen.getByText("MH2")).toBeInTheDocument();
  });

  it("shows valid/error counts", () => {
    render(
      <BatchPreviewTable
        entries={[validEntry, errorEntry]}
        onRemove={vi.fn()}
        onUpdateEntry={vi.fn()}
      />,
    );

    const counts = screen.getByTestId("preview-counts");
    expect(counts.textContent).toContain("1 valid");
    expect(counts.textContent).toContain("1 errors");
  });

  it("qty input fires onUpdateEntry", () => {
    const onUpdate = vi.fn();
    render(
      <BatchPreviewTable
        entries={[validEntry]}
        onRemove={vi.fn()}
        onUpdateEntry={onUpdate}
      />,
    );

    const qtyInput = screen.getByTestId("qty-input-1") as HTMLInputElement;
    expect(qtyInput.value).toBe("2");

    fireEvent.change(qtyInput, { target: { value: "4" } });
    expect(onUpdate).toHaveBeenCalledWith(1, "quantity", 4);
  });

  it("quality dropdown selects correct value", () => {
    const onUpdate = vi.fn();
    render(
      <BatchPreviewTable
        entries={[validEntry]}
        onRemove={vi.fn()}
        onUpdateEntry={onUpdate}
      />,
    );

    const qualitySelect = screen.getByTestId("quality-select-1");
    fireEvent.change(qualitySelect, { target: { value: "SP" } });

    expect(onUpdate).toHaveBeenCalledWith(1, "quality", "SP");
  });

  it("remove button fires callback", () => {
    const onRemove = vi.fn();
    render(
      <BatchPreviewTable
        entries={[validEntry]}
        onRemove={onRemove}
        onUpdateEntry={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByTestId("remove-row-1"));
    expect(onRemove).toHaveBeenCalledWith(1);
  });

  it("error row has red styling", () => {
    render(
      <BatchPreviewTable
        entries={[errorEntry]}
        onRemove={vi.fn()}
        onUpdateEntry={vi.fn()}
      />,
    );

    const row = screen.getByTestId("preview-row-2");
    expect(row.className).toContain("bg-red-900");
  });

  it("error row shows error icon with tooltip", () => {
    render(
      <BatchPreviewTable
        entries={[errorEntry]}
        onRemove={vi.fn()}
        onUpdateEntry={vi.fn()}
      />,
    );

    const errorIcon = screen.getByTestId("error-icon-2");
    expect(errorIcon).toHaveAttribute("title", "Could not parse card name");
  });

  it("disables inputs for error rows", () => {
    render(
      <BatchPreviewTable
        entries={[errorEntry]}
        onRemove={vi.fn()}
        onUpdateEntry={vi.fn()}
      />,
    );

    const qtyInput = screen.getByTestId("qty-input-2") as HTMLInputElement;
    expect(qtyInput.disabled).toBe(true);

    const qualitySelect = screen.getByTestId("quality-select-2") as HTMLSelectElement;
    expect(qualitySelect.disabled).toBe(true);
  });
});
