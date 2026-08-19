import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { LoadingSpinner } from "../../src/components/LoadingSpinner";

describe("LoadingSpinner", () => {
  it("renders without errors", () => {
    render(<LoadingSpinner />);

    expect(screen.getByTestId("loading-spinner")).toBeDefined();
  });

  it("renders default loading message", () => {
    render(<LoadingSpinner />);

    expect(screen.getByText("Loading...")).toBeDefined();
  });

  it("renders custom message when provided", () => {
    render(<LoadingSpinner message="Fetching data..." />);

    expect(screen.getByText("Fetching data...")).toBeDefined();
  });

  it("has status role for accessibility", () => {
    render(<LoadingSpinner />);

    expect(screen.getByRole("status")).toBeDefined();
  });
});
