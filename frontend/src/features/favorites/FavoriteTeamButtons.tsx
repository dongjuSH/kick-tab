import type { TeamRef } from "@/lib/api/types";
import { teamName } from "@/lib/format/match";

/**
 * Favourite-team shortcuts under a team search (Figma 49:57 schedule, 61:883 past results):
 * "★ 관심 팀" then the team names as blue text buttons (44px targets). Pressing a team picks
 * it; pressing the picked team again clears it. The look is the same selected or not (Figma
 * 225:1768) — the filtered list shows the choice; `aria-pressed` carries it for assistive tech.
 */
export function FavoriteTeamButtons({
  teams,
  activeId,
  onSelect,
  label,
}: {
  teams: readonly TeamRef[];
  activeId: number | null;
  onSelect: (team: TeamRef | null) => void;
  /** Accessible name of the group, e.g. "관심 팀 일정". */
  label: string;
}) {
  if (teams.length === 0) return null;
  return (
    <div className="flex items-center gap-2 overflow-x-auto [scrollbar-width:none]" role="group" aria-label={label}>
      <span className="flex shrink-0 items-center gap-1 text-small text-fg-secondary">
        <span aria-hidden className="text-action">★</span>관심 팀
      </span>
      {teams.map((team) => {
        const active = activeId === team.id;
        return (
          <button
            key={team.id}
            type="button"
            aria-pressed={active}
            className="inline-flex min-h-11 shrink-0 items-center rounded-control px-1.5 text-small text-action hover:underline"
            onClick={() => onSelect(active ? null : team)}
          >
            {teamName(team)}
          </button>
        );
      })}
    </div>
  );
}
