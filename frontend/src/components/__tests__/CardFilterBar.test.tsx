import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { CardFilterBar } from "../CardFilterBar";
import type { SortOption } from "../SortSelect";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (k: string) => k,
  }),
}));

const SORT_OPTIONS: SortOption[] = [
  { labelKey: "sort.nameAZ", sortBy: "name", sortDir: "asc" },
  { labelKey: "sort.priceHighLow", sortBy: "price", sortDir: "desc" },
];

const SET_OPTIONS = [
  { label: "DOM", value: "dom" },
  { label: "WAR", value: "war" },
];

function baseProps() {
  return {
    search: "",
    onSearchChange: vi.fn(),
    sortOptions: SORT_OPTIONS,
    sortValue: "name-asc",
    onSortChange: vi.fn(),
  };
}

describe("CardFilterBar", () => {
  it("renders with default testid and sticky container classes", () => {
    render(<CardFilterBar {...baseProps()} />);
    const bar = screen.getByTestId("sticky-filter-bar");
    expect(bar).toBeInTheDocument();
    expect(bar.className).toContain("sticky");
    expect(bar.className).toContain("top-0");
    expect(bar.className).toContain("bg-slate-900/95");
  });

  it("renders with a custom testId", () => {
    render(<CardFilterBar {...baseProps()} testId="custom-bar" />);
    expect(screen.getByTestId("custom-bar")).toBeInTheDocument();
    expect(screen.queryByTestId("sticky-filter-bar")).not.toBeInTheDocument();
  });

  it("calls onSearchChange when typing", () => {
    const onSearchChange = vi.fn();
    render(<CardFilterBar {...baseProps()} onSearchChange={onSearchChange} />);
    fireEvent.change(screen.getByTestId("search-input"), { target: { value: "a" } });
    expect(onSearchChange).toHaveBeenCalledWith("a");
  });

  it("calls onSortChange with sortBy and sortDir when picking a sort", () => {
    const onSortChange = vi.fn();
    render(<CardFilterBar {...baseProps()} onSortChange={onSortChange} />);
    fireEvent.change(screen.getByTestId("sort-select"), { target: { value: "price-desc" } });
    expect(onSortChange).toHaveBeenCalledWith("price", "desc");
  });

  it("renders SetIconFilter and calls onSetSelect when set options are provided", () => {
    const onSetSelect = vi.fn();
    render(
      <CardFilterBar
        {...baseProps()}
        setOptions={SET_OPTIONS}
        selectedSet={null}
        onSetSelect={onSetSelect}
      />,
    );
    expect(screen.getByTestId("set-icon-filter")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("set-icon-dom"));
    expect(onSetSelect).toHaveBeenCalledWith("dom");
  });

  it("does not render the set filter row when setOptions is empty", () => {
    render(<CardFilterBar {...baseProps()} setOptions={[]} onSetSelect={vi.fn()} />);
    expect(screen.queryByTestId("set-icon-filter")).not.toBeInTheDocument();
  });

  it("does not render the set filter row when onSetSelect is undefined even if options exist", () => {
    render(<CardFilterBar {...baseProps()} setOptions={SET_OPTIONS} />);
    expect(screen.queryByTestId("set-icon-filter")).not.toBeInTheDocument();
  });

  it("does not render the actions row when gridSize/onGridSizeChange are not both given", () => {
    render(<CardFilterBar {...baseProps()} actions={<button>Custom</button>} />);
    expect(screen.queryByTestId("filter-bar-actions")).not.toBeInTheDocument();
  });

  it("renders the actions row with actions before GridSizeToggle when both gridSize and onGridSizeChange are given", () => {
    render(
      <CardFilterBar
        {...baseProps()}
        gridSize="md"
        onGridSizeChange={vi.fn()}
        actions={<button data-testid="custom-action">Custom</button>}
      />,
    );
    const actionsRow = screen.getByTestId("filter-bar-actions");
    expect(actionsRow).toBeInTheDocument();
    const customAction = screen.getByTestId("custom-action");
    const gridToggle = screen.getByRole("group");
    expect(
      customAction.compareDocumentPosition(gridToggle) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
  });

  it("renders children between the set filter and the actions row", () => {
    render(
      <CardFilterBar
        {...baseProps()}
        setOptions={SET_OPTIONS}
        selectedSet={null}
        onSetSelect={vi.fn()}
        gridSize="md"
        onGridSizeChange={vi.fn()}
      >
        <div data-testid="extra-row">Extra</div>
      </CardFilterBar>,
    );
    const setFilter = screen.getByTestId("set-icon-filter");
    const extraRow = screen.getByTestId("extra-row");
    const actionsRow = screen.getByTestId("filter-bar-actions");
    expect(
      setFilter.compareDocumentPosition(extraRow) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    expect(
      extraRow.compareDocumentPosition(actionsRow) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
  });
});
