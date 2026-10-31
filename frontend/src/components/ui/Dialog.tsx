"use client";

import { useEffect, useId, useRef, type CSSProperties, type ReactNode } from "react";
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
  className?: string;
}

const SHEET = "mt-auto mb-0 w-full max-w-none rounded-b-none max-h-[85dvh]";
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
  className,
}: DialogProps) {
  const ref = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  const returnFocus = useRef<HTMLElement | null>(null);
  const onCloseRef = useRef(onClose);

  useEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) {
      returnFocus.current = document.activeElement as HTMLElement | null;
      dialog.showModal();
      document.documentElement.style.overflow = "hidden";
    } else if (!open && dialog.open) {
      dialog.close();
    }
  }, [open]);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    const handleClose = () => {
      document.documentElement.style.overflow = "";
      returnFocus.current?.focus?.();
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
      document.documentElement.style.overflow = "";
    };
  }, []);

  return (
    <dialog
      ref={ref}
      aria-labelledby={titleId}
      style={{ "--kt-dialog-width": `${width}px` } as CSSProperties}
      className={cx(
        "overflow-y-auto overscroll-contain rounded-card border border-line bg-surface p-0 text-fg",
        "backdrop:bg-fg/40 lg:max-w-(--kt-dialog-width)",
        layout === "center" && "max-w-(--kt-dialog-width)",
        LAYOUTS[layout],
        className,
      )}
      onClick={(event) => {
        // A click on the backdrop targets the <dialog> element itself.
        if (event.target === event.currentTarget) onClose();
      }}
    >
      {open && (
        <div className="flex flex-col gap-4 p-6">
          <div className="flex items-center gap-2">
            <h2 id={titleId} className="min-w-0 flex-1 text-title font-bold">
              {title}
            </h2>
            <IconButton icon="x" label={closeLabel} onClick={onClose} />
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
