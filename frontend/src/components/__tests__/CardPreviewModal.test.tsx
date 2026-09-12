import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { CardPreviewModal } from "../CardPreviewModal";

vi.mock("react-parallax-tilt", () => ({
  default: ({ children, ...props }: { children: React.ReactNode; [key: string]: unknown }) => (
    <div data-testid="tilt-wrapper" data-props={JSON.stringify(props)}>
      {children}
    </div>
  ),
}));

describe("CardPreviewModal", () => {
  const defaultProps = {
    imageUrl: "https://example.com/card.jpg",
    cardName: "Black Lotus",
    onClose: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders image with correct src and alt", () => {
    render(<CardPreviewModal {...defaultProps} />);
    const img = screen.getByRole("img");
    expect(img).toHaveAttribute("src", defaultProps.imageUrl);
    expect(img).toHaveAttribute("alt", defaultProps.cardName);
  });

  it("renders card name below image", () => {
    render(<CardPreviewModal {...defaultProps} />);
    expect(screen.getByText("Black Lotus")).toBeInTheDocument();
  });

  it("calls onClose when backdrop is clicked", () => {
    render(<CardPreviewModal {...defaultProps} />);
    fireEvent.click(screen.getByTestId("modal-backdrop"));
    expect(defaultProps.onClose).toHaveBeenCalledTimes(1);
  });

  it("does not call onClose when card area is clicked", () => {
    render(<CardPreviewModal {...defaultProps} />);
    fireEvent.click(screen.getByRole("img"));
    expect(defaultProps.onClose).not.toHaveBeenCalled();
  });

  it("calls onClose when Escape key is pressed", () => {
    render(<CardPreviewModal {...defaultProps} />);
    fireEvent.keyDown(document, { key: "Escape" });
    expect(defaultProps.onClose).toHaveBeenCalledTimes(1);
  });

  it("calls onClose when close button is clicked", () => {
    render(<CardPreviewModal {...defaultProps} />);
    fireEvent.click(screen.getByLabelText("Close"));
    expect(defaultProps.onClose).toHaveBeenCalledTimes(1);
  });

  it("passes isFoil to Card3DTilt", () => {
    const { container } = render(
      <CardPreviewModal {...defaultProps} isFoil={true} />
    );
    const shimmer = container.querySelector(".foil-shimmer");
    expect(shimmer).toBeInTheDocument();
  });

  it("renders without foil shimmer when isFoil is false", () => {
    const { container } = render(
      <CardPreviewModal {...defaultProps} isFoil={false} />
    );
    const shimmer = container.querySelector(".foil-shimmer");
    expect(shimmer).not.toBeInTheDocument();
  });

  it("prevents body scroll while open", () => {
    const { unmount } = render(<CardPreviewModal {...defaultProps} />);
    expect(document.body.style.overflow).toBe("hidden");
    unmount();
    expect(document.body.style.overflow).not.toBe("hidden");
  });

  it("renders Card3DTilt with tiltMaxAngle=18", () => {
    render(<CardPreviewModal {...defaultProps} />);
    const tiltWrapper = screen.getByTestId("tilt-wrapper");
    const props = JSON.parse(tiltWrapper.getAttribute("data-props") || "{}");
    expect(props.tiltMaxAngleX).toBe(18);
    expect(props.tiltMaxAngleY).toBe(18);
  });

  it("has role=dialog and aria-modal=true on the backdrop", () => {
    render(<CardPreviewModal {...defaultProps} />);
    const backdrop = screen.getByTestId("modal-backdrop");
    expect(backdrop).toHaveAttribute("role", "dialog");
    expect(backdrop).toHaveAttribute("aria-modal", "true");
  });

  it("has aria-label matching the card name", () => {
    render(<CardPreviewModal {...defaultProps} />);
    const backdrop = screen.getByTestId("modal-backdrop");
    expect(backdrop).toHaveAttribute("aria-label", "Black Lotus");
  });

  it("does not call onClose for non-Escape keys", () => {
    render(<CardPreviewModal {...defaultProps} />);
    fireEvent.keyDown(document, { key: "Enter" });
    fireEvent.keyDown(document, { key: "Tab" });
    expect(defaultProps.onClose).not.toHaveBeenCalled();
  });
});
