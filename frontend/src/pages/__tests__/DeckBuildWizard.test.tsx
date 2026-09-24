import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { DeckBuildWizard } from "../DeckBuildWizard";
import type { DeckGenerateResult } from "../../types/api";

const mockNavigate = vi.fn();

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, opts?: Record<string, unknown>) =>
      (opts?.defaultValue as string) ?? key,
  }),
}));

const mockGenerateResult: DeckGenerateResult = {
  deck_id: 42,
  name: "WU Control — 2026-09-17",
  format_name: "commander",
  archetype: "control",
  colors: ["U", "W"],
  total_cards: 100,
  land_count: 38,
  nonland_count: 62,
  total_value: 350.0,
  warnings: [],
  cards: [
    {
      card_id: 1,
      name_en: "Sol Ring",
      set_code: "cmr",
      collector_number: "472",
      quantity: 1,
      mana_cost: "{1}",
      type_line: "Artifact",
      rarity: "uncommon",
      image_uri: null,
      price: 10.0,
      is_owned: false,
    },
  ],
};

vi.mock("../../api/decks", () => ({
  generateDeck: vi.fn(() =>
    Promise.resolve({ data: mockGenerateResult, errors: [] }),
  ),
  searchCommanders: vi.fn(() =>
    Promise.resolve({
      data: [
        {
          card_id: 100,
          name_en: "Atraxa, Praetors' Voice",
          set_code: "cm2",
          collector_number: "10",
          color_identity: "WUBG",
          mana_cost: "{G}{W}{U}{B}",
          type_line: "Legendary Creature",
          rarity: "mythic",
          image_uri: null,
        },
      ],
      errors: [],
    }),
  ),
}));

function renderWizard() {
  return render(
    <MemoryRouter>
      <DeckBuildWizard />
    </MemoryRouter>,
  );
}

describe("DeckBuildWizard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders Step 1 by default", () => {
    renderWizard();
    expect(screen.getByTestId("wizard-step-1")).toBeInTheDocument();
    expect(screen.getByTestId("format-option-commander")).toBeInTheDocument();
    expect(screen.getByTestId("format-option-standard")).toBeInTheDocument();
  });

  it("enables Next button after selecting a format", () => {
    renderWizard();
    const nextBtn = screen.getByTestId("step1-next");
    expect(nextBtn).toBeDisabled();

    fireEvent.click(screen.getByTestId("format-option-commander"));
    expect(nextBtn).not.toBeDisabled();
  });

  it("navigates to Step 2 when Next clicked", () => {
    renderWizard();
    fireEvent.click(screen.getByTestId("format-option-commander"));
    fireEvent.click(screen.getByTestId("step1-next"));
    expect(screen.getByTestId("wizard-step-2")).toBeInTheDocument();
  });

  it("shows commander search for commander format", () => {
    renderWizard();
    fireEvent.click(screen.getByTestId("format-option-commander"));
    fireEvent.click(screen.getByTestId("step1-next"));
    expect(screen.getByTestId("commander-search")).toBeInTheDocument();
  });

  it("shows color picker for non-commander format", () => {
    renderWizard();
    fireEvent.click(screen.getByTestId("format-option-standard"));
    fireEvent.click(screen.getByTestId("step1-next"));
    expect(screen.getByTestId("color-picker")).toBeInTheDocument();
    expect(screen.getByTestId("color-toggle-W")).toBeInTheDocument();
  });

  it("offers Pioneer and Vintage; Pioneer goes to the color step", () => {
    renderWizard();
    expect(screen.getByTestId("format-option-vintage")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("format-option-pioneer"));
    fireEvent.click(screen.getByTestId("step1-next"));
    expect(screen.getByTestId("color-picker")).toBeInTheDocument();
    expect(screen.queryByTestId("commander-search")).toBeNull();
  });

  it("Step 3 shows archetype options and budget input", () => {
    renderWizard();
    // Go to step 2
    fireEvent.click(screen.getByTestId("format-option-standard"));
    fireEvent.click(screen.getByTestId("step1-next"));
    // Select a color
    fireEvent.click(screen.getByTestId("color-toggle-R"));
    // Go to step 3
    fireEvent.click(screen.getByTestId("step2-next"));
    expect(screen.getByTestId("wizard-step-3")).toBeInTheDocument();
    expect(screen.getByTestId("archetype-option-aggro")).toBeInTheDocument();
    expect(screen.getByTestId("budget-input")).toBeInTheDocument();
  });

  it("Generate button calls API and navigates to step 4", async () => {
    const { generateDeck } = vi.mocked(await import("../../api/decks"));

    renderWizard();
    // Step 1 -> 2
    fireEvent.click(screen.getByTestId("format-option-standard"));
    fireEvent.click(screen.getByTestId("step1-next"));
    // Step 2 -> 3
    fireEvent.click(screen.getByTestId("color-toggle-R"));
    fireEvent.click(screen.getByTestId("step2-next"));
    // Generate
    fireEvent.click(screen.getByTestId("generate-btn"));

    await waitFor(() => {
      expect(generateDeck).toHaveBeenCalled();
    });
    await waitFor(() => {
      expect(screen.getByTestId("wizard-step-4")).toBeInTheDocument();
    });
  });

  it("Step 4 shows generated deck cards", async () => {
    renderWizard();
    // Quick path through
    fireEvent.click(screen.getByTestId("format-option-standard"));
    fireEvent.click(screen.getByTestId("step1-next"));
    fireEvent.click(screen.getByTestId("color-toggle-R"));
    fireEvent.click(screen.getByTestId("step2-next"));
    fireEvent.click(screen.getByTestId("generate-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("generated-cards-grid")).toBeInTheDocument();
    });
    expect(screen.getByTestId("gen-total-cards")).toHaveTextContent("100");
  });

  it("Save button navigates to deck page", async () => {
    renderWizard();
    // Quick path through
    fireEvent.click(screen.getByTestId("format-option-standard"));
    fireEvent.click(screen.getByTestId("step1-next"));
    fireEvent.click(screen.getByTestId("color-toggle-R"));
    fireEvent.click(screen.getByTestId("step2-next"));
    fireEvent.click(screen.getByTestId("generate-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("save-deck-btn")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("save-deck-btn"));
    expect(mockNavigate).toHaveBeenCalledWith("/decks/42");
  });

  it("Regenerate button re-calls API", async () => {
    const { generateDeck } = vi.mocked(await import("../../api/decks"));

    renderWizard();
    // Quick path through
    fireEvent.click(screen.getByTestId("format-option-standard"));
    fireEvent.click(screen.getByTestId("step1-next"));
    fireEvent.click(screen.getByTestId("color-toggle-R"));
    fireEvent.click(screen.getByTestId("step2-next"));
    fireEvent.click(screen.getByTestId("generate-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("regenerate-btn")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("regenerate-btn"));
    await waitFor(() => {
      expect(generateDeck).toHaveBeenCalledTimes(2);
    });
  });

  it("Back button navigates between steps", () => {
    renderWizard();
    // Step 1 -> 2
    fireEvent.click(screen.getByTestId("format-option-standard"));
    fireEvent.click(screen.getByTestId("step1-next"));
    expect(screen.getByTestId("wizard-step-2")).toBeInTheDocument();

    // Step 2 -> 1
    fireEvent.click(screen.getByTestId("step2-back"));
    expect(screen.getByTestId("wizard-step-1")).toBeInTheDocument();
  });

  it("shows error when API fails", async () => {
    const { generateDeck } = vi.mocked(await import("../../api/decks"));
    generateDeck.mockResolvedValueOnce({
      data: null,
      errors: [{ code: "ERR", message: "Catalog empty" }],
      meta: { cursor: null, total: null, offset: null, request_id: "" },
    });

    renderWizard();
    fireEvent.click(screen.getByTestId("format-option-standard"));
    fireEvent.click(screen.getByTestId("step1-next"));
    fireEvent.click(screen.getByTestId("color-toggle-R"));
    fireEvent.click(screen.getByTestId("step2-next"));
    fireEvent.click(screen.getByTestId("generate-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("wizard-error")).toBeInTheDocument();
    });
  });

  it("budget preset buttons set the budget value", () => {
    renderWizard();
    // Go to step 3
    fireEvent.click(screen.getByTestId("format-option-standard"));
    fireEvent.click(screen.getByTestId("step1-next"));
    fireEvent.click(screen.getByTestId("color-toggle-R"));
    fireEvent.click(screen.getByTestId("step2-next"));

    fireEvent.click(screen.getByTestId("budget-preset-500"));
    expect(
      (screen.getByTestId("budget-input") as HTMLInputElement).value,
    ).toBe("500");
  });
});
