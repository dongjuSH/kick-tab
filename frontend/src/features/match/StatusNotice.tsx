import type { MatchInfo } from "@/lib/api/types";
import { isRuling } from "./model";

function Box({ title, lines }: { title: string; lines: (string | null)[] }) {
  return (
    <section
      role="status"
      className="flex flex-col gap-2 rounded-card bg-warning-bg p-4 text-warning lg:p-6"
    >
      <h2 className="text-lead font-bold">{title}</h2>
      {lines.filter(Boolean).map((line, index) => (
        <p
          key={line}
          className={index === 0 ? "text-label font-medium text-warning" : "text-body text-fg-secondary"}
        >
          {line}
        </p>
      ))}
    </section>
  );
}

/**
 * State notices of the match page (MAT-001 table, LIVE-001·002, Figma 57:205 state set and
 * 110:3139 ruling). A provider reason is shown only when one is supplied (never invented).
 */
export function StatusNotice({ info }: { info: MatchInfo }) {
  const { match } = info;
  const reason = match.statusReason ? `제공사 사유: ${match.statusReason}` : null;
  if (isRuling(info)) {
    const provider = `제공사 사유: ${info.statusLong ?? "행정 결과로 종료"}(${info.statusCode})`;
    const noScore = match.score.home === null || match.score.away === null;
    return (
      <Box
        title="행정 결과로 종료된 경기입니다."
        lines={[
          noScore ? `${provider} · 스코어 미제공` : provider,
          noScore
            ? "스코어가 제공되지 않아 —로 표시합니다."
            : "제공사가 기록한 스코어를 그대로 표시합니다.",
          "행정 종료된 경기에는 평점과 후기를 남길 수 없습니다. 주간 AI 선정 후 상태가 바뀐 경우 목록과 순서는 유지됩니다.",
        ]}
      />
    );
  }
  switch (match.status) {
    case "postponed":
      return (
        <Box
          title="연기된 경기입니다."
          lines={[reason, "변경 일시가 제공되면 같은 경기에서 안내합니다."]}
        />
      );
    case "cancelled":
      return (
        <Box
          title="취소된 경기입니다."
          lines={[reason ?? "제공사가 취소 사유를 제공하지 않았습니다.", "취소된 경기에는 평점과 후기를 남길 수 없습니다."]}
        />
      );
    case "abandoned":
      return (
        <Box
          title="경기가 중단되었습니다."
          lines={[
            reason,
            "중단 시점 스코어입니다. 제공된 타임라인만 표시하고 평가는 제공하지 않습니다.",
            "재개·결과 확정·재경기가 제공되면 같은 경기에서 전환됩니다.",
          ]}
        />
      );
    case "unknown":
      return (
        <Box
          title="경기 상태를 확인하고 있습니다."
          lines={["결과를 임의로 확정하지 않습니다. 확인되면 같은 경기에서 안내합니다."]}
        />
      );
    default:
      return null;
  }
}
