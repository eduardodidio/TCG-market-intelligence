import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { DeleteEntryButton } from "../../src/components/DeleteEntryButton";

describe("DeleteEntryButton", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders delete button", () => {
    render(<DeleteEntryButton onConfirm={vi.fn()} />);
    expect(screen.getByTestId("delete-entry-btn")).toBeDefined();
    expect(screen.getByText("Delete Entry")).toBeDefined();
  });

  it("shows confirmation dialog on click", () => {
    render(<DeleteEntryButton onConfirm={vi.fn()} />);
    fireEvent.click(screen.getByTestId("delete-entry-btn"));
    expect(screen.getByTestId("delete-confirm-dialog")).toBeDefined();
    expect(screen.getByTestId("delete-confirm-btn")).toBeDefined();
    expect(screen.getByTestId("delete-cancel-btn")).toBeDefined();
  });

  it("shows entry name in confirmation message when provided", () => {
    render(<DeleteEntryButton onConfirm={vi.fn()} entryName="Lightning Bolt" />);
    fireEvent.click(screen.getByTestId("delete-entry-btn"));
    expect(screen.getByTestId("delete-confirm-dialog").textContent).toContain("Lightning Bolt");
  });

  it("calls onConfirm when confirm is clicked", async () => {
    const onConfirm = vi.fn().mockResolvedValue(undefined);
    render(<DeleteEntryButton onConfirm={onConfirm} />);
    fireEvent.click(screen.getByTestId("delete-entry-btn"));
    fireEvent.click(screen.getByTestId("delete-confirm-btn"));

    await waitFor(() => {
      expect(onConfirm).toHaveBeenCalledTimes(1);
    });
  });

  it("dismisses dialog on cancel", () => {
    render(<DeleteEntryButton onConfirm={vi.fn()} />);
    fireEvent.click(screen.getByTestId("delete-entry-btn"));
    expect(screen.getByTestId("delete-confirm-dialog")).toBeDefined();

    fireEvent.click(screen.getByTestId("delete-cancel-btn"));
    expect(screen.queryByTestId("delete-confirm-dialog")).toBeNull();
    expect(screen.getByTestId("delete-entry-btn")).toBeDefined();
  });

  it("does not call onConfirm when cancel is clicked", () => {
    const onConfirm = vi.fn();
    render(<DeleteEntryButton onConfirm={onConfirm} />);
    fireEvent.click(screen.getByTestId("delete-entry-btn"));
    fireEvent.click(screen.getByTestId("delete-cancel-btn"));
    expect(onConfirm).not.toHaveBeenCalled();
  });
});
