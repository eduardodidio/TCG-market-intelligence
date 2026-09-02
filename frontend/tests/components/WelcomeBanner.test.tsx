import { render, screen, fireEvent } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { WelcomeBanner } from "../../src/components/WelcomeBanner";

// Mock react-i18next
vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { language: "en", changeLanguage: vi.fn() },
  }),
}));

function renderBanner(onDismiss = vi.fn()) {
  return render(
    <MemoryRouter>
      <WelcomeBanner onDismiss={onDismiss} />
    </MemoryRouter>,
  );
}

describe("WelcomeBanner", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("renders welcome title and subtitle", () => {
    renderBanner();
    expect(screen.getByTestId("welcome-title")).toHaveTextContent(
      "onboarding.welcomeTitle",
    );
    expect(screen.getByTestId("welcome-subtitle")).toHaveTextContent(
      "onboarding.welcomeSubtitle",
    );
  });

  it("renders 3 step cards with correct links", () => {
    renderBanner();
    const collectionStep = screen.getByTestId("welcome-step-collection");
    expect(collectionStep).toBeInTheDocument();
    expect(collectionStep).toHaveAttribute("href", "/collection");

    const marketStep = screen.getByTestId("welcome-step-market");
    expect(marketStep).toBeInTheDocument();
    expect(marketStep).toHaveAttribute("href", "/market");

    const decksStep = screen.getByTestId("welcome-step-decks");
    expect(decksStep).toBeInTheDocument();
    expect(decksStep).toHaveAttribute("href", "/decks");
  });

  it("calls onDismiss when X button clicked", () => {
    const onDismiss = vi.fn();
    renderBanner(onDismiss);
    fireEvent.click(screen.getByTestId("welcome-dismiss"));
    expect(onDismiss).toHaveBeenCalledTimes(1);
  });
});
