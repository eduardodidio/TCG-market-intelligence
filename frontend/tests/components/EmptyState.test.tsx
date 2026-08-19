import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { EmptyState } from "../../src/components/EmptyState";

describe("EmptyState", () => {
  it("renders the message text", () => {
    render(<EmptyState message="No cards found" />);
    expect(screen.getByText("No cards found")).toBeDefined();
  });

  it("renders with data-testid", () => {
    render(<EmptyState message="Empty" />);
    expect(screen.getByTestId("empty-state")).toBeDefined();
  });

  it("renders action button when action prop is provided", () => {
    const onClick = vi.fn();
    render(
      <EmptyState
        message="No results"
        action={{ label: "Clear filters", onClick }}
      />,
    );

    const button = screen.getByTestId("empty-state-action");
    expect(button).toBeDefined();
    expect(button.textContent).toBe("Clear filters");
  });

  it("fires action callback when button is clicked", () => {
    const onClick = vi.fn();
    render(
      <EmptyState
        message="No results"
        action={{ label: "Retry", onClick }}
      />,
    );

    fireEvent.click(screen.getByTestId("empty-state-action"));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("does not render action button when action is not provided", () => {
    render(<EmptyState message="Nothing here" />);
    expect(screen.queryByTestId("empty-state-action")).toBeNull();
  });

  it("renders icon when provided", () => {
    render(
      <EmptyState
        message="No data"
        icon={<span data-testid="custom-icon">X</span>}
      />,
    );
    expect(screen.getByTestId("empty-state-icon")).toBeDefined();
    expect(screen.getByTestId("custom-icon")).toBeDefined();
  });

  it("does not render icon wrapper when icon is not provided", () => {
    render(<EmptyState message="No data" />);
    expect(screen.queryByTestId("empty-state-icon")).toBeNull();
  });
});
