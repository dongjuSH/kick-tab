"use client";

import { useEffect, useId, useRef, useState } from "react";
import { IconButton } from "@/components/ui/Button";
import { cx } from "@/components/ui/cx";
import { NoticeIcon } from "./icons";

const GUTTER = 16;
const GAP = 4;
type Mode = "hover" | "pinned";
type Placement = { left: number; width: number; top?: number; bottom?: number; maxHeight: number };

export function ReviewGuidance() {
  const id = useId();
  const root = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const hoverClose = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const [mode, setMode] = useState<Mode | null>(null);
  const [placement, setPlacement] = useState<Placement>();
  const open = mode !== null;

  function updatePlacement() {
    const anchor = trigger.current?.getBoundingClientRect();
    if (!anchor) return;
    const width = Math.min(window.innerWidth >= 1024 ? 360 : 309, document.documentElement.clientWidth - GUTTER * 2);
    const below = window.innerHeight - anchor.bottom - GAP - GUTTER;
    const above = anchor.top - GAP - GUTTER;
    const upward = below < 260 && above > below;
    setPlacement({
      left: Math.max(GUTTER, Math.min(anchor.left, document.documentElement.clientWidth - width - GUTTER)),
      width,
      ...(upward ? { bottom: window.innerHeight - anchor.top + GAP } : { top: anchor.bottom + GAP }),
      maxHeight: Math.max(0, upward ? above : below),
    });
  }

  function close(restoreFocus: boolean) {
    clearTimeout(hoverClose.current);
    setMode(null);
    if (restoreFocus) trigger.current?.focus({ preventScroll: true });
  }

  useEffect(() => {
    if (!open) return;
    const outside = (event: MouseEvent) => {
      if (!(event.target instanceof Node) || root.current?.contains(event.target)) return;
      close(document.activeElement === document.body || (root.current?.contains(document.activeElement) ?? false));
    };
    const escape = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      event.preventDefault();
      close(root.current?.contains(document.activeElement) ?? false);
    };
    window.addEventListener("resize", updatePlacement);
    window.addEventListener("scroll", updatePlacement, true);
    document.addEventListener("click", outside);
    document.addEventListener("keydown", escape);
    return () => {
      clearTimeout(hoverClose.current);
      window.removeEventListener("resize", updatePlacement);
      window.removeEventListener("scroll", updatePlacement, true);
      document.removeEventListener("click", outside);
      document.removeEventListener("keydown", escape);
    };
  }, [open]);

  return (
    <div
      ref={root}
      className="shrink-0"
      onPointerEnter={(event) => {
        if (event.pointerType !== "mouse") return;
        clearTimeout(hoverClose.current);
        if (open) return;
        updatePlacement();
        setMode("hover");
      }}
      onPointerLeave={(event) => {
        if (event.pointerType !== "mouse" || mode !== "hover") return;
        hoverClose.current = setTimeout(() => {
          if (!root.current?.contains(document.activeElement)) setMode(null);
        }, 140);
      }}
      onBlur={(event) => {
        if (mode === "hover" && !event.currentTarget.contains(event.relatedTarget) &&
          !event.currentTarget.matches(":hover")) close(false);
      }}
    >
      <button
        ref={trigger}
        type="button"
        aria-label="평가 작성 주의사항"
        aria-expanded={open}
        aria-haspopup="dialog"
        aria-controls={open ? id : undefined}
        className={cx("grid size-11 cursor-pointer place-items-center rounded-control text-fg-muted hover:bg-subtle hover:text-fg-secondary",
          mode === "pinned" && "bg-subtle text-fg-secondary")}
        onClick={() => {
          if (mode === "pinned") close(true);
          else {
            clearTimeout(hoverClose.current);
            updatePlacement();
            setMode("pinned");
          }
        }}
      >
        <NoticeIcon />
      </button>
      {open && (
        <div
          id={id}
          role="dialog"
          aria-labelledby={`${id}-title`}
          style={placement}
          className="fixed z-40 flex flex-col gap-3 overflow-hidden rounded-card border border-line-strong bg-surface p-4 shadow-lg"
        >
          <div className="flex shrink-0 items-center justify-between gap-2">
            <h3 id={`${id}-title`} className="text-label font-bold">평가 작성 주의사항</h3>
            <IconButton icon="x" label="주의사항 닫기" onClick={() => close(true)} />
          </div>
          <div className="flex max-h-[280px] min-h-0 flex-col gap-3 overflow-y-auto text-small text-fg-secondary" tabIndex={0}>
            <ul className="list-disc space-y-1.5 pl-4">
              <li>이용자를 겨냥한 시비·반복 도발·싸움 유도·집단 괴롭힘은 제한합니다.</li>
              <li>도 넘은 인신공격·가족 비난·혐오·성희롱·협박·폭력 조장은 금지합니다.</li>
              <li>개인정보 노출, 확인되지 않은 범죄·사생활 의혹의 단정은 제한합니다.</li>
              <li>광고·도배·불법 베팅 홍보 등 경기와 무관한 내용은 제한합니다.</li>
            </ul>
            <p className="font-bold">
              농담이어도 대상과 맥락·수위·반복성을 함께 판단하며, 기준을 넘은 평가는 삭제될 수 있습니다.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
