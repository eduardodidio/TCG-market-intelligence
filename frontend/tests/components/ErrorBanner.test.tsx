import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ErrorBanner } from "../../src/components/ErrorBanner";

describe("ErrorBanner", () => {
  it("renders the error message", () => {
    render(<ErrorBanner message="Something went wrong" />);

    expect(screen.getByText("Something went wrong")).toBeDefined();
  });

  it("renders with alert role for accessibility", () => {
    render(<ErrorBanner message="Error occurred" />);

    expect(screen.getByRole("alert")).toBeDefined();
  });

  it("renders retry button when onRetry is provided", () => {
    const onRetry = vi.fn();
    render(<ErrorBanner message="Error" onRetry={onRetry} />);

    const button = screen.getByText("Retry");
    expect(button).toBeDefined();
  });

  it("does not render retry button when onRetry is not provided", () => {
    render(<ErrorBanner message="Error" />);

    expect(screen.queryByText("Retry")).toBeNull();
  });

  it("fires onRetry callback when retry button is clicked", () => {
    const onRetry = vi.fn();
    render(<ErrorBanner message="Error" onRetry={onRetry} />);

    fireEvent.click(screen.getByText("Retry"));

    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it("applies correct data-testid", () => {
    render(<ErrorBanner message="Error" />);

    expect(screen.getByTestId("error-banner")).toBeDefined();
  });

  // --- Variant tests (F07-T07) ---

  it("renders inline variant by default", () => {
    render(<ErrorBanner message="Inline error" />);
    const banner = screen.getByTestId("error-banner");
    expect(banner.getAttribute("data-variant")).toBe("inline");
  });

  it("renders inline variant explicitly", () => {
    render(<ErrorBanner message="Inline error" variant="inline" />);
    const banner = screen.getByTestId("error-banner");
    expect(banner.getAttribute("data-variant")).toBe("inline");
    // Should have the compact styling (border)
    expect(banner.classList.contains("rounded-md")).toBe(true);
  });

  it("renders full variant with centered layout and icon", () => {
    render(<ErrorBanner message="Full page error" variant="full" />);
    const banner = screen.getByTestId("error-banner");
    expect(banner.getAttribute("data-variant")).toBe("full");
    // Full variant has centered text
    expect(banner.classList.contains("text-center")).toBe(true);
    // Should have SVG icon
    const svg = banner.querySelector("svg");
    expect(svg).not.toBeNull();
  });

  it("renders retry button in full variant", () => {
    const onRetry = vi.fn();
    render(
      <ErrorBanner message="Full error" variant="full" onRetry={onRetry} />,
    );

    const button = screen.getByText("Retry");
    fireEvent.click(button);
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it("detects network error and shows connection message", () => {
    render(<ErrorBanner message="Failed to fetch" />);
    expect(
      screen.getByText(
        "Unable to connect to the server. Please check your connection.",
      ),
    ).toBeDefined();
  });

  it("detects network error (TypeError variant)", () => {
    render(<ErrorBanner message="NetworkError when attempting to fetch" />);
    expect(
      screen.getByText(
        "Unable to connect to the server. Please check your connection.",
      ),
    ).toBeDefined();
  });

  it("shows original message for non-network errors", () => {
    render(<ErrorBanner message="HTTP_500: Internal Server Error" />);
    expect(
      screen.getByText("HTTP_500: Internal Server Error"),
    ).toBeDefined();
  });
});
