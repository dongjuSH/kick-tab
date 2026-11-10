"use client";

import { useEffect, useId, useRef, useState, type CSSProperties, type ReactNode } from "react";
import { IconButton } from "./Button";
import { cx } from "./cx";

/**
 * Modal built on the native <dialog> (focus containment, Escape, top layer).
 * Focus returns to the element that opened it (Figma 55:27, guide §6.6).
 *
 * layout:
 * - "center": centred card on every screen size.
 * - "sheet": bottom sheet on every screen size.
 * - "responsive": bottom sheet below 1024px, centred card from 1024px.
 */
export type DialogLayout = "center" | "sheet" | "responsive";

interface DialogProps {
  open: boolean;
  onClose: () => void;
  title: ReactNode;
  children: ReactNode;
  layout?: DialogLayout;
  /** Max width of the centred card in px (Figma: 520 for feedback). */
  width?: number;
  closeLabel?: string;
  /**
   * Compact sheet (Figma TOP 5 sheet 159:924 mobile): drag handle, 16px padding, 16px
   * title, and the sheet never grows past its max height: children decide what scrolls.
   */
  compact?: boolean;
  /** Drag handle on the bottom sheet only (Figma competition picker 187:1372, 2026-11-02). */
  handle?: boolean;
  /** Where focus starts on open: the dialog itself (default) or its close button. */
  initialFocus?: "dialog" | "close";
  id?: string;
  className?: string;
}

const SHEET = "mt-auto mb-0 w-full max-w-none rounded-b-none";
const CENTER = "m-auto w-[calc(100%-32px)] max-h-[calc(100dvh-32px)]";
const LAYOUTS: Record<DialogLayout, string> = {
  sheet: SHEET,
  center: CENTER,
  responsive: cx(SHEET, "lg:m-auto lg:w-[calc(100%-32px)] lg:rounded-b-card lg:max-h-[calc(100dvh-32px)]"),
};

export function Dialog({
  open,
  onClose,
  title,
  children,
  layout = "responsive",
  width = 520,
  closeLabel = "닫기",
  compact = false,
  handle = false,
  initialFocus = "dialog",
  id,
  className,
}: DialogProps) {
  const ref = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  const returnFocus = useRef<HTMLElement | null>(null);
  const onCloseRef = useRef(onClose);
  // Content is mounted from the first open render until a closing dialog has finished its exit
  // transition (TOP 5 sheet slides down with the same list and scroll position); dialogs
  // without an exit transition drop it right away.
  const [shown, setShown] = useState(open);
  if (open && !shown) setShown(true);

  useEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) {
      returnFocus.current = document.activeElement as HTMLElement | null;
      dialog.showModal();
      // Default: start on the dialog itself so no control shows a focus ring until the user tabs.
      const close = initialFocus === "close" ? dialog.querySelector<HTMLElement>("[data-dialog-close]") : null;
      (close ?? dialog).focus();
      document.documentElement.style.overflow = "hidden";
    } else if (!open && dialog.open) {
      dialog.close();
      const exit = Math.max(0, ...getComputedStyle(dialog).transitionDuration.split(",").map(parseFloat)) * 1000;
      const timer = window.setTimeout(() => setShown(false), exit);
      return () => window.clearTimeout(timer);
    }
  }, [open, initialFocus]);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    const handleClose = () => {
      // A queued close event can arrive after the dialog has reopened.
      if (dialog.open) return;
      if (!document.querySelector("dialog:modal")) {
        document.documentElement.style.overflow = "";
        returnFocus.current?.focus?.();
      }
      returnFocus.current = null;
    };
    // Escape fires "cancel": let the parent own the open state.
    const handleCancel = (event: Event) => {
      event.preventDefault();
      onCloseRef.current();
    };
    dialog.addEventListener("close", handleClose);
    dialog.addEventListener("cancel", handleCancel);
    return () => {
      dialog.removeEventListener("close", handleClose);
      dialog.removeEventListener("cancel", handleCancel);
      if (dialog.open) dialog.close();
      if (!document.querySelector("dialog:modal")) document.documentElement.style.overflow = "";
    };
  }, []);

  return (
    <dialog
      ref={ref}
      id={id}
      // Not interactive while it animates out.
      inert={!open}
      tabIndex={-1}
      aria-labelledby={titleId}
      style={{ "--kt-dialog-width": `${width}px` } as CSSProperties}
      className={cx(
        "overscroll-contain rounded-card border border-line bg-surface p-0 text-fg outline-none",
        // The compact sheet never scrolls as a whole: a flex <dialog> reports extra scroll
        // height even when its content fits, so its body scrolls inside instead.
        compact ? "overflow-clip" : "overflow-y-auto",
        "backdrop:bg-fg/12 lg:max-w-(--kt-dialog-width)",
        layout === "center" && "max-w-(--kt-dialog-width)",
        // Sheet height: 85% of the screen; the compact sheet stops at the bottom of the sticky
        // header + TOP 5 strip instead (Figma 128:4408).
        layout !== "center" &&
          (compact ? "open:flex open:flex-col max-h-[calc(100dvh-var(--kt-header-height))]" : "max-h-[85dvh]"),
        LAYOUTS[layout],
        className,
      )}
      onClick={(event) => {
        // A click on the backdrop targets the <dialog> element itself.
        if (event.target === event.currentTarget) onClose();
      }}
    >
      {shown && (
        <div
          className={cx(
            "flex flex-col",
            compact ? "min-h-0 gap-3 overflow-y-auto p-4" : handle ? "gap-3 p-4 lg:gap-4 lg:p-6" : "gap-4 p-6",
          )}
        >
          {(compact || (handle && layout !== "center")) && (
            <span
              aria-hidden
              className={cx(
                "mx-auto h-1 w-8 shrink-0 rounded-full bg-line-strong",
                !compact && layout === "responsive" && "lg:hidden",
              )}
            />
          )}
          <div className="flex items-center gap-2">
            <h2 id={titleId} className={cx("min-w-0 flex-1 font-bold", compact ? "text-lead" : "text-title")}>
              {title}
            </h2>
            <IconButton icon="x" label={closeLabel} onClick={onClose} data-dialog-close />
          </div>
          {children}
        </div>
      )}
    </dialog>
  );
}

/** Bottom sheet (mobile TOP 5 list, mobile menu). */
export function BottomSheet(props: Omit<DialogProps, "layout">) {
  return <Dialog {...props} layout="sheet" />;
}
