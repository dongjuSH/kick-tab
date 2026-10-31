# KickTab 개발 가이드

최종 갱신: 2026-10-31 (토), 한국 시간(KST) — 00 채팅 첫 설계 반영

Claude의 전체 조율 채팅(00)과 기능별 구현 채팅(01~09)이 공유하는 최신 작업 기준이다. 각 채팅은 시작 전에 이 문서와 관련 코드를 읽는다. 프로젝트 파악·기술 설계·구현은 Claude, 기획 문서·디자인 반영·교차 검증·실제 배포는 Codex에서 진행한다.

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

주요 프레임 ID: 메인 `49:57`/`49:570`, 경기 상세 `52:151`/`52:404`(탭·평가 작성·라인업 발표 전·행정 종료 상태 별도), 팀 탐색 `52:624`/`52:949`, 팀 상세 `52:1254`/`52:1866`(모바일 선수·기록·뉴스 탭 `58:356`·`58:738`·`58:924`), 로그인 `52:2116`/`52:2265`, 회원가입 `52:2387`/`52:2545`(인증번호·자동 로그인 상태 별도), 마이페이지 `52:2674`/`52:2912`, 지난 경기 `53:593`/`53:995`, 리그 순위 `53:1353`/`53:2047`(앞이 데스크톱, 뒤가 모바일). 공통 UI 프레임은 `62:1427`~`62:1939`, `81:3209`.

별도의 디자인 전달 문서는 없다. Figma의 컬러 가이드·설계 반영 기준·개발 전달 기준 프레임과 이 가이드 §6.6이 디자인 구현 기준이다.

## 2. 채팅 구성과 담당 범위 — 전체 10개

각 기능 채팅은 담당 기능의 프런트엔드·백엔드·DB 마이그레이션·예외 처리·자체 검수까지 함께 맡는다. 같은 작업 폴더를 쓰므로 **코드 수정은 아래 순서대로 한 채팅씩 진행한다.** 기능 ID는 기능 명세서 기준이다.

| 순서 | 채팅 | 담당 기능 ID | 담당 범위(공통 기능 포함) |
| --- | --- | --- | --- |
| — | 00 전체 설계·조율·검수 | — | 공통 설계, 범위·순서 결정, 가이드 관리, 기능별 완료 확인, 전체 최종 검수, 사용자 요청 시 Git 원격 업로드 |
| 1 | 01 헤더·푸터 + **공통 기반** | COM-003·004, FEED-001~003, TOP-003(표시) | §6의 프런트·백엔드 공통 기반 전체, 디자인 토큰, 공통 UI 컴포넌트, 헤더(인증 영역은 자리만)·푸터·TOP 5 띠(조회·빈 상태)·의견 보내기 |
| 2 | 02 로그인·회원가입 | AUTH-001~005, COM-001·002·005, FAV-001~003, MY-004의 계정 API | 인증·세션·이메일 인증번호·비밀번호 찾기/변경·탈퇴 API, 헤더 인증 영역 연결, 로그인 유도 다이얼로그와 복귀(returnTo/intent), 작성 중 입력 보존 유틸, **관심 팀 저장소(비회원 localStorage·회원 DB)와 `FavoriteToggle`** |
| 3 | 03 경기 일정(메인) | SCH-001~006, LIVE-001~004, FAV-004, CMP-001~004, NEWS-001~004, BOOK-001·003, OPS-001~004(해당분) | 대회·시즌·팀 기준 데이터와 **팀 상세 허용 집합**, 별칭 사전, 경기 수집·상태 변환·실시간 갱신, `MatchCard`·`CompetitionFilter`·`TeamSearch`, 메인 일정·관심 팀 일정, **뉴스 수집·분류와 `NewsCard`·북마크 버튼·북마크 API** |
| 4 | 04 경기 상세 | MAT-001~005, REV-001~004, TOP-001·002 | 경기 상세(상태별 영역·이벤트·기록·상대 전적·최근 흐름), 회원 평가·후기·반응, TOP 5 선정 작업(정책 확정분만, §10) |
| 5 | 05 지난 경기 | HIST-001~003 | 지난 경기 조회·필터·페이지 분할, `SeasonSelect`, 2025 시즌 과거 데이터 적재 작업 |
| 6 | 06 리그 순위 | LEAG-001·002·004 | 순위 수집, 시즌별 전체 순위, 선수 순위(득점·도움·카드·선방 자체 집계), 메인 간소 순위 영역, 리그 전체 선수 시즌 기록 수집 |
| 7 | 07 팀 탐색 | LEAG-003 | 현재 시즌 5대 리그 팀 목록·리그 필터·팀명 검색·관심 팀 등록/해제 |
| 8 | 08 팀 상세 | TEAM-001~006 | 팀 기본 정보·경기·선수 표·시즌 기록·이적(배치 포함)·팀 뉴스(03 뉴스 재사용), 모바일 탭 |
| 9 | 09 마이페이지 | MY-001~004, BOOK-002 | 관심 팀 관리·내 평가·저장 뉴스·계정(02 API 사용) 화면 통합 |

**공통 기능 담당과 재사용 방식**

| 공통 기능 | 만드는 채팅 | 재사용 채팅 | 재사용 방식 |
| --- | --- | --- | --- |
| 공통 UI(버튼·뱃지·다이얼로그·하단 시트·툴팁·탭·드롭다운·페이지네이션·스켈레톤·`DataState`) | 01 | 전체 | `src/components/ui/` |
| 엠블럼·선수 사진·공통 대체 이미지(`TeamCrest`, `PlayerPhoto`) | 01 | 전체 | 이미지 URL이 `null`이면 대체 이미지 |
| API 클라이언트·응답 타입·오류 처리 | 01 | 전체 | `src/lib/api/`, OpenAPI 생성 타입 |
| TOP 5 띠 | 01(표시) / 04(선정 작업) | 전 페이지 | `GET /api/v1/top-matches/current` |
| 의견 보내기 | 01 | 전 페이지 | 데스크톱 푸터·모바일 하단 고정 영역의 진입 버튼 + 모달(모바일 하단 시트), `POST /api/v1/feedback` |
| 인증 상태·로그인 유도·복귀 | 02 | 04·03·08·09 | `useAuth()`, `requireLogin({ intent })` |
| 관심 팀 | 02(저장소·토글) / 03(일정 선별) | 03·07·08·09 | `useFavorites()`, `<FavoriteToggle teamId>` |
| 팀 링크 허용 여부 | 03 | 04·05·06·07·08 | 모든 팀 참조 응답의 `detailAvailable: true \| false \| null` |
| 경기 카드·상태 뱃지 | 03 | 04·05·08·TOP 5 | `<MatchCard>`, `<MatchStatusBadge>` |
| 대회 필터(그룹 버튼 + 체크박스 다중 선택) | 03 | 05 | `<CompetitionFilter>` |
| 팀 검색 자동완성·별칭 사전 | 03 | 05·07·뉴스 분류 | `GET /api/v1/teams/search`, `team_aliases` |
| 뉴스 카드·북마크 버튼 | 03 | 08·09 | `<NewsCard>`, `<NewsList query>` |
| 시즌 드롭다운 | 05 | 06 | `<SeasonSelect>` + `GET /api/v1/competitions` 시즌 정보 |
| 리그 선수 시즌 기록 | 06 | 08 | `player_season_stats` |

담당이 아닌 채팅은 같은 기능을 중복 구현하지 않는다. 공통 컴포넌트가 부족하면 담당 채팅의 구조를 확장하고 이 표를 갱신한다. 페이지 목록에서 빠졌다는 이유로 명세의 기능을 누락하지 않는다.

## 3. 진행 상태와 다음 작업

| 채팅 | 상태 | 비고 |
| --- | --- | --- |
| 00 | 첫 설계·01 착수 전 검수 완료(2026-10-31) | 이 문서 §2·§6~§11 확정. Codex 검토 요청 사항은 §10 |
| 01 | **다음 작업** | 선행 조건 충족: 원격 `main`·`dev` 준비(§11), Supabase Data API 꺼짐 확인(§9 U-03), Figma 커넥터 접근(§1) |
| 02~09 | 대기 | 앞 순서 채팅의 완료(교차 검증 포함) 후 진행 |

기능 채팅 완료 시 이 표의 상태, 새로 생긴 공통 인터페이스, 남은 확인 사항을 갱신한다.

## 4. 기능 구현·검수·설계 변경 흐름

기능 작업은 **가이드·관련 코드 확인 → 범위와 작업 구상 정리 → 프런트엔드·백엔드 구현 → Claude 자체 검수 → Codex 교차 검증 → Claude 보완 → 필요한 범위 재검증** 순서로 진행한다. Claude 자체 검수만으로 교차 검증 완료를 표시하지 않는다.

기존 인증·DB·외부 API·공통 UI를 재사용하고 공유 계약(API 응답, DB 테이블, 공통 컴포넌트 props)을 바꾸면 영향을 받는 기능과 이 가이드도 반영한다. 단순한 내부 구현 선택은 기존 구조에 맞춰 진행하되, 사용자 동작·화면·권한·데이터 정책이 기존 설계와 달라져야 한다면 변경 이유·대안·영향·수정할 기획/디자인 항목을 정리한다. Codex 검토와 필요한 사용자 결정 후 기획 문서·디자인·가이드에 반영하고 변경된 기준으로 구현한다. 미확정 정책(§10)은 임의로 정하지 않고 "제공 보류" 상태로 구현한다.

**기능 완료 조건(공통)**

1. 담당 기능 ID의 정상 처리·예외 처리·완료 및 검증 조건(기능 명세서)과 관련 통합 인수 기준(기능 명세서 6.2)을 충족한다.
2. 로딩·빈 결과·일부 미제공·조회 실패·권한 거부 상태를 구분해 보여준다. 누락값은 `null`로 전달하고 화면에서 '미제공' 또는 '—'로 표시한다.
3. 데스크톱·모바일(375px) 배치를 Figma 기준으로 확인한다. 접근하지 못한 프레임은 미확인으로 남긴다.
4. 백엔드 `uv run ruff check .`, `uv run python -m pytest`, 프런트엔드 `npm run lint`, `npm run build`가 통과한다. 새 API·서비스 로직에는 테스트를 추가한다.
5. 새 테이블은 Alembic 마이그레이션으로만 만들고 `upgrade`·`downgrade`를 개발 DB에서 확인한다.
6. 실제 외부 API 호출은 필요한 최소 횟수만 실행하고 횟수를 완료 응답에 적는다.
7. 완료 응답에 구현 범위·관련 경로·검사 결과·실제 API/DB 연동 여부·미확인 사항을 남기고, 이 가이드 §3과 바뀐 공통 인터페이스를 갱신한다.

모든 기능을 마치면 페이지 간 이동, 인증 후 복귀, 관심 팀·후기·북마크의 화면 간 반영, 시즌 전환, 외부 API 실패 등 연결 흐름을 전체 검수한다. **Claude 전체 최종 검수 → Codex 교차 검증 → Claude 보완 → 최종 재검증** 후 Codex의 배포 작업으로 넘긴다.

## 5. 문서 운영 규칙

**`guide.md`는 작업하면서 계속 최신화한다.** 공통 결정, 담당 범위, 주요 인터페이스·재사용 위치, 현재 진행·검수 상태, 미확정 사항과 다음 작업을 현재 기준으로 유지한다. 다른 채팅의 대화를 자동으로 공유받았다고 가정하지 않는다. 다른 문서를 언급할 때는 버전 없이 문서 이름만 쓴다(예: "PRD", "기능 명세서").

**`daily-work-log.md`와 `file-feature-map.md`는 사용자가 해당 문서의 갱신을 요청할 때만 수정한다.** 구현·검수 완료나 가이드 변경을 이유로 자동 갱신하지 않는다. 두 문서는 최신 코드와 차이가 날 수 있으므로 현재 구현은 소스로 확인한다.

요청받은 경우 일별 기록에는 실제 날짜·요일(KST), 담당 채팅, 변경 파일·함수/영역·이유, 검증 결과를 누적한다. 파일별 기능 목록에는 실제 존재하는 파일의 현재 역할·연결·구현 상태만 적고, 생성물·의존성 내부 파일과 예정 파일은 제외한다. 가이드에는 전체 변경 이력이나 파일 목록을 중복 누적하지 않는다. **비밀 값(비밀번호·API 키·토큰·DB 접속 문자열·인증번호)은 어느 문서·로그·응답에도 기록하지 않는다.**

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
| 갱신 토큰 | 무작위 256비트 값, DB에는 SHA-256 해시만 저장. 만료 14일, 사용할 때마다 교체(rotation), 재사용 감지 시 같은 계열 전체 폐기. `kt_refresh` 쿠키 `Path=/api/v1/auth` |
| 자동 갱신 | 클라이언트 요청이 `401 AUTH_EXPIRED`를 받으면 `POST /api/v1/auth/refresh`를 한 번만 시도하고 원 요청을 재시도한다. 동시에 여러 요청이 실패해도 갱신은 1회로 합친다. 갱신 실패 시 비회원 상태로 전환하고 작성 중 후기를 `sessionStorage`에 보존한 뒤 로그인 화면으로 보낸다(AUTH-003) |
| CSRF | 쿠키 인증이므로 변경 요청(POST/PUT/PATCH/DELETE)은 `X-KickTab-Client: web` 헤더를 요구하고 `Origin`이 허용 목록과 다르면 거부한다 |
| 인증번호 | `email_verifications`에 목적(`signup`·`password_reset`)·코드 해시·만료·실패 횟수·마지막 발송 시각 저장. 확인 성공 시 30분 유효한 일회용 `verificationToken`을 발급해 가입·비밀번호 재설정 요청에 사용한다. 발송·확인 API에는 이메일·IP 기준 요청 제한을 둔다 |
| 메일 발송 | `EmailSender` 인터페이스. 로컬(`APP_ENV=local`)은 콘솔 출력 구현, 운영 공급자는 미정(§10 P-01). 인증번호를 로그에 남기는 것은 로컬 콘솔 구현에서만 허용 |
| 가입 직후 로그인 | 가입 API가 계정 생성과 쿠키 발급을 한 트랜잭션 흐름으로 처리하고, 프런트엔드는 `GET /api/v1/auth/me`로 세션 성립을 확인한 뒤에만 회원 상태로 표시한다(계정 생성 성공과 인증 성립 구분) |
| 로그아웃 | 서버에서 갱신 토큰 폐기 + 쿠키 삭제 후 `/auth/me`로 비회원 확인. 공개 페이지는 유지, 회원 전용 페이지는 메인 이동. localStorage 관심 팀 복원(COM-005) |
| 로그인 복귀 | `/login?returnTo=<내부 경로>&intent=<review:경기ID \| bookmark:기사ID>`. `returnTo`는 `/`로 시작하는 내부 경로만 허용(오픈 리다이렉트 방지). 평가 intent는 평가 입력 UI를 열고, 북마크 intent는 카드 위치로만 복귀하며 자동 저장하지 않는다 |
| 소셜 로그인 | 1단계는 이메일 가입만 구현. `auth_identities` 테이블로 카카오·구글을 나중에 추가할 수 있게 한다. 제공 여부·같은 이메일 연결 방식은 §10 P-02 |

### 6.3 DB·마이그레이션

- **도구:** SQLAlchemy 2.x(동기, psycopg 3 드라이버) + Alembic. 01이 `app/db/`(엔진·세션·`Base`)와 `backend/migrations/`를 만든다. 연결 문자열은 `.env`의 `DATABASE_URL`을 코드에서 `postgresql+psycopg://`로 바꿔 쓰고, 기존과 같이 `sslmode=verify-full`·`certs/supabase-ca.crt`를 `connect_args`로 전달한다. 기존 `app/database.py`·`check_database`는 연결 점검용으로 유지한다.
- **규칙:** 스키마 변경은 마이그레이션 파일로만 한다(대시보드 수동 변경 금지). 한 기능 채팅의 마이그레이션은 기능 단위로 나누고 `downgrade`를 작성한다. 시간은 `timestamptz`(UTC 저장), 경기 묶음용 KST 날짜는 별도 `date` 컬럼으로 저장한다.
- **Supabase 공개 API 차단:** Supabase는 `public` 스키마를 Data API(PostgREST)로 노출할 수 있다. **모든 테이블 생성 마이그레이션에 `ALTER TABLE ... ENABLE ROW LEVEL SECURITY`를 포함하고 정책은 만들지 않는다.** 백엔드는 테이블 소유 역할로 접속하므로 영향을 받지 않는다. 사용자는 Supabase 대시보드에서 Data API 비활성화를 함께 검토한다(§9).
- **ID:** 외부 데이터(대회·팀·선수·경기)는 API-Football ID를 기본 키로 그대로 쓴다. 서비스 데이터(회원·후기 등)는 UUID(`users`) 또는 `bigint identity`를 쓴다.
- **누락값:** API가 비운 값은 `NULL`로 저장하고 0으로 바꾸지 않는다. 원본 상태 코드·원본 블록은 함께 보관해 재해석할 수 있게 한다.

**초기 테이블 설계(소유 채팅이 마이그레이션 작성)**

| 영역 | 테이블(주요 컬럼) | 소유 |
| --- | --- | --- |
| 운영 | `sync_runs`(job, params, started_at, finished_at, status, api_requests, error_summary), `feedback`(user_id NULL 허용, type NULL 허용, body ≤1000, page_path, created_at) | 01 |
| 회원 | `users`(id uuid, email citext unique, nickname unique, password_hash NULL 허용, login_method, created_at), `auth_identities`, `refresh_tokens`(token_hash, family_id, expires_at, revoked_at), `email_verifications`, `terms_agreements`(user_id, terms_version, agreed_at), `favorite_teams`(user_id, team_id, created_at, PK(user_id, team_id)) | 02 |
| 기준 데이터 | `competitions`(id, group, type league/cup/uefa, name_ko, name_en, sort_order, active), `competition_seasons`(competition_id, season, label, is_current, availability), `teams`(id, name_en, name_ko, logo_url, country, venue…), `team_aliases`(team_id, alias, normalized, lang, ambiguous, for_search, for_news), `team_competition_seasons`(참가 기록), `image_assets`(대상, 원본 URL, 권리 근거, 크레딧, approved) | 03 |
| 경기 | `fixtures`(id, competition_id, season, round, kickoff_at, kickoff_date_kst, status, finish_type, status_short_raw, status_reason, elapsed, home/away_team_id, goals_home/away, score jsonb, venue, api_updated_at), `fixture_events`, `fixture_details`(fixture_id, statistics/lineups/players jsonb, fetched_at) | 03(목록·상태·이벤트) / 04(상세 블록·상대 전적) |
| 뉴스 | `news_articles`(id, url_hash unique, url, title, description, published_at, source_name, fetched_at, expires_at), `news_article_tags`(article_id, badge, team_id), `news_sources`(도메인→언론사명), `bookmarks`(user_id, article 식별 키, 제목·설명·출처·뱃지 스냅샷, created_at, unique(user_id, 식별 키)) | 03 |
| 경기 상세 | `head_to_head`(fixture_id, payload jsonb, last_meeting_fixture_id, fetched_at), `reviews`(id, user_id, fixture_id, rating 1~5, body ≤300 NULL 허용, created/updated_at, unique(user_id, fixture_id)), `review_reactions`(review_id, user_id, value ±1, PK), `weekly_top_matches`(week_start, rank, fixture_id, method, computed_at) | 04 |
| 순위 | `standings`(competition_id, season, team_id, rank, points, played, w/d/l, gf, ga, form, description, group), `player_rankings`(competition_id, season, type, rank, player_id, team_id, value), `players`, `player_season_stats`(player_id, team_id, competition_id, season, 주요 지표 컬럼 + 원본 jsonb) | 06 |
| 팀 상세 | `squad_members`(team_id, season, player_id, number, position), `team_season_stats`(team_id, competition_id, season, payload jsonb), `transfers`(player_id, date, team_in_id, team_out_id, type_raw, season, half, frozen) | 08 |

관심 팀 5개 제한·후기 1인 1건·반응 1인 1건은 DB 제약(unique)과 서비스 검증(트랜잭션 안에서 개수 확인)으로 함께 보장한다. 회원 탈퇴 시 연관 데이터 처리 방식은 §10 P-03 결정 전까지 탈퇴 API를 "구현하되 처리 범위는 결정 대기"로 둔다.

### 6.4 백엔드 API 형식

- 경로 접두사 `/api/v1`. 리소스 이름은 복수형 kebab-case. 상태 확인 `/health`는 유지한다.
- JSON 필드는 camelCase(Pydantic `alias_generator=to_camel`, `populate_by_name=True`). 시각은 ISO 8601 UTC(`2026-10-31T19:00:00Z`), 경기 묶음 날짜는 `kickoffDateKst: "2026-11-01"`처럼 별도 제공. 시간대 표기는 화면에 하지 않는다.
- **성공:** `{ "data": <객체|배열>, "meta": { ... } }`. 목록은 `meta.page`, `meta.size`, `meta.total`(페이지 방식) 또는 `meta.nextCursor`(뉴스 더 보기). 수집 데이터는 `meta.updatedAt`(마지막 수집 시각)을 넣는다.
- **오류:** `{ "error": { "code": "FAVORITE_LIMIT", "message": "관심 팀은 최대 5개까지 등록할 수 있습니다.", "details": { } } }`. 메시지는 화면에 그대로 써도 되는 한국어. 내부 예외·SQL·외부 응답 원문은 노출하지 않는다.

| HTTP | code | 용도 |
| --- | --- | --- |
| 400/422 | `VALIDATION_ERROR` | 입력 형식 오류(`details.fields`에 항목별 사유) |
| 401 | `AUTH_REQUIRED` / `AUTH_EXPIRED` / `INVALID_CREDENTIALS` | 미인증 / 접근 토큰 만료(갱신 시도 대상) / 로그인 실패 |
| 403 | `FORBIDDEN` | 소유권 없음, CSRF 헤더 누락 |
| 404 | `NOT_FOUND` / `TEAM_DETAIL_UNAVAILABLE` | 없는 식별자(다른 데이터로 대체하지 않음) / 현재 상세 미제공 팀 |
| 409 | `CONFLICT`, `EMAIL_TAKEN`, `NICKNAME_TAKEN`, `FAVORITE_LIMIT`, `REVIEW_EXISTS` | 중복·제한 |
| 410/422 | `VERIFICATION_EXPIRED` / `VERIFICATION_INVALID` / `VERIFICATION_LOCKED` | 인증번호 만료 / 불일치 / 5회 실패 |
| 429 | `RATE_LIMITED` | 요청 제한(`Retry-After` 헤더) |
| 503 | `UPSTREAM_UNAVAILABLE` / `MEMBERSHIP_UNKNOWN` | 수집 데이터 없음+외부 실패 / 팀 소속 확인 불가 |
| 500 | `INTERNAL_ERROR` | 그 밖의 오류 |

- **부분 제공 블록:** 경기 상세 기록처럼 항목별 제공 여부가 다른 데이터는 `{ "status": "available" | "not_provided" | "not_yet" | "unavailable", "data": ... }`로 감싼다. `not_yet`은 라인업 발표 전처럼 시점상 아직 없는 경우, `unavailable`은 조회 실패다.
- **경기 상태:** `status`는 `scheduled | live | finished | postponed | cancelled | abandoned | unknown`, 종료 세부는 `finishType: normal | aet | pen | awarded | walkover`.

| API-Football `status.short`(대소문자 무시) | `status` | 비고 |
| --- | --- | --- |
| `TBD`, `NS` | scheduled | `TBD`는 `timeConfirmed: false` |
| `1H`, `HT`, `2H`, `ET`, `BT`, `P`, `LIVE`, `SUSP`, `INT` | live | 잠시 멈춤도 진행 중(D-17) |
| `FT` / `AET` / `PEN` | finished | finishType normal / aet / pen. 승부차기 스코어는 `score.penalty`로 분리 |
| `AWD` / `WO` | finished | finishType awarded / walkover. 평가·TOP 5 제공 보류(§10 P-05) |
| `PST` | postponed | 같은 경기 ID로 새 일시 반영 |
| `CANC` | cancelled | 실제 데이터에 `Canc`·`CANC` 혼재 |
| `ABD` | abandoned | '경기 중단', 중단 시점 스코어, 평가·TOP 5 제외 |
| 그 밖 | unknown | '확인 필요' |

- **팀 참조 공통 형태(`TeamRef`):** `{ "id", "nameKo", "nameEn", "crestUrl": string | null, "detailAvailable": true | false | null }`. `null`은 소속 미확인(조회 중·실패)이며 강등으로 표시하지 않는다(D-15).
- **경기 요약 공통 형태(`MatchSummary`):** 경기 카드·TOP 5·팀 경기 목록이 같은 형태를 쓴다. `{ "id", "competition": { "id", "nameKo", "shortName" }, "kickoffAt", "kickoffDateKst", "timeConfirmed", "status", "finishType", "elapsed", "statusReason", "home": TeamRef, "away": TeamRef, "score": { "home", "away", "penaltyHome", "penaltyAway" } }`. 스코어·경과 시간이 없으면 `null`. 01이 스키마를 먼저 정의하고 03이 실제 데이터로 채운다. 필드를 바꾸면 이 줄을 갱신한다.
- **TOP 5 응답:** `GET /api/v1/top-matches/current` → `data: { "period": { "start": "YYYY-MM-DD", "end": "YYYY-MM-DD" } | null, "items": [ { "rank", "match": MatchSummary } ] }`. 01은 테이블 없이 항상 `period: null, items: []`를 돌려주는 서비스 함수로 계약만 만든다. 주간 경계의 시간대·귀속 시각(P-06)이 정해지기 전에는 `period`를 `null`로 두고 띠는 집계 기간 표기 없이 빈 상태를 보여준다. `weekly_top_matches` 테이블과 실제 선정은 04가 만든다.
- **프런트엔드 타입:** 백엔드 OpenAPI(`/openapi.json`)에서 `openapi-typescript`로 `src/lib/api/schema.d.ts`를 생성한다(`npm run gen:api`). 손으로 타입을 중복 작성하지 않는다.

**초기 엔드포인트 목록(담당 채팅이 세부를 확정하고 이 표를 갱신)**

| 구분 | 엔드포인트 | 담당 |
| --- | --- | --- |
| 공통 | `GET /api/v1/top-matches/current`, `POST /api/v1/feedback` | 01 |
| 인증 | `POST /auth/email-codes`, `POST /auth/email-codes/verify`, `POST /auth/signup`, `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout`, `POST /auth/password-reset`, `GET /auth/me` | 02 |
| 계정·관심 팀 | `PATCH /me/password`, `DELETE /me`, `GET /me/favorites`, `POST /me/favorites`, `DELETE /me/favorites/{teamId}` | 02 |
| 기준·일정 | `GET /competitions`, `GET /fixtures?date=&competitions=&team=`, `GET /fixtures/live?ids=`, `GET /teams/search?q=&scope=schedule\|season&season=` | 03 |
| 뉴스·북마크 | `GET /news?badge=&team=&cursor=`, `GET /me/bookmarks`, `POST /me/bookmarks`, `DELETE /me/bookmarks/{id}` | 03 |
| 경기 상세 | `GET /fixtures/{id}`, `GET /fixtures/{id}/detail`, `GET /fixtures/{id}/head-to-head`, `GET /fixtures/{id}/reviews?sort=popular\|latest`, `POST /fixtures/{id}/reviews`, `PATCH·DELETE /reviews/{id}`, `PUT·DELETE /reviews/{id}/reaction`, `GET /me/reviews` | 04 |
| 지난 경기 | `GET /results?season=&competitions=&team=&page=` | 05 |
| 순위 | `GET /standings?league=&season=`, `GET /standings/summary`, `GET /player-rankings?league=&season=&type=goals\|assists\|yellow\|red\|saves` | 06 |
| 팀 | `GET /teams?league=&q=&page=`(07), `GET /teams/{id}`, `/teams/{id}/fixtures`, `/teams/{id}/squad`, `/teams/{id}/season-stats?season=`, `/teams/{id}/transfers?season=` | 07·08 |

### 6.5 외부 데이터 수집·캐시

- **클라이언트:** `app/providers/api_football.py`(01이 골격, 03이 확장)와 `app/providers/naver_news.py`(03). 키는 `SecretStr`에서 요청 직전에만 꺼내고 헤더·URL·키를 로그에 남기지 않는다. `../api-test/tests/api_client.py`(로컬 전용)의 안전 장치(HTTP 200 + `errors` 실패 처리, 쿼터 헤더 기록, 요청 간격)를 참고한다.
- **호출 한도 보호:** 공용 속도 제한기(분당 250회 이하로 운영, Pro 한도 300회), 일일 예산 경계(기본 7,000회에서 신규 수집 중단), 타임아웃 10초, 5xx·네트워크 오류는 최대 2회 지수 백오프 재시도 후 중단. 무제한 자동 재시도·폴링 금지. 호출 수는 `sync_runs`에 기록한다.
- **쓰기 규칙:** 실패 응답으로 기존 정상 데이터를 덮어쓰거나 지우지 않는다. 정상 빈 응답과 오류를 구분해 기록한다(COM-004, CMP-004).
- **수집 작업:** `app/sync/<job>.py`의 멱등 함수 + CLI(`uv run python -m app.sync <job> [옵션]`). 자동 실행은 백엔드 프로세스 안의 APScheduler로 하되 `SCHEDULER_ENABLED=true`인 인스턴스 하나에서만 켠다. 같은 작업이 겹치지 않도록 PostgreSQL advisory lock을 쓴다. 배포 환경의 스케줄 방식은 Codex 배포 단계에서 바꿀 수 있게 작업 함수와 실행기를 분리한다.
- **요청 시 보충 조회:** 경기 상세·상대 전적처럼 사용자가 열었을 때 처음 필요한 데이터만 "DB 확인 → 없거나 만료면 외부 조회 1회 → 저장" 방식을 쓴다. 같은 키의 동시 요청은 하나로 합친다.

| 작업 | 초기 주기(실측 후 조정) | 담당 |
| --- | --- | --- |
| 대회·시즌·팀·허용 집합 | 매일 1회 + 수동 실행 | 03 |
| 현재 시즌 경기 목록(오늘−1일 ~ +15일) | 30분 | 03 |
| 실시간 경기 | 진행 중 또는 30분 내 시작 경기가 있을 때만 60초, `fixtures?live=all` 1회로 지원 대회 전체 처리 | 03 |
| 경기 상세 블록 | 종료 전환 시 1회 + 요청 시 보충, 진행 중은 실시간 주기에 맞춤 | 04 |
| 상대 전적 | 경기당 1회, 두 팀이 새로 맞붙은 뒤에만 갱신 | 04 |
| 순위 | 경기일 1시간, 그 외 하루 1회 | 06 |
| 선수 순위·선수 시즌 기록(선방 집계) | 하루 1회 | 06 |
| 선수단·팀 시즌 기록 | 하루 1회 | 08 |
| 이적 | 매일 00:00 KST, 시즌 종료 후 6/30까지 갱신 후 고정 | 08 |
| 뉴스 | 30분(검색어 수·한도 실측 후 확정) | 03 |
| TOP 5 | 4시간(정책 확정 후) | 04 |

- **2025 시즌 과거 데이터:** 05가 적재 작업을 만든다. `../api-test/results/raw/`의 2025 원본 응답을 우선 가져와 재호출을 줄이고, 빠진 항목만 API로 보충한다. 원본 파일은 로컬 전용이므로 운영 서버에서는 API 적재 경로를 쓴다.
- **실시간 화면 갱신:** 웹소켓 없이 클라이언트 폴링(진행 중 경기가 화면에 있을 때 30~60초)으로 한다. 화면에 마지막 갱신 시각을 표시한다. 실제 경기 시간 검증(V-04) 전에는 지연 시간을 보장한다고 안내하지 않는다.
- **이미지:** 백엔드가 `image_assets`에서 권리가 확인된 이미지 URL만 `crestUrl`·`photoUrl`로 내려준다. `IMAGE_RIGHTS_ENFORCED=false`(로컬 기본)일 때만 API 이미지 주소를 그대로 사용한다. 공개 배포 전 `true`로 바꾸고 권리를 확보한 자산만 노출한다(V-10).
- **뉴스 보관:** `news_articles.expires_at`과 정리 작업으로 보관 기간을 설정값(`NEWS_RETENTION_HOURS`)으로 바꿀 수 있게 한다. 북마크 스냅샷 항목·보관 기간도 바꿀 수 있게 설계한다. 실제 기간은 네이버 확인(V-09) 후 확정한다. 기사 본문 수집·AI 입력은 하지 않는다.

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

**폴더**

```
src/
  app/                      경로별 page.tsx·layout.tsx (전역 헤더·TOP 5·푸터·모바일 하단 고정 영역은 루트 layout)
  components/ui/            디자인 시스템 기본 컴포넌트 (01)
  components/common/        여러 페이지 공용 도메인 컴포넌트 (TeamCrest, MatchCard, NewsCard …)
  features/<기능>/          기능 전용 컴포넌트·훅 (auth, favorites, schedule, match, results, standings, teams, team-detail, mypage, feedback, top5)
  lib/api/                  fetch 래퍼, 오류 변환, 생성 타입, query key
  lib/auth/                 AuthProvider, useAuth, requireLogin
  lib/format/               KST 날짜·시각 포맷(Intl, timeZone 'Asia/Seoul'), 누락값 표시
```

- **상태 관리 경계:** ① 필터·시즌·탭·페이지 등 화면 상태는 URL 검색 파라미터(뒤로 가기·공유 가능, 초기화 규칙은 PRD 기준). ② 서버 데이터는 서버 컴포넌트 조회 또는 TanStack Query(클라이언트 조회·폴링·변경 후 무효화). ③ 인증 상태·관심 팀은 React Context(`AuthProvider`, `FavoritesProvider`). ④ 브라우저 저장소는 비회원 관심 팀(`kt-fav-guest`), 작성 중 후기·의견 초안(`sessionStorage`)에만 쓰고 모든 접근을 try/catch로 감싼다(저장소 사용 불가 시 안내 후 공개 기능 유지). 별도 전역 상태 라이브러리는 도입하지 않는다.
- **화면 간 반영:** 관심 팀·북마크·후기 변경 후 해당 query key를 무효화해 헤더·메인·팀 탐색·팀 상세·마이페이지가 같은 값을 보게 한다. 쿼리 키 규칙은 01이 `lib/api/query-keys.ts`에 정한다.
- **요청 상태 표준:** 모든 데이터 영역은 `DataState`(로딩·정상·빈 결과·일부 미제공·실패+재시도)로 감싼다. 빈 결과 문구와 실패 문구를 구분한다.
- **스타일:** Tailwind CSS v4. Figma의 색·글꼴·간격·반경을 `globals.css`의 `@theme` 토큰으로 정의하고 컴포넌트에서 임의 색상값을 직접 쓰지 않는다. `<html lang="ko">`.
- **Figma 디자인 기준(컬러 가이드·개발 전달 기준에서 확인):**
  - 레이아웃: 시안은 데스크톱 1920px·모바일 375px. 콘텐츠·헤더·푸터 내부는 최대 1280px 중앙 정렬의 유동 컨테이너. 1024px 미만은 메뉴 접기·1열 전환, 작은 화면 좌우 24px, 모바일 16px.
  - 서체·크기: Noto Sans KR. 본문 14px/22px 이상, 보조 설명 12px/20px 이상. 모바일 조작 영역 44px 이상.
  - 간격·반경: 4·8·12·16·24·32·48px, 버튼 반경 8px, 카드 반경 16px. 포커스는 3px 외곽선.
  - 색상 토큰: `bg/canvas #F8FAFC`, `bg/surface #FFFFFF`, `bg/subtle #F1F5F9`, `bg/selected #EFF6FF`, `text/primary #0F172A`, `text/secondary #475569`, `text/muted #64748B`, `text/inverse #FFFFFF`, `action/primary #2563EB`, `action/hover #1D4ED8`, `action/soft #DBEAFE`, `action/disabled #E2E8F0`, `border/default #E2E8F0`, `border/strong #CBD5E1`, `border/focus #93C5FD`, `status/live #047857`, `status/live-bg #ECFDF5`, `status/warning #B45309`, `status/warning-bg #FFFBEB`, `status/error #B91C1C`, `status/error-bg #FEF2F2`, `brand/key #0F172A`, `brand/arrow #BFDBFE`, `brand/rim #60A5FA`. 블루는 주요 동작·선택·링크에만 쓰고, 진행 중·주의·오류는 색과 상태명을 함께 표시한다.
  - 로고: 80×48 비율 심벌(`55:22`) + 워드마크(10px 간격). 높이 헤더 데스크톱 36px·모바일 32px, 푸터 24px.
  - 헤더: 로고와 메뉴 사이 32px, 메뉴 간격 32px, 로그인·회원가입은 오른쪽. **의견 보내기는 데스크톱 푸터와 모바일 하단 고정 영역에 둔다**(떠 있는 전역 버튼 아님). 모바일은 헤더 메뉴 버튼으로 메뉴·로그아웃을 연다.
  - 필터: 문자 기호 대신 16px 벡터 화살표, 텍스트와 8px 간격. 후기 반응은 16px 엄지 아이콘.
  - 경기 기록: 데스크톱·모바일 모두 타임라인 / 팀 통계 / 라인업 / 선수 평점 4탭. 제공사 선수 평점과 회원 경기 평점을 분리.
  - 푸터: 서비스 소개·이용약관·개인정보처리방침·문의 링크, 운영자 정보, 데이터·뉴스 출처와 권리 고지. 시안의 운영자·주소·이메일은 가상 정보이므로 설정값 또는 자리 표시로 구현한다.
  - 시안의 경기·선수 수치는 샘플이다. 실제 응답을 쓰고 미제공 값은 —로 표시한다.
- **접근성:** 모달·하단 시트는 포커스 이동·Escape 닫기·포커스 복귀, 아이콘 버튼은 `aria-label`, 표는 가로 스크롤.

### 6.7 환경 변수

| 위치 | 변수 | 비고 |
| --- | --- | --- |
| 백엔드 `.env` | `API_FOOTBALL_KEY`, `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET`, `DATABASE_URL` | 설정 완료 |
| 백엔드 `.env`(추가 예정) | `APP_ENV`, `CORS_ORIGINS`, `AUTH_JWT_SECRET`(02), `EMAIL_*`(02, 공급자 결정 후), `SCHEDULER_ENABLED`, `API_FOOTBALL_DAILY_BUDGET`(01), `IMAGE_RIGHTS_ENFORCED`(03), `NEWS_RETENTION_HOURS`(03) | 추가하는 채팅이 이 표를 갱신 |
| 프런트엔드 `.env.local` | `BACKEND_ORIGIN`(01, 서버 전용) | 기존 `NEXT_PUBLIC_API_BASE_URL`은 01에서 제거 |

비밀이 아닌 설정값(`BACKEND_ORIGIN`, `APP_ENV`, `SCHEDULER_ENABLED` 등)은 담당 채팅이 `.env`·`.env.local`에 직접 추가·수정할 수 있다. 이때 기존 비밀 값 줄은 읽어서 출력하거나 바꾸지 않는다. 코드에는 비밀이 아닌 설정의 기본값을 두어 변수가 없어도 로컬에서 동작하게 한다.

비밀 값은 `.env`·`.env.local`에만 둔다. `.env`·`.env.local`·`.env.example` 등 모든 `.env*` 파일은 Git에 올리지 않으며(사용자 결정), 필요한 변수 이름은 이 표로만 관리한다. 로컬의 `.env.example`은 참고용으로만 둔다. 새 비밀 값이 필요하면 사용자에게 직접 입력을 요청하고 값을 출력·기록하지 않는다.

## 7. 현재 개발 기반과 실행 방법

아래는 2026-10-31 00 채팅 확인 시점의 상태다. 아직 제품 기능은 구현하지 않았다.

| 영역 | 현재 기준 |
| --- | --- |
| 프런트엔드 | Next.js 16.4.3·React 19.3.0·TypeScript·Tailwind CSS v4(`@tailwindcss/postcss`). `cacheComponents`·`partialPrefetching` 켜짐. create-next-app 기본 시작 화면(`page.tsx`가 `next.svg`·`vercel.svg` 사용), `lang="en"`·기본 메타데이터·Geist 글꼴 그대로. 01이 교체·정리한다 |
| 백엔드 | FastAPI·Python 3.12·uv. `/health`·CORS·환경 설정·DB 연결·읽기 전용 연결 확인 명령 구현. ORM·마이그레이션 도구 미설치 |
| DB | Supabase PostgreSQL `kicktab-dev`(서울), Direct connection 5432, 현재 환경에서 IPv6 접속. Psycopg 3, `sslmode=verify-full` + `certs/supabase-ca.crt`. 제품 테이블 없음. Data API 꺼짐. **현재 DB는 이 프로젝트 하나뿐**이므로 개발 중 마이그레이션·롤백 검증도 여기서 한다(운영 DB 분리는 §10 C-07) |
| 버전 관리 | Git 저장소 루트 `kick-tab/apps/`, 원격 `main`·`dev`(§11) |

**2026-10-31 00 채팅 실행 확인:** 백엔드 `ruff check` 통과, 기반 테스트 6개 통과, DB 인증·`SELECT 1`·TLS 확인 통과(읽기 전용), 프런트엔드 `npm run lint`·`npm run build` 통과. 개발 서버 실행은 하지 않았다.

명령은 각 앱 폴더에서 실행한다.

| 위치 | 설치·실행 | 검사 |
| --- | --- | --- |
| `frontend/` | `npm ci` → `npm run dev` | `npm run lint`, `npm run build` |
| `backend/` | `uv sync --locked --group dev` → `uv run fastapi dev app/main.py` | `uv run ruff check .`, `uv run python -m pytest`, `uv run python -m app.check_database` |

**주의:** 이 PC에서는 Windows 애플리케이션 제어 정책이 `.venv`의 실행 파일(`pytest.exe` 등)을 간헐적으로 차단한다(2026-10-31 한 차례 `uv run pytest` 실패, 이후 재확인 시 실행됨). 안정적으로 `uv run python -m pytest`, `uv run python -m alembic …`처럼 `python -m` 형태를 사용한다.

기본 주소는 프런트엔드 `http://localhost:3000`, 백엔드 `http://localhost:8000`이며 API 문서는 `/docs`, 상태 확인은 `/health`다. 기본 Google Fonts는 빌드 시 네트워크 접근이 필요하다(Figma 글꼴 확정 시 01에서 교체).

현재 백엔드 Python 3.12.14는 `.python-runtime/`에 있고 `.venv`가 이를 참조한다. 둘 다 버전 관리에서 제외한다. 새 작업 환경이나 폴더 이동 시 Python 3.12와 가상환경을 준비한다. 의존성을 변경하면 잠금 파일(`uv.lock`, `package-lock.json`)도 갱신하고, 새 패키지는 설치 시점의 안정 버전을 확인해 고정한다.

## 8. 기능별 선행 조건과 완료 조건 요약

| 채팅 | 선행 조건 | 고유 완료 조건(공통 조건 §4에 추가) |
| --- | --- | --- |
| 01 | 없음(준비 완료) | SQLAlchemy·Alembic 첫 마이그레이션(`sync_runs`, `feedback`, RLS 포함) 적용·롤백 확인, 응답·오류 형식과 예외 처리기, CSRF·요청 제한 공통 의존성, API-Football 클라이언트 골격과 한도 보호 단위 테스트, `rewrites`·API 래퍼·생성 타입·Query Provider, 디자인 토큰·공통 UI, 헤더(인증 자리)·푸터(출처·권리 고지 자리)·TOP 5 띠 빈 상태·의견 보내기(비회원 제출, 1,000자, 실패 시 입력 유지) |
| 02 | 01 완료, `AUTH_JWT_SECRET` 사용자 입력 | 가입 인증번호 규칙 전체, 가입 직후 세션 확인, 로그인·갱신·로그아웃·비밀번호 찾기/변경, CSRF·오픈 리다이렉트 방지, 관심 팀 비회원/회원 분리(A→B→로그아웃 시 A 복원), 6번째 거부, 로그인 유도·복귀 유틸 테스트 |
| 03 | 01·02 완료 | 14개 대회·현재 시즌·5대 리그 팀·허용 집합 적재, 상태 변환 표 테스트, KST 날짜 묶음, 날짜 막대·대회 필터·팀 검색(별칭)·초기화 규칙, 관심 팀 일정 우선순위, 실시간 폴링(실제 경기 검증은 가능한 시간에 별도 기록), 뉴스 분류 규칙·중복 제거·출처 표시·북마크 저장/해제/재선택 |
| 04 | 03 완료 | 상태별 영역 전환, 미제공·발표 전 표기, 상대 전적 표시 조건, 평가 작성 가능 조건(일반 종료만), 1인 1건·수정·삭제, 반응·정렬 규칙, 평가 로그인 복귀, TOP 5 선정은 정책 확정분만 |
| 05 | 03 완료(04 경기 상세 연결) | 시즌 전체 종료 경기·팀/대회 결합 필터·초기화 규칙·페이지 분할, 과거 팀 검색과 상세 미제공 팀 링크 차단, 2025 적재 후 중복 없음 |
| 06 | 03·05 완료 | 시즌별 팀 순위·선수 순위 전환 규칙, 선방 자체 집계(누락 제외·인원 안내·공동 순위), red·yellowred 분리, 메인 간소 순위, 링크 허용 집합 적용 |
| 07 | 02·03 완료 | 현재 시즌 팀만 표시, 리그 필터·검색·관심 팀 토글·페이지 분할 |
| 08 | 03·06 완료 | 팀 상세 6개 영역, 선수 표 정렬·더 보기·누락 표시, 시즌 기록 전환, 이적 반기 분류·안내·고정, 팀 뉴스, 모바일 탭, 허용되지 않은 팀 직접 URL 차단 |
| 09 | 02·03·04 완료 | 마이페이지 4개 섹션, 회원 전용 접근 차단, 다른 화면과 변경 반영 일치, 로그아웃 이동 규칙 |

**01 세부 기준(2026-10-31 착수 전 검수에서 확정)**

- **진행 단계:** A 백엔드 기반(DB·마이그레이션·응답/오류 형식·공통 의존성·API-Football 클라이언트 골격·수집 실행기) → B 프런트엔드 기반(rewrites·API 래퍼·생성 타입·Query Provider·토큰·글꼴·공통 UI) → C 전역 화면(헤더·TOP 5 띠·푸터·모바일 하단 고정 영역·의견 보내기). 단계마다 검사 통과 후 커밋하고, Codex 교차 검증은 01 전체 완료 후 한 번 받는다.
- **`feedback` 테이블:** `users` 테이블이 아직 없으므로 `user_id uuid NULL`을 외래 키 없이 만든다. 02가 `users` 생성 시 외래 키를 추가한다(삭제 시 처리 방식은 P-03 결정 후). 01의 제출 API는 항상 비회원 익명 제출로 저장하고, 로그인 회원 연결은 02가 인증 의존성으로 붙인다. IP 주소는 테이블에 저장하지 않는다.
- **요청 제한:** 단일 인스턴스 기준 메모리 기반 제한기로 구현하고 키 함수를 교체할 수 있게 한다. 브라우저 요청은 Next.js `rewrites`를 거치므로 실제 클라이언트 IP는 `X-Forwarded-For`에서 얻되, 신뢰할 프록시(로컬 Next.js) 뒤에서만 이 헤더를 믿도록 설정값으로 둔다. 의견 제출 기본값은 P-10 제안값(분당 3회·일 20회)이며 확정 전임을 코드 주석과 §10에 유지한다.
- **CSRF 헤더:** `X-KickTab-Client: web` 검사는 공개 변경 요청인 의견 제출에도 적용한다. 프런트엔드 API 래퍼가 변경 요청에 이 헤더를 자동으로 붙인다.
- **API-Football 클라이언트:** 01에서는 실제 외부 호출을 하지 않는다(0회). 모의 전송으로 속도 제한·일일 예산·HTTP 200 + `errors` 실패 처리·재시도 상한·키 비노출을 테스트한다. 실제 호출은 03부터.
- **헤더 인증 영역:** 02 전까지 비회원 상태(로그인·회원가입 버튼)만 표시하고, 02가 `useAuth()`로 연결할 수 있게 컴포넌트 경계를 둔다. 모바일 메뉴의 회원용 변형(`62:1475`, `81:3209`)은 02에서 연결한다.
- **푸터:** 서비스 소개·이용약관·개인정보처리방침·문의 항목은 대상 문서가 없으므로(P-12) 링크 없이 표시하거나 "준비 중"으로 두고, 운영자·주소·이메일은 시안의 가상 값을 쓰지 않고 설정값 자리로 둔다. 데이터·뉴스 출처 고지 문구는 Figma 푸터를 따르되 이미지 권리 고지 문구는 V-10 확인 전 임시 문구로 표시한다.
- **브랜드·대체 이미지:** Figma `55:22`(로고 심벌)과 `55:26`(공통 대체 이미지)을 SVG로 내려받아 `frontend/public/brand/`, `frontend/public/placeholder.svg`에 둔다. 파비콘도 로고 심벌 기준으로 교체한다.
- **Figma 도구 사용:** `get_design_context`는 Figma의 design-to-code 안내(skill 또는 MCP 리소스)를 먼저 읽으라고 요구한다. 읽을 수 없으면 `get_metadata`·`get_screenshot`과 §6.6 토큰으로 구현하고, 생성 코드는 그대로 붙이지 말고 프로젝트 컴포넌트·토큰으로 옮긴다.
- **기본 생성 파일 정리:** create-next-app 시작 화면·`next.svg`·`vercel.svg`·Geist 글꼴은 01에서 제거하고, 메인 경로(`/`)는 03 전까지 헤더·푸터 사이에 빈 자리 표시만 둔다.

## 9. 사용자 확인·환경 작업

| ID | 내용 | 시점 |
| --- | --- | --- |
| U-01 | Git 저장소 연결 — 진행 상태는 §11 | 01 착수 전 |
| U-02 | 완료(2026-10-31): Figma 커넥터 연결. 별도 디자인 전달 문서는 사용하지 않기로 하고 Figma의 해당 참조 문구도 삭제 | — |
| U-03 | 완료(2026-10-31 확인): Supabase Data API가 처음부터 꺼져 있음(Integrations → Data API → Enable Data API 꺼짐). 코드의 RLS 활성화 규칙과 함께 유지한다. 나중에 Data API를 켜지 않는다 | — |
| U-04 | `AUTH_JWT_SECRET` 등 새 비밀 값 직접 입력 | 02 |
| U-05 | 메일 발송 공급자 선택과 계정·도메인 준비(§10 P-01) | 02 운영 연결 전 |

## 10. 미확정 정책·Codex 검토 요청

### 10.1 제품 정책 결정 대기 — 결정 전에는 해당 기능을 "제공 보류"로 구현

| ID | 결정 대상 | 영향 채팅 | 00 제안(결정 아님) |
| --- | --- | --- | --- |
| P-01 | 인증 메일 발송 공급자 | 02 | Resend·Amazon SES·Gmail SMTP 비교. 무료 한도·발신 도메인 인증 필요 여부 확인 |
| P-02 | 소셜 로그인 제공 여부, 같은 이메일 계정 연결 방식 | 02 | 1단계 이메일만, 소셜은 앱 등록 후 추가. 같은 이메일은 자동 연결하지 않고 기존 방식으로 로그인 안내 |
| P-03 | 회원 탈퇴 시 후기·반응·북마크·의견 처리, 같은 이메일 재가입 | 02·04·09 | 관심 팀·북마크·반응 삭제, 후기 삭제(집계에서 제외), 의견은 회원 연결만 해제 |
| P-04 | 닉네임·비밀번호 규칙(길이·허용 문자·금칙어) | 02 | 닉네임 2~12자 한글·영문·숫자, 비밀번호 8~64자 영문+숫자 포함 |
| P-05 | 행정 종료(AWD·WO) 경기의 평가·TOP 5 포함 여부 | 04 | 결정 전 제공 보류(문서 기준 유지) |
| P-06 | TOP 5 시간대·주간 귀속 시각·가중치·베이지안 보정·AI 전환 임계치·동점 기준, AI 선정 입력·출력 형식과 사용할 모델 | 04 | 사용자가 보유한 기준을 받아 정리. 결정 전 TOP 5 띠는 빈 상태 |
| P-07 | 경기 상태 변경 시 기존 평가 처리(D-07 잔여) | 04 | 종료→중단·취소 등 평가 불가 상태로 바뀌면 숨김 처리 후 원복 시 재노출 |
| P-08 | 뉴스 대회/팀 분류 세부 규칙, 언론사명 매핑 방식(D-09) | 03 | 원문 도메인→언론사명 매핑 표, 매핑 없으면 도메인 표시 |
| P-09 | 북마크 중복 키·보존 범위(D-10) | 03·09 | 원문 링크 정규화 해시를 중복 키로 사용, 보관 항목은 설정값 |
| P-10 | 의견 스팸 방지·보존 정책(D-11 잔여) | 01 | IP 해시 기준 분당 3회·일 20회 제한, 보존 기간은 운영 전 결정 |
| P-11 | 팀 별칭 사전 구축·관리 방식(D-16) | 03 | 시드 파일(`app/seed/team_aliases.*`)로 버전 관리하고 마이그레이션·시드 명령으로 적재 |
| P-12 | 이용약관·개인정보 처리방침 문서(가입 동의 화면 필요) | 02 | 문서 작성 주체와 버전 관리 방식 결정 필요 |
| P-13 | 분석 지표 도구·동의·익명 식별(D-12) | 최종 | 기능 완료 후 별도 결정 |

### 10.2 Codex 검토 요청 — 기술 설계(기획 변경 없음, 확인 요청)

| ID | 내용 | 이유 |
| --- | --- | --- |
| C-01 | Supabase Auth 대신 FastAPI 자체 인증 | 가입 전 인증번호 확인·미인증 계정 없음 규칙, 기존 psycopg 구조 유지 |
| C-02 | Next.js `rewrites`로 같은 출처 구성 + `httpOnly` 쿠키 토큰(접근 15분·갱신 14일 회전) | 토큰을 브라우저 스크립트에 노출하지 않음. 배포 시 프런트·백엔드 연결 방식이 이 구조를 지원해야 함 |
| C-03 | 수집 작업을 백엔드 내 APScheduler(단일 인스턴스) + CLI로 실행 | 배포 플랫폼 미정. 플랫폼 크론으로 바꿀 수 있게 분리 |
| C-04 | Supabase Direct connection이 IPv6 전용일 수 있음 | 배포 환경에 IPv6가 없으면 Supavisor 세션 풀러 연결로 바꿔야 함(배포 시 확인) |
| C-05 | 모든 테이블 RLS 활성화(정책 없음) + Data API 비활성화 — 사용자 확정(2026-10-31) | Supabase 공개 API로 테이블이 노출되는 것을 방지 |
| C-06 | 실시간 갱신을 클라이언트 폴링(30~60초)으로 구현 | 웹소켓 없이 단순화. 실제 경기 검증(V-04) 후 조정 |
| C-07 | 개발 DB(`kicktab-dev`) 하나로 개발하고, 공개 배포 전 운영용 Supabase 프로젝트를 분리할지 결정 | 개발 중 마이그레이션·테스트 데이터가 운영 데이터와 섞이지 않게 하기 위함(배포 시 결정) |

### 10.3 기존 기획·디자인 변경 요청

현재 없음. 기능 채팅에서 필요해지면 이유·대안·영향을 이 표에 추가하고 Codex 검토로 전달한다.

### 10.4 공개 전 필수 확인(기존 검증 문서 유지)

V-04 실시간 경기 검증, V-09 네이버 뉴스 선별·재분류·중복 정리·북마크 보관·수익화 허용 확인, V-10 엠블럼·선수 사진 권리와 API-Football 데이터 제3자 권리, V-16 프랑스 컵 2026-27 재조회, 운영 호출량 재산정(V-08).

## 11. Git 브랜치·커밋 규칙

원격 저장소: `https://github.com/dongjuSH/kick-tab.git`(`origin`). 저장소 루트는 `kick-tab/apps/`이며, 상위 `kick-tab/`의 기획 문서·API 검증 자료·와이어프레임은 올리지 않는다.

| 브랜치 | 용도 |
| --- | --- |
| `main` | 완성본만 올린다. 모든 기능 완료·전체 최종 검수·Codex 교차 검증을 마친 뒤 00 채팅이 `dev`를 병합한다 |
| `dev` | 통합 브랜치. 완료된 기능 브랜치를 하나씩 병합한다 |
| `feat/<번호>-<영문 이름>` | 기능 채팅 작업 브랜치. 작업 시작 시 최신 `dev`에서 만든다 |

기능 브랜치 이름: `feat/01-header-footer`, `feat/02-auth`, `feat/03-schedule`, `feat/04-match-detail`, `feat/05-results`, `feat/06-standings`, `feat/07-team-browse`, `feat/08-team-detail`, `feat/09-mypage`.

**작업 순서**

1. 시작: `git switch dev` → `git pull origin dev` → `git switch -c feat/<번호>-<이름>`.
2. 작업 중: 의미 있는 단위로 커밋한다. 메시지는 `<영역>: <변경 요약>` 형식의 한국어 한 줄 요약 + 필요 시 본문(예: `backend: 의견 접수 API와 요청 제한 추가`). 커밋 전 `git status`로 `.env*` 파일(`.env.example` 포함)·비밀 값·생성물·불필요한 기본 생성 파일이 포함되지 않았는지 확인한다.
3. 완료: 자체 검수 → Codex 교차 검증 → 보완·재검증이 끝나면 `dev`를 기능 브랜치에 병합해 충돌을 해결하고 검사를 다시 통과시킨다.
4. 통합: 사용자 요청에 따라 기능 브랜치를 `dev`에 병합하고 `origin`에 push한다. 한 번에 한 기능씩 병합한다.
5. 완성: 전체 최종 검수 후 사용자 요청에 따라 00 채팅이 `dev`를 `main`에 병합하고 push한다.

원격 push는 사용자가 요청한 경우에만 한다. 강제 push(`--force`), 이력 재작성, 다른 채팅 브랜치 수정은 하지 않는다. GitHub 인증이 필요하면 사용자가 직접 인증한다.

**현재 상태(2026-10-31):** 사용자가 원격 저장소를 새로 만든 뒤 `apps/` 내용만 담은 첫 커밋을 `main`·`dev`로 push했다. 00 채팅의 가이드 갱신은 `dev`에 직접 커밋하고 사용자 요청 시 push한다. 01 채팅은 최신 `dev`에서 `feat/01-header-footer`를 만든다.

**Git에 올리지 않는 것:** 모든 `.env*` 파일(`.env.example` 포함), 가상환경·Python 런타임, `node_modules`·`.next`, 캐시, 저장소 밖 로컬 자료(`../docs`·`../api-test`·`../wireframe`), 쓰지 않는 기본 생성 파일. 새 파일 유형이 생기면 루트 `.gitignore`를 먼저 갱신한다.
