import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { CardHoverPreview } from "../../src/components/CardHoverPreview";

describe("CardHoverPreview", () => {
  it("renders preview when visible with imageUrl", () => {
    render(<CardHoverPreview visible={true} imageUrl="https://example.com/card.jpg" x={100} y={200} />);
    expect(screen.getByTestId("card-hover-preview")).toBeDefined();
  });

  it("does not render when not visible", () => {
    render(<CardHoverPreview visible={false} imageUrl="https://example.com/card.jpg" x={100} y={200} />);
    expect(screen.queryByTestId("card-hover-preview")).toBeNull();
  });

  it("does not render when imageUrl is null", () => {
    render(<CardHoverPreview visible={true} imageUrl={null} x={100} y={200} />);
    expect(screen.queryByTestId("card-hover-preview")).toBeNull();
  });

  it("positions correctly", () => {
    render(<CardHoverPreview visible={true} imageUrl="https://example.com/card.jpg" x={150} y={250} />);
    const el = screen.getByTestId("card-hover-preview");
    expect(el.style.left).toBe("150px");
    expect(el.style.top).toBe("250px");
  });
});
