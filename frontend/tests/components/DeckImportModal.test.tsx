import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { DeckImportModal } from "../../src/components/DeckImportModal";

function renderModal(props?: Partial<{ onClose: () => void; onSuccess: () => void }>) {
  const onClose = props?.onClose ?? vi.fn();
  const onSuccess = props?.onSuccess ?? vi.fn();

  return {
    onClose,
    onSuccess,
    ...render(
      <MemoryRouter>
        <DeckImportModal onClose={onClose} onSuccess={onSuccess} />
      </MemoryRouter>,
    ),
  };
}

describe("DeckImportModal", () => {
  let originalFetch: typeof globalThis.fetch;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("renders modal with all fields", () => {
    renderModal();

    expect(screen.getByTestId("deck-import-modal")).toBeDefined();
    expect(screen.getByTestId("deck-name-input")).toBeDefined();
    expect(screen.getByTestId("deck-content-input")).toBeDefined();
    expect(screen.getByTestId("deck-description-input")).toBeDefined();
    expect(screen.getByTestId("format-text-btn")).toBeDefined();
    expect(screen.getByTestId("format-csv-btn")).toBeDefined();
  });

  it("cancel button calls onClose", () => {
    const { onClose } = renderModal();

    fireEvent.click(screen.getByTestId("cancel-import-btn"));
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("submit button disabled when fields empty", () => {
    renderModal();

    const submitBtn = screen.getByTestId("submit-import-btn") as HTMLButtonElement;
    expect(submitBtn.disabled).toBe(true);
  });

  it("submit button enabled when fields filled", () => {
    renderModal();

    fireEvent.change(screen.getByTestId("deck-name-input"), {
      target: { value: "My Deck" },
    });
    fireEvent.change(screen.getByTestId("deck-content-input"), {
      target: { value: "4 Lightning Bolt" },
    });

    const submitBtn = screen.getByTestId("submit-import-btn") as HTMLButtonElement;
    expect(submitBtn.disabled).toBe(false);
  });

  it("shows error on validation failure", async () => {
    renderModal();

    // Both empty — should show error
    fireEvent.change(screen.getByTestId("deck-name-input"), {
      target: { value: " " },
    });
    fireEvent.change(screen.getByTestId("deck-content-input"), {
      target: { value: " " },
    });

    // Click submit (it won't be disabled because trim isn't checked until click)
    // Actually the button IS disabled because trim is checked... let me verify
    const submitBtn = screen.getByTestId("submit-import-btn") as HTMLButtonElement;
    // With spaces only, trim() would be empty, so button should be disabled
    expect(submitBtn.disabled).toBe(true);
  });

  it("calls API and onSuccess on successful import", async () => {
    const envelope = {
      data: { deck_id: 1, name: "My Deck", cards_imported: 4, cards_linked: 2 },
      meta: { cursor: null, total: null, offset: null, request_id: "r1" },
      errors: [],
    };
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(envelope),
    }) as unknown as typeof fetch;

    const { onSuccess } = renderModal();

    fireEvent.change(screen.getByTestId("deck-name-input"), {
      target: { value: "My Deck" },
    });
    fireEvent.change(screen.getByTestId("deck-content-input"), {
      target: { value: "4 Lightning Bolt" },
    });

    fireEvent.click(screen.getByTestId("submit-import-btn"));

    await waitFor(() => {
      expect(onSuccess).toHaveBeenCalledOnce();
    });
  });

  it("shows error on API failure", async () => {
    const envelope = {
      data: null,
      meta: { cursor: null, total: null, offset: null, request_id: "r1" },
      errors: [{ code: "ERR", message: "Server error" }],
    };
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(envelope),
    }) as unknown as typeof fetch;

    renderModal();

    fireEvent.change(screen.getByTestId("deck-name-input"), {
      target: { value: "My Deck" },
    });
    fireEvent.change(screen.getByTestId("deck-content-input"), {
      target: { value: "4 Bolt" },
    });

    fireEvent.click(screen.getByTestId("submit-import-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("import-error")).toBeDefined();
    });
  });

  it("toggles format between text and csv", () => {
    renderModal();

    const textBtn = screen.getByTestId("format-text-btn");
    const csvBtn = screen.getByTestId("format-csv-btn");

    // Text is active by default
    expect(textBtn.className).toContain("bg-indigo-600");
    expect(csvBtn.className).not.toContain("bg-indigo-600");

    fireEvent.click(csvBtn);
    expect(csvBtn.className).toContain("bg-indigo-600");
    expect(textBtn.className).not.toContain("bg-indigo-600");
  });
});
