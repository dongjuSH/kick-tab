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
};
const GROUPS = Object.keys(GROUP_TITLES) as CompetitionGroup[];

/** "전체 대회", "FA컵", "FA컵 외 1개" (first selected in list order + the rest). */
function competitionSummary(competitions: readonly CompetitionItem[], selected: readonly number[]) {
  const chosen = competitions.filter((c) => selected.includes(c.id));
  if (chosen.length === 0) return "전체 대회";
  const first = competitionName(chosen[0]);
  return chosen.length === 1 ? first : `${first} 외 ${chosen.length - 1}개`;
}

/**
 * Competition filter (SCH-004, CMP-002, schedule UX policy 2026-11-02; Figma 187:564
 * trigger, 187:1946 picker). One button opens the list: a competition name applies only
 * that competition at once. "여러 대회 선택" is the secondary mode: checks are a draft
 * that starts from the current explicit selection, needs at least one, and changes nothing
 * until "선택 적용". "전체 대회 보기" clears the condition. Cancel, Escape and outside
 * clicks keep the current condition. Desktop dialog, mobile bottom sheet.
 */
export function CompetitionFilter({
  competitions,
  selected,
  onChange,
}: {
  competitions: readonly CompetitionItem[];
  selected: readonly number[];
  onChange: (ids: number[]) => void;
}) {
  const [open, setOpen] = useState(false);
  const [multi, setMulti] = useState(false);
  const [draft, setDraft] = useState<number[]>([]);

  const openPicker = () => {
    setMulti(false);
    setOpen(true);
  };
  const startMulti = () => {
    setDraft(competitions.filter((c) => selected.includes(c.id)).map((c) => c.id));
    setMulti(true);
  };
  const apply = (ids: number[]) => {
    onChange(ids);
    setOpen(false);
  };
  const summary = competitionSummary(competitions, selected);

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
        title={multi ? "여러 대회 선택" : "대회 선택"}
        width={560}
        handle
      >
        <div className="flex flex-col gap-4">
          <p className="text-small text-fg-secondary">
            {multi
              ? "체크는 초안입니다. 선택 적용 전에는 기존 조건을 유지합니다."
              : "대회 이름을 누르면 해당 대회만 바로 표시합니다."}
          </p>
          <div className="grid grid-cols-2 gap-2">
            <Button onClick={() => apply([])}>전체 대회 보기</Button>
            <Button variant="ghost" onClick={multi ? () => setMulti(false) : startMulti}>
              {multi ? "한 대회 바로 선택" : "여러 대회 선택"}
            </Button>
          </div>

          <div className="gap-6 lg:columns-2">
            {GROUPS.map((group) => {
              const items = competitions.filter((c) => c.group === group);
              if (!items.length) return null;
              return (
                <fieldset key={group} className="mb-3 break-inside-avoid">
                  <legend className="mb-1 text-small text-fg-muted">{GROUP_TITLES[group]}</legend>
                  <ul className="flex flex-col gap-1">
                    {items.map((competition) => (
                      <li key={competition.id}>
                        {multi ? (
                          <DraftOption
                            competition={competition}
                            checked={draft.includes(competition.id)}
                            onToggle={(on) =>
                              setDraft((ids) =>
                                on ? [...ids, competition.id] : ids.filter((id) => id !== competition.id),
                              )
                            }
                          />
                        ) : (
                          <button
                            type="button"
                            aria-pressed={selected.length === 1 && selected[0] === competition.id}
                            onClick={() => apply([competition.id])}
                            className={cx(
                              "flex min-h-11 w-full items-center gap-2 rounded-control px-2 text-left text-body",
                              selected.length === 1 && selected[0] === competition.id
                                ? "bg-selected font-medium text-action"
                                : "text-fg hover:bg-subtle",
                            )}
                          >
                            <span className="flex-1">{competitionName(competition)}</span>
                            <NoData competition={competition} />
                          </button>
                        )}
                      </li>
                    ))}
                  </ul>
                </fieldset>
              );
            })}
          </div>

          {multi && (
            <div className="flex flex-col gap-3">
              <p role="status" className="text-small text-fg-secondary">
                {draft.length ? `${draft.length}개 선택` : "0개 선택 · 최소 1개를 선택하세요"}
              </p>
              <div className="flex gap-2">
                <Button onClick={() => setOpen(false)}>취소</Button>
                <Button
                  variant="primary"
                  className="flex-1"
                  disabled={draft.length === 0}
                  onClick={() => apply(competitions.filter((c) => draft.includes(c.id)).map((c) => c.id))}
                >
                  선택 적용
                </Button>
              </div>
            </div>
          )}
        </div>
      </Dialog>
    </>
  );
}

function DraftOption({
  competition,
  checked,
  onToggle,
}: {
  competition: CompetitionItem;
  checked: boolean;
  onToggle: (checked: boolean) => void;
}) {
  return (
    <label
      className={cx(
        "flex min-h-11 cursor-pointer items-center gap-3 rounded-control px-2 text-body text-fg",
        checked ? "bg-selected" : "hover:bg-subtle",
      )}
    >
      <input
        type="checkbox"
        className="size-[18px] accent-action"
        checked={checked}
        onChange={(event) => onToggle(event.target.checked)}
      />
      <span className="flex-1">{competitionName(competition)}</span>
      <NoData competition={competition} />
    </label>
  );
}

function NoData({ competition }: { competition: CompetitionItem }) {
  return competition.currentSeason?.availability === "no_data" ? (
    <span className="text-small text-fg-muted">이번 시즌 데이터 없음</span>
  ) : null;
}
