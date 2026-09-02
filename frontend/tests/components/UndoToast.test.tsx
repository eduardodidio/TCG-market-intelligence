import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { UndoToast } from "../../src/components/UndoToast";

describe("UndoToast", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("renders message and undo button", () => {
    render(
      <UndoToast
        message="Sol Ring deleted"
        onUndo={vi.fn()}
        onExpire={vi.fn()}
      />,
    );

    expect(screen.getByTestId("undo-toast")).toBeDefined();
    expect(screen.getByText("Sol Ring deleted")).toBeDefined();
    expect(screen.getByTestId("undo-toast-btn")).toBeDefined();
  });

  it("calls onUndo when button clicked", () => {
    const onUndo = vi.fn();
    render(
      <UndoToast
        message="Card deleted"
        onUndo={onUndo}
        onExpire={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByTestId("undo-toast-btn"));
    expect(onUndo).toHaveBeenCalledTimes(1);
  });

  it("calls onExpire after duration", () => {
    const onExpire = vi.fn();
    render(
      <UndoToast
        message="Card deleted"
        durationMs={5000}
        onUndo={vi.fn()}
        onExpire={onExpire}
      />,
    );

    expect(onExpire).not.toHaveBeenCalled();
    vi.advanceTimersByTime(5000);
    expect(onExpire).toHaveBeenCalledTimes(1);
  });

  it("does not call onExpire if undo clicked first", () => {
    const onExpire = vi.fn();
    const onUndo = vi.fn();
    render(
      <UndoToast
        message="Card deleted"
        durationMs={5000}
        onUndo={onUndo}
        onExpire={onExpire}
      />,
    );

    // Click undo at 3s
    vi.advanceTimersByTime(3000);
    fireEvent.click(screen.getByTestId("undo-toast-btn"));

    // Advance past original expiry
    vi.advanceTimersByTime(3000);

    expect(onUndo).toHaveBeenCalledTimes(1);
    expect(onExpire).not.toHaveBeenCalled();
  });

  it("progress bar element exists", () => {
    render(
      <UndoToast
        message="Card deleted"
        onUndo={vi.fn()}
        onExpire={vi.fn()}
      />,
    );

    expect(screen.getByTestId("undo-toast-progress")).toBeDefined();
  });
});
