import type { FeedbackType } from "@/lib/api/types";

/** Unsent feedback draft kept in sessionStorage (guide §6.6 ④). */
export interface FeedbackDraft {
  body: string;
  type: FeedbackType | null;
}

const KEY = "kt-feedback-draft";
export const EMPTY_DRAFT: FeedbackDraft = { body: "", type: null };

// Storage can be unavailable (private mode, blocked site data): fail silently.
export function loadDraft(): FeedbackDraft {
  try {
    const raw = window.sessionStorage.getItem(KEY);
    if (!raw) return EMPTY_DRAFT;
    const parsed = JSON.parse(raw) as Partial<FeedbackDraft>;
    return {
      body: typeof parsed.body === "string" ? parsed.body : "",
      type: parsed.type === "bug" || parsed.type === "suggestion" || parsed.type === "other" ? parsed.type : null,
    };
  } catch {
    return EMPTY_DRAFT;
  }
}

export function saveDraft(draft: FeedbackDraft): void {
  try {
    if (!draft.body && !draft.type) window.sessionStorage.removeItem(KEY);
    else window.sessionStorage.setItem(KEY, JSON.stringify(draft));
  } catch {
    // ignore
  }
}

export function clearDraft(): void {
  try {
    window.sessionStorage.removeItem(KEY);
  } catch {
    // ignore
  }
}
