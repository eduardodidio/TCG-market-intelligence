import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { SetCompletionBar, SetCompletionSection } from "../SetCompletionBar";

// Track navigation
const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return { ...actual, useNavigate: () => mockNavigate };
});

// Mock scryfallSetIconUrl
vi.mock("../../utils/scryfall", () => ({
  scryfallSetIconUrl: (code: string) => `https://scryfall.com/sets/${code}.svg`,
}));

const LS_KEY = "tcg_set_completion_open";

const sampleEntries = [
  { set_code: "mh3", set_name: "Modern Horizons 3", owned: 10, total: 100, has_catalog: true },
  { set_code: "fdn", set_name: "Foundations", owned: 50, total: 50, has_catalog: true },
  { set_code: "cmm", set_name: "Commander Masters", owned: 3, total: 200, has_catalog: true },
];

function renderBar(props?: Partial<React.ComponentProps<typeof SetCompletionBar>>) {
  const defaults = { setCode: "mh3", setName: "Modern Horizons 3", owned: 10, total: 100 };
  return render(
    <MemoryRouter>
      <SetCompletionBar {...defaults} {...props} />
    </MemoryRouter>,
  );
}

function renderSection(entries = sampleEntries) {
  return render(
    <MemoryRouter>
      <SetCompletionSection entries={entries} />
    </MemoryRouter>,
  );
}

describe("SetCompletionSection", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it("renders collapsed by default", () => {
    renderSection();
    expect(screen.getByTestId("toggle-set-completion")).toBeInTheDocument();
    expect(screen.getByTestId("set-completion-count")).toHaveTextContent("(3)");
    // Section content should NOT be visible
    expect(screen.queryByTestId("set-completion-section")).not.toBeInTheDocument();
  });

  it("expands when toggle is clicked", () => {
    renderSection();
    fireEvent.click(screen.getByTestId("toggle-set-completion"));
    expect(screen.getByTestId("set-completion-section")).toBeInTheDocument();
    // All 3 entries visible
    expect(screen.getByTestId("set-completion-mh3")).toBeInTheDocument();
    expect(screen.getByTestId("set-completion-fdn")).toBeInTheDocument();
    expect(screen.getByTestId("set-completion-cmm")).toBeInTheDocument();
  });

  it("collapses when toggle is clicked again", () => {
    renderSection();
    const toggle = screen.getByTestId("toggle-set-completion");
    fireEvent.click(toggle); // expand
    expect(screen.getByTestId("set-completion-section")).toBeInTheDocument();
    fireEvent.click(toggle); // collapse
    expect(screen.queryByTestId("set-completion-section")).not.toBeInTheDocument();
  });

  it("persists expand state to localStorage", () => {
    renderSection();
    fireEvent.click(screen.getByTestId("toggle-set-completion"));
    expect(localStorage.getItem(LS_KEY)).toBe("1");
    fireEvent.click(screen.getByTestId("toggle-set-completion"));
    expect(localStorage.getItem(LS_KEY)).toBe("0");
  });

  it("reads initial state from localStorage", () => {
    localStorage.setItem(LS_KEY, "1");
    renderSection();
    // Should start expanded
    expect(screen.getByTestId("set-completion-section")).toBeInTheDocument();
  });

  it("shows set count in summary", () => {
    renderSection([sampleEntries[0]]);
    expect(screen.getByTestId("set-completion-count")).toHaveTextContent("(1)");
  });
});

describe("SetCompletionBar", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders set icon image with scryfallSetIconUrl", () => {
    renderBar();
    const img = screen.getByTestId("set-icon-mh3") as HTMLImageElement;
    expect(img).toBeInTheDocument();
    expect(img.src).toBe("https://scryfall.com/sets/mh3.svg");
    expect(img.className).toContain("invert");
    expect(img.className).toContain("brightness-200");
  });

  it("falls back to text-only when icon fails to load", () => {
    renderBar();
    const img = screen.getByTestId("set-icon-mh3");
    fireEvent.error(img);
    // Icon should be gone
    expect(screen.queryByTestId("set-icon-mh3")).not.toBeInTheDocument();
    // Set code text should still be visible
    expect(screen.getByTestId("set-completion-mh3")).toHaveTextContent("mh3");
  });

  it("navigates to /catalog?set_code=<code>&owned_view=1 on click when hasCatalog", () => {
    renderBar({ setCode: "fdn", hasCatalog: true });
    fireEvent.click(screen.getByTestId("set-completion-fdn"));
    expect(mockNavigate).toHaveBeenCalledWith("/catalog?set_code=fdn&owned_view=1");
  });

  it("navigates to /collection?set=<code> on click when hasCatalog=false", () => {
    renderBar({ setCode: "promo", setName: "Promo Cards", hasCatalog: false });
    fireEvent.click(screen.getByTestId("set-completion-promo"));
    expect(mockNavigate).toHaveBeenCalledWith("/collection?set=promo");
  });

  it("navigates to /catalog on Enter key when hasCatalog", () => {
    renderBar({ setCode: "cmm", hasCatalog: true });
    fireEvent.keyDown(screen.getByTestId("set-completion-cmm"), { key: "Enter" });
    expect(mockNavigate).toHaveBeenCalledWith("/catalog?set_code=cmm&owned_view=1");
  });

  it("navigates to /collection on Space key when hasCatalog=false", () => {
    renderBar({ setCode: "cmm", hasCatalog: false });
    fireEvent.keyDown(screen.getByTestId("set-completion-cmm"), { key: " " });
    expect(mockNavigate).toHaveBeenCalledWith("/collection?set=cmm");
  });

  it("has cursor-pointer class for clickability", () => {
    renderBar();
    const row = screen.getByTestId("set-completion-mh3");
    expect(row.className).toContain("cursor-pointer");
  });

  it("shows completion bar with correct percentage", () => {
    renderBar({ owned: 25, total: 100 });
    const fill = screen.getByTestId("completion-bar-fill");
    expect(fill.style.width).toBe("25%");
  });

  it("shows 'Complete!' for 100% sets", () => {
    renderBar({ owned: 50, total: 50 });
    expect(screen.getByTestId("completion-label")).toHaveTextContent("Complete!");
  });

  it("shows 'X of Y' for incomplete sets", () => {
    renderBar({ owned: 10, total: 100 });
    expect(screen.getByTestId("completion-label")).toHaveTextContent("10 of 100");
  });

  it("has role=button for accessibility", () => {
    renderBar();
    expect(screen.getByTestId("set-completion-mh3")).toHaveAttribute("role", "button");
  });

  it("shows 'X cards (no catalog)' when hasCatalog is false", () => {
    renderBar({ setCode: "promo", setName: "Promo", owned: 5, total: 5, hasCatalog: false });
    const label = screen.getByTestId("completion-label");
    expect(label).toHaveTextContent("5 cards (no catalog)");
  });

  it("does not show gold styling when hasCatalog is false even with owned=total", () => {
    renderBar({ setCode: "promo", setName: "Promo", owned: 5, total: 5, hasCatalog: false });
    const label = screen.getByTestId("completion-label");
    expect(label.className).not.toContain("amber");
    expect(label).not.toHaveTextContent("Complete!");
  });

  it("does not render progress bar fill when hasCatalog is false", () => {
    renderBar({ setCode: "promo", setName: "Promo", owned: 3, total: 3, hasCatalog: false });
    expect(screen.queryByTestId("completion-bar-fill")).not.toBeInTheDocument();
  });

  it("defaults to catalog navigation when hasCatalog is undefined", () => {
    renderBar({ setCode: "mh3" });
    fireEvent.click(screen.getByTestId("set-completion-mh3"));
    expect(mockNavigate).toHaveBeenCalledWith("/catalog?set_code=mh3&owned_view=1");
  });

  it("does not include sort params in /collection link (F123-T05: let MyCollection use price desc default)", () => {
    renderBar({ setCode: "promo", setName: "Promo Cards", hasCatalog: false });
    fireEvent.click(screen.getByTestId("set-completion-promo"));
    const navUrl = mockNavigate.mock.calls[0][0] as string;
    expect(navUrl).toBe("/collection?set=promo");
    expect(navUrl).not.toContain("sort=");
    expect(navUrl).not.toContain("dir=");
  });
});
