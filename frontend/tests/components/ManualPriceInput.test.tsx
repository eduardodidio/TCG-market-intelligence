import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { ManualPriceInput } from "../../src/components/ManualPriceInput";

describe("ManualPriceInput", () => {
  let originalFetch: typeof globalThis.fetch;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("renders input field and save button", () => {
    render(<ManualPriceInput entryId={1} currency="BRL" onSaved={() => {}} />);
    expect(screen.getByTestId("manual-price-input")).toBeDefined();
    expect(screen.getByTestId("manual-price-field")).toBeDefined();
    expect(screen.getByTestId("manual-price-save")).toBeDefined();
  });

  it("shows 'Set Price' label", () => {
    render(<ManualPriceInput entryId={1} currency="BRL" onSaved={() => {}} />);
    expect(screen.getByText("Set Price")).toBeDefined();
  });

  it("rejects empty value (save button disabled)", () => {
    render(<ManualPriceInput entryId={1} currency="BRL" onSaved={() => {}} />);
    const saveBtn = screen.getByTestId("manual-price-save");
    expect(saveBtn.hasAttribute("disabled")).toBe(true);
  });

  it("rejects negative price with validation error", async () => {
    render(<ManualPriceInput entryId={1} currency="BRL" onSaved={() => {}} />);
    const input = screen.getByTestId("manual-price-field");
    fireEvent.change(input, { target: { value: "-5" } });
    screen.getByTestId("manual-price-save").click();

    await waitFor(() => {
      expect(screen.getByTestId("manual-price-error")).toBeDefined();
    });
  });

  it("rejects zero price with validation error", async () => {
    render(<ManualPriceInput entryId={1} currency="BRL" onSaved={() => {}} />);
    const input = screen.getByTestId("manual-price-field");
    fireEvent.change(input, { target: { value: "0" } });
    screen.getByTestId("manual-price-save").click();

    await waitFor(() => {
      expect(screen.getByTestId("manual-price-error")).toBeDefined();
    });
  });

  it("rejects price over 99999.99 with validation error", async () => {
    render(<ManualPriceInput entryId={1} currency="BRL" onSaved={() => {}} />);
    const input = screen.getByTestId("manual-price-field");
    fireEvent.change(input, { target: { value: "100000" } });
    screen.getByTestId("manual-price-save").click();

    await waitFor(() => {
      expect(screen.getByTestId("manual-price-error")).toBeDefined();
    });
  });

  it("calls PATCH /collection/{id}/price with correct body on save", async () => {
    const onSaved = vi.fn();
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          data: { id: 1, latest_price: 25.5, price_source: "manual" },
          meta: { cursor: null, total: null, offset: null, request_id: "r1" },
          errors: [],
        }),
    });
    globalThis.fetch = mockFetch as unknown as typeof fetch;

    render(<ManualPriceInput entryId={42} currency="USD" onSaved={onSaved} />);
    const input = screen.getByTestId("manual-price-field");
    fireEvent.change(input, { target: { value: "25.50" } });
    screen.getByTestId("manual-price-save").click();

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled();
    });

    const [url, opts] = mockFetch.mock.calls[0];
    expect(String(url)).toContain("/api/v1/collection/42/price");
    expect(opts.method).toBe("PATCH");
    const body = JSON.parse(opts.body);
    expect(body.price).toBe(25.5);
    expect(body.currency).toBe("USD");
  });

  it("calls onSaved callback on successful save", async () => {
    const onSaved = vi.fn();
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          data: { id: 1 },
          meta: { cursor: null, total: null, offset: null, request_id: "r1" },
          errors: [],
        }),
    }) as unknown as typeof fetch;

    render(<ManualPriceInput entryId={1} currency="BRL" onSaved={onSaved} />);
    fireEvent.change(screen.getByTestId("manual-price-field"), { target: { value: "10" } });
    screen.getByTestId("manual-price-save").click();

    await waitFor(() => {
      expect(onSaved).toHaveBeenCalledTimes(1);
    });
  });

  it("shows success message after save", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          data: { id: 1 },
          meta: { cursor: null, total: null, offset: null, request_id: "r1" },
          errors: [],
        }),
    }) as unknown as typeof fetch;

    render(<ManualPriceInput entryId={1} currency="BRL" onSaved={() => {}} />);
    fireEvent.change(screen.getByTestId("manual-price-field"), { target: { value: "10" } });
    screen.getByTestId("manual-price-save").click();

    await waitFor(() => {
      expect(screen.getByTestId("manual-price-success")).toBeDefined();
      expect(screen.getByTestId("manual-price-success").textContent).toContain("Price saved");
    });
  });

  it("shows error message on API failure", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      json: () =>
        Promise.resolve({
          data: null,
          meta: { cursor: null, total: null, offset: null, request_id: "e1" },
          errors: [{ code: "internal", message: "Server error" }],
        }),
    }) as unknown as typeof fetch;

    render(<ManualPriceInput entryId={1} currency="BRL" onSaved={() => {}} />);
    fireEvent.change(screen.getByTestId("manual-price-field"), { target: { value: "10" } });
    screen.getByTestId("manual-price-save").click();

    await waitFor(() => {
      expect(screen.getByTestId("manual-price-error")).toBeDefined();
      expect(screen.getByTestId("manual-price-error").textContent).toContain("Server error");
    });
  });

  it("clears error when user types new value", async () => {
    render(<ManualPriceInput entryId={1} currency="BRL" onSaved={() => {}} />);
    const input = screen.getByTestId("manual-price-field");
    fireEvent.change(input, { target: { value: "-1" } });
    screen.getByTestId("manual-price-save").click();

    await waitFor(() => {
      expect(screen.getByTestId("manual-price-error")).toBeDefined();
    });

    fireEvent.change(input, { target: { value: "10" } });
    expect(screen.queryByTestId("manual-price-error")).toBeNull();
  });

  it("uses i18n for all visible text", () => {
    render(<ManualPriceInput entryId={1} currency="BRL" onSaved={() => {}} />);
    // "Set Price" comes from t("price.setPrice")
    expect(screen.getByText("Set Price")).toBeDefined();
    // "Save" comes from t("price.save")
    expect(screen.getByText("Save")).toBeDefined();
  });
});
