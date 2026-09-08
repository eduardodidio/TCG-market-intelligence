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
});
