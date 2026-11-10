"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { cx } from "@/components/ui/cx";
import type { FavoriteChange } from "./store";
import { useFavorites } from "./useFavorites";

/** Why a change was refused (FAV-002); shared by the toggle and the match-card star. */
export const FAVORITE_REFUSALS: Partial<Record<FavoriteChange, string>> = {
  limit: "관심 팀은 최대 5개까지 등록할 수 있습니다.",
  unavailable: "이 브라우저에서는 관심 팀을 저장할 수 없습니다.",
  failed: "저장하지 못했습니다. 다시 시도해 주세요.",
};

/**
 * Register / unregister one team (Figma 52:723 "☆ 관심 팀 등록" / 52:737 "★ 관심 팀 등록됨").
 * Team browse (07) and team detail (08) place it; a refusal keeps the list unchanged and
 * says why (FAV-002: 6th team, storage blocked, write failed).
 */
export function FavoriteToggle({
  teamId,
  teamName,
  fullWidth = true,
  className,
}: {
  teamId: number;
  /** Accessible name, e.g. "맨체스터 시티 관심 팀 등록". */
  teamName: string;
  fullWidth?: boolean;
  className?: string;
}) {
  const favorites = useFavorites();
  // A refusal belongs to the list it was given for: once the list changes it is dropped, so
  // it never returns when the same list comes back (Codex 1차 지적 2). The list is taken on the
  // render after the press, since the press itself may reveal a newer list (another tab
  // already saved five teams).
  const listKey = `${favorites.status}:${favorites.ids.join(",")}`;
  const [refusal, setRefusal] = useState<{ text: string; listKey: string | null } | null>(null);
  if (refusal && refusal.listKey === null) setRefusal({ text: refusal.text, listKey });
  else if (refusal && refusal.listKey !== listKey) setRefusal(null);
  const message = refusal && (refusal.listKey ?? listKey) === listKey ? refusal.text : null;
  const active = favorites.has(teamId);
  // Figma 57:766 fav-full: with five teams the others cannot be added (FAV-002 6th refused).
  const full = !active && favorites.status === "ready" && favorites.ids.length >= favorites.max;

  const toggle = () => {
    const result = active ? favorites.remove(teamId) : favorites.add(teamId);
    const text = FAVORITE_REFUSALS[result];
    setRefusal(text ? { text, listKey: null } : null);
  };

  return (
    <div className={cx("flex flex-col gap-1", className)}>
      <Button
        variant={active ? "primary" : "secondary"}
        fullWidth={fullWidth}
        aria-pressed={active}
        aria-label={
          full
            ? `${teamName} 관심 팀 등록 불가, 최대 ${favorites.max}개까지 등록할 수 있어요`
            : `${teamName} 관심 팀 ${active ? "해제" : "등록"}`
        }
        disabled={favorites.status === "loading" || full}
        onClick={toggle}
      >
        {active ? "★ 관심 팀 등록됨" : full ? `최대 ${favorites.max}개까지 등록할 수 있어요` : "☆ 관심 팀 등록"}
      </Button>
      {message && (
        <p role="status" className="text-small text-warning">
          {message}
        </p>
      )}
    </div>
  );
}
