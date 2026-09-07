import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { CardImage } from "../../src/components/CardImage";

describe("CardImage", () => {
  it("shows skeleton before image loads", () => {
    render(<CardImage src="https://example.com/card.jpg" alt="Test Card" />);
    expect(screen.getByTestId("card-image-skeleton")).toBeDefined();
    expect(screen.getByTestId("card-image")).toBeDefined();
  });

  it("hides skeleton after image loads", () => {
    render(<CardImage src="https://example.com/card.jpg" alt="Test Card" />);
    const img = screen.getByTestId("card-image");
    fireEvent.load(img);
    expect(screen.queryByTestId("card-image-skeleton")).toBeNull();
  });

  it("shows fade-in transition class when loaded", () => {
    render(<CardImage src="https://example.com/card.jpg" alt="Test Card" />);
    const img = screen.getByTestId("card-image");
    // Before load: opacity-0
    expect(img.className).toContain("opacity-0");
    fireEvent.load(img);
    // After load: opacity-100
    expect(img.className).toContain("opacity-100");
  });

  it("shows fallback SVG on error when no fallbackSrc", () => {
    render(<CardImage src="https://example.com/bad.jpg" alt="Test Card" />);
    const img = screen.getByTestId("card-image");
    fireEvent.error(img);
    expect(screen.getByTestId("card-image-fallback")).toBeDefined();
  });

  it("renders img with correct src", () => {
    render(<CardImage src="https://example.com/card.jpg" alt="Test Card" />);
    const img = screen.getByTestId("card-image") as HTMLImageElement;
    expect(img.src).toBe("https://example.com/card.jpg");
  });

  it("renders fallback when src is null", () => {
    render(<CardImage src={null} alt="No image" />);
    expect(screen.getByTestId("card-image-fallback")).toBeDefined();
  });
});
