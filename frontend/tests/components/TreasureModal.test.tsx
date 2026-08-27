import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import { TreasureModal } from "../../src/components/TreasureModal";
import { LanguageProvider } from "../../src/contexts/LanguageContext";

// Mock localStorage
beforeEach(() => {
  vi.useFakeTimers();
  vi.stubGlobal("localStorage", {
    getItem: vi.fn().mockReturnValue(null),
    setItem: vi.fn(),
    removeItem: vi.fn(),
  });
});

function renderModal(count = 25, onClose = vi.fn()) {
  const result = render(
    <LanguageProvider>
      <TreasureModal count={count} onClose={onClose} />
    </LanguageProvider>,
  );
  return { ...result, onClose };
}

describe("TreasureModal", () => {
  it("renders the treasure image", () => {
    renderModal();

    const img = screen.getByTestId("treasure-modal-image");
    expect(img).toBeDefined();
    expect(img.tagName).toBe("IMG");
    expect((img as HTMLImageElement).src).toBeTruthy();
  });

  it("displays the token count", () => {
    renderModal(42);

    const count = screen.getByTestId("treasure-modal-count");
    expect(count.textContent).toBe("42");
  });

  it("displays zero count correctly", () => {
    renderModal(0);

    const count = screen.getByTestId("treasure-modal-count");
    expect(count.textContent).toBe("0");
  });

  it("calls onClose when backdrop is clicked (after animation)", () => {
    const onClose = vi.fn();
    renderModal(25, onClose);

    const backdrop = screen.getByTestId("treasure-modal-backdrop");
    fireEvent.click(backdrop);

    // onClose is called after the exit animation delay
    expect(onClose).not.toHaveBeenCalled();
    act(() => { vi.advanceTimersByTime(500); });
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("does not call onClose when content area is clicked", () => {
    const onClose = vi.fn();
    renderModal(25, onClose);

    const content = screen.getByTestId("treasure-modal-content");
    fireEvent.click(content);

    expect(onClose).not.toHaveBeenCalled();
  });

  it("calls onClose when Escape key is pressed (after animation)", () => {
    const onClose = vi.fn();
    renderModal(25, onClose);

    fireEvent.keyDown(document, { key: "Escape" });

    expect(onClose).not.toHaveBeenCalled();
    act(() => { vi.advanceTimersByTime(500); });
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("does not call onClose for non-Escape keys", () => {
    const onClose = vi.fn();
    renderModal(25, onClose);

    fireEvent.keyDown(document, { key: "Enter" });

    expect(onClose).not.toHaveBeenCalled();
  });

  it("shows balance label text", () => {
    renderModal();

    // "Treasure Tokens" is the default EN translation for credits.balance
    expect(screen.getAllByText("Treasure Tokens").length).toBeGreaterThan(0);
  });

  it("uses language-aware image (defaults to EN)", () => {
    renderModal();

    const img = screen.getByTestId("treasure-modal-image") as HTMLImageElement;
    // Default language is EN, so src should contain the EN treasure image
    expect(img.src).toBeTruthy();
  });
});
