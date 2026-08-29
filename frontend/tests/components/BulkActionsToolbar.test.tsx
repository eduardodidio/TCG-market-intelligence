import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { BulkActionsToolbar } from "../../src/components/BulkActionsToolbar";

// Wrap in i18n provider (setup.ts initializes i18n)

function renderToolbar(overrides: Partial<{
  selectedIds: Set<number>;
  onUpdate: (ids: number[], updates: Record<string, string>) => Promise<void>;
  onDelete: (ids: number[]) => Promise<void>;
  onCancel: () => void;
}> = {}) {
  const defaultProps = {
    selectedIds: new Set([1, 2, 3]),
    onUpdate: vi.fn().mockResolvedValue(undefined),
    onDelete: vi.fn().mockResolvedValue(undefined),
    onCancel: vi.fn(),
    ...overrides,
  };
  return { ...render(<BulkActionsToolbar {...defaultProps} />), ...defaultProps };
}

describe("BulkActionsToolbar", () => {
  it("renders with selected count", () => {
    renderToolbar();
    expect(screen.getByTestId("selected-count")).toHaveTextContent("3 selected");
  });

  it("is hidden when count is 0", () => {
    const { container } = render(
      <BulkActionsToolbar
        selectedIds={new Set()}
        onUpdate={vi.fn()}
        onDelete={vi.fn()}
        onCancel={vi.fn()}
      />
    );
    expect(container.innerHTML).toBe("");
  });

  it("cancel button fires onCancel", () => {
    const { onCancel } = renderToolbar();
    fireEvent.click(screen.getByTestId("bulk-cancel"));
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it("condition dropdown calls onUpdate with quality", async () => {
    const { onUpdate } = renderToolbar();
    fireEvent.click(screen.getByTestId("bulk-set-condition"));
    expect(screen.getByTestId("quality-popover")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("quality-option-NM"));
    await waitFor(() => {
      expect(onUpdate).toHaveBeenCalledWith([1, 2, 3], { quality: "NM" });
    });
  });

  it("language dropdown calls onUpdate with language", async () => {
    const { onUpdate } = renderToolbar();
    fireEvent.click(screen.getByTestId("bulk-set-language"));
    expect(screen.getByTestId("language-popover")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("language-option-EN"));
    await waitFor(() => {
      expect(onUpdate).toHaveBeenCalledWith([1, 2, 3], { language: "EN" });
    });
  });

  it("extras popover applies text input", async () => {
    const { onUpdate } = renderToolbar();
    fireEvent.click(screen.getByTestId("bulk-set-extras"));
    expect(screen.getByTestId("extras-popover")).toBeInTheDocument();
    fireEvent.change(screen.getByTestId("extras-input"), { target: { value: "foil" } });
    fireEvent.click(screen.getByTestId("extras-apply"));
    await waitFor(() => {
      expect(onUpdate).toHaveBeenCalledWith([1, 2, 3], { extras: "foil" });
    });
  });

  it("delete button shows confirmation dialog", () => {
    renderToolbar();
    fireEvent.click(screen.getByTestId("bulk-delete"));
    expect(screen.getByTestId("delete-confirm-dialog")).toBeInTheDocument();
    expect(screen.getByText(/permanently delete 3 card/i)).toBeInTheDocument();
  });

  it("confirm delete calls onDelete", async () => {
    const { onDelete } = renderToolbar();
    fireEvent.click(screen.getByTestId("bulk-delete"));
    fireEvent.click(screen.getByTestId("delete-confirm"));
    await waitFor(() => {
      expect(onDelete).toHaveBeenCalledWith([1, 2, 3]);
    });
  });

  it("cancel on delete dialog closes it", () => {
    renderToolbar();
    fireEvent.click(screen.getByTestId("bulk-delete"));
    expect(screen.getByTestId("delete-confirm-dialog")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("delete-cancel"));
    expect(screen.queryByTestId("delete-confirm-dialog")).not.toBeInTheDocument();
  });
});
