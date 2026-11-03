"use client";

import { Suspense, createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { FeedbackDialog } from "./FeedbackDialog";

interface FeedbackContextValue {
  openFeedback: () => void;
}

const FeedbackContext = createContext<FeedbackContextValue | null>(null);

/** Hosts the single feedback dialog for every page (FEED-001). */
export function FeedbackProvider({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const openFeedback = useCallback(() => setOpen(true), []);
  const value = useMemo(() => ({ openFeedback }), [openFeedback]);
  return (
    <FeedbackContext.Provider value={value}>
      {children}
      {/* The dialog reads the current path; Suspense keeps dynamic pages prerenderable. */}
      <Suspense>
        <FeedbackDialog open={open} onClose={() => setOpen(false)} />
      </Suspense>
    </FeedbackContext.Provider>
  );
}

export function useFeedback(): FeedbackContextValue {
  const value = useContext(FeedbackContext);
  if (!value) throw new Error("useFeedback must be used inside <FeedbackProvider>");
  return value;
}
