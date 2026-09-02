import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { EmptyState } from "../../src/components/EmptyState";

describe("EmptyState", () => {
  // Legacy API backward compat tests
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

  // New enhanced API tests
  it("renders title + description", () => {
    render(
      <EmptyState title="Empty Title" description="Some helpful description" />,
    );
    expect(screen.getByTestId("empty-state-title")).toHaveTextContent("Empty Title");
    expect(screen.getByTestId("empty-state-description")).toHaveTextContent(
      "Some helpful description",
    );
  });

  it("renders multiple actions via actions prop", () => {
    const onClick1 = vi.fn();
    const onClick2 = vi.fn();
    render(
      <EmptyState
        title="Empty"
        actions={[
          { label: "Primary", onClick: onClick1 },
          { label: "Secondary", onClick: onClick2, variant: "secondary" },
        ]}
      />,
    );
    expect(screen.getByText("Primary")).toBeInTheDocument();
    expect(screen.getByText("Secondary")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Primary"));
    expect(onClick1).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByText("Secondary"));
    expect(onClick2).toHaveBeenCalledTimes(1);
  });

  it("actions takes precedence over action when both provided", () => {
    const singleFn = vi.fn();
    const multiFn = vi.fn();
    render(
      <EmptyState
        title="Test"
        action={{ label: "Single", onClick: singleFn }}
        actions={[{ label: "Multi", onClick: multiFn }]}
      />,
    );
    expect(screen.queryByText("Single")).not.toBeInTheDocument();
    expect(screen.getByText("Multi")).toBeInTheDocument();
  });

  it("secondary variant button has correct classes", () => {
    render(
      <EmptyState
        title="Test"
        actions={[
          { label: "Ghost", onClick: vi.fn(), variant: "secondary" },
        ]}
      />,
    );
    const btn = screen.getByText("Ghost");
    expect(btn.className).toContain("border-slate-500");
    expect(btn.className).toContain("text-slate-300");
  });

  it("compact mode applies reduced padding", () => {
    render(<EmptyState message="Compact" compact />);
    const root = screen.getByTestId("empty-state");
    expect(root.className).toContain("py-6");
    expect(root.className).not.toContain("py-12");
  });

  it("all data-testid attributes present when title and description provided", () => {
    render(
      <EmptyState
        title="Title"
        description="Desc"
        icon={<span>icon</span>}
        actions={[{ label: "Act", onClick: vi.fn() }]}
      />,
    );
    expect(screen.getByTestId("empty-state")).toBeInTheDocument();
    expect(screen.getByTestId("empty-state-title")).toBeInTheDocument();
    expect(screen.getByTestId("empty-state-description")).toBeInTheDocument();
    expect(screen.getByTestId("empty-state-icon")).toBeInTheDocument();
    expect(screen.getByTestId("empty-state-actions")).toBeInTheDocument();
  });
});
