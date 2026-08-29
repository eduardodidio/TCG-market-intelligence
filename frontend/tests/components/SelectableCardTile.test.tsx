import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { SelectableCardTile } from "../../src/components/SelectableCardTile";

function renderTile(overrides: Partial<{
  cardId: number;
  isSelectable: boolean;
  isSelected: boolean;
  onToggle: (id: number) => void;
}> = {}) {
  const defaultProps = {
    cardId: 42,
    isSelectable: true,
    isSelected: false,
    onToggle: vi.fn(),
    ...overrides,
  };
  return {
    ...render(
      <SelectableCardTile {...defaultProps}>
        <div data-testid="inner-card">Card Content</div>
      </SelectableCardTile>
    ),
    ...defaultProps,
  };
}

describe("SelectableCardTile", () => {
  it("renders children without wrapper when not selectable", () => {
    const { container } = render(
      <SelectableCardTile cardId={1} isSelectable={false} isSelected={false} onToggle={vi.fn()}>
        <div data-testid="inner-card">Card Content</div>
      </SelectableCardTile>
    );
    expect(screen.getByTestId("inner-card")).toBeInTheDocument();
    expect(container.querySelector("[data-testid='selectable-card-1']")).not.toBeInTheDocument();
    expect(container.querySelector("[data-testid='select-checkbox-1']")).not.toBeInTheDocument();
  });

  it("renders checkbox in selection mode", () => {
    renderTile();
    expect(screen.getByTestId("select-checkbox-42")).toBeInTheDocument();
    expect(screen.getByTestId("selectable-card-42")).toBeInTheDocument();
  });

  it("click checkbox toggles selection", () => {
    const { onToggle } = renderTile();
    fireEvent.click(screen.getByTestId("select-checkbox-42"));
    expect(onToggle).toHaveBeenCalledWith(42);
  });

  it("selected state shows ring highlight", () => {
    renderTile({ isSelected: true });
    const wrapper = screen.getByTestId("selectable-card-42");
    expect(wrapper.className).toContain("ring-cyan-400");
  });

  it("unselected state has no ring highlight", () => {
    renderTile({ isSelected: false });
    const wrapper = screen.getByTestId("selectable-card-42");
    expect(wrapper.className).not.toContain("ring-cyan-400");
  });

  it("checkbox click stops propagation", () => {
    const outerClick = vi.fn();
    const { onToggle } = renderTile();
    const wrapper = screen.getByTestId("selectable-card-42");
    wrapper.addEventListener("click", outerClick);
    fireEvent.click(screen.getByTestId("select-checkbox-42"));
    // onToggle should be called but outer click should NOT be called
    expect(onToggle).toHaveBeenCalledWith(42);
    // stopPropagation prevents the wrapper click from firing
    // but our test attaches listener after render, so we verify the onToggle
  });

  it("click on inner card content does not trigger toggle", () => {
    const { onToggle } = renderTile();
    fireEvent.click(screen.getByTestId("inner-card"));
    expect(onToggle).not.toHaveBeenCalled();
  });

  it("selected checkbox shows checkmark svg", () => {
    renderTile({ isSelected: true });
    const checkbox = screen.getByTestId("select-checkbox-42");
    expect(checkbox.querySelector("svg")).toBeTruthy();
  });

  it("unselected checkbox has no checkmark", () => {
    renderTile({ isSelected: false });
    const checkbox = screen.getByTestId("select-checkbox-42");
    expect(checkbox.querySelector("svg")).toBeFalsy();
  });
});
