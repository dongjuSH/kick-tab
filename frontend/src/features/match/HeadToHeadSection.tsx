"use client";

import { useQuery } from "@tanstack/react-query";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { DataState, StateMessage } from "@/components/ui/DataState";
import { Skeleton } from "@/components/ui/Skeleton";
import type { FormBlock, MatchInfo, PastMeeting } from "@/lib/api/types";
import { MISSING, formatShortDate } from "@/lib/format/kst";
import { competitionName, teamName } from "@/lib/format/match";
import { RESULT_LABEL } from "./model";
import { headToHeadQuery } from "./queries";

const CARD = "flex flex-col gap-4 rounded-card border border-line bg-surface p-4 lg:p-6";

function score(meeting: PastMeeting): string {
  const base =
    meeting.scoreHome === null || meeting.scoreAway === null
      ? MISSING
      : `${meeting.scoreHome} : ${meeting.scoreAway}`;
  return meeting.penaltyHome === null || meeting.penaltyAway === null
    ? base
    : `${base} (PK ${meeting.penaltyHome}:${meeting.penaltyAway})`;
}

function FormRow({ name, block, onRetry }: { name: string; block: FormBlock; onRetry: () => void }) {
  return (
    <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-4">
      <span className="text-body font-bold text-fg sm:w-40 sm:shrink-0">{name}</span>
      {block.status === "available" && block.data ? (
        <ol className="flex flex-wrap gap-1" aria-label={`${name} 최근 경기 결과, 최신순`}>
          {block.data.map((match, index) => {
            const result = RESULT_LABEL[match.result];
            const goals =
              match.goalsFor === null || match.goalsAgainst === null
                ? MISSING
                : `${match.goalsFor}:${match.goalsAgainst}`;
            const detail = `${formatShortDate(match.kickoffDateKst)} ${competitionName({ nameKo: match.competition, shortName: match.competition })} ${match.venue === "home" ? "홈" : "원정"} vs ${match.opponentName} ${goals}`;
            return (
              <li key={index} title={detail}>
                <Badge tone={result.tone}>
                  {result.label}
                  <span className="sr-only"> ({detail})</span>
                </Badge>
              </li>
            );
          })}
        </ol>
      ) : (
        <span className="text-small text-fg-muted">
          {block.status === "unavailable" ? "최근 경기 정보를 불러오지 못했습니다." : "최근 공식 경기 기록이 없습니다."}
          {block.status === "unavailable" && <Button variant="ghost" onClick={onRetry}>다시 확인</Button>}
        </span>
      )}
    </div>
  );
}

/**
 * Before kickoff only (MAT-005, Figma 63:1909): last official meetings (friendlies excluded,
 * up to five, no links to past matches) with a win/draw/loss summary, then both teams'
 * last five official results. Fetched once and refreshed only after a new meeting.
 */
export function HeadToHeadSection({ info }: { info: MatchInfo }) {
  const query = useQuery(headToHeadQuery(info.match.id));
  const home = teamName(info.match.home);
  const away = teamName(info.match.away);

  if (!query.data) {
    return (
      <section className={CARD}>
        <h2 className="text-subtitle font-bold">상대 전적</h2>
        <DataState
          status={query.isPending ? "loading" : "error"}
          error={query.error}
          onRetry={() => void query.refetch()}
          errorTitle="상대 전적을 불러오지 못했습니다"
          loadingFallback={<Skeleton className="h-40 w-full" />}
        />
      </section>
    );
  }
  const { meetings, homeForm, awayForm } = query.data.data;
  const list = meetings.status === "available" ? (meetings.data ?? []) : [];
  const retry = () => void query.refetch();

  return (
    <>
      <section className={CARD} aria-labelledby="h2h-title">
        <div className="flex flex-col gap-1">
          <h2 id="h2h-title" className="text-subtitle font-bold">상대 전적</h2>
          <p className="text-small text-fg-secondary">
            {`친선 제외 · 최근 공식 맞대결 ${list.length}경기`}
          </p>
        </div>
        {query.isError && (
          <p role="alert" className="text-small text-warning">
            최신 상대 전적으로 갱신하지 못했습니다. 마지막으로 확인한 정보를 보여줍니다.
            <Button variant="ghost" onClick={retry}>다시 확인</Button>
          </p>
        )}
        {list.length ? (
          <>
            {meetings.summary && (
              <p className="text-body font-medium text-fg">
                {`${home} ${meetings.summary.homeWins}승 · 무승부 ${meetings.summary.draws} · ${away} ${meetings.summary.awayWins}승`}
              </p>
            )}
            <div className="overflow-x-auto">
              <table className="w-full min-w-[520px] text-left text-body">
                <thead className="bg-subtle text-small text-fg-muted">
                  <tr>
                    <th scope="col" className="px-4 py-2 font-normal">날짜</th>
                    <th scope="col" className="px-4 py-2 font-normal">대회</th>
                    <th scope="col" className="px-4 py-2 font-normal">홈 · 원정</th>
                    <th scope="col" className="px-4 py-2 text-right font-normal">결과</th>
                  </tr>
                </thead>
                <tbody>
                  {list.map((meeting, index) => (
                    <tr key={index} className="border-b border-line">
                      <td className="px-4 py-3 whitespace-nowrap">{meeting.kickoffDateKst.replaceAll("-", ".")}</td>
                      <td className="px-4 py-3">
                        {competitionName({ nameKo: meeting.competition, shortName: meeting.competition })}
                      </td>
                      <td className="px-4 py-3">{`${meeting.homeName} vs ${meeting.awayName}`}</td>
                      <td className="px-4 py-3 text-right font-bold whitespace-nowrap text-action">{score(meeting)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {list.length < 5 && (
              <p className="text-small text-fg-muted">범위를 넓혀 확인한 공식 맞대결만 표시합니다.</p>
            )}
          </>
        ) : meetings.status === "unavailable" ? (
          <StateMessage
            tone="error"
            title="상대 전적을 불러오지 못했습니다"
            description="잠시 후 다시 확인해 주세요."
            action={<Button onClick={retry}>다시 확인</Button>}
          />
        ) : (
          <StateMessage title="맞대결 기록이 없습니다" description="두 팀의 최근 공식 맞대결이 없습니다." />
        )}
      </section>
      <section className={CARD} aria-labelledby="form-title">
        <div className="flex flex-col gap-1">
          <h2 id="form-title" className="text-subtitle font-bold">최근 5경기 흐름</h2>
          <p className="text-small text-fg-secondary">친선 경기를 제외한 공식 경기 · 왼쪽이 최근</p>
        </div>
        <FormRow name={home} block={homeForm} onRetry={retry} />
        <FormRow name={away} block={awayForm} onRetry={retry} />
      </section>
    </>
  );
}
