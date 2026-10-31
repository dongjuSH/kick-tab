# KickTab 파일별 구현 기능

기준: 2026-10-31 (토), 브랜치 `feat/01-header-footer`. 실제 존재하는 파일만 적는다. 잠금 파일(`uv.lock`, `package-lock.json`), 빈 `__init__.py`, 생성 파일(`frontend/src/lib/api/schema.d.ts` — `npm run gen:api`로 생성, 직접 수정 금지)은 제외한다. 상태는 **완료**(현재 범위 구현 끝) / **골격**(계약·구조만 있고 담당 채팅이 채움)으로 표시한다.

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
| `pyproject.toml` | 의존성(FastAPI, SQLAlchemy 2.1.6, Alembic 1.20.1, APScheduler 3.11.3 등)과 ruff·pytest 설정 | `uv.lock` | 완료 |
| `.python-version`, `.gitignore` | Python 3.12 지정, 백엔드 전용 제외 목록 | — | 완료 |
| `certs/supabase-ca.crt` | Supabase TLS(`verify-full`) CA 인증서 | `app/database.py`, `app/db/session.py` | 완료 |
| `app/config.py` | `Settings`: `.env` 로딩, CORS·신뢰 프록시·스케줄러·API-Football 한도·비밀 값(`SecretStr`)·디스코드 웹후크 | 전 모듈 | 완료 |
| `app/main.py` | FastAPI 앱, CORS, 예외 처리기·`/api/v1` 라우터 등록, `/health`, 스케줄러 수명 주기 | `app/api/*`, `app/sync/scheduler.py` | 완료 |
| `app/database.py` | psycopg 직접 연결(검증 TLS), CA 경로 상수 | `check_database.py`, `db/session.py` | 완료(00) |
| `app/check_database.py` | `python -m app.check_database`: 읽기 전용 연결·TLS 확인 | `database.py` | 완료(00) |

### DB·마이그레이션

| 파일 | 역할 | 연결 | 상태 |
| --- | --- | --- | --- |
| `app/db/base.py` | 선언형 `Base`, 제약 이름 규칙 | 모델, `migrations/env.py` | 완료 |
| `app/db/session.py` | `sqlalchemy_url`(psycopg 드라이버 변환), `connect_args`(TLS), `get_engine`·`get_sessionmaker`(지연 생성), `get_db`(요청 세션 의존성) | 라우트, `sync/runner.py`, `migrations/env.py` | 완료 |
| `app/models/__init__.py` | 모든 모델 import(Alembic 인식용) | `migrations/env.py` | 완료 |
| `app/models/feedback.py` | `Feedback`: user_id(외래 키 없음)·type·body(1~1,000자)·page_path·body_hash·created_at, 제약·인덱스 | `services/feedback.py` | 완료(02가 user_id 외래 키 추가) |
| `app/models/sync_run.py` | `SyncRun`: 수집 실행 기록(job·params·상태·API 요청 수·오류 요약) | `sync/runner.py` | 완료 |
| `alembic.ini` | Alembic 설정(접속 주소는 `env.py`가 `.env`에서 읽음) | `migrations/` | 완료 |
| `migrations/env.py` | `DATABASE_URL`·TLS로 온라인 마이그레이션, 오프라인 SQL 출력 | `app.db.*`, `app.models` | 완료 |
| `migrations/script.py.mako` | 새 리비전 템플릿(RLS 활성화 안내 포함) | — | 완료 |
| `migrations/versions/20261031_0001_sync_runs_feedback.py` | `sync_runs`·`feedback` 생성, RLS 활성화 | — | 개발 DB 적용 |
| `migrations/versions/20261031_0002_feedback_body_hash.py` | `feedback.body_hash` 컬럼·길이 제약·인덱스 | — | 개발 DB 적용 |

### API

| 파일 | 역할 | 연결 | 상태 |
| --- | --- | --- | --- |
| `app/api/router.py` | `/api/v1` 라우터, 전 라우트에 CSRF 검사·오류 응답 문서화 | `main.py`, `routes/*` | 완료 |
| `app/api/errors.py` | `ApiError`, 오류 응답 형식, 검증·HTTP·미처리 예외 처리기(내부 정보 비노출) | 전 라우트 | 완료 |
| `app/api/deps.py` | `require_csrf`(헤더·Origin), `RateLimit`(클라이언트별 + 전역 상한, `key_func` 교체 가능) | `router.py`, `routes/feedback.py` | 완료(02가 회원·비회원 차등) |
| `app/core/rate_limit.py` | `RateLimiter`(슬라이딩 윈도), `client_ip`(신뢰 프록시 뒤에서만 `X-Forwarded-For`), `Retry-After` 값 | `api/deps.py` | 완료 |
| `app/api/routes/feedback.py` | `POST /api/v1/feedback`: 허니팟 거부, 중복 409, 저장 후 디스코드 알림 예약, 요청 제한 값 | `services/feedback.py`, `notifications/discord.py` | 완료 |
| `app/api/routes/top_matches.py` | `GET /api/v1/top-matches/current` | `services/top_matches.py` | 완료(계약) |

### 스키마·서비스·연동

| 파일 | 역할 | 연결 | 상태 |
| --- | --- | --- | --- |
| `app/schemas/common.py` | `ApiModel`(camelCase), `DataResponse[T]`, `ErrorBody`·`ErrorResponse` | 전 스키마 | 완료 |
| `app/schemas/match.py` | `TeamRef`, `CompetitionRef`, `MatchScore`, `MatchSummary` | `top_matches.py`, 03·04 | 골격(03이 실제 데이터로 채움) |
| `app/schemas/top_matches.py` | `TopMatches`, `TopMatchItem`(순위·경기·평균 평점·평가 수), `TopMatchesPeriod` | `services/top_matches.py` | 완료(계약) |
| `app/schemas/feedback.py` | `FeedbackCreate`(본문·유형 필수, 페이지 경로, 허니팟 `website`), `FeedbackReceipt` | `routes/feedback.py` | 완료 |
| `app/services/feedback.py` | `create_feedback`, `normalize_body`·`body_hash`, `is_duplicate`(24시간), `DuplicateFeedbackError` | `routes/feedback.py` | 완료 |
| `app/services/top_matches.py` | `get_current_top_matches()` — 현재 항상 빈 결과 | `routes/top_matches.py` | 골격(04가 선정 로직으로 교체) |
| `app/notifications/discord.py` | `notify_feedback`(웹후크 전송, 실패 무시), `build_payload`(멘션 차단), `FeedbackNotice`, httpx 로그의 웹후크 주소 가림 | `routes/feedback.py`, `config.py` | 완료 |
| `app/providers/api_football.py` | `ApiFootballClient.get`, `MinuteRateLimiter`, `DailyBudget`, 공용 보호 장치, 오류 클래스 | `sync/registry.py` | 골격(03이 엔드포인트별 함수 추가) |

### 수집 실행기

| 파일 | 역할 | 연결 | 상태 |
| --- | --- | --- | --- |
| `app/sync/registry.py` | `@register_job`, `JobSpec`, `JobContext`(세션·파라미터·`api_football()` 요청 수 집계) | 작업 모듈, `runner.py` | 완료 |
| `app/sync/runner.py` | `run_job`: advisory lock → `sync_runs` 기록 → 작업 실행 → 상태 저장 | `registry.py`, `db/session.py` | 완료 |
| `app/sync/scheduler.py` | `SCHEDULER_ENABLED`일 때만 APScheduler 시작, 중복·누락 실행 방지 | `main.py` | 완료 |
| `app/sync/__main__.py` | CLI `python -m app.sync <job> [key=value] / --list` | `runner.py` | 완료 |
| `app/sync/jobs.py` | 작업 모듈 import 지점(현재 등록 작업 없음) | `__main__.py`, `scheduler.py` | 골격(03 이후 추가) |

### 테스트

| 파일 | 대상 |
| --- | --- |
| `tests/conftest.py` | 실제 HTTP 호출 차단, 로컬 웹후크 설정 무시 |
| `tests/test_setup.py` | `/health`·CORS, 설정 로딩·비밀 값 마스킹, DB 연결 TLS, 연결 확인 명령(00 작성, 01에서 비밀 값 목록 보강) |
| `tests/test_api_foundation.py` | 응답·오류 형식, CSRF·Origin, 요청 제한, 의견 검증·허니팟·중복·익명 저장, OpenAPI camelCase |
| `tests/test_rate_limit.py` | 분·일 윈도, 거부 요청 비집계, 신뢰 프록시·`X-Forwarded-For` 처리 |
| `tests/test_api_football.py` | 성공·쿼터 기록, `errors` 실패, 재시도 상한, 중단 조건, 일일 예산, 분당 대기, 키 비노출(모의 전송) |
| `tests/test_sync_runner.py` | 성공·실패·건너뜀 기록, 잠금 키, CLI, 스케줄러 |
| `tests/test_feedback_notifications.py` | 디스코드 페이로드·주소 검사·실패 처리·토큰 비노출, 라우트 알림 예약, 전역 상한 |
| `tests/test_db.py` | 접속 주소·TLS, 모델 구조, `KICKTAB_DB_TESTS=1`일 때 개발 DB 제약·중복·RLS 확인(롤백) |

## 프런트엔드 (`frontend/`)

### 설정

| 파일 | 역할 | 상태 |
| --- | --- | --- |
| `package.json` | 스크립트(`dev`·`build`·`lint`·`gen:api`), 의존성(Next 16.4.3, React 19.3.0, TanStack Query 5.105.0, openapi-typescript 7.13.0) | 완료 |
| `next.config.ts` | `cacheComponents`·`partialPrefetching`, `/api/*` → `BACKEND_ORIGIN` rewrites | 완료 |
| `scripts/gen-api.mjs` | 백엔드 OpenAPI(실행 중 서버 또는 파일)로 `src/lib/api/schema.d.ts` 생성 | 완료 |
| `tsconfig.json`, `eslint.config.mjs`, `postcss.config.mjs`, `.gitignore`, `AGENTS.md` | TypeScript·ESLint·Tailwind 설정, Next 에이전트 안내(기본 생성) | 기존 유지 |

### 앱 경로 (`src/app/`)

| 파일 | 역할 | 연결 | 상태 |
| --- | --- | --- | --- |
| `layout.tsx` | `lang="ko"`, 글꼴, 메타데이터, Provider·의견 Provider·헤더·`main`·푸터·모바일 하단 고정 영역 배치 | 아래 컴포넌트 전부 | 완료 |
| `globals.css` | Figma 색상 토큰(`--kt-*`)·Tailwind 테마(색·글자·반경), 포커스 3px, `kt-container` | 전 컴포넌트 | 완료 |
| `providers.tsx` | TanStack Query 클라이언트(4xx 재시도 안 함) | `layout.tsx` | 완료 |
| `page.tsx` | 메인 자리 표시(제목·안내) | — | 골격(03이 일정 화면으로 교체) |
| `not-found.tsx` | 없는 경로 안내(준비 전 메뉴 경로 포함) | — | 완료 |
| `icon.svg` | 파비콘(로고 심벌 기반) | — | 완료 |

### 공통 UI (`src/components/ui/`)

| 파일 | 역할 | 상태 |
| --- | --- | --- |
| `Button.tsx` | `Button`·`ButtonLink`·`IconButton`(44px), `buttonClass`, primary·secondary·ghost | 완료 |
| `Badge.tsx` | 상태 뱃지(info·live·neutral·warning·error) | 완료 |
| `Dialog.tsx` | 네이티브 `<dialog>` 모달(center·sheet·responsive, compact 시트), 포커스 복귀·Escape·배경 클릭 닫기, `BottomSheet` | 완료 |
| `Tooltip.tsx` | 데스크톱 호버·모바일 탭 툴팁 | 완료(04 후기 주의사항 등에서 사용 예정) |
| `Tabs.tsx` | 키보드 지원 탭·`TabPanel` | 완료(04·08에서 사용 예정) |
| `Dropdown.tsx` | 단일 선택 목록(시즌·리그) | 완료(05·06에서 사용 예정) |
| `Pagination.tsx` | URL 기반 페이지 이동 | 완료(05·07에서 사용 예정) |
| `Skeleton.tsx` | 로딩 자리 | 완료 |
| `DataState.tsx` | `DataState`(로딩·정상·빈 결과·일부 미제공·실패+재시도·권한 거부), `StateMessage` | 완료 |
| `Icon.tsx` | `public/icons/` SVG 아이콘 | 완료 |
| `cx.ts` | 클래스 결합 | 완료 |

### 공통·레이아웃 컴포넌트

| 파일 | 역할 | 연결 | 상태 |
| --- | --- | --- | --- |
| `components/common/Logo.tsx` | 로고 심벌 + 워드마크(헤더 36·모바일 32·푸터 24px) | 헤더·푸터 | 완료 |
| `components/common/TeamCrest.tsx` | `TeamCrest`·`PlayerPhoto`: URL 없음·실패 시 대체 이미지 | TOP 5, 03 이후 | 완료 |
| `components/layout/SiteHeader.tsx` | 고정 헤더(본문 건너뛰기 링크, 로고, 메뉴, 인증 영역, 모바일 메뉴) + TOP 5 띠 | `layout.tsx` | 완료 |
| `components/layout/MainNav.tsx` | 데스크톱 메뉴 4개, 현재 페이지 밑줄 | `nav.ts` | 완료 |
| `components/layout/MobileMenu.tsx` | 모바일 메뉴 버튼·하단 시트, 현재 페이지 강조 | `nav.ts`, `HeaderAuth.tsx` | 완료 |
| `components/layout/HeaderAuth.tsx` | 로그인(ghost)·회원가입(primary), 데스크톱·메뉴 배치 | 헤더·모바일 메뉴 | 골격(02가 `useAuth()`로 회원 상태 연결) |
| `components/layout/nav.ts` | 메뉴 목록·현재 경로 판정 | 메뉴 컴포넌트 | 완료 |
| `components/layout/SiteFooter.tsx` | 로고·정책 항목(링크 없음)·의견 보내기·운영자·출처·저작권 | `lib/site.ts` | 완료(정책 문서 생기면 링크 연결) |
| `components/layout/MobileBottomBar.tsx` | 1024px 미만 하단 고정 의견 보내기 + 여백 | `FeedbackButton` | 완료 |

### 기능 (`src/features/`)

| 파일 | 역할 | 연결 | 상태 |
| --- | --- | --- | --- |
| `top5/queries.ts` | `currentTopMatchesQuery`(5분 캐시) | `apiFetch`, `query-keys.ts` | 완료 |
| `top5/Top5Strip.tsx` | TOP 5 띠, 데스크톱 패널(배경 딤·Escape·포커스), 모바일 시트, 로딩·실패·빈 상태 | `Top5List`, `Dialog` | 완료 |
| `top5/Top5List.tsx` | 펼침 목록 본문(순위·대회·킥오프·대진·스코어·PK·평균 평점·평가 수, 빈 상태, 안내 문구) | `TeamCrest`, `kst.ts` | 완료 |
| `feedback/FeedbackProvider.tsx` | 전역 의견 모달 1개, `useFeedback().openFeedback()` | `layout.tsx` | 완료 |
| `feedback/FeedbackButton.tsx` | 의견 보내기 진입 버튼 | 푸터·하단 고정 영역 | 완료 |
| `feedback/FeedbackDialog.tsx` | 의견 입력·검증·전송·실패/중복/요청 제한/성공 상태, 허니팟 | `apiFetch`, `draft.ts` | 완료 |
| `feedback/draft.ts` | 미전송 초안 sessionStorage 저장·복원(오류 무시) | `FeedbackDialog` | 완료 |

### 라이브러리 (`src/lib/`)

| 파일 | 역할 | 상태 |
| --- | --- | --- |
| `api/client.ts` | `apiFetch`(브라우저 같은 출처·서버는 `BACKEND_ORIGIN`, 변경 요청 CSRF 헤더, 401 갱신 연결 `setUnauthorizedHandler`) | 완료(02가 갱신 로직 등록) |
| `api/errors.ts` | `ApiError`(code·message·fieldErrors·retryAfter), 응답·네트워크 오류 변환 | 완료 |
| `api/types.ts` | 생성 타입의 이름 별칭(`MatchSummary`, `TopMatches`, `FeedbackCreate` 등) | 완료 |
| `api/query-keys.ts` | query key 규칙과 `topMatches`·`me` 키 | 완료(기능 채팅이 키 추가) |
| `format/kst.ts` | KST 시각·날짜·기간(`10/26(월)~11/1(일)`)·`10/29 03:30` 포맷, 누락값 `—` | 완료 |
| `hooks/useMediaQuery.ts` | 미디어 쿼리 구독, `DESKTOP_QUERY`(1024px) | 완료 |
| `site.ts` | 푸터 운영자 정보 설정값(`SITE_OPERATOR_*`) | 완료 |

### 정적 파일 (`public/`)

| 파일 | 역할 |
| --- | --- |
| `brand/symbol.svg` | 로고 심벌(Figma 55:22) |
| `placeholder.svg` | 공통 대체 이미지(Figma 55:26) |
| `icons/chevron-down.svg`, `chevron-right.svg`, `menu.svg`, `x.svg`, `search.svg` | Figma 아이콘 |
