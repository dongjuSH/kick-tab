"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { cx } from "@/components/ui/cx";
import type { FavoriteChange } from "./store";
import { useFavorites } from "./useFavorites";

const MESSAGES: Partial<Record<FavoriteChange, string>> = {
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
  const [message, setMessage] = useState<string | null>(null);
  const active = favorites.has(teamId);

  const toggle = () => {
    const result = active ? favorites.remove(teamId) : favorites.add(teamId);
    setMessage(MESSAGES[result] ?? null);
  };

  return (
    <div className={cx("flex flex-col gap-1", className)}>
      <Button
        variant={active ? "primary" : "secondary"}
        fullWidth={fullWidth}
        aria-pressed={active}
        aria-label={`${teamName} 관심 팀 ${active ? "해제" : "등록"}`}
        disabled={favorites.status === "loading"}
        onClick={toggle}
      >
        {active ? "★ 관심 팀 등록됨" : "☆ 관심 팀 등록"}
      </Button>
      {message && (
        <p role="status" className="text-small text-warning">
          {message}
        </p>
      )}
    </div>
  );
}
