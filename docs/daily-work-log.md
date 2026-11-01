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
