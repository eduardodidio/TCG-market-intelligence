import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { CopyCodeButton } from "../../src/components/CopyCodeButton";

function renderButton(props: { code: string; truncateAt?: number; className?: string }) {
  return render(
    <MemoryRouter>
      <CopyCodeButton {...props} />
    </MemoryRouter>,
  );
}

describe("CopyCodeButton", () => {
  let originalClipboard: Clipboard;

  beforeEach(() => {
    originalClipboard = navigator.clipboard;
    Object.defineProperty(navigator, "clipboard", {
      value: {
        writeText: vi.fn().mockResolvedValue(undefined),
      },
      writable: true,
      configurable: true,
    });
    vi.useFakeTimers();
  });

  afterEach(() => {
    Object.defineProperty(navigator, "clipboard", {
      value: originalClipboard,
      writable: true,
      configurable: true,
    });
    vi.useRealTimers();
  });

  it("renders truncated code by default at 8 chars", () => {
    renderButton({ code: "abc123def456gh78" });
    expect(screen.getByText("abc123de...")).toBeInTheDocument();
  });

  it("renders full code if shorter than truncateAt", () => {
    renderButton({ code: "short" });
    expect(screen.getByText("short")).toBeInTheDocument();
  });

  it("respects custom truncateAt", () => {
    renderButton({ code: "abc123def456gh78", truncateAt: 4 });
    expect(screen.getByText("abc1...")).toBeInTheDocument();
  });

  it("copies full code to clipboard on click", async () => {
    renderButton({ code: "full-share-code-here" });
    const btn = screen.getByTestId("copy-code-button");
    await act(async () => {
      fireEvent.click(btn);
    });
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith("full-share-code-here");
  });

  it("shows 'Copied!' feedback after click", async () => {
    renderButton({ code: "abc123def456gh78" });
    const btn = screen.getByTestId("copy-code-button");
    await act(async () => {
      fireEvent.click(btn);
    });
    expect(screen.getByTestId("copy-feedback")).toBeInTheDocument();
    expect(screen.getByText("Copied!")).toBeInTheDocument();
  });

  it("reverts to truncated code after 1.5s", async () => {
    renderButton({ code: "abc123def456gh78" });
    const btn = screen.getByTestId("copy-code-button");
    await act(async () => {
      fireEvent.click(btn);
    });
    expect(screen.getByText("Copied!")).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(1500);
    });

    expect(screen.queryByText("Copied!")).not.toBeInTheDocument();
    expect(screen.getByText("abc123de...")).toBeInTheDocument();
  });

  it("has title attribute with full code", () => {
    renderButton({ code: "my-full-share-code" });
    const btn = screen.getByTestId("copy-code-button");
    expect(btn).toHaveAttribute("title", "my-full-share-code");
  });

  it("stops event propagation on click", async () => {
    const parentHandler = vi.fn();
    render(
      <MemoryRouter>
        <div onClick={parentHandler}>
          <CopyCodeButton code="test-code" />
        </div>
      </MemoryRouter>,
    );
    const btn = screen.getByTestId("copy-code-button");
    await act(async () => {
      fireEvent.click(btn);
    });
    expect(parentHandler).not.toHaveBeenCalled();
  });
});
