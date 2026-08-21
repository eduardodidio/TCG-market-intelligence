import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { FilterChips } from "../../src/components/FilterChips";

const OPTIONS = [
  { label: "DMR", value: "DMR" },
  { label: "MH2", value: "MH2" },
  { label: "2X2", value: "2X2" },
];

describe("FilterChips", () => {
  it("renders the 'All' chip plus option chips", () => {
    render(<FilterChips options={OPTIONS} selected={null} onSelect={() => {}} />);
    expect(screen.getByTestId("filter-chip-all")).toBeDefined();
    expect(screen.getByTestId("filter-chip-DMR")).toBeDefined();
    expect(screen.getByTestId("filter-chip-MH2")).toBeDefined();
    expect(screen.getByTestId("filter-chip-2X2")).toBeDefined();
  });

  it("highlights the 'All' chip when nothing is selected", () => {
    render(<FilterChips options={OPTIONS} selected={null} onSelect={() => {}} />);
    const allChip = screen.getByTestId("filter-chip-all");
    expect(allChip.className).toContain("bg-tcg-primary");
  });

  it("highlights the selected chip and dims others", () => {
    render(<FilterChips options={OPTIONS} selected="MH2" onSelect={() => {}} />);
    const mh2Chip = screen.getByTestId("filter-chip-MH2");
    const allChip = screen.getByTestId("filter-chip-all");
    const dmrChip = screen.getByTestId("filter-chip-DMR");

    expect(mh2Chip.className).toContain("bg-tcg-primary");
    expect(allChip.className).toContain("bg-tcg-card");
    expect(dmrChip.className).toContain("bg-tcg-card");
  });

  it("fires onSelect with the chip value when clicked", () => {
    const handleSelect = vi.fn();
    render(<FilterChips options={OPTIONS} selected={null} onSelect={handleSelect} />);
    fireEvent.click(screen.getByTestId("filter-chip-DMR"));
    expect(handleSelect).toHaveBeenCalledWith("DMR");
  });

  it("fires onSelect with null when 'All' is clicked", () => {
    const handleSelect = vi.fn();
    render(<FilterChips options={OPTIONS} selected="DMR" onSelect={handleSelect} />);
    fireEvent.click(screen.getByTestId("filter-chip-all"));
    expect(handleSelect).toHaveBeenCalledWith(null);
  });

  it("toggles off the selected chip when clicked again", () => {
    const handleSelect = vi.fn();
    render(<FilterChips options={OPTIONS} selected="DMR" onSelect={handleSelect} />);
    fireEvent.click(screen.getByTestId("filter-chip-DMR"));
    expect(handleSelect).toHaveBeenCalledWith(null);
  });

  it("renders with empty options array", () => {
    render(<FilterChips options={[]} selected={null} onSelect={() => {}} />);
    expect(screen.getByTestId("filter-chip-all")).toBeDefined();
    // No option chips
    expect(screen.getByTestId("filter-chips").querySelectorAll("button")).toHaveLength(1);
  });
});
