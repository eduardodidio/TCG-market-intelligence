export const CREDITS_CHANGED_EVENT = "credits:changed";

export function notifyCreditsChanged(): void {
  window.dispatchEvent(new Event(CREDITS_CHANGED_EVENT));
}
