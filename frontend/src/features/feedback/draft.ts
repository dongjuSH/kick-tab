import type { FeedbackType } from "@/lib/api/types";

/** Unsent feedback draft kept in sessionStorage (guide §6.6 ④). */
export interface FeedbackDraft {
  body: string;
  type: FeedbackType | null;
}

const KEY = "kt-feedback-draft";
export const EMPTY_DRAFT: FeedbackDraft = { body: "", type: null };

// Storage can be unavailable (private mode, blocked site data). Reading fails silently;
// saveDraft reports failure so the dialog can tell the user once (guide §6.6 ④).
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

/** Returns false when the draft could not be stored. */
export function saveDraft(draft: FeedbackDraft): boolean {
  try {
    if (!draft.body && !draft.type) window.sessionStorage.removeItem(KEY);
    else window.sessionStorage.setItem(KEY, JSON.stringify(draft));
    return true;
  } catch {
    return false;
  }
}

export function sameDraft(a: FeedbackDraft, b: FeedbackDraft): boolean {
  return a.body === b.body && a.type === b.type;
}

export function clearDraft(): void {
  try {
    window.sessionStorage.removeItem(KEY);
  } catch {
    // ignore
  }
}
