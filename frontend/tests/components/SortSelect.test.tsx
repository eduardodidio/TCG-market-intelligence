import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { SortSelect, COLLECTION_SORT_OPTIONS } from "../../src/components/SortSelect";

describe("SortSelect", () => {
  it("renders all 8 collection sort options", () => {
    render(
      <SortSelect
        options={COLLECTION_SORT_OPTIONS}
        value="name-asc"
        onChange={() => {}}
      />,
    );

    const select = screen.getByTestId("sort-select") as HTMLSelectElement;
    const optionElements = select.querySelectorAll("option");
    expect(optionElements.length).toBe(8);

    const labels = Array.from(optionElements).map((o) => o.textContent);
    expect(labels).toEqual([
      "Name (A-Z)",
      "Name (Z-A)",
      "Set",
      "Card Number",
      "Date Added (Newest)",
      "Date Added (Oldest)",
      "Price (High-Low)",
      "Price (Low-High)",
    ]);
  });

  it("calls onChange with parsed sortBy and sortDir when selecting Name (Z-A)", () => {
    const handleChange = vi.fn();
    render(
      <SortSelect
        options={COLLECTION_SORT_OPTIONS}
        value="name-asc"
        onChange={handleChange}
      />,
    );

    const select = screen.getByTestId("sort-select");
    fireEvent.change(select, { target: { value: "name-desc" } });
    expect(handleChange).toHaveBeenCalledWith("name", "desc");
  });

  it("calls onChange with price-desc when selecting Price (High-Low)", () => {
    const handleChange = vi.fn();
    render(
      <SortSelect
        options={COLLECTION_SORT_OPTIONS}
        value="name-asc"
        onChange={handleChange}
      />,
    );

    const select = screen.getByTestId("sort-select");
    fireEvent.change(select, { target: { value: "price-desc" } });
    expect(handleChange).toHaveBeenCalledWith("price", "desc");
  });

  it("highlights the correct default value", () => {
    render(
      <SortSelect
        options={COLLECTION_SORT_OPTIONS}
        value="added-desc"
        onChange={() => {}}
      />,
    );

    const select = screen.getByTestId("sort-select") as HTMLSelectElement;
    expect(select.value).toBe("added-desc");
  });

  it("has data-testid attribute", () => {
    render(
      <SortSelect
        options={COLLECTION_SORT_OPTIONS}
        value="name-asc"
        onChange={() => {}}
      />,
    );

    expect(screen.getByTestId("sort-select")).toBeDefined();
  });
});
