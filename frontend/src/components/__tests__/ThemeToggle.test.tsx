import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, act } from "@testing-library/react";
import { ThemeProvider } from "../../contexts/ThemeContext";
import { ThemeToggle } from "../ThemeToggle";

// Mock react-i18next
vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const map: Record<string, string> = {
        "theme.selector": "Theme selector",
        "theme.dark": "Dark",
        "theme.light": "Light",
        "theme.system": "System",
      };
      return map[key] ?? key;
    },
    i18n: { language: "en" },
  }),
}));

function renderToggle() {
  return render(
    <ThemeProvider>
      <ThemeToggle />
    </ThemeProvider>,
  );
}

describe("ThemeToggle", () => {
  beforeEach(() => {
    localStorage.removeItem("tcg_theme");
    document.documentElement.classList.remove("dark");
  });

  it("renders three theme buttons", () => {
    renderToggle();
    expect(screen.getByTestId("theme-toggle")).toBeInTheDocument();
    expect(screen.getByTestId("theme-btn-dark")).toBeInTheDocument();
    expect(screen.getByTestId("theme-btn-light")).toBeInTheDocument();
    expect(screen.getByTestId("theme-btn-system")).toBeInTheDocument();
  });

  it("dark button is active by default", () => {
    renderToggle();
    expect(screen.getByTestId("theme-btn-dark")).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByTestId("theme-btn-light")).toHaveAttribute(
      "aria-pressed",
      "false",
    );
  });

  it("clicking light activates light theme", () => {
    renderToggle();

    act(() => {
      screen.getByTestId("theme-btn-light").click();
    });

    expect(screen.getByTestId("theme-btn-light")).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByTestId("theme-btn-dark")).toHaveAttribute(
      "aria-pressed",
      "false",
    );
    expect(localStorage.getItem("tcg_theme")).toBe("light");
  });

  it("clicking system activates system theme", () => {
    renderToggle();

    act(() => {
      screen.getByTestId("theme-btn-system").click();
    });

    expect(screen.getByTestId("theme-btn-system")).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(localStorage.getItem("tcg_theme")).toBe("system");
  });

  it("has proper aria-label", () => {
    renderToggle();
    expect(screen.getByTestId("theme-toggle")).toHaveAttribute(
      "aria-label",
      "Theme selector",
    );
  });
});
