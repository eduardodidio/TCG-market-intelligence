import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { TreasureBalance } from "../TreasureBalance";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

vi.mock("../../hooks/useTreasureImage", () => ({
  useTreasureImage: () => "https://example.com/treasure.jpg",
}));

vi.mock("../../hooks/useCredits", () => ({
  useCredits: () => ({
    balance: 100,
    bonusEligible: false,
    isAdmin: false,
    monthlyGrantAmount: 0,
    loading: false,
    claimBonus: vi.fn(),
  }),
}));

vi.mock("../TreasureModal", () => ({
  TreasureModal: () => <div data-testid="treasure-modal" />,
}));

describe("TreasureBalance", () => {
  it("renders treasure icon with treasure-glow class", () => {
    render(<TreasureBalance />);
    const img = screen.getByTestId("treasure-icon");
    expect(img).toHaveClass("treasure-glow");
  });

  it("keeps existing border and shadow classes alongside glow", () => {
    render(<TreasureBalance />);
    const img = screen.getByTestId("treasure-icon");
    expect(img).toHaveClass("border-amber-500/50");
    expect(img).toHaveClass("shadow-lg");
    expect(img).toHaveClass("cursor-pointer");
  });

  it("displays the balance value", () => {
    render(<TreasureBalance />);
    expect(screen.getByTestId("treasure-balance-value")).toHaveTextContent("100");
  });
});
