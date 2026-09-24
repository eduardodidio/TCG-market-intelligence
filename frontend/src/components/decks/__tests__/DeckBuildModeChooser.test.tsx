import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { DeckBuildModeChooser } from "../DeckBuildModeChooser";

const tMock = vi.fn(
  (key: string, opts?: Record<string, unknown>) =>
    (opts?.defaultValue as string) ?? key,
);

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: tMock }),
}));

describe("DeckBuildModeChooser", () => {
  beforeEach(() => {
    tMock.mockImplementation(
      (key: string, opts?: Record<string, unknown>) =>
        (opts?.defaultValue as string) ?? key,
    );
  });

  it("renders both options inside the chooser", () => {
    render(<DeckBuildModeChooser onChoose={vi.fn()} />);
    expect(screen.getByTestId("mode-chooser")).toBeInTheDocument();
    expect(screen.getByTestId("mode-option-manual")).toBeInTheDocument();
    expect(screen.getByTestId("mode-option-suggestion")).toBeInTheDocument();
  });

  it("does not call onChoose on render", () => {
    const onChoose = vi.fn();
    render(<DeckBuildModeChooser onChoose={onChoose} />);
    expect(onChoose).not.toHaveBeenCalled();
  });

  it("calls onChoose('manual') when the manual option is clicked", () => {
    const onChoose = vi.fn();
    render(<DeckBuildModeChooser onChoose={onChoose} />);
    fireEvent.click(screen.getByTestId("mode-option-manual"));
    expect(onChoose).toHaveBeenCalledTimes(1);
    expect(onChoose).toHaveBeenCalledWith("manual");
  });

  it("calls onChoose('suggestion') when the suggestion option is clicked", () => {
    const onChoose = vi.fn();
    render(<DeckBuildModeChooser onChoose={onChoose} />);
    fireEvent.click(screen.getByTestId("mode-option-suggestion"));
    expect(onChoose).toHaveBeenCalledTimes(1);
    expect(onChoose).toHaveBeenCalledWith("suggestion");
  });

  it("uses native buttons with type=button and accessible names", () => {
    render(<DeckBuildModeChooser onChoose={vi.fn()} />);
    const manual = screen.getByRole("button", { name: /build my own deck/i });
    const suggestion = screen.getByRole("button", { name: /deck suggestion/i });
    expect(manual).toHaveAttribute("type", "button");
    expect(suggestion).toHaveAttribute("type", "button");
    expect(manual.tagName).toBe("BUTTON");
  });

  it("links each description via aria-describedby", () => {
    render(<DeckBuildModeChooser onChoose={vi.fn()} />);
    expect(
      screen.getByRole("button", { name: /build my own deck/i }),
    ).toHaveAccessibleDescription(/generated instantly/i);
    expect(
      screen.getByRole("button", { name: /deck suggestion/i }),
    ).toHaveAccessibleDescription(/processed once a day/i);
  });

  it("is keyboard reachable and activatable via the native button", () => {
    const onChoose = vi.fn();
    render(<DeckBuildModeChooser onChoose={onChoose} />);
    const suggestion = screen.getByTestId("mode-option-suggestion");
    suggestion.focus();
    expect(suggestion).toHaveFocus();
    // Native buttons translate Enter/Space into a click event.
    fireEvent.click(suggestion);
    expect(onChoose).toHaveBeenCalledWith("suggestion");
  });

  it("renders without crashing when t returns raw keys", () => {
    tMock.mockImplementation((key: string) => key);
    const onChoose = vi.fn();
    render(<DeckBuildModeChooser onChoose={onChoose} />);
    expect(
      screen.getByRole("button", { name: /deckSuggest\.mode\.manualTitle/ }),
    ).toBeInTheDocument();
    fireEvent.click(
      screen.getByRole("button", {
        name: /deckSuggest\.mode\.suggestionTitle/,
      }),
    );
    expect(onChoose).toHaveBeenCalledWith("suggestion");
  });
});
