import { Badge, type BadgeSize, type BadgeTone } from "@/components/ui/Badge";
import type { MatchSummary } from "@/lib/api/types";
import { isChanged, statusWord } from "@/lib/format/match";

function tone(match: MatchSummary): BadgeTone {
  if (match.status === "live") return "live";
  if (isChanged(match)) return "warning";
  return "neutral"; // scheduled, finished, unknown ("확인 필요")
}

/** "진행 중 63′" while live (Figma 187:591, TOP 5 row); no minute when not provided. */
function statusLabel(match: MatchSummary): string {
  const word = statusWord(match);
  return match.status === "live" && match.elapsed !== null ? `${word} ${match.elapsed}′` : word;
}

/**
 * Match status badge (Figma 187:591 schedule row): 진행 중 green; 연기·취소·경기 중단·
 * 행정 종료 amber; 예정·종료·확인 필요 grey. Used by match cards and TOP 5.
 */
export function MatchStatusBadge({
  match,
  size = "small",
  awaiting = false,
}: {
  match: MatchSummary;
  size?: BadgeSize;
  /** Kickoff passed without a provider start (`awaitingStatus`): "상태 확인 중", grey. */
  awaiting?: boolean;
}) {
  return (
    <Badge tone={tone(match)} size={size}>
      {awaiting ? "상태 확인 중" : statusLabel(match)}
    </Badge>
  );
}
