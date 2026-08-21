import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { GridSizeToggle } from "../../src/components/GridSizeToggle";

describe("GridSizeToggle", () => {
  it("renders 3 buttons", () => {
    render(<GridSizeToggle value="md" onChange={() => {}} />);
    const group = screen.getByRole("group", { name: "Grid size" });
    const buttons = group.querySelectorAll("button");
    expect(buttons).toHaveLength(3);
  });

  it("active button has aria-pressed='true'", () => {
    render(<GridSizeToggle value="sm" onChange={() => {}} />);
    const smallBtn = screen.getByLabelText("Small grid");
    expect(smallBtn.getAttribute("aria-pressed")).toBe("true");
  });

  it("inactive buttons have aria-pressed='false'", () => {
    render(<GridSizeToggle value="sm" onChange={() => {}} />);
    const medBtn = screen.getByLabelText("Medium grid");
    const lgBtn = screen.getByLabelText("Large grid");
    expect(medBtn.getAttribute("aria-pressed")).toBe("false");
    expect(lgBtn.getAttribute("aria-pressed")).toBe("false");
  });

  it("clicking a button calls onChange with the correct size", () => {
    const onChange = vi.fn();
    render(<GridSizeToggle value="md" onChange={onChange} />);
    fireEvent.click(screen.getByLabelText("Large grid"));
    expect(onChange).toHaveBeenCalledWith("lg");
  });

  it("accessible group label exists", () => {
    render(<GridSizeToggle value="md" onChange={() => {}} />);
    expect(screen.getByRole("group", { name: "Grid size" })).toBeDefined();
  });
});
