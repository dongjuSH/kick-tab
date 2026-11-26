# KickTab 개발 가이드

작업할 때 확인해야 하는 규칙과 공통 설계를 모은 문서다. 00(전체 조율)과 01~09 기능 채팅이 작업 전에 읽는다.

**이 문서에 쓰는 것과 쓰지 않는 것**
- 쓴다: 작업 위치와 기준 문서, 채팅별 담당, 작업 원칙과 완료 조건, 공통 기술 설계, 정책 결정, 배포 확인 목록, Git 규칙.
- 쓰지 않는다: 날짜별 작업 내역(→ [daily-work-log.md](daily-work-log.md)), 파일별 역할(→ [file-feature-map.md](file-feature-map.md)), 커밋 번호·검사 수치 같은 작업 기록(→ 커밋).
- 2026-11-26 정리 때 그동안 이 문서에 쌓인 작업 이력과 끝난 채팅 사이의 인수인계를 뺐다. 필요하면 정리 전 판본을 Git 기록에서 본다.

최종 갱신: 2026-11-26 (목) — 배포 전 문서 정리(00).

## 1. 작업 위치와 참조 기준

**작업 폴더와 수정 범위(모든 채팅 공통):**

- 채팅의 작업 폴더는 `C:\Users\wnfjq\Desktop\fullstack\project\kick-tab`(이하 `kick-tab/`)으로 지정한다. 상위 자료를 권한 확인 없이 읽기 위해서다.
- **파일 생성·수정·삭제는 `kick-tab/apps/` 안에서만 한다.** 상위 폴더의 `docs/`·`api-test/`·`wireframe/`은 읽기 전용 참고 자료이며 수정하지 않는다(사용자가 명시적으로 요청한 경우만 예외).
- **Git 명령은 `kick-tab/apps/`에서만 실행한다.** `kick-tab/` 루트에는 Git 저장소를 만들지 않는다.
- 개발 서버·검사 명령은 `kick-tab/apps/frontend/`, `kick-tab/apps/backend/`에서 실행한다(§7).

**Git 저장소 루트는 `kick-tab/apps/`이다.** 경로는 저장소 루트 기준으로 쓴다. 상위 폴더 `kick-tab/`의 `docs/`·`api-test/`·`wireframe/`은 Git에 올리지 않는 **로컬 전용 참고 자료**이며 `../`로 표기한다(이 PC에서만 열람 가능).

| 위치 | 용도 |
| --- | --- |
| `frontend/` | Next.js 프런트엔드 |
| `backend/` | FastAPI 백엔드 |
| `docs/guide.md` | 공통 설계·기능 간 연결·진행 상태·다음 작업의 현재 기준 |
| [daily-work-log.md](daily-work-log.md) | 실제 일별 변경 이력. 사용자 요청 시에만 갱신 |
| [file-feature-map.md](file-feature-map.md) | 실제 파일별 역할. 사용자 요청 시에만 갱신 |
| `../docs/KickTab_PRD_*_Fix.docx`(로컬 전용) | PRD — 제품 범위·요구사항 |
| `../docs/KickTab_기능명세서_*_Fix.docx`(로컬 전용) | 기능 명세서 — 기능 ID별 동작·권한·데이터·예외·인수 조건 |
| `../docs/KickTab_유저_플로우_*_Fix.docx`(로컬 전용) | 유저 플로우 — 화면 이동·로그인 복귀·예외 분기 |
| `../api-test/docs/implementation-readiness.md`, `../api-test/docs/archive-scope-final-2026-10-30.md`, `../api-test/docs/api-policy-2026-10-29.md`, `../api-test/docs/api-decisions-2026-10-29.md`(로컬 전용) | 외부 API 검증 결과·제약·이용 조건·후속 확인 사항 |
| `../api-test/results/raw/` | 2025 시즌 14개 대회 경기·5대 리그 순위·선수 전체 페이지 원본 응답(로컬 전용) |
| `../wireframe/` | 화면 구조·상태 분기 참고용 와이어프레임(로컬 전용, `node ../wireframe/preview.mjs` → `http://127.0.0.1:4173`) |

`../docs/` 폴더에는 사용자가 확정한 최신본만 남긴다. 파일명의 버전은 바뀔 수 있으므로 항상 폴더의 현재 파일을 연다.

**기준 우선순위:** 최신 사용자 결정 > PRD > 유저 플로우 > 기능 명세서의 동작 규칙 > API 검증 문서. 화면 표현은 사용자가 최종 컨펌한 [Figma 디자인 시안](https://www.figma.com/design/GUMDnZGrrtetjs1mI9MZsd/KickTab?node-id=46-179), 기능 동작은 확정된 기획 문서를 따른다. 와이어프레임은 참고 자료이며 Figma와 다르면 Figma를 따른다. 명세·디자인·코드가 충돌하면 영향과 필요한 결정을 정리해 Codex 검토로 전달한다(§4).

**Figma 접근 방법(2026-10-31 확인):** 브라우저로 링크를 열면 로그인 화면이 뜨므로 쓰지 않는다. **Figma 커넥터(MCP) 도구로 접근한다.** 파일 키는 `GUMDnZGrrtetjs1mI9MZsd`. `get_metadata`로 프레임 ID를 찾고 `get_screenshot`·`get_design_context`로 대상 프레임을 확인한다. 페이지 전체 메타데이터는 매우 크므로 프레임 단위로 조회한다. `get_variable_defs`는 Figma 데스크톱 앱에서 레이어를 선택해야 동작해 00 채팅에서는 쓰지 못했다(색상 값은 컬러 가이드 프레임에서 확인).

| Figma 페이지 | 내용 |
| --- | --- |
| `46:179` 00 · 컬러 가이드 | 의미별 색상 변수, 가독성·간격·서체 기준(§6.6) |
| `46:180` 01 · 리디자인 | 9개 페이지 × 데스크톱(1920)·모바일(375) 기본 화면과 주요 상태 화면, 공통 UI(모바일 메뉴·TOP 5·의견 보내기·로그인 안내·후기 주의사항·대회 선택·비밀번호 변경·탈퇴), 시즌 선택 |
| `46:181` 02 · UI 상태와 흐름 | 페이지별 검토 상태 묶음(메인 11·경기 상세 15·지난 경기 6·리그 순위 6·팀 탐색 5·팀 상세 7·로그인 8·회원가입 11·마이페이지 8), 설계 반영 기준(`62:1960`), 개발 전달 기준(`96:412`) |
| `46:182` 03 · 컴포넌트 | 로고 심벌(`55:22`), 공통 대체 이미지(`55:26`), 버튼·입력·상태 뱃지 사용 예시(`55:27`) |

최종 대표 프레임: 메인49:57/49:570, 지난 경기53:593/53:995, 경기 상세52:151/52:404, TOP5 펼침128:3700/128:4408, 최종 인계62:1960을 사용한다. 삭제된 과거 변형 링크는 현재 기준으로 사용하지 않는다.

디자인 전달 기준은 Figma의 컬러 가이드·설계 반영 기준·개발 전달 기준과 이 가이드 §6.6이다.

**최종 브랜드(2026-11-03 승인·Figma 적용):** 원본은 Figma와 `frontend/public/brand/`의 최종 SVG다. 심벌55:22·파비콘264:1430·사용 크기/밝고 어두운 배경 보드264:1431을 따른다.36/32/24px 슬롯 안 실제 심벌31/27.56/20.67px, 슬레이트 워드마크#0F172A, 헤더 기준 간격8.5px다. 키 면#F8FAFC·경계#E2E8F0·화살표#2563EB, 파비콘은 공 없이 화살표만 사용한다.

**공통 원본:** Header Nav Item275:2544, TOP5 Strip159:923/Panel159:924, Competition Picker187:1946, Schedule Explorer225:2013, Feedback225:2374, Date Strip278:2752, Date Availability285:14295, News Feed279:4473, Review Header279:4567/Popover279:4492. 공통 대회 창은 메인·지난 경기 모두 체크 초안/적용/취소이며 지난 경기의 시즌 전체 조회를 유지한다.

## 2. 채팅 구성과 담당 범위 — 전체 10개

각 기능 채팅은 담당 기능의 프런트엔드·백엔드·DB 마이그레이션·예외 처리·자체 검수까지 함께 맡는다. 같은 작업 폴더를 쓰므로 **코드 수정은 아래 순서대로 한 채팅씩 진행한다.** 기능 ID는 기능 명세서 기준이다.

| 순서 | 채팅 | 담당 기능 ID | 담당 범위(공통 기능 포함) |
| --- | --- | --- | --- |
| — | 00 전체 설계·조율·검수 | — | 공통 설계, 범위·순서 결정, 가이드 관리, 기능별 완료 확인, 전체 최종 검수, 사용자 요청 시 Git 원격 업로드 |
| 1 | 01 헤더·푸터 + **공통 기반** | COM-003·004, FEED-001~003, TOP-003(표시) | §6의 프런트·백엔드 공통 기반 전체, 디자인 토큰, 공통 UI 컴포넌트, 헤더(인증 영역은 자리만)·푸터·TOP 5 띠(조회·7가지 상태 표시)·의견 보내기 |
| 2 | 03 경기 일정(메인) | SCH-001~006, LIVE-001~004, CMP-001~004, NEWS-001~004, FAV-001~004의 비회원 부분, OPS-001~004(해당분) | 대회·시즌·팀 기준 데이터와 **팀 상세 허용 집합**, 별칭 사전, 경기 수집·상태 변환·실시간 갱신, `MatchCard`·`CompetitionFilter`·`TeamSearch`, 메인 일정(2026-11-19: 대회 21개 — 국가별·UEFA·FIFA, 공통 경기일 기간, 대회명 `name_ko` 통일), **비회원 관심 팀(localStorage 저장소·`useFavorites()`·`FavoriteToggle`·관심 팀 일정·관심 팀 버튼) 사전 제작**, **뉴스 수집·분류와 `NewsCard`** |
| 3 | 04 경기 상세 | MAT-001~005, REV-001·004, TOP-001·002 | 경기 상세(상태별 영역·이벤트·기록·상대 전적·최근 흐름), 경기 평가(텍스트) **조회**·건수·정렬·작성 가능 판정(04 개선), TOP 5 선정 작업(정책 확정분만, §10). 후기 작성·수정·삭제·반응은 회원 기능이므로 02에서 마무리하고, 04는 02가 붙일 수 있는 API·화면 구조까지 사전 작업한다 |
| 4 | 05 지난 경기 | HIST-001~003 | 지난 경기 조회·필터·페이지 분할, `SeasonSelect`, 2025 시즌 과거 데이터 적재 작업 |
| 5 | 06 리그 순위 | LEAG-001·002·004 | 순위 수집, 시즌별 전체 순위, 선수 순위(득점·도움·카드·선방 자체 집계), 메인 간소 순위 영역, 리그 전체 선수 시즌 기록 수집 |
| 6 | 07 팀 탐색 | LEAG-003 | 현재 시즌 5대 리그 팀 목록·리그 필터·팀명 검색·비회원 관심 팀 등록/해제(03의 `FavoriteToggle` 재사용) |
| 7 | 08 팀 상세 | TEAM-001~006 | 팀 기본 정보·경기·선수 표·시즌 기록·이적(배치 포함)·팀 뉴스(03 뉴스 재사용)·비회원 관심 팀 버튼(03 재사용), 모바일 탭. **08까지 마치면 비회원 기준으로 서비스 전체를 이용할 수 있어야 한다** |
| 8 | 02 로그인·회원가입(**08 다음**) | AUTH-001~005, COM-001·002·005, FAV-001~003 회원 부분, REV-002~003 연결, MY-004 계정 API | 이메일 인증·세 필수 확인·세션·비밀번호 찾기/변경·탈퇴, 헤더·로그인 복귀·평가 입력 보존, 관심 팀 DB 동기화, 평가 작성/수정/삭제/반응, 의견 회원 연결. 소셜은 버튼과 같은 화면 준비 중 안내만 |
| 9 | 09 마이페이지 | MY-001~004 | 관심 팀·내 평가·계정 관리(02 API 사용). 닉네임 표시만·수정한 평가만 수정 날짜·비밀번호 변경 상태 연결 |

**공통 기능 담당과 재사용 방식**

| 공통 기능 | 만드는 채팅 | 재사용 채팅 | 위치 |
| --- | --- | --- | --- |
| 공통 UI(버튼·배지·팝업·스켈레톤·상태 표시·페이지 버튼) | 01 | 전체 | `frontend/src/components/ui/` |
| 엠블럼·선수 사진·대체 이미지 | 01 | 전체 | `components/common/TeamCrest.tsx`, `public/placeholder.svg` |
| API 호출·응답 타입·오류 처리 | 01 | 전체 | `frontend/src/lib/api/`, 백엔드 `app/api/errors.py`·`app/schemas/common.py` |
| TOP 5 띠·주간 선정 | 01(표시)·04(선정) | 전 페이지 | `features/top5/`, `app/services/top5_selection.py`·`app/sync/top5.py` |
| 의견 보내기 | 01 | 전 페이지 | `features/feedback/`, `app/api/routes/feedback.py`, `app/notifications/discord.py` |
| 헤더 인증 영역 | 01(자리)·02(연결) | 전 페이지 | `components/layout/HeaderAuth.tsx` |
| 수집 실행기·API-Football 클라이언트 | 01 | 03~08 | `app/sync/registry.py`·`runner.py`, `app/providers/api_football.py` |
| 요청 제한·CSRF | 01 | 변경 API 전체 | `app/api/deps.py`, `app/core/rate_limit.py` |
| 로그인 상태·로그인 유도·복귀 | 02 | 04·09 | `features/auth/session.ts`·`returnTo.ts`, `app/api/auth.py` |
| 관심 팀 | 03(비회원)·02(회원) | 07·08·09 | `features/favorites/`, `app/services/member_favorites.py` |
| 팀 상세 링크 허용 여부 | 03 | 04~08 | `app/services/reference.py`(`team_detail_lookup`) |
| 경기 카드·상태 배지 | 03 | 04·05·08·TOP 5 | `components/common/MatchCard.tsx`·`MatchStatusBadge.tsx` |
| 대회 선택 | 03 | 05 | `components/common/CompetitionFilter.tsx` |
| 팀 검색·별칭 사전 | 03 | 05·07·뉴스 분류 | `components/common/TeamSearch.tsx`, `app/services/team_search.py`, `app/seed/team_aliases.json` |
| 뉴스 카드·원문 이동 | 03 | 08 | `components/common/NewsCard.tsx`, `features/news/OriginalRedirect.tsx` |
| 경기 상세·기록·상대 전적 | 04 | 05·08·TOP 5 | `features/match/`, `app/services/match_detail.py`·`head_to_head.py` |
| 동시 보충 조회 합치기 | 04 | 외부 보충 조회가 있는 채팅 | `app/core/locks.py` |
| 시즌 선택·시즌 목록 | 05 | 06 | `components/common/SeasonSelect.tsx`, `app/services/results.py` |
| 지난 경기 조회 | 05 | 08(경기 전체 보기) | `features/results/`, `app/services/results.py` |
| 리그 순위·선수 순위·대회명 | 06 | 07·08·메인 | `features/standings/`, `app/services/standings.py` |
| 최근 5경기 | 06 | 04·08 | `components/common/RecentForm.tsx` |
| 가로 칩 줄·스크롤 줄 | 03·06 | 03·06·07 | `features/standings/ChipRow.tsx`, `lib/hooks/useScrollRow.ts` |
| 팀 탐색 목록 | 07 | 08·메인 | `features/teams/`, `app/services/team_browse.py` |
| 리그 선수 시즌 기록 | 06 | 08 | `app/sync/standings.py`(`player_stats`), `app/models/standings.py` |
| 팀 상세 | 08 | 02·09 | `features/team-detail/`, `app/services/team_detail.py` |

담당이 아닌 채팅은 같은 기능을 중복 구현하지 않는다. 공통 컴포넌트가 부족하면 담당 채팅의 구조를 확장하고 이 표를 갱신한다. 페이지 목록에서 빠졌다는 이유로 명세의 기능을 누락하지 않는다.

## 3. 진행 상태

01~09 모든 기능이 구현·검수를 마치고 `dev`에 병합됐다(2026-11-26 기준). Codex를 쓸 수 없어 2026-11-24 이후 작업은 자체 검수와 00 전체 검수로 마무리했다(사용자 결정). 남은 일은 배포 준비(§10.4·§10.5)다.

| 채팅 | 상태 | 남은 확인 |
| --- | --- | --- |
| 00 | 설계·조율, 데스크톱 검수 반영 조율, 전체 검수(2026-11-25) 완료 | 배포 준비 목록 정리. 제안(미반영): 수집 실행기(`app/sync/runner.py`)가 서버 중단으로 '실행 중'에 남은 `sync_runs` 행을 시작 때 정리하게 하기 — 지금은 수동 정리(2026-11-20 369번, 2026-11-25 798번) |
| 01 | 헤더·푸터·공통 기반·공통 버튼 체계 완료 | — |
| 02 | 로그인·회원가입·비밀번호 찾기·회원 API·약관 초안 완료 | 약관 확정·공개(§10.5 '약관·운영자') |
| 03 | 경기 일정·대회·뉴스·관심 팀(비회원) 완료 | — |
| 04 | 경기 상세·경기 평가·TOP 5 선정 완료 | 경기 평가 작성란 '평가 작성 !' 줄 제거(2026-11-26 Figma 반영, 코드 작업 대기) |
| 05 | 지난 경기 완료 | — |
| 06 | 리그 순위·선수 순위 완료 | — |
| 07 | 팀 탐색 완료 | — |
| 08 | 팀 상세·이적 완료 | — |
| 09 | 마이페이지 완료 | 닫힌 경기 평가 수정 안내(409)는 실제 사례가 없어 브라우저로 재현하지 않음 |

새 작업을 마치면 이 표의 상태와 남은 확인만 갱신한다. 작업 내용은 `daily-work-log.md`에 쓴다.

### 3.1 공통 작업 규칙

공통 인터페이스의 위치는 §2 표, 파일별 역할은 `file-feature-map.md`를 본다. 아래는 코드를 고칠 때 지켜야 하는 규칙이다.

- **API 추가:** 라우트는 `app/api/routes/<리소스>.py`에 만들고 `app/api/router.py`에 등록한다. 스키마는 `ApiModel`을 상속하고 응답은 `DataResponse[T]`로 감싼다. 오류는 `ApiError(status, code, message)`로 던진다. 새 오류 코드는 §6.4 표와 `frontend/src/lib/api/errors.ts`의 `ApiErrorCode`에 함께 추가한다. 변경 요청(POST·PUT·PATCH·DELETE)은 라우터 단에서 CSRF 검사가 자동 적용된다.
- **타입 동기화:** 백엔드 스키마를 바꾸면 백엔드 실행 후 `npm run gen:api`로 `src/lib/api/schema.d.ts`를 다시 만들고, 필요한 이름은 `src/lib/api/types.ts`에 별칭으로 추가한다. 타입을 손으로 쓰지 않는다.
- **마이그레이션:** 파일 이름 `YYYYMMDD_NNNN_<이름>.py`, 리비전 ID는 `NNNN_<이름>`으로 직접 지정한다(`python -m alembic revision --autogenerate -m ... --rev-id NNNN_<이름>` 후 파일명 변경). 자동 생성은 CHECK 제약을 만들지 않으므로 직접 추가한다. 새 테이블은 RLS 활성화를 포함한다. 개발 DB가 운영 DB와 같은 공유 DB이므로 `downgrade`는 코드로 작성만 하고 실행하지 않으며, 적용은 사용자 확인 후 `upgrade head`, 확인은 `alembic current`·`alembic check`로 한다. 모델은 `app/models/__init__.py`에 import한다. **다음 번호는 `0022`다**(현재 head `0021_drop_player_season_checks`).
- **테스트:** `tests/conftest.py`가 실제 외부 HTTP 호출을 막고 로컬 웹후크 설정을 무시한다. 외부 API는 `httpx.MockTransport`로 시험한다. 실제 DB 확인이 필요하면 `KICKTAB_DB_TESTS=1`일 때만 도는 테스트로 만들고 트랜잭션을 롤백한다(`tests/test_db.py` 참고). 라우트 테스트는 `app.dependency_overrides[get_db]`로 세션을 바꾸고, 모의 세션은 `session.scalar.return_value`를 지정해야 한다.
- **경기 표 범위:** `fixtures`에는 관리 시즌(2025·2026)의 시즌 전체 경기가 들어 있다(공통 경기일 기간 밖 미래 경기 포함). 새 조회는 날짜·시즌·상태 조건을 반드시 건다. 조건 없이 '가장 가까운 경기'를 고르면 기간 밖 경기도 나온다(관심 팀 다음 경기는 의도적으로 이렇게 동작).
- **제공사 데이터 표기:** 선수·팀 이름에 HTML 엔티티(`&apos;` 등)가 섞여 온다. 저장값은 그대로 두고 응답에서 `app/services/team_detail.py`의 `display_text`로 해제한다.
- **테스트 계정:** `backend/.env.test-accounts`(로컬 전용, Git 제외)의 계정 A만 쓴다. 계정 B는 탈퇴 검수에 써서 로그인되지 않는다. 값은 채팅·문서·로그에 남기지 않는다.
- **오류 로그:** 미처리 예외는 `app/api/errors.py`의 `UnhandledErrorMiddleware`가 공통 500 응답으로 바꾸고 예외 종류만 기록한다(서버 로그에 메시지·traceback을 남기지 않음, `tests/test_server_logging.py`가 실제 Uvicorn으로 확인). 새 앱·테스트 앱도 `register_exception_handlers(app)`를 다른 미들웨어보다 먼저 호출한다. 진단이 더 필요하면 메시지 대신 안전한 식별 정보(오류 코드·리소스 ID)를 로그에 남긴다.
- **동시성:** '조회 후 저장'으로 중복을 막는 서비스는 같은 트랜잭션 안에서 키별 `pg_advisory_xact_lock`으로 묶는다(`app/services/feedback.py`의 `lock_body_hash` 참고). 키는 다른 용도와 겹치지 않게 접두어를 붙여 해시한다. 메모리 제한기 `RateLimiter`는 `check`·`record`·`hit`가 각각 한 번의 잠금으로 동작하고(`hit`은 검사와 기록을 한 잠금 안에서 처리), 잠금 안에서는 `_check_locked`·`_record_locked`만 호출한다.
- **커서:** Tailwind v4는 버튼 커서를 기본 화살표로 두므로 `globals.css` base에서 활성 `button`·`[role=button]`·`[role=option]`·`summary`를 손가락 커서로 지정했다(03, 사용자 피드백). 새 클릭 요소는 버튼·링크 요소로 만들면 자동 적용된다.
- **화면:** 색·글자·반경은 `globals.css` 토큰 유틸리티만 쓰고(§6.6), 데스크톱 배치는 `lg:`(1024px)부터, 콘텐츠 폭은 `kt-container`. 모든 데이터 영역은 `DataState`로 상태를 구분한다. 모달·시트는 `Dialog`(`layout`: `center`·`sheet`·`responsive`)를 쓴다. 같은 성질의 Tailwind 클래스를 `buttonClass` 위에 덧붙이면 충돌해 적용되지 않을 수 있으므로(01에서 모바일 메뉴 강조가 이 문제로 실패), 상태별 스타일은 겹치지 않게 조합하고 브라우저에서 계산 스타일을 확인한다.
- **UI 기준(사용자 결정 2026-11-10):** 기획 문서와 Figma가 다르면 Figma가 최종이다. 작업은 기존 `kick-tab/apps` 작업 트리에서 하며 별도 폴더(worktree)를 만들지 않는다.
- **헤더 높이(01, 2026-11-19 갱신):** `--kt-header-height`의 CSS 값은 데스크톱(1024px 이상) 118px(내비 68+1+띠 48+1), 모바일 130px(64+1+64+1)이고 첫 렌더 기본값이다(Figma `128:3700`·`128:4408`). 로고 46/40px·메뉴·인증·메뉴 버튼 44px는 그대로이고 위아래 여백만 줄였다. `src/components/layout/HeaderHeight.tsx`가 ResizeObserver로 실제 헤더 높이를 이 변수에 맞춰, 띠가 늘어나는 경우(예: 320px에서 지난주 기간이 첫째 줄에 들어가지 않아 줄바꿈 → 150px)에도 `scroll-padding-top`·TOP 5 딤·패널·시트 위치가 실제 헤더 하단을 따른다. 헤더 아래에 붙는 고정 요소는 이 변수를 쓴다.
- **대화상자 닫힘 전환(01, 2026-11-10):** `Dialog`는 처음 열린 렌더부터 내용을 그리고, 닫을 때 `<dialog>`의 `transition-duration` 최댓값만큼 내용을 유지한 뒤 지운다(전환이 없으면 즉시). 닫힌 dialog는 즉시 `inert`이고, 다시 열린 뒤 늦게 온 close 이벤트나 다른 모달이 열린 상태에서는 스크롤 잠금·포커스 복귀를 풀지 않는다. 닫힘 모션은 사용처 className으로 준다(TOP 5 `kt-top5-sheet`: `@starting-style`·`display`/`overlay` `allow-discrete`).
- **조작 영역:** 모바일 44px 이상은 실제 클릭 영역 기준이다. 시안 높이를 지켜야 하면 `before:` 가상 요소로 영역만 넓힌다.
- **장시간 표시 데이터(04 구현):** TOP 5 목록은 화면 활성 중 30분 주기·5분 경과 후 포커스/펼침 재조회로 경기 정보를 갱신하고, 공개 결과 교체는 `GET /top-matches/version`을 30초마다(화면 활성 중·포커스 시) 확인해 공개 버전 또는 현재 KST 주가 바뀌면 즉시 `current`를 다시 조회한다(`Top5Strip`, `isOutdated()`). 조회 실패 시 화면의 기존 결과를 유지하며, 교체 조회가 실패해도 같은 공개 버전의 다음 성공 확인 때 다시 시도한다(진행 중인 재조회는 취소하지 않음). 브라우저 검수에서 공개 버전 변경 후 열린 패널이 새로고침 없이 35초 안에 바뀌었다.
- **외부 이미지:** `TeamCrest`·`PlayerPhoto`는 `next/image`를 `unoptimized`로 쓰므로 원격 도메인 설정이 필요 없다. URL이 `null`이거나 실패하면 대체 이미지가 나온다.
- **경로 구현 현황:** `/login`·`/signup`·`/password-reset`은 02, `/mypage`는 09가 구현했다. 없는 경로는 404 안내(`app/not-found.tsx`)가 뜬다. 메인 `/`는 03, 경기 상세 `/matches/[id]`는 04, 지난 경기 `/results`는 05, 리그 순위 `/standings`는 06, 팀 탐색 `/teams`는 07, 팀 상세 `/teams/[id]`는 08이 구현했다. 모든 팀 링크(경기 상세·지난 경기·리그 순위·팀 탐색)는 `detailAvailable: true`일 때 `/teams/{id}`로 열린다(08 브라우저 확인).
- **동적 경로와 루트 레이아웃(04 처리):** `cacheComponents`에서 런타임 param 페이지(`/matches/[id]`)가 정적 셸을 갖도록 루트 레이아웃의 `usePathname()` 컴포넌트를 `<Suspense>`로 감쌌다 — `SiteHeader`의 `MainNav`(대체 UI `MainNavFallback`: 현재 메뉴 표시 없는 같은 메뉴)·`MobileMenu`(44px 빈 자리)·`Top5Strip`(`Top5StripFallback`: 같은 높이의 띠), `FeedbackProvider`의 `FeedbackDialog`(대체 UI 없음). 동적 페이지 자체는 `params`를 `<Suspense>` 안의 async 컴포넌트에서 await한다(`app/matches/[id]/page.tsx` 참고). 빌드 결과 `/matches/[id]`는 ◐ Partial Prerender. 새 레이아웃 컴포넌트가 경로·검색 파라미터를 읽으면 같은 방식으로 감싼다.
- **화면 상태의 URL 반영:** 서버 데이터를 다시 받을 필요가 없는 탭·정렬 같은 상태는 `window.history.replaceState`로 검색 파라미터만 바꾼다(Next 문서: `useSearchParams`와 동기화되고 서버 왕복 없음). `router.replace`는 동적 페이지에서 서버 왕복이 생겨 탭 전환이 늦었다(04 확인).
- **하이드레이션과 공유 캐시(05 정리):** Suspense 경계 안 클라이언트 영역이 다른 컴포넌트와 같은 쿼리(대회 목록·관심 팀 등)를 읽으면, 먼저 하이드레이트된 쪽이 받아 둔 캐시 때문에 서버 HTML과 달라질 수 있다. 그런 영역은 `useHydrated()`가 false인 동안 서버와 같은 자리 표시를 그린다(`ScheduleSection`·`ResultsSection`의 `SectionSkeleton`).
- **개발 서버 모듈 캐시:** 실행 중인 `next dev`가 수정 전 서버 모듈 인스턴스를 들고 있어 서버 렌더링이 'Cannot read properties of undefined'로 실패하고 클라이언트 렌더링으로 전환된 적이 있다(05, 쿼리 키 추가 직후). 파일을 다시 저장해도 풀리지 않으면 개발 서버를 재시작한다(의존성 재설치는 하지 않음).
- **URL 검색 파라미터:** `useSearchParams()`를 쓰는 클라이언트 영역은 `<Suspense>` 안에 둔다(메인 `ScheduleSection` 참고). 렌더 중 `Date.now()`는 개발 서버가 prerender 오류로 잡으므로 데이터가 있을 때만 읽거나 효과(effect)·쿼리 상태(`dataUpdatedAt`)를 쓴다.
- **검수 팁:** 앱의 브라우저 창이 숨겨져 있으면 `requestAnimationFrame`이 멈춰 React의 Suspense 표시 전환·hydration이 대기한다(앱 결함 아님). 스크린샷을 찍으면 프레임이 진행된다.
- **로컬 실행:** 백엔드는 `uv run python -m uvicorn app.main:app --port 8000`(설정·`.env`를 바꾸면 재시작 필요), 프런트는 `npm run dev`. Windows에서 백그라운드로 띄운 서버가 종료 후에도 남아 포트를 점유할 수 있으니 `netstat -ano`로 확인한다. **07 확인:** 이 PC의 `netstat` 상태 이름은 한국어라 `LISTEN`으로 걸러지지 않고, 실행기에서 띄운 `npm run dev`는 작업을 멈춰도 `next dev` 자식 프로세스가 남았다. 포트 확인은 `curl` 응답과 프로세스 명령줄(PowerShell `Get-CimInstance Win32_Process`)로 하고, 종료는 `taskkill /PID <부모> /T /F`로 트리째 한다. 사용자가 직접 띄운 서버(예: VS Code 터미널의 `fastapi dev`)는 종료하지 않는다.
- **Figma:** 커넥터 응답이 간헐적으로 끊기면(`MCP server connection lost`) 같은 호출을 다시 하면 된다. 페이지 전체 메타데이터는 매우 커서 파일로 저장되므로 프레임 단위로 조회한다.
- **TOP 5 PC 패널은 비모달(01, 2026-11-19, 기능 명세서 COM-003·TOP-003, Figma `308:4617`):** 1024px 이상 패널은 `role="dialog"`(이름 '주목 경기 선정 목록 + 기간')만 두고 `aria-modal`·배경 inert·Tab 가두기를 쓰지 않는다. 열린 동안에도 헤더 로고·메뉴·인증 메뉴를 마우스·키보드로 쓸 수 있고, 딤은 헤더 아래만 덮는다. 첫 포커스는 닫기 버튼, 닫기·Escape·딤으로 닫을 때만 띠 버튼으로 포커스를 돌려준다. 링크(로고·메뉴 — 같은 페이지 메뉴 포함 — ·목록 경기)를 누르면 패널을 닫고 포커스는 이동한 페이지에 맡긴다(`Top5Strip`의 문서 click 캡처. 수정 키·가운데 버튼 클릭은 새 탭으로 열고 패널을 유지한다 — 목록 행도 같은 `isPlainClick` 판정을 쓴다). 위에 모달(의견 보내기 등)이 열려 있으면 Escape는 그 모달이 처리한다. 1024px 미만 하단 시트는 기존대로 모달(전체 딤·포커스 제한·닫은 뒤 띠 복귀)이며, 높이 420px 미만(200% 확대 등)에서는 목록이 납작해지지 않게 시트 본문 전체가 스크롤된다.
- **경기 행 공통 부품(01, 2026-11-19):** `components/common/MatchCard.tsx`가 `MatchTeams`(홈 이름·엠블럼·스코어/VS/—·PK·엠블럼·원정 이름. 팀명은 단어 단위로 줄바꿈하되 칸보다 긴 한 단어는 칸 안에서 끊는다 — `overflow-wrap:anywhere`), `MatchStatus`(상태 배지 + `statusNotes` 줄 — 중단 경기는 '중단 시점 스코어'와 제공사 사유를 둘 다, `end`로 오른쪽 정렬), `useMatchScore`(킥오프가 지났는데 시작 미확인이면 '상태 확인 중'·'—')를 내보낸다. `MatchCard`와 TOP 5 펼친 목록(`Top5List`)이 같이 쓰므로 배치·포맷을 바꾸면 두 화면을 함께 확인한다. TOP 5는 순위·선정 당시 킥오프·변경 일시·선정 이유만 고유 표시이고, 제공사 사유는 변경 일시 줄이 아니라 상태 배지 아래에 나온다.

**회원 상태를 쓸 때**

- 로그인 상태는 `src/features/auth/session.ts`의 `useAuth()`(`loading`·`guest`·`member`) 하나로 읽는다. `loading` 동안에는 회원·비회원 어느 쪽 데이터도 가정하지 않는다(헤더는 같은 자리를 비워 둔다). 세션 확인은 `providers.tsx`의 `AuthSync`가 페이지 로드마다 `GET /auth/me`로 한 번 하고, 회원이 바뀌면(로그인·로그아웃·만료·탈퇴) `queryKeys.me.all`을 지우고 `["matches","reviews"]`를 다시 받는다.
- `apiFetch`는 `401 AUTH_EXPIRED`에서 `POST /auth/refresh`를 한 번(동시 요청 합침) 시도한다. 갱신이 실패해도 **GET은 한 번 다시 보낸다**(서버가 쿠키를 지웠으므로 공개 데이터는 비회원으로 받음). 변경 요청은 다시 보내지 않는다. 204 응답은 `{ data: null }`로 돌려준다.
- `useFavorites()`의 `add`·`remove`는 이제 **`Promise<FavoriteChange>`**다(회원은 서버 저장). 반환에 `source`(`guest`·`member`)·`max`(5·10)·`retry`가 있고, `status`에 회원 목록 조회 실패 `failed`가 추가됐다(로컬 목록으로 대체하지 않음). 한도 문구는 `favoriteRefusal(change, max)`(`FavoriteToggle.tsx`)로 만든다.
- Next 16(`cacheComponents`)은 방문한 페이지의 상태를 숨겨 둔 채 유지한다(02 확인: 로그인 성공 후 다시 `/login`에 오면 '로그인 중…' 그대로였음). 페이지를 떠나는 성공 처리에서는 폼 상태를 직접 초기화하고, '이 페이지에 들어왔을 때 한 번' 할 일은 그 영역이 새로 마운트되는 시점(예: 회원에게만 보이는 컴포넌트의 마운트)에 둔다.
- 약관·개인정보 링크는 `src/features/legal/documents.ts`(`published`)와 `LegalLink` 한 곳이다. 문서를 확정하면 페이지(`/terms`·`/privacy`·`/privacy/consent`)를 만들고 `published: true`, 백엔드 `TERMS_VERSION`을 문서 버전으로 바꾼다(초안: `docs/legal/`).

## 4. 기능 구현·검수·설계 변경 흐름

기능 작업은 **가이드·관련 코드 확인 → 범위와 작업 구상 정리 → 프런트엔드·백엔드 구현 → Claude 자체 검수 → Codex 교차 검증 → Claude 보완 → 필요한 범위 재검증** 순서로 진행한다. Claude 자체 검수만으로 교차 검증 완료를 표시하지 않는다.

기존 인증·DB·외부 API·공통 UI를 재사용하고 공유 계약(API 응답, DB 테이블, 공통 컴포넌트 props)을 바꾸면 영향을 받는 기능과 이 가이드도 반영한다. 단순한 내부 구현 선택은 기존 구조에 맞춰 진행하되, 사용자 동작·화면·권한·데이터 정책이 기존 설계와 달라져야 한다면 변경 이유·대안·영향·수정할 기획/디자인 항목을 정리한다. Codex 검토와 필요한 사용자 결정 후 기획 문서·디자인·가이드에 반영하고 변경된 기준으로 구현한다. 미확정 정책(§10)은 임의로 정하지 않고 "제공 보류" 상태로 구현한다.

**작업 원칙(사용자 결정 2026-11-01) — 모든 기능 채팅이 반드시 지킨다**

1. **작업 순서(사용자 결정 2026-11-01):** 01 헤더·푸터(재검수) → 03 경기 일정 → 04 경기 상세 → 05 지난 경기 → 06 리그 순위 → 07 팀 탐색 → 08 팀 상세 → 02 로그인·회원가입 → 09 마이페이지. 각 작업은 **새 채팅**에서 진행한다. 08까지 비회원 기준으로 서비스 전체를 이용할 수 있게 만든 뒤 02·09로 넘어간다. 작업마다 Codex 교차 검증을 받고 00 채팅에서 확인·조율한 뒤 다음 작업으로 간다.
2. **한 작업 안에서 끝낸다:** 각 작업은 담당 화면의 프런트엔드·백엔드·DB·외부 연동을 모두 실제로 동작하게 만든 뒤 마친다. 다음 작업과 이어지는 부분은 다음 작업이 바로 쓸 수 있는 사전 작업(인터페이스·자리)까지만 만든다. 다음 작업이 알아야 할 점은 §3 표의 남은 확인에, 계속 지켜야 할 규칙은 §3.1 공통 작업 규칙에 남긴다.
3. **"완료"는 실제로 동작할 때만 쓴다:** 자리 표시·모의 구현·콘솔 출력·"설정하면 동작함"은 완료가 아니다. 예: 인증 메일이 실제 메일함에 도착하지 않으면 회원가입은 미완료다. 외부 계정·비밀 값·사용자 결정이 없어 막히면 상태를 **"차단됨 — 필요한 것: …"**으로 보고하고 완료라고 쓰지 않는다.
4. **실제 실행으로 자체 검수한다:** 자동 테스트 통과와 별개로, 백엔드·프런트엔드를 실제로 띄우고 실제 DB·외부 연동으로 담당 사용자 흐름을 브라우저에서 처음부터 끝까지 직접 수행한다. 수행한 흐름·결과(성공/실패)를 완료 보고에 목록으로 적는다. 실행하지 않은 흐름은 "미실행"으로 표시한다.
5. **범위 밖 코드는 만들지 않는다:** 담당 화면에서 실제로 쓰지 않는 컴포넌트·옵션·추상화를 "나중을 위해" 만들지 않는다. 교차 검증 전에 쓰이지 않는 코드를 지운다. 교차 검증에서 쓰이지 않는 코드의 결함이 나오면 고치지 말고 삭제한다.
6. **교차 검증 전에 결함을 줄인다:** Codex에 넘기기 전에 §4 완료 조건을 항목별로 스스로 대조해 표로 남긴다(충족·미충족·해당 없음). 미충족 항목이 있으면 넘기지 않는다.

**기능 완료 조건(공통)**

1. 담당 기능 ID의 정상 처리·예외 처리·완료 및 검증 조건(기능 명세서)과 관련 통합 인수 기준(기능 명세서 6.2)을 충족한다.
2. 로딩·빈 결과·일부 미제공·조회 실패·권한 거부 상태를 구분해 보여준다. 누락값은 `null`로 전달하고 화면에서 '미제공' 또는 '—'로 표시한다.
3. 데스크톱·모바일(375px) 배치를 Figma 기준으로 확인한다. 접근하지 못한 프레임은 미확인으로 남긴다.
4. 백엔드 `uv run ruff check .`, `uv run python -m pytest`, 프런트엔드 `npm run lint`, `npm test`, `npm run build`가 통과한다. 새 API·서비스 로직에는 테스트를 추가한다.
5. 새 테이블은 Alembic 마이그레이션으로만 만들고 `downgrade`까지 작성한다. 공유 DB(개발·운영 공용)라 적용은 사용자 확인 후 `upgrade head`만 하고 `downgrade`는 실행하지 않는다(§3.1 마이그레이션).
6. 실제 외부 API 호출은 필요한 최소 횟수만 실행하고 횟수를 완료 응답에 적는다. 담당 기능이 외부 연동(메일·축구 API·뉴스 API)을 쓰면 실제 연동으로 1회 이상 끝까지 확인한다.
7. 위 작업 원칙 4번의 실제 실행 흐름 목록과 6번의 완료 조건 대조표를 완료 보고에 포함한다.
8. 완료 응답에 구현 범위·관련 경로·검사 결과·실제 API/DB 연동 여부·미확인 사항을 남기고, 이 가이드 §3과 바뀐 공통 인터페이스를 갱신한다.

모든 기능을 마치면 페이지 간 이동, 인증 후 복귀, 관심 팀·후기의 화면 간 반영, 시즌 전환, 외부 API 실패 등 연결 흐름을 전체 검수한다. **터치·펜 실기기와 스크린리더 검사도 이 단계에서 일괄 진행한다**(사용자 결정 2026-11-01). 기능 채팅 단계에서는 실기기 미검사를 완료 차단 사유로 삼지 않고, 접근성 이름·의미 있는 마크업·키보드 포커스 등 필요한 구현을 갖추는 데 집중한다. **Claude 전체 최종 검수 → Codex 교차 검증 → Claude 보완 → 최종 재검증** 후 Codex의 배포 작업으로 넘긴다.

## 5. 문서 운영 규칙

| 문서 | 목적 | 고치는 때 |
| --- | --- | --- |
| `guide.md` | 작업할 때 지킬 규칙·공통 설계·정책·배포 확인 목록 | 규칙·설계·정책이 바뀌었을 때, 작업을 마쳐 §3 상태가 바뀌었을 때 |
| `daily-work-log.md` | 날짜별 작업 내역 | 작업을 마쳤을 때(날짜 아래 작업 한 줄) |
| `file-feature-map.md` | 폴더·파일별 기능 | 파일을 만들거나 지우거나 역할이 바뀌었을 때 |
| `legal/` | 약관 관련 문서: 이용약관·개인정보 처리방침·가입 동의 문구와 그 근거인 개인정보 처리 목록(사용자 결정 2026-11-26: 삭제하지 않고 계속 운영) | 배포 준비 때 확정(§10.5). 이후 개인정보를 다루는 기능·보관 기간·외부 업체가 바뀌면 처리 목록과 처리방침을 함께 고치고, 사이트 문서 페이지와 내용을 맞춘다 |

- 세 문서에 같은 내용을 두 번 쓰지 않는다. 날짜·커밋·검사 수치는 `daily-work-log.md`와 커밋에만 남긴다.
- 기획 문서(`../docs/*.docx`)와 와이어프레임은 사용자가 요청할 때만 고친다.

## 6. 공통 기술 설계

### 6.1 전체 구조

```
브라우저 ──(같은 출처 /api/*)──> Next.js (rewrites) ──> FastAPI /api/v1 ──> Supabase PostgreSQL
                                   │ 서버 컴포넌트는 BACKEND_ORIGIN으로 직접 조회
FastAPI 수집 작업(app/sync) ──> API-Football Pro / NAVER API HUB 뉴스 ──> DB 저장
```

- 브라우저는 외부 API를 직접 호출하지 않는다. 모든 축구·뉴스 데이터는 백엔드가 수집해 DB에 저장하고, 화면 요청은 DB에서 응답한다(OPS-001).
- 프런트엔드는 `next.config.ts`의 `rewrites`로 `/api/:path*`를 백엔드로 넘긴다. 브라우저 기준 같은 출처가 되어 인증 쿠키를 `httpOnly`로 쓸 수 있다. `NEXT_PUBLIC_API_BASE_URL`은 01에서 `BACKEND_ORIGIN`(서버 전용, 기본 `http://localhost:8000`)으로 교체한다.
- 공개 데이터는 서버 컴포넌트에서 조회해 렌더링하고, 회원 데이터·실시간 갱신·변경 작업은 클라이언트에서 같은 출처 `/api/v1`로 요청한다. 현재 `cacheComponents`가 켜져 있으므로 세션·요청 의존 UI는 `<Suspense>` 안에 둔다. 작업 전 `frontend/AGENTS.md`와 `node_modules/next/dist/docs/`의 해당 가이드(Caching, Fetching Data, Authentication with Cache Components, rewrites, proxy)를 읽는다.

### 6.2 인증·계정 (02 담당)

Supabase Auth를 쓰지 않고 FastAPI에서 직접 구현한다. 가입 화면 안의 6자리 인증번호(10분 유효·1분 뒤 재발송·5회 실패 무효)를 먼저 확인한 뒤에만 계정을 만드는 규칙(미인증 계정 없음)과 기존 psycopg·DB 구조를 그대로 맞추기 위해서다.

| 항목 | 기준 |
| --- | --- |
| 비밀번호 | Argon2id 해시(`argon2-cffi` 또는 `pwdlib[argon2]`). 평문·가역 암호화 저장 금지 |
| 접근 토큰 | JWT(HS256, `AUTH_JWT_SECRET`), 만료 15분(기술 기본값). `kt_access` 쿠키: `httpOnly`, `SameSite=Lax`, `Path=/`, 운영 `Secure` |
| 갱신 토큰 | 무작위 256비트 값, DB에는 SHA-256 해시만 저장(`refresh_tokens`). 만료 14일, 사용할 때마다 교체(rotation), 교체된 토큰이 10초 넘게 지나 다시 오면 같은 계열 전체 폐기(재사용 감지). 10초 안의 재사용(두 탭 동시 갱신)은 새 쿠키 없이 200으로 답해 브라우저가 이미 받은 새 쿠키를 쓰게 한다. `kt_refresh` 쿠키 `Path=/api/v1/auth`, 두 쿠키 모두 브라우저 보관 14일(접근 토큰 유효성은 JWT 15분이 결정). 접근 토큰에 `users.token_version`(`ver`)을 넣어 비밀번호 변경·재설정 시 모든 세션을 끝낸다(02 구현). **잠금 순서는 계정 행(`users` FOR UPDATE) → 갱신 토큰·인증 행**으로 로그인·갱신·로그아웃·비밀번호 변경·재설정·탈퇴가 같다 — 순서가 엇갈리면 데드락(Codex R1). 변경을 기다린 갱신은 폐기된 토큰을 보고 거부되고, 변경과 겹친 로그인은 새 비밀번호로 다시 확인된다(Codex R4). 계정 행을 다루는 새 기능도 이 순서를 따른다 |
| 자동 갱신 | 클라이언트 요청이 `401 AUTH_EXPIRED`를 받으면 `POST /api/v1/auth/refresh`를 한 번만 시도하고 원 요청을 재시도한다. 동시에 여러 요청이 실패해도 갱신은 1회로 합친다(`session.ts` `refreshSession`). 갱신 실패 시 서버가 두 쿠키를 지우고 화면은 비회원으로 바뀐다. 평가 작성 중이면 본문은 `sessionStorage`(`kt-review-draft:<회원ID>:<경기ID>` — 같은 회원에게만 복원, 직접 로그아웃하면 삭제, Codex N1)에 남아 있고, 저장 요청이 401이면 `/login?returnTo=/matches/<id>&intent=review:<id>`로 이동한 뒤 로그인하면 같은 입력이 복원된다(자동 제출 없음, AUTH-003, 02 브라우저 확인) |
| CSRF | 쿠키 인증이므로 변경 요청(POST/PUT/PATCH/DELETE)은 `X-KickTab-Client: web` 헤더를 요구하고 `Origin`이 허용 목록과 다르면 거부한다 |
| 인증번호 | `email_verifications`(이메일·목적별 1행)에 목적(`signup`·`password_reset`)·코드 HMAC(키 `AUTH_JWT_SECRET`)·만료(10분)·실패 횟수·마지막 발송 시각 저장. 재발송은 1분 뒤(429 `RATE_LIMITED`·`Retry-After`), 새 번호가 이전 번호를 덮어써 무효화, 5회 불일치 시 `VERIFICATION_LOCKED`. 가입 요청 단계에서 이미 가입된 이메일은 409 `EMAIL_TAKEN`, 비밀번호 찾기는 이메일 계정이 없으면 404. 확인 성공 시 30분 유효한 일회용 `verificationToken`(해시 저장)을 발급해 가입·비밀번호 재설정에 쓰고, 성공하면 토큰만 지우고 행(마지막 발송 시각)은 남겨 재설정 직후에도 1분 재발송 대기가 지켜지게 한다(Codex 1차 확인 반영). 탈퇴 시 행 삭제. 요청 제한(메모리): 발송 IP 10분 5회·일 20회·서비스 시간당 60회·일 400회, 주소별 일 10회, 확인 IP 10분 30회, 로그인 IP 10분 20회·주소별 10분 10회, 가입·재설정 IP 10분 10회. 보관 기간(사용자 결정 2026-11-22): 인증번호 행은 마지막 발송 후 30일, 갱신 토큰은 만료·폐기 후 30일, 의견은 접수 후 1년이 지나면 삭제하고 끝난 평가 제한 값은 비우는 매일 03:30 KST 정리 작업 `retention`(단계마다 따로 커밋해 잠금을 겹쳐 잡지 않음, 재발송은 인증 행을 FOR UPDATE로 읽어 정리와 직렬화)(`app/sync/retention.py`·`app/services/retention.py`, 외부 요청 없음)이 삭제한다 |
| 메일 발송 | `EmailSender` 인터페이스 + **SMTP 구현**(§10 P-01, `app/services/mailer.py`). SMTP 설정(`SMTP_HOST`·`SMTP_USERNAME`)이 있으면 로컬을 포함한 모든 환경에서 Gmail STARTTLS로 실제 메일을 보낸다. 설정이 없으면 어떤 환경에서도 보내지 않고 503으로 실패시키며 인증번호를 로그에 남기지 않는다(`UnconfiguredSender`, Codex N6 — 콘솔 발송기는 삭제). 자동 테스트는 기록용 발송기를 의존성 주입으로 넣는다 |
| 가입 직후 로그인 | 가입 API가 계정 생성과 쿠키 발급을 한 트랜잭션 흐름으로 처리하고, 프런트엔드는 `GET /api/v1/auth/me`로 세션 성립을 확인한 뒤에만 회원 상태로 표시한다(계정 생성 성공과 인증 성립 구분) |
| 로그아웃 | 서버에서 계정 행을 먼저 잠근 뒤 그 브라우저의 갱신 토큰 계열 전체 폐기(R5: 앞선 갱신이 만든 토큰도 포함, 다른 브라우저 계열은 유지) + 쿠키 삭제 후 `/auth/me`로 비회원 확인(실패하면 '로그아웃하지 못했습니다' 안내, 성공으로 오인하지 않음). 공개 페이지는 유지, 회원 전용 페이지(`/mypage`)는 메인 이동(`returnTo.ts` `isMemberOnlyPath`). localStorage 관심 팀 복원(COM-005, 02 브라우저 확인). 클라이언트는 진행 중 갱신 응답을 기다린 후 로그아웃하며, 그 요청 중에는 새 갱신을 시작하지 않는다. 동시 로그아웃은 1회로 합친다. 요청 실패 후 세션 재확인에는 갱신을 허용하고, 비회원 확인에 성공해야 평가 초안을 지운다 |
| 로그인 복귀 | `/login?returnTo=<내부 경로>&intent=review:경기ID`(`returnTo.ts` `safeReturnTo`·`loginHref`). `/`로 시작하는 같은 사이트 경로만 허용하고 `//`·`/\`·제어 문자·다른 출처·인증 페이지는 `/`로 바꾼다. 평가 intent는 로그인 성공 후 `sessionStorage`에 남겨 경기 상세의 작성 영역(또는 본인 평가)으로 스크롤·포커스만 하고 자동 제출하지 않는다. 회원가입으로 넘어가도 같은 복귀 값을 유지한다. 개인 기사 저장 목적 intent는 폐지 |
| 소셜 로그인 | 일반 이메일 회원가입·로그인·마이페이지 완료 후 실제 연동. 이번에는 시안의 버튼만 제공하고 클릭 시 버튼 묶음 아래 `카카오·구글 로그인은 준비 중입니다. 이메일로 이용해 주세요.`를 `role=status`로 표시한다. 페이지 이동·팝업·토스트 없음. 같은 이메일 자동 연결 금지 |

### 6.3 DB·마이그레이션

- **도구:** SQLAlchemy 2.x(동기, psycopg 3 드라이버) + Alembic. 01이 `app/db/`(엔진·세션·`Base`, 지연 생성 `get_engine()`, 요청 의존성 `get_db`)와 `backend/migrations/`(리비전 `0001_sync_runs_feedback`, `0002_feedback_body_hash`)를 만들었다. 모델은 `app/models/`에 두고 `app/models/__init__.py`에 import해야 Alembic이 인식한다. 제약 이름은 `Base`의 명명 규칙을 따르고, 새 리비전 템플릿에 RLS 활성화 안내가 들어 있다. 연결 문자열은 `.env`의 `DATABASE_URL`을 코드에서 `postgresql+psycopg://`로 바꿔 쓰고, 기존과 같이 `sslmode=verify-full`·`certs/supabase-ca.crt`를 `connect_args`로 전달한다. 기존 `app/database.py`·`check_database`는 연결 점검용으로 유지한다.
- **규칙:** 스키마 변경은 마이그레이션 파일로만 한다(대시보드 수동 변경 금지). 한 기능 채팅의 마이그레이션은 기능 단위로 나누고 `downgrade`를 작성한다. 시간은 `timestamptz`(UTC 저장), 경기 묶음용 KST 날짜는 별도 `date` 컬럼으로 저장한다.
- **Supabase 공개 API 차단:** Supabase는 `public` 스키마를 Data API(PostgREST)로 노출할 수 있다. **모든 테이블 생성 마이그레이션에 `ALTER TABLE ... ENABLE ROW LEVEL SECURITY`를 포함하고 정책은 만들지 않는다.** 백엔드는 테이블 소유 역할로 접속하므로 영향을 받지 않는다. 사용자는 Supabase 대시보드에서 Data API 비활성화를 함께 검토한다(§9).
- **ID:** 외부 데이터(대회·팀·선수·경기)는 API-Football ID를 기본 키로 그대로 쓴다. 서비스 데이터(회원·후기 등)는 UUID(`users`) 또는 `bigint identity`를 쓴다.
- **누락값:** API가 비운 값은 `NULL`로 저장하고 0으로 바꾸지 않는다. 원본 상태 코드·원본 블록은 함께 보관해 재해석할 수 있게 한다.

**초기 테이블 설계(소유 채팅이 마이그레이션 작성)**

| 영역 | 테이블(주요 컬럼) | 소유 |
| --- | --- | --- |
| 운영 | `sync_runs`(job, params, started_at, finished_at, status, api_requests, error_summary), `feedback`(user_id NULL 허용, type NULL 허용, body ≤1000, page_path, created_at) | 01 |
| 회원 | **02 구현(`0019_member_accounts`, 2026-11-21):** `users`(id uuid, email 소문자 unique(CHECK `email = lower(email)`), nickname(`lower(nickname)` 고유 인덱스), password_hash(이메일 계정은 필수 CHECK), login_method email·kakao·google, token_version, created_at), `auth_identities`(소셜 후속용 구조만, provider·provider_user_id unique, 지금은 비어 있음), `email_verifications`(email·purpose unique, code_hash, expires_at, failed_attempts, last_sent_at, verified_at, token_hash, token_expires_at), `refresh_tokens`(token_hash unique, family_id, expires_at, revoked_at), `terms_agreements`(user_id, item_id terms_of_service·privacy_collection·age_14_or_older CHECK, item_version, confirmed, agreed_at, unique(user, item, version)), `member_favorites`(PK(user_id, team_id), team_id → teams CASCADE, created_at — 10팀 한도는 서비스가 회원별 advisory lock 안에서 확인). `reviews.user_id`·`review_reactions.user_id` → users **CASCADE**, `feedback.user_id` → users **SET NULL**. 모두 RLS. 북마크 테이블 없음. 공유 DB라 downgrade는 실행하지 않았다. **`0020_review_restrictions`(2026-11-22):** `users.review_restricted_until`(약관 제9조 평가 작성·수정 제한 종료 시각, NULL·과거 = 제한 없음). 운영 명령 `uv run python -m app.moderation restrict <email> --days 7|30`·`lift <email>`·`remove-review <id>`·`close-account <email> --confirm`(관리 화면 없음, 회원 알림 메일은 운영자가 kicktab2026@gmail.com에서 직접 보냄) | 02 |
| 기준 데이터 | **03 구현(`0003_reference_data`, 2026-11-19 `0017_competition_groups`: `group_key` 허용값에 `FIFA` 추가 — downgrade는 FIFA 대회 행(시즌·경기 연쇄 삭제)을 먼저 지운다):** `competitions`(id, group_key, type league/cup/uefa, name_en, name_ko, short_name, sort_order, active, logo_url), `competition_seasons`(competition_id, season, label, is_current, availability available/no_data, start/end_date, teams_synced_at, fixtures_synced_at, fixtures_failed_at), `teams`(id, name_en, name_ko, logo_url, country), `team_competition_seasons`(team_id, competition_id, season), `team_aliases`(team_id, alias, normalized, lang, ambiguous, for_search, for_news). `image_assets`는 권리 확보 자산이 생길 때(V-10) 만든다 — 그 전 `IMAGE_RIGHTS_ENFORCED=true`면 모든 이미지가 대체 이미지 | 03 |
| 경기 | **03 구현(`0004_fixtures`):** `fixtures`(id, competition_id, season, round, kickoff_at, kickoff_date_kst, status, finish_type, status_short_raw, status_long_raw, status_reason, elapsed, home/away_team_id, goals_home/away, score jsonb, venue_name/city, synced_at). **04 구현(`0006_match_detail`):** `fixture_details`(fixture_id PK, statistics/lineups/players jsonb 원본 블록, fetched_at, fetched_status, last_failed_at), `fixture_events`(fixture_id, seq PK, elapsed, extra, team_id, player_name, assist_name, type, detail, comments — 수집할 때마다 통째로 교체), `head_to_head`(fixture_id PK, payload jsonb, last_meeting_fixture_id, fetched_at, last_failed_at), `team_forms`(team_id PK, payload jsonb, fetched_at, last_failed_at). **05 구현(`0010_season_fixtures`):** `competition_seasons.season_fixtures_synced_at`·`season_fixtures_failed_at`(시즌 전체 목록 적재 상태 — 30분 목록 작업(`fixtures`)의 `fixtures_synced_at`·창과 분리), 인덱스 `ix_fixtures_season_status_kickoff`(season, status, kickoff_at). 관리 시즌(2025~현재)의 `competition_seasons` 행은 `reference`가 함께 저장하고 지우지 않는다. 시즌 전체 목록을 한 번이라도 적재한 시즌은 `/leagues` 응답에서 빠져도 `no_data`로 바꾸지 않는다(가용성·시작/종료일 유지, CMP-004) | 03(목록·상태) / 04(이벤트·상세 블록·상대 전적·팀 최근 흐름) / 05(시즌 전체 적재) |
| 뉴스 | **03 구현(`0005_news`):** `news_articles`(id, url_hash unique, url, source_domain, title, description, published_at, badge, fetched_at, expires_at), `news_article_teams`(article_id, team_id). 언론사명 매핑 표(`news_sources`)는 만들지 않았다(§10.3 D-03-1). | 03 |
| 후기·TOP 5 | **04 구현:** `0007_reviews` — `reviews`(id, user_id uuid(외래 키는 02), fixture_id, body ≤300(**`0015`에서 rating 삭제·body 필수·공백 금지(Python 공백 전체 기준, 공백뿐인 기존 행이 있으면 업그레이드 실패)**), created/updated_at, unique(user_id, fixture_id)), `review_reactions`(review_id, user_id, value ±1, PK). `0008_top5` — `top5_weeks`(week_start PK, status running·retry_scheduled·delayed·published, auto_attempts, current_attempt_id, last_error, next_retry_at, needs_manual, alert_sent_at), `top5_attempts`(시도 ID·trigger scheduled·retry·manual·시작/마감/종료 시각·outcome·error·model·prompt_version·curation_version·candidate_count·api_requests·evidence·llm_output), `top5_publications`(version identity PK = 공개 버전, week_start, kind list·none·delayed, selected_at, attempt_id), `weekly_top_matches`(week_start, rank PK, 주별 fixture_id 유일, reason, selected_kickoff_at, attempt_id) | 04 |
| 순위 | **06 구현(`0011_standings`):** `standings`(PK competition_id·season·group_name·team_id, group_order, rank, points, played, win/draw/lose, goals_for/against/diff, form, description(그 시즌 제공 문구 그대로), provider_updated_at, synced_at), `player_rankings`(PK competition_id·season·type(goals·assists·yellow·red CHECK)·position(제공 순서), player_id, team_id, value, yellowred(red 목록만, value에 합산하지 않음), synced_at), `players`, `player_season_stats`(§2), `league_syncs`(PK competition_id·season·kind(standings·goals·assists·yellow·red·player_stats CHECK), synced_at, failed_at, failure(안전한 요약), row_count). 모두 RLS. 저장은 응답이 완전할 때만 리그·시즌·종류 단위로 한 트랜잭션에서 교체하고(재실행해도 중복 없음), 실패·불완전 응답은 기존 행과 `synced_at`을 두고 `failed_at`·`failure`만 기록한다. **완전성 기준(Codex 1차 지적 1 보완):** 팀 순위 — 그룹별 순위 1..n·팀 중복 없음, 저장된 표보다 행 수가 줄지 않음, 모든 팀이 그 시즌 참가 팀(`team_competition_seasons`) 안, 그 시즌 그 리그 경기가 3경기 이상인 팀(`REGULAR_TEAM_MATCHES`)은 모두 포함(2025 분데스리가·리그1 참가 팀 19에는 경기 2개뿐인 승강 PO 상대 파더보른·생테티엔이 있어 참가 팀 수 일치 대신 이 규칙을 쓴다. 현재 시즌도 PO 경기가 적재되면 같다). 선수 순위 — 저장된 목록보다 짧은 응답 거부(처음 적재·시즌 초 짧은 목록은 허용). 선수 시즌 기록 — §6.5 페이지 규칙 + 저장된 줄보다 10% 넘게 감소 시 거부 | 06 |
| 팀 상세 | **08 구현(`0012_team_detail`):** `team_coaches`(team_id PK, coach_id·name·photo_url·since — 이 팀 경력 중 종료일 없는 줄의 최신 시작, 없으면 coach_id·name NULL = 수집했으나 현직 감독 미제공), `squad_members`(PK team_id·player_id, number, position(제공값 Goalkeeper·Defender·Midfielder·Attacker), synced_at — 현재 선수단, 시즌 열 없음: `/players/squads`가 현재만 제공), `team_season_stats`(PK team_id·competition_id·season, payload jsonb = `/teams/statistics` 응답 그대로), `transfers`(id identity, team_id, player_id·player_name(제공값, 선수 외래 키 없음), transfer_date, direction in·out CHECK, counterpart_id·name·logo(상대 팀 제공값, 팀 외래 키 없음), type_raw('N/A'는 NULL), season, half 1·2 CHECK, 고유 인덱스(`0014`): 공통 키 `(team_id, player_id, transfer_date, direction)`에 상대 팀 ID가 있으면 `counterpart_id`를, 없으면 `counterpart_name`을 붙여 중복을 막는다. 상대 팀 이름도 없으면 NULL을 같은 값으로 본다), `team_syncs`(PK team_id·season·kind(coach·squad·statistics·transfers CHECK), synced_at, failed_at, failure, row_count). `teams`에 venue_name·venue_capacity, `players`에 profile_checked_at 추가. 모두 RLS. **2026-11-18 `0016_team_player_stats`:** `team_player_stats`(PK team_id·player_id·competition_id·season, appearances·goals·assists NULL 허용(0으로 채우지 않음), rating numeric(5,3)(제공 '0'은 NULL), synced_at; 팀·선수·대회 외래 키, RLS) — 이 팀의 지원 대회 8개(5대 리그 + UEFA 3개) 줄만, `team_player_stats` 작업만 쓴다(06 `player_season_stats`는 리그 전체 줄로 따로 유지 — 두 작업이 서로의 행을 덮어쓰지 않음). `team_syncs.kind` CHECK에 `player_stats` 추가. 이적 `transfers`는 2026-11-18부터 제공 원본 그대로 저장하고 중복 정리는 응답 때 한다(D-08-6). '고정'은 열 대신 날짜로 판정한다: 시즌 S의 이적은 (S+1)-07-01 00:00 실행(6/30까지 반영된 기록, 기능 명세서 6.2)까지 다시 쓰고 그 뒤에는 그날 이후 실행으로 한 번 성공할 때까지(처음 수집이거나 7/1 마지막 갱신이 실패한 경우) 매일 다시 쓰고, 성공하면 고정(§6.5와 같음) | 08 |

관심 팀 비회원 최대 5개·회원 최대 10개·평가 경기당 1건·반응 평가당 1건은 DB 제약과 서비스 검증으로 보장한다. P-03에 따라 탈퇴 시 관심 팀·경기 평가·반응·계정을 삭제하고 집계에서 제외한다. 의견은 `feedback.user_id`만 `NULL`로 해제한다. 개인 기사 저장 테이블은 생성하지 않는다.

### 6.4 백엔드 API 형식

- 경로 접두사 `/api/v1`. 리소스 이름은 복수형 kebab-case. 상태 확인 `/health`는 유지한다.
- JSON 필드는 camelCase(Pydantic `alias_generator=to_camel`, `populate_by_name=True`). 시각은 ISO 8601 UTC(`2026-10-31T19:00:00Z`), 경기 묶음 날짜는 `kickoffDateKst: "2026-11-01"`처럼 별도 제공. 시간대 표기는 화면에 하지 않는다.
- **성공:** `{ "data": <객체|배열>, "meta": { ... } }`. 목록은 `meta.page`, `meta.size`, `meta.total`(페이지 방식) 또는 `meta.nextCursor`(뉴스 더 보기). 수집 데이터는 `meta.updatedAt`(마지막 수집 시각)을 넣는다.
- **오류:** `{ "error": { "code": "FAVORITE_LIMIT", "message": "관심 팀은 최대 5팀까지 등록할 수 있습니다.", "details": { } } }`. 메시지는 화면에 그대로 써도 되는 한국어. 내부 예외·SQL·외부 응답 원문은 응답과 서버 로그 어디에도 노출하지 않는다(미처리 예외는 종류만 기록).

| HTTP | code | 용도 |
| --- | --- | --- |
| 400/422 | `VALIDATION_ERROR` | 입력 형식 오류(`details.fields`에 항목별 사유) |
| 401 | `AUTH_REQUIRED` / `AUTH_EXPIRED` / `INVALID_CREDENTIALS` | 미인증 / 접근 토큰 만료(갱신 시도 대상) / 로그인 실패 |
| 403 | `FORBIDDEN` | 소유권 없음, CSRF 헤더 누락 |
| 404 | `NOT_FOUND` / `TEAM_DETAIL_UNAVAILABLE` | 없는 식별자(다른 데이터로 대체하지 않음) / 현재 상세 미제공 팀 |
| 409 | `CONFLICT`, `EMAIL_TAKEN`, `NICKNAME_TAKEN`, `FAVORITE_LIMIT`, `REVIEW_EXISTS`, `FEEDBACK_DUPLICATE`(01) | 중복·제한 |
| 410/422 | `VERIFICATION_EXPIRED`(410) / `VERIFICATION_INVALID`(422, `details.remainingAttempts`) / `VERIFICATION_LOCKED`(422) | 인증번호 만료 / 불일치·없음·인증 만료 / 5회 실패 |
| 403 | `REVIEW_RESTRICTED`(02, `details.until`) | 약관 제9조 평가 작성·수정 제한 중(본인 평가 삭제는 허용). `GET /auth/me`의 `reviewRestrictedUntil`로도 내려가며 경기 상세 작성 영역 대신 안내가 나온다 |
| 422 | `PASSWORD_CURRENT_MISMATCH` / `PASSWORD_RULE` / `PASSWORD_CONFIRM_MISMATCH`(02) | 비밀번호 변경의 항목별 오류 — `details.fields`에 `currentPassword` / `newPassword` / `newPasswordConfirm` 하나 |
| 429 | `RATE_LIMITED` | 요청 제한(`Retry-After` 헤더) |
| 503 | `UPSTREAM_UNAVAILABLE` / `MEMBERSHIP_UNKNOWN` | 수집 데이터 없음+외부 실패 / 팀 소속 확인 불가(07 `GET /teams`가 처음 사용, 프런트 `ApiErrorCode`에 추가) |
| 500 | `INTERNAL_ERROR` | 그 밖의 오류 |

- **부분 제공 블록:** 경기 상세 기록처럼 항목별 제공 여부가 다른 데이터는 `{ "status": "available" | "not_provided" | "not_yet" | "unavailable", "data": ... }`로 감싼다. `not_yet`은 라인업 발표 전처럼 시점상 아직 없는 경우, `unavailable`은 조회 실패다.
- **경기 상태:** `status`는 `scheduled | live | finished | postponed | cancelled | abandoned | unknown`, 종료 세부는 `finishType: normal | aet | pen | awarded | walkover`.

| API-Football `status.short`(대소문자 무시) | `status` | 비고 |
| --- | --- | --- |
| `TBD`, `NS` | scheduled | `TBD`는 `timeConfirmed: false` |
| `1H`, `HT`, `2H`, `ET`, `BT`, `P`, `LIVE`, `SUSP`, `INT` | live | 잠시 멈춤도 진행 중(D-17) |
| `FT` / `AET` / `PEN` | finished | finishType normal / aet / pen. 승부차기 스코어는 `score.penalty`로 분리 |
| `AWD` / `WO` | finished | finishType awarded / walkover. 평가 제공 보류(§10 P-05). TOP 신규 후보 제외·이미 선정된 항목 유지 |
| `PST` | postponed | 같은 경기 ID로 새 일시 반영 |
| `CANC` | cancelled | 실제 데이터에 `Canc`·`CANC` 혼재 |
| `ABD` | abandoned | '경기 중단', 중단 시점 스코어, 평가 보류. TOP 신규 후보 제외·이미 선정된 항목 유지 |
| 그 밖 | unknown | '확인 필요' |

- **팀 참조 공통 형태(`TeamRef`):** `{ "id", "nameKo": string | null, "nameEn", "crestUrl": string | null, "detailAvailable": true | false | null }`. 한국어 이름이 없으면 `nameKo`는 `null`이고 화면은 `nameEn`을 쓴다(`CompetitionRef.nameKo`도 같음). `null`은 소속 미확인(조회 중·실패)이며 강등으로 표시하지 않는다(D-15).
- **경기 요약 공통 형태(`MatchSummary`):** 경기 카드·TOP 5·팀 경기 목록이 같은 형태를 쓴다. `{ "id", "competition": { "id", "nameKo", "shortName" }, "kickoffAt", "kickoffDateKst", "timeConfirmed", "status", "finishType", "elapsed", "statusReason", "home": TeamRef, "away": TeamRef, "score": { "home", "away", "penaltyHome", "penaltyAway" } }`. 스코어·경과 시간이 없으면 `null`. 01이 스키마를 먼저 정의하고 03이 실제 데이터로 채운다(예정·연기·취소는 스코어 `null`, `elapsed`는 진행 중에만, `timeConfirmed`는 `TBD`·`PST`에서 `false`, 승부차기만 `penaltyHome`·`penaltyAway`). 필드를 바꾸면 이 줄을 갱신한다.
- **지난 경기·시즌 응답(05 구현):** `GET /seasons` → `data: SeasonItem[] { season, label('2026-27'), current }`(관리 시즌 중 `available` 대회가 하나라도 있는 시즌, 최신순). `GET /results?season=&competitions=&team=&page=` → `data: ResultsPage { season: SeasonItem, team: TeamRef \| null, matches: MatchSummary[] }`, `meta: ResultsMeta { page, size(10), total, updatedAt, failedCompetitionIds }`. `status = finished`만(일반 normal/aet/pen과 행정 awarded/walkover — `finishType`으로 구분, 행정 종료 스코어는 제공값 그대로), 예정·진행·연기·취소·중단 제외, 킥오프 최신순, 날짜 조건 없음. `season` 생략 = 현재 시즌, 미지원 시즌 404 `NOT_FOUND`(대체 없음), `competitions`는 지원 21개 대회 ID(아니면 422 — 시즌 변경 시 대회 조건을 유지하므로 그 시즌 `no_data` 대회도 받아 저장된 결과만 돌려준다), 없는 팀 404, 참가하지 않은 팀은 빈 목록, 마지막 페이지를 넘으면 빈 목록+`total`. 범위 안 `available` 대회가 하나도 적재에 성공한 적이 없으면 503 `UPSTREAM_UNAVAILABLE`. 적재 후 갱신 실패·일부만 저장된 대회는 저장된 결과를 그대로 돌려주고 `failedCompetitionIds`에 넣는다(결과 없음으로 단정하지 않음, CMP-004). 화면 URL의 팀·대회·페이지 값이 숫자가 아니면 요청하지 않고 '조회 조건을 확인할 수 없습니다'(+필터 초기화)를 보여준다 — 생략·빈 값만 '전체·첫 페이지'다(`useResultsParams().invalid`). 화면은 404·422에 서버 문구와 '필터 초기화'(팀·대회가 있을 때만), 5xx에 '다시 확인'을 보여준다. `GET /teams/search?q=&season=`(§2). `GET /competitions`의 각 항목에 `seasons: CompetitionSeasonInfo[]`(관리 시즌 전체, 최신순) 추가. 2026-11-20: API 변경 없음 — 화면은 `size` 10 그대로 `ceil(total/10)` 페이지(2025-26 전체 4,198경기 = 420페이지)를 공통 `Pagination`으로 이동하고, 클럽 월드컵(15)처럼 선택 시즌이 `no_data`인 FIFA 대회는 대회 선택에서 숨긴다(빈 결과·실패로 보이지 않음, `failedCompetitionIds`는 개최 시즌의 실패만).
- **리그 순위 응답(06 구현, 06 개선 2026-11-17):** `GET /standings?league=&season=` → `data: LeagueStandings { league: CompetitionRef, season: SeasonItem, groups: StandingGroup[{ name, rows: TableRow[{ rank, team: TeamRef, played, win, draw, lose, goalsFor, goalsAgainst, goalsDiff, points, recent: RecentMatch[≤5]{ fixtureId, kickoffAt, kickoffDateKst, competition(2026-11-20 추가: 그 대회 `name_ko`), home·away: TeamName{ id, nameKo, nameEn }, goalsHome, goalsAway, result: W|D|L(그 행 팀 기준) } }] }], complete }`, `meta: StandingsMeta { updatedAt(마지막 성공 수집), refreshFailed(이후 갱신 실패 — 저장된 표를 그대로 보여줌) }`. `recent`는 저장된 그 대회·시즌 종료 경기(점수 있음) 중 팀별 최근 5개, 오래된 순(UEFA는 'League Stage' 라운드만 — 예선 'Play-offs'·'Playoff round'와 토너먼트 제외). `complete` = 그 표의 경기(리그 시즌 전체·UEFA 리그 페이즈)가 모두 저장돼 있고 모두 끝남 — 행 수가 아니라 저장된 순위표 팀끼리의 서로 다른 대진으로 센다: 리그는 n팀이 서로 홈·원정 한 번씩 종료 경기가 있는 (홈, 원정) n×(n−1)쌍, UEFA는 종료 경기가 있는 서로 다른 대진 36×8÷2=144(컨퍼런스리그 6경기 108)이고 모든 팀이 정확히 8(6)대진. 순위표 팀끼리의 경기 중 예정·진행·연기·중단·미확인이 하나라도 있으면 false. 승강 플레이오프(2부 팀 상대)·취소 기록·홈과 원정이 같은 팀인 비정상 행은 빠진 경기를 메우지 못한다(Codex 2차 지적 2·3차 지적 1·4차 지적). 경기 저장(`upsert_fixtures`)도 홈·원정 팀이 같은 경기 응답은 건너뛰어 저장된 정상 경기를 그대로 둔다 — 화면이 '강등권'→'강등', '16강 직행권'→'16강 직행'으로 바꾸는 기준. 강등·승강 PO·UEFA 구간은 응답에 없고 화면이 순위 위치로 판단한다(이전 `form`·`description`·`zone` 응답 필드는 06 개선에서 삭제, DB 컬럼은 제공 원본으로 보존). `/standings/summary` 행은 `StandingRow`(최근 경기 없음). `league`는 5대 리그와 UEFA 3개(2·3·848, 리그 페이즈 표)만(국내 컵은 404 `NOT_FOUND`), `season` 생략 = 현재, 미지원 시즌·그 시즌 데이터 없는 리그 404, 한 번도 수집되지 않았으면 503 `UPSTREAM_UNAVAILABLE`, 수집됐지만 표가 비었으면 `groups: []`. `GET /standings/summary` → `data: { season(현재), leagues: [{ league, status: available | not_collected, refreshFailed, updatedAt, rows: 첫 그룹 상위 6행 }] }`(2026-11-20부터 5대 리그 + UEFA 3개 리그 페이즈 8개 순서 — 토너먼트가 시작돼도 마지막 리그 페이즈 표; 한 대회 미수집이 다른 대회를 가리지 않음, 모두 미수집이면 503). `GET /player-rankings?league=&season=&type=goals|assists|yellow|red|saves` → `data: PlayerRankings { type, league, season, items: PlayerRankItem[{ rank, tied, player{ id, name, photoUrl }, team: TeamRef | null, value(없으면 null), yellowRed(red만) }], excluded(saves만: 선방 값이 하나라도 null인 골키퍼 수) }`, `meta: StandingsMeta`. 값 0인 기록은 5종 모두 빼고 각 목록은 최대 20명(2026-11-25 사용자 결정 — 0은 목록 끝에만 있어 다른 순위 불변, null은 유지). 4종은 제공 순서 그대로(rank = 제공 위치, tied 항상 false — 20명에서 잘린 목록이라 밖의 동률을 알 수 없음, 화면은 꽉 찬 목록에 '20위 밖에 같은 기록의 선수가 더 있을 수 있습니다.'), saves는 전체 골키퍼로 순위·공동을 계산한 뒤 상위 20명만 보내며, `player_season_stats`의 골키퍼(`position = Goalkeeper`) 줄을 선수별로 합산하고 null 줄이 있는 선수는 제외, 같은 값은 공동 순위(1,1,3, `tied`), 표시 팀은 출전이 가장 많은 팀. 잘못된 type은 422, 국내 컵은 404(2026-11-20부터 UEFA 2·3·848도 제공 — 예선 포함 대회·시즌 전체, 단계별 재집계 없음, 선방은 5대 리그와 같은 집계; 선수 이름은 HTML 엔티티 해제). 팀 링크는 모두 현재 시즌 허용 집합(`detailAvailable`). **토너먼트(06 개선):** `GET /knockouts?league=2|3|848&season=&stage=playoff|r16|qf|sf|final` → `data: KnockoutRound { league, season, stage, ties: KnockoutTie[{ state: finished|live|scheduled|undecided, home·away: KnockoutTeamSlot{ team: TeamRef|null, winnerOf: TeamRef[2]|null }, legs: KnockoutLeg[{ fixtureId, leg(1·2 — 그 대진 경기가 모두 저장됐을 때만, 하나만 저장됐으면 1차전인지 2차전인지 알 수 없어 null), kickoffAt, timeConfirmed, status, finishType, home, away, score: MatchScore }], legsNeeded(결승 1, 그 외 2), aggregateHome·aggregateAway·penaltyHome·penaltyAway(종료만, home=1차전 홈팀), winner }] }`, `meta: StandingsMeta { updatedAt(시즌 경기 목록 마지막 적재), refreshFailed }`. 단계 = 공급사 라운드 'Round of 32'(플레이오프)·'Round of 16'·'Quarter-finals'·'Semi-finals'·'Final', 단계별 대진 수 8·8·4·2·1. 저장된 경기의 팀 쌍으로 대진을 묶고(취소 제외), 모든 경기가 끝나면 합산(연장 포함 goals) → 동점이면 마지막 경기 승부차기로 승자(원정 다득점 없음). 대진이 하나만 빠진 단계는 그 단계 경기에 나오지 않은 직전 라운드 대진으로 채운다(2개 → 양쪽, 승부 미정이면 `winnerOf`='A–B전 승자'; 1개 → 한쪽 + 반대쪽 `team`·`winnerOf` 모두 null='상대 미정'). 나머지 빈 대진은 `undecided`('예정 · 대진 미정') — UEFA 추첨 결과가 필요한 경로는 추정하지 않는다. 컵·5대 리그 404, 잘못된 단계 422, 미지원 시즌 404, 시즌 경기 목록 미적재 503. 화면 조회 때 공급사 호출 없음.
- **팀 탐색 응답(07 구현, 2026-11-18 개선):** `GET /teams?league=&q=&team=&page=` → `data: BrowseTeam[] { team: TeamRef, league: CompetitionRef }`, `meta: TeamsMeta { page, size(12), total, updatedAt(목록 리그들의 마지막 팀 목록 수집 시각) }`. 현재 시즌(`CURRENT_SEASON`) 5대 리그의 `team_competition_seasons`만(과거 시즌·컵/UEFA 전용 팀 없음, 한 팀이 두 리그에 있으면 리그 순서상 앞의 리그 하나). `league`는 5대 리그 ID만 — 정수이면서 5대 리그가 아니면(0·음수·컵·UEFA·없는 ID) 404 `NOT_FOUND`, 정수가 아니면 422 `VALIDATION_ERROR`(Codex 1차 지적 4로 통일), `q`(1~40자, 빈 값·41자 이상 422)는 `match_teams()` 별칭 검색 — 모호한 별칭은 해당 팀 모두, 리그 조건과 함께 적용. 정렬: 검색 없으면 리그 순서(Premier League → LaLiga → Serie A → Bundesliga → Ligue 1) 뒤 표시 이름(한국어 우선) 가나다순, 검색이면 일치 정도순. 대상 리그 중 하나라도 현재 시즌 팀 목록이 수집되지 않았으면(`competition_seasons.teams_synced_at` NULL) 503 `MEMBERSHIP_UNKNOWN`(빈 목록·일부 목록으로 바꾸지 않음), 일치 없음은 빈 목록+`total` 0, 마지막 페이지를 넘으면 빈 목록+`total`, `page` 0·형식 오류 422. 외부 API 호출 없음. 화면 URL의 잘못된 리그·페이지·40자 넘는 검색어는 요청하지 않고 '조회 조건을 확인할 수 없습니다'+'필터 초기화'. 재조회 실패는 마지막으로 확인한 목록(페이지 초과 안내 포함)을 유지하고 '팀 목록을 다시 확인하지 못했습니다'+'다시 확인'. `team`(1~2,147,483,647, 아니면 422)은 그 팀 하나만 — 선택 리그·현재 시즌 소속이 아니면 빈 목록+`total` 0, 있으면 `q`는 쓰지 않는다(렌·바르셀로나·파리처럼 이름이 다른 팀 이름에 들어가 단어 검색으로는 고른 팀만 보일 수 없기 때문). 화면 검색(2026-11-18): 공통 `TeamSearch` 자동완성 후보 선택 = `team`(리그는 '전체'로), 후보 없이 Enter = `q`(현재 리그 안), X·입력 전체 삭제 = 해제, 리그 변경 = `team` 해제(`q` 유지), 모든 검색은 기록 1단계·같은 조건의 Enter는 이동 없음. 이전의 0.3초 자동 반영·연속 입력 기록 처리는 삭제했다. 소속 미확인은 '현재 소속을 확인하지 못했습니다 · 강등으로 단정하지 않고 팀 링크를 잠시 보류합니다.'(Figma 57:836), 첫 조회 실패는 '정보를 불러오지 못했습니다 · 잠시 후 다시 시도해 주세요.'(57:766).
- **팀 상세 응답(08 구현, 2026-11-18 수정):** 영역마다 따로 조회한다. 모든 경로의 팀 판정(`detail_access`): 없는 팀 404 `NOT_FOUND`, 허용 집합 밖(강등 등) 404 `TEAM_DETAIL_UNAVAILABLE`, 소속 미확인(허용 집합 미완성 또는 그 팀 리그의 현재 시즌 팀 목록 미수집) 503 `MEMBERSHIP_UNKNOWN`, 2³¹ 이상·0 이하 ID는 422. `GET /teams/{id}` → `TeamOverview { team: TeamRef, league: CompetitionRef, season: SeasonItem, standing, coach: { status, data: { name } \| null }, venue: { status: available|not_provided|unavailable, data }, recent: RecentMatch[≤5] }`(standing = `standings` 현재 시즌 rank·points, 미수집 unavailable; coach 행 없음 unavailable·이름 없음 not_provided; recent = 친선 제외 전체 공식 종료 경기 최근 5개를 **오래된 순**(마지막이 최신) — 2026-11-20(06)부터 04 `team_forms`(`/fixtures?team=&last=10`)가 원천: 미지원 공식전·슈퍼컵·클럽 월드컵 포함, 열 때 `ensure_form`(저장된 새 종료 경기 또는 7일 경과 시만 1~2회, 실패 시 기존 목록 유지·5분 대기), 한 번도 받지 않았으면 저장된 지원 대회 종료 경기로 대체. 06 순위 표와 같은 `RecentMatch { fixtureId, kickoffAt, kickoffDateKst, competition, home, away: { id, nameKo, nameEn }, goalsHome, goalsAway, result: W|D|L }` — 결과는 공급사 승자 표시(승부차기 포함), 동점이면 무). `GET /teams/{id}/fixtures` → `{ upcoming: MatchSummary[≤3](진행 중 먼저, 예정은 킥오프 3시간 지난 미시작까지), recent: MatchSummary[≤5](종료 최신순) }`, `meta { updatedAt, failedCompetitionIds(그 팀이 이번 시즌 참가한 대회 중 시즌 목록 미적재·실패) }` — 현재 시즌 저장 경기만, 시즌 목록이 한 번도 적재되지 않았고 결과가 없으면 503. `GET /teams/{id}/squad` → `TeamSquad { season, players: [{ player{id, name(HTML 엔티티 해제), photoUrl}, number, position, nationality(제공 영문 그대로), flagUrl(국기, 없으면 null), totals: { appearances, goals, assists }(값마다 줄 하나라도 null이면 null) \| null(이번 시즌 줄 없음), competitions: [{ competition: CompetitionRef, appearances, goals, assists, rating(제공값 '0'은 null) }] }], missingCompetitions: CompetitionRef[](이번 시즌 종료 경기가 있는데 선수 줄이 없는 지원 대회 → 화면 '부분 집계') }`, `meta { updatedAt(선수단), refreshFailed(선수단 또는 선수 기록 갱신 실패) }`(선수단 미수집 503) — 이번 시즌 개최된 지원 대회(공통 대회 마스터: 리그·국내 컵·슈퍼컵·UEFA·클럽 월드컵, 2026-11-20 `record_competitions`)의 이 팀 줄만, 합계 평점 없음. `GET /teams/{id}/season-stats?season=` → `TeamSeasonStats { season, league, status: available|not_provided|not_participated, record: { wins·draws·loses·goalsFor·goalsAgainst·cleanSheets: {home, away, total}, formation } \| null, standing }`(season은 이번·지난 시즌만, 그 밖 404. 지난 시즌에 그 리그 참가 기록이 없으면(승격 팀) 호출 없이 not_participated, 기록이 없으면 not_provided. 미수집 503). `GET /teams/{id}/transfers?season=` → `TeamTransfers { season, halves: [{ half: first|second, label('26-27 전반기'), period('2026년 6~12월'), state: open|not_started, arrivals, departures(바로 보이는 줄), otherArrivals, otherDepartures('기타 이동'): TransferGroup[{ playerId, playerName, moves: [{ transferDate, direction: in|out, counterpart{id, name(아는 팀은 한국어)}, type }] }] }] }`(2026-11-20: 같은 반기 같은 선수의 이동을 한 줄로 묶고 마지막 이동 방향의 목록에 둠, 이동마다 날짜·방향·상대·유형 유지, 한 이동이라도 바로 보이면 줄 전체가 바로 보임 — `group_moves`·`judge_move`(D-08-6a). 응답 때 `merge_transfers`로 중복 정리, 날짜 오름차순, 금액 없음 — D-08-10, 미수집 503). `GET /news?team=` → 그 팀에 연결된 만료 전 기사 최신 **24개**(`TEAM_NEWS_LIMIT`, 뱃지 없는 기사 포함, `badge`로 더 좁힐 수 있음 — 메인은 `NEWS_LIMIT` 48개 유지), 없는 팀 404, 뉴스가 한 번도 수집되지 않았으면 503. 화면은 영역별 `DataState`(로딩·빈 결과·일부 미제공(갱신 실패 시 마지막 확인 데이터+'다시 시도')·조회 실패+'다시 시도')로 구분한다.
- **메인 일정 응답(03):** `GET /competitions` → `data: [{ id, nameKo, shortName, group: EPL\|LaLiga\|SerieA\|Bundesliga\|Ligue1\|UEFA\|FIFA, currentSeason: { season, label, availability: available\|no_data } \| null, seasons(05) }]`. `GET /fixtures/availability`(03 2026-11-19) → `data: { today, start, end, dates: [{ date, competitionIds, unknownCompetitionIds }] }` — **공통 경기일 기간**: 저장된 활성 대회 경기(취소 제외)가 있는 KST 날짜만, 오늘 이전 3개 + 오늘(경기 있으면) + 이후 17개(`services/fixtures.py`의 `schedule_period()`·`PAST_MATCH_DAYS`·`FUTURE_MATCH_DAYS`, 채우려고 날짜를 만들지 않음). `unknownCompetitionIds`는 그날 경기가 있을 수 있는데 확인되지 않은 대회(30분 작업 범위 안이면 그 작업 결과, 밖이면 시즌 전체 적재 결과로 판정 — `covered()`). `GET /fixtures?date=YYYY-MM-DD`(KST, 기본 오늘, 기간의 처음~끝(오늘 포함) 밖은 422) → `data: MatchSummary[]`(지원 대회 전체, 킥오프·대회 순), `meta: ScheduleMeta { updatedAt, failedCompetitionIds, checkedAt, checkedThrough, delayed }`(03 2026-11-10: 모든 대회 마지막 성공 중 가장 이른 시각·모두가 확인한 마지막 날짜·`delayed` = `checkedAt` 후 75분 초과 — `/fixtures`·`/fixtures/next`·`/fixtures/team` 공통) — 대회·팀 필터는 화면에서 적용(날짜 빈 결과와 필터 빈 결과 구분). 한 번도 수집되지 않았거나 모든 대회가 실패하고 결과가 없으면 503 `UPSTREAM_UNAVAILABLE`, 일부 대회만 실패하면 200 + `failedCompetitionIds`. `GET /fixtures/next?teams=1,2`(양의 정수 1~5개, 아니면 422) → `data: { teams: TeamRef[], matches: MatchSummary[] }`(팀마다 진행 중 또는 가장 가까운 예정 1경기, 진행 중 우선, 맞대결 1회), `meta: ScheduleMeta`. `GET /fixtures/team?team=<id>`(03 일정 UX 후속) → `data: TeamSchedule { team: TeamRef, start, end, matches: MatchSummary[] }`(공통 경기일 기간의 처음~끝 KST 사이 저장된 해당 팀 경기 전체, 킥오프 순, 외부 API 호출 없음), `meta: ScheduleMeta`. 대회 조건은 화면에서 적용, `failedCompetitionIds`는 화면이 '일부 대회 확인 실패'·'일정 없음 단정 금지'에 쓴다. 팀 ID 형식 오류 422, 없는 팀 404, 한 번도 수집 안 됨 503. `GET /teams/search?q=`(1~40자) → `data: TeamRef[]`(최대 10개). `GET /news?badge=&cursor=&size=`(size 1~24, 기본 6) → `data: NewsItem[] { id, badge, title, description \| null, url, sourceDomain, publishedAt }`, `meta: NewsMeta { nextCursor, updatedAt, stale, total, noNew }`(저장 기사도 없고 수집이 실패·미실행이면 503). `GET /news/{id}/link` → `data: { url, status: reachable\|gone\|unknown }`(원문 HEAD→GET 헤더 1회 확인, 404/410만 gone, 요청 제한 IP별 분당 30회·전체 300회).
- **TOP 5 응답(04 구현, 2026-11-03):** `GET /api/v1/top-matches/current` → `data: TopMatches { version(공개 버전, 공개된 적 없으면 null), view: list|none|delayed, week{start,end}(표시 결과의 실제 소속 주, delayed는 준비 중인 이번 주), currentWeek{start,end}(현재 KST 주 — `week`가 앞이면 지난주 유지), selectedAt, items[rank, reason, selectedKickoffAt(선정 당시 킥오프, D-01-10), match: MatchSummary(최신)] }`, `meta: { updatedAt }`(목록 경기의 `fixtures.synced_at` 최대값). 표시 규칙(`shown_publication()`): 이번 주 공개본이 있으면 그것, 없으면 바로 지난주의 list/none 공개본(실제 기간·선정 시각 그대로), 그 밖(공개 이력 없음·지난주 지연·2주 이상 전)은 이번 주 `delayed`. `GET /api/v1/top-matches/version` → `{ version, currentWeekStart }`(열린 화면의 교체 감지용). 사용자 조회는 선정 작업을 실행하지 않는다. 작업 내부 상태(선정 중·첫 실패·재시도)는 응답에 없다.
- **경기 상세 응답(04 구현):** 영역마다 따로 조회해 한 영역 실패가 다른 영역을 가리지 않는다. 없는 ID는 404 `NOT_FOUND`(다른 경기로 대체하지 않음). `GET /fixtures/{id}` → `MatchInfo { match: MatchSummary, round, seasonLabel, statusLong, statusCode(제공사 원문 — 행정 종료 사유 표시용), reviewsAvailable, headToHeadAvailable }`, `meta.updatedAt`(경기 마지막 확인). `GET /fixtures/{id}/detail` → `MatchRecords { events, statistics, lineups, players }` 각 블록 `{ status: available|not_provided|not_yet|unavailable, data }` — `MatchEvent { elapsed, extra, side, type: goal|card|subst|var|other, detail(제공사 원문), player(교체는 나간 선수), assist(교체는 들어간 선수) }`, `StatRow { key(제공사 항목명), home, away(숫자, 없으면 null), percent }`(값이 하나도 없는 항목 제외, Figma 7항목 순서 우선), `TeamLineup { side, formation, coach, startXi, substitutes[number, name, position] }`, `PlayerRating { playerId, name, photoUrl, side, rating }`(제공사 평점, 출전하지 않은 선수와 '0' 자리값 제외, 평점순), `meta.updatedAt`(마지막 상세 수집). `GET /fixtures/{id}/head-to-head` → `{ meetings{status, data: PastMeeting[≤5], summary{homeWins, draws, awayWins}}, homeForm, awayForm: FormBlock{status, data: FormMatch[≤5]{kickoffDateKst, competition, opponentName, venue, goalsFor, goalsAgainst, result W|D|L}} }`(친선 제외 공식 종료 경기, 팀 이름은 아는 경우 한국어). `GET /fixtures/{id}/reviews` → `ReviewList`. **04 개선(2026-11-11):** `MatchInfo.reviewsAvailable` = `review_open()`(진행 중·일반 종료). `ReviewList.summary`는 `{ count }`만, `ReviewItem.rating` 삭제, `body`는 필수 문자열. `/fixtures/{id}/detail`은 예정·연기에 외부 조회를 하지 않고(빈 블록 `not_yet`), 화면도 킥오프 전에는 이 경로를 부르지 않는다. 선수·감독 이름(타임라인, 라인업, 선수 평점)은 제공사 영문 그대로 보내되 HTML 엔티티만 해제한다(번역·음역 없음). **2026-11-19:** 응답 형식 변경 없음. 타임라인은 `MatchEvent.side`(home/away/null)로 열을 정하고 null은 '소속 미확인'으로 가운데 표시한다. 새 컵 7개 경기도 같은 응답·블록 상태를 쓴다.
- **메인 일정 URL·복귀(03, 2026-11-19 갱신 — 21일 달력 폐기, 공통 경기일 기간):** 날짜 막대는 `/fixtures/availability`의 날짜만 그린다(요일+월/일, 오늘은 요일 유지 + 점·접근성 이름 '오늘'). `date`가 없으면 오늘(경기 있으면) 또는 현재 대회 조건의 가장 가까운 미래 경기일(`defaultMatchDate()`), 미래가 없으면 '예정 일정 없음'. 대회 좁히기는 같은 기간 안 합집합만 남기고(미확인 날짜는 유지), 선택일이 확인된 무경기면 가장 가까운 오늘/미래 경기일로 이동(`nearestMatchDate()`). 기간 밖·형식 오류 `date`는 서버에 보내지 않고 '조회할 수 없는 날짜' + '기본 경기일 보기'. 첫 위치는 가장 가까운 과거 경기일부터(320·375px는 4칸, 그 이상 5칸 이상). 이하 팀 보기 규칙은 그대로다. 위 `GET /fixtures/team`이다. URL은 `/?date=2026-11-14&from=135&team=42&competitions=39` — **03 2026-11-10 개정(기획 SCH-003·004·006):** 새 팀을 고르면(검색 후보·관심 팀 버튼) '전체 대회'에서 시작하고(`competitions` 삭제), 날짜 보기에서 처음 팀을 고를 때만 그 직전 대회 조건을 `from`(전체였으면 `all`)에 저장한다. 팀 보기의 `competitions`는 그 팀 일정을 좁히는 조건이며, 팀 보기 안에서 대회를 바꾸거나 다른 팀으로 바꿔도 `date`·`from`(복귀 기준)은 덮어쓰지 않는다. 해제(× 버튼·입력 전체 삭제·같은 관심 팀 재클릭)는 `team`·`from`을 지우고 `from`의 대회를 되돌려, 저장된 날짜·막대 위치·대회로 복귀한다(`from` 없는 공유 링크는 전체 대회). 계산은 `useScheduleParams.ts`의 `withTeam()`·`withoutTeam()`(테스트 `match-regressions.test.mjs`). 검색어 입력 중에는 조건을 바꾸지 않는다. 전체 초기화는 `/`(기본 경기일·전체·팀 없음·초기 위치·6개, 관심 팀·뉴스·순위 선택 유지). 팀·대회 변경은 history push, 날짜 이동은 replace. 자정 기준일 변경: `useScheduleParams`의 `useKstToday()`가 다음 KST 자정(+1초)과 탭이 다시 보일 때 오늘을 다시 계산해 날짜 막대·'오늘'·날짜 미지정 보기를 새 날짜로 옮기고, 기간 조회 키가 바뀌어 새 기간을 다시 조회한다. 팀 조회 키는 `fixtures.team(teamId, period)`(period = `today|start|end`)라 자정뿐 아니라 같은 날 기간의 시작·끝이 바뀌어도 팀 일정을 다시 조회한다(Codex N5·2차 N10). 팀 모드의 기간 표기는 응답의 `start`·`end`(서버 KST 기준)를 써서 표시 경기와 항상 일치한다. 브라우저 시계를 자정 직후로 바꿔 확인했고 실제 자정 경과는 미확인. 생성 타입 `TeamSchedule`·`TeamScheduleResponse` 반영.
- **프런트엔드 타입:** 백엔드 OpenAPI(`/openapi.json`)에서 `openapi-typescript`로 `src/lib/api/schema.d.ts`를 생성한다(`npm run gen:api`). 손으로 타입을 중복 작성하지 않는다.

**초기 엔드포인트 목록(담당 채팅이 세부를 확정하고 이 표를 갱신)**

| 구분 | 엔드포인트 | 담당 |
| --- | --- | --- |
| 공통 | `GET /api/v1/top-matches/current`, `POST /api/v1/feedback`(요청 `{ body, type: bug·suggestion·other, pagePath? }`, 유형 필수(사용자 결정 2026-10-31), 본문 앞뒤 공백 제거 후 1~1,000자, 성공 201 `{ data: { id, createdAt } }`) — 01 구현 | 01 |
| 인증 | **02 구현:** `POST /auth/email-codes`(`{ email, purpose: signup\|password_reset }` → `{ expiresAt, resendAt }`), `POST /auth/email-codes/verify`(`{ email, purpose, code }` → `{ verificationToken, expiresAt }`), `POST /auth/signup`(201, `{ email, verificationToken, nickname, password, passwordConfirm, agreements: { termsOfService, privacyCollection, age14OrOlder } }` — 셋 중 하나라도 누락·false·문자열이면 422, 계정 없음), `POST /auth/login`, `POST /auth/refresh`(실패 401 + 쿠키 삭제), `POST /auth/logout`(204), `POST /auth/password-reset`(`{ email, verificationToken, newPassword, newPasswordConfirm }`), `GET /auth/me` → `{ data: Member | null }`(`Member { id, email, nickname, loginMethod, createdAt }`, 비회원은 200 `null` — 비회원 방문마다 401 콘솔 오류가 찍히지 않게, 만료는 401 `AUTH_EXPIRED`) | 02 |
| 계정·관심 팀 | **02 구현:** `PATCH /me/password`(`{ currentPassword, newPassword, newPasswordConfirm }` → `Member` + 새 쿠키, 다른 세션 종료), `DELETE /me`(204, 탈퇴 P-03), `GET /me/favorites` · `POST /me/favorites`(`{ teamId }`, 409 `FAVORITE_LIMIT`, 팀 상세 제공 팀만) · `DELETE /me/favorites/{teamId}` → `MemberFavorites { teams: TeamRef[](등록 순), max: 10 }`, `GET /me/reviews` → `MyReview[]`. `GET /fixtures/next?teams=`는 1~10개(02) | 02 |
| 기준·일정 | `GET /competitions`, `GET /fixtures?date=`, `GET /fixtures/next?teams=`, `GET /fixtures/team?team=`, `GET /teams/search?q=` — 03 구현(§6.4 메인 일정 응답). 실시간은 같은 `GET /fixtures` 폴링으로 처리해 `/fixtures/live`는 만들지 않았다. 05가 `/teams/search`에 시즌 범위를 추가 | 03 |
| 뉴스 | `GET /news?badge=&cursor=&size=`, `GET /news/{id}/link` 및 원문 확인, `team` 조건. 회원별 기사 저장 API 없음 | 03·08 |
| 경기 상세 | **04 구현:** `GET /fixtures/{id}`(`MatchInfo`), `GET /fixtures/{id}/detail`(`MatchRecords`), `GET /fixtures/{id}/head-to-head`(예정·연기만, 그 밖은 409 `CONFLICT`), `GET /fixtures/{id}/reviews?sort=popular\|latest`(정상 종료만, 그 밖은 409), `GET /top-matches/version`. **02 구현:** `POST /fixtures/{id}/reviews`(201 `ReviewItem`, 409 `REVIEW_EXISTS`·닫힌 경기 `CONFLICT`), `PATCH /reviews/{id}`(본인·열린 경기만), `DELETE /reviews/{id}`(204, 본인이면 언제나), `PUT /reviews/{id}/reaction`(`{ value: 1\|-1 }`)·`DELETE /reviews/{id}/reaction`(본인 평가 403), `GET /me/reviews`. 목록 `ReviewItem`에 `mine`·`myReaction`이 추가됐고 `authorNickname`은 `users.nickname`. 본문은 앞뒤 공백을 지우고 1~300자 | 04·02 |
| 지난 경기 | **05 구현:** `GET /results?season=&competitions=&team=&page=`, `GET /seasons`, `GET /teams/search`의 `season` | 05 |
| 순위 | **06 구현(위 '리그 순위 응답'):** `GET /standings?league=&season=`(06 개선: UEFA 리그 페이즈 포함), `GET /knockouts?league=&season=&stage=`(06 개선), `GET /standings/summary`, `GET /player-rankings?league=&season=&type=goals\|assists\|yellow\|red\|saves` | 06 |
| 팀 | `GET /teams?league=&q=&page=`(07 구현, 위 '팀 탐색 응답'), **08 구현(위 '팀 상세 응답'):** `GET /teams/{id}`, `/teams/{id}/fixtures`, `/teams/{id}/squad`, `/teams/{id}/season-stats?season=`, `/teams/{id}/transfers?season=`, `GET /news?team=` | 07·08 |

### 6.5 외부 데이터 수집·캐시

- **클라이언트:** `app/providers/api_football.py`(01 작성, 03 수집 작업은 `get()`을 그대로 사용)와 `app/providers/naver_news.py`(03). 키는 `SecretStr`에서 요청 직전에만 꺼내고 헤더·URL·키를 로그에 남기지 않는다. `../api-test/tests/api_client.py`(로컬 전용)의 안전 장치(HTTP 200 + `errors` 실패 처리, 쿼터 헤더 기록, 요청 간격)를 참고한다.
- **호출 한도 보호:** 공용 속도 제한기(분당 250회 이하로 운영, Pro 한도 300회), 일일 예산 경계(기본 7,000회에서 신규 수집 중단), 타임아웃 10초, 5xx·네트워크 오류는 최대 2회 지수 백오프 재시도 후 중단. 무제한 자동 재시도·폴링 금지. 호출 수는 `sync_runs`에 기록한다.
- **쓰기 규칙:** 실패 응답으로 기존 정상 데이터를 덮어쓰거나 지우지 않는다. 정상 빈 응답과 오류를 구분해 기록한다(COM-004, CMP-004).
- **수집 작업:** `app/sync/<job>.py`의 멱등 함수 + CLI(`uv run python -m app.sync <job> [옵션]`). 자동 실행은 백엔드 프로세스 안의 APScheduler로 하되 `SCHEDULER_ENABLED=true`인 인스턴스 하나에서만 켠다. 같은 작업이 겹치지 않도록 PostgreSQL advisory lock을 쓴다. 배포 환경의 스케줄 방식은 Codex 배포 단계에서 바꿀 수 있게 작업 함수와 실행기를 분리한다.
- **요청 시 보충 조회:** 경기 상세·상대 전적처럼 사용자가 열었을 때 처음 필요한 데이터만 "DB 확인 → 없거나 만료면 외부 조회 1회 → 저장" 방식을 쓴다. 같은 키의 동시 요청은 하나로 합친다.

| 작업 | 초기 주기(실측 후 조정) | 담당 |
| --- | --- | --- |
| 대회·시즌·팀·허용 집합 | **03 `reference`:** 매일 04:00 KST + 수동. `/leagues?id=` 21회(2026-11-19 새 컵 7개 추가) + `/teams?league=&season=` 8회(5대 리그 + UEFA 3개, UEFA는 뉴스 주제 판정용) = 29회. 끝에 별칭 시드 적용. 별칭만 다시 넣을 때 `team_aliases`(0회) | 03 |
| 공통 경기일 기간 경기 목록 | **03 `fixtures`:** 30분, 관리 시즌(2025·2026) 중 기간(처음~끝, 오늘 포함)과 시즌 기간이 겹치는 `available` 대회·시즌마다 `/fixtures?league=&season=&from=&to=&timezone=UTC` 1회(2026-11-19 실측 14회, 이탈리아 슈퍼컵 12/23처럼 컵 경기일이 기간에 들어오면 늘어남). 실패한 대회는 기존 행 유지 + `fixtures_failed_at` 기록 | 03 |
| 시즌 전체 경기 목록 | **05 `fixtures_season`:** `available` 대회마다 `/fixtures?league=&season=&timezone=UTC` 1회(2026-11-19부터 현재 시즌 20회·2025 시즌 21회, `league=` 지정 가능). 기본 현재 시즌을 매일 13:00 KST(유럽 경기 없는 시각)에 실행해 30분 목록 작업(`fixtures`)이 멈췄던 동안의 종료 경기를 메운다. 과거 시즌은 수동 `python -m app.sync fixtures_season season=2025`. 경기 ID upsert라 재실행해도 중복 없음, 관리 시즌 밖은 거부. 요청 실패·저장 오류(그 대회만 롤백 후 다음 대회 계속)·응답 일부만 저장된 경우 모두 기존 행을 유지하고 `season_fixtures_failed_at`만 기록하며 성공 시각은 갱신하지 않는다. **공통 `upsert_fixtures()`(05 보완):** DB에 없는 팀이 이름 없이 오면 그 경기를 저장하지 않고(팀 이름·경기 값을 만들지 않음) 경고 로그를 남긴다. 호출한 작업은 저장 수가 응답 수보다 적으면 그 대회를 실패로 기록한다(03 `fixtures`도 같은 규칙, 실시간·종료 기록 작업은 다음 주기에 다시 받음). 상세 블록은 적재하지 않음(요청 시 보충) | 05 |
| 실시간 경기 | **03 `fixtures_live`:** 60초 주기지만 진행 중·킥오프 후 3시간 내 미시작 경기가 없으면 사전 확인에서 건너뜀(호출·기록 0). **2026-11-22(04에서, 사용자 결정):** 킥오프 30분 전부터 돌던 구간(`LIVE_LEAD`) 삭제 — `/fixtures?live=`는 시작한 경기만 주고 재조회 대상도 킥오프가 지난 경기뿐이라 킥오프 전 호출은 얻는 것이 없었다(최근 7일 116회 중 52회). 킥오프 감지 지연은 그대로(킥오프 후 60초 안). 실행 시 `/fixtures?live=<지원 대회>` 1회 + 라이브 응답으로 갱신하지 못한 추적 경기만 `/fixtures?ids=`(20개당 1회)로 재조회(종료로 가정하지 않음) | 03 |
| 경기 상세 블록 | **04 구현:** `fixtures_live` 응답의 이벤트와 `/fixtures?ids=` 응답의 4개 블록을 추가 요청 없이 저장. 경기 본체 저장 검증을 통과한 항목만 상세에 반영한다. 최종 기록 수집에서 누락·거부된 ID는 기존 블록을 유지하고 부분 실패로 기록한다. **`fixture_details`(5분, 사전 확인으로 대상 없으면 건너뜀):** 최근 2일 안에 종료·중단됐는데 최종 기록이 없는 경기를 `/fixtures?ids=`(20개당 1회)로 1회 수집(종료 전환 시 1회). **요청 시 보충:** 상세를 열 때 `/fixtures?id=` 1회 — 종료·중단은 최종 상태로 한 번, 진행 중은 90초에 한 번까지, 예정·연기·취소는 요청 없음(04 개선: 킥오프 전 라인업 조회 삭제, 라인업은 진행 중부터). 실패는 `last_failed_at`만 기록하고 5분간 재요청하지 않으며 기존 데이터를 덮어쓰지 않는다. 받은 적 없이 실패한 블록은 지금 다시 조회하는 경우(진행·종료·중단)에만 `unavailable`, 예정·연기는 `not_yet`. 같은 경기 동시 요청은 `single_flight`로 1회로 합치고 잠금 안에서 실패 쿨다운을 다시 확인한다 | 04 **2026-11-19 실측:** 새 컵 경기 첫 열람 1회 보충(클럽 월드컵 1399365·1392812, 커뮤니티 실드 1582365), 재열람 0회. 예정 슈퍼컵(1643514·1598252)은 상대 전적 1회씩·팀 흐름은 신선하지 않은 팀만(2팀) 조회. |
| 상대 전적·팀 최근 흐름 | **04 구현(요청 시·TOP 5 근거):** 상대 전적 `/fixtures/headtohead?h2h=A-B&last=10`(친선·미종료 제외 후 5경기 미만이고 응답이 꽉 찼으면 `last` 없이 1회 더) — 경기당 1회, 수집된 새 맞대결이 끝난 뒤에만 갱신. 팀 최근 흐름 `/fixtures?team=X&last=10`(같은 기준, 부족하면 `last=30` 1회) — 팀당 캐시, 그 팀의 새 결과가 수집되거나 7일이 지나면 갱신 | 04 |
| 순위 | **06 `standings`:** 대상은 5대 리그와 UEFA 3개 대회 리그 페이즈(06 개선 2026-11-17, `STANDINGS_IDS`) — 선수 순위·선수 기록 작업도 2026-11-20부터 UEFA 3개 대회를 포함한다(아래 행). UEFA 리그 페이즈 표는 저장 행·경기 수와 무관하게 그룹 1개·서로 다른 36팀·1~36위여야 저장한다(첫 적재 포함, Codex 2차 지적 1·3차 지적 2 — 18팀씩 두 그룹 응답 등은 거부하고 기존 표 유지, 비어 있는 응답은 '아직 미발표'로 허용). UEFA는 완전성 검사(3경기 이상 팀 포함)와 경기일 판정을 'League Stage' 라운드 경기로만 한다(예선·토너먼트 날에는 매시 갱신하지 않음, 리그 페이즈가 끝난 뒤에는 하루 1회). 매시 10분 확인(사전 확인은 DB만 — 대상이 없으면 호출·기록 없음). 현재 시즌 표별로 경기일(그 리그 경기가 오늘 KST 날짜에 있거나 4시간 안에 킥오프)이면 55분마다, 아니면 23시간마다 `/standings?league=&season=` 1회. 직전 시도(성공·실패)에서 55분이 안 지났으면 건너뜀. 이전 시즌은 저장된 적이 없을 때만(보관). 수동 `python -m app.sync standings season=2025 [league=61] [force=1]`. 하루 8~약 190회(경기일 표 수 × 시간, UEFA 3개 추가분 하루 3~약 70회) | 06 |
| 선수 순위·선수 시즌 기록(선방 집계) | **대상(2026-11-20부터):** 5대 리그 + UEFA 2·3·848(예선 포함 대회·시즌 전체 — 예선만 치른 팀 선수에게 출전 기록이 있음을 실제 API로 확인). **06 `player_rankings`:** 매일 14:00 KST, 대회마다 `/players/topscorers`·`topassists`·`topyellowcards`·`topredcards` 4회(현재 시즌 전부 받으면 32회 = 5대 리그 20 + UEFA 12). **06 `player_stats`:** 매일 14:20 KST, 대회마다 `/players?league=&season=&page=` 전체 페이지(5대 리그: 2026-11-06 기준 현재 시즌 139페이지, 2025-26은 188페이지 / UEFA: 2026-27 챔스 92·유로파 62·컨퍼런스 100페이지, 2025-26 83·63·108). **UEFA 갱신 조건:** 현재 시즌 UEFA 선수 단위는 마지막 성공 이후 그 대회 종료 경기(킥오프 ≥ 성공 시각 − 3시간)가 있을 때만 다시 받는다(`due_leagues`) — UEFA 경기 다음 날 약 266회(상위 목록 12 + 페이지 254), 경기 없는 날 0회, 주 2~3일. **팀이 빈 줄:** 페이지 응답에서 팀이 빈 선수 줄(UEFA 2025 챔스 Pafos 등 11줄)은 포지션이 명확한 필드 선수(Defender·Midfielder·Attacker·Forward)면 저장하지 않고 수를 로그에 남기며, 골키퍼·포지션 없음·모르는 값이면 선방이 불완전해지므로 그 단위를 거부(기존 값 유지)한다. 이 사유(`TEAMLESS_REFUSAL`)로 거부된 UEFA 단위는 같은 응답이 다시 거부될 것이므로 그 거부 이후 새 UEFA 경기 결과가 생길 때까지 다시 받지 않는다(그 밖의 실패는 다음 날 재시도). 페이지가 모두 모이고(1..total, 마지막 외 페이지는 정확히 20명·마지막은 1~20명 — 2025-26 원본 188페이지 확인, 같은 선수가 두 번 나오지 않음 — 제공사는 선수를 한 번만 주므로 반복은 페이지 밀림·반복이며 그만큼 다른 선수가 빠진 것, `total = 0`인 정상 빈 응답은 빈 결과), 저장된 기록보다 10%를 넘게 줄지 않고(`PLAYER_SHRINK_TOLERANCE`) 같은 선수·팀 줄이 페이지 사이에서 다르지 않을 때만 저장, 아니면 그 리그를 실패로 기록하고 다음 날 다시 받음. 두 작업 모두 이전 시즌은 저장된 적이 없을 때만, 수동 `season=2025 [league=] [force=1]`로 대회를 나눠 실행할 수 있다. 예상 일일 호출(06 전체): 약 165회 + 경기일 순위, UEFA 경기 다음 날 +약 266회 | 06 |
| 감독·선수단·팀 시즌 기록·국적 보완 | **08 `team_details`:** 매일 15:00 KST(선수 시즌 기록 14:20 뒤). 현재 5대 리그 팀(리그 팀 목록이 수집된 리그만, 미수집 리그는 실패로 기록)마다 `/coachs?team=`·`/players/squads?team=`·`/teams/statistics?team=&league=&season=`(이번 시즌) 3회 = 288회. 지난 시즌 기록은 그 팀이 그 리그를 뛴 시즌만 저장된 적이 없을 때 1회(현재 83팀, 이후 0). 이어서 선수단 중 국적이 없고 아직 조회하지 않은 선수마다 `/players/profiles?player=` 1회(조회 후 `profile_checked_at`, 실패는 다음 날 다시). 단위(팀×종류)는 KST 하루에 한 번 — 마지막 시도(성공·실패)가 이전 KST 날짜일 때만 다시 받는다(낮에 수동 실행해도 다음 정시 실행을 건너뛰지 않음)(사전 확인은 DB만 — 대상 없으면 호출·기록 0). 저장 전 완전성 검증(Codex 1차 지적 1): 선수단은 18명 이상이고 저장된 선수단보다 25%를 넘게 줄지 않을 때만(`MIN_SQUAD`·`SQUAD_SHRINK_TOLERANCE`, 2026-11-07 저장 96팀 최소 24·평균 31명), 시즌 기록은 경기 수·승무패·득실 합계가 모두 숫자이고 경기 수 = 승+무+패, 모든 항목의 홈+원정 = 합계(Codex 2차 N1)이며 저장된 기록보다 경기 수가 줄지 않을 때만(`check_statistics`, 저장 179건 모두 통과). 거부되면 저장값과 성공 시각을 그대로 두고 실패를 기록. 현직 감독은 시작일이 오늘(KST) 이후인 재임 줄을 빼고 고름. 국적 보완은 다른 선수의 응답이면 조회 완료로 기록하지 않고 다음 날 다시(빈 응답은 '프로필 없음'으로 완료). 수동 `python -m app.sync team_details [team=50 \| league=39] [force=1]` | 08 |
| 팀 선수 기록(지원 대회) | **2026-11-25:** 현재 시즌은 그 팀이 끝난 경기를 치른 대회 줄만 저장(`played_competitions` — 다음 시즌 줄로 먼저 나오는 지난 슈퍼컵 제외). 성공 뒤 선수 줄이 없는 대회의 아직 읽지 않은 경기 기록을 `/fixtures?ids=`(20개당 1회, 04 `store_fixture_records`)로 한 번 읽는다 — 첫 실행 1회·10경기. **2026-11-21 B:** 저장 원본은 그대로 두고 이적 판정 때만 빈 NULL 줄을 0, 득점·도움·평점 중 값이 있는 NULL 줄을 출전으로 본다. 지난 고정 시즌도 재수집 없이 적용.  **08 `team_player_stats`(2026-11-18, 범위 2026-11-20 확대):** 매일 15:30 KST(`team_details` 뒤). 현재 5대 리그 팀마다 `/players?team=&season=&page=` 전체 페이지(팀당 보통 2~3페이지, 20명씩). 같은 선수가 다시 나오면 페이지 밀림(다른 선수 누락)으로 보고 그 팀·시즌을 실패로 기록(Codex 1차 지적 1), 이 팀(`team.id`)의 그 시즌 개최 지원 대회 줄만 저장(`record_competitions` — 공통 대회 마스터의 활성 대회 중 그 시즌 `no_data`가 아닌 것: 리그·국내 컵·슈퍼컵·UEFA·개최된 클럽 월드컵, 친선·유스 등 마스터 밖 대회는 버림, 제외용 목록 없음. 마스터 행이 없는 2024는 활성 대회 전체). 페이지 완전성은 06 `player_stats`와 같은 규칙(1..total, 마지막 외 20명), 저장된 줄보다 10%를 넘게 줄면 거부(`TEAM_LINES_SHRINK_TOLERANCE`), 실패는 기존 줄·성공 시각 유지 + `team_syncs`(kind `player_stats`) 실패 기록. 현재 시즌은 KST 하루 한 번, 지난 시즌과 그 전 시즌(2024 — 이적 출전 근거용, D-08-6a)은 성공할 때까지 매일 1회 후 고정(`PLAYER_PAST_SEASONS` 2). **행 소유:** 이 작업은 `team_player_stats`만 쓰고 06 `player_stats`는 `player_season_stats`만 쓴다(리그 순위 집계와 섞지 않음). `players`는 값이 있을 때만 갱신. 시작 시 밀린 작업 실행 대상. 실제: 2026-11-18 첫 실행 434회, 2026-11-20 범위 확대 재수집 2026 193·2025 247 + 2024 316회(저장 2024 10,066·2025 8,207·2026 5,384줄). 수동 `python -m app.sync team_player_stats [team=50 \| league=39] [season=2025] [force=1]`(`season`+`force`는 저장된 지난 시즌도 다시 받음) | 08 |
| 이적 | **08 `transfers`:** 매일 00:00 KST(15:00 UTC), 팀마다 `/transfers?team=` 1회 = 96회. 응답 중 그 팀이 입단·이적한 줄만, 미래 날짜 제외. 같은 이동의 반복 줄은 저장 때 합치지 않고(원본 보존) 응답 때 `merge_transfers()`로 정리한다(D-08-6 (가)·(나)). 이 응답으로 쓸 수 있는 시즌 = 갱신 기간((S+1)-07-01 00:00 실행까지 — 6/30까지 반영된 기록을 받음) 안이거나, 그 날 이후 실행으로 저장된 적이 없는 관리 시즌(처음 수집, 또는 7/1 마지막 갱신이 실패한 시즌 — 성공할 때까지 매일 다시, 그동안 화면은 마지막 확인 기록과 갱신 실패 안내, Codex 1차 지적 3) — 시즌 단위로 통째 교체(재실행해도 중복 없음). 한 요청이 쓰려던 시즌 모두에 성공·실패를 기록. 저장분과 새 응답을 D-08-6 정리 후 이동 단위로 비교해, 새 응답에 없는 저장 이동(`same_move` — 같은 선수·방향에 같은 상대 ID·시즌이고 두 날짜 사이(양 끝 제외)에 그 선수의 반대 방향 이동이 없음, 또는 ID가 한쪽에 없으면 같은 날짜)이 max(2, 10%)를 넘으면 거부(`check_transfers`, 2026-11-24 — 전에는 정리 전 줄 수끼리 비교해 공급사가 중복을 줄인 응답까지 거부). 같은 수동 옵션 | 08 |
| 영입 선수 이전 팀 출전 | **2026-11-25 삭제(사용자 결정 — 이적 메인은 이 팀 리그·UEFA·클럽 월드컵 출전만 보므로 `transfer_player_checks`·`player_season_checks`·`player_club_seasons` 삭제, `0021`). 아래는 이전 기록.** **2026-11-21 B:** `/players?id=&season=` 줄의 NULL도 동일하게 해석. 값 있는 NULL은 최소 출전 근거 1로 저장한다(정확한 출전 수나 화면 합계로 쓰지 않음). 기존 NULL 합산만으로 구분 불가하여 선수·시즌 273건 재확인(수동 273회·272성공·1실패, 서버 자동 재시도 1회 추가(총 274회): 445025/2024 완료 표시 해제·실패 보존·재확인 대기).  **08 `transfer_player_checks`(2026-11-20, TEAM-006 규칙 6):** 매일 00:40 KST(`transfers` 뒤). 관리 시즌 영입 중 출전 근거를 기다리는 이동(`judge_move` = `check_pending` — 이 팀 출전 없음, 이 팀 기록 수집 완료, 임대 복귀 아님)의 선수마다 `/players?id=&season=` 1회(시즌 = 여름 이동은 전 시즌, 겨울 이동은 그 시즌 — `check_season`). 유스 대회·친선(`NOT_FIRST_TEAM` 대회명: U18/U19/U21·Premier League 2·Youth·Primavera·Reserve·Junior·Friendlies)을 뺀 공식 대회 출전을 구단별로 합쳐 `player_club_seasons`에 저장하고 `player_season_checks.checked_at`(빈 응답 = 출전 없음, 다른 선수·시즌 응답은 거부). 실패는 `failed_at`만 기록하고 다음 실행에서 다시(처음 묻는 대상 먼저). 한 실행 최대 `PLAYER_CHECKS_PER_RUN` 1,500(초기 적체를 하루 예산 안에서 나눔). 실제 2026-11-20: 대상 1,617명·시즌, 1,617회(서버 시작 시 밀린 작업 117 — 수동 실행과 겹쳐 분당 제한 오류 672건 → 같은 날 재실행으로 모두 확인), 남은 대상 0. 이후 새 영입만. 수동 `python -m app.sync transfer_player_checks [team=50 \| league=39] [limit=200]` | 08 |
| 뉴스 | **03 `news`:** 매시 정각, 네이버 검색 8개 검색어(프리미어리그·라리가·세리에A·분데스리가·리그앙·챔피언스리그·유로파리그·컨퍼런스리그) × 최신 100건 = 8회. 게시 후 `NEWS_RETENTION_HOURS`(기본 72) 지난 기사는 저장하지 않고 삭제 | 03 |
| TOP 5 선정 | **현행(2026-11-23 사용자 결정, 00 반영·`dev` 병합):** 생각 수준 `TOP5_LLM_THINKING_LEVEL` `low` 유지(Neon 기본 high는 생각 토큰·시간·비용 증가, low 비교에서 이유 품질 충분). 00:00 성공 시 모델 요청은 1번뿐(00:05·00:10 슬롯·`top5_reconcile`·재실행 모두 요청 없음 — `test_success_at_0000_makes_exactly_one_model_request`). 11/23 주는 새 요청 없이 비교 때의 Neon 답으로 공개(시도 4543, 출처는 `llm_output.note`). 모델 `gemini-4-neon`(유료 등급, Hydrogen과 요청 1번씩 비교 후 결정 — Neon 22.7초·약 $0.15/요청, 생각 수준 low 유지). 자동 선정 월요일 00:00~00:12 KST(`WINDOW_MINUTES` 12, 수동 복구도 `TOP5_ATTEMPT_TIMEOUT_SECONDS` 720초), 모델 요청 최대 3번 — 근거가 준비되면 바로 1번, 일시 오류면 00:05·00:10 고정 시각에만 다시(`RETRY_BEFORE_END`, 각 요청은 다음 시각까지만), 429·잘못된 요청·잘못된 답은 재요청 없음. 00:12까지 미공개면 지연 안내·알림. 후보는 그 주(월 00:00~다음 월 00:00 KST)의 예정(NS)·진행 중(SUSP 제외)·정상 종료(FT·AET·PEN) 경기 — 늦은 수동 복구에서도 월요일 새벽 경기(예: 11/23 01:30 리버풀–맨유)가 빠지지 않게 했다. 이미 시작·종료된 후보는 결과를 주지 않고 최근 폼·맞대결을 킥오프 시점으로 자른다(순위표는 현재 저장본이라 그 경기 결과가 반영될 수 있음 — 제한). 프롬프트 `2026-11-23.1`. 일정 신선도 확인은 `fixtures` 작업이 실제로 받는 대회 시즌만 본다(코파 델 레이 2026처럼 저장 시즌이 조회 기간 전에 끝난 대회가 선정을 막던 결함, 시도 4346). 이하 이전 기록 — **현행(2026-11-19 사용자 결정, 기획 문서 PRD·기능 명세서·유저 플로우 개정 반영):** 작업 `top5_weekly`(월 00:00 KST cron, 그 주 유일한 자동 시도)·`top5_reconcile`(60초, 멈춘 시도·보류된 지연 처리만, 새 선정 없음)·`top5`(관리 명령 `uv run python -m app.sync top5`, 이번 주가 공개되지 않았을 때만). 자동 시도는 00:20 KST(`window_end()`) − 10초까지, 수동 복구는 `TOP5_ATTEMPT_TIMEOUT_SECONDS`(기본 1200초). **00:20 전 실패**는 기록만 하고(주 상태 `delayed`, `next_retry_at` = 지연 공개 시각 00:20) 사용자에게는 지난주 결과+'이번 주 결과 준비 중'을 그대로 보인다. 00:20에 `top5_reconcile`이 주 잠금 아래 현재 주·미공개를 다시 확인하고 업데이트 지연 안내를 공개·운영 알림 1회. 보류 지연은 수동 복구가 **성공해야만** 취소된다(시작만으로는 취소되지 않음). 00:20에 수동 복구가 실행 중이면 주 잠금을 가진 그 실행 주체가 지연 안내 공개·알림 1회를 하고(`HELD_POLL_SECONDS` 1초 간격 확인), 이후 성공하면 목록이 새 버전으로 교체된다. 수동 복구 프로세스가 마감 전에 죽어 잠금이 풀린 경우에는 `top5_reconcile`이 마감을 기다리지 않고 지연을 공개한다. 00:20 이후 실패나 이미 지연이 공개된 뒤의 수동 복구 실패는 즉시 지연(추가 알림 없음). 00:00 시도가 아예 없으면 00:21(00:20+1분 유예)부터 지연·알림. 모델 요청: `TOP5_LLM_MODEL`(gemini-3.8-flash)만, 하위 모델 없음. 요청 직전마다 남은 시간 180초 이상 필요(첫 요청 포함), 요청당 최대 600초, 60초 안에 온 일시 오류(503·500·502·전송)는 30·60·120·120초 뒤, 오래 걸린 실패(504 등)는 즉시 재요청, 시도당 최대 5회, 429·잘못된 요청·응답 형식 오류는 재요청 없음, 생각 수준 `TOP5_LLM_THINKING_LEVEL`(low). 공통: 주 단위 advisory lock, 게시는 '현재 KST 주·현재 시도·실행 중·마감 전'일 때만(행 잠금 후 시각 재확인), 현재 주 공개 결과 우선이라 지난주 작업의 늦은 종료가 새 주를 가리지 않음, 지난주 시도는 내부 상태만 정리(새 공개·알림 없음). 근거 수집은 daemon 작업자 4개, DB 트랜잭션 SQL·잠금 대기 최대 5초. 입력: 일정 신선도(90분 안·실패 대회 없음) → 후보(그 주 KST 킥오프·NS·미시작, `Competition.active` 21개 대회) → `/standings`(리그·UEFA만, 대회당 1회, `standing.of` 포함) + 팀 최근 흐름·상대 전적(캐시 재사용, 압축 'W 2-1 H'·'W 2-0') + 운영 시드(`domesticPriority`) → Gemini → 검증(후보·주간·중복·개수 min(5,n)·순위·이유 한 줄 60자·'관심 팀' 등 금지 표현) → 원자적 게시. 후보 0건은 Gemini 없이 `none` 공개. DB의 `retry_scheduled` 상태·`retry` 시도 종류는 과거 기록용으로만 남는다. 운영 이력: 11/16 주 공개 결과는 사용자 요청으로 3.8 Flash 선정으로 1회 교체(버전 1291·시도 2664, 이전 결과는 시도 1641). **이전 정책(2026-11-02~11-18, 폐지):** 00:00 첫 시도 → 00:05 `top5_retry` 1회 → 두 번째 실패 시 지연·알림, 시도 240초, 하위 모델 `gemini-3.5-flash-lite` 대체. |

- **자동 실행(03):** 위 03 작업은 `SCHEDULER_ENABLED=true`인 백엔드 인스턴스 하나에서만 자동 실행된다(로컬 기본 false — 개발 중에는 `uv run python -m app.sync <job>`으로 수동 실행). 예상 일일 호출: 경기 목록 '조회 기간과 겹치는 대회·시즌 수 × 48회'(2026-11-19 14개 → 672회, 21개 모두 겹치면 1,008회) + 실시간(경기 시간대만, 1~2회/분) + 기준 29회(`/leagues` 21 + `/teams` 8), 네이버 192회.
- **하루 호출 실측(API-Football, `sync_runs.api_requests` 합계):** 2026-11-21~25 하루 약 1,250~1,400회(11/20은 이적 이전 팀 확인 일괄 실행으로 5,138회 — 이 작업은 11/25 삭제). 일일 예산 7,000회 안이다. 작업을 추가하면 이 값을 다시 잰다.
- **시작 시 밀린 작업 실행(00, 2026-11-16):** 백엔드가 꺼져 있던 동안 정해진 실행 시각이 지난 수집 작업은 서버가 시작되자마자 15초 간격으로 차례로 실행한다(`app/sync/scheduler.py`의 `catch_up_overdue()`, 기준은 `sync_runs`의 마지막 성공 시각). 10분 미만 주기 작업(`fixtures_live`·`fixture_details`·`top5_reconcile`)과 TOP 5 고정 시각 작업(`top5_weekly`, 2026-11-19까지는 `top5_retry`도)은 제외한다 — 놓친 TOP 5 선정은 정책대로 지연 안내 후 `python -m app.sync top5`로 수동 복구한다. 배경: 2026-11-11 18시~11-16 백엔드 중단으로 일정 지연 표시·뉴스 만료·TOP 5 미선정이 생겼다. 자동 수집과 월요일 00:00 TOP 5 선정(00:20까지)은 백엔드가 켜져 있어야 동작한다.
- **예약 운영 조건(03 2026-11-10 확인):** 예약은 백엔드 프로세스 안의 APScheduler라 **서버가 꺼져 있으면 모든 수집·TOP 5 작업이 멈춘다**(11/5~11/10 `fixtures` 미실행, `fixtures_live`는 11/2 이후 미실행이 그 결과 — 이 동안 21일 밖으로 밀려난 종료 경기는 13:00 `fixtures_season`이 메운다). 운영에는 ① 항상 켜져 있는 단일 백엔드 인스턴스에서만 `SCHEDULER_ENABLED=true`(여러 인스턴스면 하나만 켜고 나머지는 false — advisory lock이 중복 실행을 막지만 예약은 하나로) ② `SCHEDULER_ENABLED=true`면 뉴스도 같은 스케줄러에 들어가므로 `NEWS_SCHEDULER_ENABLED`는 다른 인스턴스에서 켜지 않는다(둘 다 켜도 한 프로세스면 전체 작업 1벌) ③ 서버 재시작·`.env` 변경 후 재기동(개발 `fastapi dev`는 소스 저장 시 재기동되며 그때 `.env`를 다시 읽음) ④ 화면은 `fixtures`가 75분 넘게 성공하지 못하면 '일정 갱신 지연'을 표시하므로 이 안내가 보이면 서버·스케줄러 상태를 먼저 확인한다. 2026-11-10 확인: 개발 백엔드 하나에서 14개 작업 등록(`fixtures` 30분, `fixtures_live` 60초, `fixture_details` 5분, `news` 매시 정각, `standings` 매시 10분, `top5_weekly` 월 00:00·`top5_retry` 월 00:05 KST 다음 실행 11/16, `top5_reconcile` 60초 등), 15:39 `fixture_details` 자동 실행(2회) 확인, 수동 `fixtures` 1회(14회)로 21일 범위(11/7~11/27) 296경기·킥오프 후 '예정'으로 남은 경기 0 확인.
- **2025 시즌 과거 데이터(05 적재 완료):** `fixtures_season season=2025`(14회)로 API에서 받았다. `../api-test/results/raw/`의 2025 원본 14개 파일과 비교해 경기 수·ID·상태·스코어·팀·킥오프 차이 0을 확인했고, 원본을 쓰면 아끼는 호출이 14회뿐이라 운영과 같은 API 경로 하나만 둔다(파일 가져오기 코드 없음). 과거 경기 상세 블록은 일괄 적재하지 않고 상세를 처음 열 때 1회 보충한다(04). 일괄 적재가 필요해지면 `/fixtures?ids=` 20개당 1회 — 2025 종료 4,125경기 기준 약 207회.
- **실시간 화면 갱신:** 웹소켓 없이 클라이언트 폴링(진행 중 경기가 화면에 있을 때 30~60초)으로 한다. 화면에 마지막 갱신 시각을 표시한다. **03 구현:** `src/features/schedule/queries.ts`의 `liveRefetchInterval()` — 진행 중·시작 30분 전~킥오프 후 3시간 미시작 경기가 있으면 60초, 없으면 목록의 다음 경기가 그 구간에 들어서는 시각에 1회 재조회한 뒤 60초 폴링으로 전환, 숨김 탭에서는 멈춤. 재조회가 실패해도 이미 보인 목록은 유지하고 '최신 일정으로 갱신하지 못했습니다'를 함께 표시한다(일정·관심 팀·뉴스 공통). 실제 경기 시간 검증(V-04) 전에는 지연 시간을 보장한다고 안내하지 않는다. **04 경기 상세:** 진행 중 기록은 60초, 예정 라인업은 킥오프 60분 전부터 10분 간격으로 발표 전까지 재조회한다(이전에는 해당 구간 진입 시 1회 재조회). 상태 전환 시 최종 기록을 즉시 한 번 더 조회한다. 재조회 실패는 기존 정보·기록과 재시도 안내를 함께 유지하고, 진행 경기의 마지막 제공사 확인에서 3분이 지나면 성공 응답이 없어도 지연 경고를 표시한다. 중단 경기는 타임라인만 제공한다. 상세 블록의 최초 보충 조회 실패는 예정 경기라도 `unavailable`이며 발표 전으로 바꾸지 않는다. 상대 전적·팀 흐름 실패는 HTTP 200 블록이어도 재시도 버튼을 제공하고, single_flight 잠금 안에서도 5분 실패 제한을 다시 확인한다(TOP 5의 strict 조회는 기존 기준 유지).
- **이미지:** 백엔드가 `image_assets`에서 권리가 확인된 이미지 URL만 `crestUrl`·`photoUrl`로 내려준다. `IMAGE_RIGHTS_ENFORCED=false`(로컬 기본)일 때만 API 이미지 주소를 그대로 사용한다. 공개 배포 전 `true`로 바꾸고 권리를 확보한 자산만 노출한다(V-10).
- **뉴스 수집 캐시:** `news_articles.expires_at`·`NEWS_RETENTION_HOURS`의 공개 뉴스 수집/정리 정책은 유지한다. 개인 기사 보관은 제공하지 않는다. 기사 본문 수집·AI 입력은 하지 않는다. 공개 이용 조건 확인은 V-09를 따른다.

### 6.6 프런트엔드 구조·상태 관리

**경로**

| 페이지 | 경로 | 담당 |
| --- | --- | --- |
| 메인(경기 일정) | `/` | 03 |
| 경기 상세 | `/matches/[fixtureId]` | 04 |
| 지난 경기 | `/results` | 05 |
| 리그 순위 | `/standings?league=39&season=2026` | 06 |
| 팀 탐색 | `/teams` | 07 |
| 팀 상세 | `/teams/[teamId]` | 08 |
| 로그인 / 회원가입 | `/login`, `/signup` | 02 |
| 마이페이지 | `/mypage` | 09 |

폴더별 파일 역할은 [file-feature-map.md](file-feature-map.md)를 본다.

- **상태 관리 경계:** ① 필터·시즌·탭·페이지 등 화면 상태는 URL 검색 파라미터(뒤로 가기·공유 가능, 초기화 규칙은 PRD 기준). ② 서버 데이터는 서버 컴포넌트 조회 또는 TanStack Query(클라이언트 조회·폴링·변경 후 무효화). ③ 인증 상태·관심 팀은 React Context(`AuthProvider`, `FavoritesProvider`). ④ 브라우저 저장소는 비회원 관심 팀(`kt-fav-guest`), 작성 중 후기·의견 초안(`sessionStorage`)에만 쓰고 모든 접근을 try/catch로 감싼다(저장소 사용 불가 시 안내 후 공개 기능 유지). 별도 전역 상태 라이브러리는 도입하지 않는다.
- **화면 간 반영:** 관심 팀·후기 변경 후 해당 query key를 무효화해 헤더·메인·팀 탐색·팀 상세·마이페이지가 같은 값을 보게 한다. 쿼리 키 규칙은 01이 `lib/api/query-keys.ts`에 정한다.
- **요청 상태 표준:** 모든 데이터 영역은 `DataState`(`status`: `loading`·`ready`·`empty`·`partial`·`error`(+`onRetry`)·`denied`(회원 전용, `deniedAction`에 로그인 유도))로 감싼다. 빈 결과 문구와 실패 문구를 구분한다.
- **스타일:** Tailwind CSS v4. Figma의 색·글꼴·간격·반경을 `globals.css`의 `@theme` 토큰으로 정의하고 컴포넌트에서 임의 색상값을 직접 쓰지 않는다. `<html lang="ko">`.
- **Figma 디자인 기준(컬러 가이드·개발 전달 기준에서 확인):**
  - 레이아웃: 시안은 데스크톱 1920px·모바일 375px. 콘텐츠·헤더·푸터 내부는 최대 1280px 중앙 정렬의 유동 컨테이너. 1024px 미만은 메뉴 접기·1열 전환, 작은 화면 좌우 24px, 모바일 16px.
  - 서체·크기: Noto Sans KR. 본문 14px/22px 이상, 보조 설명 12px/20px 이상. 모바일 조작 영역 44px 이상.
  - 간격·반경: 4·8·12·16·24·32·48px, 버튼 반경 8px, 카드 반경 16px. 포커스는 3px 외곽선.
  - 색상 토큰: `bg/canvas #F8FAFC`, `bg/surface #FFFFFF`, `bg/subtle #F1F5F9`, `bg/selected #EFF6FF`, `text/primary #0F172A`, `text/secondary #475569`, `text/muted #64748B`, `text/inverse #FFFFFF`, `action/primary #2563EB`, `action/hover #1D4ED8`, `action/soft #DBEAFE`, `action/disabled #E2E8F0`, `border/default #E2E8F0`, `border/strong #CBD5E1`, `border/focus #93C5FD`, `status/live #047857`, `status/live-bg #ECFDF5`, `status/warning #B45309`, `status/warning-bg #FFFBEB`, `status/error #B91C1C`, `status/error-bg #FEF2F2`, `brand/key #F8FAFC`, `brand/arrow #2563EB`, `brand/rim #E2E8F0`(2026-11-03 Figma 승인 브랜드 토큰. 앱 토큰·SVG는 후속 구현에서 별도 반영). 블루는 주요 동작·선택·링크에만 쓰고, 진행 중·주의·오류는 색과 상태명을 함께 표시한다.
  - 헤더 높이(2026-11-19, Figma `128:3700`·`128:4408`): PC 내비 68px(위아래 11px)+띠 48px, 모바일 내비 64px(위아래 10px)+띠 64px(위아래 6px, 두 줄), 구분선 포함 118/130px. TOP 5 대진 순환 28px/s(Figma `308:4617`).
  - 로고: 헤더는 승인 `logo-header.svg`(심벌+윤곽선 워드마크) 하나를 PC 46px·모바일 40px 슬롯으로 표시한다(Figma `49:58`·`49:571`, 2026-11-10). 푸터 로고는 없다. 파비콘은 기존 승인 ICO. 최종 SVG는 `frontend/public/brand/`에 있다.
  - 헤더: 로고와 메뉴 사이 32px, 메뉴 간격 32px, 로그인·회원가입은 오른쪽. **의견 보내기는 모든 화면에서 푸터 버튼 하나다**(Figma `304:3823`, 사용자 결정 2026-11-10 — 모바일 하단 고정 영역 제거, 떠 있는 전역 버튼 아님). 모바일은 헤더 메뉴 버튼으로 메뉴·로그아웃을 연다.
  - 필터: 문자 기호 대신 16px 벡터 화살표, 텍스트와 8px 간격. 후기 반응은 16px 엄지 아이콘.
  - 경기 기록: 데스크톱·모바일 모두 타임라인 / 팀 통계 / 라인업 / 선수 평점 4탭. 제공사 선수 평점과 회원 경기 평점을 분리.
  - 푸터(Figma `304:3823`, 2026-11-10): 로고 없음. PC 상단은 왼쪽 이용약관·개인정보처리방침·문의(문서 전까지 링크 없음), 오른쪽 의견 보내기. 구분선 아래 왼쪽 운영자 안내('운영자 정보는 서비스 공개 전에 안내합니다.' — 설정값 `SITE_OPERATOR_*`가 있으면 그 값)·데이터/뉴스 출처, 오른쪽 저작권. 모바일은 정책·문의 → 의견 보내기 → 운영자·출처 → 저작권. 이미지 출처·권리 고지는 사용자 확인 중이므로 Figma 문구를 더미로 유지한다.
  - 시안의 경기·선수 수치는 샘플이다. 실제 응답을 쓰고 미제공 값은 —로 표시한다.
- **코드의 토큰 이름(01):** `src/app/globals.css`의 `--kt-*` 변수(Figma 변수명)와 Tailwind 유틸리티 `bg-canvas`·`bg-surface`·`bg-subtle`·`bg-selected`, `text-fg`·`text-fg-secondary`·`text-fg-muted`·`text-fg-inverse`, `bg-action`·`hover:bg-action-hover`·`bg-action-soft`·`bg-action-disabled`, `border-line`·`border-line-strong`, `live`·`warning`·`error`(+`-bg`). 글자 `text-2xs`(10)·`text-caption`(11)·`text-small`(12)·`text-label`(13)·`text-body`(14)·`text-lead`(16)·`text-title`(20)·`text-heading`(28), 반경 `rounded-badge`(4)·`rounded-control`(8)·`rounded-card`(16), 콘텐츠 폭 `kt-container`. 데스크톱 배치는 1024px(`lg:`)부터.
- **접근성:** 모달·하단 시트는 포커스 이동·Escape 닫기·포커스 복귀, 아이콘 버튼은 `aria-label`, 표는 가로 스크롤.

### 6.7 환경 변수

| 위치 | 변수 | 비고 |
| --- | --- | --- |
| 백엔드 `.env` | `API_FOOTBALL_KEY`, `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET`, `DATABASE_URL` | 설정 완료 |
| 백엔드 설정(01, 코드 기본값 있음) | `APP_ENV`(local), `CORS_ORIGINS`(CSRF Origin 허용 목록 겸용, 기본 `["http://localhost:3000"]`), `TRUSTED_PROXIES`(기본 `["127.0.0.1","::1"]`), `SCHEDULER_ENABLED`(false), `NEWS_SCHEDULER_ENABLED`(false, 뉴스만), `API_FOOTBALL_BASE_URL`, `API_FOOTBALL_DAILY_BUDGET`(7000), `API_FOOTBALL_PER_MINUTE`(250) | 목록 값은 JSON 배열 문자열 |
| 백엔드 `.env`(비밀, 01 추가) | `FEEDBACK_DISCORD_WEBHOOK_URL`(의견 알림 디스코드 웹후크, 비어 있으면 알림 꺼짐, §9 U-06) | 사용자가 직접 입력 |
| 백엔드 `.env`(비밀, 04용·사용자 입력 2026-11-02) | `GEMINI_API_KEY`(TOP 5 주간 AI 선정, Google AI Studio의 Gemini API 키 — 공식 SDK 표준 이름. `GOOGLE_API_KEY`는 함께 두지 않는다), `TOP5_ALERT_DISCORD_WEBHOOK_URL`(TOP 5 운영 알림 전용 디스코드 채널 웹후크, 의견 알림과 분리) — 이름은 `backend/.env.example`에 적혀 있음 | 사용자가 직접 입력. **04 연결 완료:** `app/config.py`의 `gemini_api_key`·`top5_alert_discord_webhook_url`(SecretStr), `top5_llm_model`(기본 `gemini-4-neon` — 2026-11-23 유료 등급 전환, 이전 `gemini-3.8-flash`), `top5_attempt_timeout_seconds`(기본 720 — 2026-11-23 변경, 자동 시도는 00:12 KST−10초로 잘림, 비밀 아님). 키는 SDK 클라이언트에 직접 넘기고(`google-genai==2.34.0`, SDK 재시도 끔·요청 시간 제한은 밀리초) 환경 변수 조회에 의존하지 않는다. 비밀 아닌 설정 `TOP5_LLM_MODEL=gemini-3.8-flash`(무료 등급 중 최상위 모델, 사용자 결정 2026-11-02 — `gemini-3.5-flash`는 지원 종료되어 3.6으로 자동 연결됨)는 `.env`에 들어 있고 코드 기본값도 같게 둔다. 무료 등급은 입력이 Google 제품 개선에 쓰일 수 있으므로 공개 경기 데이터만 보낸다. 무료 한도는 AI Studio 사용량 화면에서 확인한다 |
| 백엔드 설정(04 변경 2026-11-19, 비밀 아님) | `TOP5_LLM_THINKING_LEVEL`(기본 `low`, minimal·low·medium·high, 비우면 모델 기본값 — 응답 시간을 시도 제한 안에 두기 위함). `TOP5_LLM_FALLBACK_MODEL`은 하위 모델 대체 폐지로 삭제(남아 있어도 무시) | `.env.example` 갱신, 각자 `.env`의 `TOP5_LLM_FALLBACK_MODEL` 줄은 지워도 됨 |
| 백엔드 `.env`(비밀, 02 연결 2026-11-21) | `AUTH_JWT_SECRET`, `SMTP_USERNAME`·`SMTP_PASSWORD`(앱 비밀번호, 공백은 코드가 제거), `SMTP_HOST`·`SMTP_PORT`(기본 587, STARTTLS)·`EMAIL_FROM`(비우면 `SMTP_USERNAME`) — `app/config.py`. 비밀 아닌 `TERMS_VERSION`(기본 `draft`, 약관 확정 시 변경). `APP_ENV`가 local·development·test가 아니면 인증 쿠키에 `Secure` | 값은 사용자 입력(U-04·U-05 완료) |
| 백엔드 설정(05, 코드 기본값 있음) | `FIRST_SEASON`(2025 = 2025-26, 관리 시즌의 시작. 관리 시즌 = `FIRST_SEASON`~`CURRENT_SEASON`) | `.env`에 넣지 않아도 동작 |
| 백엔드 설정(03, 코드 기본값 있음) | `CURRENT_SEASON`(2026 = 2026-27), `IMAGE_RIGHTS_ENFORCED`(false), `NEWS_RETENTION_HOURS`(72, V-09 확인 후 확정), `NAVER_NEWS_BASE_URL` | `.env`에 넣지 않아도 동작 |
| 프런트엔드 `.env.local` | `BACKEND_ORIGIN`(01, 서버 전용, 기본 `http://localhost:8000`), `SITE_OPERATOR_NAME`·`SITE_OPERATOR_REPRESENTATIVE`·`SITE_OPERATOR_EMAIL`·`SITE_OPERATOR_ADDRESS`(01, 푸터 운영자 정보, 비어 있으면 '공개 전 안내') | `NEXT_PUBLIC_API_BASE_URL`은 코드·로컬 `.env.local`에서 제거 완료 |

비밀이 아닌 설정값(`BACKEND_ORIGIN`, `APP_ENV`, `SCHEDULER_ENABLED` 등)은 담당 채팅이 `.env`·`.env.local`에 직접 추가·수정할 수 있다. 이때 기존 비밀 값 줄은 읽어서 출력하거나 바꾸지 않는다. 코드에는 비밀이 아닌 설정의 기본값을 두어 변수가 없어도 로컬에서 동작하게 한다.

비밀 값은 `.env`·`.env.local`에만 둔다. `.env`·`.env.local`·`.env.example` 등 모든 `.env*` 파일은 Git에 올리지 않으며(사용자 결정), 필요한 변수 이름은 이 표로만 관리한다. 로컬의 `.env.example`은 참고용으로만 둔다. 새 비밀 값이 필요하면 사용자에게 직접 입력을 요청하고 값을 출력·기록하지 않는다.

## 7. 현재 개발 기반과 실행 방법

| 영역 | 현재 기준 |
| --- | --- |
| 프런트엔드 | Next.js 16.4.3·React 19.3.0·TypeScript·Tailwind CSS v4. `cacheComponents`·`partialPrefetching` 켜짐. `@tanstack/react-query` 5.105.0, `openapi-typescript` 7.13.0(dev). `lang="ko"`, Noto Sans KR(로고 워드마크만 Inter). 전역 헤더·TOP 5 띠·푸터는 루트 `layout.tsx`(모바일 하단 고정 영역은 2026-11-10 제거). 메인(`/`)은 03 일정 화면, 아직 없는 메뉴 경로는 404 안내(`not-found.tsx`). 타입 생성: 백엔드 실행 후 `npm run gen:api`(또는 `npm run gen:api -- <openapi.json 경로>`) |
| 백엔드 | FastAPI·Python 3.12·uv. SQLAlchemy 2.1.6·Alembic 1.20.1·APScheduler 3.11.3. `/api/v1` 라우터(`app/api/router.py`), 오류 형식·예외 처리기, CSRF·요청 제한, API-Football 클라이언트 골격, 수집 실행기(`app/sync`, 등록된 작업 없음) |
| DB | Supabase PostgreSQL `kicktab-dev`(서울), Direct connection 5432, 현재 환경에서 IPv6 접속. Psycopg 3, `sslmode=verify-full` + `certs/supabase-ca.crt`. 테이블 `sync_runs`·`feedback`, 03의 기준 데이터·경기·뉴스 7개(모두 RLS 켜짐·정책 없음, 현재 리비전 `0009_fixture_coverage`). Data API 꺼짐. **현재 DB는 이 프로젝트 하나뿐**이므로 개발 중 마이그레이션·롤백 검증도 여기서 한다(운영 DB 분리는 §10 C-07) |
| 버전 관리 | Git 저장소 루트 `kick-tab/apps/`, 원격 `main`·`dev`(§11) |

명령은 각 앱 폴더에서 실행한다.

| 위치 | 설치·실행 | 검사 |
| --- | --- | --- |
| `frontend/` | `npm ci` → `npm run dev` | `npm run lint`, `npx tsc --noEmit`, `npm test`(04: Node 기본 테스트 실행기, `tests/*.test.mjs`, 추가 의존성 없음), `npm run build` |
| `backend/` | `uv sync --locked --group dev` → `uv run fastapi dev app/main.py`(또는 `uv run python -m uvicorn app.main:app --port 8000`) | `uv run ruff check .`, `uv run python -m pytest`(DB 실연동 테스트는 `KICKTAB_DB_TESTS=1`일 때만, 항상 롤백), `uv run python -m app.check_database`, `uv run python -m alembic current`·`check`(적용 `upgrade head`는 사용자 확인 후, `downgrade`는 실행하지 않음) |

**주의:** 이 PC에서는 Windows 애플리케이션 제어 정책이 `.venv`의 실행 파일(`pytest.exe` 등)을 간헐적으로 차단한다(2026-10-31 한 차례 `uv run pytest` 실패, 이후 재확인 시 실행됨). 안정적으로 `uv run python -m pytest`, `uv run python -m alembic …`처럼 `python -m` 형태를 사용한다.

기본 주소는 프런트엔드 `http://localhost:3000`, 백엔드 `http://localhost:8000`이며 API 문서는 `/docs`, 상태 확인은 `/health`다. 기본 Google Fonts는 빌드 시 네트워크 접근이 필요하다(Figma 글꼴 확정 시 01에서 교체).

현재 백엔드 Python 3.12.14는 `.python-runtime/`에 있고 `.venv`가 이를 참조한다. 둘 다 버전 관리에서 제외한다. 새 작업 환경이나 폴더 이동 시 Python 3.12와 가상환경을 준비한다. 의존성을 변경하면 잠금 파일(`uv.lock`, `package-lock.json`)도 갱신하고, 새 패키지는 설치 시점의 안정 버전을 확인해 고정한다.

## 8. 기능별 선행 조건과 완료 조건 요약

| 채팅 | 선행 조건 | 고유 완료 조건(공통 조건 §4에 추가) |
| --- | --- | --- |
| 01 | 없음(준비 완료) | SQLAlchemy·Alembic 첫 마이그레이션(`sync_runs`, `feedback`, RLS 포함) 적용·롤백 확인, 응답·오류 형식과 예외 처리기, CSRF·요청 제한 공통 의존성, API-Football 클라이언트 골격과 한도 보호 단위 테스트, `rewrites`·API 래퍼·생성 타입·Query Provider, 디자인 토큰·공통 UI, 헤더(인증 자리)·푸터(출처·권리 고지 자리)·TOP 5 띠 빈 상태·의견 보내기(비회원 제출, 1,000자, 실패 시 입력 유지) |
| 02 | 01·03~08 완료·회원 와이어프레임/디자인 보완 대조. 실제 메일·세션 검수 전 JWT·SMTP 설정 | 실제 메일 가입·비밀번호 찾기, 인증번호·세 필수 확인(약관·개인정보·만 14세 이상)과 서버 우회 거부·항목별 기록, 가입 후 세션, 관심 팀 DB 전환/로컬 복원·비회원 5팀/회원 10팀 한도(6·11번째 거부), 평가 작성/수정/삭제/반응/복귀, 비밀번호 변경 다이얼로그/시트 상태·탈퇴·본인 권한, CSRF·내부 returnTo, 회원 의견 연결, 소셜 버튼의 같은 화면 안내 |
| 03 | 01 재검수 완료 | 21개 대회(2026-11-19 확장, 처음 14개)·현재 시즌·5대 리그 팀·허용 집합 적재, 상태 변환 표 테스트, KST 날짜 묶음, 날짜 막대·대회 필터·팀 검색(별칭)·초기화 규칙, 비회원 관심 팀(저장소·관심 팀 일정 우선순위·관심 팀 버튼·5개 제한·저장소 사용 불가 안내), 실시간 폴링(실제 경기 검증은 가능한 시간에 별도 기록), 뉴스 분류 규칙·중복 제거·출처 표시 |
| 04 | 03 완료 | 상태별 영역 전환, 미제공·발표 전 표기, 상대 전적 표시 조건, 경기 평가 공개 조회·정렬(인기순·최신순)·유효 평가 건수(04 개선: 평균 평점 삭제), TOP 5 선정은 정책 확정분만. 후기 작성·수정·삭제·반응은 02에서 마무리(사전 작업만) |
| 05 | 03·04 완료 | 시즌 전체 종료 경기·팀/대회 결합 필터·초기화 규칙·페이지 분할, 과거 팀 검색과 상세 미제공 팀 링크 차단, 2025 적재 후 중복 없음 |
| 06 | 03·05 완료 | 시즌별 팀 순위·선수 순위 전환 규칙, 선방 자체 집계(누락 제외·인원 안내·공동 순위), red·yellowred 분리, 메인 간소 순위, 링크 허용 집합 적용 |
| 07 | 03·06 완료 | 현재 시즌 팀만 표시, 리그 필터·검색·비회원 관심 팀 토글·페이지 분할 |
| 08 | 03·06 완료 | 팀 상세 6개 영역, 선수 표 정렬·더 보기·누락 표시, 시즌 기록 전환, 이적 반기 분류·안내·고정, 팀 뉴스, 모바일 탭, 허용되지 않은 팀 직접 URL 차단 |
| 09 | 02 완료 | 마이페이지 3개 영역(관심 팀·내 평가·계정 관리), 회원 전용 접근 차단, 다른 화면과 변경 반영 일치, 로그아웃 이동 규칙, 비밀번호 변경 다이얼로그/시트 상태·탈퇴 다이얼로그 연결(02 API) |

## 9. 사용자 확인·환경 작업

| ID | 내용 | 시점 |
| --- | --- | --- |
| U-01 | Git 저장소 연결 — 진행 상태는 §11 | 01 착수 전 |
| U-02 | 완료(2026-10-31): Figma 커넥터 연결. 별도 디자인 전달 문서는 사용하지 않기로 하고 Figma의 해당 참조 문구도 삭제 | — |
| U-03 | 완료(2026-10-31 확인): Supabase Data API가 처음부터 꺼져 있음(Integrations → Data API → Enable Data API 꺼짐). 코드의 RLS 활성화 규칙과 함께 유지한다. 나중에 Data API를 켜지 않는다 | — |
| U-04 | **완료(2026-11-21):** `AUTH_JWT_SECRET`을 `backend/.env`에 입력(00이 형식 확인). 값은 채팅·문서·로그에 남기지 않는다. 배포 환경에는 로컬과 다른 값을 설정한다(§10.5) | — |
| U-05 | **완료(2026-11-21):** 발송용 Gmail의 `SMTP_USERNAME`·`SMTP_PASSWORD`(앱 비밀번호)·`SMTP_HOST`·`SMTP_PORT`·`EMAIL_FROM`을 `backend/.env`에 입력(00이 SMTP 로그인 확인). 02가 실제 인증 메일 발송에 사용 | — |
| U-06 | 의견 알림용 디스코드 채널 웹후크 URL을 `backend/.env`의 `FEEDBACK_DISCORD_WEBHOOK_URL`에 직접 입력(채널 설정 → 연동 → 웹후크 → 새 웹후크 → URL 복사). 비밀 값이므로 채팅·문서에 쓰지 않는다. 비워 두면 알림 없이 저장만 된다 | 01 이후 언제든(배포 환경에도 같은 변수 설정) |
| U-07 | **04 선행:** `backend/.env`의 `GEMINI_API_KEY`(Google AI Studio → Get API key, 무료 등급, 모델 `gemini-3.8-flash`)와 `TOP5_ALERT_DISCORD_WEBHOOK_URL`(TOP 5 알림용 새 채널의 웹후크)에 값 입력. 빈 줄은 00이 미리 추가함(2026-11-02). 비밀 값이므로 채팅·문서에 쓰지 않는다. **완료(2026-11-02 입력, 04 연결)** | — |

## 10. 미확정 정책·Codex 검토 요청

### 10.1 제품 정책 결정 대기 — 결정 전에는 해당 기능을 "제공 보류"로 구현

| ID | 결정 대상 | 영향 채팅 | 00 제안(결정 아님) |
| --- | --- | --- | --- |
| P-01 | 인증 메일 발송 공급자 | 02 | **결정(2026-11-01):** 공급자에 묶이지 않는 SMTP 발송으로 구현한다. 도메인이 없는 지금은 Gmail SMTP(`smtp.gmail.com:587`, STARTTLS, 앱 비밀번호, 하루 약 500통 한도)로 실제 발송한다. 공개 전 도메인을 확보하면 Resend·Amazon SES 등의 SMTP 정보로 설정값만 바꿔 교체한다(코드 변경 없음). Gmail 발신은 스팸함 분류 가능성이 있어 공개 운영용으로는 교체를 전제로 한다 |
| P-02 | 소셜 로그인 제공 여부, 같은 이메일 계정 연결 방식 | 02 | **최종 확정(2026-11-21 사용자 요청):** 일반 이메일 회원가입·로그인·마이페이지부터 구현한다. 카카오·구글은 디자인 시안의 버튼과 클릭 시 준비 중 안내만 구현한다. 실제 인증·회원 생성·소셜 닉네임 설정은 연결하지 않는다. 실제 소셜 연동은 일반 회원 기능 완료 후 별도로 진행한다. 소셜 회원의 내부 DB 관리가 가능하다는 조사 결과는 후속 설계 근거이며 이번 제공 범위가 아니다. 같은 이메일 자동 계정 연결은 금지한다 |
| P-03 | 회원 탈퇴 시 후기·반응·의견 처리, 같은 이메일 재가입 | 02·03·04·09 | **확정(사용자 확정 2026-11-01):** 관심 팀·반응·후기 삭제(후기는 집계에서 제외), 의견은 회원 연결만 해제. 탈퇴 후 같은 이메일로 재가입 가능(새 계정, 이전 데이터 복구 없음). 탈퇴 확인 절차는 Figma 탈퇴 다이얼로그(`62:1800`)를 따르고, 처리 후 로그아웃 상태로 메인 이동 |
| P-04 | 닉네임·비밀번호 규칙(길이·허용 문자·금칙어) | 02 | **확정(사용자 확정 2026-11-01):** 닉네임 2~12자 한글(완성형)·영문·숫자, 중복 불가. 비밀번호 8~64자, 영문과 숫자를 각각 1자 이상 포함. ~~금칙어 목록은 초기 범위에서 두지 않음~~ → **금칙어(사용자 결정 2026-11-24):** 운영자 사칭 단어(관리자·운영자·운영진·운영팀·킥탭·고객센터·공식·kicktab·admin·moderator·official·staff)와 직설적인 욕설·비속어(씨발·병신·개새끼 계열 등)가 포함되면 가입 거부, 대소문자 무시·숫자 제거 후 비교, 입력란 오류 '운영자 사칭이나 비속어로 볼 수 있는 단어가 포함되어 사용할 수 없는 닉네임입니다.'(문구 변경 2026-11-24 사용자 결정). 예외 단어는 두지 않음 — 'badminton'·'시발점'처럼 걸리는 일반 단어도 거부하고 이유는 문구로 설명. 목록은 백엔드 `auth_security.BLOCKED_NICKNAME_WORDS`와 프런트 `features/auth/rules.ts`가 같음(백엔드 테스트로 비교). 규칙 전에 만든 계정(사용자 테스트 계정 'admin')은 그대로 둠 |
| P-05 | 행정 종료(AWD·WO) 경기의 평가 제공 | 04 | 평가는 결정 전 제공 보류. TOP은 신규 후보에서 제외하되 선정 후 행정 종료로 바뀐 항목은 상태를 표시하고 유지(2026-11-01). **04 적용:** `review_open()`이 normal·aet·pen만 허용 — 행정 종료 상세는 경고 안내와 제공사 사유(`statusLong`·`statusCode`), 평가 영역 없음. **2026-11-11 사용자 지시로 추천안 적용(확정):** 경기장 밖에서 결정된 결과이므로 평가 불가 유지 |
| P-06 | TOP 5 주간 교체·실패 복구 | 04·관련 UI | **현행(2026-11-19 사용자 결정, 기획 문서 개정 반영):** 월요일 00:00 자동 선정 1회(모델 요청 최대 5회), 00:20 전 실패는 지난주 결과·준비 중 유지, 00:20까지 미공개면 지연 안내·운영 알림 1회·수동 복구. **이전(2026-11-02 확정, 폐지):** 00:00 첫 시도→실패 시 00:05 자동 1회 재시도→재실패 지연 안내/운영 알림/수동 복구. 공개 전 서버 지난주 결과를 실제 소속 기간으로 유지. 검증 성공 즉시 교체·공개 후 고정. 공개 UI 3종, 오류별 화면 없음. 시도별 시간 제한·중복 실행 방지·알림·관리 명령·클라이언트 완료 감지는 실제 구현 검증 대상 |
| P-07 | 경기 상태 변경 시 기존 평가 처리(D-07 잔여) | 04 | 종료→중단·취소 등 평가 불가 상태로 바뀌면 숨김 처리 후 원복 시 재노출. **04 적용:** 평가 노출을 현재 상태(`review_open()`)로 매번 판정해 데이터는 지우지 않고 숨김·재노출된다. **2026-11-11 추천안 적용:** 진행 중 코드 중 SUSP(재개 불확실한 장시간 중단)는 경기 중단과 같이 닫고(`CLOSED_LIVE_CODES`), INT(경기 안의 짧은 멈춤)는 진행 중으로 연다. 재개되면 다시 보인다 |
| P-08 | 뉴스 대회/팀 분류 세부 규칙, 언론사명 매핑 방식(D-09) | 03 | **03 적용(2026-11-02, 사용자 피드백 반영):** 분류는 `app/services/news_classify.py`(AI 미사용, 제목·설명만): 대회명이 명시돼야 하고, 기사의 **주제**여야 한다 — 제목에 대회명이 있거나, 주체 팀(제목의 팀, 제목에 팀이 없으면 설명에 처음 나오는 팀)이 이번 시즌 **바로 그 대회**(UCL·UEL·UECL 구분)에 참가할 때만 인정. MLS·사우디 등 다른 리그 맥락이면 제목 팀 경로만 인정(예: 'EPL도 아닌데' 손흥민 LAFC 기사 제외, 과거 UEL 우승 회고 기사 제외). UEFA가 국내 리그보다 우선, 국내 리그 2개 이상·근거 없음은 제외, AFC·다른 나라 리그는 해당 뱃지 근거 제외, 여자 축구(여자축구·위민·WSL·라리가F·'여자 프리미어리그' 등)·다른 종목·토토는 팀 연결 전에 기사 전체 제외(교차 검증 반영, 남자 팀 ID 연결 방지), 팀도 대회 단어도 축구 맥락 단어도 없는 기사(광고·제휴 등) 제외. 팀은 `for_news` 별칭만(모호한 별칭·도시명과 겹치는 짧은 별칭 제외), 여러 팀 연결. 중복은 정규화 원문 URL 해시와 같은 제목으로 1회. 표본 40건 사람 판정(주제 기준 적용 후): 대회 뱃지 적합 37건, 부적합 3건(축구 외 시위 기사·칼럼·이적설 기사의 부수 언급) — 규칙 기반 한계로 보고. Codex 교차 검증 표본 28건: 적합 24·오분류 1(밀너 마라톤 기사가 과거 챔피언스리그 이력 언급으로 UEFA)·주제 재검토 3 — 과거 이력·부수 언급은 보정 표본 후보. 참가 팀 정보는 `team_competition_seasons`(리그·UEFA 팀 목록)를 쓴다. **출처 표시:** 2026-11-02 최신 사용자 결정(언론사 표시명 제외, API 검증 문서)에 따라 매핑 표 없이 원문 도메인만 표시 — §10.3 D-03-1 |
| P-09 | 폐지: 뉴스 개인 저장의 중복 키·보존 범위 | — | 2026-11-21 제거 확인. BOOK-001~003·UF-16은 폐지 ID로만 남기며 API·테이블·추가 권한 검토를 구현하지 않는다 |
| P-10 | 의견 스팸 방지·보존 정책(D-11 잔여) | 01·02 | **01 적용(사용자 결정 2026-10-31):** ① IP별 분당 3회·일 20회 + 서비스 전체 분당 20회·일 300회(메모리 기반, IP는 DB에 저장하지 않음, 잘못된 JSON을 포함한 형식 오류 요청도 횟수에 포함) ② 허니팟 입력칸(`website`, 사람에게는 보이지 않음 — 값이 있으면 저장·알림 없이 400) ③ 중복 본문 차단(공백·대소문자를 정규화한 SHA-256을 `feedback.body_hash`에 저장, 24시간 안의 같은 본문은 발신자와 무관하게 409 `FEEDBACK_DUPLICATE`, 동시 제출은 본문 해시별 트랜잭션 잠금으로 직렬화). **02 예정:** 회원·비회원 차등 제한 — 회원은 사용자 ID 기준, 비회원은 IP 기준으로 더 엄격하게(제안값: 회원 분당 3회·일 20회, 비회원 분당 2회·일 5회, 02에서 확정). `RateLimit`의 `key_func`·제한값을 인증 상태에 따라 고르는 의존성으로 구현. CAPTCHA는 실제 남용이 확인될 때만 검토. 보존 기간은 운영 전 결정. 의견 본문이 디스코드로 전송되므로 개인정보처리방침(P-12)에 외부 전송 사실을 반영 |
| P-11 | 팀 별칭 사전 구축·관리 방식(D-16) | 03 | **03 적용(2026-11-02):** `backend/app/seed/team_aliases.json`(현재 시즌 5대 리그 96팀 한국어 이름·한국어/영문 별칭, `searchOnly`, `ambiguous` 묶음) → `uv run python -m app.sync team_aliases`(또는 `reference` 끝에서 자동). 여러 팀 표현(레알·시티·유나이티드·맨체스터·밀란·마드리드·보루시아·파리 등)은 검색에서 후보 선택, 뉴스에서 근거 제외. 2026-11-04부터 5대 리그 밖 UEFA 팀은 `uefa_team_names.json`의 한국어 이름과 별칭도 검색할 수 있다. 이름 미등록 팀은 영문으로 표시한다 |
| P-12 | 가입 필수 동의·연령 자가확인·약관 문서 | 02·공개 전 | **확정 2026-11-21:** `[필수] 서비스 이용약관 동의`, `[필수] 개인정보 수집·이용 동의`, `[필수] 만 14세 이상입니다`를 모두 미선택으로 표시한다. 세 항목 모두 확인해야 가입 가능하며 만 14세 미만 가입은 받지 않는다. 서버도 누락/false와 우회 요청을 거부한다. `terms_agreements`에 항목별 ID·버전·확인 여부·시각을 기록한다. 약관·개인정보 본문은 사용자가 공개 전 확정하며 그 전 보기는 준비 중·기록 버전은 draft다. 연령은 자가확인으로 실제 나이 검증이 아니며 생년월일·신분증·추가 인증 수집은 도입하지 않는다 |
| P-13 | 분석 지표 도구·동의·익명 식별(D-12) | 최종 | 기능 완료 후 별도 결정 |

### 10.2 Codex 검토 요청 — 기술 설계(기획 변경 없음, 확인 요청)

소셜 로그인 확인 근거(2026-11-21): [카카오 설정](https://developers.kakao.com/docs/ko/kakaologin/prerequisite)과 [서비스 회원 처리](https://developers.kakao.com/docs/ko/kakaologin/common), [Google OpenID Connect](https://developers.google.com/identity/openid-connect/openid-connect)를 확인했다. 권장 구조는 내부 `users`를 공통 회원으로 두고 `auth_identities`에 제공자와 고유 ID를 연결하는 방식이다. 카카오는 회원번호, Google은 검증한 `sub`를 사용하며 이메일은 연결 키로 쓰지 않는다. 관심 팀·평가는 공통 내부 회원 ID를 참조한다. 최초 서비스 가입에는 닉네임과 서비스 필수 동의를 적용하고, 제공자가 이메일을 주지 않으면 임의 값을 만들지 않는다. 이메일 수집 방식과 제공자 연결 해제·설정/권한·공개 가능 상태는 실제 소셜 제공을 확정할 때 점검한다. 앱 콘솔 등록 상태나 실제 로그인은 이번 작업에서 확인하지 않았다.

| ID | 내용 | 이유 |
| --- | --- | --- |
| C-01 | Supabase Auth 대신 FastAPI 자체 인증 | 가입 전 인증번호 확인·미인증 계정 없음 규칙, 기존 psycopg 구조 유지 |
| C-02 | Next.js `rewrites`로 같은 출처 구성 + `httpOnly` 쿠키 토큰(접근 15분·갱신 14일 회전) | 토큰을 브라우저 스크립트에 노출하지 않음. 배포 시 프런트·백엔드 연결 방식이 이 구조를 지원해야 함 |
| C-03 | 수집 작업을 백엔드 내 APScheduler(단일 인스턴스) + CLI로 실행 | 배포 플랫폼 미정. 플랫폼 크론으로 바꿀 수 있게 분리 |
| C-04 | Supabase Direct connection이 IPv6 전용일 수 있음 | 배포 환경에 IPv6가 없으면 Supavisor 세션 풀러 연결로 바꿔야 함(배포 시 확인) |
| C-05 | 모든 테이블 RLS 활성화(정책 없음) + Data API 비활성화 — 사용자 확정(2026-10-31) | Supabase 공개 API로 테이블이 노출되는 것을 방지 |
| C-06 | 실시간 갱신을 클라이언트 폴링(30~60초)으로 구현 | 웹소켓 없이 단순화. 실제 경기 검증(V-04) 후 조정 |
| C-07 | 개발 DB(`kicktab-dev`) 하나로 개발하고, 공개 배포 전 운영용 Supabase 프로젝트를 분리할지 결정 | 개발 중 마이그레이션·테스트 데이터가 운영 데이터와 섞이지 않게 하기 위함(배포 시 결정) |
| C-08 | **배포 시 필수 작업(사용자 결정 2026-10-31, A안):** Next.js `rewrites` 프록시는 브라우저가 보낸 `X-Forwarded-For`를 그대로 전달한다(헤더가 없을 때만 채움, 01에서 확인). 배포 시 앞단 프록시가 이 헤더를 실제 클라이언트 IP로 덮어쓰게 하고(예: Nginx `proxy_set_header X-Forwarded-For $remote_addr;`, Vercel·Cloudflare는 기본 동작 확인) 백엔드 `TRUSTED_PROXIES`를 그 경로에 맞춘다. 코드 쪽 안전망(B안)인 전역 상한은 01에서 반영 완료 | 앞단 설정 전에는 클라이언트별 제한을 헤더 위조로 우회할 수 있고, 전역 상한만 남는다. 로컬 개발 환경은 우회 가능한 상태 |

### 10.3 기존 기획·디자인 변경 요청

2026-11-01 TOP 5 정책 변경을 PRD·기능 명세·유저 플로우·와이어프레임과 Figma 시안에 반영했다. 앱의 띠·펼침 목록 UI·응답 계약은 01 재검수에서 2026-11-01 정책 기준으로 반영했다. 2026-11-02 개정(공개 UI 3종·지난주 결과 유지·지연 안내·교체 감지)의 앱 반영과 실제 선정 작업은 모두 04가 맡는다(사용자 결정 2026-11-02, §6.4 TOP 5). Figma 적용 위치와 검수 한계는 §1의 AI TOP 5 디자인 반영 항목을 따른다. 그 밖에 기능 채팅에서 변경이 필요하면 이유·대안·영향을 이 절에 추가하고 Codex 검토로 전달한다.

01 구현 중 Figma에 프레임이 없거나 기준끼리 어긋난 항목은 아래처럼 처리했다. Codex 검토와 디자인 확인을 요청한다.

| ID | 항목 | 01 처리 | 확인 요청 |
| --- | --- | --- | --- |
| D-01-1 | TOP 5 빈 상태 | 2026-11-01 디자인 갱신: `128:3674`·`128:3686` 및 공통 띠 none 상태에 '이번 주 지원 대회의 예정 경기가 없습니다' 적용. 준비·후보 조회 실패·AI 실패와 구분. 주간 기간은 조회 주 키를 사용하며 이전 주 결과로 대체하지 않음 | 해결 — 01 재검수에서 앱 반영(2026-11-02) |
| D-01-2 | TOP 5 펼침 목록 | 해결(2026-11-02 재반영): `KickTab/TOP5 Panel`(`159:924`) 기준 데스크톱 헤더 바로 아래 1280px 패널 + 12% 배경(`128:3700`), 모바일 핸들 있는 하단 시트(`128:4408`·`167:6697`). 시트는 헤더·띠 아래까지만 커지고 목록만 스크롤 | — |
| D-01-3 | 모바일 메뉴의 위치 미지정(`62:1427`) | TOP 5·의견 보내기와 같은 하단 시트. 계정 버튼은 Figma `133:4134`대로 로그인(ghost)·회원가입(primary) 가로 배치 | 위치 |
| D-01-4 | 푸터 리디자인(`49:532`·`49:1012`, 2026-10-31)에서 '맨 위로'·브랜드 소개 문구·'서비스 소개'·권리 고지 문장 제거 ↔ COM-003 5번·PRD 7장 푸터 구성(브랜드 소개, 맨 위로, 이미지 출처·권리 고지 포함) | Figma대로 구현 | 기능 명세서·PRD 푸터 항목 갱신 또는 디자인 보완 |
| D-01-5 | 푸터 운영자·출처 문구 11px(Figma) ↔ 보조 설명 12px 이상(컬러 가이드) | Figma대로 11px/19px | 글자 크기(Codex 의견: 12px/20px 통일 권장) |
| D-01-8 | TOP5 공개 UI 3종 및 주간 교체 | **2026-11-02 Figma 반영:** 목록·경기 없음·지연 안내. 첫 시도/재시도 동안 서버 지난주 결과와 실제 소속 기간 유지. 후보 부족·상태 변경은 목록 데이터 | 04의 공개 응답 계약·주간 작업과 01의 UI 반영·통합 검증 |
| D-01-9 | 의견 유형 필수(사용자 결정 2026-10-31) ↔ 기능 명세서 FEED-002·PRD 21장 '유형 선택(선택)', Figma 의견 모달 '의견 유형 · 선택' | 화면 표기 '의견 유형 · 필수', 유형을 고르기 전에는 전송 버튼 비활성·안내 문구, API도 `type` 필수. DB 컬럼은 기존 행 때문에 NULL 허용 유지 | 기획 문서·Figma 표기 갱신 |
| D-01-6 | 의견 전달 완료 상태 아이콘이 검색 아이콘(`62:1882`) | Figma대로 사용 | 아이콘 교체 여부(Codex 의견: 체크 아이콘) |
| D-01-7 | 뉴스 출처 BI 표시(COM-003) | 텍스트 'NAVER'만 표시, 이미지 권리 문구는 Figma 문구를 임시 사용 | V-09·V-10 확인 후 반영 |
| D-01-10 | **04 결정·반영(2026-11-03, 대안 A):** `weekly_top_matches.selected_kickoff_at`을 저장해 `items[].selectedKickoffAt`으로 반환, 일시 칸은 선정 당시 일시, 최신 킥오프가 다르면 아래 줄에 '변경 일시 …', 연기·시간 미정이면 '변경 일시 미정'. 이하 01 당시 기록 — TOP 5 '변경 일시'(Figma `159:513`: 일시 칸은 선정 당시 일시, 아래 줄에 바뀐 일시) ↔ §6.4 계약은 최신 `match.kickoffAt` 하나만 있어 선정 당시 일시와 '일시만 바뀐 예정 경기'를 알 수 없음 | 계약을 바꾸지 않고 일시 칸에 최신 일시, 연기·취소·중단·행정 종료 항목에 '변경 일시'(연기+시간 확정이면 최신 일시라 일시 칸과 같은 값, 그 밖은 '미정' + `statusReason`) 표시 | 대안 A: 04가 `items[]`에 선정 당시 킥오프(예: `selectedKickoffAt`)를 저장·반환해 Figma대로 표시(계약 필드 추가, 01 화면 소폭 수정). 대안 B: 현 방식 유지하고 Figma를 '현재 일시 + 상태'로 단순화 |
| D-01-11 | **04 반영:** 모바일 띠의 경기 없음·지연은 기간 줄과 안내 줄 두 줄(가변 높이), 목록은 '기간 · n경기 · 상태'. TOP5 모바일 띠 기간·안내 | **2026-11-02 Figma 반영:** 목록·경기 없음·지연 모두 기간 표시. 경기 없음·지연은 줄바꿈에 따른 가변 높이로 320px에서 확인 | 실제 앱의 이전 고정 높이·긴 문구 말줄임을 새 설계에 맞춰 보완 |

03 구현 중 기준끼리 어긋났거나 Figma에 없는 부분은 아래처럼 처리했다. Codex 검토와 사용자 확인을 요청한다.

| ID | 항목 | 03 처리 | 확인 요청 |
| --- | --- | --- | --- |
| D-03-1 | 뉴스 출처: Figma 카드 'OO스포츠' + 가이드 P-08 기본값(도메인→언론사명 매핑) ↔ API 검증 문서의 2026-11-02 최신 사용자 결정(언론사 표시명 제외, 카드 = 제목·설명·분류·날짜) | 최신 결정을 따라 매핑 표 없이 원문 도메인(`sportschosun.com`)·상대 시각·'원문 보기 ↗'를 표시하고, 영역 하단에 '뉴스 제공: 네이버 검색' 표기. 기능 명세 NEWS-001 '출처 표시, 도메인을 공식 언론사명으로 단정하지 않음'은 충족 | 도메인 표시 유지 / 언론사명 매핑 추가 / 출처 칸 제거 중 선택 |
| D-03-2 | 원문 삭제·접근 불가 안내(NEWS-004) — Figma 화면 없음 | 카드 클릭 → `/news/original?id=` 전환 화면에서 원문을 1회 확인(HEAD, 실패 시 GET 헤더). 정상·확인 불가(timeout 등)는 바로 원문으로 이동, 404/410만 '원문 기사를 확인할 수 없습니다' + 원문 주소 열기. 언론사 사이트에 클릭당 1회 요청 | 전환 화면 디자인 |
| D-03-3 | 관심 팀 경기 카드(Figma `49:330`은 '대회 · 시각'만) | 약 2주 범위의 경기가 섞이므로 '대회 · 11/5(목) 02:45'처럼 날짜를 함께 표시 | 날짜 표기 유지 |
| D-03-4 | 경기 기본 수량·전체 보기 개정 | **최신 디자인2026-11-03:** 기본6개→현재 조건 전체 보기(수량 표시)→접기. 조건 변경 시6개로 복귀. 이전 앱의5개씩 더 보기는 구현 이력이며 후속 보완 대상 | 디자인 확정·앱 후속 |
| D-03-5 | 상태 뱃지 진행 표기: TOP 5 `63′` ↔ 컴포넌트 시트 `55:27`·메인 '진행 중 63분' | 개정 Figma `187:591`(경기 행)에 맞춰 `MatchStatusBadge`를 '진행 중 63′'·예정 회색으로 통일(TOP 5 포함). 대회 표기는 한국어 이름(`competitionName`) | 컴포넌트 시트 `55:27`의 '63분'·예정 파랑 표기 정리 |
| D-03-6 | 대회 체크 적용·팀21일 개정 | **최신 디자인2026-11-03:** 단일 체크 초안/적용/취소, 오늘−3~+17의21일. 이전03의 직접/보조 다중·14일 구현 완료 기록은 구 정책 구현 이력이다. 최종 Figma·인계 기준으로 후속 보완 | 디자인 확정·앱 후속 |
| D-03-7 | 쿠프 드 프랑스 2026 | 2026-11-02 `/leagues` 재조회에서 2026 시즌이 제공되어(시작 10/31) `available`로 수집·표시. V-16의 '오픈 직전 재조회'는 그대로 유지 | V-16 기록 갱신 |
| D-03-8 | 모바일 팀 검색 입력(Figma 40px) | 입력은 40px, 감싼 label을 44px로 두어 조작 영역 확보 | — |

04 구현 중 기준끼리 어긋났거나 Figma에 없는 부분은 아래처럼 처리했다. Codex 검토와 사용자 확인을 요청한다.

| ID | 항목 | 04 처리 | 확인 요청 |
| --- | --- | --- | --- |
| D-04-1 | 비회원 '로그인하고 평가하기' 버튼(Figma `52:294`) — `/login`이 02 전까지 없음 | (이전 결정) 빈 버튼 금지 원칙대로 넣지 않았다. **2026-11-19 사용자 결정으로 대체:** 공개 전 화면이라 Figma 최신 408:16478대로 04가 `ReviewLoginNotice.tsx`에 '로그인' 버튼을 넣었고 동작은 02가 연결(§3.1) | 02에서 연결 |
| D-04-2 | 후기 안내 위치 개정 | **최신 디자인2026-11-03:** 제목 옆 원형!·여러 줄 팝오버. 기존 상시 주의사항은 제거한다. 이전04에서 항상 보이게 구현한 것은 구 UI 이력이며 후속 반영 대상 | 디자인 확정·앱 후속 |
| D-04-3 | 지난주 결과가 '경기 없음'일 때 문구(Figma none은 '이번 주 지원 대회의 예정 경기가 없습니다'만 있음) | 이번 주로 가장하지 않도록(TOP-003) 지난주 유지 시 '지난주 지원 대회의 예정 경기가 없었습니다' | 문구 |
| D-04-4 | 상대 전적 표(Figma `63:1909`: 날짜·대회·결과) ↔ MAT-005 '홈/원정' 표시 | '홈 · 원정' 열(홈팀 vs 원정팀)을 추가하고 승무패 요약 줄 표시, 5경기 미만이면 '범위를 넓혀 확인한 공식 맞대결만 표시' 안내 | 열 구성 |
| D-04-5 | 타임라인의 '경기 종료 90+4′'·'전반 종료 45+2′'(Figma `52:257`) ↔ MAT-002 '제공 이벤트만' | 제공사 이벤트가 아니므로 표시하지 않음. 이벤트는 최신순, 교체는 '나간 선수 → 들어간 선수' | — |
| D-04-6 | 선수 평점 탭에 '선수별 경기 기록'(MAT-004) — Figma `94:4418`은 평점만 | Figma대로 평점만(저장 원본에는 기록 전체 보관) | 기록 열 추가 여부 |
| D-04-7 | 후기 작성자 닉네임 | `users`가 없어 `authorNickname` null → '—'(02가 채움) | — |

05 구현 중 기준끼리 어긋났거나 Figma에 없는 부분은 아래처럼 처리했다. **Codex 교차 검증(2026-11-05)에서 D-05-1~5 처리가 모두 타당하다고 확인했다.** 디자인 갱신 여부는 사용자 확인으로 남긴다.

| ID | 항목 | 05 처리 | 확인 요청 |
| --- | --- | --- | --- |
| D-05-1 | 결과 행(Figma `53:593`·`61:883`: 구분선 행, 영문 대회명 'Champions League') ↔ 공통 경기 카드(`187:591`, 메인과 같은 테두리 카드·한국어 대회명) | 작업 지시·§2대로 `MatchCard`(schedule)를 재사용. 날짜 제목은 Figma대로 `2026-10-29`(시즌이 해를 넘으므로 연도 포함) | 지난 경기 프레임을 공통 카드로 갱신할지 |
| D-05-2 | 행정 종료 스코어(Figma `61:883` 더미 '낭트 VS 파리 생제르맹 · 행정 종료') | 04 경기 상세와 같은 규칙: 제공 스코어(실제 1388000은 0 : 0) + 주황 '행정 종료' 뱃지로 일반 종료와 구분, 값은 바꾸지 않음 | 스코어 칸 표기(제공값 / VS / —) |
| D-05-3 | 페이지 분할(Figma `53:926`: 이전·번호 3개·다음) ↔ 2025-26 전체 413페이지 | **해소(2026-11-24):** Figma 'KickTab/Results Pagination' `556:7312`에 « »(첫·마지막 페이지)가 추가되어 시안대로 구현 | 차이 없음 |
| D-05-4 | 선택 팀 안내(Figma `57:477` historic-team: '웨스트햄 · 팀 상세 미제공'과 안내 문구만) | `detailAvailable` false는 Figma대로, true는 '{팀} 팀 상세 보기' 링크, null은 팀 이름만(강등 단정 없음) | 링크 표기 |
| D-05-5 | Figma 상태 묶음(`57:477`: 정상·결과 없음·로딩·조회 실패·이전 시즌·상세 미제공 팀)에 없는 상태 | 미지원 시즌('지원하지 않는 시즌입니다' — 필터 숨김, 다른 시즌으로 대체하지 않음), 미수집 503(서버 문구), 일부 대회 미적재(주의 상자), 마지막 페이지 초과('이 페이지에는 경기가 없습니다' + 마지막 페이지로) | 문구·디자인 |

06 구현 중 기준끼리 어긋났거나 Figma에 없는 부분은 아래처럼 처리했다. Codex 검토와 사용자 확인을 요청한다.

| ID | 항목 | 06 처리 | 확인 요청 |
| --- | --- | --- | --- |
| D-06-1 | 리그 선택: PRD 16장·작업 지시 '리그·시즌 드롭다운' ↔ Figma `53:1353`·`53:2047` 리그 탭 | 화면 표현은 Figma를 따라 시즌만 `SeasonSelect` 드롭다운, 리그는 탭(`Tabs`, URL `league`) | 기획 문서 표기를 '리그 탭'으로 맞출지 |
| D-06-2 | 시즌 드롭다운 폭: 리그 순위 프레임 316px ↔ 공통 트리거 `93:3198` 220px | 지난 경기와 같은 공통 `SeasonSelect` 220px(모바일 전체 폭) 유지 | 프레임 폭 정리 |
| D-06-3 | 현재 시즌 표의 강등권 표시: Figma 현재 시즌(`53:1353`)에는 표시 없음, 이전 시즌(`61:1653`)만 '당시 강등' | 이전 시즌만 그 시즌 `description`으로 '당시 강등'·'당시 승강 PO'를 표시하고, 현재 시즌은 진행 중이라 표시하지 않음(`zone`은 응답에 있음). '팀 상세 미제공'은 시즌과 무관하게 허용 집합으로 표시 | 현재 시즌 강등권(진행 중) 표시 필요 여부 |
| D-06-4 | 퇴장 순위의 0회 선수: API `/players/topredcards`가 시즌 초에 직접 퇴장 0회 선수(경고 누적 1회·0회 포함)로 20명을 채움(2026-27 EPL 14~20위 red 0) | 규칙(제공 상위 20명·제공 순서·red만 표시)대로 그대로 두어 '0'이 보임. `yellowred`는 저장만 | 직접 퇴장 0회 행을 숨길지(숨기면 '상위 20명' 표기와 달라짐) |
| D-06-5 | 선방 순위 인원: 시즌 중 API가 출전하지 않은 골키퍼에도 0(값 있음)을 주면 그 선수는 0으로 집계·공동 최하위(2026 EPL 42명 중 일부). null만 제외 | 정책대로 null만 제외하고 제공된 0은 그대로 집계(검증 문서의 2025 집계와 같은 규칙) | 0 선방 골키퍼 표시 범위 |
| D-06-6 | 상태 묶음 `57:599`의 '팀 순위/선수 순위' 하위 탭 ↔ 대표 프레임 `53:1353`의 두 카드 동시 표시 | 대표 프레임대로 두 카드를 함께 표시(모바일은 팀 순위 아래 선수 순위). 상태 문구(제외 인원·소속 확인 실패)는 묶음 기준을 따름 | — |
| D-06-7 | 메인 간소 순위 칩 이름: Figma `49:368`·`49:848` 'EPL'·'BUN' ↔ 리그 순위 탭 'Premier League'·'Bundesliga' | 메인 칩은 Figma대로 'EPL'·'LaLiga'·'Serie A'·'BUN'·'Ligue 1'(Codex 1차 지적 4로 'Bundesliga'→'BUN' 보완), 리그 순위 탭은 전체 이름, 상위 6팀·팀 이름은 링크 없이 표시 | — |
| D-06-8 | 최근 5경기 방향: API `form` 문자열의 최신 경기 위치가 문서화돼 있지 않음 | 제공 순서 그대로 '승/무/패'로 표시(순서를 뒤집지 않음) | — |

07 구현 중 기준끼리 어긋났거나 Figma에 없는 부분은 아래처럼 처리했다. **Codex 1차 교차 검증(2026-11-06)에서 D-07-1~7 처리가 타당하다고 확인했다**(D-07-5 페이지 초과 후 갱신 실패·D-07-6 검색 기록은 지적 3·1로 보완). 디자인 갱신 여부는 사용자 확인으로 남긴다.

| ID | 항목 | 07 처리 | 확인 요청 |
| --- | --- | --- | --- |
| D-07-1 | 카드 둘째 줄: Figma `52:624` 레이어 이름은 '팀 이름과 리그'인데 더미 글자는 영문 약칭('Arsenal')만 ↔ LEAG-003·PRD 16장 출력 '엠블럼·팀명·리그' | 'Arsenal · Premier League'처럼 영문명과 리그(`shortName`)를 함께 표시(한국어 이름이 없으면 리그만 — 팀명이 영문이므로). '전체'에서 리그를 구분하기 위함 | 둘째 줄 구성(영문명+리그 / 리그만) |
| D-07-2 | 목록 순서: Figma 더미는 아스널·맨시티·리버풀… 순(기준 없음) | 리그 순서(Figma 칩 순서) 뒤 한국어 이름 가나다순, 검색은 일치 정도순. 순위·인기순은 기준이 정해지지 않아 쓰지 않음 | 정렬 기준 |
| D-07-3 | 관심 팀 한도 도달 | 비회원 5 / 5·회원 10 / 10을 구분한다. 안내 상자 role=status와 등록 불가 이유를 제공하며 해제는 유지한다. 새 팀 추가는 비회원 6번째·회원 11번째부터 거부한다. 다른 페이지에서도 실제 등록 목록·한도 상태를 함께 갱신한다 | 2026-11-21 회원 한도 정정 |
| D-07-4 | 상태 묶음의 정상 상태 버튼(파란 채움 '☆ 관심 팀 등록') ↔ 대표 프레임(미등록 흰 테두리, 등록됨 파란 채움·카드 파란 테두리) | 대표 프레임대로 | 상태 묶음 정리 |
| D-07-5 | Figma에 없는 상태: 저장소 차단, 잘못된 URL 조건, 마지막 페이지 초과, 리그 선택 중 검색 결과 없음, 재조회 실패(확인된 목록 있음) | 저장소 차단 — 안내 상자 자리에 주황 '이 브라우저에서는 관심 팀을 저장할 수 없습니다. 팀 목록은 계속 볼 수 있습니다.'(목록·필터·검색 유지). 잘못된 리그·페이지·검색어 — '조회 조건을 확인할 수 없습니다'+'필터 초기화'(05와 같음). 페이지 초과 — '이 페이지에는 팀이 없습니다'+'마지막 페이지로'. 리그 선택 중 결과 없음 — '현재 시즌 {리그} 팀만 찾을 수 있습니다.'. 목록 위 개수 줄은 검색 시 '현재 시즌 5대 리그 · '맨체스터' 검색 결과 2개 팀'. 재조회 실패 — 목록 위 '팀 목록을 다시 확인하지 못했습니다. 마지막으로 확인한 목록입니다.'+'다시 확인'(06 `partialAction`과 같은 형태) | 문구·디자인 |
| D-07-6 | **2026-11-18 개선으로 대체:** 기획 v1.12·Figma 52:624대로 공통 `TeamSearch`(라벨 '팀 검색'·자동완성)를 쓴다. Figma에 없는 동작 — 후보 선택 시 리그 '전체'로, 후보 없는 Enter로 목록 단어 검색, 드롭다운 일치 없음은 공통 문구(Codex 교차 검증에서 모두 타당 확인). 이하 이전 기록 — 검색 입력: Figma `52:705` 40px 입력(아이콘 없음) — 자동완성 후보 목록 없음 | 메인의 `TeamSearch`(한 팀을 고르는 자동완성)를 쓰지 않고, 입력한 이름으로 목록 자체를 거른다(모호한 별칭은 후보 팀이 모두 목록에 남음). 40px 입력 + 44px 조작 영역(D-03-8과 같음), 입력이 있으면 × 지우기 | — |
| D-07-7 | 태블릿 폭(640~1023px): Figma는 데스크톱 3열·모바일 1열만 | 640px부터 2열, 1024px부터 3열 | — |

08 구현 중 기준끼리 어긋났거나 Figma에 없는 부분은 아래처럼 처리했다. Codex 검토와 사용자 확인을 요청한다.

| ID | 항목 | 08 처리 | 확인 요청 |
| --- | --- | --- | --- |
| D-08-1 | 국적 표기: Figma 선수 표 '아르헨티나'·'대한민국'(한국어) ↔ API는 영문 국가명만 제공, 한국어 국가명 사전 없음 | 제공값 그대로 영문(예: 'Argentina'), 없으면 '—'. 국가명 번역 표를 만들지 않음(제공값 외 정보 생성 금지) | 영문 유지 / 국가명 한국어 사전 추가(별도 작업) |
| D-08-2 | 선수 표 기본 정렬: Figma 머리글 '번호 ↑' ↔ TEAM-002 규칙 2 '기본 정렬은 포지션순' | 기능 명세대로 포지션순(GK→DF→MF→FW, 같으면 번호·이름)으로 열고 '포지션 ↑' 표시. 모든 열 정렬(누락값은 두 방향 모두 맨 뒤), '선수 더 보기 · {남은 수}명' | Figma 머리글 표시 정리 |
| D-08-3 | 경기 영역: Figma 최근 결과 3개·시각만 ↔ 기능 명세·작업 지시 '최근 결과 5개' | 예정(진행 중 먼저) 최대 3개 + 최근 결과 5개. 여러 주에 걸치므로 공통 `MatchCard`의 날짜 표기(`withDate`, '11/8(일) 02:30')를 씀(D-03-3과 같음) | 프레임 갱신 |
| D-08-4 | 시즌 기록 행: Figma 5행(득점/실점·홈·원정·무실점·주 포메이션) ↔ TEAM-005 규칙 2 '기존 지난 시즌 성적은 지난 시즌 기록에 포함' | 맨 위에 '리그 순위'(그 시즌 순위·승점, 지난 시즌은 최종 순위) 행을 더함 | 행 추가 유지 |
| D-08-5 | 팀 뉴스 범위·문구: Figma '전체 최신 최대 48개 안에서 팀 관련 기사만 표시합니다', '관련 뉴스 2/2' ↔ 03 결정 '팀만 연결되고 뱃지가 없는 기사는 팀 상세에서만 쓴다'(메인 48개는 뱃지 기사만) | **2026-11-18 수정:** 팀에 연결된 기사(뱃지 없는 기사 포함, 같은 기사는 1건) 최신 최대 **24개**를 6개씩, 문구는 '팀 관련 최신 기사를 최대 24개까지 표시합니다.', 버튼은 더 있을 때만 '관련 뉴스 더 보기 (6/24)'. 기사가 없으면 '현재 확인할 수 있는 팀 관련 뉴스가 없습니다.'만(분류 정책 설명 없음 — TEAM-004·NEWS-003·UF-11). 메인 뉴스는 48개 그대로. 개인 기사 저장 기능은 폐지 | 범위·문구 |
| D-08-6 | 이적 표시: Figma 유형 '완전 이적·임대·계약 만료'·금액 ↔ 제공 유형은 영문 단어(금액은 2025년부터 사실상 없음). 제공사가 같은 이동을 여러 줄로 줌 — (가) 같은 선수·날짜·방향에 상대 팀 ID 있는 줄과 이름만 있는 줄('PSV'/'PSV Eindhoven', 'Hull'/'Hull City') 369줄, (나) 같은 선수·방향·상대 팀 ID·시즌이 1~46일 간격으로 다시 등록 937줄(예: J. Stones) | **2026-11-18 수정:** 저장은 원본 그대로, 응답 때 `merge_transfers()`로 정리(재수집해도 원본 보존). (가) ID 있는 줄이 있으면 ID 없는 줄을 뺀다. (나) 같은 선수·방향·상대 팀 ID·시즌의 여러 줄은 가장 이른 날짜 1건 — 단 그 사이(앞 이동 날짜~이번 날짜)에 반대 방향 이동(상대 무관)이 있으면 별개 이동(Codex 1차 지적 8 유지), 상대 팀 ID가 없는 줄은 (나)로 합치지 않음(Codex 2차 N2). 결과(전체): 2025-26 7,159→5,960, 2026-27 4,559→4,355(00 실측 5,956·4,354와 차이 4·1건 — 반대 방향 이동이 경계 날짜와 같은 날인 경우를 별개로 보존). **표시 기준 B:** ① 현재 선수단이거나 이번·지난 시즌 지원 대회에서 이 팀으로 뛴 선수 ② 영입 중 유형 Transfer·Free agent·Free Transfer·Free이고 U21·B팀·유스·리저브가 아닌 팀에서 온 이동 ③ 상대 팀이 이번·지난 시즌 5대 리그·UEFA 참가 팀 — 하나라도 맞으면 먼저 보이고, 나머지는 반기마다 '기타 이동 N건' 접기(삭제·생성 없음). 팀 평균 45.4→28.3건(맨시티 2026 57→35, 기타 22; 아칸지(인테르)·에체베리(벤피카 임대) 표시). 유형 번역: Transfer 완전 이적, Loan 임대, Return/Back from loan 임대 복귀, Free agent 자유계약, Free Transfer·Free 자유 이적, End of career 은퇴, Raise 유스 승격, 금액 형식('€ 12M')은 완전 이적(금액은 표시하지 않음, D-08-10), 그 밖은 그대로, 없음·'N/A'는 '—'. 반기는 Figma 471:6856 밑줄 탭(전반기·후반기) 하나씩 보여 주고 시작 전 반기는 비활성(흐리게·클릭·키보드 불가·`aria-disabled`), 탭 줄 오른쪽 끝에 '후반기는 1월부터'(기간 줄과 같은 크기·색) 상시 표시, 회색 안내 상자는 없앰. 열린 반기에 기록이 없으면 '아직 확인된 이적이 없습니다'. 최근 갱신 날짜는 이번 시즌에만 **2026-11-24 안전장치 비교 기준:** 수집 응답의 감소 판정도 이 동일 사건 기준을 쓴다 — 줄 수가 아니라 D-08-6 정리 후 저장 이동 중 새 응답에 없는 이동 수(허용 max(2, 10%)). 공급사가 반복 사본을 스스로 줄인 응답(53팀, 잃은 이동 0)은 저장되고, 실제 이동이 허용 폭보다 많이 빠진 응답은 계속 거부한다. 같은 구단으로의 임대 → 복귀 → 재임대처럼 사이에 반대 방향 이동이 있으면 별개 이동으로 센다(자체 검증 보완). | 유형 번역·중복 정리·표시 기준 |
| D-08-6a | 이적 출전 근거(현행 2026-11-21 사용자 결정 B, 11/20 appearances_unknown 해석 대체) | **2026-11-21 사용자 결정 B 반영 완료(커밋·`dev` 병합):** Codex 교차 검증(차단 0·중요 0·경미 1) N1 보완: 새 `parse_player_season`은 정수만 저장하므로 도달하지 않는 `club_appearances_unknown` 분기·사유 설명·합성 테스트를 삭제하고 `MoveEvidence.prior`·`parse_player_season`·`save_player_season`의 `int | None`을 `int`로 정리(모델 `player_club_seasons.appearances` 열은 nullable 그대로 — 마이그레이션 없음, 남은 NULL 행은 쓸 수 없는 확인으로 보고 `check_pending`). 무효 파생 캐시 `player_club_seasons`(445025·2024·구단 9587·NULL) 1행 삭제, 445025/2024 확인 상태(checked_at NULL·failed_at)는 유지 — 계속 `check_pending`. 8팀×2시즌 사유 played_here 425·not_played 435·played_before 31·club_unknown 1 그대로, 외부 호출 0회. 이 팀 출전 NULL에서 같은 줄 득점·도움·평점이 모두 NULL이면 기록 없음=0, 하나라도 제공(0 포함)되면 played_here. 원본 null 패턴과 바이에른 325975(2024 도움 2·평점 7.287)가 근거. 2024·2025 저장 줄도 응답 때 재판정하여 열 추가·팀 기록 재수집 없음. 이전 팀 캐시는 원본 필드가 없어 NULL 선수·시즌 273건 재확인(수동 273회, sync_runs 423: 272성공·1실패; 서버 자동 재시도 run 426 1회 추가, 총 274회). 445025/2024는 식별 정보 없는 출전 근거라 완료 표시를 해제하고 실패·check_pending 유지. 값 있는 NULL은 최소 출전 근거 1로 저장하며 실제 출전 수·화면 합계가 아니다. appearances_unknown·미사용 상태 필드 삭제. 수집 미완료 records_incomplete·이전 팀 ID 없음 club_unknown·임대 복귀 본팀 기준 유지. 8팀×2시즌 표시 400→359줄·접힘 258→299줄·본팀 출전 근거 없이 표시 73→32줄. 이동 사유 played_here 425·not_played 435·played_before 31·club_unknown 1. 주요 선수·예외 선수 모두 표시. 전체 96팀: played_here 5,646·not_played 4,337·played_before 314·club_unknown 25·check_pending 1.  묶음은 모든 이동을 보존, 하나라도 표시면 묶음 전체 표시. 명단·상대 리그·나이·유스 이름으로 판정하지 않음. 선수단 합계 NULL 표시는 그대로, 이 규칙은 이적 분류 전용. **2026-11-25 사용자 결정으로 판정 변경:** 메인은 이 팀의 리그·UEFA·클럽 월드컵 공식 출전 1경기 이상(근거 시즌: 이전·당·다음)인 선수의 이동만, 그 밖은 모두 '기타 이동'(기록 미수집 시즌만 메인 유지). 국내 컵·슈퍼컵 출전은 근거로 세지 않고, 새 영입의 이전 팀 출전 확인(`played_before`)·임대 복귀 특례·근거 부족 사유(`check_pending`·`club_unknown`)는 없앴다 — 기획 문서 최신본 TEAM-006 규칙 6·6-2에 반영 완료. | TEAM-006 해석 개정은 §3.1 후속 요청 |
| D-08-7 | 선수 표 기록 범위: '이번 시즌 선수 기록'(PRD) — 국내 컵·UEFA 포함 여부 미정 | **2026-11-18 수정:** 5대 리그 + UEFA(챔피언스리그·유로파리그·컨퍼런스리그) 8개 대회의 이번 시즌 이 팀 기록 합계(`team_player_stats`, §6.5). 국내 컵·클럽 월드컵·친선·슈퍼컵은 넣지 않는다. 그 밖의 대회 포함 여부는 전체 검수 때 결정. 평점은 대회별로만 보여 주고 합계 평점은 만들지 않는다(행별 '대회별 기록' 팝업, Figma 469:6642 — 구현은 공통 `Dialog` 가운데 카드). 값이 빠진 줄이 있으면 그 합계는 '—', 이번 시즌 경기가 끝난 지원 대회의 줄이 없으면 '부분 집계' 표시와 빠진 대회 안내. 국적은 API 영문 국가명 그대로(D-08-1) + 국기(없으면 글자만, 국적 없으면 '—'). Figma와 다른 점: 모바일 머리글의 관심 팀 버튼이 공통 `FavoriteToggle` 문구('관심 팀 등록')라 Figma('관심 팀')보다 길어 팀 이름이 두 줄이 될 수 있음 | 그 밖의 대회 포함은 전체 검수 때 결정 |
| D-08-8 | Figma 상태 묶음(57:836)에 없는 상태: 저장소 차단, 감독·경기장·순위의 미수집, 영역별 갱신 실패 | 저장소 차단 — 관심 팀 버튼 아래 주황 '이 브라우저에서는 관심 팀을 저장할 수 없습니다. 팀 정보는 계속 볼 수 있습니다.'(07 안내와 같은 형식). 미제공 '미제공', 미수집 '확인하지 못했습니다'. 영역별 갱신 실패는 마지막 확인 데이터 + '다시 시도'(2026-11-18 수정 — 조회 실패도 '다시 시도', 확인된 결과가 비어 있어도 실패 안내 + 빈 결과 문구 + '다시 시도' — 팀 뉴스·선수단, Codex 1차 지적 9). 소속 미확인(57:836)은 Figma대로 '다시 확인'. 허용되지 않은 팀 '팀 상세를 제공하지 않는 팀입니다'·없는 팀 '팀을 찾을 수 없습니다' + '팀 탐색으로 이동' | 문구·디자인 |
| D-08-9 | '경기 전체 보기' 범위(Codex 1차 지적 4): TEAM-003 규칙 2 '전체 보기에서 이번 시즌 경기 전체' ↔ 08 작업 지시·유저 플로우 UF-09 진입점 '팀 상세 경기 영역 → 지난 경기'(`/results?team=<id>`, 종료 경기만 — 맨시티 기준 종료 15·예정 34경기 중 15경기) | **사용자 결정(2026-11-07): A 현행 유지.** `/results?team=<id>`(선택 시즌 전체 종료 경기) 연결과 Figma 버튼 문구 '경기 전체 보기'를 그대로 둔다(코드 변경 없음). 예정 경기는 팀 상세 경기 영역의 '예정 경기'(최대 3개)와 메인 팀 보기(공통 경기일 기간)가 맡는다 | **반영 완료(2026-11-07, Codex):** 기능 명세서 v1.7 TEAM-003(규칙 2·출력·완료 조건 — 지난 경기 화면 연결, 팀 조건 적용·시즌 변경 시 유지), PRD v1.7 16장 팀 상세 정보, 유저 플로우 v1.6 UF-09·UF-11. 이전 버전은 보존 |
| D-08-10 | 이적료 원화 표기(2026-11-18 수정안 TEAM-006, Figma 471:6856 '약 180억 원'·'€12m') ↔ API-Football 이적료 사실상 미제공 | **사용자 결정(2026-11-18): 구현 제외. 후속 사용자 요청으로 최신 기획 문서(PRD v1.13·기능 명세서 v1.13·유저 플로우 v1.12)와 전달문에도 보류를 반영했다. Figma·와이어프레임에 남은 금액 예시는 현재 구현 기준에서 제외한다.** 이적 오른쪽 값은 유형(완전 이적·임대·임대 복귀·자유계약 등)만 표시하고, 금액 파싱·환율 조회·원화 환산 코드와 DB 열은 만들지 않는다(작업 원칙 5). 근거(00 실측 2026-11-18, `/transfers?team=` 연도별 금액 제공 건수/전체): 맨시티 2023 8/40·2024 8/40·**2025 1/90·2026 0/93**, 레알 마드리드 2024 4/23·**2025 0/51·2026 1/38**, 첼시 2024 17/66·**2025 1/111·2026 1/89** — 2025년부터 금액이 사실상 오지 않는다. 저장된 이적 약 1.17만 줄 중 금액 줄(`type_raw` '€ 55M' 형식, 모두 €)은 8줄. 유료 API·수동 입력·기사·Transfermarkt 추출은 쓰지 않는다(수정안 원칙). **대안 출처가 생기면 적용할 기준:** 금액+통화가 있는 거래만, 이적일 환율로 원화 환산(휴일은 직전 영업일), 원 금액·통화·환율·환율 날짜·출처 저장, 금액 없으면 유형만. 무료 환율 후보: Frankfurter(`https://api.frankfurter.dev/v1/{date}?base=EUR&symbols=KRW` — ECB 기준환율, 키 없음, KRW·과거 날짜 지원, 휴일은 직전 영업일 자동: 2026-08-16(일) 요청 → 08-14 값 확인) | 이적료 대안 출처 확보 시 재검토 |

06 개선(2026-11-17) 중 기준끼리 어긋났거나 Figma에 없는 부분은 아래처럼 처리했다. Codex 검토와 사용자 확인을 요청한다.

| ID | 항목 | 06 개선 처리 | 확인 요청 |
| --- | --- | --- | --- |
| D-06b-1 | 선수 순위 탭·버튼 문구(당시 Figma 영어 표기) | **사용자 결정(2026-11-17): 대회명만 영문, 나머지는 한국어 — Figma도 수정됨.** 득점·도움·경고·퇴장·선방, '더 보기 · N명', 안내 문구는 Figma대로 '리그별 제공 상위 20명' | 해결 |
| D-06b-2 | '○○전 승자'·'상대 미정': 저장된 경기(공급사)는 두 팀이 정해진 대진만 주므로 2025-26·2026-27 실제 데이터에 해당 상태 없음 | 단계에서 대진이 하나만 빠진 경우만 직전 라운드 저장 경기로 계산(결승은 4강 두 대진). UEFA 추첨으로만 정해지는 미래 경로는 추정하지 않고 '예정 · 대진 미정' | **사용자 결정(2026-11-17): 미래 경로는 추정하지 않고 가능한 범위에서 대진표 작성** — 해결 |
| D-06b-3 | UEFA 리그 페이즈 표 열: Figma `61:1653`은 순위·팀·승점·최근 5경기만 | Figma대로 경기·승·무·패·득실 열 없음(5대 리그 표는 기존 열 유지) | — |
| D-06b-4 | UEFA 팀 대부분이 5대 리그 밖이라 '팀 상세 미제공'이 표에 많이 보임 | 기획(LEAG-002 규칙 3)대로 진출 구간과 별개로 표시 | 표시 빈도 |
| D-06b-5 | UEFA 최근 5경기 | **사용자 결정(2026-11-17):** 리그 페이즈 경기만, 진행한 경기가 5개 미만이면 진행한 경기만 표시. 플레이오프부터는 토너먼트라 최근 5경기 제외(대진 카드에 없음, Figma와 같음). 2026-27 챔스·유로파 4개·컨퍼런스 3개, 예선·토너먼트 경기 포함 0 확인 | 해결 |

### 10.4 공개 전 필수 확인(기존 검증 문서 유지)

V-04 실시간 경기 검증, V-09 네이버 뉴스 선별·재분류·중복 정리·수익화 허용 확인, V-10 엠블럼·선수 사진 권리와 API-Football 데이터 제3자 권리, V-16 프랑스 컵 2026-27 재조회, 운영 호출량 재산정(V-08).

### 10.5 배포 시 확인 목록(00, 2026-11-21 — Claude·Codex 공통)

**운영 DB(사용자 결정 2026-11-21):** 공개 운영은 지금의 개발 DB(`kicktab-dev`)를 그대로 쓴다(C-07은 이 결정으로 닫는다). 로컬 환경은 큰 수정·긴급 확인 같은 특수한 경우에만 실행한다. 로컬을 실행할 때는 `backend/.env`의 `SCHEDULER_ENABLED`·`NEWS_SCHEDULER_ENABLED`를 `false`로 두고, 수집 작업은 배포 서버 한 대만 돌린다. API-Football 하루 사용량은 프로세스마다 메모리에서 따로 세므로(`DailyBudget`) 두 서버가 같은 DB로 수집하면 공급사 한도(하루 7,500회)를 넘길 수 있다. 같은 작업의 동시 실행은 DB 잠금(`pg_try_advisory_lock`)이 막지만 사용량 합산은 막지 않는다. 공유 DB에서 `alembic downgrade`·테스트 데이터 직접 삽입 금지는 그대로다(DB 테스트는 롤백).

| 구분 | 확인할 것 | 근거 |
| --- | --- | --- |
| 월요일 00:00 | TOP 5 자동 선정(00:00~00:12)은 서버가 켜져 있어야 돈다. 놓치면 그 주는 지연 안내 + 수동 복구(`uv run python -m app.sync top5`)다. 배포·점검·재시작을 월요일 00:00 전후에 잡지 않는다 | §6.5 TOP 5 |
| 서버 수 | 수집 스케줄러는 배포 서버 1대만(`SCHEDULER_ENABLED=true`), 로컬은 `false`. 배포 플랫폼이 인스턴스를 늘리면 나머지는 `false` | C-03, 위 운영 DB |
| 서버 재시작 | 재시작하면 성공 기록이 없는 작업이 밀린 작업으로 바로 실행된다. 배포 직후 수동 수집을 겹쳐 돌리지 않는다(11/20 분당 제한 오류 사례) | §6.5 |
| DB 연결 | 배포 환경에 IPv6가 없으면 Supabase 세션 풀러 연결 문자열로 바꾼다. 운영 DB 마이그레이션 head가 배포 코드와 같은지 `alembic current`로 확인(02·09 마이그레이션 포함) | C-04 |
| 같은 출처·쿠키 | Next.js `rewrites`로 프런트·백엔드를 같은 출처로 연결(`BACKEND_ORIGIN`). `APP_ENV`를 운영 값으로 두어 인증 쿠키 `Secure`가 켜지는지 확인 | C-02, §6.2 |
| Origin·CORS | `CORS_ORIGINS`에 운영 도메인(https)만. CSRF Origin 확인 허용 목록을 겸한다 | §6.2, §6.7 |
| 실제 IP | 앞단 프록시가 `X-Forwarded-For`를 실제 클라이언트 IP로 덮어쓰고, `TRUSTED_PROXIES`를 그 경로에 맞춘다. 안 맞추면 의견·인증번호 발송 요청 제한을 우회할 수 있다(인증 메일 반복 발송 → Gmail 발송 정지 위험) | C-08, P-10 |
| 비밀값 | 운영 서버 `.env`: `AUTH_JWT_SECRET`은 로컬과 다른 값, `SMTP_*`, API·DB·웹후크 키. 값은 채팅·문서·로그에 남기지 않는다 | §6.7, U-04·U-05 |
| 메일 | Gmail SMTP 하루 약 500통 한도·스팸함 분류 가능성. 실제 주소로 가입 메일 1회 수신 확인 | P-01 |
| 이미지·뉴스 | V-09·V-10 결과에 따라 사용자가 정한 방식으로 배포(`IMAGE_RIGHTS_ENFORCED`·뉴스 노출 방식). 정해지기 전에는 배포하지 않는다 | V-09·V-10 |
| 약관·운영자 | **약관·처리방침 공개(02 작성, 2026-11-22 기준 남은 값은 `[배포 시 확정]`만)** — 배포 준비 때 이 순서로 한다: ① 시행일 결정(서비스 공개일) → 처리방침 제13조·약관 부칙의 시행일과 변경 이력, 문서 버전(예: `2026-12-01`) 기입 ② 배포 호스팅 업체·리전 → 처리방침 제6조 표·`docs/legal/personal-data-inventory.md` 4장 기입(접속 로그 보관 기간도 확인) ③ 공개 전 법률 검토(권장) ④ 문서 페이지 `app/terms`·`app/privacy`·`app/privacy/consent` 작성 후 `src/features/legal/documents.ts`의 `published: true`(가입 '보기'·푸터 링크가 같은 자리에서 열림) ⑤ 백엔드 `TERMS_VERSION`을 ①의 버전으로 설정(이후 가입분부터 `terms_agreements`에 그 버전 기록) ⑥ 배포 환경 프런트 `SITE_OPERATOR_NAME=운영자 신동주`·`SITE_OPERATOR_EMAIL=kicktab2026@gmail.com` 설정(주소 미표시). 확정된 값: 운영자 신동주·문의 kicktab2026@gmail.com, Supabase 서울(ap-northeast-2), 보관 기간(인증·로그인 기록 30일, 의견·문의 1년 — 정리 작업 `retention`), 게시물·이용 제한 기준(약관 제8·9조, 평가 제한 기능·운영 명령 `app.moderation`). 2차 광고 배너 때 다시 볼 항목은 `docs/legal/personal-data-inventory.md` 5장 | P-12 |
| 배포 후 첫날 | `sync_runs`에 실패·'running' 잔류가 없는지, 하루 API 호출 수가 §6.5 수집 표의 예상 안인지, 메인·경기 상세·순위·팀 상세가 열리는지 | §6.5 |

## 11. Git 규칙

원격 저장소: `https://github.com/dongjuSH/kick-tab.git`(`origin`). 저장소 루트는 `kick-tab/apps/`이며, 상위 `kick-tab/`의 기획 문서·API 검증 자료·와이어프레임은 올리지 않는다.

| 브랜치 | 용도 |
| --- | --- |
| `main` | 완성본만 올린다. 모든 기능 완료·전체 최종 검수·Codex 교차 검증을 마친 뒤 00 채팅이 `dev`를 병합한다 |
| `dev` | 통합 브랜치. 완료된 기능 브랜치를 하나씩 병합한다 |
| `feat/<번호>-<영문 이름>` | 기능 채팅 작업 브랜치. 작업 시작 시 최신 `dev`에서 만든다 |

기능 브랜치 이름: `feat/01-header-footer`, `feat/02-auth`, `feat/03-schedule`, `feat/04-match-detail`, `feat/05-results`, `feat/06-standings`, `feat/07-team-browse`, `feat/08-team-detail`, `feat/09-mypage`.

**Git 작업은 사용자가 요청할 때만 한다(사용자 결정 2026-11-01).** 브랜치 생성·커밋·병합·push 등 저장소를 바꾸는 Git 명령은 요청 없이 실행하지 않는다(00 채팅 포함). 작업은 현재 체크아웃된 브랜치의 작업 트리에서 하고, 상태 확인용 `git status`·`git diff`·`git log`만 쓴다. 강제 push·이력 재작성은 하지 않는다. GitHub 인증이 필요하면 사용자가 직접 인증한다.

요청을 받았을 때의 기본 구조: 기능마다 `feat/<번호>-<영문 이름>` 브랜치, 마무리 시 커밋 한 번, `dev`에 한 기능씩 병합, 전체 완료 후 `dev`를 `main`에 병합. 커밋 전에는 `.env*` 파일(`.env.example` 포함)·비밀 값·생성물·쓰지 않는 파일이 없는지 확인한다.

**Git에 올리지 않는 것:** 모든 `.env*` 파일(`.env.example` 포함), 가상환경·Python 런타임, `node_modules`·`.next`, 캐시, 저장소 밖 로컬 자료(`../docs`·`../api-test`·`../wireframe`), 쓰지 않는 기본 생성 파일. 새 파일 유형이 생기면 루트 `.gitignore`를 먼저 갱신한다.
