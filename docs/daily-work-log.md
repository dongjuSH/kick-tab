# KickTab 일별 작업 내역

## 2026-11-04 — 03 경기 일정·뉴스·UEFA 팀명

`feat/03-schedule`: 21일 날짜와 가까운 경기 자동 이동, 단일 대회 체크 초안, 팀 검색 X와 기간별 대회, 경기 6개에서 한 번에 전체 보기, UEFA 한국어 팀명 199개, 뉴스 정시 갱신·최근 48개·주제 분류를 적용했다. 개발 DB에서 마이그레이션 왕복 및 일치 확인 후 팀명(0회)·경기(API-Football 14회)·뉴스(네이버 8회) 수집을 완료했다. 기존 상세 링크 허용 범위는 그대로다.

## 2026-11-04 — 01 헤더·브랜드·TOP 5 표시

`feat/01-header-footer`: 승인 자산, 헤더 글자 너비 밑줄·중앙 확장 모션, 44/72px TOP 5 요약 띠와 전체 대진 순환을 반영했다. 린트·타입 검사·프런트 테스트 6개 통과. 로컬 모의 API로 1920/320px, 로고 크기·파비콘 링크·패널 키보드 열기/Escape 닫기·딤 포인터·포커스 정지·가로 넘침을 확인했다.

## 2026-11-03 (화) — 04 경기 상세·AI 주간 TOP 5

브랜치 `feat/04-match-detail`(03 병합 후 최신 `dev`에서 분기)에 커밋·push 후 `dev`에 병합. Codex 교차 검증 통과(1차 지적 11건 Codex 보완 → Claude 확인 중 회귀 1건 수정).

| 영역 | 변경 파일·함수 | 이유 |
| --- | --- | --- |
| 경기 상세 데이터 | `models/match_detail.py`(`FixtureDetail`·`FixtureEvent`·`HeadToHead`·`TeamForm`), 마이그레이션 `0006_match_detail`, `services/match_detail.py`(`save_provider_items`·`ensure_records`·`detail_fetch_due`·`read_records`·`final_record_targets`), `services/head_to_head.py`(`ensure_meetings`·`ensure_form`·`fetch_meetings`·`fetch_form`·`recent_form`·`result_for`), `core/locks.py`(`single_flight`) | 이벤트·통계·라인업·선수 평점 저장, 요청 시 1회 보충(동시 요청 합치기·실패 쿨다운·실패로 덮어쓰지 않음), 상대 전적(친선 제외·범위 확대)·팀 최근 흐름 캐시 |
| 수집 작업 | `sync/fixtures.py`(live 응답 이벤트·`ids` 응답 상세 저장, `fixture_details` 작업 추가) | 종료 전환 시 1회 최종 기록(20경기당 1회 요청), 진행 중 이벤트는 추가 요청 없이 갱신 |
| 후기 조회 | `models/review.py`, `0007_reviews`, `services/reviews.py`(`list_reviews`·`reviews_available`) | 공개 조회·인기순(반응 3개 이상 비율순)·최신순·평균(0건 null), 행정 종료 보류(P-05)·상태 변경 시 숨김(P-07). 작성·반응은 02 |
| 경기 상세 API | `api/routes/matches.py`(`/fixtures/{id}`·`/detail`·`/head-to-head`·`/reviews`), `schemas/match_detail.py`, `api/router.py`(schedule 뒤 등록) | 영역별 조회로 한 영역 실패가 다른 영역을 가리지 않음, 블록 상태 `available·not_provided·not_yet·unavailable` |
| TOP 5 선정 | `models/top_matches.py`, `0008_top5`, `services/top5_selection.py`(`run_attempt`·`select_week`·`validate_picks`·`_publish`·`_fail`·`reconcile_attempts`), `sync/top5.py`(`top5_weekly`·`top5_retry`·`top5`·`top5_reconcile`), `providers/gemini.py`(`generate_structured`, google-genai 2.34.0), `notifications/discord.py`(`_post`·`notify_top5_delay`), `seed/top5_curation.json`, `config.py`(Gemini·알림·시간 제한 설정) | 주간 작업 상태와 공개 결과(버전) 분리, 00:00 첫 시도·00:05 고정 재시도, 주 잠금·시간 제한·게시 가드, 여섯 입력·Gemini 구조화 출력·서버 검증·원자적 게시, 두 번째 실패 지연 공개·디스코드 알림, 관리 명령 수동 복구, 중단 시도 정리 |
| TOP 5 공개 API | `services/top_matches.py`(`shown_publication`·`current_version`·`get_current_top_matches`), `schemas/top_matches.py`, `api/routes/top_matches.py`(`/current`·`/version`), `services/fixtures.py`(`summaries_by_ids`) | 이번 주 공개본 → 지난주 list/none → 지연 안내, `selectedKickoffAt`(D-01-10 대안 A), `meta.updatedAt` |
| 경기 상세 화면 | `app/matches/[id]/page.tsx`, `features/match/*`(`MatchDetail`·`Scoreboard`·`StatusNotice`·`MatchRecords`·`HeadToHeadSection`·`ReviewSection`·`model.ts`·`queries.ts`), `components/ui/Tabs.tsx`, `Badge`(error), `Icon`(thumbs) | 상태별 영역, 4탭(URL `?tab=`), 라인업 발표 전, 상대 전적·최근 흐름, 후기 정렬(URL `?sort=`)·주의사항 상시 노출, 진행 중 폴링·지연 경고, 제목 포커스, '경기 목록으로' 이전 목록 복귀 |
| TOP 5 화면 | `features/top5/*`(`Top5Strip`·`Top5StripFallback`·`Top5List`·`model.ts`·`queries.ts`), `lib/api/types.ts`·`query-keys.ts`·`schema.d.ts` | UI 3종(목록·경기 없음·지연), 지난주 제목·기간·선정 시각·PreviousNotice, ShortListNotice, 변경 일시, 공개 버전 30초 확인으로 열린 화면 즉시 교체 |
| 레이아웃 | `SiteHeader`·`MainNav`(`MainNavFallback`)·`FeedbackProvider`의 `<Suspense>` | 동적 경로 `/matches/[id]`가 정적 셸(Partial Prerender)을 갖도록 |

- **사용자 결정:** 더비 40쌍·관심도(high 10·medium 22) 운영 시드 초안 확인(버전 `2026-11-03`). D-01-10은 대안 A(선정 당시 킥오프 저장·변경 일시 표시)로 반영.
- **기획·디자인과 다르게 처리(guide §10.3 D-04-1~7):** 비회원 '로그인하고 평가하기' 버튼 생략(02 연결), 작성 주의사항을 후기 카드에 상시 표시, 지난주 '경기 없음' 문구를 '없었습니다'로, 상대 전적 표에 홈·원정 열, 타임라인 합성 행 제외, 평점 탭은 Figma대로 평점만, 닉네임 '—'.
- **실제 실행 중 발견·수정:** 탭 전환 지연(`router.replace` 서버 왕복 → `history.replaceState`), 미출전 선수 평점 '0' 자리값 제외, 상대 전적·흐름 팀 이름 한국어화, 라운드 표기 한국어화, `none` 공개에 지난 항목이 섞이던 응답, 프롬프트 축소(238k → 148k자), 실패 시도의 후보 수 기록.
- **Codex 1차 지적 보완(11건, Codex 수정):** 이번 주 공개본 우선 표시, 게시 직전 시각 재확인(마감·주 경계), 중단 시도 정리 작업 `top5_reconcile`과 재시도 슬롯 보존, 근거 수집 데몬 작업자·DB 대기 제한, 상태 전환 시 기록 재조회·라인업 10분 확인, 잠금 안 실패 쿨다운 재확인, 교체 조회 실패 후 재시도, 조회 실패를 '발표 전'으로 표시하지 않음, 지연 경고 시계 갱신, 부분 실패 재시도 버튼, 중단 경기 타임라인만. 백엔드·프런트 회귀 테스트(`npm test`) 추가.
- **Claude 확인 중 수정(회귀 1건):** 예정 경기에서 조회 실패 후 연기되거나 킥오프가 미뤄지면 '조회 실패'가 영구히 남던 문제 → 지금 다시 조회하는 경우에만 `unavailable`(`_lookup_open`), 그 밖은 '라인업 발표 전'.
- **실제 실행 검수:** 상태별 상세(종료·예정 실제, 행정 종료·취소·국내 컵 실제 2025·2026 표본, 중단·연기·확인 필요·진행 중은 테스트 상태로 확인 후 제공사 응답으로 복원), 4탭·라인업 발표 전·상대 전적·팀 링크/미제공, 후기 정렬·평균(테스트 후기 후 삭제), TOP 5 실제 Gemini: 첫 시도 실패(잘못된 모델명 404) → 00:05 재시도 실패(제공사 503) → 지연 공개·디스코드 알림(도착 사용자 확인) → 수동 복구 실패(503) → 복구 후 수동 공개 성공, 주 상태를 비운 뒤 첫 시도 실패 → 00:05 재시도 성공. 지난주 유지·경기 없음(지난주·이번 주)은 데이터 조작으로 재현. 공개 버전 변경 후 열린 화면 35초 안 교체, TOP 5·메인 → 상세 포커스·뒤로 가기, 1280·375·320. **미실행:** 실제 진행 경기 실시간 갱신(진행 경기 없음, 가능 시각 11/4(수) 02:45 KST), 실제 월요일 00:00·00:05 시각 경과(다음 실행 11/9 00:00·00:05 KST 확인).
- **관찰(03 코드, 05 인계):** 메인 `CompetitionFilter` 하이드레이션 경합(브라우저 창이 숨겨졌을 때 개발 콘솔 오류, 화면 정상).
- **검사:** 백엔드 ruff·pytest 240 통과(DB 포함, 롤백)·alembic check, 프런트 `npm test` 6·lint·tsc·build(`/matches/[id]` Partial Prerender)·`git diff --check` 통과. 외부 호출 누적 API-Football 약 468회(TOP 5 근거 첫 수집 391회 포함), Gemini 13회(성공 2·가용성 확인 성공 1), 디스코드 TOP 5 알림 1회. Codex 보완 단계 외부 호출 0회.

## 2026-11-02 (월) — 03 경기 일정(메인)

브랜치 `feat/03-schedule`(최신 `dev`에서 분기)에 커밋·push. Codex 교차 검증 2회(1차 수정 필요 6건 → 보완 → 2차 통과). `dev` 병합은 00 확인 후.

| 영역 | 변경 파일·함수 | 이유 |
| --- | --- | --- |
| 기준 데이터 | `models/reference.py`, 마이그레이션 `0003_reference_data`, `seed/competitions.py`·`team_aliases.json`, `services/reference.py`(`apply_alias_seed`·`team_detail_lookup`·`team_ref`), `sync/reference.py`(`reference`·`team_aliases`) | 14개 대회·2026 시즌·5대 리그 96팀·별칭 371개(P-11), 팀 상세 허용 집합(`detailAvailable`) |
| 경기 수집 | `models/fixture.py`, `0004_fixtures`, `services/match_status.py`(`map_status`), `services/fixtures.py`(`upsert_fixtures`·`sync_state`·`team_schedule` 등), `sync/fixtures.py`(`fixtures`·`fixtures_live`), `sync/registry.py`·`runner.py`(`precheck`·`JobPartialFailure`) | 오늘−1~+15일 289건, 상태 변환·KST 묶음, 실패 대회는 기존 행 유지, 진행·임박 경기가 없으면 실시간 작업 호출 0 |
| 뉴스 | `models/news.py`, `0005_news`, `providers/naver_news.py`, `services/news_classify.py`·`news.py`·`news_link.py`, `sync/news.py` | 네이버 8개 검색어, 규칙 기반 분류(P-08 주제 기준), 72시간 보관, 원문 확인(NEWS-004) |
| API | `api/routes/schedule.py`, `schemas/schedule.py`, `frontend/src/lib/api/schema.d.ts`·`types.ts`·`query-keys.ts` | `/competitions`·`/fixtures`·`/fixtures/next`·`/fixtures/team`·`/teams/search`·`/news`·`/news/{id}/link` |
| 메인 화면 | `app/page.tsx`, `features/schedule/*`(`ScheduleSection`·`useScheduleParams`·`queries`·`DateBar`·`ScheduleNotice`), `components/common/CompetitionFilter`·`TeamSearch`·`MatchCard`·`MatchStatusBadge`, `lib/format/match.ts` | 날짜 보기, 대회 직접 선택·보조 다중 초안, 팀 14일 모아 보기·해제 복귀, URL 뒤로가기, 빈 결과·실패·일부 실패 구분, 임박 폴링, KST 자정 전환 |
| 관심 팀·뉴스 화면 | `features/favorites/*`(`store`·`useFavorites`·`FavoriteToggle`·`FavoriteSchedule`), `features/news/MainNews`·`OriginalRedirect`, `components/common/NewsCard`, `app/news/original/page.tsx` | 비회원 관심 팀(최대 5개·저장 불가 안내), 관심 팀 일정, 뉴스 분류 칩·6개씩 더 보기·원문 이동 |
| 공통 UI | `globals.css`(포인터 커서·`rounded-tile`), `Badge`(`info` 삭제), `Dialog`(`handle`), `DataState`(정보 아이콘·'다시 확인'), `Icon`, `ui/chip.ts`, `TeamCrest`(고정 크기), TOP 5 `Top5List`·`model.ts`(`MatchStatusBadge`·공용 표기 사용) | Figma 개정 반영, TOP 5와 일정의 상태 표기 통일 |

- **사용자 피드백 반영:** 버튼 포인터 커서, 손흥민 기사가 EPL로 묶이던 뉴스 분류를 주제 기준으로 변경(표본 40건 중 37건 적합), 대회 그룹 칩 → 단일 버튼 직접 선택, 팀 검색 시 하루 → 14일 모아 보기(문서·Figma 개정 후 구현).
- **Codex 1차 지적 보완:** 초기화 시 검색어·표시 개수 초기화, 임박 구간 진입 시 폴링 시작, 뉴스 추가 조회 실패 시 기존 기사 유지, 관심 팀 일정 일부 실패 안내, `/fixtures/next` 0·음수 ID 422, 여자 축구 기사를 팀 연결 전에 제외. 함께 발견해 고친 것: '프리메라리가 FC바르셀로나'를 Liga F로 오인하던 오탐, 일정 재조회 실패 시 목록이 사라지던 문제. 디자인 차이 3건(선택창 560px·모바일 손잡이·날짜 칸 배경) 시안에 맞춤.
- **마무리 간소화:** 테스트 전용이던 `competition_badges()`를 테스트로 이동, 대회 필터에 남아 있던 `chipClass()`를 `components/ui/chip.ts`로 이동, 파일 내부 전용 `statusLabel()`·`needsLiveRefresh()` export 제거.
- **실제 실행 검수:** 1280·375·320에서 날짜·대회·팀·관심 팀·초기화·뒤로가기·빈/실패/일부 실패(DB 값 일시 변경 후 복구)·대회 선택창 스크롤, 자정 전환·임박 폴링은 브라우저 시계 조작으로 확인. **미검증:** 실제 진행 경기 실시간 갱신, 실제 자정 경과.
- **검사:** 백엔드 ruff·pytest 185 통과(DB 포함)·alembic check, 프런트 lint·tsc·build·`git diff --check` 통과. 외부 호출 누적 API-Football 57회, 네이버 40회, 언론사 원문 확인 약 13회(교차 검증 보완 단계는 0회).

## 2026-11-02 (월) — TOP 5 재시도·공개 UI 정책 개정

- 00:00 첫 시도·실패 시 00:05 자동 재시도 1회, 재실패 후 지연 안내·운영 알림·수동 복구로 확정했다. 새 결과 공개 전 지난주 결과를 실제 기간으로 유지한다. 사용자 UI는 목록·경기 일정 없음·지연 안내의 3종이다.
- PRD·기능 명세·유저 플로우·와이어프레임·개발 가이드를 최신화했다. [정책](../../docs/TOP5_POLICY_2026-11-01.md)을 우선한다. 아래 기존 7가지 상태·현재 주 pending 고정 반환은 실제 코드 이력이며 신규 정책 구현 완료를 뜻하지 않는다.
- 실제 앱·Figma·주간 작업·재시도·운영 알림은 이번 범위에서 실행/수정하지 않았다. 04 및 관련 UI의 후속 구현·통합 검증 대상이다.

## 2026-11-02 (월) — 일정 탐색 정책·와이어프레임 개정

- 사용자 승인에 따라 대회 직접 단일 선택·보조 다중 선택, 메인 팀 검색/관심 팀 선택 시 오늘 포함 14일 모아 보기로 확정했다. 검색 해제는 이전 날짜·막대 위치와 현재 대회 복귀, 전체 초기화는 오늘·전체·팀 없음이다.
- PRD·기능 명세·유저 플로우(그림 4 포함)·와이어프레임·개발 가이드를 반영했다. [확정 정책](../../docs/SCHEDULE_UX_POLICY_2026-11-02.md)과 [검수](../../wireframe/SCHEDULE_UX_REVIEW_2026-11-02.md)를 우선한다.
- 이 단계는 문서·와이어프레임 작업이었고, 실제 앱 반영은 위 03 항목에서 완료했다.

## 2026-11-02 (월) — 01 재검수

브랜치 `feat/01-header-footer`에 커밋·push 후 `dev` 병합. Codex 교차 검증 2회(1차 보완 필요 → 재검증 통과).

| 영역 | 변경 파일·함수 | 이유 |
| --- | --- | --- |
| TOP 5 응답 | `backend/app/schemas/top_matches.py`(`TopMatches`·`TopMatchItem`·`TopMatchesWeek`·`TopMatchesState`), `backend/app/services/top_matches.py`(`current_kst_week`, `get_current_top_matches`), `routes/top_matches.py`, `tests/test_api_foundation.py`, `frontend/src/lib/api/schema.d.ts`·`types.ts` | 2026-11-01 AI 주간 정책 계약(`week`·`state`·`selectedAt`·`items[rank·reason·match]`)으로 교체, 평균 평점·평가 수·`period` 제거. 04 전까지 현재 KST 주 `pending`·빈 목록 |
| TOP 5 화면 | `frontend/src/features/top5/model.ts`(새 파일), `Top5Strip.tsx`, `Top5List.tsx`, `queries.ts`, `src/app/globals.css`(헤더 높이 146/154px) | Figma `159:923`·`159:924` 7가지 상태, 선정 이유·주간·선정 시각·현재 상태·변경 일시·VS/—·정책 안내, `168:348` 열기·닫기·포커스 규칙(첫 포커스 닫기, Tab 순환, 배경 inert, 포커스 복귀) |
| 공통 UI | `Dialog.tsx`(compact 시트: 헤더 아래까지·시트 전체 스크롤 없음·`initialFocus`·`id`), `Badge.tsx`(accent 톤, 12px), `Icon.tsx`, `lib/format/kst.ts`(요일 포함 일시·선정 시각·주간 표기) | 새 TOP 5 디자인 반영 |
| 삭제 | `Tabs.tsx`·`Dropdown.tsx`·`Pagination.tsx`, `public/icons/chevron-right.svg`, Badge `info`·`error` 톤·크기 옵션, TOP 5 평점·엠블럼·PK 표시와 43px 띠 클릭 영역 확장 | 01 화면과 §3.1 사전 작업에서 쓰지 않음(§4 작업 원칙 5) |

- **실제 실행 검수:** 1280·375·320에서 헤더 고정·메뉴 이동·모바일 메뉴·푸터·404, TOP 5 7가지 상태(임시 응답 교체로 확인 후 삭제)·열기/닫기·키보드, 의견 실제 제출 2건(DB `feedback` id 96·97 저장, 디스코드 전송 실패 경고 없음)·빈 본문·1,000자 초과·유형 없음·중복·요청 제한·서버 중단 시 입력 유지.
- **Codex 1차 지적 보완:** 모바일 시트 이중 스크롤(`<dialog>`가 스크롤 높이를 더 크게 보고 → compact는 시트 전체 스크롤 차단), 데스크톱 패널 좌우 여백 바깥 클릭, Badge 미사용 크기 옵션, 파일 끝 빈 줄.
- **후속 결정(guide §10.3):** D-01-10 TOP 5 변경 일시(선정 당시 킥오프 필드 추가 여부, 04), D-01-11 320px 띠 문구 말줄임.
- **검사:** 백엔드 ruff·pytest 90 통과·2 건너뜀·alembic check, 프런트 lint·tsc·기본 Turbopack build·`git diff --check` 통과. 외부 호출 API-Football 0회, 디스코드 2회.

## 2026-11-01 (일) — TOP 5 기획·와이어프레임 변경

- 사용자 확정에 따라 월요일 00:00(KST) 1회 AI 선정·해당 주 예정 경기 후보·한 주 ID/순서/이유 고정으로 변경했다. 선정 이유·AI 안내·후보 없음/준비/수집 실패/AI 실패를 문서 3개와 와이어프레임에 반영했다.
- 최신 [정책](../../docs/TOP5_POLICY_2026-11-01.md)을 개발 가이드 P-05·P-06·수집 주기·응답 계약 인계에 반영했다. 아래 10/31의 ‘항상 표시’·평점/평가 수 계약은 당시 구현 이력이다.

## 2026-10-31 (토) — 01 헤더·푸터 + 공통 기반

브랜치 `feat/01-header-footer`(최신 `dev`에서 분기). 커밋 10개, 원격 기능 브랜치에 push. `dev` 병합과 Codex 교차 검증은 하지 않았다.

### A. 백엔드 기반

| 영역 | 변경 파일·함수 | 이유 |
| --- | --- | --- |
| DB 도입 | `backend/app/db/base.py`(`Base`, 제약 이름 규칙), `backend/app/db/session.py`(`sqlalchemy_url`, `connect_args`, `get_engine`, `get_sessionmaker`, `get_db`) | SQLAlchemy 2.1.6 도입. 기존 `verify-full` TLS·CA 인증서를 그대로 사용, 엔진은 지연 생성해 테스트·임포트가 DB 설정에 의존하지 않게 함 |
| 마이그레이션 | `backend/alembic.ini`, `backend/migrations/env.py`, `script.py.mako`, `versions/20261031_0001_sync_runs_feedback.py`, `versions/20261031_0002_feedback_body_hash.py` | Alembic 1.20.1 도입. `sync_runs`·`feedback` 생성(RLS 활성화·정책 없음, `feedback.user_id`는 외래 키 없음), 중복 판정용 `feedback.body_hash` 추가 |
| 모델 | `backend/app/models/feedback.py`(`Feedback`), `backend/app/models/sync_run.py`(`SyncRun`) | 위 테이블의 ORM 정의 |
| 응답·오류 형식 | `backend/app/schemas/common.py`(`ApiModel`, `DataResponse`, `ErrorResponse`), `backend/app/api/errors.py`(`ApiError`, `register_exception_handlers`) | camelCase JSON, `{data, meta}`·`{error}` 형식 통일. 내부 예외·SQL·입력값은 응답·로그에 노출하지 않음 |
| 공통 의존성 | `backend/app/api/deps.py`(`require_csrf`, `RateLimit`), `backend/app/core/rate_limit.py`(`RateLimiter`, `client_ip`) | 변경 요청 CSRF 헤더·Origin 검사, 메모리 기반 요청 제한(클라이언트별 + 전역 상한), 신뢰 프록시 뒤에서만 `X-Forwarded-For` 사용 |
| 라우터 | `backend/app/api/router.py`, `backend/app/main.py` | `/api/v1` 라우터와 예외 처리기 등록, `SCHEDULER_ENABLED`일 때만 스케줄러 시작 |
| 공통 경기 스키마 | `backend/app/schemas/match.py`(`TeamRef`, `CompetitionRef`, `MatchScore`, `MatchSummary`) | 03·04가 채울 경기 요약 계약을 먼저 정의 |
| TOP 5 | `backend/app/schemas/top_matches.py`, `backend/app/services/top_matches.py`(`get_current_top_matches`), `backend/app/api/routes/top_matches.py` | `GET /api/v1/top-matches/current` 계약(현재 `period: null, items: []`). 항목에 평균 평점·평가 수 포함 |
| 의견 접수 | `backend/app/schemas/feedback.py`(`FeedbackCreate`), `backend/app/services/feedback.py`(`create_feedback`, `body_hash`, `is_duplicate`), `backend/app/api/routes/feedback.py`(`submit_feedback`) | `POST /api/v1/feedback`. 본문·유형 필수, 허니팟, 24시간 중복 본문 차단, IP별 분당 3회·일 20회 + 전체 분당 20회·일 300회 |
| 디스코드 알림 | `backend/app/notifications/discord.py`(`notify_feedback`, `build_payload`), `backend/app/config.py`(`feedback_discord_webhook_url`) | 의견 저장 후 디스코드 채널 알림(백그라운드, 실패해도 저장 유지, 멘션 차단, 로그에서 웹후크 토큰 가림) |
| 외부 API 클라이언트 | `backend/app/providers/api_football.py`(`ApiFootballClient`, `MinuteRateLimiter`, `DailyBudget`) | 분당 제한·일일 예산·`errors` 실패 처리·재시도 2회·인증/쿼터 오류 시 중단·키 비노출. 실제 호출 0회 |
| 수집 실행기 | `backend/app/sync/registry.py`(`register_job`, `JobContext`), `runner.py`(`run_job`, `pg_advisory_lock`), `scheduler.py`, `__main__.py`, `jobs.py` | CLI·advisory lock·`sync_runs` 기록. 등록된 작업은 아직 없음 |
| 설정 | `backend/app/config.py`, `backend/pyproject.toml`, `backend/uv.lock` | 신뢰 프록시·스케줄러·API-Football 한도·웹후크 설정 추가, SQLAlchemy·Alembic·APScheduler 정확한 버전 고정 |

### B. 프런트엔드 기반

| 영역 | 변경 파일·함수 | 이유 |
| --- | --- | --- |
| 프록시 | `frontend/next.config.ts` | `/api/*`를 `BACKEND_ORIGIN`으로 rewrites. 로컬 `.env.local`의 `NEXT_PUBLIC_API_BASE_URL`을 `BACKEND_ORIGIN`으로 교체(커밋 대상 아님) |
| API 계층 | `frontend/src/lib/api/client.ts`(`apiFetch`, `setUnauthorizedHandler`), `errors.ts`(`ApiError`, `toApiError`), `types.ts`, `query-keys.ts`, `schema.d.ts`(생성), `frontend/scripts/gen-api.mjs` | 같은 출처 요청, 오류 변환, 변경 요청 CSRF 헤더 자동, 401 갱신 연결 자리, OpenAPI 생성 타입(`npm run gen:api`) |
| 상태·포맷 | `frontend/src/app/providers.tsx`, `frontend/src/lib/format/kst.ts`, `frontend/src/lib/hooks/useMediaQuery.ts` | TanStack Query 5.105.0 Provider, KST 날짜·시각 포맷, 1024px 기준 화면 판별 |
| 디자인 토큰·글꼴 | `frontend/src/app/globals.css`, `frontend/src/app/layout.tsx` | Figma 컬러 가이드 토큰·글자 크기·반경·`kt-container`, `lang="ko"`, Noto Sans KR·Inter(워드마크), 메타데이터 |
| 공통 UI | `frontend/src/components/ui/`(`Button`·`ButtonLink`·`IconButton`, `Badge`, `Dialog`·`BottomSheet`, `Tooltip`, `Tabs`·`TabPanel`, `Dropdown`, `Pagination`, `Skeleton`, `DataState`·`StateMessage`, `Icon`, `cx`) | 전 채팅 재사용용 기본 컴포넌트. `DataState`는 로딩·정상·빈 결과·일부 미제공·실패·권한 거부 구분 |
| 이미지 | `frontend/src/components/common/TeamCrest.tsx`(`TeamCrest`, `PlayerPhoto`), `Logo.tsx`, `frontend/public/brand/symbol.svg`, `public/placeholder.svg`, `public/icons/*.svg`, `src/app/icon.svg` | Figma 55:22·55:26 에셋과 아이콘, 파비콘 교체, 이미지 없음·로드 실패 시 대체 이미지 |
| 기본 파일 정리 | `frontend/src/app/page.tsx`, `src/app/not-found.tsx`, 삭제: `public/next.svg`·`public/vercel.svg`·`src/app/favicon.ico` | create-next-app 시작 화면 제거, 메인은 자리 표시, 아직 없는 메뉴 경로는 404 안내 |

### C. 전역 화면

| 영역 | 변경 파일·함수 | 이유 |
| --- | --- | --- |
| 헤더 | `frontend/src/components/layout/SiteHeader.tsx`, `MainNav.tsx`, `MobileMenu.tsx`, `HeaderAuth.tsx`, `nav.ts` | 고정 헤더(로고·메뉴 4개·로그인 ghost·회원가입 primary, 12px 간격), 모바일 메뉴 하단 시트, 인증 영역은 02가 교체할 경계로 분리 |
| TOP 5 띠 | `frontend/src/features/top5/Top5Strip.tsx`, `Top5List.tsx`, `queries.ts` | 헤더와 함께 고정, 데스크톱 전체 폭 펼침 패널 + 배경 딤, 모바일 하단 시트, 빈 상태·조회 실패·로딩 |
| 푸터 | `frontend/src/components/layout/SiteFooter.tsx`, `frontend/src/lib/site.ts` | Figma 리디자인(49:532·49:1012) 반영, 운영자 정보는 설정값(`SITE_OPERATOR_*`) 자리 |
| 의견 보내기 | `frontend/src/features/feedback/FeedbackProvider.tsx`, `FeedbackButton.tsx`, `FeedbackDialog.tsx`, `draft.ts`, `frontend/src/components/layout/MobileBottomBar.tsx` | 데스크톱 푸터·모바일 하단 고정 진입, 유형·본문 필수, 빈 본문·실패·중복·요청 제한·성공 상태, 실패 시 입력 유지, 초안 sessionStorage 보존, 허니팟 입력칸 |

### 결정·변경 사항(사용자 결정 포함)

- 의견 유형을 선택 → 필수로 변경, 의견은 디스코드로 알림, 남용 방지로 허니팟·중복 본문 차단·전역 상한 적용, 회원·비회원 차등 제한은 02에서 적용.
- `X-Forwarded-For` 위조 대응: 배포 시 앞단 프록시 설정(가이드 §10.2 C-08), 코드에는 전역 상한.
- TOP 5는 항상 표시가 원칙(LLM 자동 선정 포함), 선정 기능은 04에서 진행.
- Figma 갱신 반영: 푸터 리디자인, TOP 5 펼침(128:3145~128:4408), 계정 버튼(133:4077·133:4134). 가이드의 brand 토큰 값을 Figma 값으로 정정.

### 검증 결과

- 백엔드: `uv run ruff check .` 통과, `uv run python -m pytest` 72개 통과·1개 건너뜀(DB 연동 테스트는 `KICKTAB_DB_TESTS=1`로 별도 실행해 6개 통과, 항상 롤백), `alembic check` 모델·마이그레이션 일치.
- 개발 DB: `0001`·`0002` 적용, 각각 downgrade·upgrade 재확인. 현재 리비전 `0002_feedback_body_hash`. `feedback`에는 사용자가 디스코드 연동 확인 중 보낸 행이 있음, `sync_runs` 0행.
- 프런트엔드: `npm run lint`·`npm run build` 통과, `npm run gen:api` 결과가 실행 중 백엔드와 일치.
- 브라우저: 데스크톱 1920px·모바일 375px를 Figma와 측정 비교(헤더 129/113px, 푸터 147px, TOP 5 패널 1280px 등), 모달·시트의 Escape·포커스 복귀, 의견 실패·성공·중복·유형 미선택 상태 확인.
- 외부 호출: API-Football 0회. 디스코드 웹후크는 사용자가 직접 연동해 수신 확인.

## 2026-11-01 (일) — 01 Codex 교차 검증 보완

Codex 교차 검증 결과(치명 0·높음 1·중간 7·낮음 3)를 재현 또는 코드 근거로 확인한 뒤 보완했다. 오탐은 없었다(3번은 잠금 부재를 코드로 확인하고 잠금 순서·DB 대기 테스트로 검증, 11번은 문서 대조). 브랜치 `feat/01-header-footer`, 보완 커밋은 로컬만(push·`dev` 병합 전). Codex 재검증 전.

| # | 영역 | 변경 파일·함수 | 이유·결과 |
| --- | --- | --- | --- |
| 1 | 서버 로그 원문 노출(높음) | `backend/app/api/errors.py`(`UnhandledErrorMiddleware`, `register_exception_handlers`), `backend/app/main.py` | Starlette가 500 처리 후 예외를 다시 던져 Uvicorn이 traceback(메시지 포함)을 기록하던 문제. 미들웨어가 공통 500 응답 후 종류만 기록. 실제 Uvicorn 서버로 회귀 검사(`tests/test_server_logging.py`) |
| 2 | 이전 전송 성공이 새 초안 삭제 | `frontend/src/features/feedback/FeedbackDialog.tsx`(세션 번호·`Submission`), `draft.ts`(`sameDraft`) | 열고 닫을 때마다 세션을 구분해 지난 요청 결과가 새 초안·화면을 바꾸지 않게 함. 닫힌 채 같은 초안이면만 정리. 전송 중 입력 잠금 |
| 3 | 동시 요청 중복 우회 | `backend/app/services/feedback.py`(`duplicate_lock_key`, `lock_body_hash`) | 본문 해시별 `pg_advisory_xact_lock`으로 조회~저장 직렬화. 스키마 변경 없음. 개발 DB 동시 잠금 테스트(롤백) |
| 4 | 잘못된 JSON 미집계 | `backend/app/api/deps.py`(`RateLimit.route_class`), `backend/app/api/routes/feedback.py` | 요청 제한을 본문 해석 전(라우트 클래스)에 적용 |
| 5 | 비JSON 401·403·429 후 재호출 | `backend/app/providers/api_football.py`(`_parse`, `STOP_STATUSES`) | 상태 코드 중단 처리를 JSON 해석보다 먼저 |
| 6 | TOP 5 자동 갱신 없음 | `frontend/src/features/top5/queries.ts`, `Top5Strip.tsx` | 화면이 보일 때 30분 주기, 5분 지나면 창 포커스·펼칠 때 재조회 |
| 7 | 전역 거부 요청의 버킷 증가 | `backend/app/core/rate_limit.py`(`check`·`record`, LRU 정리, 최대 10,000키), `backend/app/api/deps.py` | 두 한도 모두 통과한 요청만 집계, 정리 비용 상각 O(1) |
| 8 | 모바일 TOP 5 터치 27px | `frontend/src/features/top5/Top5Strip.tsx` | 띠 높이 유지, 실제 클릭 영역 45px(`before:` 확장) |
| 9 | Tooltip 첫 클릭 닫힘 | `frontend/src/components/ui/Tooltip.tsx` | 실제 클릭으로 재현. 포인터 종류별 처리(마우스 유지·터치 토글·키보드 포커스) |
| 10 | 초안 저장 실패 안내 없음 | `draft.ts`(`saveDraft` 반환값), `FeedbackDialog.tsx` | 저장 불가 시 안내 1회 표시, 제출은 유지 |
| 11 | 확정 제한값 미확정 표기 | `backend/app/api/routes/feedback.py` 주석, `docs/guide.md` §8 | 01 적용값을 확정으로 통일, 02 차등값·보존 기간만 미확정 |

### 검증 결과

- 백엔드: `ruff` 통과, `pytest` 86 통과·2 건너뜀(DB 연동 7개는 `KICKTAB_DB_TESTS=1`로 별도 통과, 롤백), `alembic current` = `0002_feedback_body_hash`(head), `alembic check` 차이 없음.
- 프런트엔드: `npm run lint` 통과, 기본 `npm run build`(Turbopack) `.next` 삭제 후 통과. Codex 환경의 Turbopack 실패는 샌드박스 프로세스·로컬 연결 제한으로 추정(가이드 §7).
- 브라우저: 2·6·8·9·10번 재현 후 수정 확인, 1920·375px 회귀(헤더 129/113px, 푸터 147px, 버튼 간격 12px, TOP 5 패널 1280px, Escape·포커스 복귀) 유지.
- `npm audit`: moderate 18건 모두 개발 도구의 `minimatch` 경로(01 추가분 2건), 수정 미적용(가이드 §7).
- 외부 호출 0회, 디스코드 전송 0회(화면 확인은 fetch 가로채기), 영구 DB 저장 0건(feedback 2행·sync_runs 0행 유지).

### Codex 재검증 후 최종 보완 (2026-11-01)

Codex 재검증 결과: 기존 11건 중 10건 해결·1건(Tooltip) 부분 해결, 낮은 심각도 2건 추가. 두 건 모두 재현 후 보완했다. Codex 최종 재검증 전.

| 항목 | 변경 파일·함수 | 재현 → 검증 |
| --- | --- | --- |
| A. `RateLimiter.hit()` 검사·기록 비원자 | `backend/app/core/rate_limit.py`(`hit`, `_check_locked`, `_record_locked`) | 분당 1회 제한·8개 스레드 동시 `hit()`에서 여러 건 허용을 재현. 수정 후 1건만 허용(5회 반복), `RateLimit` 경로 동시성 테스트 추가(`tests/test_rate_limit.py`) |
| B. Tooltip 포인터 상태 잔류 | `frontend/src/components/ui/Tooltip.tsx`(`onPointerDown`의 바깥 놓기 처리, `onPointerCancel`, `onBlur`) | 실제 브라우저에서 누른 채 바깥에서 놓은 뒤 Tab 포커스가 열리지 않는 것을 재현. 수정 후 실제 입력으로 키보드 포커스·Enter·Space·Escape·포커스 이탈·마우스 첫 클릭 유지·바깥 클릭 닫힘 확인, pointercancel·터치/펜 탭은 이벤트 모의로 확인. 확인용 임시 페이지는 삭제 |

- 검증: 백엔드 `ruff` 통과·`pytest` 88 통과·2 건너뜀, 프런트 `lint` 통과·기본 `npm run build`(Turbopack) 통과, `git diff --check` 통과.
- 외부 호출 0회, 디스코드 전송 0회, 영구 DB 저장 0건(이번 보완은 DB를 쓰지 않음).

### 01 마무리 정리 (2026-11-01)

- **판정:** Codex가 로컬 `c3ad860` 기준으로 01(헤더·푸터 + 공통 기반) 완료·`dev` 병합 가능으로 판정했다(백엔드 ruff·pytest 88 통과·2 건너뜀, 프런트 lint·기본 Turbopack build 통과).
- **판정 정정(사용자 결정):** 현재 쓰이지 않는 `Tooltip`의 잔여 지적은 01 완료·병합의 필수 보완 항목에서 철회했다. 미사용 컴포넌트를 반복 보완 대상으로 넓힌 검증 방향을 바로잡은 것이다.
- **삭제:** `frontend/src/components/ui/Tooltip.tsx`(다른 import·사용처 없음 확인). 위 표의 Tooltip 관련 이력은 당시 작업 기록으로 보존한다.
- **문서 정정:** "04 후기 주의사항 등에서 Tooltip 사용 예정"은 잘못된 설명이었다. 후기 작성 주의사항은 화면에 보이는 UI로 제공하는 것이 사용자 기준이며, guide·file-feature-map에서 Tooltip 목록·포인터 규칙·예정 사용처를 제거했다.
- **일괄 검수로 이동:** 터치·펜 실기기·스크린리더 검사는 전체 제작 후 최종 검수에서 일괄 진행한다(guide §4).
- **검증:** 이번 정리는 Codex 재검증 대상이 아니다. 프런트 `npm run lint`·`npm run build`(기본 Turbopack), 잔여 참조 검색, `git diff --check`만 확인했다. 백엔드는 변경이 없어 다시 실행하지 않았다.
