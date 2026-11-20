# KickTab 파일별 구현 기능

**2026-11-20 · 04 경기 상세 비회원 전체 검수 개선(Codex 교차 검증 통과·`dev` 병합):** 백엔드 `services/top5_selection.py`(`PROMPT_VERSION` `2026-11-19.1`·`domesticPriority`·`formSummary`·금지 표현, `window_end()` 월 00:20 KST, `gemini_generate` `gemini-3.8-flash` 단일·요청 최대 5회·요청당 600초·남은 180초 확인, `_fail`·`_publish_due_delay` 00:20 보류 지연(수동 복구 성공 시에만 취소), `_wait_showing_held_delay`·`_show_held_delay`(실행 중 00:20 전환), `_recovery_weeks`·`_missed_week`(00:21:00) — 하위 모델 대체·`AllModelsFailed`·`retry_due` 삭제), `providers/gemini.py`(`LlmError.transient`·`thinking_level`), `config.py`(`top5_llm_thinking_level`, 시도 1200초, `top5_llm_fallback_model` 삭제), `notifications/discord.py`(지연 알림 한 종류, `kind`·`next_retry_at` 삭제), `sync/top5.py`(`top5_retry` 삭제), `services/top_matches.py`(주석), 테스트 `test_top5.py`·`test_top5_db.py`·`test_review_regressions.py`. 프런트 `features/match/MatchRecords.tsx`(양쪽 타임라인 `TIMELINE_GRID`)·`model.ts`(`eventText(event)`)·`ReviewLoginNotice.tsx`(새, Figma `408:16478` 비회원 안내, 동작은 02)·`ReviewSection.tsx`, `tests/match-regressions.test.mjs`. 아래 표의 `top5_selection.py`·`config.py`·`discord.py` 행 중 하위 모델·00:05 재시도·240초 내용은 이 변경이 우선한다.

**2026-11-19 · 03 경기 일정 비회원 전체 검수 개선(Codex 교차 검증 통과·`dev` 병합):** 백엔드 `migrations/versions/20261119_0017_competition_groups.py`(새 — `FIFA` 그룹, downgrade는 FIFA 저장 경기가 있으면 중단)·`seed/competitions.py`(21개 대회, 새 7개 `name_ko`)·`models/reference.py`·`sync/reference.py`·`services/fixtures.py`(공통 경기일 기간 `schedule_period`, `overlaps(..., stored)`·`stored_seasons`, `covered`, `sync_state(window)`의 `relevant_competition_ids`·`all_failed`, `fixture_availability`)·`sync/fixtures.py`·`api/routes/schedule.py`(`/fixtures/availability`, 503 조건)·`schemas/schedule.py`, 테스트 3개. 프런트 `features/schedule/`(`ScheduleSection`·`DateBar`·`queries.ts`·`useScheduleParams.ts`), `components/common/CompetitionFilter.tsx`·`NewsCard.tsx`, `components/ui/Dialog.tsx`(`scrollArea`), `components/layout/StickyPanel.tsx`, `app/page.tsx`(1280px 두 열/미만 단일 열), `lib/format/kst.ts`·`match.ts`, `lib/api`(쿼리 키·생성 타입), `tests/match-regressions.test.mjs`.

**2026-11-19 · 01 비회원 전체 검수 개선(Codex 교차 검증 통과·`dev` 병합):** 프런트 `SiteHeader.tsx`(내비 위아래 여백 PC 11px·모바일 10px — 헤더+띠 118/130px)·`HeaderHeight.tsx`(주석)·`globals.css`(`--kt-header-height` 130px, 1024px 이상 118px)·`top5/Top5Strip.tsx`(띠 48/64px, 순환 28px/s, PC 패널 비모달 — `inertOutside`·Tab 순환·`FOCUSABLE` 삭제, `aria-modal` 제거, 문서 click 캡처로 링크 이동 시 닫힘)·`top5/Top5List.tsx`(행에 `MatchTeams`·`MatchStatus`, PC 팀 영역 420px, 모바일 시트 높이 420px 미만 본문 스크롤 `SHEET_BODY`·`SHEET_LIST`, 일반 클릭만 닫힘)·`top5/model.ts`(`changeText`에서 사유 제거, `isPlainClick`)·`components/common/MatchCard.tsx`(`useMatchScore`·`MatchStatus`·`MatchTeams` 분리, 긴 한 단어 팀명 `overflow-wrap:anywhere`)·`lib/format/match.ts`(`statusNotes`)·`tests/top5.test.mjs`(+2: 수정 키 판정, 중단 문구·변경 일시 사유 중복 없음).

**2026-11-18 · 08 팀 상세 수정 반영(Codex 교차 검증 통과·`dev` 병합):** 백엔드 `migrations/versions/20261118_0016_team_player_stats.py`(새), `seed/countries.json`(새), `models/team_detail.py`(`TeamPlayerStat`)·`models/__init__.py`, `services/team_detail.py`(선수 기록 파싱·저장, `recent_results`, `merge_transfers`, 표시 기준 B, `flag_url`), `sync/team_detail.py`(`team_player_stats`), `schemas/team_detail.py`, `api/routes/teams.py`, `services/news.py`(팀 24개), 테스트 2개. 프런트 `features/team-detail/`(`TeamDetail`·`SquadTable`·`SeasonRecords`·`TeamNews`·`TeamMatches`·`model.ts`), `components/ui/Tabs.tsx`·`DataState.tsx`, 생성 타입, `tests/team-detail.test.mjs`.

**2026-11-18 · 07 팀 탐색 개선(Codex 교차 검증 통과·`dev` 병합):** 백엔드 `services/team_browse.py`(`team_id` — 고른 팀 하나만)·`api/routes/teams.py`(`team` 1~2,147,483,647, 아니면 422). 프런트 `app/teams/page.tsx`(보이는 제목·소개 제거, sr-only H1), `features/teams/TeamsSection.tsx`(공통 `TeamSearch`·06 `ChipRow` 재사용, 5팀일 때만 제한 안내, Figma 57:766·57:836 상태 문구, 이전 0.3초 자동 반영 `SearchField` 삭제)·`useTeamsParams.ts`(`team`, `urlKey`·replace 삭제)·`queries.ts`, `components/common/TeamSearch.tsx`(`label`·`defaultText`·`onSubmitText`), `lib/api`(쿼리 키·생성 타입). 아래 표는 이 변경을 반영했다.

**2026-11-17 · 06 리그 순위 개선(Codex 최종 교차 검증 통과·`dev` 병합):** 백엔드 `services/standings.py`(UEFA 3개 대회 리그 페이즈 순위 수집·36팀 단일 그룹 검사·대진 기준 `table_complete`·`recent_matches`, `relegation_zone` 삭제), `services/knockouts.py`(새: 토너먼트 대진), `api/routes/standings.py`(`/standings` UEFA·`recent`·`complete`, `GET /knockouts`), `schemas/standings.py`, `sync/standings.py`(대상 범위), `services/fixtures.py`·`services/match_detail.py`·`sync/fixtures.py`(같은 팀 양쪽 경기 응답 거부, 받아들인 경기만 상세 기록 저장 — Codex 보완). 프런트 `features/standings/`(`StandingsSection`·`StandingsTable`·`PlayerRankings`·`model`·`queries`·`useStandingsParams` 수정, `ChipRow`·`RecentForm`·`LeaguePhaseTable`·`KnockoutStage` 새), `app/standings/page.tsx`, `lib/api/schema.d.ts`·`types.ts`·`query-keys.ts`. 테스트 `test_standings.py`·`test_standings_db.py`·`test_schedule_db.py`·`standings.test.mjs`. 마이그레이션 없음.

**2026-11-16 · 05 지난 경기 개선(Codex 교차 검증 통과·`dev` 병합):** 프런트 `app/results/page.tsx`(보이는 제목·소개 문구 제거, sr-only H1), `components/common/SeasonSelect.tsx`(트리거·옵션 '2025-26 시즌' 공통 표기 — 리그 순위 함께), `components/common/TeamSearch.tsx`(`placeholder` 옵션 삭제, 자리표시자 공통), `features/results/ResultsSection.tsx`(메인과 같은 검색 묶음·선택 시즌 보조 문구, 시즌 버튼 모바일 175px·초기화 76px), `features/favorites/FavoriteTeamButtons.tsx`(새: '★ 관심 팀' 버튼 줄, 메인·지난 경기 공통), `features/schedule/ScheduleSection.tsx`(관심 팀 버튼 줄을 공통 컴포넌트로 교체 — 출력 동일), `tests/results.test.mjs`(시즌 옵션 표기·관심 팀 버튼 테스트).

**2026-11-11 · 04 경기 상세 개선(Codex 교차 검증 통과·`dev` 병합):** 백엔드 `migrations/versions/20261111_0015_text_reviews.py`(새: `reviews.rating` 삭제·body 필수·Python 공백 기준 공백 금지), `models/review.py`(`REVIEW_BODY_SPACE_CLASS`), `services/reviews.py`(`review_open` — 진행 중(SUSP 제외)·일반 종료, 건수만), `schemas/match_detail.py`(`ReviewItem.rating`·`ReviewSummary.average` 삭제), `services/match_detail.py`(킥오프 전 조회 삭제, `_name()` HTML 엔티티 해제), `api/routes/matches.py`, 테스트 `test_review_window.py`(새)·`test_match_detail.py`·`test_review_regressions.py`·`test_top5_db.py`. 프런트 `features/match/icons.tsx`(새: 타임라인·엄지·주의사항 벡터 아이콘), `Scoreboard`(로고+팀명 한 링크), `MatchRecords`(기록 헤더·아이콘 타임라인·선수 평점 팀별 카드·경기 정보 갱신 연동 재조회), `HeadToHeadSection`(좌우 배치·최근 5경기 미리보기), `ReviewSection`·`ReviewGuidance`('경기 평가', 건수), `MatchDetail`(종료 384px·진행 중 640px 배치), `model.ts`(`eventKind`·`formPreview`·`areasOf`), `queries.ts`(기록 자체 타이머 삭제), `StatusNotice` 문구, 삭제 `public/icons/thumbs.svg`·`Icon`의 thumbs, `tests/match-regressions.test.mjs`. 선수명은 제공사 영문 유지(사용자 결정).

**2026-11-10 · 03 비회원 개선(Codex 교차 검증 3차 통과·`dev` 병합):** 백엔드 `services/fixtures.py`(`SyncState`에 `checked_at`·`checked_through`·`delayed`, `SYNC_DELAY` 75분)·`schemas/schedule.py`(`ScheduleMeta`에 `checkedAt`·`checkedThrough`·`delayed`)·`api/routes/schedule.py`(`_schedule_meta()`), `seed/team_aliases.json`(하위 리그 프로 구단 92팀 한국어 이름, 검색 전용). 프런트 `app/page.tsx`(sr-only H1, 두 구간 그리드, `StickyPanel`), `components/layout/StickyPanel.tsx`(새), `ui/chip.tsx`(`chip.ts`에서 이름 변경, `ChipLabel` 추가), `ui/Dialog.tsx`(`closeButton`·`scrollArea`), `common/MatchCard.tsx`(별표·카드 아래 링크·상태 확인 중 '—'·164px 상태 열), `common/MatchStatusBadge.tsx`(`awaiting`), `common/TeamSearch.tsx`(48px 입력·SVG 돋보기·30px X·`candidates`), `common/CompetitionFilter.tsx`(X 없는 하단 버튼·딤 포인터·목록만 스크롤), `features/schedule/`(`ScheduleSection` 지연 안내·간격·관심 팀 버튼·`pendingReset`, `DateBar` 52px·1/5 폭·짧은 상태·위치 복원, `useScheduleParams` `withTeam`·`withoutTeam`·`nearestMatchDate`), `features/favorites/`(`FavoriteSchedule` Guest Favorites 다섯 상태, `FavoriteStar`(새), `FavoriteToggle` `FAVORITE_REFUSALS`), `features/standings/`(`MainStandings` 경기·승무패·승점·끌기/휠 이동, 'Bundesliga'), `lib/hooks/useNow.ts`(새), `lib/format/match.ts`(`awaitingStatus`), 칩 사용처 `MainNews`·`ResultsSection`·`TeamsSection`. 테스트 `match-regressions.test.mjs`(+4)·`standings.test.mjs`, 백엔드 `test_schedule_rules.py`·`test_schedule_sources.py`.

**2026-11-10 · 01 변경(비회원 개선, Codex 교차 검증 통과·`dev` 병합):** 프런트 `Logo.tsx`·`SiteHeader.tsx`·`HeaderHeight.tsx`(새)·`SiteFooter.tsx`·`layout.tsx`·`FeedbackButton.tsx`·`ui/Dialog.tsx`·`features/top5/`(`Top5Strip`·`Top5List`·`model`)·`globals.css`·`lib/format/kst.ts`·`tests/top5.test.mjs`(새), 삭제 `MobileBottomBar.tsx`·`public/brand/logo-footer.svg`·`logo-mobile.svg`. 백엔드 `services/top5_selection.py`(실행 누락 주 지연 처리)·`tests/test_top5_db.py`.

**2026-11-07 · 08 변경(팀 상세, Codex 교차 검증 통과·`dev` 병합):** 백엔드 `migrations/versions/20261107_0012_team_detail.py`·`0013_transfer_counterpart_key.py`·`0014_transfer_identity_indexes.py`, `models/team_detail.py`(+`models/reference.py` 경기장·`models/standings.py` 프로필 확인 시각), `services/team_detail.py`(파싱·완전성 검증·저장·수집 일정·접근 판정·조회), `sync/team_detail.py`(`team_details`·`transfers`), `api/routes/teams.py`(팀 상세 5개 경로)·`schemas/team_detail.py`, `api/routes/schedule.py`·`services/news.py`(`GET /news?team=`), `services/reference.py`(`upsert_teams` 경기장·`team_detail_lookup` 수집된 리그 소속만), `sync/reference.py`. 프런트 `app/teams/[id]/page.tsx`, `features/team-detail/`, `lib/api`(타입·쿼리 키·생성 타입). 시작 전 처리로 `tests/test_schedule_db.py` 날짜 가정 수정. 아래 표는 이 변경을 반영했다.

**2026-11-06 · 07 변경(팀 탐색, Codex 교차 검증 3차 통과·`dev` 병합):** 백엔드 `api/routes/teams.py`(`GET /teams`)·`schemas/teams.py`·`services/team_browse.py`(현재 시즌 5대 리그 소속·리그·검색·12개씩·소속 미확인 503), `services/team_search.py`(`match_teams()` 분리), `api/router.py`. 프런트 `app/teams/page.tsx`, `features/teams/`, `FavoriteToggle`(5개 꽉 참·거부 문구 목록 기준)·`favorites/store.ts`(`latest()`), `DataState`(`emptyAction`), `lib/api`(타입·쿼리 키·`MEMBERSHIP_UNKNOWN`). 마이그레이션 없음. 아래 표는 이 변경을 반영했다.

**2026-11-06 · 06 변경(리그 순위, Codex 교차 검증 3차 통과·`dev` 병합):** 백엔드 `migrations/versions/20261106_0011_standings.py`, `models/standings.py`, `services/standings.py`(파싱·완전성 검증·교체 저장·수집 주기·선방 집계), `sync/standings.py`(`standings`·`player_rankings`·`player_stats`), `api/routes/standings.py`·`schemas/standings.py`(`GET /standings`·`/standings/summary`·`/player-rankings`). 프런트 `app/standings/page.tsx`, `features/standings/`, `app/page.tsx`(메인 오른쪽 열 간소 순위), 공통 `Tabs`(선택 없음·스크롤 막대 숨김)·`DataState`(`partialAction`). 아래 표는 이 변경을 반영했다.

**2026-11-05 · 05 변경(지난 경기, Codex 교차 검증 통과·`dev` 병합):** 백엔드 `migrations/versions/20261105_0010_season_fixtures.py`, `services/results.py`·`api/routes/results.py`(`GET /results`), `api/routes/schedule.py`(`GET /seasons`·`/competitions` `seasons`·`/teams/search?season=`), `sync/fixtures.py`(`fixtures_season`, 일부 저장·저장 오류 실패 기록), `services/fixtures.py`(이름 없는 신규 팀 경기 제외), `sync/reference.py`(관리 시즌·가용성 유지), `seed/team_aliases.json`(강등 15팀). 프런트 `app/results/page.tsx`, `features/results/`, `components/common/SeasonSelect.tsx`, `components/ui/Pagination.tsx`, `lib/hooks/useHydrated.ts`, `CompetitionFilter`·`TeamSearch` 시즌 옵션, `ScheduleSection` 하이드레이션 대기. 아래 표는 이 변경을 반영했다.

**2026-11-04 · 04 변경:** `frontend/src/features/match/ReviewGuidance.tsx` 후기 안내 팝오버(PC 호버·클릭, 모바일 탭, 키보드), `ReviewSection.tsx` 제목과 연결, `backend/app/services/top5_selection.py` 국내 시청 관심·대회 단계와 경쟁 맥락을 우선하는 프롬프트 `2026-11-04.1`.

**2026-11-04 · 03 변경:** `migrations/versions/20261104_0009_fixture_coverage.py`·`models/reference.py` 수집 범위 저장, `services/fixtures.py`·`routes/schedule.py` 날짜별 가용성·21일 조회, `seed/uefa_team_names.json`·`services/reference.py` UEFA 한국어 이름·별칭. `services/news.py` 최근 48개·수집 상태, `services/news_classify.py`·`sync/news.py` 주제 판별과 실패 시 목록 유지, `sync/scheduler.py` 뉴스 단독 예약. `DateBar`·`ScheduleSection` 일정 UI, `CompetitionFilter` 대회 체크 초안, `TeamSearch` 통합 X, `MainNews` 갱신·개수 표시. 아래 2026-11-03 기준 표와 충돌하는 부분은 이 변경을 우선한다.

**2026-11-04 · 01 변경:** `frontend/public/brand/logo-{header,mobile,footer}.svg` 승인 로고, `frontend/src/app/favicon.ico` 승인 파비콘(이전 `icon.svg` 제거), `Logo.tsx` 사용처 연결, `MainNav.tsx` 상태별 글자 위치·밑줄, `Top5Strip.tsx`·`model.ts`·`globals.css` 요약 띠·순환·표기.

> TOP 5는 기획 문서의 2026-11-02 개정 정책(00:00/00:05·지난주 유지·UI 3종·지연 안내·운영 알림·수동 복구·공개 버전 교체)대로 04에서 구현했다.

기준: 2026-11-18 (수, 08 팀 상세 수정 반영 완료 — Codex 교차 검증 통과), 브랜치 `feat/08-team-detail`(`dev` 병합). 실제 존재하는 파일만 적는다. 잠금 파일(`uv.lock`, `package-lock.json`), 빈 `__init__.py`, 생성 파일(`frontend/src/lib/api/schema.d.ts` — `npm run gen:api`로 생성, 직접 수정 금지)은 제외한다. 상태는 **완료**(현재 범위 구현 끝) / **골격**(계약·구조만 있고 담당 채팅이 채움)으로 표시한다.

## 루트·문서

| 파일 | 역할 | 상태 |
| --- | --- | --- |
| `.gitignore` | `.env*`·가상환경·`node_modules`·캐시 등 커밋 제외 목록 | 완료 |
| `docs/guide.md` | 공통 설계·담당·진행 상태·인수인계 기준 | 계속 갱신 |
| `docs/daily-work-log.md` | 일별 작업 내역(요청 시 갱신) | 갱신됨 |
| `docs/file-feature-map.md` | 이 문서(요청 시 갱신) | 갱신됨 |

## 백엔드 (`backend/`)

### 설정·실행

| 파일 | 역할 | 연결 | 상태 |
| --- | --- | --- | --- |
| `pyproject.toml` | 의존성(FastAPI, SQLAlchemy 2.1.6, Alembic 1.20.1, APScheduler 3.11.3, 04: google-genai 2.34.0 등)과 ruff·pytest 설정 | `uv.lock` | 완료 |
| `.python-version`, `.gitignore` | Python 3.12 지정, 백엔드 전용 제외 목록 | — | 완료 |
| `certs/supabase-ca.crt` | Supabase TLS(`verify-full`) CA 인증서 | `app/database.py`, `app/db/session.py` | 완료 |
| `app/config.py` | `Settings`: `.env` 로딩, CORS·신뢰 프록시·스케줄러·API-Football 한도·비밀 값(`SecretStr`)·디스코드 웹후크, 03: `current_season`(2026)·네이버 키/주소·`news_retention_hours`(72)·`image_rights_enforced`, 04: `gemini_api_key`·`top5_alert_discord_webhook_url`(SecretStr)·`top5_llm_model`(gemini-3.8-flash)·`top5_attempt_timeout_seconds`(240), 00(2026-11-04): `top5_llm_fallback_model`(하위 모델), 05: `first_season`(2025, 관리 시즌 시작) | 전 모듈 | 완료 |
| `app/core/kst.py` | `kst_today()`·`kst_date()`(KST 고정 오프셋) | 일정·뉴스·TOP 5 | 완료 |
| `app/core/locks.py` | `single_flight()`(스레드 잠금 + 트랜잭션 advisory lock으로 같은 키의 보충 조회를 1회로 합침), `advisory_key()` | 경기 상세·상대 전적·팀 흐름 보충 | 완료(04) |
| `app/main.py` | FastAPI 앱, 예외 처리(먼저)·CORS·`/api/v1` 라우터 등록, `/health`, 스케줄러 수명 주기 | `app/api/*`, `app/sync/scheduler.py` | 완료 |
| `app/database.py` | psycopg 직접 연결(검증 TLS), CA 경로 상수 | `check_database.py`, `db/session.py` | 완료(00) |
| `app/check_database.py` | `python -m app.check_database`: 읽기 전용 연결·TLS 확인 | `database.py` | 완료(00) |

### DB·마이그레이션

| 파일 | 역할 | 연결 | 상태 |
| --- | --- | --- | --- |
| `app/db/base.py` | 선언형 `Base`, 제약 이름 규칙 | 모델, `migrations/env.py` | 완료 |
| `app/db/session.py` | `sqlalchemy_url`(psycopg 드라이버 변환), `connect_args`(TLS), `get_engine`·`get_sessionmaker`(지연 생성), `get_db`(요청 세션 의존성) | 라우트, `sync/runner.py`, `migrations/env.py` | 완료 |
| `app/models/__init__.py` | 모든 모델 import(Alembic 인식용, 06: 순위·선수 모델) | `migrations/env.py` | 완료 |
| `app/models/feedback.py` | `Feedback`: user_id(외래 키 없음)·type·body(1~1,000자)·page_path·body_hash·created_at, 제약·인덱스 | `services/feedback.py` | 완료(02가 user_id 외래 키 추가) |
| `app/models/sync_run.py` | `SyncRun`: 수집 실행 기록(job·params·상태·API 요청 수·오류 요약) | `sync/runner.py` | 완료 |
| `app/models/reference.py` | `Competition`·`CompetitionSeason`(availability·fixtures_synced/failed_at·창, 05: season_fixtures_synced/failed_at)·`Team`(08: `venue_name`·`venue_capacity`)·`TeamCompetitionSeason`·`TeamAlias`(for_search·for_news·ambiguous) | 03 서비스·수집 | 완료 |
| `app/models/fixture.py` | `Fixture`: 대회·시즌·킥오프(UTC)·KST 날짜·변환 상태·종료 유형·원본 상태·경과 분·스코어 jsonb·경기장, 05: 시즌·상태·킥오프 인덱스 | `services/fixtures.py` | 완료 |
| `app/models/standings.py` | `Standing`(리그·시즌·그룹·팀 PK, 순위·경기 수·승무패·득실·승점·form·그 시즌 `description` 그대로), `PlayerRanking`(goals·assists·yellow·red, 제공 위치 PK, red만 `yellowred` 별도), `Player`(신원·사진, 08: `profile_checked_at` — 국적 1회 보완 기록), `PlayerSeasonStat`(선수·팀·대회·시즌 PK, 출전·평점·득점·도움·선방·카드 + 원본 `raw` jsonb — 08 재사용), `LeagueSync`(리그·시즌·종류별 마지막 성공·실패·요약·행 수) | `services/standings.py` | 완료(06) |
| `app/models/team_detail.py` | `TeamCoach`(현직 감독, 없으면 이름 NULL), `SquadMember`(현재 선수단 번호·포지션), `TeamSeasonStat`(팀·리그·시즌 `/teams/statistics` 원본), `Transfer`(팀 관점 영입·방출 원본, 상대 팀 제공값, 시즌·반기, 고유 인덱스: 상대 팀 ID 있으면 ID·없으면 이름), `TeamPlayerStat`(2026-11-18: 팀·선수·대회·시즌 줄 — 지원 대회 8개, 값 NULL 허용, 평점 numeric), `TeamSync`(팀·시즌·종류 coach·squad·statistics·transfers·player_stats별 마지막 성공·실패) | `services/team_detail.py` | 완료(08) |
| `app/models/match_detail.py` | `FixtureDetail`(통계·라인업·선수 원본 블록·수집 상태·실패 시각), `FixtureEvent`(경기별 순번, 수집 때마다 교체), `HeadToHead`(경기별 맞대결), `TeamForm`(팀별 최근 공식 경기) | `services/match_detail.py`·`head_to_head.py` | 완료(04) |
| `app/models/review.py` | `Review`(텍스트 평가: 본문 필수·≤300·공백만 금지 `REVIEW_BODY_SPACE_CLASS`, 회원·경기 유일, 별점 없음 — 0015), `ReviewReaction`(±1, 평가·회원 유일) — `user_id` 외래 키는 02 | `services/reviews.py` | 완료(04, 02가 작성·반응 연결) |
| `app/models/top_matches.py` | `Top5Week`(주간 작업 상태·자동 시도 수·알림 시각), `Top5Attempt`(시도·근거·모델 출력), `Top5Publication`(공개 버전), `WeeklyTopMatch`(고정 순위·이유·선정 당시 킥오프) | `services/top5_selection.py`·`top_matches.py` | 완료(04) |
| `app/models/news.py` | `NewsArticle`(url_hash unique·출처 도메인·뱃지·만료 시각), `NewsArticleTeam` | `services/news.py`, `sync/news.py` | 완료 |
| `alembic.ini` | Alembic 설정(접속 주소는 `env.py`가 `.env`에서 읽음) | `migrations/` | 완료 |
| `migrations/env.py` | `DATABASE_URL`·TLS로 온라인 마이그레이션, 오프라인 SQL 출력 | `app.db.*`, `app.models` | 완료 |
| `migrations/script.py.mako` | 새 리비전 템플릿(RLS 활성화 안내 포함) | — | 완료 |
| `migrations/versions/20261031_0001_sync_runs_feedback.py` | `sync_runs`·`feedback` 생성, RLS 활성화 | — | 개발 DB 적용 |
| `migrations/versions/20261031_0002_feedback_body_hash.py` | `feedback.body_hash` 컬럼·길이 제약·인덱스 | — | 개발 DB 적용 |
| `migrations/versions/20261102_0003_reference_data.py` | 대회·시즌·팀·참가·별칭 테이블, RLS 활성화 | — | 개발 DB 적용 |
| `migrations/versions/20261102_0004_fixtures.py` | `fixtures`, KST 날짜·팀·상태 인덱스, RLS | — | 개발 DB 적용 |
| `migrations/versions/20261102_0005_news.py` | `news_articles`·`news_article_teams`, RLS | — | 개발 DB 적용 |
| `migrations/versions/20261103_0006_match_detail.py` | `fixture_details`·`fixture_events`·`head_to_head`·`team_forms`, RLS | — | 개발 DB 적용 |
| `migrations/versions/20261103_0007_reviews.py` | `reviews`·`review_reactions`(CHECK·유일 제약), RLS | — | 개발 DB 적용 |
| `migrations/versions/20261103_0008_top5.py` | `top5_weeks`·`top5_attempts`·`top5_publications`·`weekly_top_matches`, RLS | — | 개발 DB 적용 |
| `migrations/versions/20261104_0009_fixture_coverage.py` | `competition_seasons.fixtures_window_start/end`(03, 21일 수집 범위) | — | 개발 DB 적용 |
| `migrations/versions/20261105_0010_season_fixtures.py` | `competition_seasons.season_fixtures_synced_at/failed_at`, 인덱스 `ix_fixtures_season_status_kickoff`(05) | — | 개발 DB 적용 |
| `migrations/versions/20261106_0011_standings.py` | `standings`·`players`·`player_rankings`·`player_season_stats`·`league_syncs`, CHECK(종류)·인덱스, RLS 활성화(06) | — | 개발 DB 적용 |
| `migrations/versions/20261107_0012_team_detail.py` | `team_coaches`·`squad_members`·`team_season_stats`·`transfers`·`team_syncs`, CHECK·인덱스·RLS, `teams.venue_*`·`players.profile_checked_at` 추가(08) | — | 개발 DB 적용 |
| `migrations/versions/20261107_0013_transfer_counterpart_key.py` | 이적 고유 키에 상대 팀 이름 추가(Codex 3차 N4) | — | 개발 DB 적용 |
| `migrations/versions/20261107_0014_transfer_identity_indexes.py` | 이적 고유 제약을 상대 팀 ID 유무별 부분 고유 인덱스 2개로 교체 — 파서의 ID 또는 이름 기준과 같음(Codex 4차 N7) | — | 개발 DB 적용 |
| `migrations/versions/20261118_0016_team_player_stats.py` | 08 수정(2026-11-18): `team_player_stats`(PK team·player·competition·season, 외래 키·RLS), `ck_team_syncs_kind_allowed`에 `player_stats` 추가, downgrade는 player_stats 동기화 행 삭제 후 CHECK 복원·테이블 삭제 | `models/team_detail.py` | 개발 DB 적용(head) |
| `migrations/versions/20261111_0015_text_reviews.py` | 04 개선: `reviews.rating`·범위 CHECK 삭제, body NOT NULL + `ck_reviews_body_not_blank`(Python `str.isspace()` 공백만이면 거부), 공백 본문이 있으면 업그레이드 실패·평가가 있으면 downgrade 거부 | `models/review.py` | 개발 DB 적용 |
| `app/seed/competitions.py` | 21개 대회(03 2026-11-19: 국가별 슈퍼컵 5·UEFA 슈퍼컵·FIFA 클럽 월드컵 추가, 처음 14개) 한국어 이름·그룹·정렬, `LEAGUE_IDS`·`UEFA_IDS`, `season_label` | `services/reference.py`, `sync/*` | 완료 |
| `app/seed/countries.json` | 08 수정: API-Football `/countries` 1회로 만든 {국가명: 국기 URL} 170개(국적 국기 표시, `flag_url`이 공백·하이픈 무시하고 찾음) | `services/team_detail.py` | 완료(08) |
| `app/seed/team_aliases.json` | 5대 리그 96팀 한국어 이름·별칭(P-11), `searchOnly`·모호 별칭 묶음, 05: 2025-26 강등 15팀(모두 `searchOnly`, 뉴스 근거 제외) | `apply_alias_seed` | 완료(검수된 별칭 추가 시 갱신) |
| `app/seed/top5_curation.json` | TOP 5 운영 기준: 더비·라이벌 40쌍(팀 ID 쌍), 팀 관심도 high·medium(시청 관심 추정 지표), 버전 | `services/top5_selection.py` | 완료(사용자 확인 2026-11-03, 바꿀 때 버전 올림) |

### API

| 파일 | 역할 | 연결 | 상태 |
| --- | --- | --- | --- |
| `app/api/router.py` | `/api/v1` 라우터, 전 라우트에 CSRF 검사·오류 응답 문서화, 05 지난 경기 라우터, 06 순위 라우터, 07 팀 탐색 라우터, 경기 상세 라우터는 일정 라우터 뒤에 등록 | `main.py`, `routes/*` | 완료 |
| `app/api/errors.py` | `ApiError`, 오류 응답 형식, 검증·HTTP 예외 처리기, `UnhandledErrorMiddleware`(미처리 예외를 500으로, 서버 로그에는 종류만) | 전 라우트 | 완료 |
| `app/api/deps.py` | `require_csrf`(헤더·Origin), `RateLimit`(클라이언트별 + 전역 상한, 둘 다 통과 시에만 집계, `route_class()`로 본문 해석 전 적용, `key_func` 교체 가능) | `router.py`, `routes/feedback.py` | 완료(02가 회원·비회원 차등) |
| `app/core/rate_limit.py` | `RateLimiter`(슬라이딩 윈도, `check`·`record`·`hit` 각각 단일 잠금 — `hit`은 검사·기록 원자적, 최근 사용 순 정리·최대 10,000키), `client_ip`(신뢰 프록시 뒤에서만 `X-Forwarded-For`), `Retry-After` 값 | `api/deps.py` | 완료 |
| `app/api/routes/feedback.py` | `POST /api/v1/feedback`: 요청 제한(라우트 클래스, 확정값), 허니팟 거부, 중복 409, 저장 후 디스코드 알림 예약 | `services/feedback.py`, `notifications/discord.py` | 완료 |
| `app/api/routes/top_matches.py` | `GET /api/v1/top-matches/current`(공개 결과·`meta.updatedAt`), `/version`(열린 화면 교체 감지) | `services/top_matches.py` | 완료 |
| `app/api/routes/matches.py` | `GET /fixtures/{id}`(경기 정보·영역 표시 여부), `/detail`(4개 블록, 요청 시 보충), `/head-to-head`(예정·연기만), `/reviews?sort=`(`review_open` — 진행 중·일반 종료만, 아니면 409) | `services/match_detail.py`·`head_to_head.py`·`reviews.py` | 완료(04) |
| `app/api/routes/results.py` | `GET /results?season=&competitions=&team=&page=`(시즌 전체 종료 경기·10개 단위, 미지원 시즌 404·잘못된 대회 422·없는 팀 404·최초 미적재 503·갱신 실패는 결과 + `failedCompetitionIds`) | `services/results.py` | 완료(05) |
| `app/api/routes/standings.py` | `GET /standings?league=&season=`(5대 리그 + 06 개선 UEFA 2·3·848 리그 페이즈, 행마다 `recent` 최근 5경기·표 `complete`, 컵 404·미지원 시즌 404·미수집 503·`refreshFailed`), `/standings/summary`(현재 시즌 리그별 상위 6행, 리그별 미수집 분리), `/player-rankings?league=&season=&type=`(5대 리그만·UEFA 404, 4종 제공 순서, 선방 자체 집계·`excluded`·`tied`, 잘못된 유형 422), 06 개선 `GET /knockouts?league=&season=&stage=`(UEFA만, 저장 경기로 대진·차전 `leg`(모든 경기 저장 시만)·합산·승부차기·승자, 시즌 경기 미적재 503, 공급사 호출 없음) | `services/standings.py`·`services/knockouts.py` | 완료(06, 06 개선) |
| `app/api/routes/teams.py` | `GET /teams?league=&q=&team=&page=`(07, 현재 시즌 5대 리그 소속 팀 12개씩, 정수이면서 5대 리그가 아니면 404·정수가 아니면 422, `team`은 그 팀 하나만(소속 아니면 빈 목록, 1~2,147,483,647 밖 422), 소속 미확인 503 `MEMBERSHIP_UNKNOWN`), 08: `GET /teams/{id}`(기본 정보·순위·감독·경기장·최근 5경기 — 저장 경기, 외부 호출 없음)·`/fixtures`(예정 3·최근 5)·`/squad`(지원 대회 합계·대회별 줄·국기·빠진 대회)·`/season-stats?season=`(승격 팀 not_participated)·`/transfers?season=`(응답 때 중복 정리, 표시·기타 목록)(이번·지난 시즌만), 없는 팀 404·허용 밖 404 `TEAM_DETAIL_UNAVAILABLE`·소속 미확인 503·미수집 503 | `services/team_browse.py`·`team_detail.py` | 완료(07·08) |
| `app/api/routes/schedule.py` | `GET /competitions`(05: 관리 시즌별 `seasons`), 05: `GET /seasons`·`require_supported_season`·`/teams/search?season=`, `/fixtures?date=`, `/fixtures/next?teams=`(양의 정수 1~5개), `/fixtures/team?team=`(오늘−3~+17일), `/teams/search?q=`, `/news`(08: `team` — 팀 연결 기사 최신 48개, 없는 팀 404), `/news/{id}/link`(요청 제한). 미수집 503·일부 실패 `failedCompetitionIds` | `services/fixtures.py`·`news.py`·`news_link.py`·`team_search.py` | 완료 |

### 스키마·서비스·연동

| 파일 | 역할 | 연결 | 상태 |
| --- | --- | --- | --- |
| `app/schemas/common.py` | `ApiModel`(camelCase), `DataResponse[T]`, `ErrorBody`·`ErrorResponse` | 전 스키마 | 완료 |
| `app/schemas/match.py` | `TeamRef`(`detailAvailable`), `CompetitionRef`, `MatchScore`, `MatchSummary` | `top_matches.py`, 03·04 | 완료(03이 실제 데이터로 채움) |
| `app/schemas/schedule.py` | `CompetitionItem`(05: `seasons`), 05: `SeasonItem`·`SeasonsResponse`·`ResultsPage`·`ResultsMeta`·`ResultsResponse`, `ScheduleMeta`, `FavoriteSchedule`, `TeamSchedule`, `NewsItem`·`NewsMeta`·`NewsLink`와 각 응답 | `routes/schedule.py` | 완료 |
| `app/schemas/standings.py` | `StandingRow`·`TableRow`(+`recent`)·`RecentMatch`·`TeamName`·`StandingGroup`·`LeagueStandings`(`complete`)·`StandingsMeta`(`updatedAt`·`refreshFailed`)·`StandingsSummary`, `PlayerRef`·`PlayerRankItem`(`rank`·`tied`·`yellowRed`)·`PlayerRankings`(`excluded`), 06 개선 `KnockoutStage`·`KnockoutTeamSlot`(`team`·`winnerOf`)·`KnockoutLeg`(`leg` 1·2·null)·`KnockoutTie`·`KnockoutRound`·`KnockoutsResponse`. 06 개선에서 `zone`·`form`·`description` 응답 필드 삭제 | `routes/standings.py` | 완료(06, 06 개선) |
| `app/schemas/teams.py` | `BrowseTeam`(`team: TeamRef`·`league: CompetitionRef`)·`TeamsMeta`(`page`·`size`·`total`·`updatedAt`)·`TeamsResponse` | `routes/teams.py` | 완료(07) |
| `app/schemas/team_detail.py` | `TeamOverview`(standing·coach·venue 부분 제공 블록, `recent: RecentMatch[]` — 06 스키마 재사용), `TeamFixtures`, `TeamSquad`(`missingCompetitions`)·`SquadPlayer`(`flagUrl`·`totals`·`competitions`)·`SquadTotals`·`SquadCompetitionLine`, `TeamSeasonStats`(available·not_provided·not_participated)·`TeamSeasonRecord`, `TeamTransfers`·`TransferHalf`(라벨·기간·상태·영입/방출·기타 영입/방출)·`TransferItem`, `TeamSyncMeta`(`updatedAt`·`refreshFailed`) | `routes/teams.py` | 완료(08) |
| `app/schemas/top_matches.py` | `TopMatches`(`version`·`view` list·none·delayed·`week`·`currentWeek`·`selectedAt`·`items`), `TopMatchItem`(순위·이유·`selectedKickoffAt`·경기), `TopMatchesVersion`, 응답 래퍼 | `services/top_matches.py` | 완료(04) |
| `app/schemas/match_detail.py` | `MatchInfo`, 블록 상태 `BlockStatus`와 `EventsBlock`·`StatisticsBlock`·`LineupsBlock`·`PlayersBlock`, `HeadToHead`(`MeetingsBlock`·`FormBlock`), `ReviewList`·`ReviewItem`·`ReviewSummary` | `routes/matches.py` | 완료(04) |
| `app/schemas/feedback.py` | `FeedbackCreate`(본문·유형 필수, 페이지 경로, 허니팟 `website`), `FeedbackReceipt` | `routes/feedback.py` | 완료 |
| `app/services/feedback.py` | `create_feedback`, `normalize_body`·`body_hash`, `lock_body_hash`(본문 해시별 트랜잭션 잠금), `is_duplicate`(24시간), `DuplicateFeedbackError` | `routes/feedback.py` | 완료 |
| `app/services/top_matches.py` | `shown_publication()`(이번 주 공개본 → 바로 지난주 list·none → 지연 안내), `current_version()`, `get_current_top_matches()`, `current_kst_week()`·`week_of()` | `routes/top_matches.py`, 선정 | 완료(04) |
| `app/services/top5_selection.py` | `run_attempt(trigger)`(주 잠금·시간 제한·데몬 스레드·게시 가드), `select_week`(일정 신선도·후보·순위표·근거 수집·프롬프트·Gemini·검증), `validate_picks`, `_publish`·`_fail`·`_start`, `reconcile_attempts`(중단 시도 정리), `retry_due`·`first_attempt_due`·`recovery_due`, `load_curation`, 00(2026-11-04): `gemini_generate()` 주 모델 오류 시 하위 모델 1회 대체·`AllModelsFailed`, 두 모델 실패 시 운영 알림, 응답 모델 기록 | `sync/top5.py` | 완료(04) | 01(2026-11-10): `_missed_week`·`reconcile_attempts`가 시도 기록이 없는 현재 주를 슬롯+60초 뒤 지연 공개(잠금 후 현재 주 재확인).
| `app/services/match_detail.py` | `store_fixture_records`(06 개선: 경기 본체 저장 `upsert_fixture_items`를 통과한 항목만 이벤트·상세 블록 저장, 받아들인 경기 ID 반환 — 옛 `save_provider_items` 대체), `detail_fetch_due`·`ensure_records`(요청 시 1회 보충, 거부된 경기는 기존 기록 보존·실패 시각만 기록), `mark_record_failures`, `final_record_targets`(종료 전환 대상), `read_records`(블록 상태 판정·통계·라인업·평점 해석, 04 개선: 예정·연기는 외부 조회 없음, `_name()`으로 선수·감독 이름 HTML 엔티티 해제·영문 유지) | 라우트·`sync/fixtures.py` | 완료(04, 06 개선 보완) |
| `app/services/head_to_head.py` | `fetch_meetings`·`fetch_form`(친선·미종료 제외, 범위 확대 1회), `ensure_meetings`·`ensure_form`(갱신 조건·쿨다운, `strict`는 TOP 5), `recent_form`·`result_for`, `read_head_to_head` | 라우트·TOP 5 | 완료(04, 08 재사용 가능) |
| `app/services/reviews.py` | `list_reviews(sort)`(인기순·최신순·반응 수·유효 건수, 평균 없음), `review_open`(진행 중(SUSP 제외)·일반 종료만 공개·작성 가능 — 02 쓰기 API도 사용) | `routes/matches.py` | 완료(04, 02가 작성·반응·닉네임) |
| `app/services/match_status.py` | `map_status()`: 제공사 상태 → scheduled·live·finished·postponed·cancelled·abandoned·unknown, 종료 유형, 시각 확정 여부 | `services/fixtures.py` | 완료 |
| `app/services/reference.py` | `normalize_name`, 대회·팀·참가 upsert, `apply_alias_seed`, `team_detail_lookup`(팀 상세 허용 집합 — 08: 팀 목록이 수집된 리그 소속만 true), `team_ref`·`competition_ref`·`crest`, 05: `managed_seasons`, 08: `upsert_teams`가 venue 블록의 있는 필드만 저장 | 전 03 서비스 | 완료 |
| `app/services/results.py` | `supported_seasons`·`season_item`, `season_coverage`(`SeasonCoverage`: 실패·최초 미적재 구분), `finished_results`(시즌 종료 경기 최신순·대회·팀·페이지) | `routes/results.py`·`schedule.py` | 완료(05) |
| `app/services/standings.py` | 파싱 `parse_standings`(그룹별 순위 1..n·그룹 안 팀 중복 거부)·`parse_top_list`(리그 줄 합산, red만 `yellowred`)·`parse_player_pages`(1..total·마지막 외 20명·같은 선수 반복 거부·정상 빈 응답), 저장 `check_standings`(행 수 감소 금지·참가 팀 안·3경기 이상 팀 포함, 06 개선: UEFA는 그룹 1개·36팀·1~36위)·`save_standings`·`save_ranking`(목록 축소 금지)·`save_player_stats`(10% 초과 감소 금지) — 완전한 응답만 한 트랜잭션 교체, 06 개선 `STANDINGS_IDS`(5대 리그 + UEFA 3)·`table_fixtures`(UEFA는 'League Stage' 라운드만)·`table_complete`(순위표 팀끼리 서로 다른 대진 기준: 리그 n×(n−1) 홈·원정 쌍, UEFA 144/108 대진·팀별 8/6, 같은 팀 행·표 밖 팀·취소 행 제외, 열린 경기 있으면 false)·`recent_matches`(팀별 최근 종료 5경기, 오래된 순), 수집 주기 `due_leagues`·`is_matchday`, 조회 `read_standings`·`read_top_list`·`read_saves`·`aggregate_saves`(null 제외·공동 순위), `sync_state`·`mark_success`·`mark_failure`. 06 개선에서 `relegation_zone` 삭제(강등 구간은 화면이 순위 위치로 판단) | `routes/standings.py`·`sync/standings.py` | 완료(06, 06 개선) |
| `app/services/knockouts.py` | 06 개선: UEFA 토너먼트 단계(`playoff`·`r16`·`qf`·`sf`·`final` = 'Round of 32'~'Final', 대진 8·8·4·2·1) — `build_stage`가 저장 경기를 팀 쌍으로 묶어 합산(연장 포함)·마지막 경기 승부차기로 승자 결정, 대진 하나만 빠지면 직전 라운드 미사용 대진으로 'A–B전 승자'·'상대 미정', 나머지는 '예정 · 대진 미정'(추첨 경로 추정 없음), 예선 제외 | `routes/standings.py` | 완료(06 개선) |
| `app/services/fixtures.py` | `upsert_fixtures`(05: 이름 없는 신규 팀 경기 제외·경고, 저장 수 반환; 06 개선: 홈·원정 팀이 같은 경기 응답은 건너뛰고 기존 행 유지)·`upsert_fixture_items`(06 개선: 실제 저장한 원본 항목 반환 — 상세 기록 저장 기준), `live_targets`·`needs_live_sync`, `to_summary`(예정·연기·취소 스코어 null), `sync_state`(실패 대회; 03 2026-11-19: `window`면 그 기간 관련 대회 `relevant_competition_ids`·`all_failed`), `schedule_period`(공통 경기일 기간: 과거 3 + 오늘 + 미래 17 경기일)·`fixture_availability`·`overlaps`·`stored_seasons`·`covered`, `fixtures_on`, `team_schedule`(공통 기간), `next_for_teams`, 04: `summaries_by_ids`(TOP 5 항목) | 라우트·수집 | 완료 |
| `app/services/team_search.py` | `search_teams(q, season=)`: 별칭·이름 검색, 여러 팀 후보, 최대 10개(기본 현재 시즌, 05: 선택 시즌 참가 팀), 07: 매칭·정렬 `match_teams(q, teams)`(상한 없음, 팀 탐색과 공유) | `routes/schedule.py`, `services/team_browse.py` | 완료 |
| `app/services/team_browse.py` | `browse_teams(league=, query=, page=, team_id=)`: 현재 시즌 5대 리그 `team_competition_seasons`만, 리그 순서→표시 이름 또는 검색 일치순, `team_id`면 그 소속 팀 하나만, `PAGE_SIZE` 12, 대상 리그 팀 목록 미수집 시 `MembershipUnknown` | `routes/teams.py` | 완료(07) |
| `app/services/news_classify.py` | 규칙 기반 분류(P-08): `AliasIndex`, `subject_competitions`(주제 기준), `classify`(다른 종목·여자 축구·근거 없음 제외), `plain_text` | `sync/news.py` | 완료 |
| `app/services/news.py` | 커서 페이지 분할 `list_news`(08: `team` — 팀 연결 기사 최신 24개 `TEAM_NEWS_LIMIT`, 뱃지 없는 기사 포함, 메인 48개), `collection_state`(최근 수집 실패·오래됨) | `routes/schedule.py` | 완료 |
| `app/services/team_detail.py` | 08: 파싱(`pick_coach` 시작 전 재임 제외·`parse_squad`·`parse_statistics`·`parse_transfers` 날짜→시즌·반기, 미래 제외, 원본 그대로·`parse_profile_nationality`·`parse_team_players` 페이지 완전성·같은 선수 반복 거부·8개 대회 줄만), 완전성(`check_squad` 18명·25%, `check_statistics` 합계, `check_transfers` max(2,10%), 선수 기록 10% 감소 거부), 저장(`save_*`·`save_team_player_stats`, 실패 시 기존 행 유지), 일정(`is_due` KST 하루 1회·`transfer_seasons`·`last_refresh_day` 7/1·`final_refresh_done`), 접근(`detail_access`), 조회(`recent_results`·`match_result`·`team_fixtures`·`read_squad`·`missing_record_competitions`·`read_transfers`·`display_text`), 이적 정리 `merge_transfers`((가) ID 없는 복사 줄 제거·(나) 같은 시즌 재등록 합침), 표시 기준 B `transfer_context`·`shown_first`, 국기 `flag_url` | `routes/teams.py`, `sync/team_detail.py` | 완료(08) |
| `app/services/news_link.py` | `check_link()`: 원문 HEAD→GET 헤더 1회, 404·410만 gone, 공개 주소만 | `routes/schedule.py` | 완료 |
| `app/providers/naver_news.py` | `NaverNewsClient.search()`(키 없으면 요청 없음, 인증·한도 오류 시 중단, 요청 수 집계) | `sync/news.py` | 완료 |
| `app/notifications/discord.py` | 공통 전송 `_post`(재시도 없음), `notify_feedback`·`build_payload`·`FeedbackNotice`, 04: `notify_top5_delay`·`build_top5_payload`·`Top5DelayNotice`(별도 채널, 복구 명령 안내), httpx 로그의 웹후크 주소 가림, 00(2026-11-04): `Top5DelayNotice.kind`(`delay`·`models_failed`)·`next_retry_at`, 두 모델 실패 알림 | 의견 라우트, TOP 5 선정 | 완료 |
| `app/providers/gemini.py` | `generate_structured()`: 키 직접 전달, 구조화 출력(`response_json_schema`), SDK 재시도 끔·밀리초 시간 제한, 오류를 안전한 `LlmError`로 | `services/top5_selection.py` | 완료(04) |
| `app/providers/api_football.py` | `ApiFootballClient.get`(401·403·429는 본문 형식과 무관하게 이후 호출 중단), `MinuteRateLimiter`, `DailyBudget`, 공용 보호 장치, 오류 클래스 | `sync/registry.py` | 완료(03 수집 작업이 `get()`으로 사용) |

### 수집 실행기

| 파일 | 역할 | 연결 | 상태 |
| --- | --- | --- | --- |
| `app/sync/registry.py` | `@register_job`(03: `precheck` — False면 호출·기록 없이 건너뜀), `JobSpec`, `JobContext`(세션·파라미터·`api_football()` 요청 수 집계), `JobPartialFailure`(일부 단위 실패) | 작업 모듈, `runner.py` | 완료 |
| `app/sync/runner.py` | `run_job`: 사전 확인 → advisory lock → `sync_runs` 기록 → 작업 실행 → 상태 저장(일부 실패 요약 포함) | `registry.py`, `db/session.py` | 완료 |
| `app/sync/reference.py` | `reference`(매일 04:00, `/leagues` 14회 + `/teams` 8회, 별칭 시드 적용, 05: 관리 시즌 모두 저장·적재한 시즌 가용성 유지, 08: 팀 목록 응답의 경기장 전달), `team_aliases`(0회) | `services/reference.py` | 완료 |
| `app/sync/team_detail.py` | 08: `team_details`(매일 15:00 KST, 팀마다 `/coachs`·`/players/squads`·`/teams/statistics` 3회, 지난 시즌 기록 1회, 선수단 국적 누락 `/players/profiles` 1회), `transfers`(매일 00:00 KST, 팀마다 `/transfers` 1회, 요청이 쓰려던 모든 시즌에 성공·실패 기록), `team_player_stats`(2026-11-18, 매일 15:30 KST, 팀마다 `/players?team=&season=` 전체 페이지 — 현재 시즌 매일·지난 시즌은 성공 1회 후 고정, `_player_units`). `team`·`league`·`force` 파라미터, DB만 보는 사전 확인 | `services/team_detail.py` | 완료(08) |
| `app/sync/fixtures.py` | `fixtures`(30분, 대회별 오늘−3~+17일 14회, 실패 대회는 기존 행 유지), `fixtures_live`(1분, 진행·임박 경기 없으면 건너뜀, 04: 응답 이벤트·상세 블록 저장; 06 개선: 라이브 응답에서 거부·누락된 추적 경기는 ID로 다시 조회, 그래도 거부되면 정상 항목은 저장하고 부분 실패 기록), `fixture_details`(04, 5분, 최근 종료 경기 최종 기록 20개당 1회; 06 개선: 거부·누락 경기는 기존 기록 보존·실패 시각만 기록 후 대기 시간 뒤 재시도), 05: `fixtures_season`(시즌 전체 대회당 1회, 현재 시즌 매일 13:00 KST, 요청 실패·저장 오류 롤백·일부 저장을 실패로 기록), `fixtures` 일부 저장 시 실패 기록 | `services/fixtures.py`·`match_detail.py` | 완료 |
| `app/sync/standings.py` | `standings`(매시 10분 확인, DB 사전 확인으로 경기일 55분·그 외 23시간·이전 시즌 보관; 06 개선: 대상 5대 리그 + UEFA 3개 대회 리그 페이즈, UEFA 경기일은 리그 페이즈 경기로만 판단), `player_rankings`(매일 14:00 KST, 리그당 4회), `player_stats`(매일 14:20 KST, 리그 전체 `/players` 페이지) — 선수 작업은 5대 리그만. `season`·`league`·`force` 파라미터, 단위(리그×종류)별 실패 기록 후 계속, 인증·한도 중단 시 남은 단위 실패 기록 | `services/standings.py` | 완료(06, 06 개선) |
| `app/sync/top5.py` | `top5_weekly`(월 00:00 KST)·`top5_retry`(월 00:05 KST, 첫 시도 실패·미실행 시)·`top5`(관리 명령 수동 복구)·`top5_reconcile`(60초, 중단 시도 상태 정리, 01: 00:00·00:05 실행 누락 주는 지연 공개·알림 1회) | `services/top5_selection.py` | 완료(04·01) |
| `app/sync/news.py` | `news`(매시 정각, 네이버 8개 검색어), `normalize_url`·`url_hash`(중복 제거), 72시간 보관 | `services/news_classify.py`, `providers/naver_news.py` | 완료 |
| `app/sync/scheduler.py` | `SCHEDULER_ENABLED`(전체) 또는 `NEWS_SCHEDULER_ENABLED`(뉴스만)일 때 APScheduler 시작, 중복·누락 실행 방지 | `main.py` | 완료 |
| `app/sync/__main__.py` | CLI `python -m app.sync <job> [key=value] / --list` | `runner.py` | 완료 |
| `app/sync/jobs.py` | 작업 모듈 import 지점(`fixtures`·`news`·`reference`, 04: `top5`, 06: `standings`) | `__main__.py`, `scheduler.py` | 완료(기능 채팅이 모듈 추가) |

### 테스트

| 파일 | 대상 |
| --- | --- |
| `tests/conftest.py` | 실제 HTTP 호출 차단, 로컬 웹후크 설정 무시 |
| `tests/test_setup.py` | `/health`·CORS, 설정 로딩·비밀 값 마스킹, DB 연결 TLS, 연결 확인 명령(00 작성, 01에서 비밀 값 목록 보강) |
| `tests/test_api_foundation.py` | 응답·오류 형식, CSRF·Origin, 요청 제한(잘못된 JSON 포함), 의견 검증·허니팟·중복·잠금 순서·익명 저장, TOP 5 공개 이력 없음=지연 안내·KST 주 경계·계약 필드, OpenAPI camelCase |
| `tests/test_server_logging.py` | 실제 Uvicorn 서버로 미처리 예외 메시지가 로그·응답에 남지 않는지 확인 |
| `tests/test_rate_limit.py` | 분·일 윈도, 거부 요청 비집계, 미등록 키 상태 미생성, 키 수 상한, 같은 키 동시 `hit()`·`RateLimit` 동시 호출, 신뢰 프록시·`X-Forwarded-For` 처리 |
| `tests/test_api_football.py` | 성공·쿼터 기록, `errors` 실패, 재시도 상한, 중단 조건(JSON·비JSON 401·403·429), 일일 예산, 분당 대기, 키 비노출(모의 전송) |
| `tests/test_sync_runner.py` | 성공·실패·건너뜀 기록, 잠금 키, CLI, 스케줄러 |
| `tests/test_feedback_notifications.py` | 디스코드 페이로드·주소 검사·실패 처리·토큰 비노출, 라우트 알림 예약, 전역 상한·전역 거부 시 버킷 미생성 |
| `tests/test_db.py` | 접속 주소·TLS, 모델 구조, `KICKTAB_DB_TESTS=1`일 때 개발 DB 제약·중복·RLS·동시 제출 잠금 확인(롤백) |
| `tests/test_schedule_rules.py` | 상태 변환 표, 스코어 null 규칙, 이름 정규화, 뉴스 분류(주제·제외·여자 축구·Liga F 오탐), URL 중복 제거, 커서 |
| `tests/test_schedule_sources.py` | 네이버 클라이언트(모의 전송·중단 조건·키 없음), 사전 확인 건너뜀, 원문 확인(리다이렉트·내부 주소 거부), 일정·뉴스 API 입력 검증(날짜·팀 ID·분류 422), OpenAPI 메타 타입 |
| `tests/test_schedule_db.py` | `KICKTAB_DB_TESTS=1`일 때 KST 날짜·상태·연기, 관심 팀 일정(진행 우선·맞대결 1회), 별칭 검색, 실패 대회 기존 행 유지, 공통 경기일 기간·팀 일정 기간·날짜 가용성·창 경계·관련 대회 전체 실패 503·관련 대회 없는 날(03 2026-11-19)(08 시작 전 처리: 저장된 마지막 경기 날짜+30일을 써서 실제 데이터와 무관)·뉴스 48개 제한(롤백) |. 06 개선(Codex 보완): 같은 팀 양쪽 응답이 섞인 배치·잘못된 중복 응답, 라이브 거부 경기 ID 재조회 복구·실패, 최종·보충 기록 보존(롤백)
| `tests/test_match_detail.py` | 이벤트 중복 제거, 통계 순서·누락값, 라인업·평점(미출전·'0' 자리값 제외), 보충 조회 시점(예정은 호출 없음), 이름 HTML 엔티티 해제, 친선 제외·범위 확대·결과 판정 |
| `tests/test_review_window.py` | 04 개선: 상태·코드별 평가 공개·작성 가능 판정(SUSP 닫힘·INT 열림·AWD/WO 닫힘), 진행 중→SUSP→재개→종료 유지, 공백 문자 집합과 Python `isspace()`·0015 일치 |
| `tests/test_top5.py` | KST 주 경계·00:05 슬롯, 선정 검증(개수·중복·후보·순위·이유·주간), 공개 결과 선택 규칙, 프롬프트, 시드, Gemini 래퍼(모의), 지연 알림 |, 하위 모델 대체·두 모델 실패·시간 부족·대체 끔·두 모델 실패 알림 내용(2026-11-04)
| `tests/test_review_regressions.py` | Codex 교차 검증 회귀: 이번 주 공개본 우선, 게시 직전 시각 재확인, 중단 복구·재시도 슬롯, 근거 작업자 종료, 잠금 안 쿨다운, 조회 실패 블록 상태(지금 조회하는 경우만 unavailable) |
| `tests/test_results_db.py` | `KICKTAB_DB_TESTS=1`일 때 시즌 목록, 종료 경기만·최신순·행정 종료 유지, 시즌 분리·페이지, 과거 팀 검색, 상태 코드(404·422·503), 갱신 실패와 최초 미적재 구분, 시즌 적재 실패·재실행 중복 없음, 이름 없는 신규 팀, 일부 저장·저장 오류 처리, 21일 작업 일부 저장 실패, 가용성 유지(롤백) |
| `tests/test_standings.py` | 06 파싱·규칙: 제공값 그대로(33경기·null), 다른 리그·시즌 거부, red/yellowred 분리, 페이지 완전성·크기·반복·일부 겹침 거부·정상 빈 응답, 선방 합산·제외·공동 순위, 축소 규칙, 수집 주기(경기일·일일·이전 시즌), 잘못된 파라미터 기록, 06 개선: UEFA `table_fixtures`(리그 페이즈만)·`standings` 대상 범위(강등 문구 판정 테스트 삭제) |
| `tests/test_standings_db.py` | `KICKTAB_DB_TESTS=1`일 때 10개 표·요약·4종 목록·선방(검증 문서 값), 상태 코드, 갱신 실패 보존·재실행 중복 없음, 빈·잘린 응답(10/20팀·10/20명·빈 페이지·페이지 밀림) 보존, 첫 적재 짧은 목록 허용·잘린 표 거부, 미수집 503. 06 개선: 최근 5경기, UEFA 리그 페이즈 표·첫 적재 36팀만·그룹 1개 1~36위, `complete`(전체 경기 범위·대진 기준·승강 PO·취소 중복·같은 팀 행), 토너먼트 대진·결승 경로 도출·한 경기만 저장 시 `leg` null·미발표 단계(모두 롤백) |
| `tests/test_teams_db.py` | `KICKTAB_DB_TESTS=1`일 때 07 5개: 현재 소속 96팀 1회씩·리그 순서·마지막/초과 페이지, 리그별 소속, 한국어·영문·모호한 별칭·리그 결합·0건, 과거 시즌·UEFA 전용 팀 제외, 소속 미확인 503(롤백), 07 개선: 고른 팀만(`team`, 리그 불일치·미소속 빈 결과) — 6개 |
| `tests/test_teams_rules.py` | 07 요청 규칙 13건(DB 없이): 0·음수·UEFA·컵·없는 리그 404(DB 조회 없음), 형식 오류·page 0·빈/41자 q·`team` 0/문자/범위 밖 422 |
| `tests/test_team_detail.py` | 08 규칙 단위 테스트(DB 없이): 현직 감독·시작 전 제외, 선수단·시즌 기록 파싱과 잘린 응답 거부, 반기 분류·7/1 경계·KST 하루 1회, 이적 필터·원본 저장·`merge_transfers`((가) 이름만 복사 줄·(나) 재등록·반대 방향·상대 ID 없음·같은 날 두 팀), 표시 기준 B, 선수 기록 8개 대회·페이지 누락·같은 선수 반복 거부, 승부차기 결과, 프로필 응답 |
| `tests/test_team_detail_db.py` | `KICKTAB_DB_TESTS=1`일 때 08: 직접 URL 판정·링크 일치(소속 미확인), 영역 API 상태 코드, 선수단 합계 = 대회별 줄 합·평점 0 제외, 최근 5경기 순서, 승격 팀 not_participated, 반기·고정 규칙·Stones 1건·기준 B 표시, 잘린 응답 보존·실패 기록, 7/1 실패 재시도, 같은 날 두 팀 이적 저장, 경기장 부분 응답, 팀 뉴스·24개 상한, 반복 선수 페이지 기록 유지, 선수 기록 작업 단위(롤백) |
| `tests/test_top5_db.py` | `KICKTAB_DB_TESTS=1`일 때 첫 실패→재시도 공개, 두 번 실패→지연·알림 1회→수동 복구, 경기 없음, 오래된 일정 실패, 시간 초과 게시 차단, 후기 정렬·평균(롤백) |, 두 모델 실패 시 시도별 알림과 지연 알림 1회·대체 모델 응답 게시·기록(2026-11-04), 실행 누락 주 지연→수동 복구 교체·주 경계에서 지난주 공개 금지(2026-11-10)

## 프런트엔드 (`frontend/`)

### 설정

| 파일 | 역할 | 상태 |
| --- | --- | --- |
| `package.json` | 스크립트(`dev`·`build`·`lint`·`test`(04, Node 테스트 실행기)·`gen:api`), 의존성(Next 16.4.3, React 19.3.0, TanStack Query 5.105.0, openapi-typescript 7.13.0) | 완료 |
| `tests/results.test.mjs` | 05 테스트 7개(시즌 변경·팀 해제·초기화 URL, 미지원 시즌, 잘못된 팀·대회·페이지, 페이지 분할 번호, 시즌 드롭다운 트리거·옵션 '2025-26 시즌' 표기, 공통 관심 팀 버튼 줄) | 완료(05) |
| `tests/standings.test.mjs` | 06 URL 기본값·시즌/리그 변경 시 유형 유지·유형은 replace, 미지원 리그·시즌·유형, 표기 규칙, `dataStatus` — 0건 뒤 갱신 실패는 partial, 메인 칩 'BUN', `DataState` `partialAction` 마크업; 06 개선: UEFA 대회·단계 URL(단계 기본·대회 변경 시 단계 삭제), `leagueZone`(리그별 강등·승강 PO, 종료 후 결과), `phaseBands`, 차전 표기 `legRows` |
| `tests/teams.test.mjs` | 07 테스트 7개(URL 기본값·리그/검색 변경 시 첫 페이지·검색마다 기록 1단계, 잘못된 리그·페이지·검색어·팀(32비트 상한), 고른 팀 조건(리그·단어 대체), `FavoriteToggle` 5개 꽉 참 마크업, 다른 탭 선저장 시 저장소 알림, `DataState` `emptyAction` 마크업) |
| `tests/team-detail.test.mjs` | 08 테스트(포지션순 기본 정렬, 누락값 두 방향 맨 뒤·같은 선수 집합, 정렬 전환, '—' 표시, 시즌 기록 행, 이적 유형 문구(금액은 완전 이적), 반기 기본값·시작 전 반기 대체, 경기장 표기) |
| `tests/top5.test.mjs` | 01 테스트 5개(지난주 유지 시 실제 기간·준비 상태·대진 순서, 지연·경기 없음 문구 구분, 띠 고정 제목·배지 렌더, 일반 클릭 판정 `isPlainClick`, 중단 경기 문구 `statusNotes`·변경 일시 사유 중복 없음) |
| `tests/match-regressions.test.mjs` | 04 회귀 테스트(경기 정보 갱신 연동 기록 재조회·종료 1회, 상태별 영역, 타임라인 아이콘·문구, 최근 5경기 미리보기, 평가 건수만, 로고+팀명 링크, 선수 평점 카드, 중단 경기 타임라인만, 지연 경고 시계, TOP 5 교체 재시도 등), 실제 TS 모듈을 변환해 실행 | 완료(04, 개선 반영) |
| `next.config.ts` | `cacheComponents`·`partialPrefetching`, `/api/*` → `BACKEND_ORIGIN` rewrites | 완료 |
| `scripts/gen-api.mjs` | 백엔드 OpenAPI(실행 중 서버 또는 파일)로 `src/lib/api/schema.d.ts` 생성 | 완료 |
| `tsconfig.json`, `eslint.config.mjs`, `postcss.config.mjs`, `.gitignore`, `AGENTS.md` | TypeScript·ESLint·Tailwind 설정, Next 에이전트 안내(기본 생성) | 기존 유지 |

### 앱 경로 (`src/app/`)

| 파일 | 역할 | 연결 | 상태 |
| --- | --- | --- | --- |
| `layout.tsx` | `lang="ko"`, 글꼴, 메타데이터, Provider·의견 Provider·헤더·`main`·푸터 배치 | 아래 컴포넌트 전부 | 완료 |
| `globals.css` | Figma 색상 토큰(`--kt-*`)·Tailwind 테마(색·글자·반경, 03: `rounded-tile`), 포커스 3px, `kt-container`, 버튼류 포인터 커서(03) | 전 컴포넌트 | 완료 |
| `providers.tsx` | TanStack Query 클라이언트(4xx 재시도 안 함) | `layout.tsx` | 완료 |
| `page.tsx` | 메인: 일정(Suspense)·관심 팀 일정·뉴스·5대 리그 간소 순위 그리드(데스크톱 오른쪽 열 관심 팀 아래, 모바일 뉴스 다음) | `features/schedule`·`favorites`·`news`·`standings` | 완료(06 간소 순위) |
| `news/original/page.tsx` | `/news/original?id=` 원문 이동 전환 화면(NEWS-004) | `OriginalRedirect` | 완료 |
| `results/page.tsx` | `/results` 지난 경기(05 개선: 보이는 제목·소개 문구 없이 필터 카드부터, sr-only H1, Suspense 안 `ResultsSection`) | `features/results` | 완료(05) |
| `standings/page.tsx` | `/standings?league=&season=&stage=&type=` 리그 순위(06 개선: 보이는 제목·소개 삭제, sr-only H1, Suspense 안 `StandingsSection`) | `features/standings` | 완료(06, 06 개선) |
| `teams/page.tsx` | `/teams?league=&q=&team=&page=` 팀 탐색(보이는 제목·소개 없음, sr-only H1, Suspense 안 `TeamsSection`) | `features/teams` | 완료(07) |
| `teams/[id]/page.tsx` | `/teams/[id]` 팀 상세(정적 셸 + Suspense 안 `params`, 숫자 아닌 ID는 404 페이지) | `features/team-detail` | 완료(08) |
| `matches/[id]/page.tsx` | `/matches/[id]` 경기 상세(정적 셸 + Suspense 안에서 params 확인, 숫자 ID만) | `features/match/MatchDetail` | 완료(04) |
| `not-found.tsx` | 없는 경로 안내(02 전 `/login`·`/signup`, 09 전 `/mypage`) | — | 완료 |
| `icon.svg` | 파비콘(로고 심벌 기반) | — | 완료 |

### 공통 UI (`src/components/ui/`)

| 파일 | 역할 | 상태 |
| --- | --- | --- |
| `Button.tsx` | `Button`·`ButtonLink`·`IconButton`(44px), `buttonClass`, primary·secondary·ghost | 완료 |
| `Badge.tsx` | 상태 뱃지(accent·live·neutral·warning·error(04, 최근 흐름 '패'), small 12px·caption 11px) | 완료 |
| `Pagination.tsx` | 페이지 분할(Figma 53:926: 이전·번호 3개·다음 44px, 640px 이상 첫·마지막 번호와 …) | 완료(05) |
| `Tabs.tsx` | 탭(Figma Tab navigation: 44px·선택 굵은 파랑+밑줄·가로 스크롤, ARIA tabs·방향키/Home/End), `tabId`·`tabPanelId` | 완료(04, 06: `value` null = 선택 없음·첫 탭 Tab 순서, 스크롤 막대 숨김, 08: 항목 `disabled`(흐리게·클릭·방향키 건너뜀·`aria-disabled`)·오른쪽 `trailing` 문구) |
| `Dialog.tsx` | 네이티브 `<dialog>` 모달(center·sheet·responsive, compact 시트: 헤더 아래까지·시트 전체 스크롤 없음·자식 스크롤, `handle`: 하단 시트일 때만 손잡이·16px 여백, 03: `closeButton={false}` 머리말 X 없음·`scrollArea` 내용이 스크롤 영역을 정함), 첫 포커스(대화상자/닫기 버튼), 포커스 복귀·Escape·배경 클릭 닫기, 닫힘 전환 동안 내용 유지·`inert`·늦은 close 이벤트 가드(01, 2026-11-10), `BottomSheet` | 완료 |
| `chip.tsx` | `chipClass()` 필터 칩(관심 팀·뉴스 분류·리그, Figma 49:171/49:173), `<ChipLabel>`(선택 시 굵기가 바뀌어도 폭 고정 — 칩 글자를 감쌈) | 완료 |
| `Skeleton.tsx` | 로딩 자리 | 완료 |
| `DataState.tsx` | `DataState`(로딩·정상·빈 결과·일부 미제공·실패+'다시 확인'·권한 거부), `StateMessage`(오류는 정보 아이콘, Figma 57:150), 06: `partialAction`(일부 미제공 안내 옆 조작, 없으면 기존 마크업), 07: `emptyAction`(빈 결과 아래 조작), 08: `retryLabel`(실패 버튼 문구, 팀 상세 '다시 시도') | 완료 |
| `Icon.tsx` | `public/icons/` SVG 아이콘(03: chevron-left·right, info. 04 개선: thumbs 삭제 — 경기 상세는 `features/match/icons.tsx` 인라인 벡터) | 완료 |
| `cx.ts` | 클래스 결합 | 완료 |

### 공통·레이아웃 컴포넌트

| 파일 | 역할 | 연결 | 상태 |
| --- | --- | --- | --- |
| `components/common/Logo.tsx` | 승인 `logo-header.svg`(심벌+워드마크) PC 46px·모바일 40px | 헤더 | 완료 |
| `components/common/TeamCrest.tsx` | `TeamCrest`·`PlayerPhoto`: URL 없음·실패 시 대체 이미지, 고정 크기 | 경기 카드·팀 검색 | 완료 |
| `components/common/MatchCard.tsx` | 경기 카드(Figma 187:591/225:1918): `layout` schedule·stacked, `withDate`, 한국어 대회명, 카드 전체 `/matches/[id]` 링크. 01(2026-11-19): 공통 부품 `useMatchScore`(상태 확인 중·—)·`MatchStatus`(배지 + `statusNotes`, `end` 오른쪽 정렬)·`MatchTeams`(이름·엠블럼·스코어·PK, 긴 한 단어는 칸 안 줄바꿈) 분리 — TOP 5 목록도 사용 | 일정·관심 팀(04·05·08 재사용), `Top5List` | 완료 |
| `components/common/MatchStatusBadge.tsx` | 상태 뱃지(진행 중 `63′`·예정/종료 회색·변경 주황) | `MatchCard`, TOP 5 | 완료 |
| `components/common/CompetitionFilter.tsx` | 대회 단일 버튼 + 선택창(체크 초안·적용·취소·'전체 대회 보기'·0개 적용 불가), 데스크톱 560px·모바일 시트, 05: `season`(그 시즌 데이터 없음 표기) | 메인·지난 경기 | 완료 |
| `components/common/TeamSearch.tsx` | 팀 검색 combobox(별칭·여러 후보·일치 없음), ×·전체 삭제 시 선택 해제, 05: `season`(선택 시즌 후보), 라벨 '팀 일정 검색'·`description` 보조 문구 묶음을 메인·지난 경기가 함께 씀(05 개선에서 `placeholder` 옵션 삭제), 07 개선: `label`(팀 탐색 '팀 검색')·`defaultText`(단어 검색 표시)·`onSubmitText`(후보 없는 Enter = 단어 검색, 고른 팀 이름 그대로면 무시) | 메인·지난 경기·메인 관심 팀 '팀 추가'·팀 탐색 | 완료 |
| `components/common/SeasonSelect.tsx` | 시즌 드롭다운(Figma 93:3198·65:1616, 트리거·옵션 '2025-26 시즌' 표기, listbox 팝오버·키보드·포커스 복귀, 미지원 시즌은 '시즌 선택') | 지난 경기·리그 순위 | 완료(05, 2026-11-16 표기 개선) |
| `components/common/NewsCard.tsx` | 뉴스 카드(분류·제목·설명·도메인·상대 시각·원문 보기), `NEWS_BADGE_LABELS` | `MainNews`(08 재사용) | 완료(02가 북마크 버튼 추가) |
| `components/layout/SiteHeader.tsx` | 고정 헤더(본문 건너뛰기 링크, 로고, 메뉴, 인증 영역, 모바일 메뉴) + TOP 5 띠, 경로를 읽는 부분은 `<Suspense>`(04). 높이 PC 118px·모바일 130px(Figma `128:3700`·`128:4408`) | `layout.tsx` | 완료 |
| `components/layout/MainNav.tsx` | 데스크톱 메뉴 4개, 현재 페이지 밑줄, `MainNavFallback`(04, 경로 확인 전 같은 메뉴) | `nav.ts` | 완료 |
| `components/layout/MobileMenu.tsx` | 모바일 메뉴 버튼·하단 시트, 현재 페이지 강조 | `nav.ts`, `HeaderAuth.tsx` | 완료 |
| `components/layout/HeaderAuth.tsx` | 로그인(ghost)·회원가입(primary), 데스크톱·메뉴 배치 | 헤더·모바일 메뉴 | 골격(02가 `useAuth()`로 회원 상태 연결) |
| `components/layout/nav.ts` | 메뉴 목록·현재 경로 판정 | 메뉴 컴포넌트 | 완료 |
| `components/layout/HeaderHeight.tsx` | 실제 헤더 높이를 `--kt-header-height`에 동기화(ResizeObserver) | `SiteHeader.tsx`, 스크롤 여백·TOP 5 딤·패널·시트 | 완료 |
| `components/layout/StickyPanel.tsx` | 메인 PC 우측 패널 고정(헤더·TOP 5 아래 12px, 가용 높이 520px 이상이고 패널이 들어갈 때만, 구간 끝에서 멈춤 — Figma 308:4617) | `app/page.tsx` | 완료 |
| `components/layout/SiteFooter.tsx` | 로고 없음, 정책 항목(링크 없음)·의견 보내기, 구분선 아래 운영자 안내·출처·저작권(Figma `304:3823`) | `lib/site.ts`, `FeedbackButton` | 완료(정책 문서 생기면 링크 연결, 이미지 출처는 확인 중 더미) |

### 기능 (`src/features/`)

| 파일 | 역할 | 연결 | 상태 |
| --- | --- | --- | --- |
| `top5/queries.ts` | `currentTopMatchesQuery`(5분 신선도·30분 주기·포커스 재조회), `topMatchesVersionQuery`(30초 공개 버전 확인), `isOutdated` | `apiFetch`, `query-keys.ts` | 완료(04) |
| `top5/Top5Strip.tsx` | AI 선정 TOP 5 띠(PC 48px 한 줄·모바일 64px 두 줄, 순환 28px/s — 첫째 줄 배지·제목·기간, 둘째 줄 준비 상태·대진·화살표, PC는 두 줄을 `contents`로 한 줄 배치. 'AI 선정' 배지·고정 제목·실제 표시 주 기간·지난주 준비 상태·화살표 고정, `Lineup` 1~5위 끊김 없는 순환), 공개 버전 변경 시 즉시 재조회(실패 시 기존 결과 유지), `Top5StripFallback`, 펼칠 때 오래된 결과 재조회, PC 패널(비모달 `role=dialog`, 본문 폭 1280px·150ms 펼침/접힘·접힘 즉시 inert·헤더 아래 딤·첫 포커스 닫기·닫기/Escape/딤은 띠로 포커스 복귀·링크 이동(같은 페이지 메뉴 포함, 일반 클릭만) 시 닫힘), 모바일 시트(`kt-top5-sheet` 슬라이드·딤 포인터), `PanelHeading` | `Top5List`, `model.ts`, `Dialog` | 완료(04·01) |
| `top5/Top5List.tsx` | 펼침 본문(PC 행: 순위·양 팀 엠블럼 대진(420px)/대회·일시·선정 이유·상태, 모바일 행: 순위·대회·상태/일시/대진/이유 — 대진·상태는 `MatchTeams`·`MatchStatus`, 변경 일시, 경기 없음·지연 안내 상자, 5개 미만 안내, 'AI 선정 · 순서와 이유는 해당 주 동안 유지됩니다.', 목록만 스크롤 — 모바일 높이 420px 미만은 시트 본문 스크롤, 행은 일반 클릭에만 닫힘) | `model.ts`, `kst.ts`, `MatchCard.tsx` | 완료(04·01) |
| `top5/model.ts` | 공개 UI 3종(list·none·delayed) 판정과 문구, 지난주 여부·`weekLabel`(요일 없는 기간)·`PREPARING`·선정 시각, 변경 일시(D-01-10, 사유는 배지 아래로), 띠 대진 `lineupItems`, 일반 클릭 판정 `isPlainClick` | `kst.ts`, `match.ts` | 완료(04·01) |
| `match/MatchDetail.tsx` | 경기 상세 조립: 상태별 영역(MAT-001), 종료 PC 기록 좌·평가 우 384px, 진행 중 평가 아래 640px, 모바일 세로, 탭·정렬 URL(`history.replaceState`), 제목 포커스, '경기 목록으로'(같은 사이트 이전 목록 복귀), 404 안내 | 아래 파일 | 완료(04, 개선 반영) |
| `match/Scoreboard.tsx` | 대회·상태 뱃지, 팀(`detailAvailable`이면 로고+팀명 한 링크, 아니면 일반 표시), 스코어/VS/—·승부차기, 시즌·라운드·킥오프, 진행 중 스코어 지연 경고만(시계 갱신) | `MatchDetail` | 완료(04, 개선 반영) |
| `match/StatusNotice.tsx` | 연기·취소·경기 중단·행정 종료·확인 필요 안내(제공 사유만) | `MatchDetail` | 완료(04) |
| `match/MatchRecords.tsx` | '경기 기록' 헤더(진행 중 '마지막 갱신'), 4탭(아이콘 타임라인·팀 통계·라인업·선수 평점 팀별 카드), 중단 경기 타임라인만, 블록별 미제공·조회 실패·재조회 실패 안내, 경기 정보 갱신(`infoUpdatedAt`)마다 진행 중 1회·상태 변경 1회 재조회 | `queries.ts`, `Tabs`, `icons.tsx` | 완료(04, 개선 반영) |
| `match/HeadToHeadSection.tsx` | 상대 전적(요약 칩·날짜·장소·대회·결과, 현재 홈 기준 스코어)·양 팀 최근 5경기 흐름(PC 812/444 좌우·모바일 세로, 호버·포커스·탭 미리보기 '홈팀 스코어 원정팀'), 영역별 재시도 | `queries.ts`, `model.ts` | 완료(04, 개선 반영) |
| `match/ReviewSection.tsx` | '경기 평가' 공개 조회(유효 건수, 인기순·최신순, 본문·반응 수, 별점·평균 없음), `ReviewGuidance` 연결 | `queries.ts`, `icons.tsx` | 완료(04, 02가 로그인 상자·작성·반응 버튼) |
| `match/ReviewGuidance.tsx` | '경기 평가' 제목 옆 주의사항 팝오버(벡터 아이콘, 차분한 색), 포커스 복귀와 뷰포트 내 배치 | `ReviewSection.tsx` | 완료(04) |
| `match/icons.tsx` | 04 개선: 인라인 벡터 아이콘 `EventIcon`(골·실축·교체·경고·퇴장·골 취소·VAR·기타), `ThumbIcon`, `NoticeIcon` | 경기 상세 | 완료(04) |
| `match/model.ts` | 이벤트 종류 `eventKind`·문구 `eventText`('골'·'골 취소' 등), 통계 한국어 표기·막대 비율, 포지션, 승무패 뱃지, 상태별 영역 `areasOf`(`reviewsBeside`), 최근 경기 미리보기 `formPreview` | 위 컴포넌트 | 완료(04, 개선 반영) |
| `match/queries.ts` | `matchInfoQuery`(진행 중 60초), `matchRecordsQuery`(자체 타이머·포커스 재조회 없음 — `MatchRecords`가 경기 정보 갱신에 맞춰 재조회, 킥오프 전 조회 없음), `headToHeadQuery`, `reviewsQuery` | `apiFetch` | 완료(04) |
| `results/ResultsSection.tsx` | 지난 경기(05 개선: 메인과 같은 검색 묶음 + 보조 문구 '선택한 시즌의 지난 경기를 팀 이름으로 검색합니다.', 공통 `FavoriteTeamButtons`, 시즌 버튼 모바일 175px·sm 220px, 초기화 76px): 시즌·대회·팀 검색·관심 팀 버튼, 선택 팀 상세 링크/미제공 표시, 날짜별 경기 카드·페이지 분할, 후보 없음·결과 없음·조회 실패·미수집·일부 미적재·미지원 시즌·잘못된 URL 조건·페이지 초과 구분, 하이드레이션 대기 | `useResultsParams`·`queries`·공통 컴포넌트 | 완료(05) |
| `results/useResultsParams.ts` | URL 조건(`season`·`competitions`·`team`·`page`), 생략과 잘못된 값 구분(`seasonInvalid`·`invalid`), 조건 변경 시 첫 페이지·push, 시즌 유지 초기화 | `ResultsSection` | 완료(05) |
| `results/queries.ts` | `seasonsQuery`(`GET /seasons`, 06 재사용), `resultsQuery` | `apiFetch` | 완료(05) |
| `standings/StandingsSection.tsx` | 리그 순위 흰색 영역 하나: 시즌 드롭다운·대회 칩(5대 리그, 챔스·유로파·컨퍼런스 — `ChipRow`)·UEFA 단계 칩·본문. 5대 리그는 팀 표(PC 좌)·선수 순위(우, 모바일 세로, 리그·시즌별 다시 마운트 → 더 보기 초기화), UEFA는 리그 페이즈 표 또는 토너먼트 단계, 미지원 대회·시즌·단계 안내, 하이드레이션 대기 | `useStandingsParams`·`StandingsTable`·`PlayerRankings`·`LeaguePhaseTable`·`KnockoutStage` | 완료(06, 06 개선) |
| `standings/ChipRow.tsx` | 06 개선: 대회·단계 칩 줄(가로 스크롤, 선택 칩 자동 표시, 그룹 구분선) | `StandingsSection` | 완료(06 개선) |
| `standings/StandingsTable.tsx` | 5대 리그 팀 순위 표(role=table 격자, PC 순위·팀·경기·승·무·패·득실·승점·최근 5경기, 모바일 순위·팀·승점·최근 5경기·나머지 가로 스크롤), `TeamCell`(허용 집합 링크·구간 배지·'팀 상세 미제공'), 강등권·승강 PO권은 `leagueZone`으로 순위 위치 판단(종료 후 '강등'·'승강 플레이오프'), `DataState`로 로딩·빈 결과·일부 미제공(갱신 실패·소속 미확인 + '다시 확인')·조회 실패 | `queries`·`model`·`RecentForm` | 완료(06, 06 개선) |
| `standings/RecentForm.tsx` | 06 개선: 최근 5경기 칩(오래된 순, 오른쪽 끝 '최신')과 미리보기(날짜·홈 스코어 원정) — PC 호버·포커스·모바일 탭, 고정 헤더 아래·표 가로 스크롤 보이는 영역 밖이면 닫힘, 미리보기 위 호버 유지·150ms 지연 닫힘(스크롤 위치 갱신은 예약된 닫힘 유지), Escape·바깥 탭, 공급사 호출 없음 | `StandingsTable`·`LeaguePhaseTable` | 완료(06 개선) |
| `standings/LeaguePhaseTable.tsx` | 06 개선: UEFA 리그 페이즈 36팀 표(순위·팀·승점·최근 5경기, 1~8 직행·9~24 플레이오프·25~36 탈락 구간, '현재 순위 기준'/확정 결과, 모바일 팀 열 최소 120px·가로 스크롤) | `queries`·`model`·`RecentForm`·`TeamCell` | 완료(06 개선) |
| `standings/KnockoutStage.tsx` | 06 개선: UEFA 토너먼트 단계 대진 카드(상태 배지 종료·진행 중·예정·'예정 · 대진 미정', 차전·일시·스코어·승부차기, 합산/결과·진출/우승, 'A–B전 승자'·'상대 미정') | `queries`·`model` | 완료(06 개선) |
| `standings/PlayerRankings.tsx` | 선수 순위 5종 탭(득점·도움·경고·퇴장·선방), 10명 + 더 보기, '리그별 제공 상위 20명' 안내·퇴장 red만 안내, 선방 제외 인원·'공동 N', `DataState` 상태 구분(06 개선: 카드 테두리 제거, 순위 영역 오른쪽 열) | `queries`·`model` | 완료(06, 06 개선) |
| `standings/MainStandings.tsx` | 메인 5대 리그 간소 순위(Figma 306:6221): 칩(EPL·LaLiga·Serie A·Bundesliga·Ligue 1, 9px 간격, 마우스 끌기·휠·터치 가로 이동)·상위 6팀 경기·승무패·승점·'전체 순위 보기'(같은 리그·현재 시즌), 리그별 미수집·갱신 실패 구분 | `queries`·`model` | 완료(06, 03 개선) |
| `standings/useStandingsParams.ts` | URL 상태(`league`·`season`·`stage`·`type`), 미지원 대회·시즌·단계·유형 구분, 대회·시즌·단계는 push·유형은 `replaceState`, 06 개선: UEFA 대회 허용·대회 변경 시 단계 삭제·리그 페이즈는 단계 파라미터 없음 | `StandingsSection` | 완료(06, 06 개선) |
| `standings/queries.ts` | `standingsQuery`·`standingsSummaryQuery`·`playerRankingsQuery`, 06 개선 `knockoutsQuery`(5분 신선도) | `apiFetch` | 완료(06, 06 개선) |
| `standings/model.ts` | `LEAGUES`(탭·칩 이름), 06 개선 `UEFA`·`isUefa`·`competitionLabel`·`STAGES`·`stageLabel`·`leagueZone`(리그별 강등·승강 PO 위치, 종료 후 결과)·`phaseBands`·`RESULT_LABEL`·`legRows`(차전 표기), `RANKING_TYPES`, `signed`·`numberText`·`rankText`, `dataStatus`(실패 우선 → partial). 06 개선에서 `formResults`·`zoneLabel` 삭제 | 06 화면, 07 리그 칩·상태 판정 | 완료(06, 06 개선) |
| `teams/TeamsSection.tsx` | 팀 탐색 화면(Figma 52:624/52:949, 상태 57:766·57:836): 리그 칩(06 `ChipRow`, 모바일 한 줄 가로 스크롤), 공통 `TeamSearch`(라벨 '팀 검색', 후보는 현재 5대 리그 팀 — 선택 = `team`·리그 '전체', 후보 없는 Enter = `q`, 같은 조건 Enter는 이동 없음), 관심 팀 안내(5팀일 때만·저장소 차단), 소속 미확인 안내(57:836), 카드(엠블럼·이름·영문명 · 리그, `/teams/{id}` 링크, `FavoriteToggle`, 등록 시 파란 테두리), `Pagination`, `DataState`(로딩·검색 결과 없음+검색어 지우기·조회 실패·재조회 실패 시 확인된 목록 유지), 잘못된 URL·페이지 초과 안내 | `useTeamsParams`·`queries`·`favorites` | 완료(07) |
| `teams/useTeamsParams.ts` | URL 상태(`league`·`q`·`team`·`page`), 잘못된 리그·페이지·팀(32비트 상한)·40자 넘는 검색어는 `invalid`, 리그·검색 변경 시 첫 페이지, 모든 변경 push, 초기화 | Next 라우터 | 완료(07) |
| `teams/queries.ts` | `teamsQuery`(`GET /teams`, `team`이면 `q` 미전송, 10분 신선도, key `teams.list`) | `apiFetch` | 완료(07) |
| `team-detail/TeamDetail.tsx` | 팀 상세(Figma 52:1254/52:1866, 헤더 472:18198, 상태 57:766·57:836): '‹ 팀 탐색', PC 왼쪽(기본 정보·경기·선수단·뉴스)/오른쪽(시즌 기록·이적), 기본 정보(엠블럼 56·이름·영문명·리그·`FavoriteToggle`·저장소 차단 안내·리그·감독·홈구장·최근 5경기 06 `RecentForm`), 모바일 4탭(경기·선수단·기록·뉴스), URL `tab`·`stats`·`transfers`·`half`(pushState — 뒤로 가기 복원), 404·503 안내 | 영역 컴포넌트·`queries` | 완료(08) |
| `team-detail/TeamMatches.tsx` | 예정(진행 중 먼저, 3)·최근 결과(5) `MatchCard`, '경기 전체 보기' → `/results?team=`, 일부 대회 미적재·재조회 실패 안내·'다시 시도' | `teamFixturesQuery` | 완료(08) |
| `team-detail/SquadTable.tsx` | 선수단 표(Figma 470:6667: 사진·선수명·등번호·포지션·국적(국기)·출전·득점·도움·상세), 이번 시즌 지원 대회 합계, 열 정렬(`aria-sort`), 10명 후 더 보기, '부분 집계'·빠진 대회 안내, 누락 '—', 모바일 표 내부 가로 스크롤, 대회별 기록 Dialog(469:6642, 대회별 평점, 닫으면 상세 버튼으로 포커스 복귀) | `model.ts`·`teamSquadQuery` | 완료(08) |
| `team-detail/SeasonRecords.tsx` | 시즌 기록(이번/지난 시즌 버튼, '2026–27 · 리그 정규 리그', 순위·득점/실점·홈·원정·무실점·주 포메이션, '선택한 시즌의 기록이 없습니다.'·승격 팀 '…참가하지 않았습니다.')·이적(471:6856: 시즌 버튼, 이번 시즌만 최근 갱신일, 전반기/후반기 밑줄 탭 — 시작 전 비활성·'후반기는 1월부터', 영입·방출 줄 '날짜 · A → B'·유형, '기타 이동 N건' 접기, '아직 확인된 이적이 없습니다') | `model.ts`·쿼리 | 완료(08) |
| `team-detail/TeamNews.tsx` | 팀 뉴스(`NewsCard`, 최신 24개를 6개씩 더 보기, 빈 상태 '현재 확인할 수 있는 팀 관련 뉴스가 없습니다.', 갱신 실패+빈 목록 함께 안내·'다시 시도') | `teamNewsQuery` | 완료(08) |
| `team-detail/model.ts` | 탭(경기·선수단·기록·뉴스)·시즌 선택·`seasonText`('2026–27'), 포지션 표기·정렬(`sortPlayers`·`nextSort` — 합계 기준), 누락 표시(`statText`·`ratingText`), 시즌 기록 행, 이적 유형 문구(금액 형식은 완전 이적)·`dotDate`, 반기 `HALF_TABS`·`isHalf`·`currentHalf`·`pickHalf`, 경기장 표기 | — | 완료(08) |
| `team-detail/queries.ts` | `teamOverviewQuery`(404·503 재시도 없음)·`teamFixturesQuery`(진행 경기 폴링)·`teamSquadQuery`·`teamSeasonStatsQuery`·`teamTransfersQuery`·`teamNewsQuery`(무한 조회) | `apiFetch` | 완료(08) |
| `schedule/ScheduleSection.tsx` | 메인 일정(05: 하이드레이션 전 `SectionSkeleton`, 05 개선: 관심 팀 버튼 줄을 공통 `FavoriteTeamButtons`로): 날짜 보기와 팀 기간 날짜별 보기(03 2026-11-19: 공통 경기일 기간, 팀 진입은 전체 대회·해제 시 복원, 소멸 날짜 이동·안내, 기간 갱신 실패 경고)(기본 6개·한 번에 전체 보기), 대회·팀·관심 팀 조건, 빈 결과·조회 실패·일부 실패·재조회 실패 구분, 초기화 | 아래 파일, `MatchCard` | 완료 |
| `schedule/useScheduleParams.ts` | URL 조건(`date`·`competitions`·`team`·`from`), `selectTeam`·`clearTeam`(새 팀은 전체 대회, 첫 팀 직전 날짜·대회 보존·해제 시 복원 — `withTeam`·`withoutTeam`), `nearestMatchDate`(대회 적용 시 미확인 날짜를 건너뛴 가장 가까운 확인된 경기일), push/replace 규칙, `useKstToday()`(KST 자정 전환) | `ScheduleSection` | 완료 |
| `schedule/queries.ts` | `competitionsQuery`, `fixturesByDateQuery`, `favoriteScheduleQuery`, `teamScheduleQuery`, `liveRefetchInterval`(진행 60초·임박 진입 시 시작·숨김 탭 정지, 04 경기 상세도 사용) | `apiFetch` | 완료 |
| `schedule/DateBar.tsx` | 공통 경기일 날짜 막대(03 2026-11-19: 경기 있는 날만, 월/일·요일; 이전 21일 달력 폐기)(데스크톱 화살표·모바일 터치 스크롤) | `ScheduleSection` | 완료 |
| `schedule/ScheduleNotice.tsx` | 일정 안내 상자(neutral·warning·error, Figma 225:2374), `failedNames()` | 일정·관심 팀 | 완료 |
| `favorites/store.ts`·`useFavorites.ts` | 비회원 관심 팀 localStorage(`kt-fav-guest`, 최대 5개, 저장 불가 처리, 다른 탭 반영, 07: 등록·해제 직전 더 새 목록을 발견하면 모든 구독자에 알림 `latest()`) | 관심 팀 UI | 완료(02가 회원 DB 동기화) |
| `favorites/FavoriteToggle.tsx` | 관심 팀 등록/해제 버튼(거부 사유 표시 — 누른 직후 목록에 묶이고 목록이 바뀌면 지움, 07: 5개가 차면 다른 팀 비활성 '최대 5개까지 등록할 수 있어요') | 07 사용, 08 사용 예정 | 완료(07) |
| `favorites/FavoriteSchedule.tsx` | 메인 관심 팀 패널(Figma Guest Favorites 306:6220): n/5·팀 추가(`TeamSearch`, 등록 가능 팀만)·빈 상태·등록 목록 해제·5팀 제한·저장 실패 재시도, 팀별 진행 중·가장 가까운 예정 1경기 요약, 일부 실패·재조회 실패 안내 | `favoriteScheduleQuery`, `useFavorites` | 완료 |
| `favorites/FavoriteTeamButtons.tsx` | 팀 검색 아래 '★ 관심 팀' + 파란 글자 버튼(44px), 다시 누르면 해제, 선택돼도 같은 모양·`aria-pressed`, 팀이 없으면 표시 안 함(Figma 49:57·61:883) | 메인 일정·지난 경기 | 완료(05 개선) |
| `favorites/FavoriteStar.tsx` | 경기 카드 팀 옆 별표(이동 없이 등록·해제, 거부 문구 잠시 표시) | `MatchCard` | 완료 |
| `news/MainNews.tsx` | 주요 뉴스(분류 칩, 6개씩 더 보기, 추가 조회·재조회 실패 시 기존 기사 유지, 출처 안내) | `NewsCard` | 완료 |
| `news/OriginalRedirect.tsx` | 원문 확인 후 이동, 404·410만 접근 불가 안내 | `/news/{id}/link` | 완료 |
| `feedback/FeedbackProvider.tsx` | 전역 의견 모달 1개(`<Suspense>` 안, 04), `useFeedback().openFeedback()` | `layout.tsx` | 완료 |
| `feedback/FeedbackButton.tsx` | 의견 보내기 진입 버튼(모든 화면에서 푸터 하나) | 푸터 | 완료 |
| `feedback/FeedbackDialog.tsx` | 의견 입력·검증·전송·실패/중복/요청 제한/성공 상태, 허니팟, 열기 단위 세션(지난 요청 결과가 새 초안을 바꾸지 않음), 전송 중 입력 잠금, 저장소 불가 안내 | `apiFetch`, `draft.ts` | 완료 |
| `feedback/draft.ts` | 미전송 초안 sessionStorage 저장·복원, 저장 실패 여부 반환, `sameDraft` | `FeedbackDialog` | 완료 |

### 라이브러리 (`src/lib/`)

| 파일 | 역할 | 상태 |
| --- | --- | --- |
| `api/client.ts` | `apiFetch`(브라우저 같은 출처·서버는 `BACKEND_ORIGIN`, 변경 요청 CSRF 헤더, 401 갱신 연결 `setUnauthorizedHandler`) | 완료(02가 갱신 로직 등록) |
| `api/errors.ts` | `ApiError`(code·message·fieldErrors·retryAfter), 응답·네트워크 오류 변환, 07: `MEMBERSHIP_UNKNOWN` 코드 | 완료 |
| `api/types.ts` | 생성 타입의 이름 별칭(`MatchSummary`, `TopMatches`, `FeedbackCreate`, 03: `CompetitionItem`·`ScheduleMeta`·`FavoriteSchedule`·`TeamSchedule`·`NewsItem` 등, 04: `TopMatchesVersion`·`MatchInfo`·`MatchRecords`·`BlockStatus`·`HeadToHead`·`ReviewList`·`ReviewSort` 등, 05: `SeasonItem`·`ResultsPage`·`ResultsMeta`, 06: `LeagueStandings`·`StandingRow`·`StandingsMeta`·`StandingsSummary`·`PlayerRankings`·`PlayerRankItem`·`RankingType`, 07: `BrowseTeam`·`TeamsMeta`, 08: `TeamOverview`·`TeamFixtures`·`TeamSquad`·`SquadPlayer`·`TeamSeasonStats`·`TeamSeasonRecord`·`HomeAway`·`TeamTransfers`·`TransferHalf`·`TransferItem`·`TeamSyncMeta` 등), 06 개선: `TableRow`·`RecentMatch`·`KnockoutStage`·`KnockoutTeamSlot`·`KnockoutLeg`·`KnockoutTie`·`KnockoutRound` | 완료 |
| `api/query-keys.ts` | query key 규칙과 `topMatches`(current·version)·`competitions`·`fixtures`(date·team(오늘 포함)·next)·`matches`(info·records·headToHead·reviews)·`teams.search`·`news`·`me` 키, 05: `seasons`·`results`·`teams.search(q, season)`, 06: `standings`(table·summary)·`playerRankings`, 07: `teams.list`, 08: `teams.detail`·`fixtures`·`squad`·`seasonStats`·`transfers`, `news.team`, 06 개선: `standings.knockouts`(대회·시즌·단계) | 완료(기능 채팅이 키 추가) |
| `format/kst.ts` | KST 시각·날짜·주간(`10/26(월)–11/1(일)`)·`10/29(목) 03:30`·`2026-10-26 00:00` 포맷, 누락값 `—`, 03: `kstTodayIso`·`addDaysIso`·`formatRelativeKst` | 완료 |
| `format/match.ts` | 경기 표기 공용 규칙: `teamName`·`competitionName`·`scoreText`·`penaltyText`·`kickoffTime`·`isChanged`·`statusWord`, 01: `statusNotes`(중단 시점 스코어 + 제공사 사유) | 완료 |
| `hooks/useMediaQuery.ts` | 미디어 쿼리 구독, `DESKTOP_QUERY`(1024px) | 완료 |
| `hooks/useHydrated.ts` | 하이드레이션 완료 여부(공유 캐시를 읽는 Suspense 영역의 서버·클라이언트 불일치 방지) | 완료(05) |
| `hooks/useNow.ts` | 30초마다 갱신되는 현재 시각(서버 렌더 0) — 킥오프 후 '상태 확인 중' 판정 | 완료 |
| `site.ts` | 푸터 운영자 정보 설정값(`SITE_OPERATOR_*`) | 완료 |

### 정적 파일 (`public/`)

| 파일 | 역할 |
| --- | --- |
| `brand/symbol.svg` | 로고 심벌(Figma 55:22) |
| `placeholder.svg` | 공통 대체 이미지(Figma 55:26) |
| `icons/chevron-down.svg`, `chevron-left.svg`, `chevron-right.svg`, `menu.svg`, `x.svg`, `search.svg`, `info.svg`, `thumbs.svg`(04) | Figma 아이콘 |
