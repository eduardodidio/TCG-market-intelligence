import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { FormatHelpSection } from "../../src/components/FormatHelpSection";

describe("FormatHelpSection", () => {
  it("renders collapsed by default", () => {
    render(<FormatHelpSection />);
    expect(screen.getByTestId("format-help-section")).toBeInTheDocument();
    expect(screen.getByTestId("format-help-toggle")).toBeInTheDocument();
    expect(screen.queryByTestId("format-help-content")).not.toBeInTheDocument();
  });

  it("expands on click to show format examples", () => {
    render(<FormatHelpSection />);

    fireEvent.click(screen.getByTestId("format-help-toggle"));

    expect(screen.getByTestId("format-help-content")).toBeInTheDocument();
    expect(screen.getByText(/Lightning Bolt/)).toBeInTheDocument();
  });

  it("collapses again on second click", () => {
    render(<FormatHelpSection />);

    fireEvent.click(screen.getByTestId("format-help-toggle"));
    expect(screen.getByTestId("format-help-content")).toBeInTheDocument();

    fireEvent.click(screen.getByTestId("format-help-toggle"));
    expect(screen.queryByTestId("format-help-content")).not.toBeInTheDocument();
  });
});
