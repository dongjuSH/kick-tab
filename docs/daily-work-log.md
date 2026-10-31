# KickTab 일별 작업 내역

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
