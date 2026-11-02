# KickTab 개발 가이드

최종 갱신: 2026-11-02 (월), 한국 시간(KST) — 03 경기 일정(메인) 완료(Codex 교차 검증 통과), `feat/03-schedule` 커밋·push

**일정 UX(2026-11-02 확정, 03 반영 완료):** [확정 정책](../../docs/SCHEDULE_UX_POLICY_2026-11-02.md) — 대회는 단일 버튼에서 개별 대회 직접 선택(다중 선택은 보조 모드), 메인 팀 검색/관심 팀은 오늘 포함 14일 모아 보기, 해제 시 검색 전 날짜·현재 대회 복귀. 05 지난 경기도 같은 대회 선택 UI를 쓴다(§3.1).

**TOP 5 최신 확정(2026-11-02):** [정책](../../docs/TOP5_POLICY_2026-11-01.md)은 00:00 첫 시도→실패 시 00:05 자동 재시도 1회→재실패 시 자동 중단·운영 알림·지연 안내·수동 복구다. 첫 시도/재시도 동안 서버의 지난주 공개 결과를 실제 기간으로 유지하고 정상 검증 후 이번 주 결과로 교체한다. 사용자 UI는 목록·경기 일정 없음·지연 안내 3종이다. 문서·와이어프레임·Figma는 최신 UI 3종으로 반영했다. 기존 앱/계약의 처리 상태는 후속 보완 대상이며 이번 디자인 작업에서 실제 앱 코드·운영 알림은 실행하지 않았다.

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

주요 프레임 ID: 메인 `49:57`/`49:570`, 경기 상세 `52:151`/`52:404`(탭·평가 작성·라인업 발표 전·행정 종료 상태 별도), 팀 탐색 `52:624`/`52:949`, 팀 상세 `52:1254`/`52:1866`(모바일 선수·기록·뉴스 탭 `58:356`·`58:738`·`58:924`), 로그인 `52:2116`/`52:2265`, 회원가입 `52:2387`/`52:2545`(인증번호·자동 로그인 상태 별도), 마이페이지 `52:2674`/`52:2912`, 지난 경기 `53:593`/`53:995`, 리그 순위 `53:1353`/`53:2047`(앞이 데스크톱, 뒤가 모바일). 공통 UI 프레임은 `62:1427`~`62:1939`, `81:3209`. 01에서 추가·갱신된 프레임(2026-10-31): TOP 5 펼침 데스크톱 패널 `128:3145`(5경기)·`128:3474`(3경기)·`128:3674`(빈 상태), 모바일 시트 `128:3574`·`128:3686`, 전체 화면 `128:3700`(데스크톱)·`128:4408`(모바일), TOP 5 행 컴포넌트 `126:111`(데스크톱)·`126:140`(모바일), 계정 버튼 `133:4077`(헤더)·`133:4134`(모바일 메뉴), 리디자인 푸터 `49:532`·`49:1012`. 비밀번호 찾기(`134:4077`~`134:5037`)·소셜 가입 닉네임(`134:5149`·`134:5282`)·회원가입 인증번호/인증 완료 데스크톱(`134:5398`·`134:5623`) 프레임도 새로 생겼다(02 참고).

별도의 디자인 전달 문서는 없다. Figma의 컬러 가이드·설계 반영 기준·개발 전달 기준 프레임과 이 가이드 §6.6이 디자인 구현 기준이다.

**일정 탐색 디자인 — 간소화된 현재 구성(2026-11-02):** 전체 화면은 기존 기본 목록 `49:57`/`49:570`과 대표 FA컵 선택 결과 `193:12311`/`193:12949`, 여러 대회 선택 결과 `234:8881`/`234:9750`으로 데스크톱·모바일 각각 3개를 사용한다. 여러 대회는 FA컵·EFL컵 대표 조합 1개만 보여 주며 `FA컵 외 1개` 요약과 해당 대회 경기만 표시한다. 체크된 선택창은 `234:9381`/`234:10226`이며 적용 시 대표 결과, 취소·바깥 클릭 시 이전 화면을 유지한다. 전체 캔버스와 레이어 순서는 경기 일정→지난 경기→경기 상세→리그 순위→팀 탐색→팀 상세→계정→마이페이지→대회 선택→공통 UI→TOP5로 정리했다. 프레임 ID와 연결은 유지했고 캔버스 프레임 간 겹침 0건을 확인했다. 기존 지난 경기 `53:593`/`53:995`와 이전 시즌 `61:883`/`61:1290`에는 같은 대회 선택 UI를 반영했다. 공통 컴포넌트는 `KickTab/Competition Trigger`(`187:580`), `Competition Picker`(`187:1946`), `Schedule Match Row`(`187:603`), `Schedule Explorer`(`225:2013`: 기본·대회 선택·팀 14일·팀의 선택 대회 결과 없음), `Schedule Feedback`(`225:2374`: 대회 결과 없음·등록 일정 없음·팀명 불일치·로딩·조회 실패·부분 실패·0개 부분 실패)다. 필터 값과 상태는 이 컴포넌트의 데이터·모드로 표현한다. 중복 전체 화면과 검수용 복제본 330개를 삭제했다. 공통 대회 UI는 데스크톱 대화상자·모바일 하단 시트와 직접/보조 다중 선택 상태를 유지한다.

Figma 프로토타입은 대표 흐름(FA컵 선택·맨시티 팀 보기·선택창 열기/닫기)만 연결한 시안이고 날짜·경기는 10/29 기준 더미다. 동작 기준은 `62:1960`·확정 정책 문서와 03 구현(§2·§6.4)이다.

**AI TOP 5 디자인 반영·간소화(2026-11-02):** `KickTab/TOP5 Strip`(`159:923`)과 `KickTab/TOP5 Panel`(`159:924`)은 각각 Device 2종 × State 3종(`list`/`none`/`delayed`)이다. 기존 색상·서체·경기 행(`126:141`)을 유지했다. 준비·수집 실패·AI 실패별 UI를 없애고 후보 부족·지난주/이번 주·경기 상태 변경은 동일 목록의 데이터로 표현한다. 구 정책·중복 검수·불필요한 상세 변형 프레임 37개와 원본 변형 16개를 삭제했다. 9개 기본 페이지와 기존 확장 화면의 TOP5 인스턴스 75개가 개정 원본 3종을 사용한다.

대표 전체 펼침은 [데스크톱](https://www.figma.com/design/GUMDnZGrrtetjs1mI9MZsd/KickTab?node-id=128-3700)·[모바일](https://www.figma.com/design/GUMDnZGrrtetjs1mI9MZsd/KickTab?node-id=128-4408)만 유지했다. 공통 패널/시트는 목록 `128:3145`/`62:1523`, 경기 없음 `128:3674`/`128:3686`, 지연 `164:5582`/`164:6129`다. 기능별 캔버스 배치와 레이어 순서를 유지한다. 삭제된 과거 7종·320 검수 프레임 링크는 현재 기준으로 사용하지 않는다.

`Title`, `Period`/`Metadata`, `EmptyMessage`, `PreviousNotice`로 실제 표시 주·선정 시각과 지난주 유지 안내를 전달한다. `ShowRow4`/`ShowRow5`/`ShortListNotice` 및 행 데이터로 후보 부족을 표현하며 주별·개수별 전체 페이지를 복제하지 않는다. 모바일 경기 없음·지연 띠도 기간을 표시하고 줄바꿈에 맞춰 높이가 변한다. 지난주 공개가 경기 없음이면 실제 지난주 기간·제목으로 같은 UI를 유지한다. 00:00 첫 시도와 고정 시각 00:05 재시도 동안 서버 공개 결과 유지, 재실패 후 통합 지연 안내, 정상 검증 후 원자적 공개 버전 교체다. 사용자 AI 선정 재시도 버튼은 없다.

1920·375·320px에서 대표 화면과 3종 UI, 지난주 제목·기간·선정 시각의 정적 배치·속성을 확인했다. 실제 프로토타입 플레이어의 클릭·스크롤·키보드/포커스·스크린리더/터치 실기기는 미검증이다. 검수용 임시 보드는 확인 후 삭제한다. 날짜·경기·선정 이유는 10/29 기준 와이어프레임 더미다. 전체 펼침은 대표 배경과 BACK을 사용하므로 실제 구현은 출발 페이지·스크롤을 보존한다. 현재 matchId를 유지한 상세 탭 조회, 실제 예약 실행·시간 제한·잠금·운영 알림·수동 복구·이전 시도 공개 차단·클라이언트 버전 감지 및 즉시 교체는 구현 인계 사항이다. 실제 서비스 코드는 수정하지 않았다. [TOP5 정책·접근성 인계](https://www.figma.com/design/GUMDnZGrrtetjs1mI9MZsd/KickTab?node-id=168-348)를 따른다.

## 2. 채팅 구성과 담당 범위 — 전체 10개

각 기능 채팅은 담당 기능의 프런트엔드·백엔드·DB 마이그레이션·예외 처리·자체 검수까지 함께 맡는다. 같은 작업 폴더를 쓰므로 **코드 수정은 아래 순서대로 한 채팅씩 진행한다.** 기능 ID는 기능 명세서 기준이다.

| 순서 | 채팅 | 담당 기능 ID | 담당 범위(공통 기능 포함) |
| --- | --- | --- | --- |
| — | 00 전체 설계·조율·검수 | — | 공통 설계, 범위·순서 결정, 가이드 관리, 기능별 완료 확인, 전체 최종 검수, 사용자 요청 시 Git 원격 업로드 |
| 1 | 01 헤더·푸터 + **공통 기반** | COM-003·004, FEED-001~003, TOP-003(표시) | §6의 프런트·백엔드 공통 기반 전체, 디자인 토큰, 공통 UI 컴포넌트, 헤더(인증 영역은 자리만)·푸터·TOP 5 띠(조회·7가지 상태 표시)·의견 보내기 |
| 2 | 03 경기 일정(메인) | SCH-001~006, LIVE-001~004, CMP-001~004, NEWS-001~004, FAV-001~004의 비회원 부분, OPS-001~004(해당분) | 대회·시즌·팀 기준 데이터와 **팀 상세 허용 집합**, 별칭 사전, 경기 수집·상태 변환·실시간 갱신, `MatchCard`·`CompetitionFilter`·`TeamSearch`, 메인 일정, **비회원 관심 팀(localStorage 저장소·`useFavorites()`·`FavoriteToggle`·관심 팀 일정·관심 팀 버튼) 사전 제작**, **뉴스 수집·분류와 `NewsCard`** |
| 3 | 04 경기 상세 | MAT-001~005, REV-001·004, TOP-001·002 | 경기 상세(상태별 영역·이벤트·기록·상대 전적·최근 흐름), 회원 평가·후기 **조회**·정렬, TOP 5 선정 작업(정책 확정분만, §10). 후기 작성·수정·삭제·반응은 회원 기능이므로 02에서 마무리하고, 04는 02가 붙일 수 있는 API·화면 구조까지 사전 작업한다 |
| 4 | 05 지난 경기 | HIST-001~003 | 지난 경기 조회·필터·페이지 분할, `SeasonSelect`, 2025 시즌 과거 데이터 적재 작업 |
| 5 | 06 리그 순위 | LEAG-001·002·004 | 순위 수집, 시즌별 전체 순위, 선수 순위(득점·도움·카드·선방 자체 집계), 메인 간소 순위 영역, 리그 전체 선수 시즌 기록 수집 |
| 6 | 07 팀 탐색 | LEAG-003 | 현재 시즌 5대 리그 팀 목록·리그 필터·팀명 검색·비회원 관심 팀 등록/해제(03의 `FavoriteToggle` 재사용) |
| 7 | 08 팀 상세 | TEAM-001~006 | 팀 기본 정보·경기·선수 표·시즌 기록·이적(배치 포함)·팀 뉴스(03 뉴스 재사용)·비회원 관심 팀 버튼(03 재사용), 모바일 탭. **08까지 마치면 비회원 기준으로 서비스 전체를 이용할 수 있어야 한다** |
| 8 | 02 로그인·회원가입(**08 다음**) | AUTH-001~005, COM-001·002·005, FAV-001~003의 회원 부분, BOOK-001·003, REV-002~003 연결, MY-004의 계정 API | 인증·세션·실제 메일 인증번호·비밀번호 찾기/변경·탈퇴 API, 헤더 인증 영역 연결, 로그인 유도 다이얼로그와 복귀(returnTo/intent), 작성 중 입력 보존 유틸, **관심 팀 회원 DB 동기화**(비회원 관심 팀은 03), **뉴스 북마크 버튼·API**, **04 후기 작성·수정·삭제·반응 연결 마무리**, 의견 회원 연결 |
| 9 | 09 마이페이지 | MY-001~004, BOOK-002 | 관심 팀 관리·내 평가·저장 뉴스·계정(02 API 사용) 화면 통합 |

**공통 기능 담당과 재사용 방식**

| 공통 기능 | 만드는 채팅 | 재사용 채팅 | 재사용 방식 |
| --- | --- | --- | --- |
| 공통 UI(버튼·뱃지·다이얼로그·하단 시트·스켈레톤·`DataState`) | 01 | 전체 | `src/components/ui/`: `Button`·`ButtonLink`·`IconButton`(`Button.tsx`), `Badge`(tone `accent`·`live`·`neutral`·`warning`(`info`는 예정 회색 변경으로 03에서 삭제), size `small` 12px(기본·TOP 5)·`caption` 11px(일정·뉴스)), `Dialog`(layout `center`·`sheet`·`responsive`, `compact` 시트는 헤더 아래까지만 커지고 시트 전체는 스크롤하지 않으며 자식이 스크롤 영역을 정함, `handle`은 하단 시트일 때만 손잡이·16px 여백(03 대회 선택창), `initialFocus` `dialog`·`close`, `id`)·`BottomSheet`, `Skeleton`, `DataState`·`StateMessage`(오류는 Figma `57:150`대로 정보 아이콘·어두운 제목·'다시 확인' 버튼, 03에서 변경), `Icon`(`public/icons/`: chevron-down·left·right, menu, x, search, info), `cx`, 필터 칩 스타일 `chipClass()`(`chip.ts`, 03). 반경 토큰 `rounded-tile`(12px, 뉴스 카드)을 03이 추가했다. 탭·드롭다운·페이지네이션은 01 화면에서 쓰지 않아 삭제했다(2026-11-02 재검수). 처음 필요한 채팅이 Figma 기준으로 만들고 이 표에 추가한다 |
| 엠블럼·선수 사진·공통 대체 이미지(`TeamCrest`, `PlayerPhoto`) | 01 | 전체 | `src/components/common/TeamCrest.tsx`. 이미지 URL이 `null`이거나 로드 실패면 `public/placeholder.svg`. 로고는 `src/components/common/Logo.tsx`(`size`: `header`·`header-mobile`·`footer`) |
| API 클라이언트·응답 타입·오류 처리 | 01 | 전체 | `src/lib/api/client.ts`의 `apiFetch<T>(path, { method, query, body })`(→ `{ data, meta }`, 변경 요청에 CSRF 헤더 자동, 401 갱신 연결 자리 `setUnauthorizedHandler`), `errors.ts`의 `ApiError`(`status`·`code`·`message`·`fieldErrors`·`retryAfter`), `types.ts`(생성 타입 별칭), `query-keys.ts`, KST 포맷 `src/lib/format/kst.ts`. 백엔드는 `app/api/errors.py`의 `ApiError(status, code, message)`, `app/schemas/common.py`의 `ApiModel`·`DataResponse[T]`, 공통 경기 스키마 `app/schemas/match.py` |
| TOP 5 띠 | 01(표시, 2026-11-01 정책 기준) / 04(선정 작업 + 2026-11-02 개정의 UI 3종·응답 계약·교체 감지, 사용자 결정 2026-11-02) | 전 페이지 | `GET /api/v1/top-matches/current`, `src/features/top5/`(`Top5Strip`, `Top5List`, 상태·문구 규칙 `model.ts`, `currentTopMatchesQuery`), 백엔드 `app/services/top_matches.py`의 `get_current_top_matches()`(04가 교체)·`current_kst_week()` |
| 의견 보내기 | 01 | 전 페이지 | `src/features/feedback/`(`FeedbackProvider`·`useFeedback().openFeedback()`, `FeedbackButton`, `FeedbackDialog`), `POST /api/v1/feedback`, 백엔드 `app/services/feedback.py`의 `create_feedback(session, payload, user_id=None)`(02가 회원 ID 전달). 저장 후 디스코드 채널 알림(`app/notifications/discord.py`의 `notify_feedback`, 백그라운드 작업·실패해도 저장 유지) |
| 헤더 인증 영역 | 01(비회원 자리) / 02(연결) | 전 페이지 | `src/components/layout/HeaderAuth.tsx`(`layout`: `desktop`·`menu`, `onNavigate`)의 본문만 `useAuth()`로 교체 |
| 수집 작업 실행기·API-Football 클라이언트 | 01 | 03·04·05·06·08 | `app/sync/registry.py`의 `@register_job(name, schedule=...)`와 `JobContext.api_football()`(요청 수 자동 집계), 작업 모듈은 `app/sync/jobs.py`에 import 추가, 실행 `uv run python -m app.sync <job> [key=value]`. 클라이언트 `app/providers/api_football.py`의 `ApiFootballClient.get()`. 03 추가: `register_job(..., precheck=)`(DB만 보는 사전 확인이 False면 API 호출·`sync_runs` 기록 없이 건너뜀, 1분 주기 작업용), `JobPartialFailure`(일부 단위만 실패할 때 저장 가능한 식별자만 담아 `sync_runs.error_summary`에 남김). 03 작업: `reference`·`team_aliases`·`fixtures`·`fixtures_live`·`news`(§6.5). 네이버 클라이언트 `app/providers/naver_news.py`의 `NaverNewsClient.search()` |
| 요청 제한·CSRF | 01 | 02 이후 변경 API | `app/api/deps.py`의 `RateLimit(scope, [Limit(횟수, 초)], key_func=, global_limits=)`. 본문이 있는 경로는 라우터에 `route_class=limit.route_class()`를 지정해 본문 해석 전에 적용한다(잘못된 JSON도 집계). 본문 없는 경로는 의존성으로 써도 된다. `/api/v1` 라우터 전체에 `require_csrf` 적용 |
| 인증 상태·로그인 유도·복귀 | 02 | 09, 04 후기 작성 연결 | `useAuth()`, `requireLogin({ intent })` |
| 관심 팀 | 03(비회원 저장소·토글·일정 선별) / 02(회원 DB 동기화) | 07·08·09 | `src/features/favorites/`: `useFavorites()`(`status` `loading`·`ready`·`unavailable`, `ids`, `max`, `has(id)`, `add(id)`·`remove(id)` → `added`·`removed`·`exists`·`limit`·`unavailable`·`failed`), `<FavoriteToggle teamId teamName fullWidth?>`(Figma `52:723`/`52:737`, 거부 사유 표시), 저장소 `store.ts`(`kt-fav-guest`, 팀 ID 배열 최대 5개, 모든 접근 try/catch, 다른 탭 `storage` 이벤트 반영), 메인 패널 `FavoriteSchedule`. 일정 API `GET /fixtures/next?teams=`(§6.4) |
| 팀 링크 허용 여부 | 03 | 04·05·06·07·08 | 모든 팀 참조 응답의 `detailAvailable: true \| false \| null`. 백엔드 `app/services/reference.py`의 `team_detail_lookup(session)`(현재 시즌 5대 리그 팀 목록이 모두 수집됐을 때만 `false`, 그 전에는 목록 밖 팀을 `null`)·`team_ref(team, lookup)`·`crest(url)`(`IMAGE_RIGHTS_ENFORCED`) |
| 경기 카드·상태 뱃지 | 03 | 04·05·08·TOP 5 | `src/components/common/MatchCard.tsx` `<MatchCard match layout="schedule"\|"stacked" withDate?>`(Figma `187:591`/`225:1918`: 테두리 카드, 카드 전체가 `/matches/[id]` 링크, 한국어 대회명, 1024px 이상 schedule은 164px 대회·시각 열 + 팀·스코어 + 상태 한 줄, 좁은 폭·stacked는 대회·시각 → 팀 → 상태, 승부차기 `PK 4:2`, 경기 중단 '중단 시점 스코어', `withDate`는 '11/5(목) 02:45'), `MatchStatusBadge.tsx` `<MatchStatusBadge match size?>`(진행 중 `63′` 초록·예정/종료/확인 필요 회색·연기/취소/경기 중단/행정 종료 주황). 표기 규칙 `src/lib/format/match.ts`(`teamName`·`competitionName`(한국어 이름, 'UEFA ' 접두 생략)·`scoreText`·`penaltyText`·`kickoffTime`·`isChanged`·`statusWord`). 백엔드 `app/services/fixtures.py`의 `to_summary()`·`fixtures_on()`·`next_for_teams()`·`team_schedule()`, 상태 변환 `app/services/match_status.py`의 `map_status()` |
| 대회 필터 | 03 | 05 | `src/components/common/CompetitionFilter.tsx` `<CompetitionFilter competitions selected onChange>`(03 반영 2026-11-02, Figma `187:564` 버튼·`187:1946` 선택창): 단일 버튼('전체 대회'·'FA컵'·'FA컵 외 1개') → 데스크톱 560px 대화상자·모바일 손잡이 있는 하단 시트(`Dialog` `handle`). 대회 이름 클릭 = 그 대회만 즉시 적용·닫힘. '전체 대회 보기' = 조건 해제. '여러 대회 선택' = 현재 명시 선택에서 시작하는 초안 체크, 'N개 선택'/'0개 선택 · 최소 1개를 선택하세요', 0개면 '선택 적용' 비활성, 취소·Esc·바깥 클릭은 기존 조건 유지. 국가/UEFA 제목은 분류만(그룹 전체 선택 없음). `selected`가 빈 배열이면 전체. [확정 정책](../../docs/SCHEDULE_UX_POLICY_2026-11-02.md) |
| 팀 검색 자동완성·별칭 사전 | 03 | 05·07·뉴스 분류 | `src/components/common/TeamSearch.tsx` `<TeamSearch selected onSelect>`(combobox, 후보 여러 개·일치 없음 '다른 팀으로 바꿔 보여주지 않습니다' 상태, 입력 옆 × 또는 입력 전체 삭제 = `onSelect(null)`), `GET /api/v1/teams/search?q=`(현재 시즌 후보만, 05가 시즌 범위 추가), 백엔드 `app/services/team_search.py`, 별칭 시드 `app/seed/team_aliases.json`(P-11) + `normalize_name()` |
| 뉴스 카드·북마크 버튼 | 03(카드) / 02(북마크 버튼·API) | 08·09 | `src/components/common/NewsCard.tsx` `<NewsCard article now>`(뱃지·제목·설명·원문 도메인·상대 시각, 카드 전체가 `/news/original?id=` 원문 이동), `NEWS_BADGE_LABELS`, 메인 영역 `src/features/news/MainNews.tsx`(뱃지 필터·6개씩 더 보기). 팀 뉴스 목록 컴포넌트는 08이 같은 카드로 만든다 |
| 시즌 드롭다운 | 05 | 06 | `<SeasonSelect>` + `GET /api/v1/competitions` 시즌 정보 |
| 리그 선수 시즌 기록 | 06 | 08 | `player_season_stats` |

담당이 아닌 채팅은 같은 기능을 중복 구현하지 않는다. 공통 컴포넌트가 부족하면 담당 채팅의 구조를 확장하고 이 표를 갱신한다. 페이지 목록에서 빠졌다는 이유로 명세의 기능을 누락하지 않는다.

## 3. 진행 상태와 다음 작업

| 채팅 | 상태 | 비고 |
| --- | --- | --- |
| 00 | 첫 설계·01 착수 전 검수(2026-10-31), 01 완료 확인(2026-11-01) | 이 문서 §2·§6~§11 확정. Codex 검토 요청 사항은 §10 |
| 01 | **완료(2026-11-02) — 재검수·Codex 교차 검증 통과, `dev` 병합** | 재검수에서 TOP 5를 AI 주간 정책으로 교체(응답 `week`·`state`·`selectedAt`·`items[rank·reason·match]`, 띠·데스크톱 패널·모바일 시트 7가지 상태), 실제 실행 검수(1280·375·320, 의견 실제 제출·DB 저장·디스코드 전송), 쓰지 않는 코드 삭제(탭·드롭다운·페이지네이션·평점 표시 등). TOP 5는 04 전까지 `pending`(선정 중)으로 표시된다. 2026-11-02 정책 개정(UI 3종 등)은 01이 아니라 04에서 반영한다(사용자 결정 2026-11-02). 후속 결정은 §10.3 D-01-10·D-01-11 |
| 02 | **대기 — 08 다음에 처음부터 진행** | 이전 구현은 모두 삭제했다(브랜치 삭제, 개발 DB `0002_feedback_body_hash`, `backend/.env`의 02 항목 삭제). 확정 정책(P-01·P-02·P-03·P-04·P-10·P-12)과 §6.2 설계는 그대로 쓴다. 착수 전 §9 U-04·U-05 |
| 03 | **완료(2026-11-02) — Codex 교차 검증 통과(2차), `feat/03-schedule` 커밋·push. `dev` 병합은 00 확인 후** | 실제 API로 14개 대회·현재 시즌·5대 리그 96팀·별칭 371개, 경기(오늘−1~+15일) 289건, 네이버 뉴스 352건 수집. 메인 일정(날짜 보기·[일정 UX 정책](../../docs/SCHEDULE_UX_POLICY_2026-11-02.md)의 대회 직접 선택·팀 14일 모아 보기·URL 복귀), 비회원 관심 팀, 뉴스 분류(P-08)·원문 확인, `MatchStatusBadge`. 브라우저 실제 실행 검수 1280·375·320, 자정 전환·임박 폴링은 시계 조작으로 확인. **미검증:** 실제 진행 경기 실시간 갱신(검수 시점 진행 경기 없음), 실제 자정 경과. 1차 교차 검증 지적 6건(초기화·임박 폴링·뉴스/관심 팀 실패 처리·팀 ID 검증·여자 축구 제외)과 디자인 차이 3건을 보완했다 |
| 04~09 | 대기 — 다음은 04 경기 상세 | §4 작업 원칙 1의 순서대로, 앞 작업의 Codex 교차 검증과 00 채팅 확인 후 진행 |

기능 채팅 완료 시 이 표의 상태, 새로 생긴 공통 인터페이스, 남은 확인 사항을 갱신한다.

### 3.1 다음 채팅 인수인계

**정리 규칙(사용자 결정 2026-11-01):** 인수인계는 받는 채팅 이름 아래에 적는다. 받는 채팅이 그 내용을 반영해 작업을 마치면 해당 항목을 지워 문서를 간소화한다. 여러 채팅이 계속 지켜야 하는 규칙은 인수인계에 두지 않고 '공통 규칙'(또는 §6 상설 장)으로 옮긴 뒤 지우지 않는다.

공통 인터페이스의 위치·이름은 §2 표, 파일별 역할은 `docs/file-feature-map.md`를 본다. 아래는 그 밖에 이어받을 때 알아야 할 점이다.

**공통 규칙(전 채팅)**

- **API 추가:** 라우트는 `app/api/routes/<리소스>.py`에 만들고 `app/api/router.py`에 등록한다. 스키마는 `ApiModel`을 상속하고 응답은 `DataResponse[T]`로 감싼다. 오류는 `ApiError(status, code, message)`로 던진다. 새 오류 코드는 §6.4 표와 `frontend/src/lib/api/errors.ts`의 `ApiErrorCode`에 함께 추가한다. 변경 요청(POST·PUT·PATCH·DELETE)은 라우터 단에서 CSRF 검사가 자동 적용된다.
- **타입 동기화:** 백엔드 스키마를 바꾸면 백엔드 실행 후 `npm run gen:api`로 `src/lib/api/schema.d.ts`를 다시 만들고, 필요한 이름은 `src/lib/api/types.ts`에 별칭으로 추가한다. 타입을 손으로 쓰지 않는다.
- **마이그레이션:** 파일 이름 `YYYYMMDD_NNNN_<이름>.py`, 리비전 ID는 `NNNN_<이름>`으로 직접 지정한다(`python -m alembic revision --autogenerate -m ... --rev-id NNNN_<이름>` 후 파일명 변경). 자동 생성은 CHECK 제약을 만들지 않으므로 직접 추가한다. 새 테이블은 RLS 활성화를 포함하고, 적용 후 `downgrade -1`·`upgrade head`·`alembic check`를 확인한다. 모델은 `app/models/__init__.py`에 import한다.
- **테스트:** `tests/conftest.py`가 실제 외부 HTTP 호출을 막고 로컬 웹후크 설정을 무시한다. 외부 API는 `httpx.MockTransport`로 시험한다. 실제 DB 확인이 필요하면 `KICKTAB_DB_TESTS=1`일 때만 도는 테스트로 만들고 트랜잭션을 롤백한다(`tests/test_db.py` 참고). 라우트 테스트는 `app.dependency_overrides[get_db]`로 세션을 바꾸고, 모의 세션은 `session.scalar.return_value`를 지정해야 한다.
- **오류 로그:** 미처리 예외는 `app/api/errors.py`의 `UnhandledErrorMiddleware`가 공통 500 응답으로 바꾸고 예외 종류만 기록한다(서버 로그에 메시지·traceback을 남기지 않음, `tests/test_server_logging.py`가 실제 Uvicorn으로 확인). 새 앱·테스트 앱도 `register_exception_handlers(app)`를 다른 미들웨어보다 먼저 호출한다. 진단이 더 필요하면 메시지 대신 안전한 식별 정보(오류 코드·리소스 ID)를 로그에 남긴다.
- **동시성:** '조회 후 저장'으로 중복을 막는 서비스는 같은 트랜잭션 안에서 키별 `pg_advisory_xact_lock`으로 묶는다(`app/services/feedback.py`의 `lock_body_hash` 참고). 키는 다른 용도와 겹치지 않게 접두어를 붙여 해시한다. 메모리 제한기 `RateLimiter`는 `check`·`record`·`hit`가 각각 한 번의 잠금으로 동작하고(`hit`은 검사와 기록을 한 잠금 안에서 처리), 잠금 안에서는 `_check_locked`·`_record_locked`만 호출한다.
- **커서:** Tailwind v4는 버튼 커서를 기본 화살표로 두므로 `globals.css` base에서 활성 `button`·`[role=button]`·`[role=option]`·`summary`를 손가락 커서로 지정했다(03, 사용자 피드백). 새 클릭 요소는 버튼·링크 요소로 만들면 자동 적용된다.
- **화면:** 색·글자·반경은 `globals.css` 토큰 유틸리티만 쓰고(§6.6), 데스크톱 배치는 `lg:`(1024px)부터, 콘텐츠 폭은 `kt-container`. 모든 데이터 영역은 `DataState`로 상태를 구분한다. 모달·시트는 `Dialog`(`layout`: `center`·`sheet`·`responsive`)를 쓴다. 같은 성질의 Tailwind 클래스를 `buttonClass` 위에 덧붙이면 충돌해 적용되지 않을 수 있으므로(01에서 모바일 메뉴 강조가 이 문제로 실패), 상태별 스타일은 겹치지 않게 조합하고 브라우저에서 계산 스타일을 확인한다.
- **조작 영역:** 모바일 44px 이상은 실제 클릭 영역 기준이다. 시안 높이를 지켜야 하면 `before:` 가상 요소로 영역만 넓힌다.
- **장시간 표시 데이터:** 현재 앱 TOP 5는 5분 경과 후 포커스/펼침 재조회·화면 활성 중 30분 주기 조회다. **새 정책 보완 대상:** 정상 공개 API는 새 버전을 즉시 반환하고 열린 화면도 공개 버전 변경/완료를 감지해 교체해야 한다. 30분 주기만으로 주간 교체·수동 복구를 반영하지 않는다. 실제 완료 감지 수단과 지연은 04에서 구현·검증한다.
- **외부 이미지:** `TeamCrest`·`PlayerPhoto`는 `next/image`를 `unoptimized`로 쓰므로 원격 도메인 설정이 필요 없다. URL이 `null`이거나 실패하면 대체 이미지가 나온다.
- **아직 없는 경로:** `/results`·`/standings`·`/teams`·`/login`·`/signup`·`/matches/[id]`는 404 안내(`app/not-found.tsx`)가 뜬다. 담당 채팅이 `app/<경로>/page.tsx`를 만들면 바로 연결된다. 메인 `/`는 03이 구현했다.
- **동적 경로와 루트 레이아웃(03 확인):** `cacheComponents`에서 `[id]` 같은 동적 세그먼트 페이지를 만들면 루트 레이아웃의 `usePathname()` 클라이언트 컴포넌트(`MainNav`·`MobileMenu`·`Top5Strip`·`FeedbackDialog`)가 `<Suspense>` 밖이라 개발 콘솔에 'blocking-prerender-client-hook' 오류가 난다. 03은 원문 이동을 정적 경로 `/news/original?id=`로 피했다. 첫 동적 경로를 만드는 04가 레이아웃 쪽 처리(해당 컴포넌트를 `<Suspense>`로 감싸기 등)를 결정한다.
- **URL 검색 파라미터:** `useSearchParams()`를 쓰는 클라이언트 영역은 `<Suspense>` 안에 둔다(메인 `ScheduleSection` 참고). 렌더 중 `Date.now()`는 개발 서버가 prerender 오류로 잡으므로 데이터가 있을 때만 읽거나 효과(effect)·쿼리 상태(`dataUpdatedAt`)를 쓴다.
- **검수 팁:** 앱의 브라우저 창이 숨겨져 있으면 `requestAnimationFrame`이 멈춰 React의 Suspense 표시 전환·hydration이 대기한다(앱 결함 아님). 스크린샷을 찍으면 프레임이 진행된다.
- **로컬 실행:** 백엔드는 `uv run python -m uvicorn app.main:app --port 8000`(설정·`.env`를 바꾸면 재시작 필요), 프런트는 `npm run dev`. Windows에서 백그라운드로 띄운 서버가 종료 후에도 남아 포트를 점유할 수 있으니 `netstat -ano`로 확인한다.
- **Figma:** 커넥터 응답이 간헐적으로 끊기면(`MCP server connection lost`) 같은 호출을 다시 하면 된다. 페이지 전체 메타데이터는 매우 커서 파일로 저장되므로 프레임 단위로 조회한다.

**02 이전 단계 규칙(03~08)**

- 회원 로그인이 필요한 기능(회원 관심 팀 DB 동기화, 뉴스 북마크, 후기 작성·수정·삭제·반응, 마이페이지)의 UI·API·테이블은 만들지 않는다. 비회원이 쓰는 기능은 그 단계에서 끝까지 만든다: **비회원 관심 팀은 03이 사전 제작**(localStorage 저장소·`useFavorites()`·`FavoriteToggle`·관심 팀 일정·관심 팀 버튼)하고 07·08이 재사용해 마무리한다. 04는 후기 조회까지 만들고 작성 API·화면이 붙을 자리를 02에 인수인계한다. 빈 버튼이나 '준비 중' 자리는 넣지 않는다.
- 헤더 인증 영역은 01 상태(비회원 로그인·회원가입 버튼)를 유지한다. `/login`·`/signup`은 02 전까지 404 안내다.
- 의견은 01 방식대로 모두 비회원 익명 저장(`user_id` NULL, 외래 키 없음)·IP 기준 요청 제한을 유지한다. 회원 연결·차등 제한(P-10)은 02가 붙인다.
- 마이그레이션 번호는 만드는 순서대로 이어 쓴다(03이 `0003`~`0005`, 다음은 `0006`). 02는 착수 시점의 다음 번호를 쓴다.

**02 로그인·회원가입(08 다음)**

- 이전 구현은 삭제됐으므로 처음부터 만든다. 착수 전 `AUTH_JWT_SECRET`(U-04)과 Gmail SMTP 계정(U-05)을 준비하고, 실제 메일로 가입·비밀번호 찾기가 끝까지 동작해야 완료다(§4 작업 원칙 3).
- (03에서) 관심 팀 출처 전환은 `src/features/favorites/useFavorites.ts` 한 곳에서 한다(반환 형태 유지). 저장소 `store.ts`는 비회원 전용으로 남기고 로그인 중에는 읽지 않는다. 뉴스 북마크 버튼은 `NewsCard` 오른쪽 위(Figma `49:462`, 44px)에 둔다.
- 앞 단계에서 넘어올 일: 비회원 관심 팀(03)에 회원 DB 동기화 연결(로그인 시 DB 목록 사용·병합 금지·로그아웃 시 로컬 복원), `NewsCard` 북마크 버튼과 `/me/bookmarks` API·`bookmarks` 테이블(BOOK-001·003, P-03 `ON DELETE CASCADE`, P-09 중복 키), 04 후기 작성·수정·삭제·반응 마무리(REV-002·003, 평가 로그인 복귀). 각 단계가 남긴 구체 인수인계는 이 항목 아래에 추가한다.
- `src/components/layout/HeaderAuth.tsx` 본문을 `useAuth()`로 교체한다(회원: 마이페이지·로그아웃, Figma `62:1475`·`81:3209`). 헤더와 모바일 메뉴가 같은 컴포넌트를 쓴다.
- `setUnauthorizedHandler`(`src/lib/api/client.ts`)에 `POST /api/v1/auth/refresh` 1회 갱신(동시 요청 합치기)을 등록한다. 서버 컴포넌트에서 `apiFetch`를 부르면 브라우저 쿠키가 전달되지 않으므로, 회원 데이터를 서버에서 조회하려면 `cookies()`를 넘기도록 확장한다.
- 의견: `routes/feedback.py`에서 인증 사용자 ID를 `create_feedback(..., user_id=)`로 넘기고, `users` 생성 마이그레이션에서 `feedback.user_id` 외래 키를 추가한다(삭제 처리는 P-03). 회원·비회원 차등 요청 제한을 붙인다(P-10). 디스코드 알림의 '작성자'는 `user_id`로 회원/비회원을 자동 표시한다.
- 의견 본문이 디스코드로 전송되므로 개인정보처리방침(P-12)에 반영한다. 정책 문서가 생기면 `SiteFooter.tsx`의 정책 항목을 링크로 바꾼다.
- 로그아웃 시 `queryKeys.me.all`을 무효화하도록 회원 데이터 key는 `me` 아래에 둔다.

**04 경기 상세**

- `app/services/top_matches.py`는 현재 `pending` 고정 반환이고 기존 계약은 5가지 처리 상태다. **04 보완 대상:** 주별 작업 상태와 공개 결과를 분리하고 대상 주/표시 결과 소속 주·공개 버전을 관리한다. 00:00/00:05 자동 최대 2회, 지난주 결과 유지, 두 번째 실패의 지연 안내·운영 알림·관리 명령 수동 복구를 구현한다. 정상 결과는 검증 후 한 번에 게시하고 성공한 주간 결과 재생성·늦은 이전 시도 덮어쓰기를 막는다. 사용자 UI 3종에 맞춘 계약·생성 타입·화면과 Figma를 함께 보완하고 실제 실행으로 검증한다.
- 경기 상세(`/matches/[id]`)를 만들 때 TOP 5 행 선택 후 상세 제목으로 포커스를 옮긴다(Figma `168:348` '접근성'). 01 띠는 행을 누르면 펼침을 닫고 이동만 한다.
- 선정 후 일정이 바뀐 항목의 '변경 일시'는 §10.3 D-01-10 결정에 따라 계약 필드(예: 선정 당시 킥오프)를 추가할지 정한다.
- TOP 5는 P-06의 2026-11-02 정책을 따른다. 주간 KST 예정 경기·여섯 입력·뉴스/회원 평가 미사용·공개 후 ID/순서/이유 고정은 유지한다. 새 주 첫 시도/재시도 중 지난주 결과의 실제 제목·기간·시각을 유지하며 후보 0건 확인만 경기 없음으로 공개한다. 5개 미만·경기 상태 변경은 별도 화면이 아닌 목록 데이터다.
- 공개 버전이 바뀌면 열린 브라우저가 완료/버전 변경을 감지해 해당 쿼리를 재조회해야 한다. 서버에서 캐시만 지우거나 프런트의 기존 30분 주기에 맡기는 것만으로 즉시 반영을 구현했다고 보지 않는다. 조회 실패 시 기존 공개 결과를 유지하고, 서버의 재실패 공개 상태가 전달되면 지연 안내로 바꾼다. 사용자 조회로 AI 작업을 실행하지 않는다.
- 후기 작성 주의사항은 정보 아이콘·툴팁이 아니라 화면에 바로 보이는 UI로 제공한다(사용자 기준, 2026-11-01). 01에서 만들었던 `Tooltip`은 쓰이지 않아 삭제했으므로, 숨겨진 안내가 필요해지면 그때 요구에 맞춰 새로 만든다.
- (03에서) 경기 데이터는 `fixtures`에 있다. 단일 경기 응답은 `app/services/fixtures.py`의 `to_summary()`를 재사용하고, `MatchSummary`에서 예정·연기·취소 경기의 스코어는 항상 `null`(제공사 0-0 자리값 무시), `timeConfirmed`는 `TBD`·`PST`에서 `false`, `statusReason`은 제공사에 사유 필드가 없어 현재 항상 `null`이다. `fixture_events`는 메인에서 쓰지 않아 03이 만들지 않았다 — 04가 이벤트·상세 블록 테이블과 함께 만든다.
- (03에서) TOP 5 상태 표기는 `MatchStatusBadge size="small"`로 바꿨다. 진행 중 표기는 개정 Figma(`187:591`) 기준 '진행 중 63′', 예정은 회색이다. `top-matches` 응답의 `meta.updatedAt`은 아직 `null`이다 — 04가 선정 경기의 `fixtures.synced_at` 최대값으로 채운다.
- (03에서) `MatchCard`는 `prefetch={false}`로 `/matches/[id]`를 연다. 위 '동적 경로와 루트 레이아웃' 공통 규칙을 먼저 처리한다.

**05 지난 경기**

- (03에서) `CompetitionFilter`·`TeamSearch`·`MatchCard`를 재사용한다. 지난 경기·이전 시즌 Figma(`53:593`·`61:883`)도 같은 대회 선택 UI다. 필터 URL 처리는 `src/features/schedule/useScheduleParams.ts`처럼 팀·대회 변경은 `router.push`(뒤로가기 단계), 날짜 이동은 `replace`로 맞춘다. 팀 검색 API는 현재 시즌 후보만 찾으므로 `season` 범위(해당 시즌 참가 팀, 상세 미제공 팀 포함)를 추가한다. 과거 시즌 경기 적재 시 `app/services/fixtures.py`의 `upsert_fixtures()`(팀·참가 기록 함께 저장)를 재사용하면 된다.

**06 리그 순위**

- (03에서) 메인 간소 순위 자리는 비워 두었다. `app/page.tsx` 그리드의 오른쪽 열(`FavoriteSchedule` 아래, 모바일은 뉴스 다음 — Figma `49:368`·`49:848`)에 넣는다. 5대 리그 팀 목록·`team_competition_seasons`는 `reference` 작업이 매일 갱신한다.

**07 팀 탐색**

- (03에서) `<FavoriteToggle teamId teamName />`를 팀 행에 두면 메인 관심 팀 일정·버튼이 바로 반영된다(같은 저장소 구독). 메인의 '관리'·'팀 탐색에서 등록'은 `/teams`로 연결돼 있다. 팀 목록은 `team_competition_seasons`(현재 시즌 5대 리그) + `teams.name_ko`를 쓰면 된다.

**08 팀 상세**

- (03에서) 팀 뉴스는 `news_article_teams`(명확한 별칭으로 연결된 기사)에 이미 쌓인다. `GET /news`에 `team` 조건을 추가하고 `NewsCard`로 목록을 만든다. 메인 뉴스는 대회 뱃지가 있는 기사만 보여주며, 팀만 연결되고 뱃지가 없는 기사는 팀 상세에서만 쓴다. 관심 팀 버튼은 `FavoriteToggle` 재사용.

## 4. 기능 구현·검수·설계 변경 흐름

기능 작업은 **가이드·관련 코드 확인 → 범위와 작업 구상 정리 → 프런트엔드·백엔드 구현 → Claude 자체 검수 → Codex 교차 검증 → Claude 보완 → 필요한 범위 재검증** 순서로 진행한다. Claude 자체 검수만으로 교차 검증 완료를 표시하지 않는다.

기존 인증·DB·외부 API·공통 UI를 재사용하고 공유 계약(API 응답, DB 테이블, 공통 컴포넌트 props)을 바꾸면 영향을 받는 기능과 이 가이드도 반영한다. 단순한 내부 구현 선택은 기존 구조에 맞춰 진행하되, 사용자 동작·화면·권한·데이터 정책이 기존 설계와 달라져야 한다면 변경 이유·대안·영향·수정할 기획/디자인 항목을 정리한다. Codex 검토와 필요한 사용자 결정 후 기획 문서·디자인·가이드에 반영하고 변경된 기준으로 구현한다. 미확정 정책(§10)은 임의로 정하지 않고 "제공 보류" 상태로 구현한다.

**작업 원칙(사용자 결정 2026-11-01) — 모든 기능 채팅이 반드시 지킨다**

1. **작업 순서(사용자 결정 2026-11-01):** 01 헤더·푸터(재검수) → 03 경기 일정 → 04 경기 상세 → 05 지난 경기 → 06 리그 순위 → 07 팀 탐색 → 08 팀 상세 → 02 로그인·회원가입 → 09 마이페이지. 각 작업은 **새 채팅**에서 진행한다. 08까지 비회원 기준으로 서비스 전체를 이용할 수 있게 만든 뒤 02·09로 넘어간다. 작업마다 Codex 교차 검증을 받고 00 채팅에서 확인·조율한 뒤 다음 작업으로 간다.
2. **한 작업 안에서 끝낸다:** 각 작업은 담당 화면의 프런트엔드·백엔드·DB·외부 연동을 모두 실제로 동작하게 만든 뒤 마친다. 다음 작업과 이어지는 부분은 다음 작업이 바로 쓸 수 있는 사전 작업(인터페이스·자리)까지만 만들고 §3.1에 인수인계한다.
3. **"완료"는 실제로 동작할 때만 쓴다:** 자리 표시·모의 구현·콘솔 출력·"설정하면 동작함"은 완료가 아니다. 예: 인증 메일이 실제 메일함에 도착하지 않으면 회원가입은 미완료다. 외부 계정·비밀 값·사용자 결정이 없어 막히면 상태를 **"차단됨 — 필요한 것: …"**으로 보고하고 완료라고 쓰지 않는다.
4. **실제 실행으로 자체 검수한다:** 자동 테스트 통과와 별개로, 백엔드·프런트엔드를 실제로 띄우고 실제 DB·외부 연동으로 담당 사용자 흐름을 브라우저에서 처음부터 끝까지 직접 수행한다. 수행한 흐름·결과(성공/실패)를 완료 보고에 목록으로 적는다. 실행하지 않은 흐름은 "미실행"으로 표시한다.
5. **범위 밖 코드는 만들지 않는다:** 담당 화면에서 실제로 쓰지 않는 컴포넌트·옵션·추상화를 "나중을 위해" 만들지 않는다. 교차 검증 전에 쓰이지 않는 코드를 지운다. 교차 검증에서 쓰이지 않는 코드의 결함이 나오면 고치지 말고 삭제한다.
6. **교차 검증 전에 결함을 줄인다:** Codex에 넘기기 전에 §4 완료 조건을 항목별로 스스로 대조해 표로 남긴다(충족·미충족·해당 없음). 미충족 항목이 있으면 넘기지 않는다.

**기능 완료 조건(공통)**

1. 담당 기능 ID의 정상 처리·예외 처리·완료 및 검증 조건(기능 명세서)과 관련 통합 인수 기준(기능 명세서 6.2)을 충족한다.
2. 로딩·빈 결과·일부 미제공·조회 실패·권한 거부 상태를 구분해 보여준다. 누락값은 `null`로 전달하고 화면에서 '미제공' 또는 '—'로 표시한다.
3. 데스크톱·모바일(375px) 배치를 Figma 기준으로 확인한다. 접근하지 못한 프레임은 미확인으로 남긴다.
4. 백엔드 `uv run ruff check .`, `uv run python -m pytest`, 프런트엔드 `npm run lint`, `npm run build`가 통과한다. 새 API·서비스 로직에는 테스트를 추가한다.
5. 새 테이블은 Alembic 마이그레이션으로만 만들고 `upgrade`·`downgrade`를 개발 DB에서 확인한다.
6. 실제 외부 API 호출은 필요한 최소 횟수만 실행하고 횟수를 완료 응답에 적는다. 담당 기능이 외부 연동(메일·축구 API·뉴스 API)을 쓰면 실제 연동으로 1회 이상 끝까지 확인한다.
7. 위 작업 원칙 4번의 실제 실행 흐름 목록과 6번의 완료 조건 대조표를 완료 보고에 포함한다.
8. 완료 응답에 구현 범위·관련 경로·검사 결과·실제 API/DB 연동 여부·미확인 사항을 남기고, 이 가이드 §3과 바뀐 공통 인터페이스를 갱신한다.

모든 기능을 마치면 페이지 간 이동, 인증 후 복귀, 관심 팀·후기·북마크의 화면 간 반영, 시즌 전환, 외부 API 실패 등 연결 흐름을 전체 검수한다. **터치·펜 실기기와 스크린리더 검사도 이 단계에서 일괄 진행한다**(사용자 결정 2026-11-01). 기능 채팅 단계에서는 실기기 미검사를 완료 차단 사유로 삼지 않고, 접근성 이름·의미 있는 마크업·키보드 포커스 등 필요한 구현을 갖추는 데 집중한다. **Claude 전체 최종 검수 → Codex 교차 검증 → Claude 보완 → 최종 재검증** 후 Codex의 배포 작업으로 넘긴다.

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
| 메일 발송 | `EmailSender` 인터페이스 + **SMTP 구현**(§10 P-01). SMTP 설정이 있으면 로컬을 포함한 모든 환경에서 실제 메일을 보낸다. 콘솔 출력 구현은 SMTP 설정이 없는 로컬 자동 테스트용으로만 남기며, 콘솔 출력 상태는 회원가입 '완료'로 보지 않는다. 인증번호를 로그에 남기는 것은 콘솔 구현에서만 허용 |
| 가입 직후 로그인 | 가입 API가 계정 생성과 쿠키 발급을 한 트랜잭션 흐름으로 처리하고, 프런트엔드는 `GET /api/v1/auth/me`로 세션 성립을 확인한 뒤에만 회원 상태로 표시한다(계정 생성 성공과 인증 성립 구분) |
| 로그아웃 | 서버에서 갱신 토큰 폐기 + 쿠키 삭제 후 `/auth/me`로 비회원 확인. 공개 페이지는 유지, 회원 전용 페이지는 메인 이동. localStorage 관심 팀 복원(COM-005) |
| 로그인 복귀 | `/login?returnTo=<내부 경로>&intent=<review:경기ID \| bookmark:기사ID>`. `returnTo`는 `/`로 시작하는 내부 경로만 허용(오픈 리다이렉트 방지). 평가 intent는 평가 입력 UI를 열고, 북마크 intent는 카드 위치로만 복귀하며 자동 저장하지 않는다 |
| 소셜 로그인 | (사용자 확정 2026-11-01) 초기에는 이메일 가입만 구현한다. `auth_identities` 테이블로 카카오·구글을 앱 등록 후 추가할 수 있게 구조만 둔다. 같은 이메일의 계정을 자동 연결하지 않는다(§10 P-02) |

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
| 회원 | `users`(id uuid, email citext unique, nickname unique, password_hash NULL 허용, login_method, created_at), `auth_identities`, `refresh_tokens`(token_hash, family_id, expires_at, revoked_at), `email_verifications`, `terms_agreements`(user_id, terms_version, agreed_at), `favorite_teams`(user_id, team_id, created_at, PK(user_id, team_id)) | 02 |
| 기준 데이터 | **03 구현(`0003_reference_data`):** `competitions`(id, group_key, type league/cup/uefa, name_en, name_ko, short_name, sort_order, active, logo_url), `competition_seasons`(competition_id, season, label, is_current, availability available/no_data, start/end_date, teams_synced_at, fixtures_synced_at, fixtures_failed_at), `teams`(id, name_en, name_ko, logo_url, country), `team_competition_seasons`(team_id, competition_id, season), `team_aliases`(team_id, alias, normalized, lang, ambiguous, for_search, for_news). `image_assets`는 권리 확보 자산이 생길 때(V-10) 만든다 — 그 전 `IMAGE_RIGHTS_ENFORCED=true`면 모든 이미지가 대체 이미지 | 03 |
| 경기 | **03 구현(`0004_fixtures`):** `fixtures`(id, competition_id, season, round, kickoff_at, kickoff_date_kst, status, finish_type, status_short_raw, status_long_raw, status_reason, elapsed, home/away_team_id, goals_home/away, score jsonb, venue_name/city, synced_at). `fixture_events`·`fixture_details`(fixture_id, statistics/lineups/players jsonb, fetched_at)는 04 | 03(목록·상태) / 04(이벤트·상세 블록·상대 전적) |
| 뉴스 | **03 구현(`0005_news`):** `news_articles`(id, url_hash unique, url, source_domain, title, description, published_at, badge, fetched_at, expires_at), `news_article_teams`(article_id, team_id). 언론사명 매핑 표(`news_sources`)는 만들지 않았다(§10.3 D-03-1). `bookmarks`(user_id, article 식별 키, 제목·설명·출처·뱃지 스냅샷, created_at, unique(user_id, 식별 키))는 02 | 03·02 |
| 경기 상세 | `head_to_head`(fixture_id, payload jsonb, last_meeting_fixture_id, fetched_at), `reviews`(id, user_id, fixture_id, rating 1~5, body ≤300 NULL 허용, created/updated_at, unique(user_id, fixture_id)), `review_reactions`(review_id, user_id, value ±1, PK), `weekly_top_matches`(week_start, rank, fixture_id, method, computed_at) | 04 |
| 순위 | `standings`(competition_id, season, team_id, rank, points, played, w/d/l, gf, ga, form, description, group), `player_rankings`(competition_id, season, type, rank, player_id, team_id, value), `players`, `player_season_stats`(player_id, team_id, competition_id, season, 주요 지표 컬럼 + 원본 jsonb) | 06 |
| 팀 상세 | `squad_members`(team_id, season, player_id, number, position), `team_season_stats`(team_id, competition_id, season, payload jsonb), `transfers`(player_id, date, team_in_id, team_out_id, type_raw, season, half, frozen) | 08 |

관심 팀 5개 제한·후기 1인 1건·반응 1인 1건은 DB 제약(unique)과 서비스 검증(트랜잭션 안에서 개수 확인)으로 함께 보장한다. 회원 탈퇴 시 연관 데이터는 §10 P-03 확정안대로 처리한다(사용자 확정 2026-11-01): 관심 팀·북마크·후기 반응·후기는 삭제(외래 키 `ON DELETE CASCADE`, 후기는 평점 집계에서도 빠짐), 의견은 `feedback.user_id`만 `NULL`로(`ON DELETE SET NULL`). 각 테이블을 만드는 채팅(02 북마크, 04 후기·반응)이 같은 규칙으로 외래 키를 건다.

### 6.4 백엔드 API 형식

- 경로 접두사 `/api/v1`. 리소스 이름은 복수형 kebab-case. 상태 확인 `/health`는 유지한다.
- JSON 필드는 camelCase(Pydantic `alias_generator=to_camel`, `populate_by_name=True`). 시각은 ISO 8601 UTC(`2026-10-31T19:00:00Z`), 경기 묶음 날짜는 `kickoffDateKst: "2026-11-01"`처럼 별도 제공. 시간대 표기는 화면에 하지 않는다.
- **성공:** `{ "data": <객체|배열>, "meta": { ... } }`. 목록은 `meta.page`, `meta.size`, `meta.total`(페이지 방식) 또는 `meta.nextCursor`(뉴스 더 보기). 수집 데이터는 `meta.updatedAt`(마지막 수집 시각)을 넣는다.
- **오류:** `{ "error": { "code": "FAVORITE_LIMIT", "message": "관심 팀은 최대 5개까지 등록할 수 있습니다.", "details": { } } }`. 메시지는 화면에 그대로 써도 되는 한국어. 내부 예외·SQL·외부 응답 원문은 응답과 서버 로그 어디에도 노출하지 않는다(미처리 예외는 종류만 기록).

| HTTP | code | 용도 |
| --- | --- | --- |
| 400/422 | `VALIDATION_ERROR` | 입력 형식 오류(`details.fields`에 항목별 사유) |
| 401 | `AUTH_REQUIRED` / `AUTH_EXPIRED` / `INVALID_CREDENTIALS` | 미인증 / 접근 토큰 만료(갱신 시도 대상) / 로그인 실패 |
| 403 | `FORBIDDEN` | 소유권 없음, CSRF 헤더 누락 |
| 404 | `NOT_FOUND` / `TEAM_DETAIL_UNAVAILABLE` | 없는 식별자(다른 데이터로 대체하지 않음) / 현재 상세 미제공 팀 |
| 409 | `CONFLICT`, `EMAIL_TAKEN`, `NICKNAME_TAKEN`, `FAVORITE_LIMIT`, `REVIEW_EXISTS`, `FEEDBACK_DUPLICATE`(01) | 중복·제한 |
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
| `AWD` / `WO` | finished | finishType awarded / walkover. 평가 제공 보류(§10 P-05). TOP 신규 후보 제외·이미 선정된 항목 유지 |
| `PST` | postponed | 같은 경기 ID로 새 일시 반영 |
| `CANC` | cancelled | 실제 데이터에 `Canc`·`CANC` 혼재 |
| `ABD` | abandoned | '경기 중단', 중단 시점 스코어, 평가 보류. TOP 신규 후보 제외·이미 선정된 항목 유지 |
| 그 밖 | unknown | '확인 필요' |

- **팀 참조 공통 형태(`TeamRef`):** `{ "id", "nameKo": string | null, "nameEn", "crestUrl": string | null, "detailAvailable": true | false | null }`. 한국어 이름이 없으면 `nameKo`는 `null`이고 화면은 `nameEn`을 쓴다(`CompetitionRef.nameKo`도 같음). `null`은 소속 미확인(조회 중·실패)이며 강등으로 표시하지 않는다(D-15).
- **경기 요약 공통 형태(`MatchSummary`):** 경기 카드·TOP 5·팀 경기 목록이 같은 형태를 쓴다. `{ "id", "competition": { "id", "nameKo", "shortName" }, "kickoffAt", "kickoffDateKst", "timeConfirmed", "status", "finishType", "elapsed", "statusReason", "home": TeamRef, "away": TeamRef, "score": { "home", "away", "penaltyHome", "penaltyAway" } }`. 스코어·경과 시간이 없으면 `null`. 01이 스키마를 먼저 정의하고 03이 실제 데이터로 채운다(예정·연기·취소는 스코어 `null`, `elapsed`는 진행 중에만, `timeConfirmed`는 `TBD`·`PST`에서 `false`, 승부차기만 `penaltyHome`·`penaltyAway`). 필드를 바꾸면 이 줄을 갱신한다.
- **메인 일정 응답(03):** `GET /competitions` → `data: [{ id, nameKo, shortName, group: EPL\|LaLiga\|SerieA\|Bundesliga\|Ligue1\|UEFA, currentSeason: { season, label, availability: available\|no_data } \| null }]`. `GET /fixtures?date=YYYY-MM-DD`(KST, 기본 오늘, 수집 범위 오늘−1~+15일 밖은 422) → `data: MatchSummary[]`(지원 14개 대회 전체, 킥오프·대회 순), `meta: ScheduleMeta { updatedAt, failedCompetitionIds }` — 대회·팀 필터는 화면에서 적용(날짜 빈 결과와 필터 빈 결과 구분). 한 번도 수집되지 않았거나 모든 대회가 실패하고 결과가 없으면 503 `UPSTREAM_UNAVAILABLE`, 일부 대회만 실패하면 200 + `failedCompetitionIds`. `GET /fixtures/next?teams=1,2`(양의 정수 1~5개, 아니면 422) → `data: { teams: TeamRef[], matches: MatchSummary[] }`(팀마다 진행 중 또는 가장 가까운 예정 1경기, 진행 중 우선, 맞대결 1회), `meta: ScheduleMeta`. `GET /fixtures/team?team=<id>`(03 일정 UX 후속) → `data: TeamSchedule { team: TeamRef, start, end, matches: MatchSummary[] }`(오늘~오늘+13일 KST의 저장된 해당 팀 경기 전체, 킥오프 순, 외부 API 호출 없음), `meta: ScheduleMeta`. 대회 조건은 화면에서 적용, `failedCompetitionIds`는 화면이 '일부 대회 확인 실패'·'일정 없음 단정 금지'에 쓴다. 팀 ID 형식 오류 422, 없는 팀 404, 한 번도 수집 안 됨 503. `GET /teams/search?q=`(1~40자) → `data: TeamRef[]`(최대 10개). `GET /news?badge=&cursor=&size=`(size 1~24, 기본 6) → `data: NewsItem[] { id, badge, title, description \| null, url, sourceDomain, publishedAt }`, `meta: NewsMeta { nextCursor, updatedAt, stale }`(저장 기사도 없고 수집이 실패·미실행이면 503). `GET /news/{id}/link` → `data: { url, status: reachable\|gone\|unknown }`(원문 HEAD→GET 헤더 1회 확인, 404/410만 gone, 요청 제한 IP별 분당 30회·전체 300회).
- **TOP 5 현재 코드 계약(01 구현 이력):** `GET /api/v1/top-matches/current`는 `week`, `state: ready|pending|no_candidates|source_error|ai_error`, `selectedAt`, `items[rank,reason,match]` 형태이며 04 전까지 현재 주 `pending`을 반환한다. **2026-11-02 변경 대상:** 공개 UI는 목록·경기 없음·지연 3종으로 정리하고 작업 내부 상태는 분리한다. 대상 주와 실제 표시 결과의 소속 주·선정 시각·공개 버전을 식별해야 한다. 첫 시도/재시도 중 지난주 결과를 서버에서 제공하고, 새 주 정상 공개나 두 번째 실패 지연 상태로 한 번에 전환한다. **담당은 04(사용자 결정 2026-11-02)**: 04가 새 필드명을 정해 스키마·생성 타입·띠/패널 화면(Figma `159:923`·`159:924`의 list·none·delayed, 지난주 표시 PreviousNotice)·새 정책 안내 문구·공개 버전 변경 감지를 한 번에 반영하고 이 줄을 갱신한다. 04 전까지는 01 구현(`pending` → '선정 중' 표시)을 그대로 두며, 출시 전 개발 화면이므로 01을 다시 열지 않는다. 기존 `current_kst_week()`로 표시 결과의 과거 소속 주를 덮어쓰지 않는다. 경기 ID/순서/이유 고정·최신 `MatchSummary` 연결은 유지한다.
- **일정 UX 팀 14일 조회(2026-11-02, 03 구현):** 위 `GET /fixtures/team`이다. URL은 `/?team=50&competitions=45&date=2026-11-05` — 팀 모드에서 `date`는 해제 시 돌아갈 날짜로 유지하고, 해제(팀 검색 해제·× 버튼·입력 전체 삭제·관심 팀 버튼 재클릭)는 `team`만 지워 그 날짜·막대 위치와 현재 대회로 복귀한다. 전체 초기화는 `/`(오늘·전체·팀 없음, 관심 팀 유지). 팀·대회 변경은 history push, 날짜 이동은 replace. 자정 기준일 변경: `useScheduleParams`의 `useKstToday()`가 다음 KST 자정(+1초)과 탭이 다시 보일 때 오늘을 다시 계산해 날짜 막대·'오늘'·날짜 미지정 보기를 새 날짜로 옮기고, 팀 조회 키(`fixtures.team(teamId, today)`)가 바뀌어 새 14일을 다시 조회한다. 팀 모드의 기간 표기는 응답의 `start`·`end`(서버 KST 기준)를 써서 표시 경기와 항상 일치한다. 브라우저 시계를 자정 직후로 바꿔 확인했고 실제 자정 경과는 미확인. 생성 타입 `TeamSchedule`·`TeamScheduleResponse` 반영.
- **프런트엔드 타입:** 백엔드 OpenAPI(`/openapi.json`)에서 `openapi-typescript`로 `src/lib/api/schema.d.ts`를 생성한다(`npm run gen:api`). 손으로 타입을 중복 작성하지 않는다.

**초기 엔드포인트 목록(담당 채팅이 세부를 확정하고 이 표를 갱신)**

| 구분 | 엔드포인트 | 담당 |
| --- | --- | --- |
| 공통 | `GET /api/v1/top-matches/current`, `POST /api/v1/feedback`(요청 `{ body, type: bug·suggestion·other, pagePath? }`, 유형 필수(사용자 결정 2026-10-31), 본문 앞뒤 공백 제거 후 1~1,000자, 성공 201 `{ data: { id, createdAt } }`) — 01 구현 | 01 |
| 인증 | `POST /auth/email-codes`, `POST /auth/email-codes/verify`, `POST /auth/signup`, `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout`, `POST /auth/password-reset`, `GET /auth/me` | 02 |
| 계정·관심 팀 | `PATCH /me/password`, `DELETE /me`, `GET /me/favorites`, `POST /me/favorites`, `DELETE /me/favorites/{teamId}` | 02 |
| 기준·일정 | `GET /competitions`, `GET /fixtures?date=`, `GET /fixtures/next?teams=`, `GET /fixtures/team?team=`, `GET /teams/search?q=` — 03 구현(§6.4 메인 일정 응답). 실시간은 같은 `GET /fixtures` 폴링으로 처리해 `/fixtures/live`는 만들지 않았다. 05가 `/teams/search`에 시즌 범위를 추가 | 03 |
| 뉴스·북마크 | `GET /news?badge=&cursor=&size=`, `GET /news/{id}/link`(03 구현, `team` 조건은 08이 추가), `GET /me/bookmarks`, `POST /me/bookmarks`, `DELETE /me/bookmarks/{id}`(02, 연기) | 03·02 |
| 경기 상세 | `GET /fixtures/{id}`, `GET /fixtures/{id}/detail`, `GET /fixtures/{id}/head-to-head`, `GET /fixtures/{id}/reviews?sort=popular\|latest`, `POST /fixtures/{id}/reviews`, `PATCH·DELETE /reviews/{id}`, `PUT·DELETE /reviews/{id}/reaction`, `GET /me/reviews` | 04 |
| 지난 경기 | `GET /results?season=&competitions=&team=&page=` | 05 |
| 순위 | `GET /standings?league=&season=`, `GET /standings/summary`, `GET /player-rankings?league=&season=&type=goals\|assists\|yellow\|red\|saves` | 06 |
| 팀 | `GET /teams?league=&q=&page=`(07), `GET /teams/{id}`, `/teams/{id}/fixtures`, `/teams/{id}/squad`, `/teams/{id}/season-stats?season=`, `/teams/{id}/transfers?season=` | 07·08 |

### 6.5 외부 데이터 수집·캐시

- **클라이언트:** `app/providers/api_football.py`(01 작성, 03 수집 작업은 `get()`을 그대로 사용)와 `app/providers/naver_news.py`(03). 키는 `SecretStr`에서 요청 직전에만 꺼내고 헤더·URL·키를 로그에 남기지 않는다. `../api-test/tests/api_client.py`(로컬 전용)의 안전 장치(HTTP 200 + `errors` 실패 처리, 쿼터 헤더 기록, 요청 간격)를 참고한다.
- **호출 한도 보호:** 공용 속도 제한기(분당 250회 이하로 운영, Pro 한도 300회), 일일 예산 경계(기본 7,000회에서 신규 수집 중단), 타임아웃 10초, 5xx·네트워크 오류는 최대 2회 지수 백오프 재시도 후 중단. 무제한 자동 재시도·폴링 금지. 호출 수는 `sync_runs`에 기록한다.
- **쓰기 규칙:** 실패 응답으로 기존 정상 데이터를 덮어쓰거나 지우지 않는다. 정상 빈 응답과 오류를 구분해 기록한다(COM-004, CMP-004).
- **수집 작업:** `app/sync/<job>.py`의 멱등 함수 + CLI(`uv run python -m app.sync <job> [옵션]`). 자동 실행은 백엔드 프로세스 안의 APScheduler로 하되 `SCHEDULER_ENABLED=true`인 인스턴스 하나에서만 켠다. 같은 작업이 겹치지 않도록 PostgreSQL advisory lock을 쓴다. 배포 환경의 스케줄 방식은 Codex 배포 단계에서 바꿀 수 있게 작업 함수와 실행기를 분리한다.
- **요청 시 보충 조회:** 경기 상세·상대 전적처럼 사용자가 열었을 때 처음 필요한 데이터만 "DB 확인 → 없거나 만료면 외부 조회 1회 → 저장" 방식을 쓴다. 같은 키의 동시 요청은 하나로 합친다.

| 작업 | 초기 주기(실측 후 조정) | 담당 |
| --- | --- | --- |
| 대회·시즌·팀·허용 집합 | **03 `reference`:** 매일 04:00 KST + 수동. `/leagues?id=` 14회 + `/teams?league=&season=` 8회(5대 리그 + UEFA 3개, UEFA는 뉴스 주제 판정용) = 22회. 끝에 별칭 시드 적용. 별칭만 다시 넣을 때 `team_aliases`(0회) | 03 |
| 현재 시즌 경기 목록(오늘−1일 ~ +15일) | **03 `fixtures`:** 30분, 대회마다 `/fixtures?league=&season=&from=&to=&timezone=UTC` 1회(14회). 실패한 대회는 기존 행 유지 + `fixtures_failed_at` 기록 | 03 |
| 실시간 경기 | **03 `fixtures_live`:** 60초 주기지만 진행 중·30분 내 시작·킥오프 후 3시간 내 미시작 경기가 없으면 사전 확인에서 건너뜀(호출·기록 0). 실행 시 `/fixtures?live=<지원 대회>` 1회 + 라이브 응답에 없는 추적 경기만 `/fixtures?ids=`(20개당 1회)로 재조회(종료로 가정하지 않음) | 03 |
| 경기 상세 블록 | 종료 전환 시 1회 + 요청 시 보충, 진행 중은 실시간 주기에 맞춤 | 04 |
| 상대 전적 | 경기당 1회, 두 팀이 새로 맞붙은 뒤에만 갱신 | 04 |
| 순위 | 경기일 1시간, 그 외 하루 1회 | 06 |
| 선수 순위·선수 시즌 기록(선방 집계) | 하루 1회 | 06 |
| 선수단·팀 시즌 기록 | 하루 1회 | 08 |
| 이적 | 매일 00:00 KST, 시즌 종료 후 6/30까지 갱신 후 고정 | 08 |
| 뉴스 | **03 `news`:** 30분, 네이버 검색 8개 검색어(프리미어리그·라리가·세리에A·분데스리가·리그앙·챔피언스리그·유로파리그·컨퍼런스리그) × 최신 100건 = 8회. 게시 후 `NEWS_RETENTION_HOURS`(기본 72) 지난 기사는 저장하지 않고 삭제 | 03 |
| TOP 5 선정 | KST 월요일 00:00 첫 시도·실패 시 00:05 한 번 재시도. 자동 최대 2회. 재실패는 자동 중단·운영 알림·지연 안내·관리 명령 수동 복구. 공개 전 지난주 유지·정상 검증 후 버전 교체 | 04 |

- **자동 실행(03):** 위 03 작업은 `SCHEDULER_ENABLED=true`인 백엔드 인스턴스 하나에서만 자동 실행된다(로컬 기본 false — 개발 중에는 `uv run python -m app.sync <job>`으로 수동 실행). 예상 일일 호출: 경기 목록 672회 + 실시간(경기 시간대만, 1~2회/분) + 기준 22회, 네이버 384회.
- **2025 시즌 과거 데이터:** 05가 적재 작업을 만든다. `../api-test/results/raw/`의 2025 원본 응답을 우선 가져와 재호출을 줄이고, 빠진 항목만 API로 보충한다. 원본 파일은 로컬 전용이므로 운영 서버에서는 API 적재 경로를 쓴다.
- **실시간 화면 갱신:** 웹소켓 없이 클라이언트 폴링(진행 중 경기가 화면에 있을 때 30~60초)으로 한다. 화면에 마지막 갱신 시각을 표시한다. **03 구현:** `src/features/schedule/queries.ts`의 `liveRefetchInterval()` — 진행 중·시작 30분 전~킥오프 후 3시간 미시작 경기가 있으면 60초, 없으면 목록의 다음 경기가 그 구간에 들어서는 시각에 1회 재조회한 뒤 60초 폴링으로 전환, 숨김 탭에서는 멈춤. 재조회가 실패해도 이미 보인 목록은 유지하고 '최신 일정으로 갱신하지 못했습니다'를 함께 표시한다(일정·관심 팀·뉴스 공통). 실제 경기 시간 검증(V-04) 전에는 지연 시간을 보장한다고 안내하지 않는다.
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
- **요청 상태 표준:** 모든 데이터 영역은 `DataState`(`status`: `loading`·`ready`·`empty`·`partial`·`error`(+`onRetry`)·`denied`(회원 전용, `deniedAction`에 로그인 유도))로 감싼다. 빈 결과 문구와 실패 문구를 구분한다.
- **스타일:** Tailwind CSS v4. Figma의 색·글꼴·간격·반경을 `globals.css`의 `@theme` 토큰으로 정의하고 컴포넌트에서 임의 색상값을 직접 쓰지 않는다. `<html lang="ko">`.
- **Figma 디자인 기준(컬러 가이드·개발 전달 기준에서 확인):**
  - 레이아웃: 시안은 데스크톱 1920px·모바일 375px. 콘텐츠·헤더·푸터 내부는 최대 1280px 중앙 정렬의 유동 컨테이너. 1024px 미만은 메뉴 접기·1열 전환, 작은 화면 좌우 24px, 모바일 16px.
  - 서체·크기: Noto Sans KR. 본문 14px/22px 이상, 보조 설명 12px/20px 이상. 모바일 조작 영역 44px 이상.
  - 간격·반경: 4·8·12·16·24·32·48px, 버튼 반경 8px, 카드 반경 16px. 포커스는 3px 외곽선.
  - 색상 토큰: `bg/canvas #F8FAFC`, `bg/surface #FFFFFF`, `bg/subtle #F1F5F9`, `bg/selected #EFF6FF`, `text/primary #0F172A`, `text/secondary #475569`, `text/muted #64748B`, `text/inverse #FFFFFF`, `action/primary #2563EB`, `action/hover #1D4ED8`, `action/soft #DBEAFE`, `action/disabled #E2E8F0`, `border/default #E2E8F0`, `border/strong #CBD5E1`, `border/focus #93C5FD`, `status/live #047857`, `status/live-bg #ECFDF5`, `status/warning #B45309`, `status/warning-bg #FFFBEB`, `status/error #B91C1C`, `status/error-bg #FEF2F2`, `brand/key #EFF6FF`, `brand/arrow #2563EB`, `brand/rim #CBD5E1`(01에서 Figma 46:258·96:412 값으로 정정). 블루는 주요 동작·선택·링크에만 쓰고, 진행 중·주의·오류는 색과 상태명을 함께 표시한다.
  - 로고: 80×48 비율 심벌(`55:22`) + 워드마크(10px 간격). 높이 헤더 데스크톱 36px·모바일 32px, 푸터 24px.
  - 헤더: 로고와 메뉴 사이 32px, 메뉴 간격 32px, 로그인·회원가입은 오른쪽. **의견 보내기는 데스크톱 푸터와 모바일 하단 고정 영역에 둔다**(떠 있는 전역 버튼 아님). 모바일은 헤더 메뉴 버튼으로 메뉴·로그아웃을 연다.
  - 필터: 문자 기호 대신 16px 벡터 화살표, 텍스트와 8px 간격. 후기 반응은 16px 엄지 아이콘.
  - 경기 기록: 데스크톱·모바일 모두 타임라인 / 팀 통계 / 라인업 / 선수 평점 4탭. 제공사 선수 평점과 회원 경기 평점을 분리.
  - 푸터: 서비스 소개·이용약관·개인정보처리방침·문의 링크, 운영자 정보, 데이터·뉴스 출처와 권리 고지. 시안의 운영자·주소·이메일은 가상 정보이므로 설정값 또는 자리 표시로 구현한다.
  - 시안의 경기·선수 수치는 샘플이다. 실제 응답을 쓰고 미제공 값은 —로 표시한다.
- **코드의 토큰 이름(01):** `src/app/globals.css`의 `--kt-*` 변수(Figma 변수명)와 Tailwind 유틸리티 `bg-canvas`·`bg-surface`·`bg-subtle`·`bg-selected`, `text-fg`·`text-fg-secondary`·`text-fg-muted`·`text-fg-inverse`, `bg-action`·`hover:bg-action-hover`·`bg-action-soft`·`bg-action-disabled`, `border-line`·`border-line-strong`, `live`·`warning`·`error`(+`-bg`). 글자 `text-2xs`(10)·`text-caption`(11)·`text-small`(12)·`text-label`(13)·`text-body`(14)·`text-lead`(16)·`text-title`(20)·`text-heading`(28), 반경 `rounded-badge`(4)·`rounded-control`(8)·`rounded-card`(16), 콘텐츠 폭 `kt-container`. 데스크톱 배치는 1024px(`lg:`)부터.
- **접근성:** 모달·하단 시트는 포커스 이동·Escape 닫기·포커스 복귀, 아이콘 버튼은 `aria-label`, 표는 가로 스크롤.

### 6.7 환경 변수

| 위치 | 변수 | 비고 |
| --- | --- | --- |
| 백엔드 `.env` | `API_FOOTBALL_KEY`, `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET`, `DATABASE_URL` | 설정 완료 |
| 백엔드 설정(01, 코드 기본값 있음) | `APP_ENV`(local), `CORS_ORIGINS`(CSRF Origin 허용 목록 겸용, 기본 `["http://localhost:3000"]`), `TRUSTED_PROXIES`(기본 `["127.0.0.1","::1"]`), `SCHEDULER_ENABLED`(false), `API_FOOTBALL_BASE_URL`, `API_FOOTBALL_DAILY_BUDGET`(7000), `API_FOOTBALL_PER_MINUTE`(250) | 목록 값은 JSON 배열 문자열 |
| 백엔드 `.env`(비밀, 01 추가) | `FEEDBACK_DISCORD_WEBHOOK_URL`(의견 알림 디스코드 웹후크, 비어 있으면 알림 꺼짐, §9 U-06) | 사용자가 직접 입력 |
| 백엔드 `.env`(추가 예정) | `AUTH_JWT_SECRET`(02), `SMTP_HOST`·`SMTP_PORT`·`SMTP_USERNAME`·`SMTP_PASSWORD`(비밀)·`EMAIL_FROM`(02)| 추가하는 채팅이 이 표를 갱신 |
| 백엔드 설정(03, 코드 기본값 있음) | `CURRENT_SEASON`(2026 = 2026-27), `IMAGE_RIGHTS_ENFORCED`(false), `NEWS_RETENTION_HOURS`(72, V-09 확인 후 확정), `NAVER_NEWS_BASE_URL` | `.env`에 넣지 않아도 동작 |
| 프런트엔드 `.env.local` | `BACKEND_ORIGIN`(01, 서버 전용, 기본 `http://localhost:8000`), `SITE_OPERATOR_NAME`·`SITE_OPERATOR_REPRESENTATIVE`·`SITE_OPERATOR_EMAIL`·`SITE_OPERATOR_ADDRESS`(01, 푸터 운영자 정보, 비어 있으면 '공개 전 안내') | `NEXT_PUBLIC_API_BASE_URL`은 코드·로컬 `.env.local`에서 제거 완료 |

비밀이 아닌 설정값(`BACKEND_ORIGIN`, `APP_ENV`, `SCHEDULER_ENABLED` 등)은 담당 채팅이 `.env`·`.env.local`에 직접 추가·수정할 수 있다. 이때 기존 비밀 값 줄은 읽어서 출력하거나 바꾸지 않는다. 코드에는 비밀이 아닌 설정의 기본값을 두어 변수가 없어도 로컬에서 동작하게 한다.

비밀 값은 `.env`·`.env.local`에만 둔다. `.env`·`.env.local`·`.env.example` 등 모든 `.env*` 파일은 Git에 올리지 않으며(사용자 결정), 필요한 변수 이름은 이 표로만 관리한다. 로컬의 `.env.example`은 참고용으로만 둔다. 새 비밀 값이 필요하면 사용자에게 직접 입력을 요청하고 값을 출력·기록하지 않는다.

## 7. 현재 개발 기반과 실행 방법

아래는 2026-10-31 01 채팅 완료 시점의 상태다.

| 영역 | 현재 기준 |
| --- | --- |
| 프런트엔드 | Next.js 16.4.3·React 19.3.0·TypeScript·Tailwind CSS v4. `cacheComponents`·`partialPrefetching` 켜짐. `@tanstack/react-query` 5.105.0, `openapi-typescript` 7.13.0(dev). `lang="ko"`, Noto Sans KR(로고 워드마크만 Inter). 전역 헤더·TOP 5 띠·푸터·모바일 하단 고정 영역은 루트 `layout.tsx`. 메인(`/`)은 03 일정 화면, 아직 없는 메뉴 경로는 404 안내(`not-found.tsx`). 타입 생성: 백엔드 실행 후 `npm run gen:api`(또는 `npm run gen:api -- <openapi.json 경로>`) |
| 백엔드 | FastAPI·Python 3.12·uv. SQLAlchemy 2.1.6·Alembic 1.20.1·APScheduler 3.11.3. `/api/v1` 라우터(`app/api/router.py`), 오류 형식·예외 처리기, CSRF·요청 제한, API-Football 클라이언트 골격, 수집 실행기(`app/sync`, 등록된 작업 없음) |
| DB | Supabase PostgreSQL `kicktab-dev`(서울), Direct connection 5432, 현재 환경에서 IPv6 접속. Psycopg 3, `sslmode=verify-full` + `certs/supabase-ca.crt`. 테이블 `sync_runs`·`feedback`, 03의 기준 데이터·경기·뉴스 7개(모두 RLS 켜짐·정책 없음, 현재 리비전 `0005_news`). Data API 꺼짐. **현재 DB는 이 프로젝트 하나뿐**이므로 개발 중 마이그레이션·롤백 검증도 여기서 한다(운영 DB 분리는 §10 C-07) |
| 버전 관리 | Git 저장소 루트 `kick-tab/apps/`, 원격 `main`·`dev`(§11) |

**2026-10-31 00 채팅 실행 확인:** 백엔드 `ruff check` 통과, 기반 테스트 6개 통과, DB 인증·`SELECT 1`·TLS 확인 통과(읽기 전용), 프런트엔드 `npm run lint`·`npm run build` 통과. 개발 서버 실행은 하지 않았다.

명령은 각 앱 폴더에서 실행한다.

| 위치 | 설치·실행 | 검사 |
| --- | --- | --- |
| `frontend/` | `npm ci` → `npm run dev` | `npm run lint`, `npm run build` |
| `backend/` | `uv sync --locked --group dev` → `uv run fastapi dev app/main.py`(또는 `uv run python -m uvicorn app.main:app --port 8000`) | `uv run ruff check .`, `uv run python -m pytest`(DB 실연동 테스트는 `KICKTAB_DB_TESTS=1`일 때만, 항상 롤백), `uv run python -m app.check_database`, `uv run python -m alembic upgrade head`·`downgrade -1`·`check` |

**빌드 참고(2026-11-01):** 기본 `npm run build`(Turbopack)는 이 PC에서 `.next`를 지운 상태로도 통과한다(Node 24.20.0). Codex 샌드박스에서는 `TurbopackInternalError: Failed to write app endpoint /page … globals.css → creating new process … node process exited before we could connect to it`로 실패했다. Turbopack이 PostCSS(Tailwind)를 별도 Node 프로세스로 띄워 로컬 연결로 붙는 단계라 샌드박스의 프로세스·로컬 소켓 제한이 원인으로 보이며(같은 코드가 일반 환경 Turbopack·Codex 환경 Webpack 빌드 모두 통과), 정확한 제한 항목은 미확인이다(추정). Codex 재검증(2026-11-01)에서는 일반 실행 환경의 기본 Turbopack 빌드가 통과했다. 번들러 설정은 바꾸지 않았다. 검증 환경에서 재현되면 `npm run build -- --webpack` 결과는 참고로만 쓰고 기본 빌드 통과로 기록하지 않는다.

**의존성 점검(2026-11-01):** `npm audit`의 moderate 18건은 모두 `minimatch`(glob 패턴 처리 서비스 거부) 한 경로다. 16건은 기존 ESLint 체인(`eslint`·`eslint-config-next`), 2건은 01에서 추가한 `openapi-typescript` → `@redocly/openapi-core`. 모두 개발 도구라 운영 번들에 포함되지 않고(`npm audit --omit=dev` 0건) 패턴은 설정 파일에서만 들어온다. 제시된 수정안은 주 버전을 낮추는 것이라 적용하지 않았다(`npm audit fix --force` 금지). 상위 패키지가 고친 버전을 내면 갱신한다.

**주의:** 이 PC에서는 Windows 애플리케이션 제어 정책이 `.venv`의 실행 파일(`pytest.exe` 등)을 간헐적으로 차단한다(2026-10-31 한 차례 `uv run pytest` 실패, 이후 재확인 시 실행됨). 안정적으로 `uv run python -m pytest`, `uv run python -m alembic …`처럼 `python -m` 형태를 사용한다.

기본 주소는 프런트엔드 `http://localhost:3000`, 백엔드 `http://localhost:8000`이며 API 문서는 `/docs`, 상태 확인은 `/health`다. 기본 Google Fonts는 빌드 시 네트워크 접근이 필요하다(Figma 글꼴 확정 시 01에서 교체).

현재 백엔드 Python 3.12.14는 `.python-runtime/`에 있고 `.venv`가 이를 참조한다. 둘 다 버전 관리에서 제외한다. 새 작업 환경이나 폴더 이동 시 Python 3.12와 가상환경을 준비한다. 의존성을 변경하면 잠금 파일(`uv.lock`, `package-lock.json`)도 갱신하고, 새 패키지는 설치 시점의 안정 버전을 확인해 고정한다.

## 8. 기능별 선행 조건과 완료 조건 요약

| 채팅 | 선행 조건 | 고유 완료 조건(공통 조건 §4에 추가) |
| --- | --- | --- |
| 01 | 없음(준비 완료) | SQLAlchemy·Alembic 첫 마이그레이션(`sync_runs`, `feedback`, RLS 포함) 적용·롤백 확인, 응답·오류 형식과 예외 처리기, CSRF·요청 제한 공통 의존성, API-Football 클라이언트 골격과 한도 보호 단위 테스트, `rewrites`·API 래퍼·생성 타입·Query Provider, 디자인 토큰·공통 UI, 헤더(인증 자리)·푸터(출처·권리 고지 자리)·TOP 5 띠 빈 상태·의견 보내기(비회원 제출, 1,000자, 실패 시 입력 유지) |
| 02 | 01·03~08 완료, `AUTH_JWT_SECRET`·SMTP 계정 사용자 입력(§9 U-04·U-05) | 실제 메일로 가입·비밀번호 찾기 완료, 비회원 관심 팀에 회원 DB 동기화 연결(A→B→로그아웃 시 A 복원, 6번째 거부), 뉴스 북마크 저장/해제/재선택(BOOK-001·003), 04 후기 작성·수정·삭제·반응·평가 로그인 복귀, 가입 인증번호 규칙 전체, 가입 직후 세션 확인, 로그인·갱신·로그아웃·비밀번호 찾기/변경, CSRF·오픈 리다이렉트 방지, 의견 제출 회원·비회원 차등 요청 제한(§10.1 P-10) |
| 03 | 01 재검수 완료 | 14개 대회·현재 시즌·5대 리그 팀·허용 집합 적재, 상태 변환 표 테스트, KST 날짜 묶음, 날짜 막대·대회 필터·팀 검색(별칭)·초기화 규칙, 비회원 관심 팀(저장소·관심 팀 일정 우선순위·관심 팀 버튼·5개 제한·저장소 사용 불가 안내), 실시간 폴링(실제 경기 검증은 가능한 시간에 별도 기록), 뉴스 분류 규칙·중복 제거·출처 표시 |
| 04 | 03 완료 | 상태별 영역 전환, 미제공·발표 전 표기, 상대 전적 표시 조건, 후기 공개 조회·정렬(인기순·최신순)·평균 평점 집계, TOP 5 선정은 정책 확정분만. 후기 작성·수정·삭제·반응은 02에서 마무리(사전 작업만) |
| 05 | 03·04 완료 | 시즌 전체 종료 경기·팀/대회 결합 필터·초기화 규칙·페이지 분할, 과거 팀 검색과 상세 미제공 팀 링크 차단, 2025 적재 후 중복 없음 |
| 06 | 03·05 완료 | 시즌별 팀 순위·선수 순위 전환 규칙, 선방 자체 집계(누락 제외·인원 안내·공동 순위), red·yellowred 분리, 메인 간소 순위, 링크 허용 집합 적용 |
| 07 | 03·06 완료 | 현재 시즌 팀만 표시, 리그 필터·검색·비회원 관심 팀 토글·페이지 분할 |
| 08 | 03·06 완료 | 팀 상세 6개 영역, 선수 표 정렬·더 보기·누락 표시, 시즌 기록 전환, 이적 반기 분류·안내·고정, 팀 뉴스, 모바일 탭, 허용되지 않은 팀 직접 URL 차단 |
| 09 | 02 완료 | 마이페이지 4개 섹션, 회원 전용 접근 차단, 다른 화면과 변경 반영 일치, 로그아웃 이동 규칙 |

**01 세부 기준(2026-10-31 착수 전 검수에서 확정)**

- **진행 단계:** A 백엔드 기반(DB·마이그레이션·응답/오류 형식·공통 의존성·API-Football 클라이언트 골격·수집 실행기) → B 프런트엔드 기반(rewrites·API 래퍼·생성 타입·Query Provider·토큰·글꼴·공통 UI) → C 전역 화면(헤더·TOP 5 띠·푸터·모바일 하단 고정 영역·의견 보내기). Codex 교차 검증은 01 전체 완료 후 한 번 받는다.
- **`feedback` 테이블:** `users` 테이블이 아직 없으므로 `user_id uuid NULL`을 외래 키 없이 만든다. 02가 `users` 생성 시 외래 키를 추가한다(삭제 시 처리 방식은 P-03 결정 후). 01의 제출 API는 항상 비회원 익명 제출로 저장하고, 로그인 회원 연결은 02가 인증 의존성으로 붙인다. IP 주소는 테이블에 저장하지 않는다.
- **요청 제한:** 단일 인스턴스 기준 메모리 기반 제한기로 구현하고 키 함수를 교체할 수 있게 한다. 브라우저 요청은 Next.js `rewrites`를 거치므로 실제 클라이언트 IP는 `X-Forwarded-For`에서 얻되, 신뢰할 프록시(로컬 Next.js) 뒤에서만 이 헤더를 믿도록 설정값으로 둔다. 의견 제출 제한값은 사용자 확정(2026-10-31): IP별 분당 3회·일 20회, `X-Forwarded-For` 위조 대비 전역 분당 20회·일 300회(C-08). 두 한도를 모두 통과한 요청만 집계해 거부된 요청이 새 클라이언트 상태를 만들지 않고, 저장 키는 최대 10,000개(오래 안 쓰인 키부터 정리)로 제한한다. 남은 미확정은 02의 회원·비회원 차등값과 보존 기간(§10.1 P-10).
- **CSRF 헤더:** `X-KickTab-Client: web` 검사는 공개 변경 요청인 의견 제출에도 적용한다. 프런트엔드 API 래퍼가 변경 요청에 이 헤더를 자동으로 붙인다.
- **API-Football 클라이언트:** 01에서는 실제 외부 호출을 하지 않는다(0회). 모의 전송으로 속도 제한·일일 예산·HTTP 200 + `errors` 실패 처리·재시도 상한·키 비노출을 테스트한다. 실제 호출은 03부터.
- **헤더 인증 영역:** 02 전까지 비회원 상태(로그인·회원가입 버튼)만 표시하고, 02가 `useAuth()`로 연결할 수 있게 컴포넌트 경계를 둔다. 모바일 메뉴의 회원용 변형(`62:1475`, `81:3209`)은 02에서 연결한다.
- **푸터:** 서비스 소개·이용약관·개인정보처리방침·문의 항목은 대상 문서가 없으므로(P-12) 링크 없이 표시하거나 "준비 중"으로 두고, 운영자·주소·이메일은 시안의 가상 값을 쓰지 않고 설정값 자리로 둔다. 데이터·뉴스 출처 고지 문구는 Figma 푸터를 따르되 이미지 권리 고지 문구는 V-10 확인 전 임시 문구로 표시한다.
- **브랜드·대체 이미지:** Figma `55:22`(로고 심벌)과 `55:26`(공통 대체 이미지)을 SVG로 내려받아 `frontend/public/brand/`, `frontend/public/placeholder.svg`에 둔다. 파비콘도 로고 심벌 기준으로 교체한다.
- **Figma 도구 사용:** `get_design_context`는 Figma의 design-to-code 안내(skill 또는 MCP 리소스)를 먼저 읽으라고 요구한다. 읽을 수 없으면 `get_metadata`·`get_screenshot`과 §6.6 토큰으로 구현하고, 생성 코드는 그대로 붙이지 말고 프로젝트 컴포넌트·토큰으로 옮긴다.
- **기본 생성 파일 정리:** create-next-app 시작 화면·`next.svg`·`vercel.svg`·Geist 글꼴은 01에서 제거했다. 메인 경로(`/`)는 03이 일정 화면으로 구현했다.

## 9. 사용자 확인·환경 작업

| ID | 내용 | 시점 |
| --- | --- | --- |
| U-01 | Git 저장소 연결 — 진행 상태는 §11 | 01 착수 전 |
| U-02 | 완료(2026-10-31): Figma 커넥터 연결. 별도 디자인 전달 문서는 사용하지 않기로 하고 Figma의 해당 참조 문구도 삭제 | — |
| U-03 | 완료(2026-10-31 확인): Supabase Data API가 처음부터 꺼져 있음(Integrations → Data API → Enable Data API 꺼짐). 코드의 RLS 활성화 규칙과 함께 유지한다. 나중에 Data API를 켜지 않는다 | — |
| U-04 | `AUTH_JWT_SECRET` 준비: 사용자가 직접 입력하거나, 사용자가 허락하면 02가 무작위 값(64바이트 이상)을 **화면에 출력하지 않고** `backend/.env`에 바로 추가한다. 값은 채팅·문서·로그에 남기지 않는다. 배포 환경에는 별도 값을 설정한다 | 02 착수 시(연기) |
| U-05 | **인증 메일 계정 준비(02 착수 전, 02 연기로 급하지 않음):** 발송 전용 Gmail 계정 준비(개인 계정과 분리 권장) → Google 계정 보안에서 2단계 인증 켜기 → '앱 비밀번호' 생성 → `backend/.env`의 `SMTP_USERNAME`(Gmail 주소)·`SMTP_PASSWORD`(앱 비밀번호 16자리)에 직접 입력. 비밀 값이므로 채팅·문서에 쓰지 않는다. 호스트·포트·발신 주소는 02가 비밀이 아닌 설정값으로 넣는다 | 02 착수 전 |
| U-06 | 의견 알림용 디스코드 채널 웹후크 URL을 `backend/.env`의 `FEEDBACK_DISCORD_WEBHOOK_URL`에 직접 입력(채널 설정 → 연동 → 웹후크 → 새 웹후크 → URL 복사). 비밀 값이므로 채팅·문서에 쓰지 않는다. 비워 두면 알림 없이 저장만 된다 | 01 이후 언제든(배포 환경에도 같은 변수 설정) |

## 10. 미확정 정책·Codex 검토 요청

### 10.1 제품 정책 결정 대기 — 결정 전에는 해당 기능을 "제공 보류"로 구현

| ID | 결정 대상 | 영향 채팅 | 00 제안(결정 아님) |
| --- | --- | --- | --- |
| P-01 | 인증 메일 발송 공급자 | 02 | **결정(2026-11-01):** 공급자에 묶이지 않는 SMTP 발송으로 구현한다. 도메인이 없는 지금은 Gmail SMTP(`smtp.gmail.com:587`, STARTTLS, 앱 비밀번호, 하루 약 500통 한도)로 실제 발송한다. 공개 전 도메인을 확보하면 Resend·Amazon SES 등의 SMTP 정보로 설정값만 바꿔 교체한다(코드 변경 없음). Gmail 발신은 스팸함 분류 가능성이 있어 공개 운영용으로는 교체를 전제로 한다 |
| P-02 | 소셜 로그인 제공 여부, 같은 이메일 계정 연결 방식 | 02 | **확정(사용자 확정 2026-11-01):** 초기에는 이메일 가입만. 카카오·구글은 앱 등록 후 추가. 같은 이메일 계정을 자동 연결하지 않고, 이미 가입된 이메일이면 기존 로그인 방식으로 안내 |
| P-03 | 회원 탈퇴 시 후기·반응·북마크·의견 처리, 같은 이메일 재가입 | 02·03·04·09 | **확정(사용자 확정 2026-11-01):** 관심 팀·북마크·반응·후기 삭제(후기는 집계에서 제외), 의견은 회원 연결만 해제. 탈퇴 후 같은 이메일로 재가입 가능(새 계정, 이전 데이터 복구 없음). 탈퇴 확인 절차는 Figma 탈퇴 다이얼로그(`62:1800`)를 따르고, 처리 후 로그아웃 상태로 메인 이동 |
| P-04 | 닉네임·비밀번호 규칙(길이·허용 문자·금칙어) | 02 | **확정(사용자 확정 2026-11-01):** 닉네임 2~12자 한글(완성형)·영문·숫자, 중복 불가. 비밀번호 8~64자, 영문과 숫자를 각각 1자 이상 포함. 금칙어 목록은 초기 범위에서 두지 않음 |
| P-05 | 행정 종료(AWD·WO) 경기의 평가 제공 | 04 | 평가는 결정 전 제공 보류. TOP은 신규 후보에서 제외하되 선정 후 행정 종료로 바뀐 항목은 상태를 표시하고 유지(2026-11-01) |
| P-06 | TOP 5 주간 교체·실패 복구 | 04·관련 UI | **2026-11-02 사용자 확정:** 00:00 첫 시도→실패 시 00:05 자동 1회 재시도→재실패 지연 안내/운영 알림/수동 복구. 공개 전 서버 지난주 결과를 실제 소속 기간으로 유지. 검증 성공 즉시 교체·공개 후 고정. 공개 UI 3종, 오류별 화면 없음. 시도별 시간 제한·중복 실행 방지·알림·관리 명령·클라이언트 완료 감지는 실제 구현 검증 대상 |
| P-07 | 경기 상태 변경 시 기존 평가 처리(D-07 잔여) | 04 | 종료→중단·취소 등 평가 불가 상태로 바뀌면 숨김 처리 후 원복 시 재노출 |
| P-08 | 뉴스 대회/팀 분류 세부 규칙, 언론사명 매핑 방식(D-09) | 03 | **03 적용(2026-11-02, 사용자 피드백 반영):** 분류는 `app/services/news_classify.py`(AI 미사용, 제목·설명만): 대회명이 명시돼야 하고, 기사의 **주제**여야 한다 — 제목에 대회명이 있거나, 주체 팀(제목의 팀, 제목에 팀이 없으면 설명에 처음 나오는 팀)이 이번 시즌 **바로 그 대회**(UCL·UEL·UECL 구분)에 참가할 때만 인정. MLS·사우디 등 다른 리그 맥락이면 제목 팀 경로만 인정(예: 'EPL도 아닌데' 손흥민 LAFC 기사 제외, 과거 UEL 우승 회고 기사 제외). UEFA가 국내 리그보다 우선, 국내 리그 2개 이상·근거 없음은 제외, AFC·다른 나라 리그는 해당 뱃지 근거 제외, 여자 축구(여자축구·위민·WSL·라리가F·'여자 프리미어리그' 등)·다른 종목·토토는 팀 연결 전에 기사 전체 제외(교차 검증 반영, 남자 팀 ID 연결 방지), 팀도 대회 단어도 축구 맥락 단어도 없는 기사(광고·제휴 등) 제외. 팀은 `for_news` 별칭만(모호한 별칭·도시명과 겹치는 짧은 별칭 제외), 여러 팀 연결. 중복은 정규화 원문 URL 해시와 같은 제목으로 1회. 표본 40건 사람 판정(주제 기준 적용 후): 대회 뱃지 적합 37건, 부적합 3건(축구 외 시위 기사·칼럼·이적설 기사의 부수 언급) — 규칙 기반 한계로 보고. Codex 교차 검증 표본 28건: 적합 24·오분류 1(밀너 마라톤 기사가 과거 챔피언스리그 이력 언급으로 UEFA)·주제 재검토 3 — 과거 이력·부수 언급은 보정 표본 후보. 참가 팀 정보는 `team_competition_seasons`(리그·UEFA 팀 목록)를 쓴다. **출처 표시:** 2026-11-02 최신 사용자 결정(언론사 표시명 제외, API 검증 문서)에 따라 매핑 표 없이 원문 도메인만 표시 — §10.3 D-03-1 |
| P-09 | 북마크 중복 키·보존 범위(D-10) | 02·09 | 원문 링크 정규화 해시를 중복 키로 사용, 보관 항목은 설정값 |
| P-10 | 의견 스팸 방지·보존 정책(D-11 잔여) | 01·02 | **01 적용(사용자 결정 2026-10-31):** ① IP별 분당 3회·일 20회 + 서비스 전체 분당 20회·일 300회(메모리 기반, IP는 DB에 저장하지 않음, 잘못된 JSON을 포함한 형식 오류 요청도 횟수에 포함) ② 허니팟 입력칸(`website`, 사람에게는 보이지 않음 — 값이 있으면 저장·알림 없이 400) ③ 중복 본문 차단(공백·대소문자를 정규화한 SHA-256을 `feedback.body_hash`에 저장, 24시간 안의 같은 본문은 발신자와 무관하게 409 `FEEDBACK_DUPLICATE`, 동시 제출은 본문 해시별 트랜잭션 잠금으로 직렬화). **02 예정:** 회원·비회원 차등 제한 — 회원은 사용자 ID 기준, 비회원은 IP 기준으로 더 엄격하게(제안값: 회원 분당 3회·일 20회, 비회원 분당 2회·일 5회, 02에서 확정). `RateLimit`의 `key_func`·제한값을 인증 상태에 따라 고르는 의존성으로 구현. CAPTCHA는 실제 남용이 확인될 때만 검토. 보존 기간은 운영 전 결정. 의견 본문이 디스코드로 전송되므로 개인정보처리방침(P-12)에 외부 전송 사실을 반영 |
| P-11 | 팀 별칭 사전 구축·관리 방식(D-16) | 03 | **03 적용(2026-11-02):** `backend/app/seed/team_aliases.json`(현재 시즌 5대 리그 96팀 한국어 이름·한국어/영문 별칭, `searchOnly`, `ambiguous` 묶음) → `uv run python -m app.sync team_aliases`(또는 `reference` 끝에서 자동). 여러 팀 표현(레알·시티·유나이티드·맨체스터·밀란·마드리드·보루시아·파리 등)은 검색에서 후보 선택, 뉴스에서 근거 제외. 5대 리그 밖 팀(UEFA·컵 상대)은 영문 이름만 검색 |
| P-12 | 이용약관·개인정보 처리방침 문서(가입 동의 화면 필요) | 02·공개 전 | **확정(사용자 확정 2026-11-01):** 문서 본문은 사용자가 공개 전에 작성한다. 그 전까지 가입 화면에는 필수 동의 항목(이용약관·개인정보 처리방침)만 두고 '보기'는 '준비 중'으로 표시하며, 동의 시 `terms_agreements`에 약관 버전 `draft`를 기록한다. 문서가 확정되면 버전을 올리고 푸터 링크를 연결한다 |
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
| D-01-10 | TOP 5 '변경 일시'(Figma `159:513`: 일시 칸은 선정 당시 일시, 아래 줄에 바뀐 일시) ↔ §6.4 계약은 최신 `match.kickoffAt` 하나만 있어 선정 당시 일시와 '일시만 바뀐 예정 경기'를 알 수 없음 | 계약을 바꾸지 않고 일시 칸에 최신 일시, 연기·취소·중단·행정 종료 항목에 '변경 일시'(연기+시간 확정이면 최신 일시라 일시 칸과 같은 값, 그 밖은 '미정' + `statusReason`) 표시 | 대안 A: 04가 `items[]`에 선정 당시 킥오프(예: `selectedKickoffAt`)를 저장·반환해 Figma대로 표시(계약 필드 추가, 01 화면 소폭 수정). 대안 B: 현 방식 유지하고 Figma를 '현재 일시 + 상태'로 단순화 |
| D-01-11 | TOP5 모바일 띠 기간·안내 | **2026-11-02 Figma 반영:** 목록·경기 없음·지연 모두 기간 표시. 경기 없음·지연은 줄바꿈에 따른 가변 높이로 320px에서 확인 | 실제 앱의 이전 고정 높이·긴 문구 말줄임을 새 설계에 맞춰 보완 |

03 구현 중 기준끼리 어긋났거나 Figma에 없는 부분은 아래처럼 처리했다. Codex 검토와 사용자 확인을 요청한다.

| ID | 항목 | 03 처리 | 확인 요청 |
| --- | --- | --- | --- |
| D-03-1 | 뉴스 출처: Figma 카드 'OO스포츠' + 가이드 P-08 기본값(도메인→언론사명 매핑) ↔ API 검증 문서의 2026-11-02 최신 사용자 결정(언론사 표시명 제외, 카드 = 제목·설명·분류·날짜) | 최신 결정을 따라 매핑 표 없이 원문 도메인(`sportschosun.com`)·상대 시각·'원문 보기 ↗'를 표시하고, 영역 하단에 '뉴스 제공: 네이버 검색' 표기. 기능 명세 NEWS-001 '출처 표시, 도메인을 공식 언론사명으로 단정하지 않음'은 충족 | 도메인 표시 유지 / 언론사명 매핑 추가 / 출처 칸 제거 중 선택 |
| D-03-2 | 원문 삭제·접근 불가 안내(NEWS-004) — Figma 화면 없음 | 카드 클릭 → `/news/original?id=` 전환 화면에서 원문을 1회 확인(HEAD, 실패 시 GET 헤더). 정상·확인 불가(timeout 등)는 바로 원문으로 이동, 404/410만 '원문 기사를 확인할 수 없습니다' + 원문 주소 열기. 언론사 사이트에 클릭당 1회 요청 | 전환 화면 디자인 |
| D-03-3 | 관심 팀 경기 카드(Figma `49:330`은 '대회 · 시각'만) | 약 2주 범위의 경기가 섞이므로 '대회 · 11/5(목) 02:45'처럼 날짜를 함께 표시 | 날짜 표기 유지 |
| D-03-4 | '경기 더 보기' 초기 개수(Figma 표본 5행) | 개정 Figma(`225:1216`·`225:1768`)에 맞춰 날짜 보기 5경기씩 표시, 버튼에 '(5/37)' 개수 표기, 날짜·팀·대회가 바뀌거나 초기화하면 처음 개수로 복귀. 팀 14일 보기도 같은 5경기씩 더 보기이며 보이는 경기만 날짜별 제목으로 묶음 | 초기 개수 |
| D-03-5 | 상태 뱃지 진행 표기: TOP 5 `63′` ↔ 컴포넌트 시트 `55:27`·메인 '진행 중 63분' | 개정 Figma `187:591`(경기 행)에 맞춰 `MatchStatusBadge`를 '진행 중 63′'·예정 회색으로 통일(TOP 5 포함). 대회 표기는 한국어 이름(`competitionName`) | 컴포넌트 시트 `55:27`의 '63분'·예정 파랑 표기 정리 |
| D-03-6 | 대회 직접 선택·팀 검색 14일 모아 보기 | **2026-11-02 문서·와이어프레임·Figma 반영:** 기본/대표 필터 화면과 공통 컴포넌트 상태로 간소화(§1). 대회 직접 적용·보조 다중 초안, 팀 14일 날짜별 표시·해제 복귀 정책 적용. **03 앱 반영·검수 완료(2026-11-02)**: `CompetitionFilter` 재작성, `GET /fixtures/team`, 팀 14일 화면·URL 복귀·빈/부분 실패 안내(1280·375·320) | — |
| D-03-7 | 쿠프 드 프랑스 2026 | 2026-11-02 `/leagues` 재조회에서 2026 시즌이 제공되어(시작 10/31) `available`로 수집·표시. V-16의 '오픈 직전 재조회'는 그대로 유지 | V-16 기록 갱신 |
| D-03-8 | 모바일 팀 검색 입력(Figma 40px) | 입력은 40px, 감싼 label을 44px로 두어 조작 영역 확보 | — |

### 10.4 공개 전 필수 확인(기존 검증 문서 유지)

V-04 실시간 경기 검증, V-09 네이버 뉴스 선별·재분류·중복 정리·북마크 보관·수익화 허용 확인, V-10 엠블럼·선수 사진 권리와 API-Football 데이터 제3자 권리, V-16 프랑스 컵 2026-27 재조회, 운영 호출량 재산정(V-08).

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

**현재 상태(2026-11-02):** 원격 `main`·`dev`·`feat/01-header-footer`·`feat/03-schedule`. 03은 최신 `dev`에서 만든 `feat/03-schedule`에 커밋·push했다(Codex 교차 검증 통과). `dev` 병합은 00 채팅 확인 후 사용자 요청 시 진행한다. 다음 04는 03 병합 후의 최신 `dev`에서 `feat/04-match-detail`을 만든다.

**Git에 올리지 않는 것:** 모든 `.env*` 파일(`.env.example` 포함), 가상환경·Python 런타임, `node_modules`·`.next`, 캐시, 저장소 밖 로컬 자료(`../docs`·`../api-test`·`../wireframe`), 쓰지 않는 기본 생성 파일. 새 파일 유형이 생기면 루트 `.gitignore`를 먼저 갱신한다.
