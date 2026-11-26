# KickTab 파일별 기능 지도

어느 폴더가 무슨 일을 하고, 그 안의 파일이 각각 어떤 기능을 맡는지 한눈에 보기 위한 문서다.

**쓰는 법**
- 파일을 새로 만들거나, 지우거나, 역할이 바뀌었을 때만 고친다.
- 변경 날짜·담당 채팅·검수 이력은 쓰지 않는다. 그것은 `daily-work-log.md`와 커밋에 남긴다.
- 설명은 "무엇을 하는 파일인지" 한 줄로 쓴다. 세부 규칙은 코드 주석과 `guide.md`를 본다.

## 전체 구조

```text
apps/
├─ backend/        FastAPI 서버 — API, DB, 외부 데이터 수집, TOP 5 AI 선정
│  ├─ app/
│  │  ├─ api/          HTTP 입구: 라우터, 인증 쿠키, CSRF·요청 제한, 오류 형식
│  │  ├─ models/       DB 표 정의(SQLAlchemy)
│  │  ├─ schemas/      API 요청·응답 형식(Pydantic, camelCase)
│  │  ├─ services/     기능별 업무 규칙(조회·저장·판정)
│  │  ├─ sync/         정기 수집 작업과 실행기·스케줄러
│  │  ├─ providers/    외부 API 클라이언트(API-Football·네이버·Gemini)
│  │  ├─ notifications/ 디스코드 알림
│  │  ├─ seed/         고정 기준 데이터(대회·팀 별칭·국가·TOP 5 기준)
│  │  ├─ core/         시간대·잠금·요청 제한 같은 공용 도구
│  │  └─ db/           DB 연결·세션
│  ├─ migrations/   DB 구조 변경 이력(Alembic)
│  └─ tests/        백엔드 테스트(DB 연동 테스트는 KICKTAB_DB_TESTS=1일 때만)
├─ frontend/       Next.js 화면
│  ├─ src/app/        페이지 경로(URL 하나 = 폴더 하나)
│  ├─ src/components/ 여러 화면이 함께 쓰는 UI(ui: 기본 부품, common: 축구 공용 부품, layout: 헤더·푸터)
│  ├─ src/features/   기능별 화면과 상태(기능 하나 = 폴더 하나)
│  ├─ src/lib/        API 호출·표기 형식·공용 훅
│  ├─ public/         아이콘·로고·대체 이미지
│  └─ tests/          프런트 테스트(Node 테스트 실행기)
└─ docs/           작업 문서(가이드·일별 작업 내역·이 문서)
   └─ legal/       약관 관련 문서(이용약관·처리방침·동의 문구·개인정보 처리 목록)
```

## 화면별 빠른 찾기

한 화면을 고칠 때 함께 볼 파일이다. 프런트 경로는 `frontend/src/`, 백엔드 경로는 `backend/app/` 기준이다.

| 화면 | 프런트 | API 라우트 | 서비스 | 수집 작업 |
| --- | --- | --- | --- | --- |
| 메인 경기 일정 `/` | `features/schedule/`, `features/favorites/`, `features/news/`, `features/standings/MainStandings.tsx` | `routes/schedule.py`, `routes/standings.py` | `services/fixtures.py`, `news.py`, `standings.py` | `sync/fixtures.py`, `news.py`, `standings.py` |
| TOP 5 띠 | `features/top5/` | `routes/top_matches.py` | `services/top_matches.py`, `top5_selection.py` | `sync/top5.py` |
| 경기 상세 `/matches/[id]` | `features/match/` | `routes/matches.py`, `routes/reviews.py` | `services/match_detail.py`, `head_to_head.py`, `reviews.py` | `sync/fixtures.py`(진행 중·종료 기록) |
| 지난 경기 `/results` | `features/results/` | `routes/results.py` | `services/results.py` | `sync/fixtures.py`(시즌 전체) |
| 리그 순위 `/standings` | `features/standings/` | `routes/standings.py` | `services/standings.py`, `knockouts.py` | `sync/standings.py` |
| 팀 탐색 `/teams` | `features/teams/` | `routes/teams.py` | `services/team_browse.py`, `team_search.py` | `sync/reference.py` |
| 팀 상세 `/teams/[id]` | `features/team-detail/` | `routes/teams.py` | `services/team_detail.py` | `sync/team_detail.py` |
| 로그인·회원가입·비밀번호 찾기 | `features/auth/` | `routes/auth.py`, `api/auth.py` | `services/accounts.py`, `auth_security.py`, `mailer.py` | `sync/retention.py`(보관 기간 정리) |
| 마이페이지 `/mypage` | `features/mypage/` | `routes/me.py`, `routes/reviews.py` | `services/accounts.py`, `member_favorites.py`, `reviews.py` | — |
| 의견 보내기(푸터) | `features/feedback/` | `routes/feedback.py` | `services/feedback.py`, `notifications/discord.py` | — |
| 헤더·푸터·공통 UI | `components/layout/`, `components/ui/`, `components/common/` | — | — | — |

## 백엔드 `backend/`

### 설정·실행

| 파일 | 기능 |
| --- | --- |
| `pyproject.toml`, `uv.lock` | 의존성과 ruff·pytest 설정, 잠금 파일 |
| `.python-version`, `.gitignore` | Python 3.12 지정, 백엔드 커밋 제외 목록 |
| `alembic.ini` | 마이그레이션 설정(접속 주소는 `.env`에서 읽음) |
| `certs/supabase-ca.crt` | Supabase TLS 검증용 공개 CA 인증서 |
| `app/main.py` | FastAPI 앱 생성, 오류 처리·CORS·`/api/v1` 라우터·`/health`, 스케줄러 시작·종료 |
| `app/config.py` | 환경 변수 설정(`.env`) — CORS, 스케줄러, API 한도, 현재 시즌, 비밀 값, TOP 5 모델 |
| `app/database.py`, `app/check_database.py` | psycopg 직접 연결(검증 TLS), `python -m app.check_database` 연결 확인 |
| `app/moderation.py` | 운영 명령 `python -m app.moderation` — 평가 작성 제한 설정·해제, 계정 해지 |

### `app/core/` 공용 도구

| 파일 | 기능 |
| --- | --- |
| `kst.py` | 한국 시간(KST) 오늘·날짜 계산 |
| `locks.py` | 같은 보충 조회를 한 번으로 합치는 잠금(`single_flight`) |
| `rate_limit.py` | 요청 횟수 제한기(분·일 단위), 신뢰 프록시 기준 클라이언트 IP |

### `app/db/` DB 연결

| 파일 | 기능 |
| --- | --- |
| `base.py` | 모델 공통 `Base`, 제약 이름 규칙 |
| `session.py` | 엔진·세션 생성, 요청마다 세션을 주는 `get_db` |

### `app/api/` HTTP 입구

| 파일 | 기능 |
| --- | --- |
| `router.py` | `/api/v1` 라우터 묶음, 모든 변경 요청에 CSRF 검사 |
| `deps.py` | CSRF(헤더·Origin) 검사, 클라이언트별·전체 요청 제한 `RateLimit` |
| `auth.py` | 로그인 쿠키(`kt_access`·`kt_refresh`) 읽기·쓰기, 현재 회원 확인 |
| `errors.py` | 공통 오류 형식, 예외 처리기(미처리 예외는 500, 로그에 내용 미노출) |

### `app/api/routes/` API 목록

| 파일 | 기능 |
| --- | --- |
| `schedule.py` | 대회·시즌 목록, 날짜별 경기, 관심 팀 경기, 팀 일정, 팀 검색, 뉴스, 뉴스 원문 확인 |
| `matches.py` | 경기 정보·상세 기록·상대 전적·평가 목록·평가 작성 |
| `results.py` | 지난 경기(시즌·대회·팀·페이지) |
| `standings.py` | 리그 순위, 메인 간소 순위, 선수 순위, UEFA 토너먼트 대진 |
| `teams.py` | 팀 탐색 목록, 팀 상세(개요·경기·선수단·시즌 기록·이적) |
| `top_matches.py` | 이번 주 TOP 5 공개 결과·공개 버전 |
| `auth.py` | 인증번호 발송·확인, 가입, 로그인·갱신·로그아웃, 비밀번호 찾기, 세션 확인 |
| `me.py` | 회원 관심 팀, 내 평가, 비밀번호 변경, 회원 탈퇴 |
| `reviews.py` | 평가 수정·삭제, 좋아요·싫어요 |
| `feedback.py` | 의견 보내기(요청 제한·허니팟·중복 거부) |

### `app/models/` DB 표

| 파일 | 기능 |
| --- | --- |
| `reference.py` | 대회·대회 시즌·팀·대회 참가·팀 별칭 |
| `fixture.py` | 경기(킥오프·상태·스코어) |
| `match_detail.py` | 경기 상세 기록(통계·라인업·선수), 이벤트, 상대 전적, 팀 최근 경기 |
| `standings.py` | 리그 순위, 선수, 선수 순위, 선수 시즌 기록, 리그 수집 상태 |
| `team_detail.py` | 감독, 선수단, 팀 시즌 기록, 팀 선수 기록, 이적, 팀 수집 상태 |
| `news.py` | 뉴스 기사와 팀 연결 |
| `review.py` | 경기 평가, 평가 반응 |
| `user.py` | 회원, 인증번호, 갱신 토큰, 약관 확인 기록, 회원 관심 팀 |
| `top_matches.py` | TOP 5 주간 상태·선정 시도·공개 버전·주간 결과 |
| `feedback.py` | 의견 |
| `sync_run.py` | 수집 작업 실행 기록 |
| `__init__.py` | 모든 모델 import(마이그레이션 인식용) |

### `app/schemas/` API 형식

| 파일 | 기능 |
| --- | --- |
| `common.py` | 공통 응답 `{ data, meta }`·오류 형식, camelCase 변환 |
| `match.py` | 경기 요약·팀·대회·스코어 공통 형식 |
| `schedule.py` | 대회·시즌·일정·지난 경기·뉴스 응답 |
| `match_detail.py` | 경기 상세 블록·상대 전적·평가 응답 |
| `standings.py` | 순위·선수 순위·대진 응답 |
| `teams.py`, `team_detail.py` | 팀 탐색, 팀 상세 응답 |
| `top_matches.py` | TOP 5 응답 |
| `auth.py` | 인증·가입·로그인·비밀번호 요청과 회원 응답 |
| `feedback.py` | 의견 요청·접수 응답 |

### `app/services/` 업무 규칙

| 파일 | 기능 |
| --- | --- |
| `reference.py` | 대회·팀·참가 저장, 별칭 시드 적용, 팀 상세 제공 여부 |
| `fixtures.py` | 경기 저장, 날짜별·관심 팀·팀 일정 조회, 공통 경기일 기간 |
| `match_status.py` | 제공사 경기 상태를 서비스 상태로 변환 |
| `match_detail.py` | 경기 상세 기록 저장·조회, 요청 시 1회 보충 |
| `head_to_head.py` | 상대 전적·최근 경기 흐름 조회·보충 |
| `results.py` | 지원 시즌, 시즌 적재 상태, 지난 경기 조회 |
| `standings.py` | 순위·선수 순위 파싱과 조회, 선방 자체 집계, 순위 구간 |
| `knockouts.py` | UEFA 토너먼트 단계별 대진 구성 |
| `team_search.py` | 팀 이름·별칭 검색 |
| `team_browse.py` | 팀 탐색 목록(현재 시즌 5대 리그 팀) |
| `team_detail.py` | 팀 상세 파싱·저장·조회, 선수단 합계, 이적 정리·주요 이동 판정 |
| `news.py`, `news_classify.py` | 뉴스 조회, 규칙 기반 대회·팀 분류와 설명 정리 |
| `news_link.py` | 뉴스 원문 주소가 살아 있는지 확인(공개 주소만) |
| `reviews.py` | 평가 목록·작성 가능 판정·작성·반응 |
| `accounts.py` | 인증번호, 가입, 로그인·세션 회전, 비밀번호 찾기·변경, 탈퇴 |
| `auth_security.py` | 비밀번호 해시, 접근 토큰, 인증번호 해시, 닉네임·비밀번호 규칙·금칙어 |
| `mailer.py` | 인증번호 메일 발송(Gmail SMTP) |
| `member_favorites.py` | 회원 관심 팀 조회·등록(10팀)·해제 |
| `moderation.py` | 평가 작성 제한 설정·해제 |
| `retention.py` | 보관 기간이 지난 인증·세션·의견 기록 정리 |
| `feedback.py` | 의견 저장, 중복 확인 |
| `top_matches.py` | TOP 5 공개 결과 선택, 공개 버전 |
| `top5_selection.py` | TOP 5 주간 선정(후보·근거 수집, Gemini 요청, 검증, 게시) |

### `app/sync/` 정기 수집

| 파일 | 기능 |
| --- | --- |
| `registry.py`, `runner.py` | 작업 등록, 실행(잠금·`sync_runs` 기록·일부 실패 요약) |
| `scheduler.py` | 자동 실행 일정(`SCHEDULER_ENABLED`일 때 한 서버에서만) |
| `__main__.py`, `jobs.py` | 수동 실행 명령 `python -m app.sync <작업>`, 작업 모듈 모음 |
| `reference.py` | 대회·팀 기준 데이터, 팀 별칭 |
| `fixtures.py` | 경기 일정(30분), 진행 중 경기(1분), 시즌 전체 경기, 종료 경기 상세 |
| `standings.py` | 리그 순위, 선수 순위, 선수 시즌 기록 |
| `team_detail.py` | 팀 상세(감독·선수단·시즌 기록), 이적, 팀 선수 기록 |
| `news.py` | 네이버 뉴스(매시간), 원문 주소 정규화 |
| `top5.py` | TOP 5 월요일 자동 선정·수동 복구·중단 정리 |
| `retention.py` | 보관 기간 정리 작업 |

### `app/providers/`, `app/notifications/` 외부 연동

| 파일 | 기능 |
| --- | --- |
| `providers/api_football.py` | API-Football 호출(분당·일일 한도, 인증·한도 오류 시 중단) |
| `providers/naver_news.py` | 네이버 뉴스 검색 |
| `providers/gemini.py` | Gemini 구조화 응답 요청 |
| `notifications/discord.py` | 의견 도착·TOP 5 지연 디스코드 알림 |

### `app/seed/` 기준 데이터

| 파일 | 기능 |
| --- | --- |
| `competitions.py` | 지원 대회 21개(한국어 이름·그룹·순서) |
| `team_aliases.json` | 5대 리그 팀 한국어 이름·검색 별칭 |
| `uefa_team_names.json` | UEFA 참가 팀 한국어 이름 |
| `countries.json` | 국가명 → 국기 이미지 |
| `top5_curation.json` | TOP 5 판단 기준(더비·팀 관심도) |

### `migrations/` DB 구조 변경

| 파일 | 기능 |
| --- | --- |
| `env.py`, `script.py.mako` | 마이그레이션 실행 설정, 새 리비전 양식(RLS 활성화 포함) |
| `versions/0001`~`0002` | 수집 기록·의견 |
| `versions/0003`~`0005` | 기준 데이터·경기·뉴스 |
| `versions/0006`~`0008` | 경기 상세·평가·TOP 5 |
| `versions/0009`~`0010` | 경기 수집 범위·시즌 전체 경기 |
| `versions/0011` | 순위·선수 순위 |
| `versions/0012`~`0014` | 팀 상세·이적 고유 키 |
| `versions/0015` | 평가를 텍스트 전용으로 |
| `versions/0016` | 팀 선수 기록 |
| `versions/0017` | 대회 그룹(21개 대회) |
| `versions/0018`, `0021` | 이적 판정용 이전 팀 확인 표 추가 → 삭제 |
| `versions/0019`~`0020` | 회원·인증·관심 팀, 평가 작성 제한 |

### `tests/` 백엔드 테스트

| 파일 | 기능 |
| --- | --- |
| `conftest.py` | 실제 외부 호출 차단 |
| `test_setup.py`, `test_db.py`, `test_server_logging.py` | 설정·DB 연결·모델 구조, 오류 로그 미노출 |
| `test_api_foundation.py`, `test_rate_limit.py` | 응답·오류 형식, CSRF, 요청 제한, 의견 |
| `test_api_football.py`, `test_sync_runner.py`, `test_feedback_notifications.py` | 외부 API 클라이언트, 수집 실행기, 디스코드 알림 |
| `test_schedule_rules.py`, `test_schedule_sources.py`, `test_schedule_db.py` | 경기 일정·뉴스 |
| `test_match_detail.py`, `test_review_window.py`, `test_review_regressions.py` | 경기 상세, 평가 가능 판정, TOP 5·상세 회귀 |
| `test_results_db.py` | 지난 경기 |
| `test_standings.py`, `test_standings_db.py` | 리그 순위·선수 순위 |
| `test_teams_rules.py`, `test_teams_db.py` | 팀 탐색 |
| `test_team_detail.py`, `test_team_detail_db.py` | 팀 상세·이적 |
| `test_top5.py`, `test_top5_db.py` | TOP 5 선정·공개 |
| `test_auth_rules.py`, `test_auth_db.py`, `test_retention_db.py` | 회원·인증, 보관 기간 정리 |

## 프런트엔드 `frontend/`

### 설정

| 파일 | 기능 |
| --- | --- |
| `package.json`, `package-lock.json` | 스크립트(`dev`·`build`·`lint`·`test`·`gen:api`)와 의존성 |
| `next.config.ts` | Next 설정, `/api/*`를 백엔드로 보내는 같은 출처 연결 |
| `scripts/gen-api.mjs` | 백엔드 OpenAPI로 `src/lib/api/schema.d.ts` 생성 |
| `tsconfig.json`, `eslint.config.mjs`, `postcss.config.mjs`, `.gitignore`, `AGENTS.md` | TypeScript·ESLint·Tailwind 설정, 에이전트 안내 |

### `src/app/` 페이지 경로

| 파일 | 기능 |
| --- | --- |
| `layout.tsx`, `providers.tsx`, `globals.css` | 전체 틀(헤더·본문·푸터), 데이터 조회 클라이언트, 색·글자 토큰과 공용 스타일 |
| `page.tsx` | `/` 메인 — 경기 일정·관심 팀·주요 뉴스·리그 순위 |
| `results/page.tsx` | `/results` 지난 경기 |
| `standings/page.tsx` | `/standings` 리그 순위 |
| `teams/page.tsx` | `/teams` 팀 탐색 |
| `teams/[id]/page.tsx` | `/teams/[id]` 팀 상세 |
| `matches/[id]/page.tsx` | `/matches/[id]` 경기 상세 |
| `mypage/page.tsx` | `/mypage` 마이페이지 |
| `login`·`signup`·`password-reset/page.tsx` | 로그인·회원가입·비밀번호 찾기 |
| `news/original/page.tsx` | 뉴스 원문 확인 후 이동 |
| `not-found.tsx`, `favicon.ico` | 없는 주소 안내, 파비콘 |

### `src/components/ui/` 기본 부품

| 파일 | 기능 |
| --- | --- |
| `Button.tsx` | 버튼 4종(주요·보조·텍스트·위험)·링크 버튼·아이콘 버튼 |
| `Dialog.tsx` | 팝업·하단 시트(포커스 가두기·복귀) |
| `DataState.tsx` | 로딩·빈 결과·일부 미제공·실패·다시 확인 상태 표시 |
| `Pagination.tsx` | 페이지 버튼 « ‹ 번호 › » |
| `Tabs.tsx` | 탭 |
| `Badge.tsx`, `chip.tsx` | 배지, 필터 칩 |
| `Icon.tsx`, `Skeleton.tsx`, `cx.ts` | SVG 아이콘, 로딩 자리, 클래스 결합 |

### `src/components/common/` 축구 공용 부품

| 파일 | 기능 |
| --- | --- |
| `MatchCard.tsx`, `MatchStatusBadge.tsx` | 경기 카드, 경기 상태 배지 |
| `TeamCrest.tsx` | 팀 엠블럼·선수 사진(없으면 대체 이미지) |
| `RecentForm.tsx` | 최근 5경기 승무패 |
| `TeamSearch.tsx` | 팀 검색 입력(별칭·후보) |
| `CompetitionFilter.tsx`, `SeasonSelect.tsx` | 대회 선택창, 시즌 선택 |
| `NewsCard.tsx` | 뉴스 카드 |
| `Logo.tsx` | 헤더 로고 |

### `src/components/layout/` 헤더·푸터

| 파일 | 기능 |
| --- | --- |
| `SiteHeader.tsx`, `MainNav.tsx`, `MobileMenu.tsx`, `nav.ts` | 고정 헤더, PC 메뉴, 모바일 메뉴, 메뉴 목록 |
| `HeaderAuth.tsx` | 헤더 로그인·회원가입 / 마이페이지·로그아웃 |
| `HeaderHeight.tsx` | 실제 헤더 높이를 CSS 변수로 동기화 |
| `StickyPanel.tsx` | PC 오른쪽 패널 스크롤 고정 |
| `SiteFooter.tsx` | 푸터(정책 링크·운영자 안내·의견 보내기) |

### `src/features/` 기능별 화면

| 폴더 | 파일 | 기능 |
| --- | --- | --- |
| `schedule/` | `ScheduleSection.tsx`, `DateBar.tsx`, `ScheduleNotice.tsx`, `useScheduleParams.ts`, `queries.ts` | 메인 경기 일정 — 날짜 막대, 대회 필터, 팀 일정, 안내 상자, URL 조건, 조회 |
| `favorites/` | `FavoriteSchedule.tsx` | 메인 관심 팀 패널(팀 칩·가까운 경기) |
| | `FavoriteStar.tsx`, `FavoriteToggle.tsx`, `FavoriteTeamButtons.tsx` | 경기·팀 카드 별, 팀 상세 등록 버튼, 검색 아래 관심 팀 버튼 |
| | `store.ts`, `useFavorites.ts`, `nextMatches.ts` | 비회원(브라우저 5팀)·회원(서버 10팀) 관심 팀 상태, 팀별 다음 경기 선택 |
| `news/` | `MainNews.tsx`, `OriginalRedirect.tsx` | 메인 주요 뉴스, 원문 이동 |
| `top5/` | `Top5Strip.tsx`, `Top5List.tsx`, `model.ts`, `queries.ts` | 헤더 아래 TOP 5 띠와 펼친 목록 |
| `match/` | `MatchDetail.tsx`, `Scoreboard.tsx`, `StatusNotice.tsx` | 경기 상세 조립, 상단 점수판, 연기·중단 안내 |
| | `MatchRecords.tsx`, `HeadToHeadSection.tsx`, `icons.tsx` | 경기 기록 4탭(타임라인·통계·라인업·평점), 상대 전적, 이벤트 아이콘 |
| | `ReviewSection.tsx`, `ReviewComposer.tsx`, `ReviewTextForm.tsx`, `ReviewGuidance.tsx`, `ReviewLoginNotice.tsx`, `ReviewRestriction.tsx` | 경기 평가 목록·작성·입력 폼·주의사항·로그인 안내·작성 제한 |
| | `model.ts`, `queries.ts` | 표기 규칙, 조회 |
| `results/` | `ResultsSection.tsx`, `useResultsParams.ts`, `queries.ts` | 지난 경기 화면, URL 조건, 조회 |
| `standings/` | `StandingsSection.tsx`, `StandingsTable.tsx`, `LeaguePhaseTable.tsx`, `KnockoutStage.tsx`, `PlayerRankings.tsx` | 리그 순위 화면, 리그 순위표, UEFA 리그 페이즈, 토너먼트 대진, 선수 순위 |
| | `MainStandings.tsx`, `ChipRow.tsx`, `StageTabs.tsx` | 메인 간소 순위, 대회 칩 줄, UEFA 단계 탭 |
| | `model.ts`, `useStandingsParams.ts`, `useCompetitionLabel.ts`, `queries.ts` | 구간·표기 규칙, URL 조건, 대회명, 조회 |
| `teams/` | `TeamsSection.tsx`, `useTeamsParams.ts`, `queries.ts` | 팀 탐색 화면, URL 조건, 조회 |
| `team-detail/` | `TeamDetail.tsx`, `TeamMatches.tsx`, `SquadTable.tsx`, `SeasonRecords.tsx`, `TeamNews.tsx` | 팀 상세 조립, 경기, 선수단 표, 시즌 기록·이적, 팀 뉴스 |
| | `model.ts`, `queries.ts` | 정렬·표기 규칙, 조회 |
| `auth/` | `LoginForm.tsx`, `SignupForm.tsx`, `PasswordResetForm.tsx`, `EmailCodeStep.tsx`, `AuthForm.tsx` | 로그인, 회원가입, 비밀번호 찾기, 이메일 인증번호, 공용 카드·입력칸·소셜 버튼(소셜 로그인은 배포 이후 작업이라 버튼 사용을 주석 처리) |
| | `session.ts`, `AuthSync.tsx`, `returnTo.ts`, `rules.ts` | 로그인 상태·자동 갱신, 로그인 후 돌아갈 곳, 입력 규칙·닉네임 금칙어 |
| `mypage/` | `MyPage.tsx`, `FavoriteTeams.tsx`, `MyReviews.tsx`, `AccountPanel.tsx` | 마이페이지 조립, 관심 팀·팀별 다음 경기, 내 평가, 계정 관리 |
| | `PasswordDialog.tsx`, `WithdrawDialog.tsx`, `MyCard.tsx`, `model.ts`, `queries.ts` | 비밀번호 변경 창, 탈퇴 확인 창, 영역 카드, 화면 규칙, 조회 |
| `feedback/` | `FeedbackProvider.tsx`, `FeedbackButton.tsx`, `FeedbackDialog.tsx`, `draft.ts` | 의견 보내기 창과 임시 저장 |
| `legal/` | `documents.ts`, `LegalLink.tsx` | 약관·개인정보 문서 목록과 링크(공개 전 '준비 중') |

### `src/lib/` 공용 도구

| 파일 | 기능 |
| --- | --- |
| `api/client.ts`, `api/errors.ts` | API 호출(CSRF 헤더·세션 갱신 후 재시도), 오류 변환 |
| `api/query-keys.ts` | 조회 캐시 키 규칙 |
| `api/schema.d.ts`, `api/types.ts` | 백엔드에서 생성한 타입, 자주 쓰는 타입 이름 |
| `format/kst.ts`, `format/match.ts` | 한국 시간 표기, 경기 표기(팀명·대회명·스코어·상태) |
| `hooks/useMediaQuery.ts`, `useHydrated.ts`, `useNow.ts`, `useScrollRow.ts` | PC/모바일 판정, 하이드레이션 완료, 현재 시각, 가로 스크롤 줄 |
| `site.ts` | 푸터 운영자 정보 설정값 |

### `public/` 정적 파일

| 파일 | 기능 |
| --- | --- |
| `brand/logo-header.svg`, `brand/symbol.svg` | 헤더 로고, 로고 심벌 |
| `icons/*.svg` | 화살표(chevron·chevrons)·메뉴·닫기·검색·정보 아이콘 |
| `placeholder.svg` | 엠블럼·사진이 없을 때의 대체 이미지 |

### `tests/` 프런트 테스트

| 파일 | 기능 |
| --- | --- |
| `top5.test.mjs` | TOP 5 띠·목록 |
| `match-regressions.test.mjs` | 경기 상세·평가·타임라인 |
| `results.test.mjs`, `standings.test.mjs`, `teams.test.mjs`, `team-detail.test.mjs` | 지난 경기·리그 순위·팀 탐색·팀 상세 |
| `auth.test.mjs`, `auth-session.test.mjs`, `mypage.test.mjs` | 회원 입력 규칙·세션, 마이페이지 |

## 문서 `docs/`

| 파일 | 기능 |
| --- | --- |
| `guide.md` | 작업할 때 지킬 규칙과 공통 설계, 진행 상태, 배포 확인 목록 |
| `daily-work-log.md` | 날짜별 작업 내역 |
| `file-feature-map.md` | 이 문서 — 폴더·파일별 기능 |
| `legal/terms-of-service.md` | 서비스 이용약관 |
| `legal/privacy-policy.md` | 개인정보 처리방침 |
| `legal/privacy-consent.md` | 가입 화면 '[필수] 개인정보 수집·이용 동의' 문구 |
| `legal/personal-data-inventory.md` | 코드 기준 개인정보 처리 목록(무엇을 어느 표에 얼마나 보관하는지) — 처리방침의 근거 |

`legal/`은 약관 관련 문서를 관리하는 폴더다. 지금은 공개 전 초안이며, 배포 준비 때 확정해 사이트 문서 페이지와 내용을 맞춘다(`guide.md` §10.5).
