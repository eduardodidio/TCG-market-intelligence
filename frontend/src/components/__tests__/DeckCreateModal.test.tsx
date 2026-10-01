import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { DeckCreateModal } from "../DeckCreateModal";
import * as decksApi from "../../api/decks";

vi.mock("../../api/decks", () => ({
  createDeck: vi.fn(),
}));

describe("DeckCreateModal", () => {
  const defaultProps = {
    isOpen: true,
    onClose: vi.fn(),
    onCreated: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders modal with name input and create button", () => {
    render(<DeckCreateModal {...defaultProps} />);
    expect(screen.getByTestId("create-deck-name-input")).toBeInTheDocument();
    expect(screen.getByTestId("create-deck-description-input")).toBeInTheDocument();
    expect(screen.getByTestId("submit-create-btn")).toBeInTheDocument();
    expect(screen.getByTestId("cancel-create-btn")).toBeInTheDocument();
  });

  it("does not render when isOpen is false", () => {
    render(<DeckCreateModal {...defaultProps} isOpen={false} />);
    expect(screen.queryByTestId("deck-create-modal")).not.toBeInTheDocument();
  });

  it("create button disabled when name is empty", () => {
    render(<DeckCreateModal {...defaultProps} />);
    const btn = screen.getByTestId("submit-create-btn");
    expect(btn).toBeDisabled();
  });

  it("create button enabled when name has content", () => {
    render(<DeckCreateModal {...defaultProps} />);
    fireEvent.change(screen.getByTestId("create-deck-name-input"), {
      target: { value: "My Deck" },
    });
    const btn = screen.getByTestId("submit-create-btn");
    expect(btn).not.toBeDisabled();
  });

  it("calls createDeck API on submit", async () => {
    vi.mocked(decksApi.createDeck).mockResolvedValue({
      data: { deck_id: 42, name: "My Deck", description: null },
      meta: { cursor: null, total: null, offset: null, request_id: "r1" },
      errors: [],
    });

    render(<DeckCreateModal {...defaultProps} />);
    fireEvent.change(screen.getByTestId("create-deck-name-input"), {
      target: { value: "My Deck" },
    });
    fireEvent.click(screen.getByTestId("submit-create-btn"));

    await waitFor(() => {
      expect(decksApi.createDeck).toHaveBeenCalledWith("My Deck", undefined);
    });
  });

  it("shows loading state during creation", async () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let resolvePromise: (value: any) => void;
    vi.mocked(decksApi.createDeck).mockReturnValue(
      new Promise((resolve) => {
        resolvePromise = resolve;
      }) as ReturnType<typeof decksApi.createDeck>,
    );

    render(<DeckCreateModal {...defaultProps} />);
    fireEvent.change(screen.getByTestId("create-deck-name-input"), {
      target: { value: "My Deck" },
    });
    fireEvent.click(screen.getByTestId("submit-create-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("submit-create-btn")).toHaveTextContent("Creating...");
    });

    // Clean up
    resolvePromise!({
      data: { deck_id: 1, name: "My Deck", description: null },
      meta: { cursor: null, total: null, offset: null, request_id: "r1" },
      errors: [],
    });
  });

  it("calls onCreated with deck ID on success", async () => {
    vi.mocked(decksApi.createDeck).mockResolvedValue({
      data: { deck_id: 42, name: "My Deck", description: null },
      meta: { cursor: null, total: null, offset: null, request_id: "r1" },
      errors: [],
    });

    render(<DeckCreateModal {...defaultProps} />);
    fireEvent.change(screen.getByTestId("create-deck-name-input"), {
      target: { value: "My Deck" },
    });
    fireEvent.click(screen.getByTestId("submit-create-btn"));

    await waitFor(() => {
      expect(defaultProps.onCreated).toHaveBeenCalledWith(42);
    });
  });

  it("shows error on API failure", async () => {
    vi.mocked(decksApi.createDeck).mockResolvedValue({
      data: null,
      meta: { cursor: null, total: null, offset: null, request_id: "r1" },
      errors: [{ code: "VALIDATION_ERROR", message: "Name already exists" }],
    });

    render(<DeckCreateModal {...defaultProps} />);
    fireEvent.change(screen.getByTestId("create-deck-name-input"), {
      target: { value: "My Deck" },
    });
    fireEvent.click(screen.getByTestId("submit-create-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("create-error")).toHaveTextContent("Name already exists");
    });
  });

  it("calls onClose when cancel button is clicked", () => {
    render(<DeckCreateModal {...defaultProps} />);
    fireEvent.click(screen.getByTestId("cancel-create-btn"));
    expect(defaultProps.onClose).toHaveBeenCalledTimes(1);
  });

  it("calls onClose when backdrop is clicked", () => {
    render(<DeckCreateModal {...defaultProps} />);
    fireEvent.click(screen.getByTestId("deck-create-modal"));
    expect(defaultProps.onClose).toHaveBeenCalledTimes(1);
  });

  it("does not close when modal content is clicked", () => {
    render(<DeckCreateModal {...defaultProps} />);
    // Click inside the modal content (the name input)
    fireEvent.click(screen.getByTestId("create-deck-name-input"));
    expect(defaultProps.onClose).not.toHaveBeenCalled();
  });

  it("sends description when provided", async () => {
    vi.mocked(decksApi.createDeck).mockResolvedValue({
      data: { deck_id: 1, name: "My Deck", description: "A cool deck" },
      meta: { cursor: null, total: null, offset: null, request_id: "r1" },
      errors: [],
    });

    render(<DeckCreateModal {...defaultProps} />);
    fireEvent.change(screen.getByTestId("create-deck-name-input"), {
      target: { value: "My Deck" },
    });
    fireEvent.change(screen.getByTestId("create-deck-description-input"), {
      target: { value: "A cool deck" },
    });
    fireEvent.click(screen.getByTestId("submit-create-btn"));

    await waitFor(() => {
      expect(decksApi.createDeck).toHaveBeenCalledWith("My Deck", "A cool deck");
    });
  });

  it("submits on Enter key in name input", async () => {
    vi.mocked(decksApi.createDeck).mockResolvedValue({
      data: { deck_id: 1, name: "My Deck", description: null },
      meta: { cursor: null, total: null, offset: null, request_id: "r1" },
      errors: [],
    });

    render(<DeckCreateModal {...defaultProps} />);
    const input = screen.getByTestId("create-deck-name-input");
    fireEvent.change(input, { target: { value: "My Deck" } });
    fireEvent.keyDown(input, { key: "Enter" });

    await waitFor(() => {
      expect(decksApi.createDeck).toHaveBeenCalled();
    });
  });
});
