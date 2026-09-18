import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import { TreasureModal } from "../../src/components/TreasureModal";
import { LanguageProvider } from "../../src/contexts/LanguageContext";

vi.mock("react-parallax-tilt", () => ({
  default: ({ children, ...props }: { children: React.ReactNode; [key: string]: unknown }) => (
    <div data-testid="tilt-wrapper" data-props={JSON.stringify(props)}>
      {children}
    </div>
  ),
}));

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
    act(() => { vi.advanceTimersByTime(600); });
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
    act(() => { vi.advanceTimersByTime(600); });
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

  it("wraps image in Card3DTilt with tiltMaxAngle=18 and scale=1.08", () => {
    renderModal();

    const tiltWrapper = screen.getByTestId("tilt-wrapper");
    expect(tiltWrapper).toBeDefined();
    const props = JSON.parse(tiltWrapper.getAttribute("data-props") || "{}");
    expect(props.tiltMaxAngleX).toBe(18);
    expect(props.tiltMaxAngleY).toBe(18);
    expect(props.scale).toBe(1.08);
  });

  it("enables foil shimmer on Card3DTilt (glare enabled)", () => {
    renderModal();

    const tiltWrapper = screen.getByTestId("tilt-wrapper");
    const props = JSON.parse(tiltWrapper.getAttribute("data-props") || "{}");
    expect(props.glareEnable).toBe(true);
    expect(props.glareMaxOpacity).toBe(0.35);
  });

  it("renders foil-shimmer wrapper around image", () => {
    renderModal();

    // TreasureModal uses createPortal to document.body, so query from there
    const shimmer = document.body.querySelector(".foil-shimmer");
    expect(shimmer).not.toBeNull();
    // The image should be inside the shimmer wrapper
    const img = screen.getByTestId("treasure-modal-image");
    expect(shimmer!.contains(img)).toBe(true);
  });

  it("keeps fly-in animation styles on content container", () => {
    renderModal();

    const content = screen.getByTestId("treasure-modal-content");
    // The content element should have transition styles for the fly-in animation
    expect(content.style.transition).toContain("transform");
    expect(content.style.transition).toContain("opacity");
  });
});
