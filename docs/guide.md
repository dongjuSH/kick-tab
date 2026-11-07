# KickTab 개발 가이드

**2026-11-07 · 08 팀 상세(완료 — Codex 교차 검증 통과(4차 후속), 공유 개발 DB `0014` 적용, `feat/08-team-detail` 커밋·push, `dev` 병합):** 마무리 확인(Claude): 공유 개발 DB를 `0013` → `0014`로 올리고 `alembic current` = `0014_transfer_identity_indexes`(head)·`alembic check` 변경 없음, 이적 2025-26 7,159건·2026-27 4,446건, 새 고유 인덱스 기준 중복 0(ID 있는 줄·없는 줄 각각) 확인 — 재수집 없음. 최종 검사 ruff, pytest 285(DB 실연동 포함 353), lint, tsc, npm test 33, build 통과. 사용자 요청으로 `daily-work-log.md`·`file-feature-map.md`에 08 반영. `/teams/[id]`를 비회원 기준으로 끝까지 구현했다. 이로써 비회원 기준 서비스 전체(메인·경기 상세·지난 경기·리그 순위·팀 탐색·팀 상세)가 이어진다(로그인·회원가입 링크만 02 전까지 404). 수집: 03 `reference`가 리그 팀 목록 응답의 경기장(이름·수용 인원)을 `teams`에 함께 저장하고, 새 작업 `team_details`(매일 15:00 KST — 팀마다 `/coachs`·`/players/squads`·`/teams/statistics` 이번 시즌, 지난 시즌 기록은 그 리그를 뛴 팀만 1회 저장 후 고정, 선수단 중 국적 누락 선수는 `/players/profiles` 1회 보완)와 `transfers`(매일 00:00 KST — 팀마다 `/transfers` 1회, 날짜로 시즌·반기 분류, 시즌 종료 후 6/30까지 반영된 기록을 7/1 00:00 갱신으로 받은 뒤 고정, 미래 날짜 제외, 제공사가 같은 이적을 다음 날 한 번 더 준 항목은 1건으로)를 추가했다. 적재(96팀): 경기장 96/96, 현직 감독 95/96(1팀 미제공), 선수단 2,946명(등번호 누락 17·0.6%, 국적 누락 297·10.1% — 프로필 보완 412명 조회 후에도 남은 값, 이번 시즌 리그 기록 없음 362·12.3%), 팀 시즌 기록 이번 96·지난 83(승격 13팀 제외), 이적 11,605줄(2025-26 7,159·2026-27 4,446 — Codex 2차 보완 후 재적재, 유형 미제공 623, 중복 0). 실제 API 호출 누적 1,386회(`sync_runs` 확인분 1,382회와 팀 최근 흐름 별도 집계 4회 — Codex 4차 N8): `reference` 22, `team_details` 783 = 감독·선수단·이번 시즌 기록 288 + 지난 시즌 기록 83 + 국적 보완 412, `transfers` 577 = 1팀 시험 1 + 전체 95 + 동일 결과 재실행 확인 1 + 하루 차이 반복 규칙 도입 후 재적재 96×2 + Codex 1차(지적 8)·2차(N2)·3차(N4) 보완 후 재적재 96×3, 팀 최근 흐름 요청 시 보충 4(애플리케이션 로그 집계 대상). 일일 운영 예상: 약 384회 + 새 선수 국적 보완. 마이그레이션 `0012_team_detail`, `0013_transfer_counterpart_key`(Codex 3차 N4), `0014_transfer_identity_indexes`(Codex 4차 N7 — 상대 팀 ID 유무별 이적 고유 인덱스). 디자인·기획 차이는 §10.3 D-08. **자체 검수 보완(같은 날):** ① 수집 단위 갱신 판정이 '마지막 시도 후 23시간'이라 낮에 수동 실행하면 그날 밤 00:00 이적 갱신을 건너뛰던 문제 → 'KST 날짜가 바뀌면 대상'(하루 1회)으로 변경 ② 고정 경계가 6/30 00:00 실행까지라 6/30에 반영된 기록을 놓치던 문제 → 기능 명세서 6.2('6월 30일까지 반영된 기록은 다음 00:00 갱신에 반영')대로 7/1 00:00 실행까지 갱신 후 고정 ③ 선수단 갱신 실패와 빈 선수단이 겹칠 때 빈 결과 문구가 빠지던 문제 ④ 화면에서 쓰지 않는 응답 필드(`statsUpdatedAt`·`frozen`·`formationPlayed`·`played`) 삭제(작업 원칙 5). 보완 후 외부 API 추가 호출 0회(같은 날 재실행은 건너뜀 확인). **Codex 1차 교차 검증(보완 필요: 차단 1·중요 3·경미 5) 보완:** ① 잘린 응답(선수단 27→1명, 이적 59→1건, 빈 fixtures 시즌 기록)이 저장값을 덮고 성공으로 기록되던 문제 → 저장 전 완전성 검증(§6.5 표, 저장된 96팀·179건 모두 통과 확인) ② 리그 팀 목록 미수집 시 팀 상세는 503인데 검색·순위 링크는 `detailAvailable: true`이던 불일치 → 03 공통 `team_detail_lookup()`이 수집된 리그 소속만 `true`(그 밖 `null`) ③ 이적 요청 실패를 한 시즌에만 기록하던 문제·7/1 마지막 갱신 실패 시 지난 시즌이 재시도 없이 고정되던 문제 → 요청이 쓰려던 모든 시즌에 실패 기록, 마지막 갱신이 성공할 때까지 매일 재시도 ⑤ venue 블록에 없는 필드(예: 수용 인원)를 NULL로 덮던 문제 → 응답에 있는 필드만 갱신 ⑥ 다른 선수의 프로필 응답을 조회 완료로 기록하던 문제 → 거부·다음 날 재조회 ⑦ 시작일이 미래인 감독을 현직으로 고르던 문제 → 시작 전 재임 제외 ⑧ 반대 방향 이동이 끼어 있어도 하루 차이 반복으로 합치던 문제 → 그 이틀에 반대 방향 이동이 있으면 둘 다 보존(규칙 변경분을 반영하려 2025-26 초기 적재분을 비우고 이적 96회 재수집, 7,155→7,156) ⑨ 팀 뉴스 갱신 실패+빈 목록에서 빈 결과만 보이던 문제 → 실패 안내·빈 결과 문구·'다시 확인' 함께(뉴스 실패 기록을 잠시 넣어 브라우저 확인 후 삭제). **Codex 2차(보완 필요: 차단 0·중요 2·경미 1) 보완:** N1 시즌 기록의 홈+원정≠전체(예: 홈 11·원정 9인데 전체 30) 응답이 저장되던 문제 → 승·무·패·경기 수·득점·실점 모두 홈+원정=전체 검사(저장 179건 모두 통과) N2 상대 팀 ID가 없는(이름만 있는, 933줄) 이적을 같은 팀으로 보고 하루 차이 반복으로 합치던 문제 → 상대 팀 ID가 있을 때만 합침(반영하려 2025-26 초기 적재분을 다시 비우고 이적 96회 재수집, 7,156→7,159) N3 §2·§6.3의 고정 규칙 설명 정정. **Codex 3차(보완 필요: 차단 0·중요 1·경미 2) 보완:** N4 같은 날 상대 팀 ID가 없는 두 팀으로의 이적(A 임대 → A 복귀 → B 임대)이 파서 키와 DB 고유 키에서 한 건으로 겹쳐 하나가 빠지던 문제 → ID가 없으면 상대 팀 이름으로 구분(파서 키, 마이그레이션 `0013` 고유 키에 `counterpart_name`), 재적재 결과 실제 데이터에는 해당 충돌이 없었음(7,159·4,446 그대로) N5 가이드의 기획 문서 반영 상태·API 호출 총계 정리 N6 미사용 export(`TEAM_NEWS_PAGE`) 제거. **Codex 4차 후속 보완:** N7 상대 팀 ID 유무별 고유 인덱스로 파서와 DB 규칙 통일(`0014`), N8 수집 실행 기록 1,382회와 팀 최근 흐름 별도 집계 4회 구분. ④ '경기 전체 보기' 범위는 사용자 결정(2026-11-07) A — `/results?team=` 연결 유지, 기획 문서 반영 완료(Codex, 기능 명세서 v1.7 TEAM-003·PRD v1.7 16장·유저 플로우 v1.6 UF-09·UF-11)(§10.3 D-08-9). 시작 전 처리: `tests/test_schedule_db.py`의 '오늘+21일에는 실제 경기가 없다' 가정을 '저장된 마지막 경기 날짜+30일'로 바꿔 실제 데이터·날짜와 무관하게 했다(제품 코드 변경 없음).

**2026-11-06 · 07 팀 탐색(완료 — Codex 교차 검증 통과(3차), `feat/07-team-browse` 커밋·push, `dev` 병합):** 3차 확인에서 2차 지적 2건 해결이 확인되어 통과했다. 최종 검수(ruff·pytest 260/DB 포함 314·alembic check·lint·tsc·npm test 26·build, 브라우저 목록·리그 필터·관심 팀 등록 → 메인 반영) 이상 없음. 사용자 요청으로 `daily-work-log.md`·`file-feature-map.md`에 07을 반영했다. 2차 보완 기록 — Codex 2차(1차 지적 5건 모두 해결, 새 지적 중요 1·경미 1) 보완 — ① URL에 반영되기 전(0.3초 안)의 검색어가 뒤로 가기 후 다시 적용되던 문제: 검색창이 보내지 않은 URL 변경이면 검색어가 같아도 입력값을 그 URL에 맞춰 보내지 않은 글자(와 대기 중 반영)를 버린다 ② 연속 입력을 Tab(blur)·Enter로 끝내면 기록이 두 단계로 나뉘던 문제: 마지막 글자를 같은 기록 단계에 반영(replace)한 뒤 연속 입력을 끝내고, 그다음 입력부터 새 기록. ×는 새 기록. 다른 조작(리그·페이지)이 0.3초 안에 URL을 바꾸면 아직 보내지 않은 글자는 버려진다(URL이 기준). 이하 2차 이전 기록 — Codex 1차(차단 0·중요 1·경미 4) 보완 — ① 2페이지에서 검색 → 뒤로 → 포커스를 유지한 채 새 검색하면 2페이지 기록을 덮어쓰던 문제: 검색창이 보내지 않은 URL 변경(뒤로·앞으로·리그·페이지·초기화)에서 연속 입력을 끝내 새 검색의 첫 반영을 새 기록으로 남김(보낸 검색을 순서대로 기억해 자기 반영과 구분) ② 거부 당시 목록을 벗어나면 거부 문구를 지워 같은 5개 조합으로 돌아와도 다시 나오지 않음 ③ 페이지 초과 화면도 재조회 실패 안내('마지막으로 확인한 목록'·'다시 확인') 안에서 표시 ④ `league`는 정수면 5대 리그가 아닌 모든 값(0·음수 포함) 404, 정수가 아니면 422로 계약 통일 ⑤ §3 테스트 수 정정. 이하 1차 기록 — `/teams?league=&q=&page=`를 비회원 기준으로 구현했다. 새 API `GET /teams`(현재 시즌 5대 리그 소속 `team_competition_seasons` 기준 96팀, 리그 필터·별칭 검색·12개씩 페이지, `TeamRef`+리그, 소속 미확인 503 `MEMBERSHIP_UNKNOWN`) — 기존 `/teams/search`는 10개 상한·컵/UEFA 참가 팀 포함·리그 정보 없음이라 목록에 쓸 수 없어, 매칭 로직만 `match_teams()`로 분리해 함께 쓴다. 화면은 리그 칩·검색(입력 후 0.3초, 한 번의 입력은 기록 1단계)·관심 팀 안내·팀 카드(`FavoriteToggle`)·`Pagination`·`DataState`. `FavoriteToggle`에 5개 꽉 참 상태(Figma 57:766, 다른 팀 버튼 비활성 '최대 5개까지 등록할 수 있어요')를, `DataState`에 `emptyAction`을 추가했다. 자체 재검토 보완 2건: ① 다른 탭이 먼저 5개를 저장한 경우 거부 문구가 곧바로 사라지고 안내 상자가 '4 / 5'로 남던 문제 — 저장소 `latest()`가 더 새 목록을 발견하면 모든 구독 화면에 알리고, 거부 문구는 누른 직후의 목록 기준으로 유지 ② 재조회 실패 시 이미 보인 목록을 버리고 오류만 보이던 문제 — `dataStatus()`(06)로 '마지막으로 확인한 목록' 일부 미제공 상태 + '다시 확인'. 외부 API 호출 0회, 마이그레이션 없음(다음 번호 계속 `0012`). 디자인 차이는 §10.3 D-07.

**2026-11-06 · 06 리그 순위(완료 — Codex 교차 검증 통과(3차), `feat/06-standings` 커밋·push, `dev` 병합):** 2차 차단(페이지 번호·20명은 정상인데 다른 페이지의 선수가 반복된 응답이 기록을 줄이고 성공으로 기록됨)은 '같은 선수가 두 번 나오면 그 리그 수집 전체를 거부'로 막았다(Codex가 넣은 '페이지 전체 반복' 검사를 일부 겹침까지 넓힘 — 2025-26 원본 188페이지·3,709명 중 두 페이지에 나온 선수 0, 2026 분데스리가 실제 재수집 통과). 1차 지적 5건 보완 — ① 잘린 수집 응답(10/20팀·10/20명·빈 2페이지)이 저장 데이터를 덮어쓰고 성공으로 기록되던 문제: 저장 전 완전성 검증 추가(§6.3) ② 마지막 확인 결과가 0건인 갱신 실패가 정상 빈 결과로 보이던 문제 ③ 소속 확인 실패의 '다시 확인' ④ 메인 칩 'BUN' ⑤ 미사용 `pages` 삭제. `/standings?league=&season=&type=`와 메인 5대 리그 간소 순위를 비회원 기준으로 구현했다. 5대 리그 × 2025·2026의 팀 순위(`standings`, 그룹 포함, 제공값 그대로 — 리그1 2025-26 33경기 유지), 선수 순위 4종(`player_rankings`, API 상위 20명 제공 순서, 퇴장은 red만·`yellowred` 별도 보관), 리그 전체 선수 시즌 기록(`player_season_stats`, 모든 `/players` 페이지)을 적재하고 선방은 이 표에서 골키퍼 기준으로 자체 집계한다(null 선수 제외·인원 안내·공동 순위). 수집 상태는 리그·시즌·종류별 `league_syncs`. 작업 `standings`(매시 확인, 경기일 1시간·그 외 하루 1회)·`player_rankings`·`player_stats`(매일). 실제 API 호출 누적 436회(팀 순위 13·선수 순위 48·선수 페이지 375, Codex 보완·확인 포함), 2025는 API로 받아 원본 파일과 팀 순위·선수 순위 4종·선방 집계가 모두 일치함을 확인했다. 마이그레이션 `0011_standings`.

**2026-11-05 · 05 지난 경기(완료, Codex 교차 검증 통과·`dev` 병합):** `/results`를 비회원 기준으로 구현했다. 2025·2026 시즌 14개 대회 전체 경기를 `fixtures_season` 작업으로 적재(대회·시즌당 1회, 2025 4,128경기·2026 3,290경기)하고, 선택 시즌의 종료 경기(일반·행정 종료, 최신순 10개씩)를 시즌·대회 다중·팀 조건으로 조회한다. 공통 `SeasonSelect`·`Pagination`·`GET /seasons`·`GET /results`·팀 검색 `season`·`/competitions`의 `seasons`를 추가했다(§2·§6.4). 2025-26 5대 리그 강등 15팀은 검색 전용 한국어 이름을 별칭 시드에 넣었다. 메인 `ScheduleSection`은 하이드레이션이 끝날 때까지 서버와 같은 자리 표시를 그려 04가 보고한 대회 필터 경합을 정리했다. 마이그레이션 `0010_season_fixtures`.

**2026-11-04 · 04 후기·TOP 5 선정:** 경기 상세 후기 제목 옆 `!`에서 기존 안내 전문을 읽는다. PC는 호버 및 클릭 고정, 모바일은 탭, 키보드는 Enter/Space로 연다. 닫기·바깥 클릭·Escape로 닫는다. 02 후기 작성에는 `ReviewGuidance`를 재사용한다. TOP 5 선정 프롬프트 `2026-11-04.1`은 국내 팬의 시청 관심과 대회 단계·실제 경쟁 맥락을 우선하고, 시즌 초 순위·승점 차나 더비 하나만으로 우선하지 않는다. 최근 흐름과 맞대결은 보조다. 후보 근거, 주간 게시·재시도·지연 운영은 유지한다.

**2026-11-04 · 03 일정·뉴스:** KST 오늘−3~+17의 21일을 수집·조회하며 날짜 막대는 어제부터 보인다. 대회 체크 초안은 적용할 때만 반영한다. 현재 날짜가 선택 대회 기준으로 비어 있음이 확인되면 오늘 이후 가장 가까운 경기가 있는 날로 이동하며 미확인 날짜는 비활성화하지 않는다. 팀 검색·관심 팀은 날짜 막대 없이 같은 21일을 보고, 경기 없음이 확인된 대회만 비활성화한다. X로 검색 해제, 6개 기본 표시에서 한 번에 전체 보기, 대회 선택 버튼 표시 방식은 유지한다.

**03 개발·배포 설정:** `alembic upgrade head`(0009) 뒤 `python -m app.sync team_aliases`, `python -m app.sync fixtures`로 한국어 이름과 실제 수집 범위를 채운다. 뉴스는 단일 백엔드 인스턴스의 `NEWS_SCHEDULER_ENABLED=true`로 정시(시간당 1회, 네이버 8회) 작업을 시작한다. `SCHEDULER_ENABLED=true`는 기존 전체 작업을 실행한다. 화면은 최신 48개 안에서 대회별로 필터링하며, 새 기사 없음 또는 수집 실패 시 기존 보관 기간 안의 기사를 유지한다. `/fixtures/availability`는 날짜별 경기 대회와 미확인 대회를 분리하고 `/news`는 `meta.total`·`meta.noNew`를 추가한다. 아래 2026-11-03 이전 기록의 날짜 범위·노출 개수·갱신 주기는 당시 기준이다.

**2026-11-04 · 01 사용성 개선:** 승인된 헤더·모바일·푸터 로고와 16/32px ICO를 앱에 반영했다. 헤더 활성 상태와 호버에서 글자 위치를 유지하며 밑줄만 바뀐다. TOP 5 요약은 44/72px, 제목 옆 실제 기간, 전체 대진 가로 순환, 호버·키보드 정지 및 동작 감소 설정을 적용한다. 펼친 목록과 주간 운영 계약은 유지한다.

최종 갱신: 2026-11-07 (토), 한국 시간(KST) — 08 팀 상세 완료(Codex 교차 검증 통과, 공유 개발 DB `0014` 적용, `feat/08-team-detail` 커밋·push, `dev` 병합), 사용자 요청으로 `daily-work-log.md`·`file-feature-map.md`에 08 반영. 다음은 02 로그인·회원가입. 이전: 07 팀 탐색 완료(Codex 교차 검증 3차 통과, `feat/07-team-browse` 커밋·push, `dev` 병합), 사용자 요청으로 `daily-work-log.md`·`file-feature-map.md`에 07 반영. 이전: 06 리그 순위 완료(Codex 교차 검증 3차 통과, `feat/06-standings` 커밋·push, `dev` 병합), 사용자 요청으로 `daily-work-log.md`·`file-feature-map.md`에 06 반영. 이전: 05 지난 경기 완료(Codex 교차 검증 통과, `feat/05-results` 커밋·push, `dev` 병합). 이전: 디자인 v1.6 기준 01 브랜드·공통 UI, 03 메인 일정·뉴스, 04 후기 안내·TOP 5 선정 기준을 실제 앱에 반영했다.

**최신 디자인 기준(2026-11-03, v1.6):** 대회는 하나의 체크 초안·적용·취소, 일정·팀 검색은 KST 오늘−3~오늘+17의 21일, 경기는 기본 6개→현재 조건 전체 보기/접기다. 정책과 디자인 출처는 기획 문서(PRD·기능 명세서·유저 플로우)와 Figma다. 별도 정책·인계 md 파일은 2026-11-04 사용자가 삭제했다.

**TOP 5 최신 확정(2026-11-02):** TOP 5 정책(기획 문서 PRD 15장·기능 명세서 TOP-001~003)은 00:00 첫 시도→실패 시 00:05 자동 재시도 1회→재실패 시 자동 중단·운영 알림·지연 안내·수동 복구다. 첫 시도/재시도 동안 서버의 지난주 공개 결과를 실제 기간으로 유지하고 정상 검증 후 이번 주 결과로 교체한다. 사용자 UI는 목록·경기 일정 없음·지연 안내 3종이다. 문서·Figma·앱(04, 2026-11-03)에 UI 3종으로 반영했다.

**2026-11-04 · TOP 5 하위 모델 대체(00, 사용자 결정):** 한 시도 안에서 주 모델(`TOP5_LLM_MODEL`, `gemini-3.8-flash`) 호출이 오류(503·429·시간 초과·빈/형식 오류 응답)면 남은 시간으로 하위 모델(`TOP5_LLM_FALLBACK_MODEL`, 기본 `gemini-3.5-flash-lite`)을 1회 호출한다. 주 모델 몫은 시도 모델 시간의 60%, 남은 시간이 10초 미만이면 대체하지 않는다. 둘 다 실패하면 그 시도를 실패로 기록하고 기존 TOP 5 디스코드 채널(`TOP5_ALERT_DISCORD_WEBHOOK_URL`)로 '주 모델·하위 모델 모두 실패' 알림을 보낸다(00:00 실패면 00:05 재시도 예정, 수동 복구 실패면 복구 명령 안내). 00:05 재시도까지 실패한 경우에는 기존 지연 알림(주당 1회)만 보낸다. 응답한 모델은 `top5_attempts.model`에 남는다. 00:00/00:05·지난주 유지·지연 안내·수동 복구 정책은 그대로다. 선정 결과 검증 실패는 대체 호출 대상이 아니다.

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

최종 대표 프레임: 메인49:57/49:570, 지난 경기53:593/53:995, 경기 상세52:151/52:404, TOP5 펼침128:3700/128:4408, 최종 인계62:1960을 사용한다. 삭제된 과거 변형 링크는 현재 기준으로 사용하지 않는다.

디자인 전달 기준은 Figma의 컬러 가이드·설계 반영 기준·개발 전달 기준과 이 가이드 §6.6이다.

**최종 브랜드(2026-11-03 승인·Figma 적용):** 원본은 Figma와 `frontend/public/brand/`의 최종 SVG다. 심벌55:22·파비콘264:1430·사용 크기/밝고 어두운 배경 보드264:1431을 따른다.36/32/24px 슬롯 안 실제 심벌31/27.56/20.67px, 슬레이트 워드마크#0F172A, 헤더 기준 간격8.5px다. 키 면#F8FAFC·경계#E2E8F0·화살표#2563EB, 파비콘은 공 없이 화살표만 사용한다.

**디자인 갱신(2026-11-03):** 기존9페이지의 데스크톱/모바일 기본 프레임을 유지하며 전역 헤더·TOP5·승인 로고를 반영했다. 일정 대표 전체 화면은 기본/FA컵/FA컵+EFL컵 각 기기3개를 유지한다. 팀21일·전체 보기·빈 결과·실패·뉴스·후기 팝오버는03 · 컴포넌트의 공통 원본/변형으로 제공한다. 새 전체 화면은 변경된TOP5 대진의 예정 경기 상세2개뿐이다. 공통 원본·변경 기준은 Figma(최종 인계 `62:1960`)와 기획 문서를 따른다.

**공통 원본:** Header Nav Item275:2544, TOP5 Strip159:923/Panel159:924, Competition Picker187:1946, Schedule Explorer225:2013, Feedback225:2374, Date Strip278:2752, Date Availability285:14295, News Feed279:4473, Review Header279:4567/Popover279:4492. 공통 대회 창은 메인·지난 경기 모두 체크 초안/적용/취소이며 지난 경기의 시즌 전체 조회를 유지한다.

**TOP5 최신 표현:** 띠는 데스크톱44px 한 줄·모바일72px 두 줄, 기존 글자 크기 유지. 제목·실제 표시 주 날짜·화살표를 고정하고 모든 선정 대진을 한 문구로 이어 가로 순환한다. 호버/포커스 정지·모션 감소 정적 표시를 명시했다. 주간 고정·00:00/00:05 시도·지난주 유지·list/none/delayed는 유지하며 국내 관점의 대진 관심도·대회 중요도·시즌 맥락을 이유에 반영한다. 수치 가중치와 새 공급원은 임의 확정하지 않았다.

**검수 구분:**1920/375/320 대표 화면과 변경 공통 컴포넌트의 정적 렌더·스크롤 컨테이너 구조를 확인했다.9페이지18기본 프레임에서 공통 요소 누락0,01캔버스105프레임 간 겹침0,실제 화면 프로토타입 목적지 누락0을 확인했다. 임시 검수 복제본은 삭제했다. 실제 플레이어 입력·스크롤·키보드·포커스·연속 순환·호버 정지·임의 조건 전파·실제 브라우저 파비콘 설치는 미검증이며 앱 구현 완료로 표현하지 않는다. 날짜·뉴스·선정 이유는10/29 기준 더미다.

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
| 공통 UI(버튼·뱃지·다이얼로그·하단 시트·스켈레톤·`DataState`) | 01 | 전체 | `src/components/ui/`: `Button`·`ButtonLink`·`IconButton`(`Button.tsx`), `Badge`(tone `accent`·`live`·`neutral`·`warning`·`error`(04: 최근 흐름 '패')(`info`는 예정 회색 변경으로 03에서 삭제), size `small` 12px(기본·TOP 5)·`caption` 11px(일정·뉴스)), `Dialog`(layout `center`·`sheet`·`responsive`, `compact` 시트는 헤더 아래까지만 커지고 시트 전체는 스크롤하지 않으며 자식이 스크롤 영역을 정함, `handle`은 하단 시트일 때만 손잡이·16px 여백(03 대회 선택창), `initialFocus` `dialog`·`close`, `id`)·`BottomSheet`, `Skeleton`, `DataState`(06: 선택 `partialAction` — 일부 미제공 안내 옆 조작, 없으면 기존 마크업 그대로)·`StateMessage`(오류는 Figma `57:150`대로 정보 아이콘·어두운 제목·'다시 확인' 버튼, 03에서 변경), 07: `DataState`의 선택 `emptyAction`(빈 결과 문구 아래 조작 — 팀 탐색 '검색어 지우기', 없으면 기존 마크업 그대로), `Icon`(`public/icons/`: chevron-down·left·right, menu, x, search, info, thumbs(04, Figma 엄지 16px — 싫어요는 `rotate-180`)), `cx`, 필터 칩 스타일 `chipClass()`(`chip.ts`, 03). 반경 토큰 `rounded-tile`(12px, 뉴스 카드)을 03이 추가했다. **탭(04):** `Tabs.tsx` `<Tabs items value onChange label idBase>` + `tabId()`·`tabPanelId()`(Figma Tab navigation 52:240 — 44px, 선택 굵은 파랑+2px 밑줄, 좁으면 가로 스크롤, ARIA tabs·방향키/Home/End). 06: `value`에 `null`(선택 없음 — URL의 미지원 리그·유형)을 허용하고 그때 첫 탭이 Tab 순서를 받는다. 탭 줄의 가로 스크롤 막대는 숨긴다(모바일 탭 아래 회색 막대 제거). **페이지 분할(05):** `Pagination.tsx` `<Pagination page pages onChange label?>`(Figma `53:926` — 이전·현재 주변 3개 번호·다음, 44px, 640px 이상에서만 첫·마지막 번호와 '…' 추가, 1페이지면 표시 안 함). **하이드레이션 대기(05):** `src/lib/hooks/useHydrated.ts` `useHydrated()`(서버·하이드레이션 중 false) — 다른 컴포넌트와 공유하는 쿼리 캐시를 읽는 Suspense 영역은 false일 때 서버와 같은 자리 표시를 그린다(`ScheduleSection`·`ResultsSection`). 드롭다운은 05의 `SeasonSelect`(아래 시즌 드롭다운 행) |
| 엠블럼·선수 사진·공통 대체 이미지(`TeamCrest`, `PlayerPhoto`) | 01 | 전체 | `src/components/common/TeamCrest.tsx`. 이미지 URL이 `null`이거나 로드 실패면 `public/placeholder.svg`. 로고는 `src/components/common/Logo.tsx`(`size`: `header`·`header-mobile`·`footer`) |
| API 클라이언트·응답 타입·오류 처리 | 01 | 전체 | `src/lib/api/client.ts`의 `apiFetch<T>(path, { method, query, body })`(→ `{ data, meta }`, 변경 요청에 CSRF 헤더 자동, 401 갱신 연결 자리 `setUnauthorizedHandler`), `errors.ts`의 `ApiError`(`status`·`code`·`message`·`fieldErrors`·`retryAfter`), `types.ts`(생성 타입 별칭), `query-keys.ts`, KST 포맷 `src/lib/format/kst.ts`. 백엔드는 `app/api/errors.py`의 `ApiError(status, code, message)`, `app/schemas/common.py`의 `ApiModel`·`DataResponse[T]`, 공통 경기 스키마 `app/schemas/match.py` |
| TOP 5 띠·주간 선정 | 01(표시) / 04(선정 작업·UI 3종·응답 계약·교체 감지, 2026-11-03) | 전 페이지 | `GET /api/v1/top-matches/current`·`/version`(§6.4), `src/features/top5/`(`Top5Strip`·`Top5StripFallback`, `Top5List`, 문구·표시 규칙 `model.ts`, `currentTopMatchesQuery`·`topMatchesVersionQuery`·`isOutdated()`), 백엔드 공개 조회 `app/services/top_matches.py`(`get_current_top_matches()`·`current_version()`·`shown_publication()`·`current_kst_week()`), 선정 `app/services/top5_selection.py`(`run_attempt(trigger)`), 작업 `app/sync/top5.py`(`top5_weekly`·`top5_retry`·`top5`·`top5_reconcile`), Gemini `app/providers/gemini.py`(`generate_structured()`), 운영 기준 `app/seed/top5_curation.json` |
| 의견 보내기 | 01 | 전 페이지 | `src/features/feedback/`(`FeedbackProvider`·`useFeedback().openFeedback()`, `FeedbackButton`, `FeedbackDialog`), `POST /api/v1/feedback`, 백엔드 `app/services/feedback.py`의 `create_feedback(session, payload, user_id=None)`(02가 회원 ID 전달). 저장 후 디스코드 채널 알림(`app/notifications/discord.py`의 `notify_feedback`, 백그라운드 작업·실패해도 저장 유지). 04가 같은 파일에 공통 전송 `_post()`와 TOP 5 지연 알림 `notify_top5_delay()`(별도 채널)를 추가했다 |
| 헤더 인증 영역 | 01(비회원 자리) / 02(연결) | 전 페이지 | `src/components/layout/HeaderAuth.tsx`(`layout`: `desktop`·`menu`, `onNavigate`)의 본문만 `useAuth()`로 교체 |
| 수집 작업 실행기·API-Football 클라이언트 | 01 | 03·04·05·06·08 | `app/sync/registry.py`의 `@register_job(name, schedule=...)`와 `JobContext.api_football()`(요청 수 자동 집계), 작업 모듈은 `app/sync/jobs.py`에 import 추가, 실행 `uv run python -m app.sync <job> [key=value]`. 클라이언트 `app/providers/api_football.py`의 `ApiFootballClient.get()`. 03 추가: `register_job(..., precheck=)`(DB만 보는 사전 확인이 False면 API 호출·`sync_runs` 기록 없이 건너뜀, 1분 주기 작업용), `JobPartialFailure`(일부 단위만 실패할 때 저장 가능한 식별자만 담아 `sync_runs.error_summary`에 남김). 03 작업: `reference`·`team_aliases`·`fixtures`·`fixtures_live`·`news`(§6.5). 08 작업: `team_details`·`transfers`(§6.5). 08: 공통 `upsert_teams()`는 팀 dict에 `venue` 블록이 있으면 경기장 이름·수용 인원을 저장하고 없으면 기존 값을 유지한다(`reference`가 리그 팀 목록 응답의 venue를 넘김). 네이버 클라이언트 `app/providers/naver_news.py`의 `NaverNewsClient.search()` |
| 요청 제한·CSRF | 01 | 02 이후 변경 API | `app/api/deps.py`의 `RateLimit(scope, [Limit(횟수, 초)], key_func=, global_limits=)`. 본문이 있는 경로는 라우터에 `route_class=limit.route_class()`를 지정해 본문 해석 전에 적용한다(잘못된 JSON도 집계). 본문 없는 경로는 의존성으로 써도 된다. `/api/v1` 라우터 전체에 `require_csrf` 적용 |
| 인증 상태·로그인 유도·복귀 | 02 | 09, 04 후기 작성 연결 | `useAuth()`, `requireLogin({ intent })` |
| 관심 팀 | 03(비회원 저장소·토글·일정 선별) / 02(회원 DB 동기화) | 07·08·09 | `src/features/favorites/`: `useFavorites()`(`status` `loading`·`ready`·`unavailable`, `ids`, `max`, `has(id)`, `add(id)`·`remove(id)` → `added`·`removed`·`exists`·`limit`·`unavailable`·`failed`), `<FavoriteToggle teamId teamName fullWidth?>`(Figma `52:723`/`52:737`, 거부 사유 표시 — 거부 문구는 누른 직후의 목록에 묶이고 목록이 바뀌면 지워져 같은 목록으로 돌아와도 다시 나오지 않음. 07: 5개가 차면 등록되지 않은 팀은 비활성 '최대 5개까지 등록할 수 있어요'(Figma `57:766` fav-full), 등록된 팀은 계속 해제 가능), 저장소 `store.ts`(`kt-fav-guest`, 팀 ID 배열 최대 5개, 모든 접근 try/catch, 다른 탭 `storage` 이벤트 반영, 07: 등록·해제 직전 읽은 목록이 화면 목록과 다르면 모든 구독자에 알림 — `latest()`), 메인 패널 `FavoriteSchedule`. 일정 API `GET /fixtures/next?teams=`(§6.4) |
| 팀 링크 허용 여부 | 03 | 04·05·06·07·08 | 모든 팀 참조 응답의 `detailAvailable: true \| false \| null`. 백엔드 `app/services/reference.py`의 `team_detail_lookup(session)`(현재 시즌 팀 목록이 수집된 리그(`teams_synced_at`)의 소속 팀만 `true` — 경기 적재로만 생긴 소속은 확인으로 보지 않음(08, Codex 1차 지적 2: 링크와 팀 상세 직접 URL 판정 일치). 5대 리그 팀 목록이 모두 수집됐을 때만 그 밖 팀이 `false`, 그 전에는 `null`)·`team_ref(team, lookup)`·`crest(url)`(`IMAGE_RIGHTS_ENFORCED`) |
| 경기 카드·상태 뱃지 | 03 | 04·05·08·TOP 5 | `src/components/common/MatchCard.tsx` `<MatchCard match layout="schedule"\|"stacked" withDate?>`(Figma `187:591`/`225:1918`: 테두리 카드, 카드 전체가 `/matches/[id]` 링크, 한국어 대회명, 1024px 이상 schedule은 164px 대회·시각 열 + 팀·스코어 + 상태 한 줄, 좁은 폭·stacked는 대회·시각 → 팀 → 상태, 승부차기 `PK 4:2`, 경기 중단 '중단 시점 스코어', `withDate`는 '11/5(목) 02:45'), `MatchStatusBadge.tsx` `<MatchStatusBadge match size?>`(진행 중 `63′` 초록·예정/종료/확인 필요 회색·연기/취소/경기 중단/행정 종료 주황). 표기 규칙 `src/lib/format/match.ts`(`teamName`·`competitionName`(한국어 이름, 'UEFA ' 접두 생략)·`scoreText`·`penaltyText`·`kickoffTime`·`isChanged`·`statusWord`). 백엔드 `app/services/fixtures.py`의 `to_summary()`·`fixtures_on()`·`next_for_teams()`·`team_schedule()`, 상태 변환 `app/services/match_status.py`의 `map_status()` |
| 대회 필터 | 03 | 05 | `src/components/common/CompetitionFilter.tsx` `<CompetitionFilter competitions selected onChange>`(03 반영 2026-11-02, Figma `187:564` 버튼·`187:1946` 선택창): 단일 버튼('전체 대회'·'FA컵'·'FA컵 외 1개') → 데스크톱 560px 대화상자·모바일 손잡이 있는 하단 시트(`Dialog` `handle`). 대회 이름 클릭 = 그 대회만 즉시 적용·닫힘. '전체 대회 보기' = 조건 해제. '여러 대회 선택' = 현재 명시 선택에서 시작하는 초안 체크, 'N개 선택'/'0개 선택 · 최소 1개를 선택하세요', 0개면 '선택 적용' 비활성, 취소·Esc·바깥 클릭은 기존 조건 유지. 국가/UEFA 제목은 분류만(그룹 전체 선택 없음). `selected`가 빈 배열이면 전체. 2026-11-04 개정(단일 체크 초안·적용·취소, 21일)은 §1 '최신 디자인 기준'과 `CompetitionFilter.tsx`를 기준으로 한다. **05 추가:** `season?`(지정하면 '데이터 없음' 표기를 그 시즌의 `CompetitionItem.seasons`로 판정, '선택한 시즌 데이터 없음'). 지난 경기는 선택 시즌에 `available`인 대회(+URL에 이미 선택된 대회)만 넘긴다(CMP-004) |
| 팀 검색 자동완성·별칭 사전 | 03 | 05·뉴스 분류, 07(`match_teams()` 매칭만 공유 — 팀 탐색은 자동완성 대신 목록을 거름) | `src/components/common/TeamSearch.tsx` `<TeamSearch selected onSelect description? season? placeholder?>`(combobox, 후보 여러 개·일치 없음 '다른 팀으로 바꿔 보여주지 않습니다' 상태, 입력 옆 × 또는 입력 전체 삭제 = `onSelect(null)`), `GET /api/v1/teams/search?q=&season=`(`season` 없으면 현재 시즌, 있으면 그 시즌 참가 팀 — 경기 적재·리그 팀 목록의 `team_competition_seasons` 기준, 상세 미제공 팀 포함, 미지원 시즌 404), 백엔드 `app/services/team_search.py` `search_teams(session, q, season=)`(07: 매칭·정렬을 `match_teams(session, q, teams)`로 분리 — 주어진 팀 집합에서 영문명·검색 별칭이 포함되는 팀 ID를 정확·앞부분·포함 순으로, 상한 없이 반환. 팀 탐색이 같은 함수를 쓴다), 별칭 시드 `app/seed/team_aliases.json`(P-11, 05가 2025-26 5대 리그 강등 15팀을 `searchOnly`로 추가 — 뉴스 분류 근거로 쓰지 않음) + `normalize_name()` |
| 뉴스 카드·북마크 버튼 | 03(카드) / 02(북마크 버튼·API) | 08·09 | `src/components/common/NewsCard.tsx` `<NewsCard article now>`(뱃지·제목·설명·원문 도메인·상대 시각, 카드 전체가 `/news/original?id=` 원문 이동), `NEWS_BADGE_LABELS`, 메인 영역 `src/features/news/MainNews.tsx`(뱃지 필터·6개씩 더 보기). 팀 뉴스 목록은 08 `src/features/team-detail/TeamNews.tsx`(같은 카드, `GET /news?team=`, 6개씩 더 보기) — 02가 `NewsCard`에 북마크 버튼을 넣으면 팀 뉴스에도 함께 나온다 |
| 경기 상세·기록·상대 전적 | 04 | 05·08·TOP 5 | 화면 `/matches/[id]`(`src/features/match/`: `MatchDetail`·`Scoreboard`·`StatusNotice`·`MatchRecords`(`RECORD_TABS`)·`HeadToHeadSection`·`ReviewSection`·`ReviewGuidance`·`model.ts`·`queries.ts`). 백엔드 `app/services/match_detail.py`(`save_provider_items()` — 경기 응답의 이벤트·상세 블록 저장, `ensure_records()` 요청 시 1회 보충, `read_records()`), `app/services/head_to_head.py`(`ensure_meetings()`·`ensure_form()`(`strict=True`면 실패를 예외로), `fetch_form()`·`recent_form()`·`result_for()` — 팀 최근 공식 경기는 `team_forms`에 팀 단위로 캐시돼 08 팀 상세 최근 흐름도 재사용 가능), `app/services/reviews.py`(`list_reviews(sort)`·`reviews_available()`) |
| 동시 요청 합치기 | 04 | 외부 보충 조회가 있는 전 채팅 | `app/core/locks.py`의 `single_flight(session, "kicktab-<용도>:<키>")`(프로세스 내 스레드 잠금 + 트랜잭션 advisory lock, 블록 안에서 상태를 다시 확인하고 저장, 나갈 때 commit)·`advisory_key(name)` |
| 시즌 드롭다운·시즌 목록 | 05 | 06 | `src/components/common/SeasonSelect.tsx` `<SeasonSelect seasons value onChange className?>`(Figma 트리거 `93:3198` 220×44, 목록 `65:1616`/`65:1633`: '시즌 선택' 제목, '2026-27 · 현재 시즌'·'2025-26 · 이전 시즌', listbox 팝오버·방향키/Home/End/Enter·Esc/바깥 클릭 닫기·포커스 복귀. `value` null = 미지원 시즌, '시즌 선택' 표시로 다른 시즌을 보여주지 않음), 쿼리 `seasonsQuery`(`src/features/results/queries.ts`, key `queryKeys.seasons.all`) + `GET /api/v1/seasons`, 대회별 시즌 가용성은 `GET /competitions`의 `seasons[]`. 백엔드 `app/services/results.py`의 `supported_seasons()`·`season_item()`, 라우트 `require_supported_season()`(`routes/schedule.py`, 미지원 404), 관리 시즌 `app/services/reference.py`의 `managed_seasons()`(`FIRST_SEASON`~`CURRENT_SEASON`) |
| 지난 경기 조회 | 05 | 08(팀 경기에서 지난 경기 이동 시) | `GET /api/v1/results?season=&competitions=&team=&page=`(§6.4), 백엔드 `app/services/results.py`의 `finished_results()`·`season_coverage()`, 화면 `src/features/results/`(`ResultsSection`·`useResultsParams`·`queries.ts`). 다른 화면에서는 `/results?season=2025&team=48` 같은 URL로 연결한다 |
| 리그 순위·선수 순위 | 06 | 07·08·메인 | `GET /standings?league=&season=`·`/standings/summary`·`/player-rankings?league=&season=&type=`(§6.4), 백엔드 `app/services/standings.py`(파싱 `parse_standings`·`parse_top_list`·`parse_player_pages`, 저장 `save_*` — 완전한 응답만 리그·시즌·종류 단위로 교체, 조회 `read_standings`·`read_top_list`·`read_saves`·`aggregate_saves`, `relegation_zone()`, 수집 상태 `sync_state()`·`due_leagues()`), 작업 `app/sync/standings.py`. 화면 `src/features/standings/`(`StandingsSection`·`StandingsTable`·`PlayerRankings`·`MainStandings`·`useStandingsParams`·`queries.ts`·`model.ts` — 5대 리그 목록 `LEAGUES`·`formResults`·`zoneLabel`·`rankText`·`dataStatus()`(쿼리 → `DataState` 상태: 데이터가 있는 재조회 실패는 `partial`)). 세 데이터 영역(팀 순위·선수 순위·메인 간소 순위)은 모두 `DataState`로 로딩·빈 결과·일부 미제공(갱신 실패·소속 미확인)·조회 실패를 구분한다. 다른 화면에서는 `/standings?league=78&season=2025&type=saves` 같은 URL로 연결한다 |
| 팀 탐색 목록 | 07 | 08(카드의 팀 상세 링크 대상)·메인(관심 팀 '관리'·'팀 탐색에서 등록') | `GET /api/v1/teams?league=&q=&page=`(§6.4), 백엔드 `app/services/team_browse.py`의 `browse_teams(session, league=, query=, page=)`(`PAGE_SIZE` 12, 소속 미확인 시 `MembershipUnknown`)·라우트 `app/api/routes/teams.py`·스키마 `app/schemas/teams.py`(`BrowseTeam { team: TeamRef, league: CompetitionRef }`, `TeamsMeta`). 화면 `src/features/teams/`(`TeamsSection`·`useTeamsParams`(URL `league`·`q`·`page`, 잘못된 값은 `invalid`)·`queries.ts`의 `teamsQuery`, key `queryKeys.teams.list`). 다른 화면에서는 `/teams?league=78` 같은 URL로 연결한다 |
| 리그 선수 시즌 기록 | 06 | 08 | `player_season_stats`(PK `player_id`·`team_id`·`competition_id`·`season` — 한 선수의 팀별 리그 시즌 기록 한 줄, 5대 리그 × 관리 시즌의 전체 선수). 컬럼 `position`·`number`·`appearances`·`lineups`·`minutes`·`rating`·`goals`·`assists`·`conceded`·`saves`·`yellow`·`yellowred`·`red`(없으면 NULL) + 원본 통계 블록 `raw`(jsonb), 인덱스 (`team_id`, `season`). 선수 신원은 `players`(id·name·firstname·lastname·nationality·birth_date·photo_url, 08: `profile_checked_at` — 국적 누락 시 `/players/profiles` 1회 보완 후 기록). 리그 대회 기록만 있다. 08은 명세(TEAM-002 `/players` 리그 페이지)대로 이 리그 기록만 쓰고 국내 컵·UEFA 선수 기록은 수집하지 않았다. 평점 `0`은 제공사의 '평점 없음' 자리값이라 화면에서 '—'(04 선수 평점과 같은 규칙) |
| 팀 상세 | 08 | 02(관심 팀 회원 연결)·09(관심 팀 관리에서 팀 상세 링크) | API `GET /teams/{id}`·`/fixtures`·`/squad`·`/season-stats?season=`·`/transfers?season=`, `GET /news?team=`(§6.4 '팀 상세 응답'). 라우트 `app/api/routes/teams.py`(07 목록과 같은 파일), 서비스 `app/services/team_detail.py`(파싱 `pick_coach`·`parse_squad`·`parse_statistics`·`parse_transfers`·`parse_profile_nationality`, 저장 `save_*` — 빈·잘린 응답은 기존 행을 지우지 않음, 반기 `season_of`·`half_range`·`last_refresh_day`(7/1 — 마지막 갱신일)·`final_refresh_done`(그날 이후 성공 여부)·`transfer_seasons`, 직접 URL 판정 `detail_access()` → `TeamNotFound`·`DetailUnavailable`·`MembershipUnknown`, 조회 `read_*`·`form_block`·`team_fixtures`), 모델 `app/models/team_detail.py`, 스키마 `app/schemas/team_detail.py`, 작업 `app/sync/team_detail.py`(`team_details`·`transfers`). 화면 `src/app/teams/[id]/page.tsx` + `src/features/team-detail/`(`TeamDetail`(기본 정보·모바일 4탭·URL `tab`·`stats`·`transfers`)·`TeamMatches`·`SquadTable`·`SeasonRecords`·`TeamNews`·`model.ts`(정렬·누락 표시·이적 유형 문구)·`queries.ts`), 쿼리 키 `queryKeys.teams.detail·fixtures·squad·seasonStats·transfers`, `queryKeys.news.team`. 다른 화면에서는 `/teams/50?tab=records&stats=last` 같은 URL로 연결한다 |

담당이 아닌 채팅은 같은 기능을 중복 구현하지 않는다. 공통 컴포넌트가 부족하면 담당 채팅의 구조를 확장하고 이 표를 갱신한다. 페이지 목록에서 빠졌다는 이유로 명세의 기능을 누락하지 않는다.

## 3. 진행 상태와 다음 작업

| 채팅 | 상태 | 비고 |
| --- | --- | --- |
| 00 | 첫 설계·01 착수 전 검수(2026-10-31), 01 완료 확인(2026-11-01) | 이 문서 §2·§6~§11 확정. Codex 검토 요청 사항은 §10 |
| 01 | **완료(2026-11-02) — 재검수·Codex 교차 검증 통과, `dev` 병합** | 재검수에서 TOP 5를 AI 주간 정책으로 교체(응답 `week`·`state`·`selectedAt`·`items[rank·reason·match]`, 띠·데스크톱 패널·모바일 시트 7가지 상태), 실제 실행 검수(1280·375·320, 의견 실제 제출·DB 저장·디스코드 전송), 쓰지 않는 코드 삭제(탭·드롭다운·페이지네이션·평점 표시 등). TOP 5는 04 전까지 `pending`(선정 중)으로 표시된다. 2026-11-02 정책 개정(UI 3종 등)은 01이 아니라 04에서 반영한다(사용자 결정 2026-11-02). 후속 결정은 §10.3 D-01-10·D-01-11 |
| 02 | **대기 — 08 다음에 처음부터 진행** | 이전 구현은 모두 삭제했다(브랜치 삭제, 개발 DB `0002_feedback_body_hash`, `backend/.env`의 02 항목 삭제). 확정 정책(P-01·P-02·P-03·P-04·P-10·P-12)과 §6.2 설계는 그대로 쓴다. 착수 전 §9 U-04·U-05 |
| 03 | **완료(2026-11-02) — Codex 교차 검증 통과(2차), `feat/03-schedule` 커밋·push. `dev` 병합은 00 확인 후** | 실제 API로 14개 대회·현재 시즌·5대 리그 96팀·별칭 371개, 경기(오늘−1~+15일) 289건, 네이버 뉴스 352건 수집. 메인 일정(날짜 보기·일정 UX 정책의 대회 직접 선택·팀 14일 모아 보기·URL 복귀), 비회원 관심 팀, 뉴스 분류(P-08)·원문 확인, `MatchStatusBadge`. 브라우저 실제 실행 검수 1280·375·320, 자정 전환·임박 폴링은 시계 조작으로 확인. **미검증:** 실제 진행 경기 실시간 갱신(검수 시점 진행 경기 없음), 실제 자정 경과. 1차 교차 검증 지적 6건(초기화·임박 폴링·뉴스/관심 팀 실패 처리·팀 ID 검증·여자 축구 제외)과 디자인 차이 3건을 보완했다 |
| 04 | **완료(2026-11-03) — Codex 교차 검증 통과(1차 지적 11건 보완 + Claude 확인 중 8번 회귀 1건 수정), `feat/04-match-detail` 커밋·push, `dev` 병합** | 경기 상세(상태별 영역·4탭·상대 전적/최근 흐름·후기 공개 조회·요청 시 보충 수집·종료 전환 수집 작업 `fixture_details`), TOP 5(주간 상태/공개 결과 분리·00:00/00:05 작업·Gemini 구조화 출력·검증·원자적 게시·지연 공개·디스코드 운영 알림·관리 명령·공개 버전 감지), 마이그레이션 `0006`~`0008`, 운영 시드 `top5_curation.json`(사용자 확인 2026-11-03). 실제 실행: 첫 시도 실패(잘못된 모델명, 실제 404) → 00:05 재시도 실패(제공사 503) → 지연 안내 공개·디스코드 알림 전송(운영 채널 도착 사용자 확인 2026-11-03) → 수동 복구 실패(503, 지연 유지) → Gemini 복구 후 수동 복구 성공·공개, 이어서 주 상태를 비우고 첫 시도 실패 → 00:05 재시도 성공까지 실제 Gemini로 수행. 열린 화면은 공개 버전 변경 후 새로고침 없이 35초 안에 교체. **미실행:** 실제 진행 경기 실시간 갱신(검수 시점 진행 경기 없음, 가능 시각 11/4(수) 02:45 KST — 진행 중 화면·60초 폴링은 테스트 상태로 확인), 실제 월요일 00:00/00:05 시각 경과(크론 다음 실행 11/9 00:00·00:05 KST 확인) |
| 05 | **완료(2026-11-05) — Codex 교차 검증 통과(1차 지적 4건 + 2차 표시 문제 1건 보완), `feat/05-results` 커밋·push, `dev` 병합** | 2차 보완: 잘못된 URL 조건에서 캐시된 결과 수 문구도 숨김(초기화 후 뒤로 가기). 1차 보완: ① 적재 후 갱신 실패는 저장된 결과를 그대로 보여주고 `failedCompetitionIds`로 표시(최초 미적재만 503) ② URL의 잘못된 팀·대회·페이지를 전체 조건·첫 페이지로 바꾸지 않고 '조회 조건을 확인할 수 없습니다'로 안내(조회 요청 없음) ③ 이름 없는 신규 팀이 든 경기는 저장하지 않고(이름을 만들지 않음) 그 대회를 실패로 기록, 대회별 저장 오류는 롤백 후 다음 대회 계속 — 03 `fixtures`도 일부만 저장되면 실패로 기록 ④ 2026 합계 정정: 이전 보고의 3,524는 대회별 수(적재 기록 run 29와 DB 일치)를 더할 때 UCL 234를 두 번 더한 계산 오류이며 실제 3,290경기, 데이터 누락 없음. 적재: `reference`(관리 시즌 2025·2026 함께 저장)·`fixtures_season`(2025 4,128·2026 3,290경기, 대회별 수는 API 검증 문서와 일치, 재실행 후 중복 0). 2025는 `../api-test/results/raw/` 원본 대신 API로 받았다(대회·시즌당 1회 14회, 원본 14개 파일과 경기 ID·상태·스코어·팀·킥오프 차이 0 확인 — 운영 경로와 같고 호출이 적어 파일 가져오기 코드는 만들지 않음). 과거 상세 블록은 일괄 적재하지 않고 04의 요청 시 1회 보충을 쓴다. 실제 API 호출 79회(reference 22, fixtures_season 14×3, fixtures 14, 상세 보충 1). `/results`·`SeasonSelect`·`Pagination`·팀 검색 시즌 범위·하이드레이션 경합 정리. 브라우저 실제 실행 1280·375·320. 디자인 차이는 §10.3 D-05 |
| 06 | **완료(2026-11-06) — Codex 교차 검증 통과(1차 지적 5건·2차 차단 1건 보완 후 3차 통과), `feat/06-standings` 커밋·push, `dev` 병합** | 보완: ① 저장 전 완전성 검증(팀 순위 순위 1..n·행 수 감소 금지·참가 팀 안·그 시즌 리그 3경기 이상 팀 모두 포함, 선수 순위 목록 축소 금지, 선수 페이지 마지막 외 20명·1..20명·기록 10% 초과 감소 금지 — 거부 시 기존 행·`synced_at` 유지, `failed_at` 기록, 화면 `refreshFailed`) ② `dataStatus()`가 0건 뒤 갱신 실패를 `partial`로 판정(세 영역 모두 안내 + 빈 결과 문구) ③ 소속 미확인 시 '다시 확인'(`DataState.partialAction`, Figma 57:599) ④ 메인 칩 'BUN'(Figma 49:368) ⑤ `ParsedPlayerStats.pages` 삭제. **2차 보완:** 같은 선수가 두 페이지에 나오면 거부(전체 반복·일부 겹침 1~19명, 10% 감소 허용 안에 드는 35페이지 사례를 단위·DB 실연동 회귀로 추가). 실제 API 24회(분데스리가 2026 선수 페이지 재수집, 478줄 그대로). 회귀: 1차 재현 3사례·첫 적재 잘린 표 거부·시즌 초 짧은 목록 허용(DB 실연동), 페이지·축소 규칙(단위), 0건 실패 두 경로·칩·`DataState` 마크업(프런트). 보완 중 실제 API 호출 1회(EPL 2025 순위 복구). 이하 1차 기록 — 적재(리그·시즌·종류별 행 수): 팀 순위 2025·2026 각 EPL·라리가·세리에 A 20팀 / 분데스리가·리그1 18팀(리그1 2025-26 33경기 팀 그대로), 선수 순위 4종 × 5리그 × 2시즌 = 40목록 × 20명, 선수 시즌 기록 2025 693·793·876·680·798줄, 2026 537·608·651·478·489줄(EPL·라리가·세리에 A·분데스리가·리그1, 합계 6,603줄, 선수 4,284명). 선방 2025: 순위 38·38·43·31·42명 / 제외 34·51·67·42·46명(검증 문서와 같은 수·같은 순서), 2026: 순위 42·57·62·40·40명 / 제외 10·10·17·3·7명. 실제 API 호출 누적 436회(`standings` 13, `player_rankings` 48, `player_stats` 375 — 갱신 실패 검수로 접속 불가 주소에 보낸 요청·모의 응답 실행은 제외, 복구 재수집·Codex 보완 확인 포함). 2025는 원본 파일 대신 API로 받았다(244회, 일일 예산의 약 3.5% — 운영과 같은 경로이고 원본 파일과 팀 순위·선수 순위 4종·선방 집계가 모두 일치해 파일 가져오기 코드는 만들지 않음). 재실행 후 중복 0. 브라우저 실제 실행 1280·375·320. 디자인·기획 차이는 §10.3 D-06 |
| 07 | **완료(2026-11-06) — Codex 교차 검증 통과(1차 중요 1·경미 4, 2차 중요 1·경미 1 보완 후 3차 통과), `feat/07-team-browse` 커밋·push, `dev` 병합** | 2차: 1차 지적 5건 해결 확인, 새 지적 2건(중요 1·경미 1) 보완(위 첫 단락). 보완 확인(브라우저, 입력은 스크립트로 정확한 시점을 맞춤): EPL 1 → 2페이지 → '리버풀' 입력 후 0.1초에 뒤로 = 검색어 없는 EPL 1페이지·입력 비움(3초 뒤에도 유지), 2페이지 → '맨체' 반영 → '맨체스터' 직후 blur → 뒤로 = 2페이지(기록 1단계), 같은 경로를 Enter로 = 2페이지, Enter 뒤 새 입력 = 새 기록, 1차 지적 1 경로 회귀 없음, 콘솔 오류 0. 이하 1차 보완 기록 — | 1차 결과 '보완 필요(차단 0·중요 1·경미 4)'를 모두 반영(위 첫 단락 ①~⑤). 보완 확인: 지적 1 재현 경로(EPL 2페이지 → '맨체스터' → 뒤로 → 포커스 유지 '리버풀' → 뒤로 = 2페이지, 앞으로 = '리버풀')와 한 번의 연속 입력 = 기록 1단계·리그 변경 후 새 검색 = 새 기록, 지적 2(다른 탭 선저장 거부 → 맨시티 해제 → 재등록 시 문구 없음), 지적 3(9페이지 캐시 후 EPL 수집 시각을 잠시 비우고 쿼리 무효화 → 갱신 실패 안내+페이지 초과 안내 함께, 복구 후 정상), 지적 4(`league=0`·`-1`·UEFA·컵·없는 ID 404, `abc` 422 — `tests/test_teams_rules.py`, DB 없이 실행). 테스트 수: 백엔드 DB 실연동 5개(`test_teams_db.py`) + 요청 규칙 10개(`test_teams_rules.py`), 프런트 6개(`teams.test.mjs`). 이하 1차 자체 검수 기록 — | `GET /teams`(현재 시즌 5대 리그 소속 96팀 — EPL·라리가·세리에 A 20팀, 분데스리가·리그1 18팀, 리그 필터·별칭 검색·12개씩 8페이지, 소속 미확인 503)·`/teams` 화면(리그 칩·검색·관심 팀 안내·카드·페이지·상태), `FavoriteToggle` 5개 꽉 참 상태, `DataState.emptyAction`. 자체 재검토 보완 2건(다른 탭 선저장 시 거부 안내 유지·안내 상자 갱신, 재조회 실패 시 확인된 목록 유지 — 위 첫 단락). 외부 API 호출 0회(저장 데이터만), 마이그레이션 없음. 테스트(1차 당시, 수는 위 보완 기록이 현재): 백엔드 DB 실연동(`tests/test_teams_db.py` — 전체 수·리그 순서·마지막 페이지·리그별 소속·한국어/영문/모호한 별칭·리그+검색 결합·과거 시즌·UEFA 전용 팀 제외·소속 미확인 503), 프런트(`tests/teams.test.mjs` — URL 상태·잘못된 조건·5개 꽉 참 마크업·다른 탭 선저장 알림·`emptyAction`). 브라우저 실제 실행 1280·375·320(관심 팀 등록→메인 반영→해제, 6번째 거부, 새로고침 유지, 저장소 차단(스크립트로 접근 차단을 흉내 냄), 팀 클릭 404 안내, 잘못된 URL, 소속 미확인(리그1 수집 시각을 잠시 비운 뒤 원래 값 복구)·서버 중단 조회 실패와 '다시 확인' 복구, 재조회 실패 시 확인된 목록 유지(EPL 수집 시각을 잠시 비우고 쿼리 무효화 → 복구 후 '다시 확인')). 디자인 차이는 §10.3 D-07 |
| 08 | **완료(2026-11-07) — Codex 교차 검증 통과(4차 N7·N8 보완 확인), 공유 개발 DB `0014` 적용(current head·check·이적 7,159/4,446·중복 0 확인), `feat/08-team-detail` 커밋·push, `dev` 병합** | 4차 후속 검증: ruff 통과, 기본 pytest 285개 통과, 격리 스키마에서 팀 상세 pytest 39개 및 0014 적용·되돌리기·재적용·alembic check 통과. 이적 기존 11,605건 보존, API 호출 0회, 검증 스키마 롤백. 3차 결과 '보완 필요(차단 0·중요 1·경미 2)' — 2차 지적 N1~N3 해결 확인, 새 지적 N4·N5·N6 보완(위 첫 단락). 보완 후 검사: ruff, pytest 285(+DB 67 = 352), alembic upgrade·downgrade·upgrade·check(0013), lint, tsc, npm test 33, build. 2차 결과 '보완 필요(차단 0·중요 2·경미 1)' — 1차 지적 모두 해결 확인, 새 지적 N1·N2·N3 보완(위 첫 단락). 기획 문서는 Codex가 사용자 결정 A대로 새 버전 저장(기능 명세서 v1.7 TEAM-003, PRD v1.7 16장, 유저 플로우 v1.6 UF-09·UF-11). 1차 결과 '보완 필요(차단 1·중요 3·경미 5)' — 지적 1·2·3·5·6·7·8·9 보완(위 첫 단락), 지적 4는 사용자 결정(2026-11-07) A 현행 유지 — 기획 문서 반영 완료(Codex, 기능 명세서 v1.7 TEAM-003·PRD v1.7 16장·유저 플로우 v1.6 UF-09·UF-11)(§10.3 D-08-9). 보완 후 검사: ruff, pytest 284(+DB 66 = 350), alembic check, lint, tsc, npm test 33, build. 이하 1차 전 자체 검수 기록 — 실제 실행 검수(브라우저 1280·375·320, 실제 DB·API-Football): 5대 리그 각 1팀(맨시티·바르셀로나·라치오·바이에른·앙제)+승격 팀(입스위치·데포르티보) 6개 영역, 선수 표 정렬(오름·내림·누락 뒤)·더 보기(27명 중복 0)·'—', 시즌 중 이적 선수 줄 분리(라치오 A. 구드뮌드손 = 라치오 줄 3경기 1골만), 시즌 기록·이적 이번/지난 시즌 전환(URL `stats`·`transfers`), 승격 팀 지난 시즌 빈 상태, '2027년 1월부터 집계됩니다', 경기 카드 → 경기 상세, '경기 전체 보기' → `/results?team=50`, 팀 뉴스·원문 이동·뉴스 없음(앙제), 관심 팀 등록 → 메인 '1/5' 반영 → 해제, 6번째 비활성, 저장소 차단 안내(스크립트로 접근 차단), 직접 URL(현재 팀·강등 팀 404 `TEAM_DETAIL_UNAVAILABLE`·없는 ID 404·숫자 아님 404 페이지·EPL 수집 시각을 잠시 비운 503 `MEMBERSHIP_UNKNOWN` → 복구 후 '다시 확인'), 04·05·06·07에서 들어오는 링크, 모바일 4탭, 콘솔 오류 0(의도한 404·503 응답만). 비회원 전체 흐름(메인 → 경기 상세 → 지난 경기 → 리그 순위 → 팀 탐색 → 팀 상세)의 모든 내부 링크를 요청해 확인 — 404는 `/login`·`/signup`(02)뿐. 검사: ruff, pytest 274(+DB 62 = 336), alembic upgrade·downgrade·upgrade·check, lint, tsc, npm test 33, build |
| 09 | **대기 — 02 다음** | §4 작업 원칙 1의 순서대로 |

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
- **장시간 표시 데이터(04 구현):** TOP 5 목록은 화면 활성 중 30분 주기·5분 경과 후 포커스/펼침 재조회로 경기 정보를 갱신하고, 공개 결과 교체는 `GET /top-matches/version`을 30초마다(화면 활성 중·포커스 시) 확인해 공개 버전 또는 현재 KST 주가 바뀌면 즉시 `current`를 다시 조회한다(`Top5Strip`, `isOutdated()`). 조회 실패 시 화면의 기존 결과를 유지하며, 교체 조회가 실패해도 같은 공개 버전의 다음 성공 확인 때 다시 시도한다(진행 중인 재조회는 취소하지 않음). 브라우저 검수에서 공개 버전 변경 후 열린 패널이 새로고침 없이 35초 안에 바뀌었다.
- **외부 이미지:** `TeamCrest`·`PlayerPhoto`는 `next/image`를 `unoptimized`로 쓰므로 원격 도메인 설정이 필요 없다. URL이 `null`이거나 실패하면 대체 이미지가 나온다.
- **아직 없는 경로:** `/login`·`/signup`(02)·`/mypage`(09)는 404 안내(`app/not-found.tsx`)가 뜬다. 담당 채팅이 `app/<경로>/page.tsx`를 만들면 바로 연결된다. 메인 `/`는 03, 경기 상세 `/matches/[id]`는 04, 지난 경기 `/results`는 05, 리그 순위 `/standings`는 06, 팀 탐색 `/teams`는 07, 팀 상세 `/teams/[id]`는 08이 구현했다. 모든 팀 링크(경기 상세·지난 경기·리그 순위·팀 탐색)는 `detailAvailable: true`일 때 `/teams/{id}`로 열린다(08 브라우저 확인).
- **동적 경로와 루트 레이아웃(04 처리):** `cacheComponents`에서 런타임 param 페이지(`/matches/[id]`)가 정적 셸을 갖도록 루트 레이아웃의 `usePathname()` 컴포넌트를 `<Suspense>`로 감쌌다 — `SiteHeader`의 `MainNav`(대체 UI `MainNavFallback`: 현재 메뉴 표시 없는 같은 메뉴)·`MobileMenu`(44px 빈 자리)·`Top5Strip`(`Top5StripFallback`: 같은 높이의 띠), `FeedbackProvider`의 `FeedbackDialog`(대체 UI 없음). 동적 페이지 자체는 `params`를 `<Suspense>` 안의 async 컴포넌트에서 await한다(`app/matches/[id]/page.tsx` 참고). 빌드 결과 `/matches/[id]`는 ◐ Partial Prerender. 새 레이아웃 컴포넌트가 경로·검색 파라미터를 읽으면 같은 방식으로 감싼다.
- **화면 상태의 URL 반영:** 서버 데이터를 다시 받을 필요가 없는 탭·정렬 같은 상태는 `window.history.replaceState`로 검색 파라미터만 바꾼다(Next 문서: `useSearchParams`와 동기화되고 서버 왕복 없음). `router.replace`는 동적 페이지에서 서버 왕복이 생겨 탭 전환이 늦었다(04 확인).
- **하이드레이션과 공유 캐시(05 정리):** Suspense 경계 안 클라이언트 영역이 다른 컴포넌트와 같은 쿼리(대회 목록·관심 팀 등)를 읽으면, 먼저 하이드레이트된 쪽이 받아 둔 캐시 때문에 서버 HTML과 달라질 수 있다. 그런 영역은 `useHydrated()`가 false인 동안 서버와 같은 자리 표시를 그린다(`ScheduleSection`·`ResultsSection`의 `SectionSkeleton`).
- **개발 서버 모듈 캐시:** 실행 중인 `next dev`가 수정 전 서버 모듈 인스턴스를 들고 있어 서버 렌더링이 'Cannot read properties of undefined'로 실패하고 클라이언트 렌더링으로 전환된 적이 있다(05, 쿼리 키 추가 직후). 파일을 다시 저장해도 풀리지 않으면 개발 서버를 재시작한다(의존성 재설치는 하지 않음).
- **URL 검색 파라미터:** `useSearchParams()`를 쓰는 클라이언트 영역은 `<Suspense>` 안에 둔다(메인 `ScheduleSection` 참고). 렌더 중 `Date.now()`는 개발 서버가 prerender 오류로 잡으므로 데이터가 있을 때만 읽거나 효과(effect)·쿼리 상태(`dataUpdatedAt`)를 쓴다.
- **검수 팁:** 앱의 브라우저 창이 숨겨져 있으면 `requestAnimationFrame`이 멈춰 React의 Suspense 표시 전환·hydration이 대기한다(앱 결함 아님). 스크린샷을 찍으면 프레임이 진행된다.
- **로컬 실행:** 백엔드는 `uv run python -m uvicorn app.main:app --port 8000`(설정·`.env`를 바꾸면 재시작 필요), 프런트는 `npm run dev`. Windows에서 백그라운드로 띄운 서버가 종료 후에도 남아 포트를 점유할 수 있으니 `netstat -ano`로 확인한다. **07 확인:** 이 PC의 `netstat` 상태 이름은 한국어라 `LISTEN`으로 걸러지지 않고, 실행기에서 띄운 `npm run dev`는 작업을 멈춰도 `next dev` 자식 프로세스가 남았다. 포트 확인은 `curl` 응답과 프로세스 명령줄(PowerShell `Get-CimInstance Win32_Process`)로 하고, 종료는 `taskkill /PID <부모> /T /F`로 트리째 한다. 사용자가 직접 띄운 서버(예: VS Code 터미널의 `fastapi dev`)는 종료하지 않는다.
- **Figma:** 커넥터 응답이 간헐적으로 끊기면(`MCP server connection lost`) 같은 호출을 다시 하면 된다. 페이지 전체 메타데이터는 매우 커서 파일로 저장되므로 프레임 단위로 조회한다.

**02 이전 단계 규칙(03~08)**

- 회원 로그인이 필요한 기능(회원 관심 팀 DB 동기화, 뉴스 북마크, 후기 작성·수정·삭제·반응, 마이페이지)의 UI·API·테이블은 만들지 않는다. 비회원이 쓰는 기능은 그 단계에서 끝까지 만든다: **비회원 관심 팀은 03이 사전 제작**(localStorage 저장소·`useFavorites()`·`FavoriteToggle`·관심 팀 일정·관심 팀 버튼)하고 07·08이 재사용해 마무리한다. 04는 후기 조회까지 만들었고(테이블 `reviews`·`review_reactions` 포함) 작성 API·화면이 붙을 자리는 아래 02 항목에 있다. 빈 버튼이나 '준비 중' 자리는 넣지 않는다.
- 헤더 인증 영역은 01 상태(비회원 로그인·회원가입 버튼)를 유지한다. `/login`·`/signup`은 02 전까지 404 안내다.
- 의견은 01 방식대로 모두 비회원 익명 저장(`user_id` NULL, 외래 키 없음)·IP 기준 요청 제한을 유지한다. 회원 연결·차등 제한(P-10)은 02가 붙인다.
- 마이그레이션 번호는 만드는 순서대로 이어 쓴다(03이 `0003`~`0005`·`0009`, 04가 `0006`~`0008`, 05가 `0010`, 06이 `0011`, 07은 마이그레이션 없음, 08이 `0012`·`0013`·`0014`, 다음은 `0015`). 02는 착수 시점의 다음 번호를 쓴다.

**02 로그인·회원가입(08 다음)**

- 이전 구현은 삭제됐으므로 처음부터 만든다. 착수 전 `AUTH_JWT_SECRET`(U-04)과 Gmail SMTP 계정(U-05)을 준비하고, 실제 메일로 가입·비밀번호 찾기가 끝까지 동작해야 완료다(§4 작업 원칙 3).
- (03에서) 관심 팀 출처 전환은 `src/features/favorites/useFavorites.ts` 한 곳에서 한다(반환 형태 유지). 저장소 `store.ts`는 비회원 전용으로 남기고 로그인 중에는 읽지 않는다. 뉴스 북마크 버튼은 `NewsCard` 오른쪽 위(Figma `49:462`, 44px)에 둔다.
- 앞 단계에서 넘어올 일: 비회원 관심 팀(03)에 회원 DB 동기화 연결(로그인 시 DB 목록 사용·병합 금지·로그아웃 시 로컬 복원), `NewsCard` 북마크 버튼과 `/me/bookmarks` API·`bookmarks` 테이블(BOOK-001·003, P-03 `ON DELETE CASCADE`, P-09 중복 키), 04 후기 작성·수정·삭제·반응 마무리(REV-002·003, 평가 로그인 복귀). 각 단계가 남긴 구체 인수인계는 이 항목 아래에 추가한다.
- `src/components/layout/HeaderAuth.tsx` 본문을 `useAuth()`로 교체한다(회원: 마이페이지·로그아웃, Figma `62:1475`·`81:3209`). 헤더와 모바일 메뉴가 같은 컴포넌트를 쓴다.
- `setUnauthorizedHandler`(`src/lib/api/client.ts`)에 `POST /api/v1/auth/refresh` 1회 갱신(동시 요청 합치기)을 등록한다. 서버 컴포넌트에서 `apiFetch`를 부르면 브라우저 쿠키가 전달되지 않으므로, 회원 데이터를 서버에서 조회하려면 `cookies()`를 넘기도록 확장한다.
- 의견: `routes/feedback.py`에서 인증 사용자 ID를 `create_feedback(..., user_id=)`로 넘기고, `users` 생성 마이그레이션에서 `feedback.user_id` 외래 키를 추가한다(삭제 처리는 P-03). 회원·비회원 차등 요청 제한을 붙인다(P-10). 디스코드 알림의 '작성자'는 `user_id`로 회원/비회원을 자동 표시한다.
- 의견 본문이 디스코드로 전송되므로 개인정보처리방침(P-12)에 반영한다. 정책 문서가 생기면 `SiteFooter.tsx`의 정책 항목을 링크로 바꾼다.
- 로그아웃 시 `queryKeys.me.all`을 무효화하도록 회원 데이터 key는 `me` 아래에 둔다.
- (04에서) **후기 작성·수정·삭제·반응 연결 위치와 인터페이스:**
  - 테이블은 04가 만들었다(`0007_reviews`): `reviews`(id identity, user_id uuid, fixture_id → fixtures CASCADE, rating 1~5 CHECK, body ≤300 CHECK, created/updated_at, `uq_reviews_user_fixture`), `review_reactions`(review_id → reviews CASCADE, user_id, value ±1 CHECK, PK(review_id, user_id)). `users` 생성 마이그레이션에서 두 테이블의 `user_id`에 `REFERENCES users(id) ON DELETE CASCADE`를 추가한다(P-03).
  - 조회: `GET /api/v1/fixtures/{id}/reviews?sort=popular|latest` → `ReviewList { summary: { average(null=0건), count }, items: ReviewItem[] }`(`app/services/reviews.py`의 `list_reviews()`). `ReviewItem.authorNickname`은 지금 항상 `null`(화면 '—')이므로 `users.nickname` 조인으로 채운다. 회원 본인 평가 여부·내 반응이 필요하면 `ReviewItem`에 필드를 추가한다.
  - 작성 가능 판정은 `reviews_available(fixture)`(정상 종료 normal/aet/pen만 — 행정 종료 P-05 보류, 중단·취소·상태 변경 시 숨김 P-07)를 그대로 쓰고 쓰기 API에서도 같은 함수로 거부한다. 응답 `MatchInfo.reviewsAvailable`이 화면 표시 기준이다.
  - 화면: `src/features/match/ReviewSection.tsx`. Figma `52:294`의 '로그인하고 평가하기' 버튼과 `63:1408`의 작성 영역(평점 칩·후기 입력·평가 등록)은 02 전까지 넣지 않았다(빈 버튼 금지). 정보 상자 '평점과 후기는 누구나 볼 수 있어요.' 아래에 버튼을, 기존 ReviewGuidelines 상시 노출은 최신 디자인에서 제거됐다. 02는 제목 옆 안내 팝오버(원본279:4567·279:4492)와 작성 영역63:1408/63:1675를 기준으로 연결한다. 반응 수는 지금 아이콘+숫자 텍스트(`Reactions`)이며 02가 44px 버튼으로 바꾸고 비회원 클릭 시 로그인 안내, 본인 후기는 비활성.
  - 변경 후 `queryKeys.matches.reviews(id, sort)`를 무효화한다(두 정렬 모두: `["matches", "reviews"]` 접두로 무효화).
- (08에서) **관심 팀 회원 연결:** 팀 상세 기본 정보의 관심 팀 버튼은 `<FavoriteToggle teamId teamName />` 그대로라 `useFavorites()`의 출처만 바꾸면 메인·팀 탐색·팀 상세가 함께 회원 목록을 쓴다. 팀 상세 머리말에는 `useFavorites().status === "unavailable"`일 때만 '이 브라우저에서는 관심 팀을 저장할 수 없습니다. 팀 정보는 계속 볼 수 있습니다.'가 나온다(`TeamDetail.tsx`의 `TeamHeader`) — 회원 상태에서는 저장소를 읽지 않으므로 이 안내가 나오지 않게 상태 값을 맞춘다. 회원 DB 저장 실패·5개 제한은 `FavoriteToggle`의 기존 거부 문구(`failed`·`limit`)로 표시된다.
- (08에서) **뉴스 북마크 위치:** 팀 뉴스(`TeamNews.tsx`)도 메인과 같은 `NewsCard`를 쓰므로 `NewsCard` 오른쪽 위(Figma `49:462`, 팀 상세 `52:1254`의 카드도 같은 위치) 한 곳에 버튼을 넣으면 두 화면에 함께 나온다. 북마크 로그인 복귀 `returnTo`는 팀 상세 URL(`/teams/{id}?tab=news` — 모바일 뉴스 탭 유지)로 둔다. 팀 뉴스 쿼리 키는 `queryKeys.news.team(teamId)`(메인 `news.list`와 별도)라 북마크 변경 후 무효화가 필요하면 `["news"]` 접두로 한다.

**00 확인 요청(05에서)**

- `fixtures` 테이블에 이제 현재 시즌 전체 일정(21일 밖 미래 경기 포함)과 2025 시즌이 들어 있다. 날짜 조건 없이 '가장 가까운 예정 경기'를 고르는 메인 관심 팀 일정(`next_for_teams`, FAV-004)은 21일 안에 경기가 없는 팀에도 그 뒤의 가장 가까운 경기를 보여주게 됐다(명세 '가장 가까운 일정'과 일치, 21일 밖 경기는 매일 13:00 `fixtures_season`으로 갱신). 다른 조회·작업(일정·팀 21일·실시간·종료 기록·TOP 5 후보·뉴스 참가 팀)은 날짜·시즌 조건이 있어 영향이 없음을 확인했다. 관심 팀 일정을 21일로 제한할지 결정이 필요하면 03 담당 범위에서 조건만 추가하면 된다. **Codex 검토(2026-11-05):** FAV-004에는 기간 상한이 없고 메인 팀 검색의 21일 보기와 역할이 달라 현재 동작이 타당하다.

**00 확인 요청(06에서)**

- TOP 5 선정(04, `top5_selection.py`)은 근거로 `/standings`를 대회당 1회 직접 호출한다. 06이 5대 리그 순위를 `standings`에 매시(경기일)·매일 저장하므로 `read_standings(session, league, season)`과 `sync_state(..., "standings")`(수집 시각·갱신 실패)로 DB에서 읽으면 호출을 줄일 수 있다(UEFA 순위는 06이 수집하지 않으므로 계속 API). TOP 5 코드는 고치지 않았다.

**09 마이페이지**

- (08에서) 관심 팀 관리 목록의 팀 이름은 `TeamRef.detailAvailable === true`일 때 `/teams/{id}`로 연결하면 08 팀 상세가 열린다(강등 등 허용 집합 밖 팀은 일반 텍스트 + '팀 상세 미제공', `null`은 소속 미확인 — 강등으로 표시하지 않음). 저장 뉴스(BOOK-002)의 카드는 `NewsCard`를 그대로 쓰면 메인·팀 상세와 같은 모양·원문 이동(`/news/original?id=`)이 된다.

**00 확인 요청(08에서)**

- 03 `reference` 작업의 `/teams?league=&season=` 응답에 있던 경기장 블록을 `upsert_teams()`가 함께 저장하게 했다(추가 호출 없음, 팀 목록 응답의 venue가 없으면 기존 값 유지). 03 담당 코드의 동작 변경이므로 확인을 요청한다.
- 08 수집 작업이 하루 약 384회(`team_details` 288 — 15:00 KST, `transfers` 96 — 00:00 KST)와 새 선수 국적 보완(선수당 1회)을 더한다. 06 이후 일일 예상(경기 목록 672 + 실시간 + 기준 22 + 순위·선수 약 165 + 경기일 순위 + 08 약 384)은 7,000 안이다. 팀 상세의 최근 5경기는 04 `ensure_form`(요청 시 보충, 팀당 7일 캐시)을 쓰므로 팀 상세를 처음 연 팀마다 1~2회가 더해진다.
- 03 공통 `team_detail_lookup()`을 바꿨다(Codex 1차 지적 2): 팀 목록이 수집되지 않은 리그의 팀은 경기 적재로 소속 행이 있어도 `true`가 아니라 `null`(소속 미확인)이다. 모든 화면의 팀 링크가 팀 상세 직접 URL(503 `MEMBERSHIP_UNKNOWN`)과 같은 판정을 쓴다. 평소(5대 리그 모두 수집)에는 결과가 같다.
- 제공사 이적 응답은 같은 이동을 하루 차이로 두 번 주는 경우가 많다(예: 2026-08-10·08-11 같은 선수·같은 팀·같은 유형). 08은 이런 쌍을 1건(앞 날짜)으로 저장한다(그 이틀에 반대 방향 이동이 있으면 둘 다 보존, §10.3 D-08-6). 그 밖의 제공 오류(예: 상대 팀 이름이 선수 이름인 줄)는 고치지 않고 그대로 보여준다.
- 제공사 선수 이름에 HTML 엔티티가 섞여 온다(예: `N. O&apos;Reilly` — `players` 8명, 이적 선수 이름 48줄). 08은 팀 상세 응답에서만 해제해 보여준다(`team_detail.display_text`, 저장값은 그대로). 06 선수 순위에도 해당 선수가 1명 있어 화면에 `&apos;`가 그대로 보일 수 있다 — 06 담당 범위라 고치지 않았다.

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
4. 백엔드 `uv run ruff check .`, `uv run python -m pytest`, 프런트엔드 `npm run lint`, `npm test`, `npm run build`가 통과한다. 새 API·서비스 로직에는 테스트를 추가한다.
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
| 경기 | **03 구현(`0004_fixtures`):** `fixtures`(id, competition_id, season, round, kickoff_at, kickoff_date_kst, status, finish_type, status_short_raw, status_long_raw, status_reason, elapsed, home/away_team_id, goals_home/away, score jsonb, venue_name/city, synced_at). **04 구현(`0006_match_detail`):** `fixture_details`(fixture_id PK, statistics/lineups/players jsonb 원본 블록, fetched_at, fetched_status, last_failed_at), `fixture_events`(fixture_id, seq PK, elapsed, extra, team_id, player_name, assist_name, type, detail, comments — 수집할 때마다 통째로 교체), `head_to_head`(fixture_id PK, payload jsonb, last_meeting_fixture_id, fetched_at, last_failed_at), `team_forms`(team_id PK, payload jsonb, fetched_at, last_failed_at). **05 구현(`0010_season_fixtures`):** `competition_seasons.season_fixtures_synced_at`·`season_fixtures_failed_at`(시즌 전체 목록 적재 상태 — 21일 작업의 `fixtures_synced_at`·창과 분리), 인덱스 `ix_fixtures_season_status_kickoff`(season, status, kickoff_at). 관리 시즌(2025~현재)의 `competition_seasons` 행은 `reference`가 함께 저장하고 지우지 않는다. 시즌 전체 목록을 한 번이라도 적재한 시즌은 `/leagues` 응답에서 빠져도 `no_data`로 바꾸지 않는다(가용성·시작/종료일 유지, CMP-004) | 03(목록·상태) / 04(이벤트·상세 블록·상대 전적·팀 최근 흐름) / 05(시즌 전체 적재) |
| 뉴스 | **03 구현(`0005_news`):** `news_articles`(id, url_hash unique, url, source_domain, title, description, published_at, badge, fetched_at, expires_at), `news_article_teams`(article_id, team_id). 언론사명 매핑 표(`news_sources`)는 만들지 않았다(§10.3 D-03-1). `bookmarks`(user_id, article 식별 키, 제목·설명·출처·뱃지 스냅샷, created_at, unique(user_id, 식별 키))는 02 | 03·02 |
| 후기·TOP 5 | **04 구현:** `0007_reviews` — `reviews`(id, user_id uuid(외래 키는 02), fixture_id, rating 1~5, body ≤300 NULL 허용, created/updated_at, unique(user_id, fixture_id)), `review_reactions`(review_id, user_id, value ±1, PK). `0008_top5` — `top5_weeks`(week_start PK, status running·retry_scheduled·delayed·published, auto_attempts, current_attempt_id, last_error, next_retry_at, needs_manual, alert_sent_at), `top5_attempts`(시도 ID·trigger scheduled·retry·manual·시작/마감/종료 시각·outcome·error·model·prompt_version·curation_version·candidate_count·api_requests·evidence·llm_output), `top5_publications`(version identity PK = 공개 버전, week_start, kind list·none·delayed, selected_at, attempt_id), `weekly_top_matches`(week_start, rank PK, 주별 fixture_id 유일, reason, selected_kickoff_at, attempt_id) | 04 |
| 순위 | **06 구현(`0011_standings`):** `standings`(PK competition_id·season·group_name·team_id, group_order, rank, points, played, win/draw/lose, goals_for/against/diff, form, description(그 시즌 제공 문구 그대로), provider_updated_at, synced_at), `player_rankings`(PK competition_id·season·type(goals·assists·yellow·red CHECK)·position(제공 순서), player_id, team_id, value, yellowred(red 목록만, value에 합산하지 않음), synced_at), `players`, `player_season_stats`(§2), `league_syncs`(PK competition_id·season·kind(standings·goals·assists·yellow·red·player_stats CHECK), synced_at, failed_at, failure(안전한 요약), row_count). 모두 RLS. 저장은 응답이 완전할 때만 리그·시즌·종류 단위로 한 트랜잭션에서 교체하고(재실행해도 중복 없음), 실패·불완전 응답은 기존 행과 `synced_at`을 두고 `failed_at`·`failure`만 기록한다. **완전성 기준(Codex 1차 지적 1 보완):** 팀 순위 — 그룹별 순위 1..n·팀 중복 없음, 저장된 표보다 행 수가 줄지 않음, 모든 팀이 그 시즌 참가 팀(`team_competition_seasons`) 안, 그 시즌 그 리그 경기가 3경기 이상인 팀(`REGULAR_TEAM_MATCHES`)은 모두 포함(2025 분데스리가·리그1 참가 팀 19에는 경기 2개뿐인 승강 PO 상대 파더보른·생테티엔이 있어 참가 팀 수 일치 대신 이 규칙을 쓴다. 현재 시즌도 PO 경기가 적재되면 같다). 선수 순위 — 저장된 목록보다 짧은 응답 거부(처음 적재·시즌 초 짧은 목록은 허용). 선수 시즌 기록 — §6.5 페이지 규칙 + 저장된 줄보다 10% 넘게 감소 시 거부 | 06 |
| 팀 상세 | **08 구현(`0012_team_detail`):** `team_coaches`(team_id PK, coach_id·name·photo_url·since — 이 팀 경력 중 종료일 없는 줄의 최신 시작, 없으면 coach_id·name NULL = 수집했으나 현직 감독 미제공), `squad_members`(PK team_id·player_id, number, position(제공값 Goalkeeper·Defender·Midfielder·Attacker), synced_at — 현재 선수단, 시즌 열 없음: `/players/squads`가 현재만 제공), `team_season_stats`(PK team_id·competition_id·season, payload jsonb = `/teams/statistics` 응답 그대로), `transfers`(id identity, team_id, player_id·player_name(제공값, 선수 외래 키 없음), transfer_date, direction in·out CHECK, counterpart_id·name·logo(상대 팀 제공값, 팀 외래 키 없음), type_raw('N/A'는 NULL), season, half 1·2 CHECK, 고유 인덱스(`0014`): 공통 키 `(team_id, player_id, transfer_date, direction)`에 상대 팀 ID가 있으면 `counterpart_id`를, 없으면 `counterpart_name`을 붙여 중복을 막는다. 상대 팀 이름도 없으면 NULL을 같은 값으로 본다), `team_syncs`(PK team_id·season·kind(coach·squad·statistics·transfers CHECK), synced_at, failed_at, failure, row_count). `teams`에 venue_name·venue_capacity, `players`에 profile_checked_at 추가. 모두 RLS. '고정'은 열 대신 날짜로 판정한다: 시즌 S의 이적은 (S+1)-07-01 00:00 실행(6/30까지 반영된 기록, 기능 명세서 6.2)까지 다시 쓰고 그 뒤에는 그날 이후 실행으로 한 번 성공할 때까지(처음 수집이거나 7/1 마지막 갱신이 실패한 경우) 매일 다시 쓰고, 성공하면 고정(§6.5와 같음) | 08 |

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
- **지난 경기·시즌 응답(05 구현):** `GET /seasons` → `data: SeasonItem[] { season, label('2026-27'), current }`(관리 시즌 중 `available` 대회가 하나라도 있는 시즌, 최신순). `GET /results?season=&competitions=&team=&page=` → `data: ResultsPage { season: SeasonItem, team: TeamRef \| null, matches: MatchSummary[] }`, `meta: ResultsMeta { page, size(10), total, updatedAt, failedCompetitionIds }`. `status = finished`만(일반 normal/aet/pen과 행정 awarded/walkover — `finishType`으로 구분, 행정 종료 스코어는 제공값 그대로), 예정·진행·연기·취소·중단 제외, 킥오프 최신순, 날짜 조건 없음. `season` 생략 = 현재 시즌, 미지원 시즌 404 `NOT_FOUND`(대체 없음), `competitions`는 지원 14개 대회 ID(아니면 422 — 시즌 변경 시 대회 조건을 유지하므로 그 시즌 `no_data` 대회도 받아 저장된 결과만 돌려준다), 없는 팀 404, 참가하지 않은 팀은 빈 목록, 마지막 페이지를 넘으면 빈 목록+`total`. 범위 안 `available` 대회가 하나도 적재에 성공한 적이 없으면 503 `UPSTREAM_UNAVAILABLE`. 적재 후 갱신 실패·일부만 저장된 대회는 저장된 결과를 그대로 돌려주고 `failedCompetitionIds`에 넣는다(결과 없음으로 단정하지 않음, CMP-004). 화면 URL의 팀·대회·페이지 값이 숫자가 아니면 요청하지 않고 '조회 조건을 확인할 수 없습니다'(+필터 초기화)를 보여준다 — 생략·빈 값만 '전체·첫 페이지'다(`useResultsParams().invalid`). 화면은 404·422에 서버 문구와 '필터 초기화'(팀·대회가 있을 때만), 5xx에 '다시 확인'을 보여준다. `GET /teams/search?q=&season=`(§2). `GET /competitions`의 각 항목에 `seasons: CompetitionSeasonInfo[]`(관리 시즌 전체, 최신순) 추가.
- **리그 순위 응답(06 구현):** `GET /standings?league=&season=` → `data: LeagueStandings { league: CompetitionRef, season: SeasonItem, groups: StandingGroup[{ name, rows: StandingRow[{ rank, team: TeamRef, played, win, draw, lose, goalsFor, goalsAgainst, goalsDiff, points, form(제공 W/D/L 문자열, 없으면 null), description(그 시즌 제공 문구), zone: relegation | relegation_playoff | null(description이 'Relegation…'일 때만, play-off 문구면 relegation_playoff) }] }] }`, `meta: StandingsMeta { updatedAt(마지막 성공 수집), refreshFailed(이후 갱신 실패 — 저장된 표를 그대로 보여줌) }`. `league`는 5대 리그만(컵·UEFA는 404 `NOT_FOUND`), `season` 생략 = 현재, 미지원 시즌·그 시즌 데이터 없는 리그 404, 한 번도 수집되지 않았으면 503 `UPSTREAM_UNAVAILABLE`, 수집됐지만 표가 비었으면 `groups: []`. `GET /standings/summary` → `data: { season(현재), leagues: [{ league, status: available | not_collected, refreshFailed, updatedAt, rows: 첫 그룹 상위 6행 }] }`(한 리그 미수집이 다른 리그를 가리지 않음, 5개 모두 미수집이면 503). `GET /player-rankings?league=&season=&type=goals|assists|yellow|red|saves` → `data: PlayerRankings { type, league, season, items: PlayerRankItem[{ rank, tied, player{ id, name, photoUrl }, team: TeamRef | null, value(없으면 null), yellowRed(red만) }], excluded(saves만: 선방 값이 하나라도 null인 골키퍼 수) }`, `meta: StandingsMeta`. 4종은 제공 순서 그대로(rank = 제공 위치, tied 항상 false), saves는 `player_season_stats`의 골키퍼(`position = Goalkeeper`) 줄을 선수별로 합산하고 null 줄이 있는 선수는 제외, 같은 값은 공동 순위(1,1,3, `tied`), 표시 팀은 출전이 가장 많은 팀. 잘못된 type은 422. 팀 링크는 모두 현재 시즌 허용 집합(`detailAvailable`).
- **팀 탐색 응답(07 구현):** `GET /teams?league=&q=&page=` → `data: BrowseTeam[] { team: TeamRef, league: CompetitionRef }`, `meta: TeamsMeta { page, size(12), total, updatedAt(목록 리그들의 마지막 팀 목록 수집 시각) }`. 현재 시즌(`CURRENT_SEASON`) 5대 리그의 `team_competition_seasons`만(과거 시즌·컵/UEFA 전용 팀 없음, 한 팀이 두 리그에 있으면 리그 순서상 앞의 리그 하나). `league`는 5대 리그 ID만 — 정수이면서 5대 리그가 아니면(0·음수·컵·UEFA·없는 ID) 404 `NOT_FOUND`, 정수가 아니면 422 `VALIDATION_ERROR`(Codex 1차 지적 4로 통일), `q`(1~40자, 빈 값·41자 이상 422)는 `match_teams()` 별칭 검색 — 모호한 별칭은 해당 팀 모두, 리그 조건과 함께 적용. 정렬: 검색 없으면 리그 순서(Premier League → LaLiga → Serie A → Bundesliga → Ligue 1) 뒤 표시 이름(한국어 우선) 가나다순, 검색이면 일치 정도순. 대상 리그 중 하나라도 현재 시즌 팀 목록이 수집되지 않았으면(`competition_seasons.teams_synced_at` NULL) 503 `MEMBERSHIP_UNKNOWN`(빈 목록·일부 목록으로 바꾸지 않음), 일치 없음은 빈 목록+`total` 0, 마지막 페이지를 넘으면 빈 목록+`total`, `page` 0·형식 오류 422. 외부 API 호출 없음. 화면 URL의 잘못된 리그·페이지·40자 넘는 검색어는 요청하지 않고 '조회 조건을 확인할 수 없습니다'+'필터 초기화'. 재조회 실패는 마지막으로 확인한 목록(페이지 초과 안내 포함)을 유지하고 '팀 목록을 다시 확인하지 못했습니다'+'다시 확인'. 검색 입력은 0.3초 뒤 URL에 반영하며 한 번의 연속 입력이 기록 1단계(첫 반영 push, 이후 replace). blur·Enter는 마지막 글자를 같은 단계에 반영한 뒤 연속 입력을 끝내고, ×는 새 단계. 검색창이 보내지 않은 URL 변경(뒤로·앞으로·리그·페이지·초기화)은 연속 입력을 끝내고 입력값을 그 URL로 맞춘다(보내지 않은 글자는 버림).
- **팀 상세 응답(08 구현):** 영역마다 따로 조회한다. 모든 경로의 팀 판정(`detail_access`): 없는 팀 404 `NOT_FOUND`, 허용 집합 밖(강등 등) 404 `TEAM_DETAIL_UNAVAILABLE`, 소속 미확인(허용 집합 미완성 또는 그 팀 리그의 현재 시즌 팀 목록 미수집) 503 `MEMBERSHIP_UNKNOWN`, 2³¹ 이상·0 이하 ID는 422. `GET /teams/{id}` → `TeamOverview { team: TeamRef, league: CompetitionRef, season: SeasonItem, standing, coach, venue: { status: available|not_provided|unavailable, data }, form: FormBlock(04와 같은 형태, 친선 제외 최근 5경기 최신순) }`(standing = `standings` 현재 시즌 rank·points, 미수집 unavailable; coach 행 없음 unavailable·이름 없음 not_provided). 최근 흐름만 요청 시 보충(`ensure_form`). `GET /teams/{id}/fixtures` → `{ upcoming: MatchSummary[≤3](진행 중 먼저, 예정은 킥오프 3시간 지난 미시작까지), recent: MatchSummary[≤5](종료 최신순) }`, `meta { updatedAt, failedCompetitionIds(그 팀이 이번 시즌 참가한 대회 중 시즌 목록 미적재·실패) }` — 현재 시즌 저장 경기만, 시즌 목록이 한 번도 적재되지 않았고 결과가 없으면 503. `GET /teams/{id}/squad` → `TeamSquad { league, season, players: [{ player{id, name(HTML 엔티티 해제), photoUrl}, number, position, nationality(제공 영문 그대로), stats: { appearances, minutes, goals, assists, rating(제공값 '0'은 null) } \| null }] }`, `meta { updatedAt, refreshFailed }`(선수단 미수집 503). `GET /teams/{id}/season-stats?season=` → `TeamSeasonStats { season, league, status: available|not_provided, record: { wins·draws·loses·goalsFor·goalsAgainst·cleanSheets: {home, away, total}, formation } \| null, standing }`(season은 이번·지난 시즌만, 그 밖 404. 지난 시즌에 그 리그 참가 기록이 없으면(승격 팀) 호출 없이 not_provided. 미수집 503). `GET /teams/{id}/transfers?season=` → `TeamTransfers { season, halves: [{ half: first|second, label('26-27 전반기'), period('2026년 6~12월'), start, end, state: open|not_started, arrivals, departures: [{ transferDate, playerId, playerName, counterpart{id, name(아는 팀은 한국어), crestUrl}, type }] }] }`(날짜 오름차순, 미수집 503). `GET /news?team=` → 그 팀에 연결된 만료 전 기사 최신 48개(뱃지 없는 기사 포함, `badge`로 더 좁힐 수 있음), 없는 팀 404, 뉴스가 한 번도 수집되지 않았으면 503. 화면은 영역별 `DataState`(로딩·빈 결과·일부 미제공(갱신 실패 시 마지막 확인 데이터+'다시 확인')·조회 실패)로 구분한다.
- **메인 일정 응답(03):** `GET /competitions` → `data: [{ id, nameKo, shortName, group: EPL\|LaLiga\|SerieA\|Bundesliga\|Ligue1\|UEFA, currentSeason: { season, label, availability: available\|no_data } \| null, seasons(05) }]`. `GET /fixtures?date=YYYY-MM-DD`(KST, 기본 오늘, 수집 범위 오늘−3~+17일 밖은 422) → `data: MatchSummary[]`(지원 14개 대회 전체, 킥오프·대회 순), `meta: ScheduleMeta { updatedAt, failedCompetitionIds }` — 대회·팀 필터는 화면에서 적용(날짜 빈 결과와 필터 빈 결과 구분). 한 번도 수집되지 않았거나 모든 대회가 실패하고 결과가 없으면 503 `UPSTREAM_UNAVAILABLE`, 일부 대회만 실패하면 200 + `failedCompetitionIds`. `GET /fixtures/next?teams=1,2`(양의 정수 1~5개, 아니면 422) → `data: { teams: TeamRef[], matches: MatchSummary[] }`(팀마다 진행 중 또는 가장 가까운 예정 1경기, 진행 중 우선, 맞대결 1회), `meta: ScheduleMeta`. `GET /fixtures/team?team=<id>`(03 일정 UX 후속) → `data: TeamSchedule { team: TeamRef, start, end, matches: MatchSummary[] }`(오늘−3~+17일 KST의 저장된 해당 팀 경기 전체, 킥오프 순, 외부 API 호출 없음), `meta: ScheduleMeta`. 대회 조건은 화면에서 적용, `failedCompetitionIds`는 화면이 '일부 대회 확인 실패'·'일정 없음 단정 금지'에 쓴다. 팀 ID 형식 오류 422, 없는 팀 404, 한 번도 수집 안 됨 503. `GET /teams/search?q=`(1~40자) → `data: TeamRef[]`(최대 10개). `GET /news?badge=&cursor=&size=`(size 1~24, 기본 6) → `data: NewsItem[] { id, badge, title, description \| null, url, sourceDomain, publishedAt }`, `meta: NewsMeta { nextCursor, updatedAt, stale, total, noNew }`(저장 기사도 없고 수집이 실패·미실행이면 503). `GET /news/{id}/link` → `data: { url, status: reachable\|gone\|unknown }`(원문 HEAD→GET 헤더 1회 확인, 404/410만 gone, 요청 제한 IP별 분당 30회·전체 300회).
- **TOP 5 응답(04 구현, 2026-11-03):** `GET /api/v1/top-matches/current` → `data: TopMatches { version(공개 버전, 공개된 적 없으면 null), view: list|none|delayed, week{start,end}(표시 결과의 실제 소속 주, delayed는 준비 중인 이번 주), currentWeek{start,end}(현재 KST 주 — `week`가 앞이면 지난주 유지), selectedAt, items[rank, reason, selectedKickoffAt(선정 당시 킥오프, D-01-10), match: MatchSummary(최신)] }`, `meta: { updatedAt }`(목록 경기의 `fixtures.synced_at` 최대값). 표시 규칙(`shown_publication()`): 이번 주 공개본이 있으면 그것, 없으면 바로 지난주의 list/none 공개본(실제 기간·선정 시각 그대로), 그 밖(공개 이력 없음·지난주 지연·2주 이상 전)은 이번 주 `delayed`. `GET /api/v1/top-matches/version` → `{ version, currentWeekStart }`(열린 화면의 교체 감지용). 사용자 조회는 선정 작업을 실행하지 않는다. 작업 내부 상태(선정 중·첫 실패·재시도)는 응답에 없다.
- **경기 상세 응답(04 구현):** 영역마다 따로 조회해 한 영역 실패가 다른 영역을 가리지 않는다. 없는 ID는 404 `NOT_FOUND`(다른 경기로 대체하지 않음). `GET /fixtures/{id}` → `MatchInfo { match: MatchSummary, round, seasonLabel, statusLong, statusCode(제공사 원문 — 행정 종료 사유 표시용), reviewsAvailable, headToHeadAvailable }`, `meta.updatedAt`(경기 마지막 확인). `GET /fixtures/{id}/detail` → `MatchRecords { events, statistics, lineups, players }` 각 블록 `{ status: available|not_provided|not_yet|unavailable, data }` — `MatchEvent { elapsed, extra, side, type: goal|card|subst|var|other, detail(제공사 원문), player(교체는 나간 선수), assist(교체는 들어간 선수) }`, `StatRow { key(제공사 항목명), home, away(숫자, 없으면 null), percent }`(값이 하나도 없는 항목 제외, Figma 7항목 순서 우선), `TeamLineup { side, formation, coach, startXi, substitutes[number, name, position] }`, `PlayerRating { playerId, name, photoUrl, side, rating }`(제공사 평점, 출전하지 않은 선수와 '0' 자리값 제외, 평점순), `meta.updatedAt`(마지막 상세 수집). `GET /fixtures/{id}/head-to-head` → `{ meetings{status, data: PastMeeting[≤5], summary{homeWins, draws, awayWins}}, homeForm, awayForm: FormBlock{status, data: FormMatch[≤5]{kickoffDateKst, competition, opponentName, venue, goalsFor, goalsAgainst, result W|D|L}} }`(친선 제외 공식 종료 경기, 팀 이름은 아는 경우 한국어). `GET /fixtures/{id}/reviews` → `ReviewList`(§3.1 02).
- **기존03의 팀14일 구현 이력(2026-11-02, 최신21일 디자인의 후속 반영 대상):** 위 `GET /fixtures/team`이다. URL은 `/?team=50&competitions=45&date=2026-11-05` — 팀 모드에서 `date`는 해제 시 돌아갈 날짜로 유지하고, 해제(팀 검색 해제·× 버튼·입력 전체 삭제·관심 팀 버튼 재클릭)는 `team`만 지워 그 날짜·막대 위치와 현재 대회로 복귀한다. 전체 초기화는 `/`(오늘·전체·팀 없음, 관심 팀 유지). 팀·대회 변경은 history push, 날짜 이동은 replace. 자정 기준일 변경: `useScheduleParams`의 `useKstToday()`가 다음 KST 자정(+1초)과 탭이 다시 보일 때 오늘을 다시 계산해 날짜 막대·'오늘'·날짜 미지정 보기를 새 날짜로 옮기고, 팀 조회 키(`fixtures.team(teamId, today)`)가 바뀌어 새 14일을 다시 조회한다. 팀 모드의 기간 표기는 응답의 `start`·`end`(서버 KST 기준)를 써서 표시 경기와 항상 일치한다. 브라우저 시계를 자정 직후로 바꿔 확인했고 실제 자정 경과는 미확인. 생성 타입 `TeamSchedule`·`TeamScheduleResponse` 반영.
- **프런트엔드 타입:** 백엔드 OpenAPI(`/openapi.json`)에서 `openapi-typescript`로 `src/lib/api/schema.d.ts`를 생성한다(`npm run gen:api`). 손으로 타입을 중복 작성하지 않는다.

**초기 엔드포인트 목록(담당 채팅이 세부를 확정하고 이 표를 갱신)**

| 구분 | 엔드포인트 | 담당 |
| --- | --- | --- |
| 공통 | `GET /api/v1/top-matches/current`, `POST /api/v1/feedback`(요청 `{ body, type: bug·suggestion·other, pagePath? }`, 유형 필수(사용자 결정 2026-10-31), 본문 앞뒤 공백 제거 후 1~1,000자, 성공 201 `{ data: { id, createdAt } }`) — 01 구현 | 01 |
| 인증 | `POST /auth/email-codes`, `POST /auth/email-codes/verify`, `POST /auth/signup`, `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout`, `POST /auth/password-reset`, `GET /auth/me` | 02 |
| 계정·관심 팀 | `PATCH /me/password`, `DELETE /me`, `GET /me/favorites`, `POST /me/favorites`, `DELETE /me/favorites/{teamId}` | 02 |
| 기준·일정 | `GET /competitions`, `GET /fixtures?date=`, `GET /fixtures/next?teams=`, `GET /fixtures/team?team=`, `GET /teams/search?q=` — 03 구현(§6.4 메인 일정 응답). 실시간은 같은 `GET /fixtures` 폴링으로 처리해 `/fixtures/live`는 만들지 않았다. 05가 `/teams/search`에 시즌 범위를 추가 | 03 |
| 뉴스·북마크 | `GET /news?badge=&cursor=&size=`, `GET /news/{id}/link`(03 구현, `team` 조건은 08 구현), `GET /me/bookmarks`, `POST /me/bookmarks`, `DELETE /me/bookmarks/{id}`(02, 연기) | 03·02 |
| 경기 상세 | **04 구현:** `GET /fixtures/{id}`(`MatchInfo`), `GET /fixtures/{id}/detail`(`MatchRecords`), `GET /fixtures/{id}/head-to-head`(예정·연기만, 그 밖은 409 `CONFLICT`), `GET /fixtures/{id}/reviews?sort=popular\|latest`(정상 종료만, 그 밖은 409), `GET /top-matches/version`. **02 예정:** `POST /fixtures/{id}/reviews`, `PATCH·DELETE /reviews/{id}`, `PUT·DELETE /reviews/{id}/reaction`, `GET /me/reviews` | 04·02 |
| 지난 경기 | **05 구현:** `GET /results?season=&competitions=&team=&page=`, `GET /seasons`, `GET /teams/search`의 `season` | 05 |
| 순위 | **06 구현(위 '리그 순위 응답'):** `GET /standings?league=&season=`, `GET /standings/summary`, `GET /player-rankings?league=&season=&type=goals\|assists\|yellow\|red\|saves` | 06 |
| 팀 | `GET /teams?league=&q=&page=`(07 구현, 위 '팀 탐색 응답'), **08 구현(위 '팀 상세 응답'):** `GET /teams/{id}`, `/teams/{id}/fixtures`, `/teams/{id}/squad`, `/teams/{id}/season-stats?season=`, `/teams/{id}/transfers?season=`, `GET /news?team=` | 07·08 |

### 6.5 외부 데이터 수집·캐시

- **클라이언트:** `app/providers/api_football.py`(01 작성, 03 수집 작업은 `get()`을 그대로 사용)와 `app/providers/naver_news.py`(03). 키는 `SecretStr`에서 요청 직전에만 꺼내고 헤더·URL·키를 로그에 남기지 않는다. `../api-test/tests/api_client.py`(로컬 전용)의 안전 장치(HTTP 200 + `errors` 실패 처리, 쿼터 헤더 기록, 요청 간격)를 참고한다.
- **호출 한도 보호:** 공용 속도 제한기(분당 250회 이하로 운영, Pro 한도 300회), 일일 예산 경계(기본 7,000회에서 신규 수집 중단), 타임아웃 10초, 5xx·네트워크 오류는 최대 2회 지수 백오프 재시도 후 중단. 무제한 자동 재시도·폴링 금지. 호출 수는 `sync_runs`에 기록한다.
- **쓰기 규칙:** 실패 응답으로 기존 정상 데이터를 덮어쓰거나 지우지 않는다. 정상 빈 응답과 오류를 구분해 기록한다(COM-004, CMP-004).
- **수집 작업:** `app/sync/<job>.py`의 멱등 함수 + CLI(`uv run python -m app.sync <job> [옵션]`). 자동 실행은 백엔드 프로세스 안의 APScheduler로 하되 `SCHEDULER_ENABLED=true`인 인스턴스 하나에서만 켠다. 같은 작업이 겹치지 않도록 PostgreSQL advisory lock을 쓴다. 배포 환경의 스케줄 방식은 Codex 배포 단계에서 바꿀 수 있게 작업 함수와 실행기를 분리한다.
- **요청 시 보충 조회:** 경기 상세·상대 전적처럼 사용자가 열었을 때 처음 필요한 데이터만 "DB 확인 → 없거나 만료면 외부 조회 1회 → 저장" 방식을 쓴다. 같은 키의 동시 요청은 하나로 합친다.

| 작업 | 초기 주기(실측 후 조정) | 담당 |
| --- | --- | --- |
| 대회·시즌·팀·허용 집합 | **03 `reference`:** 매일 04:00 KST + 수동. `/leagues?id=` 14회 + `/teams?league=&season=` 8회(5대 리그 + UEFA 3개, UEFA는 뉴스 주제 판정용) = 22회. 끝에 별칭 시드 적용. 별칭만 다시 넣을 때 `team_aliases`(0회) | 03 |
| 현재 시즌 경기 목록(오늘−3일 ~ +17일) | **03 `fixtures`:** 30분, 대회마다 `/fixtures?league=&season=&from=&to=&timezone=UTC` 1회(14회). 실패한 대회는 기존 행 유지 + `fixtures_failed_at` 기록 | 03 |
| 시즌 전체 경기 목록 | **05 `fixtures_season`:** 대회마다 `/fixtures?league=&season=&timezone=UTC` 1회(14회). 기본 현재 시즌을 매일 13:00 KST(유럽 경기 없는 시각)에 실행해 21일 작업이 멈췄던 동안의 종료 경기를 메운다. 과거 시즌은 수동 `python -m app.sync fixtures_season season=2025`. 경기 ID upsert라 재실행해도 중복 없음, 관리 시즌 밖은 거부. 요청 실패·저장 오류(그 대회만 롤백 후 다음 대회 계속)·응답 일부만 저장된 경우 모두 기존 행을 유지하고 `season_fixtures_failed_at`만 기록하며 성공 시각은 갱신하지 않는다. **공통 `upsert_fixtures()`(05 보완):** DB에 없는 팀이 이름 없이 오면 그 경기를 저장하지 않고(팀 이름·경기 값을 만들지 않음) 경고 로그를 남긴다. 호출한 작업은 저장 수가 응답 수보다 적으면 그 대회를 실패로 기록한다(03 `fixtures`도 같은 규칙, 실시간·종료 기록 작업은 다음 주기에 다시 받음). 상세 블록은 적재하지 않음(요청 시 보충) | 05 |
| 실시간 경기 | **03 `fixtures_live`:** 60초 주기지만 진행 중·30분 내 시작·킥오프 후 3시간 내 미시작 경기가 없으면 사전 확인에서 건너뜀(호출·기록 0). 실행 시 `/fixtures?live=<지원 대회>` 1회 + 라이브 응답에 없는 추적 경기만 `/fixtures?ids=`(20개당 1회)로 재조회(종료로 가정하지 않음) | 03 |
| 경기 상세 블록 | **04 구현:** `fixtures_live` 응답의 이벤트와 `/fixtures?ids=` 응답의 4개 블록을 추가 요청 없이 저장. **`fixture_details`(5분, 사전 확인으로 대상 없으면 건너뜀):** 최근 2일 안에 종료·중단됐는데 최종 기록이 없는 경기를 `/fixtures?ids=`(20개당 1회)로 1회 수집(종료 전환 시 1회). **요청 시 보충:** 상세를 열 때 `/fixtures?id=` 1회 — 종료·중단은 최종 상태로 한 번, 진행 중은 90초에 한 번까지, 예정은 킥오프 60분 전부터 라인업이 없을 때 10분에 한 번, 연기·취소는 요청 없음. 실패는 `last_failed_at`만 기록하고 5분간 재요청하지 않으며 기존 데이터를 덮어쓰지 않는다. 받은 적 없이 실패한 블록은 지금 다시 조회하는 경우(진행·종료·중단, 킥오프 60분 안의 예정)에만 `unavailable`, 그 밖의 예정·연기는 `not_yet`(라인업 발표 전). 같은 경기 동시 요청은 `single_flight`로 1회로 합치고 잠금 안에서 실패 쿨다운을 다시 확인한다 | 04 |
| 상대 전적·팀 최근 흐름 | **04 구현(요청 시·TOP 5 근거):** 상대 전적 `/fixtures/headtohead?h2h=A-B&last=10`(친선·미종료 제외 후 5경기 미만이고 응답이 꽉 찼으면 `last` 없이 1회 더) — 경기당 1회, 수집된 새 맞대결이 끝난 뒤에만 갱신. 팀 최근 흐름 `/fixtures?team=X&last=10`(같은 기준, 부족하면 `last=30` 1회) — 팀당 캐시, 그 팀의 새 결과가 수집되거나 7일이 지나면 갱신 | 04 |
| 순위 | **06 `standings`:** 매시 10분 확인(사전 확인은 DB만 — 대상이 없으면 호출·기록 없음). 현재 시즌 리그별로 경기일(그 리그 경기가 오늘 KST 날짜에 있거나 4시간 안에 킥오프)이면 55분마다, 아니면 23시간마다 `/standings?league=&season=` 1회. 직전 시도(성공·실패)에서 55분이 안 지났으면 건너뜀. 이전 시즌은 저장된 적이 없을 때만(보관). 수동 `python -m app.sync standings season=2025 [league=61] [force=1]`. 하루 5~약 120회(경기일 리그 수 × 시간) | 06 |
| 선수 순위·선수 시즌 기록(선방 집계) | **06 `player_rankings`:** 매일 14:00 KST, 리그마다 `/players/topscorers`·`topassists`·`topyellowcards`·`topredcards` 4회(현재 시즌 20회). **06 `player_stats`:** 매일 14:20 KST, 리그마다 `/players?league=&season=&page=` 전체 페이지(2026-11-06 기준 현재 시즌 139페이지, 2025-26은 188페이지). 페이지가 모두 모이고(1..total, 마지막 외 페이지는 정확히 20명·마지막은 1~20명 — 2025-26 원본 188페이지 확인, 같은 선수가 두 번 나오지 않음 — 제공사는 선수를 한 번만 주므로 반복은 페이지 밀림·반복이며 그만큼 다른 선수가 빠진 것, `total = 0`인 정상 빈 응답은 빈 결과), 저장된 기록보다 10%를 넘게 줄지 않고(`PLAYER_SHRINK_TOLERANCE`) 같은 선수·팀 줄이 페이지 사이에서 다르지 않을 때만 저장, 아니면 그 리그를 실패로 기록하고 다음 날 다시 받음. 두 작업 모두 이전 시즌은 저장된 적이 없을 때만, 수동 `season=2025 [league=] [force=1]`로 리그를 나눠 실행할 수 있다. 예상 일일 호출(06 전체): 약 165회 + 경기일 순위 | 06 |
| 감독·선수단·팀 시즌 기록·국적 보완 | **08 `team_details`:** 매일 15:00 KST(선수 시즌 기록 14:20 뒤). 현재 5대 리그 팀(리그 팀 목록이 수집된 리그만, 미수집 리그는 실패로 기록)마다 `/coachs?team=`·`/players/squads?team=`·`/teams/statistics?team=&league=&season=`(이번 시즌) 3회 = 288회. 지난 시즌 기록은 그 팀이 그 리그를 뛴 시즌만 저장된 적이 없을 때 1회(현재 83팀, 이후 0). 이어서 선수단 중 국적이 없고 아직 조회하지 않은 선수마다 `/players/profiles?player=` 1회(조회 후 `profile_checked_at`, 실패는 다음 날 다시). 단위(팀×종류)는 KST 하루에 한 번 — 마지막 시도(성공·실패)가 이전 KST 날짜일 때만 다시 받는다(낮에 수동 실행해도 다음 정시 실행을 건너뛰지 않음)(사전 확인은 DB만 — 대상 없으면 호출·기록 0). 저장 전 완전성 검증(Codex 1차 지적 1): 선수단은 18명 이상이고 저장된 선수단보다 25%를 넘게 줄지 않을 때만(`MIN_SQUAD`·`SQUAD_SHRINK_TOLERANCE`, 2026-11-07 저장 96팀 최소 24·평균 31명), 시즌 기록은 경기 수·승무패·득실 합계가 모두 숫자이고 경기 수 = 승+무+패, 모든 항목의 홈+원정 = 합계(Codex 2차 N1)이며 저장된 기록보다 경기 수가 줄지 않을 때만(`check_statistics`, 저장 179건 모두 통과). 거부되면 저장값과 성공 시각을 그대로 두고 실패를 기록. 현직 감독은 시작일이 오늘(KST) 이후인 재임 줄을 빼고 고름. 국적 보완은 다른 선수의 응답이면 조회 완료로 기록하지 않고 다음 날 다시(빈 응답은 '프로필 없음'으로 완료). 수동 `python -m app.sync team_details [team=50 \| league=39] [force=1]` | 08 |
| 이적 | **08 `transfers`:** 매일 00:00 KST(15:00 UTC), 팀마다 `/transfers?team=` 1회 = 96회. 응답 중 그 팀이 입단·이적한 줄만, 미래 날짜 제외, 하루 차이로 반복된 같은 이동은 1건(상대 팀 ID가 같을 때만, 그 두 날짜에 반대 방향 이동이 있으면 둘 다 보존 — Codex 1차 지적 8·2차 N2). 이 응답으로 쓸 수 있는 시즌 = 갱신 기간((S+1)-07-01 00:00 실행까지 — 6/30까지 반영된 기록을 받음) 안이거나, 그 날 이후 실행으로 저장된 적이 없는 관리 시즌(처음 수집, 또는 7/1 마지막 갱신이 실패한 시즌 — 성공할 때까지 매일 다시, 그동안 화면은 마지막 확인 기록과 갱신 실패 안내, Codex 1차 지적 3) — 시즌 단위로 통째 교체(재실행해도 중복 없음). 한 요청이 쓰려던 시즌 모두에 성공·실패를 기록. 저장된 시즌보다 max(2, 10%)를 넘게 줄어든 응답은 거부(`check_transfers`). 같은 수동 옵션 | 08 |
| 뉴스 | **03 `news`:** 매시 정각, 네이버 검색 8개 검색어(프리미어리그·라리가·세리에A·분데스리가·리그앙·챔피언스리그·유로파리그·컨퍼런스리그) × 최신 100건 = 8회. 게시 후 `NEWS_RETENTION_HOURS`(기본 72) 지난 기사는 저장하지 않고 삭제 | 03 |
| TOP 5 선정 | **04 구현:** `top5_weekly`(월 00:00 KST cron, 그 주 첫 시도만)·`top5_retry`(월 00:05 KST 고정, 첫 시도 실패·미실행일 때만)·`top5_reconcile`(60초, 만료된 중단 작업의 상태 복구만, 새 선정 없음)·`top5`(관리 명령 `uv run python -m app.sync top5`, 이번 주가 공개되지 않았을 때만). 시도마다 `TOP5_ATTEMPT_TIMEOUT_SECONDS`(240초) 시간 제한, 주 단위 advisory lock, 게시는 '현재 KST 주·현재 시도·실행 중·마감 전'일 때만(행 잠금·조회 대기 후 시각 재확인). 현재 주 공개 결과를 먼저 선택하므로 지난주 작업의 늦은 종료가 새 주 결과를 가리지 않는다. 첫 시도는 00:05 슬롯 10초 전까지 끝나도록 제한한다. 중단된 첫 시도는 고정 재시도 슬롯을 유지하고, 두 번째 중단 또는 재시도 슬롯+60초까지 놓친 경우 지연 공개·운영 알림 후 수동 복구로 넘긴다(자동 선정 추가 없음). 지난주는 내부 상태만 정리하고 새 공개 버전·알림을 만들지 않는다. 근거 수집은 daemon 작업자 4개로 실행하며 취소 후 대기 작업은 시작하지 않는다. 이미 시작한 HTTP는 기존 제공사 시간 제한을 따르고, DB 각 트랜잭션의 SQL·잠금 대기는 최대 5초(근거 수집은 시도 잔여 시간 이내)다. 입력: 일정 신선도 확인(90분 안·실패 대회 없음) → 후보(그 주 KST 킥오프·NS·미시작) → `/standings`(리그·UEFA, 대회당 1회) + 팀 최근 흐름·상대 전적(캐시 재사용, 병렬 4) + 운영 시드 → Gemini 1회 → 검증(후보·주간·중복·개수 min(5,n)·순위·이유 한 줄 60자) → 원자적 게시. 후보 0건은 Gemini 없이 `none` 공개. 두 번째 자동 실패는 `delayed` 공개 + 디스코드 알림 1회(실패해도 재시도 없음). 첫 실행 API-Football 391회(캐시 비어 있을 때)·81초, 캐시가 차면 8회 | 04 2026-11-04: 주 모델 호출 오류 시 같은 시도에서 하위 모델 1회 대체, 둘 다 실패하면 운영 알림(§1 'TOP 5 하위 모델 대체') |

- **자동 실행(03):** 위 03 작업은 `SCHEDULER_ENABLED=true`인 백엔드 인스턴스 하나에서만 자동 실행된다(로컬 기본 false — 개발 중에는 `uv run python -m app.sync <job>`으로 수동 실행). 예상 일일 호출: 경기 목록 672회 + 실시간(경기 시간대만, 1~2회/분) + 기준 22회, 네이버 192회.
- **2025 시즌 과거 데이터(05 적재 완료):** `fixtures_season season=2025`(14회)로 API에서 받았다. `../api-test/results/raw/`의 2025 원본 14개 파일과 비교해 경기 수·ID·상태·스코어·팀·킥오프 차이 0을 확인했고, 원본을 쓰면 아끼는 호출이 14회뿐이라 운영과 같은 API 경로 하나만 둔다(파일 가져오기 코드 없음). 과거 경기 상세 블록은 일괄 적재하지 않고 상세를 처음 열 때 1회 보충한다(04). 일괄 적재가 필요해지면 `/fixtures?ids=` 20개당 1회 — 2025 종료 4,125경기 기준 약 207회.
- **실시간 화면 갱신:** 웹소켓 없이 클라이언트 폴링(진행 중 경기가 화면에 있을 때 30~60초)으로 한다. 화면에 마지막 갱신 시각을 표시한다. **03 구현:** `src/features/schedule/queries.ts`의 `liveRefetchInterval()` — 진행 중·시작 30분 전~킥오프 후 3시간 미시작 경기가 있으면 60초, 없으면 목록의 다음 경기가 그 구간에 들어서는 시각에 1회 재조회한 뒤 60초 폴링으로 전환, 숨김 탭에서는 멈춤. 재조회가 실패해도 이미 보인 목록은 유지하고 '최신 일정으로 갱신하지 못했습니다'를 함께 표시한다(일정·관심 팀·뉴스 공통). 실제 경기 시간 검증(V-04) 전에는 지연 시간을 보장한다고 안내하지 않는다. **04 경기 상세:** 진행 중 기록은 60초, 예정 라인업은 킥오프 60분 전부터 10분 간격으로 발표 전까지 재조회한다(이전에는 해당 구간 진입 시 1회 재조회). 상태 전환 시 최종 기록을 즉시 한 번 더 조회한다. 재조회 실패는 기존 정보·기록과 재시도 안내를 함께 유지하고, 진행 경기의 마지막 제공사 확인에서 3분이 지나면 성공 응답이 없어도 지연 경고를 표시한다. 중단 경기는 타임라인만 제공한다. 상세 블록의 최초 보충 조회 실패는 예정 경기라도 `unavailable`이며 발표 전으로 바꾸지 않는다. 상대 전적·팀 흐름 실패는 HTTP 200 블록이어도 재시도 버튼을 제공하고, single_flight 잠금 안에서도 5분 실패 제한을 다시 확인한다(TOP 5의 strict 조회는 기존 기준 유지).
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
  - 색상 토큰: `bg/canvas #F8FAFC`, `bg/surface #FFFFFF`, `bg/subtle #F1F5F9`, `bg/selected #EFF6FF`, `text/primary #0F172A`, `text/secondary #475569`, `text/muted #64748B`, `text/inverse #FFFFFF`, `action/primary #2563EB`, `action/hover #1D4ED8`, `action/soft #DBEAFE`, `action/disabled #E2E8F0`, `border/default #E2E8F0`, `border/strong #CBD5E1`, `border/focus #93C5FD`, `status/live #047857`, `status/live-bg #ECFDF5`, `status/warning #B45309`, `status/warning-bg #FFFBEB`, `status/error #B91C1C`, `status/error-bg #FEF2F2`, `brand/key #F8FAFC`, `brand/arrow #2563EB`, `brand/rim #E2E8F0`(2026-11-03 Figma 승인 브랜드 토큰. 앱 토큰·SVG는 후속 구현에서 별도 반영). 블루는 주요 동작·선택·링크에만 쓰고, 진행 중·주의·오류는 색과 상태명을 함께 표시한다.
  - 로고: 승인 심벌55:22·80×48 비율+Inter Bold 슬레이트 워드마크. 헤더36/모바일32/푸터24px 슬롯, 실제 심벌31/27.56/20.67px. 데스크톱 간격8.5px, 최종 SVG는 `frontend/public/brand/`에 있다.
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
| 백엔드 설정(01, 코드 기본값 있음) | `APP_ENV`(local), `CORS_ORIGINS`(CSRF Origin 허용 목록 겸용, 기본 `["http://localhost:3000"]`), `TRUSTED_PROXIES`(기본 `["127.0.0.1","::1"]`), `SCHEDULER_ENABLED`(false), `NEWS_SCHEDULER_ENABLED`(false, 뉴스만), `API_FOOTBALL_BASE_URL`, `API_FOOTBALL_DAILY_BUDGET`(7000), `API_FOOTBALL_PER_MINUTE`(250) | 목록 값은 JSON 배열 문자열 |
| 백엔드 `.env`(비밀, 01 추가) | `FEEDBACK_DISCORD_WEBHOOK_URL`(의견 알림 디스코드 웹후크, 비어 있으면 알림 꺼짐, §9 U-06) | 사용자가 직접 입력 |
| 백엔드 `.env`(비밀, 04용·사용자 입력 2026-11-02) | `GEMINI_API_KEY`(TOP 5 주간 AI 선정, Google AI Studio의 Gemini API 키 — 공식 SDK 표준 이름. `GOOGLE_API_KEY`는 함께 두지 않는다), `TOP5_ALERT_DISCORD_WEBHOOK_URL`(TOP 5 운영 알림 전용 디스코드 채널 웹후크, 의견 알림과 분리) — 이름은 `backend/.env.example`에 적혀 있음 | 사용자가 직접 입력. **04 연결 완료:** `app/config.py`의 `gemini_api_key`·`top5_alert_discord_webhook_url`(SecretStr), `top5_llm_model`(기본 `gemini-3.8-flash`), `top5_attempt_timeout_seconds`(기본 240, 비밀 아님). 키는 SDK 클라이언트에 직접 넘기고(`google-genai==2.34.0`, SDK 재시도 끔·요청 시간 제한은 밀리초) 환경 변수 조회에 의존하지 않는다. 비밀 아닌 설정 `TOP5_LLM_MODEL=gemini-3.8-flash`(무료 등급 중 최상위 모델, 사용자 결정 2026-11-02 — `gemini-3.5-flash`는 지원 종료되어 3.6으로 자동 연결됨)는 `.env`에 들어 있고 코드 기본값도 같게 둔다. 무료 등급은 입력이 Google 제품 개선에 쓰일 수 있으므로 공개 경기 데이터만 보낸다. 무료 한도는 AI Studio 사용량 화면에서 확인한다 |
| 백엔드 설정(00 추가 2026-11-04, 비밀 아님) | `TOP5_LLM_FALLBACK_MODEL`(기본 `gemini-3.5-flash-lite`, 무료 등급 하위 모델. 비우면 대체 없음. 주 모델과 같으면 대체하지 않음) | `.env`·`.env.example`에 기본값으로 적어 둠 |
| 백엔드 `.env`(추가 예정) | `AUTH_JWT_SECRET`(02), `SMTP_HOST`·`SMTP_PORT`·`SMTP_USERNAME`·`SMTP_PASSWORD`(비밀)·`EMAIL_FROM`(02)| 추가하는 채팅이 이 표를 갱신 |
| 백엔드 설정(05, 코드 기본값 있음) | `FIRST_SEASON`(2025 = 2025-26, 관리 시즌의 시작. 관리 시즌 = `FIRST_SEASON`~`CURRENT_SEASON`) | `.env`에 넣지 않아도 동작 |
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
| DB | Supabase PostgreSQL `kicktab-dev`(서울), Direct connection 5432, 현재 환경에서 IPv6 접속. Psycopg 3, `sslmode=verify-full` + `certs/supabase-ca.crt`. 테이블 `sync_runs`·`feedback`, 03의 기준 데이터·경기·뉴스 7개(모두 RLS 켜짐·정책 없음, 현재 리비전 `0009_fixture_coverage`). Data API 꺼짐. **현재 DB는 이 프로젝트 하나뿐**이므로 개발 중 마이그레이션·롤백 검증도 여기서 한다(운영 DB 분리는 §10 C-07) |
| 버전 관리 | Git 저장소 루트 `kick-tab/apps/`, 원격 `main`·`dev`(§11) |

**2026-10-31 00 채팅 실행 확인:** 백엔드 `ruff check` 통과, 기반 테스트 6개 통과, DB 인증·`SELECT 1`·TLS 확인 통과(읽기 전용), 프런트엔드 `npm run lint`·`npm run build` 통과. 개발 서버 실행은 하지 않았다.

명령은 각 앱 폴더에서 실행한다.

| 위치 | 설치·실행 | 검사 |
| --- | --- | --- |
| `frontend/` | `npm ci` → `npm run dev` | `npm run lint`, `npx tsc --noEmit`, `npm test`(04: Node 기본 테스트 실행기, `tests/*.test.mjs`, 추가 의존성 없음), `npm run build` |
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
| U-07 | **04 선행:** `backend/.env`의 `GEMINI_API_KEY`(Google AI Studio → Get API key, 무료 등급, 모델 `gemini-3.8-flash`)와 `TOP5_ALERT_DISCORD_WEBHOOK_URL`(TOP 5 알림용 새 채널의 웹후크)에 값 입력. 빈 줄은 00이 미리 추가함(2026-11-02). 비밀 값이므로 채팅·문서에 쓰지 않는다. **완료(2026-11-02 입력, 04 연결)** | — |

## 10. 미확정 정책·Codex 검토 요청

### 10.1 제품 정책 결정 대기 — 결정 전에는 해당 기능을 "제공 보류"로 구현

| ID | 결정 대상 | 영향 채팅 | 00 제안(결정 아님) |
| --- | --- | --- | --- |
| P-01 | 인증 메일 발송 공급자 | 02 | **결정(2026-11-01):** 공급자에 묶이지 않는 SMTP 발송으로 구현한다. 도메인이 없는 지금은 Gmail SMTP(`smtp.gmail.com:587`, STARTTLS, 앱 비밀번호, 하루 약 500통 한도)로 실제 발송한다. 공개 전 도메인을 확보하면 Resend·Amazon SES 등의 SMTP 정보로 설정값만 바꿔 교체한다(코드 변경 없음). Gmail 발신은 스팸함 분류 가능성이 있어 공개 운영용으로는 교체를 전제로 한다 |
| P-02 | 소셜 로그인 제공 여부, 같은 이메일 계정 연결 방식 | 02 | **확정(사용자 확정 2026-11-01):** 초기에는 이메일 가입만. 카카오·구글은 앱 등록 후 추가. 같은 이메일 계정을 자동 연결하지 않고, 이미 가입된 이메일이면 기존 로그인 방식으로 안내 |
| P-03 | 회원 탈퇴 시 후기·반응·북마크·의견 처리, 같은 이메일 재가입 | 02·03·04·09 | **확정(사용자 확정 2026-11-01):** 관심 팀·북마크·반응·후기 삭제(후기는 집계에서 제외), 의견은 회원 연결만 해제. 탈퇴 후 같은 이메일로 재가입 가능(새 계정, 이전 데이터 복구 없음). 탈퇴 확인 절차는 Figma 탈퇴 다이얼로그(`62:1800`)를 따르고, 처리 후 로그아웃 상태로 메인 이동 |
| P-04 | 닉네임·비밀번호 규칙(길이·허용 문자·금칙어) | 02 | **확정(사용자 확정 2026-11-01):** 닉네임 2~12자 한글(완성형)·영문·숫자, 중복 불가. 비밀번호 8~64자, 영문과 숫자를 각각 1자 이상 포함. 금칙어 목록은 초기 범위에서 두지 않음 |
| P-05 | 행정 종료(AWD·WO) 경기의 평가 제공 | 04 | 평가는 결정 전 제공 보류. TOP은 신규 후보에서 제외하되 선정 후 행정 종료로 바뀐 항목은 상태를 표시하고 유지(2026-11-01). **04 적용:** `reviews_available()`이 normal·aet·pen만 허용 — 행정 종료 상세는 경고 안내와 제공사 사유(`statusLong`·`statusCode`), 평가 영역 없음 |
| P-06 | TOP 5 주간 교체·실패 복구 | 04·관련 UI | **2026-11-02 사용자 확정:** 00:00 첫 시도→실패 시 00:05 자동 1회 재시도→재실패 지연 안내/운영 알림/수동 복구. 공개 전 서버 지난주 결과를 실제 소속 기간으로 유지. 검증 성공 즉시 교체·공개 후 고정. 공개 UI 3종, 오류별 화면 없음. 시도별 시간 제한·중복 실행 방지·알림·관리 명령·클라이언트 완료 감지는 실제 구현 검증 대상 |
| P-07 | 경기 상태 변경 시 기존 평가 처리(D-07 잔여) | 04 | 종료→중단·취소 등 평가 불가 상태로 바뀌면 숨김 처리 후 원복 시 재노출. **04 적용:** 평가 노출을 현재 상태(`reviews_available()`)로 매번 판정해 데이터는 지우지 않고 숨김·재노출된다 |
| P-08 | 뉴스 대회/팀 분류 세부 규칙, 언론사명 매핑 방식(D-09) | 03 | **03 적용(2026-11-02, 사용자 피드백 반영):** 분류는 `app/services/news_classify.py`(AI 미사용, 제목·설명만): 대회명이 명시돼야 하고, 기사의 **주제**여야 한다 — 제목에 대회명이 있거나, 주체 팀(제목의 팀, 제목에 팀이 없으면 설명에 처음 나오는 팀)이 이번 시즌 **바로 그 대회**(UCL·UEL·UECL 구분)에 참가할 때만 인정. MLS·사우디 등 다른 리그 맥락이면 제목 팀 경로만 인정(예: 'EPL도 아닌데' 손흥민 LAFC 기사 제외, 과거 UEL 우승 회고 기사 제외). UEFA가 국내 리그보다 우선, 국내 리그 2개 이상·근거 없음은 제외, AFC·다른 나라 리그는 해당 뱃지 근거 제외, 여자 축구(여자축구·위민·WSL·라리가F·'여자 프리미어리그' 등)·다른 종목·토토는 팀 연결 전에 기사 전체 제외(교차 검증 반영, 남자 팀 ID 연결 방지), 팀도 대회 단어도 축구 맥락 단어도 없는 기사(광고·제휴 등) 제외. 팀은 `for_news` 별칭만(모호한 별칭·도시명과 겹치는 짧은 별칭 제외), 여러 팀 연결. 중복은 정규화 원문 URL 해시와 같은 제목으로 1회. 표본 40건 사람 판정(주제 기준 적용 후): 대회 뱃지 적합 37건, 부적합 3건(축구 외 시위 기사·칼럼·이적설 기사의 부수 언급) — 규칙 기반 한계로 보고. Codex 교차 검증 표본 28건: 적합 24·오분류 1(밀너 마라톤 기사가 과거 챔피언스리그 이력 언급으로 UEFA)·주제 재검토 3 — 과거 이력·부수 언급은 보정 표본 후보. 참가 팀 정보는 `team_competition_seasons`(리그·UEFA 팀 목록)를 쓴다. **출처 표시:** 2026-11-02 최신 사용자 결정(언론사 표시명 제외, API 검증 문서)에 따라 매핑 표 없이 원문 도메인만 표시 — §10.3 D-03-1 |
| P-09 | 북마크 중복 키·보존 범위(D-10) | 02·09 | 원문 링크 정규화 해시를 중복 키로 사용, 보관 항목은 설정값 |
| P-10 | 의견 스팸 방지·보존 정책(D-11 잔여) | 01·02 | **01 적용(사용자 결정 2026-10-31):** ① IP별 분당 3회·일 20회 + 서비스 전체 분당 20회·일 300회(메모리 기반, IP는 DB에 저장하지 않음, 잘못된 JSON을 포함한 형식 오류 요청도 횟수에 포함) ② 허니팟 입력칸(`website`, 사람에게는 보이지 않음 — 값이 있으면 저장·알림 없이 400) ③ 중복 본문 차단(공백·대소문자를 정규화한 SHA-256을 `feedback.body_hash`에 저장, 24시간 안의 같은 본문은 발신자와 무관하게 409 `FEEDBACK_DUPLICATE`, 동시 제출은 본문 해시별 트랜잭션 잠금으로 직렬화). **02 예정:** 회원·비회원 차등 제한 — 회원은 사용자 ID 기준, 비회원은 IP 기준으로 더 엄격하게(제안값: 회원 분당 3회·일 20회, 비회원 분당 2회·일 5회, 02에서 확정). `RateLimit`의 `key_func`·제한값을 인증 상태에 따라 고르는 의존성으로 구현. CAPTCHA는 실제 남용이 확인될 때만 검토. 보존 기간은 운영 전 결정. 의견 본문이 디스코드로 전송되므로 개인정보처리방침(P-12)에 외부 전송 사실을 반영 |
| P-11 | 팀 별칭 사전 구축·관리 방식(D-16) | 03 | **03 적용(2026-11-02):** `backend/app/seed/team_aliases.json`(현재 시즌 5대 리그 96팀 한국어 이름·한국어/영문 별칭, `searchOnly`, `ambiguous` 묶음) → `uv run python -m app.sync team_aliases`(또는 `reference` 끝에서 자동). 여러 팀 표현(레알·시티·유나이티드·맨체스터·밀란·마드리드·보루시아·파리 등)은 검색에서 후보 선택, 뉴스에서 근거 제외. 2026-11-04부터 5대 리그 밖 UEFA 팀은 `uefa_team_names.json`의 한국어 이름과 별칭도 검색할 수 있다. 이름 미등록 팀은 영문으로 표시한다 |
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
| D-04-1 | 비회원 '로그인하고 평가하기' 버튼(Figma `52:294`) — `/login`이 02 전까지 없음 | 빈 버튼 금지 원칙대로 넣지 않고 안내 문구만 표시. 02가 연결(§3.1) | 02에서 연결 |
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
| D-05-3 | 페이지 분할(Figma `53:926`: 이전·번호 3개·다음) ↔ 2025-26 전체 413페이지 | 모바일은 Figma 그대로, 640px 이상에서 첫·마지막 번호와 '…'를 더해 마지막 페이지를 한 번에 이동 | 데스크톱 첫·마지막 번호 추가 유지 |
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
| D-07-3 | 5개 꽉 참(`57:766` fav-full: 안내 '관심 팀 5 / 5 · 다른 팀을 해제한 뒤 추가하세요.'+비활성 '최대 5개까지 등록할 수 있어요') ↔ 대표 프레임에는 상태 없음 | 상태 묶음대로 구현. 비활성 버튼은 Tab 이동에서 빠지므로 안내 상자를 `role=status`로 두고 버튼 접근 이름에 '등록 불가, 최대 5개' 포함. 다른 탭이 먼저 5개를 저장한 경우 등 저장소 단계 거부는 기존 문구 '관심 팀은 최대 5개까지 등록할 수 있습니다.'를 그 버튼 아래에 두고 안내 상자·다른 버튼도 5 / 5로 갱신(목록이 다시 바뀌면 문구 사라짐) | — |
| D-07-4 | 상태 묶음의 정상 상태 버튼(파란 채움 '☆ 관심 팀 등록') ↔ 대표 프레임(미등록 흰 테두리, 등록됨 파란 채움·카드 파란 테두리) | 대표 프레임대로 | 상태 묶음 정리 |
| D-07-5 | Figma에 없는 상태: 저장소 차단, 잘못된 URL 조건, 마지막 페이지 초과, 리그 선택 중 검색 결과 없음, 재조회 실패(확인된 목록 있음) | 저장소 차단 — 안내 상자 자리에 주황 '이 브라우저에서는 관심 팀을 저장할 수 없습니다. 팀 목록은 계속 볼 수 있습니다.'(목록·필터·검색 유지). 잘못된 리그·페이지·검색어 — '조회 조건을 확인할 수 없습니다'+'필터 초기화'(05와 같음). 페이지 초과 — '이 페이지에는 팀이 없습니다'+'마지막 페이지로'. 리그 선택 중 결과 없음 — '현재 시즌 {리그} 팀만 찾을 수 있습니다.'. 목록 위 개수 줄은 검색 시 '현재 시즌 5대 리그 · '맨체스터' 검색 결과 2개 팀'. 재조회 실패 — 목록 위 '팀 목록을 다시 확인하지 못했습니다. 마지막으로 확인한 목록입니다.'+'다시 확인'(06 `partialAction`과 같은 형태) | 문구·디자인 |
| D-07-6 | 검색 입력: Figma `52:705` 40px 입력(아이콘 없음) — 자동완성 후보 목록 없음 | 메인의 `TeamSearch`(한 팀을 고르는 자동완성)를 쓰지 않고, 입력한 이름으로 목록 자체를 거른다(모호한 별칭은 후보 팀이 모두 목록에 남음). 40px 입력 + 44px 조작 영역(D-03-8과 같음), 입력이 있으면 × 지우기 | — |
| D-07-7 | 태블릿 폭(640~1023px): Figma는 데스크톱 3열·모바일 1열만 | 640px부터 2열, 1024px부터 3열 | — |

08 구현 중 기준끼리 어긋났거나 Figma에 없는 부분은 아래처럼 처리했다. Codex 검토와 사용자 확인을 요청한다.

| ID | 항목 | 08 처리 | 확인 요청 |
| --- | --- | --- | --- |
| D-08-1 | 국적 표기: Figma 선수 표 '아르헨티나'·'대한민국'(한국어) ↔ API는 영문 국가명만 제공, 한국어 국가명 사전 없음 | 제공값 그대로 영문(예: 'Argentina'), 없으면 '—'. 국가명 번역 표를 만들지 않음(제공값 외 정보 생성 금지) | 영문 유지 / 국가명 한국어 사전 추가(별도 작업) |
| D-08-2 | 선수 표 기본 정렬: Figma 머리글 '번호 ↑' ↔ TEAM-002 규칙 2 '기본 정렬은 포지션순' | 기능 명세대로 포지션순(GK→DF→MF→FW, 같으면 번호·이름)으로 열고 '포지션 ↑' 표시. 모든 열 정렬(누락값은 두 방향 모두 맨 뒤), '선수 더 보기 · {남은 수}명' | Figma 머리글 표시 정리 |
| D-08-3 | 경기 영역: Figma 최근 결과 3개·시각만 ↔ 기능 명세·작업 지시 '최근 결과 5개' | 예정(진행 중 먼저) 최대 3개 + 최근 결과 5개. 여러 주에 걸치므로 공통 `MatchCard`의 날짜 표기(`withDate`, '11/8(일) 02:30')를 씀(D-03-3과 같음) | 프레임 갱신 |
| D-08-4 | 시즌 기록 행: Figma 5행(득점/실점·홈·원정·무실점·주 포메이션) ↔ TEAM-005 규칙 2 '기존 지난 시즌 성적은 지난 시즌 기록에 포함' | 맨 위에 '리그 순위'(그 시즌 순위·승점, 지난 시즌은 최종 순위) 행을 더함 | 행 추가 유지 |
| D-08-5 | 팀 뉴스 범위·문구: Figma '전체 최신 최대 48개 안에서 팀 관련 기사만 표시합니다', '관련 뉴스 2/2' ↔ 03 결정 '팀만 연결되고 뱃지가 없는 기사는 팀 상세에서만 쓴다'(메인 48개는 뱃지 기사만) | 팀에 연결된 기사 최신 최대 48개(뱃지 없는 기사 포함)를 6개씩, 문구는 '팀 관련 최신 기사를 최대 48개까지 표시합니다.', 버튼은 더 있을 때만 '관련 뉴스 더 보기 (6/13)'. 북마크 아이콘은 02 | 범위·문구 |
| D-08-6 | 이적 표시: Figma 유형 '완전 이적·임대·계약 만료' ↔ 제공 유형은 영문 단어 또는 금액. 제공사가 같은 이동을 하루 차이로 두 번 주는 경우 다수(예: 같은 선수·팀·유형 08-10·08-11) | 제공 단어만 한국어로 옮김(Transfer 완전 이적, Loan 임대, Return/Back from loan 임대 복귀, Free agent 자유계약, Free Transfer 자유 이적, End of career 은퇴), 금액·그 밖은 그대로, 없음·'N/A'는 '—'. 하루 차이 반복은 앞 날짜 1건(상대 팀 ID가 같을 때만 — ID 없이 이름만 있으면 합치지 않음(Codex 2차 N2), 그 이틀에 반대 방향 이동이 있으면 별개 거래로 보고 둘 다 보존 — Codex 1차 지적 8). 이름의 HTML 엔티티('&apos;')는 화면에서 해제. 큰 구단은 한 반기에 영입·방출이 수십 건이라 오른쪽 열이 길어짐(접기 없음 — Figma에 기준 없음) | 유형 번역·긴 목록 처리 |
| D-08-7 | 선수 표 기록 범위: '이번 시즌 선수 기록'(PRD) — 국내 컵·UEFA 포함 여부 미정 | TEAM-002 외부 API(`/players` 리그 페이지)대로 리그 기록만. 표 아래 '시즌 기록은 {리그} 경기 기준입니다.'를 더함(머리 문구 '현재 선수단 + 이번 시즌 기록'은 Figma 그대로) | 컵·UEFA 포함이 필요하면 범위·호출 수 산정 후 별도 작업 |
| D-08-8 | Figma 상태 묶음(57:836)에 없는 상태: 저장소 차단, 감독·경기장·순위의 미수집, 영역별 갱신 실패 | 저장소 차단 — 관심 팀 버튼 아래 주황 '이 브라우저에서는 관심 팀을 저장할 수 없습니다. 팀 정보는 계속 볼 수 있습니다.'(07 안내와 같은 형식). 미제공 '미제공', 미수집 '확인하지 못했습니다'. 영역별 갱신 실패는 마지막 확인 데이터 + '다시 확인'(06·07과 같음, 확인된 결과가 비어 있어도 실패 안내 + 빈 결과 문구 + '다시 확인' — 팀 뉴스·선수단, Codex 1차 지적 9). 허용되지 않은 팀 '팀 상세를 제공하지 않는 팀입니다'·없는 팀 '팀을 찾을 수 없습니다' + '팀 탐색으로 이동' | 문구·디자인 |
| D-08-9 | '경기 전체 보기' 범위(Codex 1차 지적 4): TEAM-003 규칙 2 '전체 보기에서 이번 시즌 경기 전체' ↔ 08 작업 지시·유저 플로우 UF-09 진입점 '팀 상세 경기 영역 → 지난 경기'(`/results?team=<id>`, 종료 경기만 — 맨시티 기준 종료 15·예정 34경기 중 15경기) | **사용자 결정(2026-11-07): A 현행 유지.** `/results?team=<id>`(선택 시즌 전체 종료 경기) 연결과 Figma 버튼 문구 '경기 전체 보기'를 그대로 둔다(코드 변경 없음). 예정 경기는 팀 상세 경기 영역의 '예정 경기'(최대 3개)와 메인 팀 21일 보기가 맡는다 | **반영 완료(2026-11-07, Codex):** 기능 명세서 v1.7 TEAM-003(규칙 2·출력·완료 조건 — 지난 경기 화면 연결, 팀 조건 적용·시즌 변경 시 유지), PRD v1.7 16장 팀 상세 정보, 유저 플로우 v1.6 UF-09·UF-11. 이전 버전은 보존 |

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

**현재 상태(2026-11-07):** 08도 `dev` 작업 트리에서 작업한 뒤 Codex 교차 검증 통과 후 사용자 요청(2026-11-07)으로 `feat/08-team-detail`을 만들어 커밋·push하고 `dev`에 병합했다. 원격 `main`·`dev`·`feat/01-header-footer`·`feat/03-schedule`·`feat/04-match-detail`·`feat/05-results`·`feat/06-standings`·`feat/07-team-browse`·`feat/08-team-detail`. 다음 02는 최신 `dev`에서 `feat/02-auth`를 만든다. 07도 `dev` 작업 트리에서 작업한 뒤 Codex 교차 검증(3차) 통과 후 사용자 요청(2026-11-06)으로 `feat/07-team-browse`를 만들어 커밋·push하고 `dev`에 병합했다. 다음 08은 최신 `dev`에서 `feat/08-team-detail`을 만든다. 이하 이전 기록 — 04는 최신 `dev`에서 만든 `feat/04-match-detail`에 커밋·push하고 `dev`에 병합했다(Codex 교차 검증 통과, 사용자 요청 2026-11-03). 05는 `dev` 작업 트리에서 작업한 뒤 Codex 교차 검증 통과 후 사용자 요청(2026-11-05)으로 `feat/05-results`를 만들어 커밋·push하고 `dev`에 병합했다. 06도 `dev` 작업 트리에서 작업한 뒤 Codex 교차 검증(3차) 통과 후 사용자 요청(2026-11-06)으로 `feat/06-standings`를 만들어 커밋·push하고 `dev`에 병합했다. 다음 07은 최신 `dev`에서 `feat/07-team-browse`를 만든다.

**Git에 올리지 않는 것:** 모든 `.env*` 파일(`.env.example` 포함), 가상환경·Python 런타임, `node_modules`·`.next`, 캐시, 저장소 밖 로컬 자료(`../docs`·`../api-test`·`../wireframe`), 쓰지 않는 기본 생성 파일. 새 파일 유형이 생기면 루트 `.gitignore`를 먼저 갱신한다.
