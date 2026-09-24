import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { META_FORMATS } from "../../../types/metaDecks";
import type { MetaFormatInfo } from "../../../types/metaDecks";
import { MetaFormatPills } from "../MetaFormatPills";

const FORMATS: MetaFormatInfo[] = [
  { format: "commander", latest_snapshot_date: "2026-09-24", deck_count: 50 },
  { format: "modern", latest_snapshot_date: "2026-09-24", deck_count: 30 },
  { format: "pauper", latest_snapshot_date: null, deck_count: 0 },
];

describe("MetaFormatPills", () => {
  it("renders one pill per format and marks the active one", () => {
    render(<MetaFormatPills value="modern" formats={FORMATS} onChange={vi.fn()} />);
    for (const fmt of META_FORMATS) {
      expect(screen.getByTestId(`meta-format-${fmt}`)).toBeInTheDocument();
    }
    expect(screen.getByTestId("meta-format-modern")).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByTestId("meta-format-modern").className).toContain("bg-cyan-500");
    expect(screen.getByTestId("meta-format-commander")).toHaveAttribute("aria-pressed", "false");
  });

  it("calls onChange when an available pill is clicked", () => {
    const onChange = vi.fn();
    render(<MetaFormatPills value="modern" formats={FORMATS} onChange={onChange} />);
    fireEvent.click(screen.getByTestId("meta-format-commander"));
    expect(onChange).toHaveBeenCalledWith("commander");
  });

  it("does not call onChange when clicking the active pill", () => {
    const onChange = vi.fn();
    render(<MetaFormatPills value="modern" formats={FORMATS} onChange={onChange} />);
    fireEvent.click(screen.getByTestId("meta-format-modern"));
    expect(onChange).not.toHaveBeenCalled();
  });

  it("disables formats without snapshot (null date or missing) with a tooltip", () => {
    const onChange = vi.fn();
    render(<MetaFormatPills value="modern" formats={FORMATS} onChange={onChange} />);
    const pauper = screen.getByTestId("meta-format-pauper");
    const legacy = screen.getByTestId("meta-format-legacy");
    expect(pauper).toBeDisabled();
    expect(legacy).toBeDisabled();
    expect(pauper).toHaveAttribute("title");
    fireEvent.click(pauper);
    fireEvent.click(legacy);
    expect(onChange).not.toHaveBeenCalled();
  });

  it("keeps the active pill enabled even without snapshot", () => {
    render(<MetaFormatPills value="pauper" formats={FORMATS} onChange={vi.fn()} />);
    expect(screen.getByTestId("meta-format-pauper")).not.toBeDisabled();
  });

  it("enables all pills while availability is unknown (empty formats)", () => {
    const onChange = vi.fn();
    render(<MetaFormatPills value="modern" formats={[]} onChange={onChange} />);
    expect(screen.getByTestId("meta-format-vintage")).not.toBeDisabled();
    fireEvent.click(screen.getByTestId("meta-format-vintage"));
    expect(onChange).toHaveBeenCalledWith("vintage");
  });
});
