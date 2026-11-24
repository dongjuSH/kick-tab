"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { TeamCrest } from "@/components/common/TeamCrest";
import { TeamSearch } from "@/components/common/TeamSearch";
import { Button } from "@/components/ui/Button";
import { DataState } from "@/components/ui/DataState";
import { favoriteRefusal } from "@/features/favorites/FavoriteToggle";
import type { FavoriteChange } from "@/features/favorites/store";
import { memberFavoritesQuery, useFavorites } from "@/features/favorites/useFavorites";
import type { TeamRef } from "@/lib/api/types";
import { teamName } from "@/lib/format/match";
import { favoriteAddBlocked, favoriteCountText, favoriteLimitText, teamDetailNote } from "./model";
import { AreaError, MyCard } from "./MyCard";

/**
 * 관심 팀 (MY-002, Figma 52:2674 / 52:2912, limit 656:27025). The account list through
 * `useFavorites()` — the same list and actions as the main panel, team browse and team detail —
 * in registration order, up to 10, all shown (no main-panel folding). '관심 팀 추가' opens the
 * same team search as the main panel; at 10 / 10 only adding stops.
 */
export function FavoriteTeams() {
  const favorites = useFavorites();
  // Names, crests and detail links come from the same cached account list.
  const list = useQuery({ ...memberFavoritesQuery, enabled: favorites.source === "member" });
  const teams = new Map((list.data?.teams ?? []).map((team) => [team.id, team]));
  const [adding, setAdding] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const addButton = useRef<HTMLButtonElement>(null);
  const limitNotice = useRef<HTMLParagraphElement>(null);
  const count = favorites.ids.length;
  const blocked = favoriteAddBlocked(count, favorites.max);
  // After an add or a removal the pressed control is gone (search closed, row removed) or
  // disabled (10 / 10): focus goes to '관심 팀 추가', or to the limit notice once it is off.
  const refocus = useRef(false);
  useEffect(() => {
    if (!refocus.current) return;
    refocus.current = false;
    (blocked ? limitNotice.current : addButton.current)?.focus();
  }, [count, blocked, adding]);

  const run = async (change: () => Promise<FavoriteChange>) => {
    setSaving(true);
    const result = await change();
    setSaving(false);
    setMessage(favoriteRefusal(result, favorites.max));
    return result;
  };
  const add = async (team: TeamRef) => {
    // Set before the change: the list (and the effect) updates before the promise resolves.
    refocus.current = true;
    const result = await run(() => favorites.add(team.id));
    if (result === "added" || result === "exists") setAdding(false);
    else refocus.current = false;
  };
  const remove = async (teamId: number) => {
    refocus.current = true;
    if ((await run(() => favorites.remove(teamId))) !== "removed") refocus.current = false;
  };

  let body;
  if (favorites.status === "loading") {
    body = <DataState status="loading" />;
  } else if (favorites.status !== "ready") {
    // The account list could not be read: never replaced by this browser's list (COM-005).
    body = <AreaError text="관심 팀을 불러오지 못했습니다." onRetry={favorites.retry} />;
  } else {
    body = (
      <>
        <p className="text-label text-fg-muted">{favoriteCountText(count, favorites.max)}</p>
        {blocked && (
          <p
            ref={limitNotice}
            tabIndex={-1}
            role="status"
            className="rounded-control bg-subtle p-4 text-body text-fg-secondary"
          >
            {favoriteLimitText(favorites.max)}
          </p>
        )}
        <Button
          ref={addButton}
          className="self-stretch lg:self-start lg:px-8"
          aria-expanded={adding && !blocked}
          disabled={blocked || saving}
          onClick={() => {
            setAdding((open) => !open);
            setMessage(null);
          }}
        >
          관심 팀 추가
        </Button>
        {adding && !blocked && (
          <TeamSearch
            label="관심 팀 검색"
            selected={null}
            onSelect={(team) => team && add(team)}
            candidates={(team) => team.detailAvailable === true && !favorites.ids.includes(team.id)}
          />
        )}
        {message && (
          <p role="status" className="text-small text-warning">
            {message}
          </p>
        )}
        {count === 0 ? (
          <p className="text-body text-fg-secondary">등록한 관심 팀이 없습니다.</p>
        ) : (
          <ul aria-label="등록된 관심 팀" className="flex flex-col">
            {favorites.ids.map((id) => (
              <FavoriteRow
                key={id}
                team={teams.get(id)}
                saving={saving}
                onRemove={() => remove(id)}
              />
            ))}
          </ul>
        )}
      </>
    );
  }

  return (
    <MyCard title="관심 팀" titleId="my-favorites-title">
      {body}
    </MyCard>
  );
}

function FavoriteRow({
  team,
  saving,
  onRemove,
}: {
  team: TeamRef | undefined;
  saving: boolean;
  onRemove: () => void;
}) {
  const name = team ? teamName(team) : "팀 정보 확인 중";
  const note = team ? teamDetailNote(team.detailAvailable) : null;
  return (
    <li className="flex min-h-14 items-center gap-3 border-b border-line py-1.5">
      <TeamCrest src={team?.crestUrl ?? null} name={name} size={32} />
      <span className="flex min-w-0 flex-1 flex-col">
        {team?.detailAvailable === true ? (
          <Link
            href={`/teams/${team.id}`}
            prefetch={false}
            className="self-start text-body font-medium break-words text-fg hover:underline"
          >
            {name}
          </Link>
        ) : (
          <span className="text-body font-medium break-words text-fg">{name}</span>
        )}
        {note && <span className="text-small text-fg-muted">{note}</span>}
      </span>
      <Button variant="text" aria-label={`${name} 관심 팀 삭제`} disabled={saving} onClick={onRemove}>
        삭제
      </Button>
    </li>
  );
}
