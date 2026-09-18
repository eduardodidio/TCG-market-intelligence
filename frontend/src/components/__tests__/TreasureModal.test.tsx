import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import { TreasureModal } from "../TreasureModal";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

vi.mock("../../hooks/useTreasureImage", () => ({
  useTreasureImage: () => "https://example.com/treasure.jpg",
}));

vi.mock("react-parallax-tilt", () => ({
  default: ({
    children,
  }: {
    children: React.ReactNode;
    [key: string]: unknown;
  }) => (
    <div data-testid="tilt-wrapper">
      {children}
    </div>
  ),
}));

describe("TreasureModal", () => {
  const defaultProps = {
    count: 42,
    onClose: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders modal in document.body via portal", () => {
    render(<TreasureModal {...defaultProps} />);
    const backdrop = document.body.querySelector(
      '[data-testid="treasure-modal-backdrop"]',
    );
    expect(backdrop).toBeInTheDocument();
  });

  it("calls onClose after animation when Escape key is pressed", () => {
    render(<TreasureModal {...defaultProps} />);
    fireEvent.keyDown(document, { key: "Escape" });
    // onClose is called after ANIM_DURATION (600ms) timeout
    expect(defaultProps.onClose).not.toHaveBeenCalled();
    act(() => { vi.advanceTimersByTime(600); });
    expect(defaultProps.onClose).toHaveBeenCalledTimes(1);
  });

  it("calls onClose after animation when backdrop is clicked", () => {
    render(<TreasureModal {...defaultProps} />);
    fireEvent.click(screen.getByTestId("treasure-modal-backdrop"));
    expect(defaultProps.onClose).not.toHaveBeenCalled();
    act(() => { vi.advanceTimersByTime(600); });
    expect(defaultProps.onClose).toHaveBeenCalledTimes(1);
  });

  it("does not close when content area is clicked", () => {
    render(<TreasureModal {...defaultProps} />);
    fireEvent.click(screen.getByTestId("treasure-modal-content"));
    act(() => { vi.advanceTimersByTime(600); });
    expect(defaultProps.onClose).not.toHaveBeenCalled();
  });

  it("displays the credit count", () => {
    render(<TreasureModal {...defaultProps} />);
    expect(screen.getByTestId("treasure-modal-count")).toHaveTextContent("42");
  });

  it("renders the treasure image", () => {
    render(<TreasureModal {...defaultProps} />);
    const img = screen.getByTestId("treasure-modal-image");
    expect(img).toHaveAttribute("src", "https://example.com/treasure.jpg");
  });

  it("uses smooth easing curve without bounce overshoot", () => {
    render(<TreasureModal {...defaultProps} />);
    const content = screen.getByTestId("treasure-modal-content");
    expect(content.style.transition).toContain("cubic-bezier(0.16, 1, 0.3, 1)");
    // Must NOT contain the old bouncy easing
    expect(content.style.transition).not.toContain("1.56");
  });

  it("applies golden shimmer wrapper when modal is open", async () => {
    render(<TreasureModal {...defaultProps} />);
    // Flush requestAnimationFrame to trigger phase → "open"
    await act(async () => { vi.advanceTimersByTime(16); });
    const shimmerWrapper = screen.getByTestId("treasure-shimmer-wrapper");
    expect(shimmerWrapper).toHaveClass("treasure-golden-shimmer");
  });

  it("applies treasure-modal-glow class to image when open", async () => {
    render(<TreasureModal {...defaultProps} />);
    await act(async () => { vi.advanceTimersByTime(16); });
    const img = screen.getByTestId("treasure-modal-image");
    expect(img).toHaveClass("treasure-modal-glow");
  });

  it("applies float animation class after enter transition completes", async () => {
    render(<TreasureModal {...defaultProps} />);
    const content = screen.getByTestId("treasure-modal-content");
    // Flush rAF to trigger phase → "open"
    await act(async () => { vi.advanceTimersByTime(16); });
    // Float should NOT be active yet (enter transition still in progress)
    expect(content).not.toHaveClass("treasure-float");
    // After ANIM_DURATION (600ms) the float class should be applied
    await act(async () => { vi.advanceTimersByTime(600); });
    expect(content).toHaveClass("treasure-float");
  });

  it("removes float animation when leaving", async () => {
    render(<TreasureModal {...defaultProps} />);
    // Enter and wait for float
    await act(async () => { vi.advanceTimersByTime(16); });
    await act(async () => { vi.advanceTimersByTime(600); });
    const content = screen.getByTestId("treasure-modal-content");
    expect(content).toHaveClass("treasure-float");
    // Trigger close
    fireEvent.keyDown(document, { key: "Escape" });
    expect(content).not.toHaveClass("treasure-float");
  });
});
