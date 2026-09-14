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
    // onClose is called after ANIM_DURATION (500ms) timeout
    expect(defaultProps.onClose).not.toHaveBeenCalled();
    act(() => { vi.advanceTimersByTime(500); });
    expect(defaultProps.onClose).toHaveBeenCalledTimes(1);
  });

  it("calls onClose after animation when backdrop is clicked", () => {
    render(<TreasureModal {...defaultProps} />);
    fireEvent.click(screen.getByTestId("treasure-modal-backdrop"));
    expect(defaultProps.onClose).not.toHaveBeenCalled();
    act(() => { vi.advanceTimersByTime(500); });
    expect(defaultProps.onClose).toHaveBeenCalledTimes(1);
  });

  it("does not close when content area is clicked", () => {
    render(<TreasureModal {...defaultProps} />);
    fireEvent.click(screen.getByTestId("treasure-modal-content"));
    act(() => { vi.advanceTimersByTime(500); });
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
});
