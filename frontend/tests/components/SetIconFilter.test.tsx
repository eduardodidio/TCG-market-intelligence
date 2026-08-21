import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { SetIconFilter } from "../../src/components/SetIconFilter";

vi.mock("../../src/utils/scryfall", () => ({
  scryfallSetIconUrl: (code: string) => `https://mock-svg/${code}.svg`,
}));

const OPTIONS = [
  { label: "Dominaria Remastered", value: "DMR" },
  { label: "Modern Horizons 2", value: "MH2" },
];

describe("SetIconFilter", () => {
  it("renders 'All' button plus one icon button per option", () => {
    render(<SetIconFilter options={OPTIONS} selected={null} onSelect={() => {}} />);
    const container = screen.getByTestId("set-icon-filter");
    const buttons = container.querySelectorAll("button");
    // 1 "All" + 2 options = 3 buttons
    expect(buttons).toHaveLength(3);
    expect(screen.getByText("All")).toBeDefined();
    expect(screen.getByTestId("set-icon-DMR")).toBeDefined();
    expect(screen.getByTestId("set-icon-MH2")).toBeDefined();
  });

  it("highlights 'All' button when nothing is selected", () => {
    render(<SetIconFilter options={OPTIONS} selected={null} onSelect={() => {}} />);
    const allButton = screen.getByText("All");
    expect(allButton.className).toContain("bg-indigo-500");
  });

  it("clicking an icon calls onSelect with the value", () => {
    const handleSelect = vi.fn();
    render(<SetIconFilter options={OPTIONS} selected={null} onSelect={handleSelect} />);
    fireEvent.click(screen.getByTestId("set-icon-DMR"));
    expect(handleSelect).toHaveBeenCalledWith("DMR");
  });

  it("clicking a selected icon calls onSelect(null) to deselect", () => {
    const handleSelect = vi.fn();
    render(<SetIconFilter options={OPTIONS} selected="DMR" onSelect={handleSelect} />);
    fireEvent.click(screen.getByTestId("set-icon-DMR"));
    expect(handleSelect).toHaveBeenCalledWith(null);
  });

  it("clicking 'All' calls onSelect(null)", () => {
    const handleSelect = vi.fn();
    render(<SetIconFilter options={OPTIONS} selected="DMR" onSelect={handleSelect} />);
    fireEvent.click(screen.getByText("All"));
    expect(handleSelect).toHaveBeenCalledWith(null);
  });

  it("shows label as title attribute on each icon button", () => {
    render(<SetIconFilter options={OPTIONS} selected={null} onSelect={() => {}} />);
    const dmrButton = screen.getByTestId("set-icon-DMR");
    const mh2Button = screen.getByTestId("set-icon-MH2");
    expect(dmrButton.getAttribute("title")).toBe("Dominaria Remastered");
    expect(mh2Button.getAttribute("title")).toBe("Modern Horizons 2");
  });

  it("falls back to set code text when image fails to load", () => {
    render(<SetIconFilter options={OPTIONS} selected={null} onSelect={() => {}} />);
    const dmrButton = screen.getByTestId("set-icon-DMR");
    const img = dmrButton.querySelector("img");
    expect(img).toBeDefined();
    // Simulate image load error
    fireEvent.error(img!);
    // After error, should show text fallback instead of img
    expect(dmrButton.querySelector("img")).toBeNull();
    expect(dmrButton.textContent).toBe("DMR");
  });

  it("renders with empty options array", () => {
    render(<SetIconFilter options={[]} selected={null} onSelect={() => {}} />);
    const container = screen.getByTestId("set-icon-filter");
    const buttons = container.querySelectorAll("button");
    // Only the "All" button
    expect(buttons).toHaveLength(1);
  });
});
