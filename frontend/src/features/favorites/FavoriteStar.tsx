"use client";

import { useEffect, useState } from "react";
import { cx } from "@/components/ui/cx";
import { FAVORITE_REFUSALS } from "./FavoriteToggle";
import { useFavorites } from "./useFavorites";

/**
 * Star beside a team name on a match card (Figma 49:57 / 49:570, 2026-11-09): registers or
 * removes the team without leaving the page. A refusal (6th team, storage blocked, write
 * failed) keeps the list and says why for a few seconds.
 */
export function FavoriteStar({ teamId, teamName }: { teamId: number; teamName: string }) {
  const favorites = useFavorites();
  const [refusal, setRefusal] = useState<string | null>(null);
  const active = favorites.has(teamId);

  useEffect(() => {
    if (!refusal) return;
    const timer = setTimeout(() => setRefusal(null), 3_000);
    return () => clearTimeout(timer);
  }, [refusal]);

  return (
    <span className="relative inline-flex shrink-0">
      <button
        type="button"
        aria-pressed={active}
        aria-label={`${teamName} 관심 팀 ${active ? "해제" : "등록"}`}
        disabled={favorites.status === "loading"}
        onClick={() => {
          const result = active ? favorites.remove(teamId) : favorites.add(teamId);
          setRefusal(FAVORITE_REFUSALS[result] ?? null);
        }}
        // 24px star, 44px target (guide §3.1 '조작 영역').
        className="relative inline-flex size-6 items-center justify-center rounded-full before:absolute before:-inset-2.5 hover:bg-subtle"
      >
        <svg aria-hidden width="16" height="16" viewBox="0 0 16 16" className={cx(active ? "text-action" : "text-fg-muted")}>
          <path
            d="M8 1.6l1.9 4 4.4.5-3.3 3 .9 4.3L8 11.2l-3.9 2.2.9-4.3-3.3-3 4.4-.5z"
            fill={active ? "currentColor" : "none"}
            stroke="currentColor"
            strokeWidth="1.3"
            strokeLinejoin="round"
          />
        </svg>
      </button>
      {refusal && (
        <span
          role="status"
          className="absolute top-full left-1/2 z-20 mt-1 w-max max-w-56 -translate-x-1/2 rounded-control border border-line bg-surface px-2 py-1 text-small text-warning shadow-lg"
        >
          {refusal}
        </span>
      )}
    </span>
  );
}
