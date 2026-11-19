"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { Icon } from "@/components/ui/Icon";
import { cx } from "@/components/ui/cx";
import type { CompetitionGroup, CompetitionItem } from "@/lib/api/types";
import { competitionName } from "@/lib/format/match";

/** Headings of the picker list (navigation only, never "select the whole group"). */
const GROUP_TITLES: Record<CompetitionGroup, string> = {
  EPL: "잉글랜드",
  LaLiga: "스페인",
  SerieA: "이탈리아",
  Bundesliga: "독일",
  Ligue1: "프랑스",
  UEFA: "UEFA",
  FIFA: "FIFA",
};
const GROUPS = Object.keys(GROUP_TITLES) as CompetitionGroup[];

/** The viewed season of a competition: the given one (past results) or the current one. */
function seasonInfo(competition: CompetitionItem, season?: number) {
  return season === undefined
    ? competition.currentSeason
    : competition.seasons.find((s) => s.season === season) ?? null;
}

/**
 * Picker name (CMP-001, 2026-11-19): the competition's name, with the tournament year for the
 * club world cup, which is held only in some seasons ("FIFA 클럽 월드컵 2025").
 */
function pickerName(competition: CompetitionItem, season?: number) {
  const name = competitionName(competition);
  const held = seasonInfo(competition, season);
  return competition.group === "FIFA" && held ? `${name} ${held.season}` : name;
}

/** "전체 대회", "FA컵", "FA컵 외 1개" (first selected in list order + the rest). */
function competitionSummary(
  competitions: readonly CompetitionItem[],
  selected: readonly number[],
  season?: number,
) {
  const chosen = competitions.filter((c) => selected.includes(c.id));
  if (chosen.length === 0) return "전체 대회";
  const first = pickerName(chosen[0], season);
  return chosen.length === 1 ? first : `${first} 외 ${chosen.length - 1}개`;
}

/** A single draft for one or many competitions (Figma 187:1946). */
export function CompetitionFilter({
  competitions,
  selected,
  onChange,
  unavailable,
  season,
}: {
  competitions: readonly CompetitionItem[];
  selected: readonly number[];
  onChange: (ids: number[]) => void;
  unavailable?: ReadonlySet<number>;
  /** Season whose provider data is described (past results, chat 05); default current. */
  season?: number;
}) {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState<number[]>([]);

  const openPicker = () => {
    setDraft(competitions.filter((c) => selected.includes(c.id)).map((c) => c.id));
    setOpen(true);
  };
  const apply = (ids: number[]) => {
    onChange(ids);
    setOpen(false);
  };
  const summary = competitionSummary(competitions, selected, season);
  // A competition the viewed season does not know is left out, and so is the club world
  // cup outside its tournament season (2026-11-19: shown for 2025-26 only). Other "no data"
  // seasons stay listed with that note (CMP-004). A selection the URL still carries stays
  // listed so it can be cleared.
  const offered = competitions.filter((c) => {
    if (selected.includes(c.id)) return true;
    const info = seasonInfo(c, season);
    return info !== null && (c.group !== "FIFA" || info.availability === "available");
  });

  return (
    <>
      <button
        type="button"
        aria-haspopup="dialog"
        aria-label={`대회 선택: ${summary}`}
        onClick={openPicker}
        className="flex min-h-11 w-full items-center gap-3 rounded-control border border-line-strong bg-surface px-3 py-2.5 text-left text-fg hover:bg-subtle"
      >
        <span className="min-w-0 flex-1 text-body font-medium">{summary}</span>
        <Icon name="chevron-down" />
      </button>

      <Dialog
        open={open}
        onClose={() => setOpen(false)}
        title="대회 선택"
        width={560}
        handle
        closeButton={false}
        scrollArea
        className="backdrop:cursor-pointer"
      >
        <div className="flex min-h-0 flex-1 flex-col gap-4">
          <p className="text-small text-fg-secondary">
            한 개 또는 여러 개를 체크한 뒤 적용하세요. 적용 전에는 기존 조건을 유지합니다.
          </p>
          <Button fullWidth onClick={() => apply([])}>전체 대회 보기</Button>

          {/* Only the check list scrolls; the count and the buttons below stay in view. On a
              short screen the whole dialog scrolls instead (Dialog scrollArea, Codex N6). */}
          <div className="min-h-0 max-h-[340px] flex-1 overflow-y-auto overscroll-contain px-1 [@media(max-height:500px)]:max-h-none [@media(max-height:500px)]:overflow-visible">
            <div className="gap-6 lg:columns-2">
              {GROUPS.map((group) => {
              const items = offered.filter((c) => c.group === group);
              if (!items.length) return null;
              return (
                <fieldset key={group} className="mb-3 break-inside-avoid">
                  <legend className="mb-1 text-small text-fg-muted">{GROUP_TITLES[group]}</legend>
                  <ul className="flex flex-col gap-1">
                    {items.map((competition) => (
                      <li key={competition.id}>
                        <DraftOption
                          competition={competition}
                          checked={draft.includes(competition.id)}
                          noTeamMatch={unavailable?.has(competition.id) ?? false}
                          season={season}
                          onToggle={(on) =>
                            setDraft((ids) =>
                              on ? [...ids, competition.id] : ids.filter((id) => id !== competition.id),
                            )
                          }
                        />
                      </li>
                    ))}
                  </ul>
                </fieldset>
              );
              })}
            </div>
          </div>

          <div className="flex flex-col gap-3">
              <p role="status" className="text-small text-fg-secondary">
                {draft.length ? `${draft.length}개 선택` : "0개 선택 · 최소 1개를 선택하세요"}
              </p>
              {/* No header X (Figma 2026-11-09): cancel, Escape and the dim drop the draft only. */}
              <div className="grid grid-cols-2 gap-2">
                <Button onClick={() => setOpen(false)}>취소</Button>
                <Button
                  variant="primary"
                  disabled={draft.length === 0}
                  onClick={() => apply(competitions.filter((c) => draft.includes(c.id)).map((c) => c.id))}
                >
                  선택 적용
                </Button>
              </div>
          </div>
        </div>
      </Dialog>
    </>
  );
}

function DraftOption({
  competition,
  checked,
  noTeamMatch,
  season,
  onToggle,
}: {
  competition: CompetitionItem;
  checked: boolean;
  noTeamMatch: boolean;
  season?: number;
  onToggle: (checked: boolean) => void;
}) {
  const disabled = noTeamMatch && !checked;
  return (
    <label
      className={cx(
        "flex min-h-11 items-center gap-3 rounded-control px-2 py-1 text-body",
        disabled ? "cursor-not-allowed text-fg-muted" : "cursor-pointer text-fg",
        checked ? "bg-selected" : !disabled && "hover:bg-subtle",
      )}
    >
      <input
        type="checkbox"
        className="size-[18px] accent-action"
        checked={checked}
        disabled={disabled}
        onChange={(event) => onToggle(event.target.checked)}
      />
      <span className="min-w-0 flex-1">
        {pickerName(competition, season)}
        {noTeamMatch ? <span className="block text-small text-fg-muted">기간 내 팀 경기 없음</span>
          : <NoData competition={competition} season={season} />}
      </span>
    </label>
  );
}

/** The provider has no data for the season (CMP-004, V-16): "no data", never "no matches". */
function NoData({ competition, season }: { competition: CompetitionItem; season?: number }) {
  const info = seasonInfo(competition, season);
  if (!info || info.availability !== "no_data") return null;
  return (
    <span className="text-small text-fg-muted">
      {season === undefined ? "이번 시즌 데이터 없음" : "선택한 시즌 데이터 없음"}
    </span>
  );
}
