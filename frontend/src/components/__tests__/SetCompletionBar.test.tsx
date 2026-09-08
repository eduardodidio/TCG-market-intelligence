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
  { set_code: "mh3", set_name: "Modern Horizons 3", owned: 10, total: 100 },
  { set_code: "fdn", set_name: "Foundations", owned: 50, total: 50 },
  { set_code: "cmm", set_name: "Commander Masters", owned: 3, total: 200 },
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

  it("navigates to /collection?set=<code> on click", () => {
    renderBar({ setCode: "fdn" });
    fireEvent.click(screen.getByTestId("set-completion-fdn"));
    expect(mockNavigate).toHaveBeenCalledWith("/collection?set=fdn");
  });

  it("navigates on Enter key", () => {
    renderBar({ setCode: "cmm" });
    fireEvent.keyDown(screen.getByTestId("set-completion-cmm"), { key: "Enter" });
    expect(mockNavigate).toHaveBeenCalledWith("/collection?set=cmm");
  });

  it("navigates on Space key", () => {
    renderBar({ setCode: "cmm" });
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
});
