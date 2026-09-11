import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { SetCompletionBar } from "../../src/components/SetCompletionBar";

vi.mock("../../src/utils/scryfall", () => ({
  scryfallSetIconUrl: (code: string) => `https://scryfall.com/sets/${code}.svg`,
}));

function renderBar(props: React.ComponentProps<typeof SetCompletionBar>) {
  return render(
    <MemoryRouter>
      <SetCompletionBar {...props} />
    </MemoryRouter>,
  );
}

describe("SetCompletionBar", () => {
  it("renders correct width percentage", () => {
    renderBar({ setCode: "MH3", setName: "Modern Horizons 3", owned: 25, total: 100 });
    const fill = screen.getByTestId("completion-bar-fill");
    expect(fill.style.width).toBe("25%");
  });

  it("shows gold highlight at 100%", () => {
    renderBar({ setCode: "MH3", setName: "Modern Horizons 3", owned: 100, total: 100 });
    const fill = screen.getByTestId("completion-bar-fill");
    expect(fill.className).toContain("amber");
    const label = screen.getByTestId("completion-label");
    expect(label.textContent).toContain("Complete!");
  });

  it("shows owned/total label for partial completion", () => {
    renderBar({ setCode: "FDN", setName: "Foundations", owned: 50, total: 200 });
    const label = screen.getByTestId("completion-label");
    expect(label.textContent).toContain("50");
    expect(label.textContent).toContain("200");
  });

  it("handles 0 owned cards", () => {
    renderBar({ setCode: "CMM", setName: "Commander Masters", owned: 0, total: 100 });
    const fill = screen.getByTestId("completion-bar-fill");
    expect(fill.style.width).toBe("0%");
  });

  it("handles 0 total cards", () => {
    renderBar({ setCode: "X", setName: "Unknown", owned: 0, total: 0 });
    const fill = screen.getByTestId("completion-bar-fill");
    expect(fill.style.width).toBe("0%");
  });

  it("handles 0 total cards with hasCatalog=false", () => {
    renderBar({ setCode: "X", setName: "Unknown", owned: 0, total: 0, hasCatalog: false });
    // No catalog = no fill rendered
    expect(screen.queryByTestId("completion-bar-fill")).not.toBeInTheDocument();
  });

  it("shows no catalog text when hasCatalog is false", () => {
    renderBar({ setCode: "PROMO", setName: "Promo", owned: 5, total: 5, hasCatalog: false });
    const label = screen.getByTestId("completion-label");
    expect(label).toHaveTextContent("5 cards (no catalog)");
  });

  it("does not show gold styling when hasCatalog is false", () => {
    renderBar({ setCode: "PROMO", setName: "Promo", owned: 10, total: 10, hasCatalog: false });
    const label = screen.getByTestId("completion-label");
    expect(label.className).not.toContain("amber");
    expect(label).not.toHaveTextContent("Complete!");
  });
});
