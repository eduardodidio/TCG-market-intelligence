import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { InlineEditField } from "../../src/components/InlineEditField";

describe("InlineEditField", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders display mode with current value", () => {
    render(<InlineEditField value="NM" onSave={vi.fn()} type="text" label="quality" />);
    expect(screen.getByTestId("inline-edit-display").textContent).toBe("NM");
    expect(screen.getByTestId("inline-edit-pencil")).toBeDefined();
  });

  it("shows edit mode when pencil is clicked", () => {
    render(<InlineEditField value="NM" onSave={vi.fn()} type="text" label="quality" />);
    fireEvent.click(screen.getByTestId("inline-edit-pencil"));
    expect(screen.getByTestId("inline-edit-input")).toBeDefined();
    expect(screen.getByTestId("inline-edit-save")).toBeDefined();
    expect(screen.getByTestId("inline-edit-cancel")).toBeDefined();
  });

  it("calls onSave with new value on Enter", async () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    render(<InlineEditField value="NM" onSave={onSave} type="text" label="quality" />);

    fireEvent.click(screen.getByTestId("inline-edit-pencil"));
    const input = screen.getByTestId("inline-edit-input");
    fireEvent.change(input, { target: { value: "SP" } });
    fireEvent.keyDown(input, { key: "Enter" });

    await waitFor(() => {
      expect(onSave).toHaveBeenCalledWith("SP");
    });
  });

  it("reverts to original value on Escape", () => {
    render(<InlineEditField value="NM" onSave={vi.fn()} type="text" label="quality" />);

    fireEvent.click(screen.getByTestId("inline-edit-pencil"));
    const input = screen.getByTestId("inline-edit-input");
    fireEvent.change(input, { target: { value: "changed" } });
    fireEvent.keyDown(input, { key: "Escape" });

    // Back to display mode with original value
    expect(screen.getByTestId("inline-edit-display").textContent).toBe("NM");
  });

  it("renders select dropdown with options in select mode", () => {
    const options = [
      { label: "Near Mint", value: "NM" },
      { label: "Slightly Played", value: "SP" },
    ];
    render(<InlineEditField value="NM" onSave={vi.fn()} type="select" options={options} label="quality" />);

    // In display mode, shows the label for the matching option
    expect(screen.getByTestId("inline-edit-display").textContent).toBe("Near Mint");

    fireEvent.click(screen.getByTestId("inline-edit-pencil"));
    const select = screen.getByTestId("inline-edit-select");
    expect(select).toBeDefined();
    expect(select.querySelectorAll("option")).toHaveLength(2);
  });

  it("calls onSave when save button is clicked", async () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    render(<InlineEditField value="old" onSave={onSave} type="text" label="extras" />);

    fireEvent.click(screen.getByTestId("inline-edit-pencil"));
    fireEvent.change(screen.getByTestId("inline-edit-input"), { target: { value: "new" } });
    fireEvent.click(screen.getByTestId("inline-edit-save"));

    await waitFor(() => {
      expect(onSave).toHaveBeenCalledWith("new");
    });
  });

  it("shows success indicator after save", async () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    render(<InlineEditField value="old" onSave={onSave} type="text" label="test" />);

    fireEvent.click(screen.getByTestId("inline-edit-pencil"));
    fireEvent.change(screen.getByTestId("inline-edit-input"), { target: { value: "new" } });
    fireEvent.click(screen.getByTestId("inline-edit-save"));

    await waitFor(() => {
      expect(screen.getByTestId("inline-edit-success")).toBeDefined();
    });
  });

  it("shows error and reverts on save failure", async () => {
    const onSave = vi.fn().mockRejectedValue(new Error("fail"));
    render(<InlineEditField value="original" onSave={onSave} type="text" label="test" />);

    fireEvent.click(screen.getByTestId("inline-edit-pencil"));
    fireEvent.change(screen.getByTestId("inline-edit-input"), { target: { value: "bad" } });
    fireEvent.click(screen.getByTestId("inline-edit-save"));

    await waitFor(() => {
      expect(screen.getByTestId("inline-edit-error")).toBeDefined();
    });
  });

  it("does not call onSave when value is unchanged", async () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    render(<InlineEditField value="same" onSave={onSave} type="text" label="test" />);

    fireEvent.click(screen.getByTestId("inline-edit-pencil"));
    // Don't change value, just press Enter
    fireEvent.keyDown(screen.getByTestId("inline-edit-input"), { key: "Enter" });

    // Should just close edit mode without calling onSave
    expect(onSave).not.toHaveBeenCalled();
    expect(screen.getByTestId("inline-edit-display")).toBeDefined();
  });

  it("shows (empty) placeholder when value is empty string", () => {
    render(<InlineEditField value="" onSave={vi.fn()} type="text" label="test" />);
    expect(screen.getByTestId("inline-edit-display").textContent).toBe("(empty)");
  });

  it("validates number type with min constraint", async () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    render(<InlineEditField value="1" onSave={onSave} type="number" label="qty" min={1} />);

    fireEvent.click(screen.getByTestId("inline-edit-pencil"));
    fireEvent.change(screen.getByTestId("inline-edit-input"), { target: { value: "0" } });
    fireEvent.click(screen.getByTestId("inline-edit-save"));

    await waitFor(() => {
      expect(screen.getByTestId("inline-edit-error")).toBeDefined();
    });
    expect(onSave).not.toHaveBeenCalled();
  });
});
