"use client";

import { queryOptions, useQuery } from "@tanstack/react-query";
import { useDeferredValue, useEffect, useId, useRef, useState } from "react";
import { IconButton } from "@/components/ui/Button";
import { StateMessage } from "@/components/ui/DataState";
import { Icon } from "@/components/ui/Icon";
import { Skeleton } from "@/components/ui/Skeleton";
import { cx } from "@/components/ui/cx";
import { apiFetch } from "@/lib/api/client";
import { queryKeys } from "@/lib/api/query-keys";
import type { TeamRef } from "@/lib/api/types";
import { teamName } from "@/lib/format/match";
import { TeamCrest } from "./TeamCrest";

function teamSearchQuery(q: string) {
  return queryOptions({
    queryKey: queryKeys.teams.search(q),
    queryFn: async ({ signal }) => (await apiFetch<TeamRef[]>("/teams/search", { query: { q }, signal })).data,
    staleTime: 10 * 60_000,
  });
}

/**
 * Team search with autocomplete (SCH-006, Figma 225:1086 field, 57:58 candidates, 225:2374
 * no match). Korean/English aliases resolve on the server; an alias naming several teams
 * lists them all ("후보 중 원하는 팀을 선택하세요"). Nothing is ever replaced by another team.
 * Clearing the text (× beside the field) clears the selection.
 */
export function TeamSearch({
  selected,
  onSelect,
  description,
}: {
  selected: TeamRef | null;
  onSelect: (team: TeamRef | null) => void;
  description?: string;
}) {
  const [text, setText] = useState(selected ? teamName(selected) : "");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const listId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const boxRef = useRef<HTMLDivElement>(null);
  const query = useDeferredValue(text.trim());
  const search = useQuery({ ...teamSearchQuery(query), enabled: open && query.length > 0 });
  const results = search.data ?? [];

  // Follow outside changes (reset, favourite button, URL) without fighting the user's typing.
  const selectedKey = selected?.id ?? null;
  const [syncedKey, setSyncedKey] = useState(selectedKey);
  if (syncedKey !== selectedKey) {
    setSyncedKey(selectedKey);
    setText(selected ? teamName(selected) : "");
    setOpen(false);
  }

  useEffect(() => {
    if (!open) return;
    const close = (event: PointerEvent) => {
      if (!boxRef.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("pointerdown", close);
    return () => document.removeEventListener("pointerdown", close);
  }, [open]);

  const pick = (team: TeamRef) => {
    onSelect(team);
    setText(teamName(team));
    setOpen(false);
  };

  const clear = () => {
    setText("");
    setOpen(false);
    if (selected) onSelect(null);
    inputRef.current?.focus();
  };

  const showList = open && query.length > 0;
  const optionId = (index: number) => `${listId}-option-${index}`;

  return (
    <div ref={boxRef} className="relative">
      {description && <label htmlFor={`${listId}-input`} className="mb-2 block text-body font-bold">팀 일정 검색</label>}
      {description && <p id={`${listId}-help`} className="mb-3 text-small text-fg-secondary">{description}</p>}
      <div className="relative flex items-center">
        <span className="pointer-events-none absolute left-3 text-fg-secondary"><Icon name="search" /></span>
        <label className="flex min-h-11 min-w-0 flex-1 items-center">
          {!description && <span className="sr-only">팀 검색</span>}
          <input
            ref={inputRef}
            id={`${listId}-input`}
            type="search"
            role="combobox"
            aria-expanded={showList}
            aria-controls={listId}
            aria-autocomplete="list"
            aria-describedby={description ? `${listId}-help` : undefined}
            aria-activedescendant={showList && results.length ? optionId(active) : undefined}
            autoComplete="off"
            placeholder="예: 맨시티, 레알 마드리드, Bayern Munich"
            maxLength={40}
            value={text}
            onChange={(event) => {
              setText(event.target.value);
              // Deleting the whole search term ends the team view (policy 2026-11-02).
              if (!event.target.value.trim() && selected) onSelect(null);
              setActive(0);
              setOpen(true);
            }}
            onFocus={() => text.trim() && !selected && setOpen(true)}
            onKeyDown={(event) => {
              if (event.key === "Escape") {
                setOpen(false);
              } else if (event.key === "ArrowDown" && results.length) {
                event.preventDefault();
                setOpen(true);
                setActive((i) => (i + 1) % results.length);
              } else if (event.key === "ArrowUp" && results.length) {
                event.preventDefault();
                setActive((i) => (i - 1 + results.length) % results.length);
              } else if (event.key === "Enter" && showList && results[active]) {
                event.preventDefault();
                pick(results[active]);
              }
            }}
            className="h-11 w-full rounded-control border border-line-strong bg-surface pl-9 pr-11 text-body text-fg placeholder:text-fg-muted [&::-webkit-search-cancel-button]:hidden"
          />
        </label>
        {text && <IconButton className="absolute right-0" icon="x" label="검색어 지우기" onClick={clear} />}
      </div>

      {showList && (
        <div className="absolute inset-x-0 top-full z-20 mt-1 rounded-control border border-line bg-surface p-3 shadow-lg">
          {search.isPending ? (
            <div className="flex flex-col gap-2" aria-busy>
              <Skeleton className="h-6 w-2/3" />
              <Skeleton className="h-6 w-1/2" />
              <span className="sr-only">팀을 찾는 중</span>
            </div>
          ) : search.isError ? (
            <StateMessage tone="error" title="팀을 찾지 못했습니다" description="잠시 후 다시 시도해 주세요." className="p-2" />
          ) : results.length === 0 ? (
            <p role="status" className="rounded-control bg-canvas px-3 py-2 text-label text-fg-secondary">
              일치하는 팀이 없습니다. 다른 팀으로 바꿔 보여주지 않습니다.
            </p>
          ) : (
            <>
              {results.length > 1 && <p className="mb-2 text-small text-fg-muted">후보 중 원하는 팀을 선택하세요.</p>}
              <ul id={listId} role="listbox" aria-label="팀 후보" className="flex flex-col">
                {results.map((team, index) => (
                  <li
                    key={team.id}
                    id={optionId(index)}
                    role="option"
                    aria-selected={index === active}
                    onPointerDown={(event) => event.preventDefault()}
                    onClick={() => pick(team)}
                    onMouseEnter={() => setActive(index)}
                    className={cx(
                      "flex min-h-11 cursor-pointer items-center gap-3 rounded-control px-2",
                      index === active && "bg-subtle",
                    )}
                  >
                    <TeamCrest src={team.crestUrl} name={teamName(team)} size={24} />
                    <span className="min-w-0 flex-1 truncate text-body text-fg">
                      {teamName(team)}
                      {team.nameKo && <span className="ml-2 text-small text-fg-muted">{team.nameEn}</span>}
                    </span>
                    <Icon name="chevron-right" />
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      )}
    </div>
  );
}
