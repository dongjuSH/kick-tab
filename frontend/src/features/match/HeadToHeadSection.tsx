"use client";

import { useQuery } from "@tanstack/react-query";
import { RecentForm } from "@/components/common/RecentForm";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { DataState, StateMessage } from "@/components/ui/DataState";
import { Skeleton } from "@/components/ui/Skeleton";
import type { FormBlock, MatchInfo, PastMeeting } from "@/lib/api/types";
import { MISSING } from "@/lib/format/kst";
import { competitionName, teamName } from "@/lib/format/match";
import { formItems } from "./model";
import { headToHeadQuery } from "./queries";

const CARD = "flex min-w-0 flex-col gap-4 rounded-card border border-line bg-surface p-4 lg:p-6";

/** Score from this match's point of view: this match's home team first. */
function score(meeting: PastMeeting): string {
  const flip = !meeting.homeIsCurrentHome;
  const pair = (a: number | null, b: number | null) =>
    a === null || b === null ? null : flip ? `${b} : ${a}` : `${a} : ${b}`;
  const base = pair(meeting.scoreHome, meeting.scoreAway) ?? MISSING;
  const penalty = pair(meeting.penaltyHome, meeting.penaltyAway);
  return penalty ? `${base} (PK ${penalty.replaceAll(" ", "")})` : base;
}

function FormRow({ name, block, onRetry }: { name: string; block: FormBlock; onRetry: () => void }) {
  return (
    <div className="flex flex-col gap-2">
      <span className="text-body font-bold text-fg">{name}</span>
      {block.status === "available" && block.data ? (
        // MAT-005 rule 4: the shared recent-five row, oldest first like every other screen.
        <RecentForm matches={formItems(name, block.data)} teamName={name} />
      ) : (
        <span className="text-small text-fg-muted">
          {block.status === "unavailable" ? "최근 경기 정보를 불러오지 못했습니다." : "최근 공식 경기 기록이 없습니다."}
          {block.status === "unavailable" && <Button variant="secondary" onClick={onRetry}>다시 확인</Button>}
        </span>
      )}
    </div>
  );
}

function FormCard({ info, homeForm, awayForm, onRetry }: {
  info: MatchInfo;
  homeForm: FormBlock;
  awayForm: FormBlock;
  onRetry: () => void;
}) {
  return (
    <section className={CARD} aria-labelledby="form-title">
      <div className="flex flex-col gap-1">
        <h2 id="form-title" className="text-subtitle font-bold">최근 5경기 흐름</h2>
        <p className="text-small text-fg-secondary">공식 경기 기준</p>
      </div>
      <div className="flex flex-col gap-4">
        <FormRow name={teamName(info.match.home)} block={homeForm} onRetry={onRetry} />
        <FormRow name={teamName(info.match.away)} block={awayForm} onRetry={onRetry} />
      </div>
    </section>
  );
}

/**
 * Before kickoff only (MAT-005, Figma 63:1909 PC / 63:2116 mobile): last official meetings
 * (friendlies excluded, up to five, no links to past matches) with win/draw/loss chips below,
 * and both teams' last five official results — side by side on PC, stacked on mobile.
 * Fetched once and refreshed only after a new meeting.
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
    <div className="grid items-start gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,444px)] lg:gap-6">
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
            <Button variant="secondary" onClick={retry}>다시 확인</Button>
          </p>
        )}
        {list.length ? (
          <>
            {/* PC [날짜 110 | 대회 180 | 결과], mobile [날짜·대회 94 | 결과] (Figma 63:1909 / 63:2116).
                This match's home team is always left, with the score turned to match. */}
            <table className="w-full table-fixed text-left text-label text-fg">
              <caption className="sr-only">{`최근 공식 맞대결, 스코어는 ${home} 기준`}</caption>
              <thead className="bg-subtle text-small font-medium text-fg-muted">
                <tr>
                  <th scope="col" className="w-[94px] p-2.5 font-medium lg:w-[110px]">날짜</th>
                  <th scope="col" className="hidden w-[180px] p-2.5 font-medium lg:table-cell">대회</th>
                  <th scope="col" className="p-2.5 text-center font-medium">결과</th>
                </tr>
              </thead>
              <tbody>
                {list.map((meeting, index) => {
                  const competition = competitionName({
                    nameKo: meeting.competition,
                    shortName: meeting.competition,
                  });
                  return (
                    <tr key={index} className="border-line not-last:border-b">
                      <td className="h-14 px-2.5 py-1 align-middle">
                        <span className="block whitespace-nowrap">
                          {meeting.kickoffDateKst.replaceAll("-", ".")}
                        </span>
                        <span className="block break-keep [overflow-wrap:anywhere] lg:hidden">{competition}</span>
                      </td>
                      <td className="hidden h-14 px-2.5 py-1 align-middle break-keep lg:table-cell">{competition}</td>
                      <td className="h-14 px-2.5 py-1 text-center align-middle font-bold break-keep text-action [overflow-wrap:anywhere]">
                        {`${home} ${score(meeting)} ${away}`}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            {meetings.summary && (
              <ul className="flex flex-wrap gap-x-2 gap-y-1.5" aria-label="맞대결 요약">
                <li><Badge>{`${home} ${meetings.summary.homeWins}승`}</Badge></li>
                <li><Badge>{`${meetings.summary.draws}무`}</Badge></li>
                <li><Badge>{`${away} ${meetings.summary.awayWins}승`}</Badge></li>
              </ul>
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
      <FormCard info={info} homeForm={homeForm} awayForm={awayForm} onRetry={retry} />
    </div>
  );
}
