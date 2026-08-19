import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { SearchBar } from "../../src/components/SearchBar";

describe("SearchBar", () => {
  it("renders the search input with default placeholder", () => {
    render(<SearchBar value="" onChange={() => {}} />);
    const input = screen.getByTestId("search-input");
    expect(input).toBeDefined();
    expect(input.getAttribute("placeholder")).toBe("Search cards by name...");
  });

  it("renders with a custom placeholder", () => {
    render(<SearchBar value="" onChange={() => {}} placeholder="Find a card" />);
    const input = screen.getByTestId("search-input");
    expect(input.getAttribute("placeholder")).toBe("Find a card");
  });

  it("renders the search icon", () => {
    render(<SearchBar value="" onChange={() => {}} />);
    expect(screen.getByTestId("search-icon")).toBeDefined();
  });

  it("displays the current value", () => {
    render(<SearchBar value="Lightning" onChange={() => {}} />);
    const input = screen.getByTestId("search-input") as HTMLInputElement;
    expect(input.value).toBe("Lightning");
  });

  it("fires onChange callback when user types", () => {
    const handleChange = vi.fn();
    render(<SearchBar value="" onChange={handleChange} />);
    const input = screen.getByTestId("search-input");
    fireEvent.change(input, { target: { value: "Bolt" } });
    expect(handleChange).toHaveBeenCalledWith("Bolt");
  });

  it("fires onChange for each keystroke", () => {
    const handleChange = vi.fn();
    render(<SearchBar value="" onChange={handleChange} />);
    const input = screen.getByTestId("search-input");
    fireEvent.change(input, { target: { value: "A" } });
    fireEvent.change(input, { target: { value: "AB" } });
    expect(handleChange).toHaveBeenCalledTimes(2);
  });
});
