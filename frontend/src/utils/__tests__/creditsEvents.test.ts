import { describe, it, expect, vi } from "vitest";
import { CREDITS_CHANGED_EVENT, notifyCreditsChanged } from "../creditsEvents";

describe("creditsEvents", () => {
  it("has the expected event name", () => {
    expect(CREDITS_CHANGED_EVENT).toBe("credits:changed");
  });

  it("dispatches an Event of type credits:changed on window", () => {
    const listener = vi.fn();
    window.addEventListener(CREDITS_CHANGED_EVENT, listener);

    notifyCreditsChanged();

    expect(listener).toHaveBeenCalledTimes(1);
    const event = listener.mock.calls[0][0] as Event;
    expect(event.type).toBe(CREDITS_CHANGED_EVENT);

    window.removeEventListener(CREDITS_CHANGED_EVENT, listener);
  });
});
