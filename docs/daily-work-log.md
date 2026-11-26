# KickTab 일별 작업 내역

## 2026-11-25 (수) — 03 남은 수집 기록 정리·뉴스 설명 주소 제거(00 전체 검수 후속)

브랜치 `feat/03-schedule`(최신 `dev` 6cc9d28 병합 후 작업)에 커밋·push 후 `dev` 병합. 공유 DB(개발·운영 공용)라 데이터 변경은 아래 1줄만, downgrade·외부 API 호출 없음.

| 영역 | 변경 파일·함수 | 이유 |
| --- | --- | --- |
| 수집 기록 1줄(데이터) | `sync_runs` id 798 — `status` running → failed, `finished_at` 2026-11-25 14:03 UTC, `error_summary` '서버 중단으로 끝나지 않은 실행 — 2026-11-25 수동 정리'(다른 `fixtures` 실행 중 없음 확인 후, id·작업·상태·종료 시각 조건이 정확히 1줄일 때만 반영) | 사용자 결정: 배포 확인 목록(guide §10.5) 'running 잔류 없음' 점검에서 옛 기록과 진짜 멈춘 작업을 구분하지 않게. 잔류 이후 `fixtures` 48회 모두 정상 실행 — 수집은 막히지 않음, 자동 정리 기능은 만들지 않음 |
| 뉴스 설명 주소 제거 | `backend/app/services/news_classify.py`(`description_text` 새, `_ADDRESS`·`_SPACES`), `app/sync/news.py`(저장 설명), `app/services/news.py`(`list_news` 응답 설명) | 네이버 설명의 '→ [원문에서 영상 보기] https://…' 주소가 카드에 그대로 보임(레알 마드리드 팀 뉴스 1건). 이미 저장된 기사는 다시 쓰지 않고(72시간 후 소멸) 조회 응답에서 같은 함수로 정리 |
| 테스트 | `backend/tests/test_schedule_rules.py`(`test_description_text_drops_addresses_and_their_pointer`) | 주소·안내 조각 제거, 일반 설명(대괄호·콜론·화살표) 유지, 주소만 → None |

- **실제 확인:** `status='running'` 0건. 레알 마드리드 팀 상세 뉴스(기사 18498 — DB에는 주소가 남아 있고 응답은 정리됨) 1920·375에서 주소 없음, 가로 넘침 없음.
- **참고:** 수집 때 분류는 원문 설명 그대로. 다음 실행의 저장 기사 재분류는 정리된 설명을 읽음 — 주소 글자 안에 팀·대회 이름이 있을 때만 차이. 대괄호 안내가 주소 바로 앞에 붙은 경우('[속보]https://…')는 그 대괄호도 함께 빠짐(드묾).
- **검사:** ruff, pytest 389 통과/162 건너뜀(DB 포함 548), alembic check 변경 없음, frontend lint·`tsc --noEmit`·test 93·build 통과.
- **문서:** `guide.md`(상단 요약·§3 03 행·최종 갱신), 이 문서, `file-feature-map.md`.

## 2026-11-25 (수) — 09 마이페이지 데스크톱 검수 반영(관심 팀 제목 줄·팀별 다음 경기·내 평가 더 보기·상단 문구·계정 관리 고정)

브랜치 `feat/09-mypage`(최신 `dev` b190ff8 병합 후)에 커밋·push 후 `dev` 병합. 기준 Figma 52:2674 / 52:2912, 상태 797:20589(2026-11-25 사용자 결정). 사용자 추가 결정: 다른 페이지처럼 최상단 제목·소개 제거, 계정 관리 패널은 경기 일정 우측 패널처럼 스크롤 고정 — Figma에도 반영.

| 영역 | 변경 파일·함수 | 이유 |
| --- | --- | --- |
| 관심 팀 제목 줄 | `features/mypage/MyCard.tsx`(`icon`·`note`·`action`), `FavoriteTeams.tsx`, `model.ts`(`favoriteCountText` 'n / 10') | 09-1: '★ 관심 팀 n / 10 … 팀 추가'(접근성 이름 '관심 팀 추가'), 10/10 비활성·한도 안내·포커스 유지 |
| 팀별 다음 경기 | `features/favorites/nextMatches.ts`(새), `FavoriteSchedule.tsx`, `mypage/FavoriteTeams.tsx`(`FavoriteRow`·`NextMatch`) | 09-2: 메인 패널과 같은 `favoriteScheduleQuery`·같은 기준으로 팀마다 1경기(관심 팀끼리 경기는 두 줄 모두), '해제'('○○ 관심 팀 해제'), 경기 없음·스켈레톤·`ScheduleNotice` 경고+'다시 확인'(전체 실패면 2행 비움) |
| 내 평가 더 보기 | `features/mypage/MyReviews.tsx`(`REVIEWS_STEP` 5) | 09-4: 5개씩, 다 보이면 버튼 없음, 수정·삭제 후 펼친 개수 유지 |
| 상단 문구 | `app/mypage/page.tsx`, `features/mypage/MyPage.tsx` | 다른 페이지와 같이 sr-only H1만, 첫 카드부터 표시 |
| 계정 관리 고정 | `components/layout/StickyPanel.tsx`(`minWidth`), `MyPage.tsx` | 메인 우측 패널과 같은 고정(헤더 아래 12px, 창보다 길면 아래 끝 유지), 마이페이지는 1024px부터 |
| Figma | 52:2674·52:2912·643:658·643:755('Page title' 삭제), 642:21111(고정 주석) | 화면과 시안 일치 |
| 테스트 | `frontend/tests/mypage.test.mjs`(팀별 다음 경기·해제 즉시 제외, 개수 문구) | 회귀 |

- **브라우저 확인(테스트 계정 A):** 1920·1280·1024·1023·375·320, 관심 팀 0·3·10, 관심 팀끼리 경기 두 줄, 모의 응답으로 경기 없음·일부 미확인·갱신 실패·전체 실패·다시 확인·추가 중 스켈레톤·긴 팀명, 해제 후 메인 패널·별 동기화, 평가 모의 12개 5→10→12·펼친 상태 수정·삭제, 계정 관리 고정(top 130)·1280×460 아래 끝 유지·1023 한 줄, 비회원 안내·로그인 복귀, 비밀번호 창 포커스 복귀. 관심 팀은 원래 10팀 순서로 되돌림. 진행 중 경기는 확인 시점에 없어 미확인.
- **검사:** frontend lint, tsc, npm test 93, build, `git diff --check`. 외부 API 호출 없음.

## 2026-11-25 (수) — 08 선수단 정렬·부분 집계 해소·이적 기준 변경(사용자 요청·결정)

브랜치 `feat/08-team-detail`(최신 `dev` 3689620 위)에 커밋·push 후 `dev` 병합. 사용자 결정 2건(이적 메인 = 리그·UEFA·클럽 월드컵 출전, 공급사 미제공 경기 제외), 마이그레이션 `0021` 사용자 확인 후 공유 DB 적용. 자체 검수, 외부 호출 API-Football 3회(발렌시아 확인 2·경기 기록 읽기 1).

| 영역 | 변경 파일·함수 | 이유 |
| --- | --- | --- |
| 선수단 표 정렬 | `features/team-detail/SquadTable.tsx`(`COLUMNS`, 사진·숫자 셀, 정렬 화살표 `absolute`, `CompetitionLines`) | 선수명·국적만 왼쪽, 사진·등번호·포지션·출전·득점·도움·상세와 대회별 기록 숫자는 가운데(열 제목 포함). PC(lg) 숫자 열 80px·좌우 12px, 모바일은 표 안에서만 가로 스크롤. 제목 아래 설명 삭제, '부분 집계'는 제목 옆 상태로만 |
| Figma | Team Squad Table 470:6667·Row 470:6646·Popover 469:6642, PC 인스턴스 472:18385 | 가운데 정렬 반영, PC 열 간격 16px(모바일 8px 유지) |
| 아직 안 치른 대회 제외 | `services/team_detail.py`(`played_competitions`, `read_squad`), `sync/team_detail.py`(`team_player_stats` 현재 시즌 범위) | 2026-27 아래에 미리 나오는 지난 슈퍼컵 줄이 합계·'부분 집계'에 섞이던 문제 |
| 공급사 미제공 경기 | `services/team_detail.py`(`missing_record_competitions`, `_gives_player_data`, `unread_record_matches`), `sync/team_detail.py`(`_read_record_matches`, 20개당 1회, 04 `store_fixture_records` 재사용) | 코파 델 레이 초반 라운드처럼 경기 기록에 그 팀 선수 기록이 없는 경기만 있는 대회는 부분 집계가 아님. 1회 실행으로 10경기 읽어 96팀 배지·안내 0 |
| 이적 판정 | `services/team_detail.py`(`first_team_competitions`, `move_evidence`, `judge_move`), `api/routes/teams.py` | 메인 = 이 팀 리그·UEFA·클럽 월드컵 출전 1경기 이상, 그 외 모두 '기타 이동', 기록 미수집 시즌만 메인 유지. 맨시티 2026-27 메인 31→22줄, 8개 팀×2시즌 359→302줄, 주요 선수 유지 |
| 쓰지 않는 코드·표 삭제 | `transfer_player_checks` 작업·`parse_player_season` 등, `models/team_detail.py`(`PlayerSeasonCheck`·`PlayerClubSeason`), `migrations/versions/20261125_0021_drop_player_season_checks.py`(새) | 이전 팀 확인이 더 이상 판정에 쓰이지 않음(작업 원칙 5). 공유 DB에서 1,667·2,408행 삭제(사용자 확인) |
| 테스트 | `tests/test_team_detail.py`, `tests/test_team_detail_db.py` | 새 판정·안 치른 대회·공급사 미제공 경기 테스트, 삭제된 기능 테스트 제거 |
| 기획 문서 | `docs/` 기능 명세서·PRD·유저 플로우 새 버전 | TEAM-002 규칙 2·6, TEAM-006 규칙 6·6-2·추가 검수·완료 조건, 변경 이력 |

검사: ruff, pytest 388(+DB 547, 3 skipped), alembic check(head `0021`), lint, tsc, npm test 92, build, 브라우저 1920·375(콘솔 오류 0).

## 2026-11-25 (수) — 07 팀 탐색 별 아이콘 팀 카드(데스크탑 검수)

브랜치 `feat/07-team-browse`(최신 `dev` a8e2f6a 병합 후 작업)에 커밋·push 후 `dev` 병합. 기준: Figma 52:624·52:949. 자체 검수, 외부 호출 0회.

| 영역 | 변경 파일·함수 | 이유 |
| --- | --- | --- |
| 팀 카드 | `features/teams/TeamsSection.tsx`의 `TeamCard` | 한 줄 구성(엠블럼 40px · 팀명 16px Bold / 보조 글씨 12px · 오른쪽 끝 별), 여백 16px·둥글기 12px, 큰 '관심 팀 등록' 버튼 제거(팀 상세의 `FavoriteToggle`은 유지), 팀명 상세 링크·관심 팀 파란 테두리·한도 안내 유지 |
| 별 | `features/favorites/FavoriteStar.tsx`(`iconSize` 16·18) | 경기 카드 별 재사용, 팀 카드는 18px. 누르는 영역 44px·03의 한도·거절 팝업 그대로 |
| 문서 | `docs/guide.md`(첫 단락·§2 관심 팀·§3 07·§11), `docs/file-feature-map.md`, 이 문서 | 사용자 요청으로 세 문서 최신화 |

검수: 프런트 lint·`tsc --noEmit`·npm test 92·Turbopack 빌드, `git diff --check`. 브라우저 1920·1280·375·320에서 카드 높이 82px(Figma와 같음)·별 18px·영역 44px, 등록·해제, 5팀 후 6번째 별 거절 안내(320에서도 화면 안), 메인 관심 팀 패널(5/5·칩·요약 경기)·일정 관심 팀 버튼 동기화, 키보드로 팀명 링크(Enter = 상세)와 별(Tab → Enter·Space) 각각 조작·포커스 3px, 긴 팀명 말줄임·별 위치 유지, 페이지 이동 후 별 상태 유지, 가로 넘침 없음, 콘솔 오류 0.

## 2026-11-25 (수) — 06 단계 탭 첫 화면 왼쪽 맞춤 결함 수정(00 검수)

브랜치 `feat/06-standings`(최신 `dev` 464bee2 병합 후 작업)에 커밋·push 후 `dev` 병합. 00 검수: 글꼴 캐시 없는 첫 접속 1920에서 '리그 페이즈' 탭 왼쪽(843)이 'UEFA 챔피언스리그' 칩(815)보다 28px 오른쪽, 창 크기를 바꾸면 맞춰짐.

| 영역 | 변경 파일·함수 | 이유 |
| --- | --- | --- |
| 단계 탭 왼쪽 맞춤 | `frontend/src/features/standings/StageTabs.tsx`(측정 `useLayoutEffect`) | 감싼 상자 크기·스크롤·창 크기에만 반응해, 웹 글꼴이 늦게 적용되거나 `/competitions` 이름이 바뀌어 칩 폭만 달라질 때 다시 재지 않음(칩 글자 폭만 넓혀 재현: 칩 815→850, 탭 815). 대회 칩 줄 안쪽 내용(`[role=group]` 첫 자식)을 `ResizeObserver`로 관찰하고 `document.fonts.ready`·`loadingdone` 때 다시 잰다. `ChipRow.tsx`는 고치지 않음 |

검수: 새 탭 1920 첫 화면 칩·탭 822/822 → 칩 815로 이동 시 탭도 815, 칩 폭 변경 1920 850/851·1280 562/562, 대회 전환 뒤 815/815, 1024 칩 줄 넘긴 뒤 152/152(칩이 오른쪽 끝에 가려질 때만 기존 설계대로 160px 여유에서 멈춤), 콘솔 오류 0. 브라우저 창의 글꼴 캐시는 비울 수 없어 첫 접속은 칩 폭 변화 재현으로 대신 확인. lint·tsc·npm test 92·build 통과.

## 2026-11-25 (수) — 06 리그 순위 데스크톱 검수 반영(단계 탭·구간 색·선수 순위)

브랜치 `feat/06-standings`(최신 `dev` 96ba335 병합 후 작업)에 커밋·push 후 `dev` 병합. 기준: 00 지시(2026-11-24 데스크톱 검수), Figma `53:1353`·`53:2047`·`61:1653`·`61:2355`·`451:20753`·`451:20778`·선택부 `449:6666`, 이후 사용자 결정(0 기록 제외·선방 20명·20위 밖 동률 안내). `ChipRow.tsx`는 03 담당이라 고치지 않음. 외부 호출 없음.

| 영역 | 변경 파일·함수 | 이유 |
| --- | --- | --- |
| UEFA 단계 선택 | `features/standings/StageTabs.tsx`(새), `StandingsSection.tsx`(`[data-competition-choices]` 묶음) | 칩 → 하위 탭(44px·간격 4·둥글기 6px·13px Medium, 선택 #f1f5f9·#2563eb, 비선택 #475569), `useScrollRow`로 넘김·선택 탭 보이기, 칩 줄 10px 아래, PC는 'UEFA 챔피언스리그' 칩 실제 위치에 왼쪽 맞춤(칩 줄 스크롤·창 크기 따라감; 부모 ref가 자식 layout effect 뒤에 붙어 `closest()`로 찾음), 모바일 왼쪽 시작. URL·뒤로 가기·`aria-pressed` 유지 |
| 순위 구간 색 | `app/globals.css`(`--kt-band-direct`·`-playoff`·`-out`·`-relegation`), `standings/model.ts`(`Band.tone`), `StandingsTable.tsx`(`BAND_BORDER`·`BAND_BAR`, export 제거) | UEFA 직행 #2563eb·플레이오프 #F59E0B·탈락 #64748b, 국내 강등 #b91c1c·승강 PO #F59E0B(사용자 결정), 행 막대·범례 막대 같이 |
| 선수 순위 넘침 | `standings/PlayerRankings.tsx` | `table-fixed` 순위 64px · 선수·팀 · 값 56px, 이름·팀명 말줄임 없이 띄어쓰기 줄바꿈(`break-keep`, 열보다 긴 한 단어만 끊음), '공동 n' 한 줄 |
| 0 기록·20명 | 백엔드 `api/routes/standings.py`(`LIST_SIZE`), 프런트 `PlayerRankings.tsx` | 사용자 결정: 값 0(경고 누적만인 퇴장·출전 없는 골키퍼 선방) 5종·8개 대회 공통 제외(예: 챔스 2026 선방 172→71명), 선방도 상위 20명(순위·공동은 전체로 계산 후 자름), 4종은 공급사 순서 유지, 꽉 찬 목록에 '20위 밖에 같은 기록의 선수가 더 있을 수 있습니다.' |
| 긴 이름 | `standings/KnockoutStage.tsx`(`SlotTitle` 이름 `[overflow-wrap:anywhere]`) | DB 최장 선수·팀명을 6개 구성요소에 넣어 확인 중 1024px 2열 대진 카드에서 'Haverfordwest'가 칸을 넘음 → 칸보다 긴 한 단어만 단어 안에서 끊김 |
| 테스트 | 프런트 `tests/standings.test.mjs`(구간 tone), 백엔드 `tests/test_standings_db.py`(`test_a_recorded_zero_is_not_ranked`, 선방 검증 38명 집계·화면 20명) | 구간 색·0 제외·20명 고정 |

검수: lint·tsc·npm test 92·build, ruff·pytest 400·DB 557 통과. 브라우저 1920·1280·1024·375·320 — UEFA 3대회 단계 전환·뒤로 가기·국내↔UEFA, 탭 왼쪽 맞춤(칩 줄 넘긴 뒤 포함), 구간 색·범례(UEFA·국내·분데스리가·리그 1), 분데스리가 선방(긴 이름 줄바꿈·'공동 21' 한 줄), 메인 리그 순위 카드·팀 탐색 칩 줄 그대로, 가장 긴 이름 시험 통과, 페이지 가로 넘침 0·콘솔 오류 0.

## 2026-11-25 (수) — 05 지난 경기 필터 줄·페이지 버튼 데스크탑 검수 반영

브랜치 `feat/05-results`(최신 `dev` e14aba4 — 01 버튼 체계·02·03·04 반영 포함 — 병합 후 작업)에 커밋·push 후 `dev` 병합. 기준: Figma `53:593`·`53:995`(지난 경기), 'KickTab/Results Pagination' `556:7312`(PC `530:21586`·모바일 `530:21659`, 팀 탐색 `52:886`·`52:1197`). 작업 지시(2026-11-24 데스크탑 검수) 반영. `TeamSearch`·`ChipRow`는 03에서 끝나 손대지 않음.

| 영역 | 변경 파일·함수 | 이유 |
| --- | --- | --- |
| 필터 배치 | `frontend/src/features/results/ResultsSection.tsx` | 첫 줄 시즌 선택만, '초기화'를 대회 선택 옆(보조 80px)으로 — 메인 경기 일정 필터 줄과 같은 모양(모바일 포함). 미지원 시즌은 대회 줄과 함께 숨김(시즌만 유지하는 초기화는 그 상태를 풀지 못함) |
| 페이지 버튼 | `components/ui/Pagination.tsx`(`pageWindow`·`numbersFor(width, arrows)`, 옛 `pageItems`·'…' 삭제) | `« ‹ [번호] › »`, 현재 중심 연속 번호 1~7개(PC 7·375px 3·320px 1), « »는 번호가 다 보이지 않을 때만, 양 끝 비활성, 접근성 이름 '첫 페이지…마지막 페이지' |
| 아이콘 | `components/ui/Icon.tsx`, `public/icons/chevrons-left.svg`·`chevrons-right.svg`(새) | Figma 708:7807·708:7810 이중 화살표 |
| 테스트 | `frontend/tests/results.test.mjs` | 번호 범위·폭별 개수·렌더(« » 조건·비활성·현재 페이지) |

- **실제 확인:** 지난 경기 1920·1280·375·320(1·5·8·210·419·420페이지, «·‹·›·» 이동, URL·뒤로 가기, 320 한 줄·넘침 없음·버튼 44px, 필터 줄 좌표 — 대회 선택 1079/221/166 + 초기화 80), 팀 탐색 EPL 2페이지 `‹ 1 2 ›`(1920·320)·전체 8페이지(PC 7개, 320 1개), 콘솔 오류 없음.
- **검사:** lint·tsc·프런트 테스트 92·build·`git diff --check` 통과. 외부 호출 0회, 백엔드 변경 없음.

## 2026-11-25 (수) — 04 경기 상세 상대 전적·타임라인 데스크탑 검수 시안 반영

브랜치 `feat/04-match-detail`(최신 `dev` 11cf508 — 01 버튼 체계·02·03 반영 포함 — 병합 후 작업)에 커밋·push 후 `dev` 병합. 기준: Figma 63:1909·63:2116(예정 경기 상대 전적), 52:151·52:404(타임라인). 작업 지시(2026-11-24 데스크탑 검수) 반영 후 사용자 지적으로 타임라인 머리 줄·소속 미확인 줄을 시안에 맞게 추가 수정, 자체 검수 후 결정 필요 사항 없음.

| 영역 | 변경 파일·함수 | 이유 |
| --- | --- | --- |
| 상대 전적 | `frontend/src/features/match/HeadToHeadSection.tsx`(표 `table-fixed` PC [날짜 110 · 대회 180 · 결과 가운데]·모바일 [날짜 아래 대회 94 · 결과], 결과 '홈팀 스코어 원정팀' 파란 굵은 13px, 승·무·패 칩을 표 아래로, caption '장소' 삭제) | Figma 63:1909 / 63:2116: 표 위 요약·날짜 아래 '홈/원정' 줄 삭제. 이 경기 홈팀 왼쪽 기준 스코어·승부차기 표기 유지 |
| 타임라인 | `features/match/MatchRecords.tsx`(`TimelineTeam` 각 팀 열 가운데 — PC 엠블럼 옆 14px·높이 28px, 모바일 엠블럼 아래 13px·높이 44px, '시간'·분 14px, 소속 미확인 줄은 '분 / 소속 미확인'만 표시·이벤트는 낭독용, `EventBody` 가운데 정렬 분기 삭제) | Figma 52:151 / 52:404 |
| 테스트 | `frontend/tests/match-regressions.test.mjs`(+1 상대 전적: 홈팀 왼쪽 스코어·원정 경기 뒤집기·승부차기·홈/원정 줄 없음·caption·칩 위치·맞대결 없음, 소속 미확인 줄 기대값 갱신) | 회귀 |

- **화면 확인:** PC 1920·1280, 모바일 375·320. 상대 전적 1575231(5경기, 열 폭 110/180/472·줄 56px, 긴 팀명 '아인트라흐트 프랑크푸르트' 결과 칸 줄바꿈, 원정 경기 스코어 뒤집기 원본 대조)·1635735(맞대결 없음 — 안내만, 표·칩 없음). 타임라인 1550201 종료 경기(머리 줄 379/56/379·팀 묶음 열 가운데, 글씨 14·13·10px, 가로 넘침 없음).
- **제한:** 검수 시점 진행 중 경기가 없어 진행 중 타임라인은 같은 컴포넌트(종료 경기)로 갈음. 소속 미확인 이벤트는 저장 데이터 2,347건 중 0건이라 테스트로만 확인.
- **검사:** lint·tsc·프런트 테스트 92·build·`git diff --check` 통과(백엔드 변경 없음).

## 2026-11-24 (화) — 03 경기 일정 데스크탑 검수 시안 반영

브랜치 `feat/03-schedule`(최신 `dev` c8004c3 병합 후 작업)에 커밋·push 후 `dev` 병합. 기준: Figma 메인 `49:57`·`49:570`, 팀 화면 `193:12311`, 관심 팀 `KickTab/Guest Favorites` `306:6220`·회원 `669:7801`·요약 카드 `669:7794`, 모바일 경기 카드 `306:3969`. 관심 팀 요약 경기는 Figma를 먼저 고치고 사용자 확인 후 코드 반영.

| 영역 | 변경 파일·함수 | 이유 |
| --- | --- | --- |
| 기간 문구 삭제 | `frontend/src/features/schedule/ScheduleSection.tsx`(기간 표시·계산 삭제, '표시된 조회 기간' 문구 정리), `lib/format/kst.ts`(`formatDateRange` 삭제), `backend/app/schemas/schedule.py`·`api/routes/schedule.py`(`TeamSchedule.start`·`end` 삭제), 생성 타입 | 03-1: 날짜·팀 화면 모두 기간 문구 없음 |
| 날짜 막대 | `features/schedule/DateBar.tsx`(`fit` — PC 60px 이상 칸을 들어가는 만큼 늘려 채움(1920 11칸 약 64px), 모바일 5칸/240px 이하 4칸, `page` 한 줄 단위·`snap-mandatory`) | 03-2: 처음·끝·넘김 후 잘린 칸 없음 |
| 필터 줄·검색 | `ScheduleSection.tsx`([대회 선택 / 초기화 80px], 제목 줄 초기화 이동), `components/common/TeamSearch.tsx`(라벨→설명 4·설명→입력 8), `features/results/ResultsSection.tsx`(입력→관심 팀 줄 0) | 03-3·03-4 |
| 관심 팀 패널 | `features/favorites/FavoriteSchedule.tsx`(제목 줄 [★ 관심 팀 n/한도 … 팀 추가], 상시 한도 문구 삭제, `TeamChips` 가로 칩 한 줄(PC 넘칠 때만 24×44 ‹ ›), 요약 경기 2줄 76px·행 사이 12, 접기 기준 경기 3개(`FOLDED_MATCHES`) — 팀 기준 접기 삭제, 해제한 팀 경기 즉시 제외, 칩 '해제' 버튼 칩 안 호버·포커스), `components/ui/Badge.tsx`(크기 `compact`·톤 `raised`), `components/common/MatchStatusBadge.tsx`(`raised`) | 03-5와 사용자 검수: 한 줄형(A안)은 팀명 잘림·대회명 누락으로 미채택, 3경기 + 더 보기 패널이 경기 1개인 날 일정 카드와 같은 482px, 예정 뱃지는 시안 색(흰 바탕·보조 글자) |
| 칩 줄 | `lib/hooks/useScrollRow.ts`(새 — 끝 판정·넘김·`reveal`, 내용 변화 감지), `features/standings/ChipRow.tsx`(흐림 제거, 스크롤 영역 = 아래 내용 폭, 칩 포커스 외곽선 안쪽, 화살표 24×44) | 03-6, 순위 화살표 폭 사용자 요청 |
| 별 한도 팝업 | `features/favorites/FavoriteStar.tsx`(한 줄 고정, 화면 끝 16px 안쪽 보정) | 홈·원정 팝업 양식이 달랐음 |
| 우측 패널 고정 | `components/layout/StickyPanel.tsx`(창보다 긴 패널은 아래 끝이 창 하단 12px에 닿을 때까지 스크롤 후 고정) | 관심 팀 펼친 뒤 일정이 길어져도 패널이 따라오지 않던 문제 |
| 모바일 경기 카드 | `components/common/MatchCard.tsx`(1024 미만 Figma `306:3969`: 상태 우상단, 별 24px 고정 자리, 팀명 12/18px 단어 단위 2줄, 엠블럼 16, 점수 38, `MatchTeams` `card`) | 375·320에서 팀명이 단어 중간에서 끊기던 문제. PC·TOP 5 대진 줄은 그대로 |
| 테스트 | `backend/tests/test_schedule_rules.py`·`test_schedule_db.py`, `frontend/tests/match-regressions.test.mjs`(`formatDateRange` 검사 삭제) | |

- **Figma:** `Guest Favorites` 4개 상태·회원 요약 카드·`Member Schedule Favorites`(간격 16 → 12, 접힘/5팀 상태 3경기 + '더 보기 (3/n)', 펼침 '접기 (n/n)', 뱃지 색 비회원과 통일)·컴포넌트 설명 갱신, 한 줄형 비교 프레임 `767:7842`(미채택 표시) 남김.
- **실제 확인(앱 내 브라우저·3000):** 1920·1280·1024·768·375·320 가로 넘침 0·날짜 막대 잘린 칸 0, 검색 여백(메인·지난 경기·팀 탐색), 관심 팀 비회원 0·2·5팀(회원 10팀 더 보기·접기는 사용자 확인), 해제 후 목록·일정 버튼·별 동기화, 3경기 패널 = 일정 카드 482px, 1368×500 패널 고정, 모바일 카드(메인·지난 경기·팀 상세), 새 탭 콘솔 오류 0. 브라우저 관심 팀 저장값은 확인 후 원래대로.
- **검사:** ruff, pytest 400(DB 포함 556), alembic check 변경 없음, frontend lint·`tsc --noEmit`·test 91·build 통과.
- **문서:** `guide.md`(상단 요약·§3 03 행·최종 갱신), 이 문서, `file-feature-map.md`.

## 2026-11-24 (화) — 02 로그인·회원가입 버튼 체계 적용·비밀번호 찾기 시안 맞춤

브랜치 `feat/02-auth`(01 버튼 체계가 들어간 `dev` ed2e49d 병합 후 작업)에 커밋·push 후 `dev` 병합. 기준: 버튼 `691:8003`, 로그인 `52:2116`·`52:2265`, 회원가입 `52:2387`·`52:2545`, 자동 로그인 `62:1177`·`62:1306`, 비밀번호 찾기 `134:4077`·`134:4344`·`134:4633`·`134:5037`.

| 영역 | 변경 파일·함수 | 이유 |
| --- | --- | --- |
| 버튼 종류 | `AuthForm.tsx`(`SocialButtons`), `LoginForm.tsx`, `SignupForm.tsx` | 소셜 보조, 로그인 하단 링크·가입 완료 '경기 일정 보기' 텍스트, '가입하기'·'자동 로그인 확인 중' 항상 주요. 개별 클래스·`Link` import 삭제 |
| 비밀번호 찾기 단계 | `EmailCodeStep.tsx`(`password_reset`이면 단계형: 1단계 '인증번호 받기' 주요, 발송 후 이메일 칸 숨김, '이메일 다시 입력' → `onEditEmail`, `onSent(email)`), `PasswordResetForm.tsx`(`sentTo`, 2단계 제목·'인증번호 전송: 이메일', 3단계 이메일 칸·규칙 안내 제거·자리표시 문구·'로그인으로 돌아가기', 비밀번호 관리자용 숨은 `username` 칸, 인증 무효 시 단계 표시도 1단계로) | 2단계에서 이메일을 지우면 1단계로 튕기던 문제, Figma에 있는 '이메일 다시 입력'·단계별 '로그인으로 돌아가기' 누락. 처음 구현 때 가입용 같은 화면 부품을 그대로 써서 비밀번호 찾기 단계 프레임과 하나씩 대조하지 않았음 |

- **실제 확인(앱 내 브라우저·3000):** 1920·375에서 로그인, 회원가입 조건 전·후(가입하기 비활성 회색 → 활성 파랑), 가입 완료 확인 중·실패, 비밀번호 찾기 1→2→'이메일 다시 입력'→다른 주소로 2→3→'로그인으로 돌아가기'→재방문 시 1단계, 3단계 규칙 위반 오류, 소셜 안내, 호버·비활성·키보드 포커스(3px). 메일 단계는 페이지 안에서 응답만 대체해 실제 발송·가입·변경 0회. 가로 넘침 없음.
- **검사:** frontend lint·`tsc --noEmit`·test 91 통과·build 통과.
- **문서:** `guide.md` §3 02 행, 이 문서, `file-feature-map.md`(02 파일 항목을 처음 추가 — 백엔드·프런트·테스트).
- **추가(같은 날, 사용자 요청):** 회원가입 '인증번호 받기'를 주요로(`EmailCodeStep.tsx` — 두 화면 모두 주요) 하고 Figma `52:2387`(`52:2459`)·`52:2545`(`52:2596`) 버튼을 Primary + KickTab 주요 색 토큰(비밀번호 찾기 `134:4205`와 같은 덮어쓰기)으로 변경. 닉네임 금칙어(P-04 갱신): 운영자 사칭 단어와 직설적인 욕설·비속어가 포함되면 가입 거부, 대소문자 무시·숫자 제거 후 비교(`backend/app/services/auth_security.py` `BLOCKED_NICKNAME_WORDS`·`nickname_blocked`·`NICKNAME_BLOCKED`, `frontend/src/features/auth/rules.ts` `nicknameError`, `SignupForm.tsx` 오류 표시), 사용자 테스트 계정 'admin'은 유지. 검사: backend ruff·pytest 397 passed/159 skipped, `KICKTAB_DB_TESTS=1` `test_auth_db` 42 passed, frontend lint·tsc·91 tests·build 통과. 화면: 1920에서 '킥탭운영자'·'Admin7' 오류와 '가입하기' 비활성, 'Sonny7' 정상(메일 응답 대체, 실제 발송 0).
- **금칙어 오류 문구 변경(같은 날, 사용자 결정):** '사용할 수 없는 닉네임입니다.' → '운영자 사칭이나 비속어로 볼 수 있는 단어가 포함되어 사용할 수 없는 닉네임입니다.'(서버 `NICKNAME_BLOCKED`, 화면 `rules.ts` `NICKNAME_BLOCKED`). 검사 방식·목록은 그대로, 예외 단어 없음('badminton'·'시발점'도 거부하고 이유는 문구로 설명 — 테스트로 고정). 기획 문서 3개는 00이 반영, `guide.md`는 P-04·§3 02 행만. 검사: backend ruff·`test_auth_rules` 59 passed, frontend lint·tsc·91 tests·build 통과. 화면: 1920·375에서 'badminton' 입력 시 새 문구가 닉네임 입력란 오류(두 줄, 가로 넘침 없음)로 표시(메일 응답 대체, 실제 발송 0).
- **확인 결과(사용자 질문):** 비밀번호 찾기에서 기존과 같은 비밀번호로 바꾸는 것은 기획 문서(PRD·기능 명세서 v1.14)에 금지 규칙이 없어 현재 동작은 명세와 일치. 사용자 결정(2026-11-24): 현재처럼 허용 유지(막으려면 오류 문구·상태(Figma)와 서버 오류 코드를 새로 정해야 함).

## 2026-11-24 (화) — 01 공통 버튼 체계·헤더·팝업 버튼 통일(데스크탑 검수)

브랜치 `feat/01-header-footer`(최신 `dev` f2b1428 병합 후 작업)에 커밋·push 후 `dev` 병합. 기준: Figma `KickTab/Button · 4종 × 5상태`(`691:8003`, `55:27` 안), 헤더 `49:58`, 모바일 메뉴 `62:1427`·`62:1475`·`81:3209`, 팝업 `62:1800`·`62:1939`·`62:1702`·`643:658`·`643:755`·`187:1946`. Codex 교차 검증을 쓸 수 없어 사용자 결정으로 자체 검수 후 마무리(보고할 이상 없음, 주석 2곳만 다듬음).

| 영역 | 변경 파일·함수 | 이유 |
| --- | --- | --- |
| 버튼 4종 | `frontend/src/components/ui/Button.tsx`(`ButtonVariant` primary·secondary·text·danger, `VARIANTS`), `src/app/globals.css`(`--kt-text-disabled`·`--color-fg-disabled`, `kt-press-8`·`12`·`18`, `--kt-action-disabled` 삭제) | 주요·보조·텍스트·위험 × 기본·호버·누름·비활성·포커스를 Figma 값대로. 누름은 `:active`, 겹침은 안쪽 그림자로 토큰 색 유지, 호버·누름은 비활성일 때 적용 안 함 |
| 포커스 외곽선 | `globals.css` 전역 `:focus-visible` | `--color-focus`가 `:root`에 없어(브라우저 확인: 빈 값) 외곽선이 글자색으로 그려지던 앱 전체 문제 → `--kt-border-focus`(#93c5fd) 직접 참조 |
| 사용처 종류 | `HeaderAuth.tsx`, `FavoriteSchedule.tsx`, `HeadToHeadSection.tsx`, `MatchDetail.tsx`, `MatchRecords.tsx`, `ReviewComposer.tsx`, `ReviewTextForm.tsx`, `AccountPanel.tsx`, `FavoriteTeams.tsx`, `MyReviews.tsx`, `ResultsSection.tsx`, `ScheduleSection.tsx`, `TeamDetail.tsx` | 보조: 다시 확인·다시 시도·초기화·취소·헤더 로그인/마이페이지/로그아웃. 텍스트: 줄 안의 해제·삭제·수정, 회원 탈퇴. 위험: 평가 삭제 확인 '삭제' 2곳·탈퇴 확인 |
| 팝업 버튼 | `ReviewSection.tsx`(로그인 안내), `WithdrawDialog.tsx`(빨간 테두리 전용 버튼 삭제), `MyPage.tsx`(비로그인 카드), `PasswordDialog.tsx` | [취소·계속(보조) \| 실행(주요·위험)] 한 줄 같은 폭. `flex-1`은 테두리 있는 보조가 2px 넓어져 `grid grid-cols-2` |

- **실제 확인(헤드리스 Edge·3000):** 1920·375에서 비회원·회원(로그인·`/me/*` 응답 모의, 쓰기 요청 차단) 헤더·모바일 메뉴, 비로그인 마이페이지, 로그인 안내(경기 1557473 반응 버튼), 탈퇴, 비밀번호 변경, 내 평가·경기 상세 평가 삭제 확인. 팝업 두 버튼 같은 폭(159/159, 비밀번호 211/211·375 167/167). 4종 계산값: 기본·호버·누름·비활성이 Figma 값과 일치, 비활성 호버 무변화·`not-allowed`, 높이 44·반경 8·14px 500, 키보드 포커스 3px #93c5fd. 콘솔 오류 0.
- **범위 밖(변경 없음):** 칩·날짜 막대·페이지 번호·탭, 버튼 위치(03·05 담당). 대회 선택·의견 보내기는 이미 규칙대로.
- **검사:** 프런트 lint·`tsc --noEmit`·`npm test` 91·build 통과. 외부 호출 0회.

## 2026-11-24 (화) — 08 이적 갱신 실패 결함 수정

브랜치 `feat/08-team-detail`(최신 `dev` f8c42a9 — 09 마이페이지 병합 포함 — 병합 후 작업)에 커밋·push 후 `dev` 병합. Codex 교차 검증을 쓸 수 없어 자체 교차 검증으로 대신했다.

| 영역 | 변경 파일·함수 | 이유 |
| --- | --- | --- |
| 원인 확정 | (코드 변경 없음) 5팀 160·163·77·81·541 `/transfers?team=` 5회를 저장분과 이동 단위로 비교 | 11/23부터 `transfers`가 53팀에서 'N rows would replace M'으로 거부. 사라진 줄은 모두 같은 선수·방향·상대·유형의 날짜만 다른 사본(공급사가 반복을 정리, 대개 늦은 날짜 하나만 남김), 실제 이동 손실 0. 우리 정리 후 수까지 준 8팀은 같은 날 임대 복귀로 `merge_transfers`가 사본을 별개로 두던 경우 |
| 안전장치 | `services/team_detail.py`(`same_move` 새로, `check_transfers(stored, new, season)` — D-08-6 정리 후 저장 이동 중 새 응답에 없는 이동 수를 max(2, 10%)와 비교, `save_transfers`) | 줄 수 비교가 중복 정리된 정상 응답을 거부. 허용 폭·원본 저장·지난 시즌 고정 규칙 그대로 |
| 자체 검증 보완 | `same_move`(두 날짜 사이 반대 방향 이동이 있으면 별개 이동) | 새 응답 한 줄이 같은 구단·시즌의 서로 다른 이동(임대 → 복귀 → 재임대)을 모두 덮어 손실을 못 세던 문제 |
| 테스트 | `tests/test_team_detail.py`(중복 정리 응답 저장, 실제 이동 누락 거부, 허용 폭 경계 20건 2/3·40건 4/5, 재임대 누락), `tests/test_team_detail_db.py`(맨시티 실제 시즌: 사본 없는 응답 저장·절반 누락 거부) | 회귀 |
| 문서 | `docs/guide.md`(첫 단락·§3 08·§6.5 이적·D-08-6·§11), `docs/file-feature-map.md`, 이 문서 | 사용자 요청으로 세 문서 최신화 |

재수집: `transfers force=1` 96회(오늘 00:00 실패 시도가 있어 일반 실행은 건너뜀) → 96팀 성공, 줄 수가 준 53팀 모두 손실 이동 0(45팀은 정리 후 수 같음·이상, 8팀 77·81·160·163·173·523·542·728은 사본만 줄어 감소), 갱신 실패 표시 0·갱신일 2026-11-24. 자체 보완 뒤 11/22 저장분 대비 재판정도 96팀 저장·손실 0. 외부 호출: API-Football 101회(원인 확인 5 + 재수집 96), Gemini·top5 실행 없음. 판정 사유 8개 팀 그대로(played_here 425·not_played 435·played_before 31·club_unknown 1), 96팀 played_here 5,650→5,644·not_played 4,337→4,328·played_before 313→312(사본 감소분), 같은 선수 중복 줄 0, 새 영입 확인 대상 0(대기 1 = 445025). 화면: 맨시티 로드리(공급사 날짜 08-16)·베르나르두 실바 방출, 엘리엇 앤더슨 영입, 아칸지 묶음 유지, 레알 '최근 갱신 2026.11.24'·'다시 시도' 없음·콘솔 오류 0.

검수: 백엔드 ruff·pytest 383(DB 포함 539, 다른 기능의 기존 건너뜀 3)·alembic check, 프런트 lint·`tsc --noEmit`·npm test 90·Turbopack 빌드.

## 2026-11-24 (화) — 데스크탑 검수 간단 수정(00)

사용자 데스크탑 전체 검수 중 디자인 없이 진행하기로 한 항목. 08 이적 갱신 결함(b73806c)은 08 채팅에서 별도 처리·병합.

| 영역 | 변경 파일·함수 | 이유 |
| --- | --- | --- |
| TOP 5 띠 | `frontend/src/features/top5/Top5Strip.tsx`(바깥 띠 클릭 → 토글 버튼) | 하늘색 띠가 화면 전체인데 가운데 1280px만 눌림 |
| 딤 배경 | `frontend/src/components/ui/Dialog.tsx`(`backdrop:cursor-pointer`), `app/globals.css`(TOP 5 시트 전용 규칙 삭제) | 딤을 누르면 닫힌다는 것을 포인터로 알림(의견 보내기 등 모든 다이얼로그·시트) |
| 경기일 기간 | `backend/app/services/fixtures.py`(`FUTURE_MATCH_DAYS` 28), `schemas/schedule.py`·생성 타입·`ScheduleSection.tsx` 설명, `tests/test_schedule_db.py` | 미래 경기일 17 → 28개(사용자 결정) |
| 통계 이름 | `frontend/src/features/match/model.ts`(`STAT_LABELS` Free Kicks), `tests/match-regressions.test.mjs` | 영문 그대로 보이던 항목 |
| 내 평가 갱신 | `frontend/src/features/match/ReviewComposer.tsx`(`refresh`에 `queryKeys.me.reviews`) | 경기 상세에서 평가를 바꿔도 마이페이지 목록이 바로 바뀌지 않음 |

- **검사:** ruff, 기본 pytest 383 통과/159 건너뜀, DB 포함 pytest 539 통과(기간 테스트 갱신), lint·tsc·프런트 테스트 91. build는 개발 서버 실행 중이라 미실행.
- **브라우저(1920):** 띠 왼쪽 빈 영역 클릭 → 목록 열림, 의견 보내기 딤 포인터, 날짜 막대 32개(과거 3 + 오늘 + 미래 28). 프리킥은 테스트로 확인, 내 평가 즉시 갱신은 회원 로그인 브라우저 확인 미실행.

## 2026-11-23 (월) — 09 마이페이지(관심 팀·내 평가·계정 관리)

브랜치 `feat/09-mypage`(최신 `dev` 2c39a4d)에 커밋·push 후 `dev` 병합. 02 API만 사용했고 새 서버 API·마이그레이션은 없다. Codex 교차 검증 4차례(1차 N1~N4·7번 의견, 2차 N1 잔여·N5~N7, 3차 N8·N9, 최종 N10·N11은 Codex가 직접 보완) 후 통과.

| 영역 | 변경 파일·함수 | 이유 |
| --- | --- | --- |
| 화면 | `frontend/src/app/mypage/page.tsx`, `features/mypage/MyPage.tsx`·`MyCard.tsx` | MY-001: 인증 확인 중 개인 정보 없음, 비회원·만료 세션은 로그인 안내 카드(`loginHref('/mypage')`), PC 2열(왼쪽 관심 팀·내 평가, 오른쪽 360px 계정 관리) |
| 관심 팀 | `features/mypage/FavoriteTeams.tsx`, `favorites/useFavorites.ts`(`memberFavoritesQuery` export) | MY-002: 다른 화면과 같은 `useFavorites()`, 10 / 10이면 추가만 막고 한도 안내, 상세 제공 팀만 링크, 추가·삭제 뒤 포커스 |
| 내 평가 | `features/mypage/MyReviews.tsx`·`queries.ts`·`model.ts`, `features/match/ReviewTextForm.tsx`(새, `ReviewComposer`와 공용) | MY-003: 최신순, 수정한 평가만 수정 날짜, 수정·삭제 뒤 경기 상세 건수 반영, 닫힌 경기 수정은 409 `CONFLICT` 안내 |
| 작성 제한 | `features/match/ReviewRestriction.tsx`(새 — `ReviewRestrictionNotice`·`useRestrictionEnd`) | Codex 7번 의견·사용자 결정: 마이페이지도 경기 상세처럼 안내·수정 비활성·삭제 유지 |
| 계정 관리 | `features/mypage/AccountPanel.tsx`·`PasswordDialog.tsx`·`WithdrawDialog.tsx`, `components/ui/Dialog.tsx`(`closeDisabled`·`sheetInset`) | MY-004: 이메일 계정만 비밀번호 변경(오류 코드↔칸 1:1, 저장 중 잠금, 실패 시 입력 유지), 탈퇴(62:1800) 후 비회원·메인 |
| 세션 경합 | `features/auth/session.ts`(`authEpoch`·`signedOut`·`memberRequest`), `ReviewComposer.tsx`·`ReviewSection.tsx` | Codex N1·N3·N5·N6·N8~N10: 로그아웃·회원 전환·재로그인 뒤 늦은 응답과 401이 새 세션을 바꾸지 않게, 회원 전용 요청 401은 비회원 전환 후 로그인 안내(경기 상세는 초안·intent 유지한 로그인 이동). 첫 세션 확인 완료는 세대 변경이 아님(정상 갱신 보존) |
| 로그인 복귀 | `ReviewComposer.tsx` | Codex N11: 수정 초안 복원 시 입력창이 생긴 뒤 포커스 |
| 테스트 | `frontend/tests/mypage.test.mjs`(새 7개), `auth-session.test.mjs`·`match-regressions.test.mjs`(세션 경합·복귀 포커스), `backend/tests/test_auth_db.py`(닫힌 경기 수정 409·삭제 204) | 회귀 |

- **사용자 결정:** Figma 주석은 참고(구현에 문제 없으면 차이 보고 안 함), 작성 제한 회원의 마이페이지 수정은 경기 상세와 맞춤. 닫힌 경기 409는 드문 상황이라 코드 검수·테스트로 고정. 같은 이메일 재가입은 사용자가 실제 계정으로 확인.
- **실제 계정 검수:** 테스트 계정 A·B(탈퇴는 B 1개). 비밀번호 변경 후 A는 원래 비밀번호로 되돌림. 검수용 평가는 작성 후 삭제. 유료 외부 호출 0회.
- **검사:** backend ruff, pytest 381 통과/158 건너뜀, `KICKTAB_DB_TESTS=1` 539, alembic check 변경 없음. frontend lint, tsc, npm test 90, build, `git diff --check`.

## 2026-11-23 (월) — TOP 5 유료 Neon 전환·선정 시간 12분·이미 치른 주간 경기 후보·일정 신선도 결함 수정(00)

브랜치 `feat/04-match-detail`(최신 `dev` a600efc)에 커밋·push 후 `dev` 병합. 계기: 11/23 00:00에 서버가 꺼져 있어 자동 선정이 돌지 않았고, 수동 복구가 ① 일정 신선도 확인 결함 ② 무료 Gemini 3.8 Flash 503·504(요청 10번 모두)로 실패. 사용자가 Gemini 유료 등급으로 전환하고 다음을 결정했다.

| 영역 | 변경 파일·함수 | 이유 |
| --- | --- | --- |
| 일정 신선도 | `backend/app/services/top5_selection.py`(`check_schedule` — `fixtures` 작업이 실제로 받는 시즌만 90분 신선도 확인) | 코파 델 레이 2026처럼 저장 시즌 종료일이 조회 기간 전인 대회는 수집 대상에서 빠지는데 확인 대상에는 남아 선정이 막힘(시도 4346) |
| 후보 범위 | `candidate_rows`(예정 NS·진행 중(SUSP 제외)·정상 종료 FT/AET/PEN, 시작 전 조건 삭제), `select_week`(최근 폼·맞대결을 킥오프 시점으로 자름), `build_prompt`(이미 치른 후보 규칙), `PROMPT_VERSION` `2026-11-23.1` | 늦은 수동 복구에서 월요일 새벽 경기(11/23 01:30 리버풀–맨유)가 빠짐 — 00:00 선정과 같은 주를 판단해야 함(사용자 결정) |
| 선정 시간·요청 | `WINDOW_MINUTES` 12, `gemini_generate`(최대 3번: 근거 준비 즉시·00:05·00:10 고정 시각, 요청은 다음 시각까지만, `RETRY_BEFORE_END`·`MIN_REQUEST_SECONDS`), `config.py`(`top5_attempt_timeout_seconds` 720), `notifications/discord.py`·`sync/top5.py`·`services/top_matches.py`(문구) | 유료 전환 후 비용 최소화(사용자 결정: 00:20 → 00:12, 재요청 00:05·00:10 두 번만) |
| 모델 | `config.py`(`top5_llm_model` `gemini-4-neon`), 로컬 `.env`·`.env.example`(커밋 안 함) | Hydrogen·Neon 각 1번 비교(같은 후보 137경기, 생각 수준 low): Hydrogen 10.6초·$0.072, Neon 22.7초·$0.152, Neon 이유가 더 구체적·근거 일치 |
| 테스트 | `backend/tests/test_top5.py`(요청 시각·최대 3번·늦은 근거·00:12), `test_top5_db.py`(00:00 성공 시 요청 1번뿐 — 00:05·00:10·정리 작업·재실행 모두 요청 없음, 이미 치른 경기 후보, 수집 대상 밖 시즌 무시, 00:12 기준 시각) | 비용 회귀 방지 |

- **생각 수준:** `low` 유지. Neon 기본값은 high라 생각 토큰·응답 시간이 늘어 요청당 비용이 커진다. low 비교에서 이유의 질이 충분했다(생각 1,962토큰).
- **이번 주 공개:** 새 요청 없이 비교 때 받은 Neon 답(시도 4403 후보 137경기, 프롬프트 `2026-11-19.1`)을 서버 검증 후 시도 4543으로 공개(`llm_output.note`에 출처·토큰 기록). 이 답은 리버풀–맨유가 후보에 없던 때의 결과다.
- **비용:** 11/23 과금 약 $0.22(330원, Hydrogen+Neon 1번씩). 3.8 Flash 503·504 요청은 과금되지 않은 것으로 보임. Neon 예상 주 1번 약 220원(후보 수에 따라 110~340원).
- **검사:** ruff, 기본 pytest 381 통과/158 건너뜀, DB 포함 pytest 539, alembic check 변경 없음. 브라우저 메인 TOP 5 띠 11/23–11/29 표시.

## 2026-11-22 (일) — 04 경기 상세 진행 중 화면 실경기 검수·보완(유벤투스–베네치아)

브랜치 `feat/04-match-detail`(최신 `dev` 0b397a6 — 02 병합 포함 — 반영 후 작업)에 커밋·push 후 `dev` 병합. 계기: 사용자가 11/21 맨시티–풀럼 진행 중 화면이 Figma 최신과 다르다고 지적. 11/22 20:30 유벤투스–베네치아(1550201)를 킥오프 전~종료까지 사용자와 함께 실시간 검수. 사용자 결정: 진행 중도 데스크톱 경기 기록·평가 같은 줄, 이벤트 0건이어도 상태 줄만 추가(시안 불필요), 하프타임 표기, 하프타임 교체는 '전반 종료' 위, 킥오프 전 실시간 호출 제거를 03 대신 04에서 반영.

| 영역 | 변경 파일·함수 | 이유 |
| --- | --- | --- |
| 타임라인 | `frontend/src/features/match/model.ts`(`timelineRows`·`TimelineRow`·`halfTimeSubstitutions`), `MatchRecords.tsx`(`Timeline`·`Minute`·`EventBody`·`TimelineTeam` — Figma 161:4161/52:151 크기: 시간 열 56px, 시간 12px, 이벤트 13px, 줄 최소 52px) | 시안의 상태 줄('n′ 후반 진행 중'·'45′ 전반 종료'·'경기 종료')이 없었음. 끝난 구간 추가시간은 제공사가 주지 않아(`periods`·`status.extra` 빈 값 실측) 45′·90′·120′, 마지막 이벤트가 추가시간이면 그 분 |
| 배치 | `features/match/model.ts`(`areasOf` — 진행 중도 `reviewsBeside`), `MatchDetail.tsx` | 진행 중 데스크톱도 경기 기록 왼쪽·평가 오른쪽 384px(사용자 결정, Figma 161:4161은 아래 배치) |
| 하프타임 표기 | `backend/app/schemas/match.py`(`MatchSummary.live_break`), `services/fixtures.py`(`LIVE_BREAKS`, `to_summary`), 생성 타입, `frontend/src/lib/format/match.ts`(`statusWord`), `components/common/MatchStatusBadge.tsx` | HT 동안 모든 카드가 '진행 중 45′'. HT '하프타임'·BT '연장 전 휴식'(분 없음) |
| 실시간 호출 | `backend/app/services/fixtures.py`(`LIVE_LEAD` 삭제, `needs_live_sync` 킥오프부터), `sync/fixtures.py`(설명) | 킥오프 전 30분 호출은 정보가 없음(최근 7일 116회 중 52회) |
| 테스트 | `backend/tests/test_schedule_db.py`(+1: 킥오프 기준·`live_break`), `frontend/tests/match-regressions.test.mjs`(상태 줄·0건·하프타임 교체 6가지·하프타임 배지·진행 중 배치) | 회귀 |

- **실경기 확인(1550201):** 킥오프 전 30분 60초 호출 확인(제거 대상) → 20:32 1H 반영, 예정 화면이 새로고침 없이 진행 중으로 전환 → 21:18 HT(전반 이벤트 0건, 원본도 0건) → 21:33 2H(하프타임 교체 2건) → 22:21 FT 4:0, 실시간 응답에서 빠진 경기를 `?ids=`로 재조회해 최종 기록 저장. 원본 대조: 이벤트 14건·분 일치, 평점 32명 일치, 진행 중 평점은 90초 보충으로 갱신(2′ 시점 '미제공'은 제공사 미제공).
- **제한:** 앱 안 브라우저 창을 숨기면 브라우저가 타이머를 멈춰 갱신이 늦어짐(지연 경고는 설계대로 표시, 포커스 시 즉시 따라잡음). 화면 켜 둔 상태의 60초 갱신은 사용자 브라우저로 확인. 연장·승부차기·BT 실경기는 미확인(테스트로만).
- **검사:** ruff, 기본 pytest 381 통과/155 건너뜀, DB 포함 pytest 536, alembic check 변경 없음, lint·tsc·프런트 테스트 71·build·`git diff --check` 통과.

## 2026-11-21 (토) — 06 UEFA 토너먼트 대진 카드 제목 표기(사용자 Figma 수정 반영)

브랜치 `feat/06-standings`(최신 `dev` a13c125 병합)에 커밋·push 후 `dev` 병합. 사용자가 Figma 리그 순위 · UEFA 16강 대진 데스크톱 레이어(`451:20753`)의 대진 제목을 이전과 같은 '팀 로고 vs 로고 팀' 양식으로 통일한 것을 반영.

| 영역 | 변경 파일·함수 | 이유 |
| --- | --- | --- |
| 대진 카드 제목 | `frontend/src/features/standings/KnockoutStage.tsx`(`SlotTitle`에 `home` — `lg:flex-row-reverse lg:text-right`) | 데스크톱은 홈 '이름 로고' · vs · 원정 '로고 이름'(vs 기준 대칭), 모바일(`451:20778`)은 '로고 이름 vs 로고 이름' 그대로. DOM 순서는 로고 → 이름 유지 |

검수: 브라우저 1280(갈라타사라이 [로고] vs [로고] 리버풀, vs 양쪽 간격 12px로 같음)·1024(카드 잘림 0)·375(로고 → 이름), 페이지 가로 넘침 없음, 콘솔 오류 0. lint·tsc·npm test·build 통과.

## 2026-11-21 (토) — 08 이적 출전 근거 결정 B·Codex N1 보완·00 소규모 수정

브랜치 `feat/08-team-detail`(2026-11-20 `dev` 병합 7b56869 이후)에 한 커밋으로 커밋·push 후 `dev` 병합. Codex 교차 검증 차단 0·중요 0·경미 1 → N1 보완. 그 밖의 판단(득점·도움 0도 '값 있음' 유지, 445025 재확인 유지, 판정 순서)은 현재대로.

| 영역 | 변경 파일·함수 | 이유 |
| --- | --- | --- |
| 사용자 결정 B | `services/team_detail.py`(`move_evidence` — 이 팀 출전 NULL 줄은 같은 줄 득점·도움·평점이 있으면 출전 근거, `parse_player_season` — 값 있는 NULL은 최소 1·빈 NULL은 0, `judge_move` 순서 records_incomplete → played_here, 삭제 `appearances_unknown`·`MoveEvidence.unknown`), `models/team_detail.py`(설명) | 출전 수 미제공 해석(D-08-6a). 이전 팀 캐시 NULL 선수·시즌 273건 재확인(274회 — 11/21 결정 B 적용 때) |
| Codex N1 | `services/team_detail.py`(`club_appearances_unknown` 분기·설명 삭제, `prior`·`parse_player_season`·`save_player_season` 타입 `int`), `tests/test_team_detail.py`(합성 테스트 삭제), DB `player_club_seasons` 무효 캐시 1행 삭제(445025·2024·9587·NULL) | 도달하지 않는 분기(작업 원칙 5). 445025/2024 확인 상태는 유지(check_pending) |
| 00 소규모 수정 | `services/top5_selection.py`(`stored_standings` — 06 `standings` 저장 표 우선, 없는 표만 API), `tests/test_top5_db.py`, 프런트 `TeamDetail.tsx`·`teams/TeamsSection.tsx`(`competitionName()` 한글 대회명) | TOP 5 호출 절감, 03 대회명 통일 메모(§3.1) 반영 |
| 테스트 | `tests/test_team_detail.py`·`tests/test_team_detail_db.py`(결정 B 판정·NULL 해석), `tests/test_top5_db.py` | 회귀 |
| 문서 | `docs/guide.md`(첫 단락·§3 08·§6.5·D-08-6a·§11), `docs/file-feature-map.md`, 이 문서 | 사용자 요청으로 세 문서 최신화 |

결과: 8개 팀×2시즌 바로 보이는 400 → 359줄, 접힘 258 → 299줄, 이 팀 출전 근거 없이 표시 73 → 32줄. 이동 사유 8개 팀 played_here 425·not_played 435·played_before 31·club_unknown 1(N1 보완 전후 같음), 전체 96팀 played_here 5,646·not_played 4,337·played_before 314·club_unknown 25·check_pending 1. N1 보완의 외부 호출 0회.

검수: 백엔드 ruff·pytest 339(DB 포함 446)·alembic check(head 0018), 프런트 lint·`tsc --noEmit`·npm test 62·Turbopack 빌드.

## 2026-11-20 (금) — 08 팀 상세 비회원 전체 검수 개선

브랜치 `feat/08-team-detail`(최신 `dev` a7ef699 병합 후 작업)에 커밋·push 후 `dev` 병합. 기준: PRD v1.14 Fix, 기능 명세서 v1.14 Fix(TEAM-002 규칙 1·6·7, TEAM-006 규칙 1~6과 추가 검수), 유저 플로우 v1.13 Fix, Figma 52:1254·58:738·308:4617. 사용자 결정: 이적료·원화 환산 제외(D-08-10), 최근 5경기는 06 범위. Codex 교차 검증 2회(1차 중요 3·경미 2 → 보완 후 2차 통과).

| 영역 | 변경 파일·함수 | 이유 |
| --- | --- | --- |
| 선수단 합계 범위 | `services/team_detail.py`(`record_competitions` — 활성 대회 중 그 시즌 `no_data` 아닌 것, `parse_team_players(…, competitions)`, `missing_record_competitions`), 삭제 `RECORD_COMPETITIONS` | TEAM-002 규칙 1·7: 국내 컵·슈퍼컵·개최 클럽 월드컵 포함, 친선·미개최 제외, 제외용 하드코딩 없음 |
| 출전 근거 수집 | `sync/team_detail.py`(`team_player_stats` 과거 2시즌 1회·`season=` 수동 경로, 새 작업 `transfer_player_checks` 00:40 KST·`PLAYER_CHECKS_PER_RUN`, `_run_units`의 실패 기록 인자), `models/team_detail.py`(`PlayerSeasonCheck`·`PlayerClubSeason`), `migrations/versions/20261120_0018_player_season_checks.py`(새) | 2024 기록을 2025-26 이적 근거로, 새 영입의 이전 팀 1군 출전을 `/players?id=&season=`로 선수·시즌당 1회 |
| 이적 판정 | `services/team_detail.py`(`NOT_FIRST_TEAM`·`is_first_team`·`parse_player_season`·`evidence_seasons`·`check_season`·`move_evidence`·`is_loan_return`·`judge_move`·`pending_checks`), 삭제 `GROUP_TYPES`·`YOUTH_SIDE`·`TransferContext`·`shown_first` | TEAM-006 규칙 6: 출전 근거로 판정, 근거 부족은 숨기지 않음, 임대 복귀는 이 팀 출전만(Codex '유지 권고') |
| 같은 선수 묶음 | `services/team_detail.py`(`MoveGroup`·`group_moves`), `schemas/team_detail.py`(`TransferGroup`, `TransferItem.direction`), `api/routes/teams.py`, 프런트 `SeasonRecords.tsx`(묶음 줄), `lib/api`(타입·생성 타입) | TEAM-006 추가 검수: 이동은 그대로 보존하고 한 줄로 표시 |
| Codex 1차 보완 | `move_evidence`·`judge_move`(`appearances_unknown`), `parse_player_season`(양수 없음 + 빠진 값 = 미확인, 구단·대회 없는 줄은 응답 거부), 프런트 `types.ts`(미사용 `TransferItem` 별칭 삭제), `guide.md`(다음 마이그레이션 0019) | N1~N3 출전 수 미제공을 미출전으로 접던 결함, N4·N5 |
| 화면 문구 | `SquadTable.tsx`(합계 범위 안내·주석) | 컵·슈퍼컵·클럽 월드컵 포함 |
| 테스트 | `tests/test_team_detail.py`(대회 마스터 선별, 판정 규칙 4종, 임대 복귀, 1군 기준, NULL 조합, 구단·대회 없는 줄, 묶음), `tests/test_team_detail_db.py`(합계 범위, Akanji 한 줄, 접힘 = not_played만, 영입 확인 작업·재시도, NULL 근거 방출, 작업 단위) | 새 규칙 회귀 |
| 문서 | `docs/guide.md`(첫 단락·§3 08·§3.1·§6.4·§6.5·D-08-6a·§11), `docs/file-feature-map.md`, 이 문서 | 사용자 요청으로 세 문서 최신화 |

실제 외부 호출(2026-11-20, 이 작업): 응답 표본 2, 선수 기록 재수집 2026 193·2025 247, 2024 316, 영입 이전 팀 확인 1,617(서버 시작 시 자동 실행 117 + 1,500 — 수동 실행과 겹쳐 분당 제한 오류 → 재실행), Codex 1차 보완 후 재확인 222 = 2,597회(그날 전체 약 4,840/7,500). 남은 확인 대상 0, 이후 새 영입만. 저장: 선수 기록 2024 10,066·2025 8,207·2026 5,384줄. 8개 팀(맨시티·레알·맨유·바이에른·PSG·유벤투스·아스널·바르셀로나)×2025·2026 전후: 바로 보이는 514이동 → 400줄, 같은 선수 중복 줄 109 → 0, 출전 0 노출 150 → 73, 접힘 378 → 258, 근거 부족 78. 주요: 로드리·베르나르두 실바 방출, 엘리엇 앤더슨 영입, 아칸지 한 줄, 워커·모드리치(2024 근거) 표시. 선수단 96팀 합계 = 대회별 합(불일치 0), 라리가 11팀 코파 델 레이 부분 집계.

검수: 백엔드 ruff·pytest 333(DB 포함 439)·alembic check(head 0018), 프런트 lint·`tsc --noEmit`·npm test 62·Turbopack 빌드. 브라우저 320·375·640(1280의 200%)·768·1024·1280·1920 이적 영역·모바일 기록 탭 가로 넘침 0, 시즌·반기·URL half·뒤로 가기, 콘솔 오류 0.

## 2026-11-20 (금) — 06 리그 순위 비회원 전체 검수 개선

브랜치 `feat/06-standings`(최신 `dev` f211ab2 병합 후 작업)에 커밋·push 후 `dev` 병합. 기준: PRD·기능 명세서(LEAG-001·002·004, TEAM-001 규칙 3, MAT-005 규칙 4, CMP) v1.14 Fix, 유저 플로우 v1.13 Fix, Figma `49:57`·`49:570`·`234:8881`·`234:9750`·`53:1353`·`53:2047`·`61:1653`·`61:2355`·`567:7275`. Codex 교차 검증 2회(1차 결함 2·개선 2 → 보완 후 통과). 마이그레이션 없음.

| 영역 | 변경 파일·함수 | 이유 |
| --- | --- | --- |
| 메인 리그 순위 | `features/standings/MainStandings.tsx`, `ChipRow.tsx`, 백엔드 `services/standings.py`(`league_competitions`) | LEAG-001: 제목 '리그 순위', 5대 리그 + UEFA 3개 리그 페이즈 상위 6팀, 링크 '전체 순위 보기'/'전체 순위·대진 보기'(현재 시즌), PC 화살표(넘칠 때만·끝 비활성)·모바일 스와이프+가장자리 흐림, 옛 휠·끌기 코드 삭제 |
| 대회명 | `features/standings/useCompetitionLabel.ts`(새), `model.ts`(`LEAGUES`·`UEFA`·`COMPETITIONS`) | DB `name_ko` 기준(guide §3.1), 영문 칩 삭제 |
| 공통 최근 5경기 | `components/common/RecentForm.tsx`(새, `FormItem`·`formItem`), 삭제 `features/standings/RecentForm.tsx`, 04 `HeadToHeadSection.tsx`·`match/model.ts`(`formItems`, 삭제 `formPreview`·`RESULT_LABEL`), 08 `TeamDetail.tsx` | LEAG-002 규칙 4·MAT-005 규칙 4: 네 화면 같은 표현(오래된 순·최신만 테두리·화면 '최신' 글자 삭제·팝업 '날짜 · 대회'+'홈 – 스코어 – 원정'), 팝업은 실제 높이로 위/아래/화면 안 배치(낮은 창) |
| 최근 경기 데이터 | 백엔드 `schemas/standings.py`(`RecentMatch.competition`), `routes/standings.py`, `routes/teams.py`(`_recent`), `services/team_detail.py`(`official_form`, `RecentResult.competition`) | 팀 상세 = 친선 제외 전체 공식 경기(04 `team_forms` 재사용, 열 때 `ensure_form` — 새 종료 경기·7일 경과 때만 1~2회, 실패 시 기존 유지), 한 번도 받지 않은 팀은 저장 경기로 대체 |
| 순위 구간 | `features/standings/model.ts`(`tableBands`·`bandOf`·`rangeText`, 삭제 `leagueZone`·`phaseBands`), `StandingsTable.tsx`(`bandRowClass`·`BandLegend`·`BasisNote`, `TeamCell` 이름 폭 제한), `LeaguePhaseTable.tsx` | LEAG-002 규칙 5·6: 행 배지 → 행 왼쪽 테두리 + 범례 한 번, 접근성 이름에 구간, '현재 순위 기준'/'확정 결과', 1024px 긴 팀명 말줄임 |
| UEFA 선수 순위 | 백엔드 `routes/standings.py`(UEFA 허용·이름 HTML 엔티티 해제), `sync/standings.py`(UEFA 포함·제외 줄 로그), `services/standings.py`(`due_leagues` UEFA 결과 후에만, `OUTFIELD_POSITIONS`·`teamless`), 프런트 `StandingsSection.tsx`·`PlayerRankings.tsx`·`KnockoutStage.tsx` | LEAG-004: 예선 포함 대회·시즌 전체(실제 API로 예선 포함 확인), 리그 페이즈·토너먼트 화면 모두 오른쪽 선수 순위. 공급사 페이지 응답의 팀 빈 줄은 명확한 필드 선수만 빼고 골키퍼·포지션 미확인은 단위 거부 |
| 테스트 | 백엔드 `test_standings.py`·`test_standings_db.py`·`test_team_detail_db.py`, 프런트 `standings.test.mjs`·`match-regressions.test.mjs` | 구간 판정, 최근 5경기 범위·대체·실패 보존, UEFA 선방(누락 제외·공동 순위), UEFA 갱신 조건, 팀 빈 줄 규칙, 공통 RecentForm 마크업 |

검수: ruff, pytest 325(+DB 427), alembic check(head 0017), lint, tsc, npm test 62, 빌드(Next 16.4.6) 통과. 브라우저 320·375·768·1023·1024·1280·1920, 1280×560, 640×450(200% 대용), 640×285(낮은 창 팝업) — 페이지 가로 넘침·헤더 가림·팝업 잘림 없음, 콘솔 오류 0. 메인 8개 대회·화살표, 2025-26/2026-27 국내·UEFA 구간(분데스리가 16위 승강 PO), UEFA 3대회 × 2시즌 × 5분류, 최근 5경기 4개 화면, 지난 경기 페이지 분할 폭 변화. 실제 API 호출: UEFA 선수 첫 적재 532 + 사전 확인 7, 챔스 2025 원인 확인·재시도 528 + 중단 실행 1회(기록 없음, 최대 83), Codex 지적 후 UEFA 2025 재적재 337 — 화면 확인 0. 슈퍼컵·클럽 월드컵 등이 팀 상세에 반영되는 실제 화면 예시는 현재 허용 96팀 최근 공식 10경기에 해당 경기가 없어 DB 테스트로만 고정.

## 2026-11-20 (금) — 05 지난 경기 비회원 전체 검수 개선(페이지 분할·새 대회 확인)

브랜치 `feat/05-results`(최신 `dev` 5186d6b 병합 후 작업)에 커밋·push 후 `dev` 병합. 기준: PRD·기능 명세서(HIST-001~003, CMP) v1.14 Fix, 유저 플로우 v1.13 Fix, Figma `53:593`·`53:995`·`187:1946`. Codex 교차 검증 통과(지적 없음) 후, 페이지 분할이 사용자 구상(기존 `< 1 2 3 … 400 >` 양식에서 보이는 번호만 늘리기)과 달라 사용자가 Figma를 수정(`530:21586` PC·`530:21659` 모바일)했고 그대로 다시 구현했다.

| 영역 | 변경 파일·함수 | 이유 |
| --- | --- | --- |
| 페이지 분할 | `frontend/src/components/ui/Pagination.tsx`(`pageItems`·`numbersFor`, 옛 `windowOf`·`edge` 삭제) | 한 줄 `< 1 2 3 … 420 >`, 1·마지막 고정, 줄 폭에 따라 번호 3~9개(PC·태블릿 9, 375px 4, 320px 3 — 320px도 넘침 없음), 화살표 양 끝 비활성. 처음/끝 버튼·두 줄 배치(중간 구현)는 사용자 디자인 수정으로 철회. 팀 탐색 공통 |
| 대회 선택 | `components/common/CompetitionFilter.tsx`(`pickerName`) | 2026-27로 클럽 월드컵 선택을 유지하면 'FIFA 클럽 월드컵 2026'으로 보이던 문제 — 연도는 개최 시즌에만 |
| 테스트 | `frontend/tests/results.test.mjs` | 페이지 항목·폭 계산·렌더, 클럽 월드컵 연도 회귀 |

- **기존 충족:** 소개 제거·'2025-26 시즌'·메인과 같은 검색 묶음·시즌별 보조 문구(11-16 개선), 2025-26만 클럽 월드컵 2025 표시·2026-27 숨김, 개최했지만 실패 별도 안내, 슈퍼컵 카드→상세, 비유럽 팀 검색(링크는 `detailAvailable`), 행정 종료 표시, 영문 대회명 없음.
- **실제 확인:** 2025-26 전체 420페이지(1·2·5·8·210·417·419·420, 번호·이전/다음, URL·뒤로/앞으로, 상세→뒤로 페이지·스크롤 복원, 시즌·대회 변경 시 1페이지), 클럽 월드컵 63경기·7페이지·2026-27 숨김, 실패 상태 모의, 커뮤니티 실드 상세, Flamengo 4경기·팀 상세 미제공, 폭 320·375·640·768·960·1023·1024·1280·1920 넘침·잘림 없음(버튼 44px), 팀 탐색 8페이지, 콘솔 오류 없음.
- **제한:** 비유럽 클럽 월드컵 팀 한글 별칭 없음('플라멩고' 검색 불가), 카드 aria-label에 PK 없음, 실행 중 `next dev`에서 `/teams` 직접 접속 시 자리 표시에서 멈춤(메뉴 이동·프로덕션 빌드 정상, 개발 서버 캐시 계열).
- **검사:** ruff, pytest 324 통과/98 건너뜀(DB 포함 422), alembic check 변경 없음, tsc·lint·프런트 테스트 62·build·`git diff --check` 통과. 외부 API 2회(과거 경기 상세 첫 열람 보충).

## 2026-11-20 (금) — 04 경기 상세 비회원 전체 검수 개선(양쪽 타임라인·평가 로그인 안내·TOP 5 선정 구조 개편)

브랜치 `feat/04-match-detail`(최신 `dev` d6941fd 병합 후 작업, 2026-11-19 시작)에 커밋·push 후 `dev` 병합. 기준: 기획 문서 PRD·기능 명세서(MAT·REV·TOP)·유저 플로우 최신 Fix(TOP 5 선정 구조는 Codex가 개정), Figma `408:16478`(비회원 평가 안내). 사용자 결정: 최근 5경기 흐름 양식은 06에서 진행, 로그인 안내는 Figma 그대로 두고 동작은 02, 하위 모델(`gemini-3.5-flash-lite`) 대체 폐지·`gemini-3.8-flash` 단일, 월요일 00:00~00:20 KST 자동 1회·시도 안 요청 최대 5회, 실패 시 업데이트 지연 안내 유지, 11/16 주 결과를 3.8 Flash 선정으로 교체. Codex 교차 검증 3회(1차 수정 필요 2 → 2차 선정 구조 변경분 수정 필요 4 + 기획 문서 개정 → 3차 N5 1건 보완 후 통과).

| 영역 | 변경 파일·함수 | 이유 |
| --- | --- | --- |
| 타임라인 | `frontend/src/features/match/MatchRecords.tsx`(`TIMELINE_GRID` 홈 왼쪽·시간 가운데·원정 오른쪽, sr-only 팀명, 소속 미확인 가운데, 긴 이름 `overflow-wrap:anywhere`), `model.ts`(`eventText(event)` — 팀명 제거) | 두 팀 이벤트를 열로 구분, 임의 팀 배정 없음 |
| 평가 로그인 안내 | `features/match/ReviewLoginNotice.tsx`(새, '로그인 후 경기 평가를 작성할 수 있습니다.' + primary 전체 폭 '로그인' 버튼, 동작 없음), `ReviewSection.tsx`(안내 삽입, 카드 안쪽 여백 16px) | Figma 최신 `408:16478`, 로그인 동작은 02에서 구현 |
| TOP 5 이유 | `backend/app/services/top5_selection.py`(`PROMPT_VERSION` `2026-11-19.1`, `domesticPriority`·`formSummary`·`standing.of`, 압축 근거 'W 2-1 H'·'W 2-0', `FORBIDDEN_REASON_WORDS`로 '관심 팀' 등 거부) | 등급 나열 대신 순위·흐름·맞대결 근거의 이유 문장 |
| TOP 5 선정 구조 | `top5_selection.py`(`window_end()` 00:20, 자동 시도 00:20−10초까지, `gemini_generate` 요청 최대 5회·요청당 600초·남은 180초 확인(첫 요청 포함)·빠른 일시 오류 30·60·120·120초 뒤 재요청·`LlmError.transient`, `_fail`·`_publish_due_delay` 00:20 보류 지연, `_wait_showing_held_delay`·`_show_held_delay`, `_recovery_weeks`·`_missed_week` 00:21:00), `providers/gemini.py`(`TRANSIENT_CODES`, `thinking_level`), `config.py`(`top5_llm_thinking_level` low, 시도 1200초, 하위 모델 설정 삭제), `notifications/discord.py`(지연 알림 한 종류), `sync/top5.py`(`top5_retry` 작업 삭제), `services/top_matches.py`(주석) | 3.8 Flash 503 과부하·504 시간 초과로 하위 모델 결과가 나가던 문제. 낮은 품질 대신 지연 안내 |
| 이번 주 결과 교체 | 일회성 스크립트(저장소 밖)로 11/16 주 후보(시도 1641 근거)에 3.8 Flash 선정 → 버전 1291·시도 2664 공개 | 사용자 요청 |
| 테스트 | `backend/tests/test_top5.py`(요청 규칙·창 경계·프롬프트·금지 표현·Gemini 래퍼), `test_top5_db.py`(00:20 보류·00:21 누락·실행 중 수동 복구 00:20 전환 3개 등), `test_review_regressions.py`, `frontend/tests/match-regressions.test.mjs` | Codex N1·N2·2차 4건·N5 회귀 |

- **Codex 보완:** 1차 N1·N2. 2차: 00:20 전 실패는 즉시 지연이 아니라 지난주 결과 유지 후 00:20 공개, 첫 요청도 남은 180초 필요, 누락 주 00:21:00 경계, 가이드 이전 정책 '폐지' 표기, 기획 문서 개정(Codex). 3차 N5: 수동 복구 **시작**이 보류 지연을 지우던 문제 → 성공 때만 취소, 실행 중이면 주 잠금을 가진 실행 주체가 00:20에 지연 공개·알림 1회, 마감 전 죽은 실행은 정리 작업이 공개.
- **실제 확인:** 3.8 Flash 실제 호출(성공 93~162초, 실패는 503 과부하·504 시간 초과 — 사용량 한도 아님), 11/16 주 교체 공개. 새 컵 7개 경기 상세 실측(기록 1회 호출 후 재호출 없음).
- **제한:** 실제 월요일 00:00~00:20 경과는 다음 월요일(11/23) 확인 예정. 로그인 버튼 동작·회원 작성 폼은 02. 최근 5경기 흐름 양식은 06.
- **검사:** ruff, 기본 pytest 324 통과/98 건너뜀, TOP 5 DB pytest 20 통과, alembic check 변경 없음, lint·tsc·프런트 테스트 59·build·`git diff --check` 통과.

## 2026-11-19 (목) — 03 경기 일정 비회원 전체 검수 개선(대회 21개·공통 경기일 기간·팀 보기 복원)

브랜치 `feat/03-schedule`(최신 `dev` 359f2e9 병합 후 작업)에 커밋·push 후 `dev` 병합. 기준: PRD v1.13 Fix·기능 명세서 v1.13 Fix(SCH·CMP·NEWS·FAV 비회원, COM-003 대회명)·유저 플로우 v1.12 Fix, Figma `49:57`·`49:570`·`234:8881`·`234:9750`·`193:12311`·`193:12949`·`187:1946`·`308:4617`. 사용자 결정: 대회명은 DB `name_ko` 기준('리그 1' 유지), 21일 달력 폐기, 팀 선택 시 전체 대회. Codex 교차 검증 3회(1차 수정 필요 6·문서 1 → 2차 수정 필요 2·문서 1(00이 보완, 1차 D·I 포함) → 3차 잔여 N11~N13을 Codex가 보완 후 통과).

| 영역 | 변경 파일·함수 | 이유 |
| --- | --- | --- |
| 대회 21개 | `backend/migrations/versions/20261119_0017_competition_groups.py`(새, `FIFA` 그룹 허용 — downgrade는 FIFA 저장 경기가 있으면 중단), `seed/competitions.py`(528·556·547·529·526·531·15, `name_ko`), `models/reference.py`, `sync/reference.py`(21 + 8 = 29회) | 국가별 슈퍼컵 5개·UEFA 슈퍼컵·FIFA 클럽 월드컵 추가, 시즌별 노출(클럽 월드컵은 2025-26만) |
| 수집·판정 | `services/fixtures.py`(`SchedulePeriod`·`schedule_period`, `overlaps(..., stored)`·`stored_seasons`, `covered`(30분 작업 창 안/밖 구분), `sync_state(window)` — `relevant_competition_ids`·`all_failed`·관련 대회가 없는 날은 관리 시즌 적재 이력으로 판정, `fixture_availability`), `sync/fixtures.py`, `api/routes/schedule.py`(`/fixtures/availability`, `/fixtures`의 503 조건, `/fixtures/team` 기간), `schemas/schedule.py` | 공통 경기일 기간(과거 3 + 오늘 + 미래 17 경기일), 갱신 실패·미수집·정상 0건 구분 |
| 메인 일정 화면 | `frontend/src/features/schedule/ScheduleSection.tsx`(기간 공유 날짜 막대·좁히기 합집합·소멸 날짜 이동과 안내(`seenDates`, 목적지 변경 시 안내 갱신)·기간 갱신 실패 경고·팀 보기), `DateBar.tsx`, `queries.ts`(`fixtureAvailabilityQuery`, `teamScheduleQuery(teamId, period)`), `useScheduleParams.ts`, `lib/api/query-keys.ts`, 생성 타입 | 경기 없는 날짜 버튼 제거, 팀 진입은 전체 대회·해제 시 이전 날짜·대회·막대 위치 복원, 기간 변경 시 팀 일정 재조회 |
| 공통 UI | `components/common/CompetitionFilter.tsx`(21개 그룹, 높이 500px 이하 대화상자 전체 스크롤), `components/ui/Dialog.tsx`(`scrollArea`), `components/common/NewsCard.tsx`·`lib/format/match.ts`(대회명 `name_ko` 통일, 시간 미정·VS), `lib/format/kst.ts`, `components/layout/StickyPanel.tsx`·`app/page.tsx`(1280px 두 열/미만 720px 단일 열) | Figma `308:4617`, COM-003 대회명 규칙 |
| 테스트 | `backend/tests/test_schedule_rules.py`·`test_schedule_db.py`·`test_results_db.py`, `frontend/tests/match-regressions.test.mjs` | 기간·창 경계·전체 실패 범위·과거 시즌·소멸 날짜 뒤로 가기 회귀 |

- **실제 확인:** 실제 수집(reference 7·fixtures_season 13·fixtures 14회, 새 대회 경기 81건). 브라우저 320·375·768·1023·1024·1279·1280·1920·200%·1280×570, 콘솔 오류 0. 모의 응답으로 기간 갱신 실패·소멸 날짜 자동 이동·뒤로/앞으로·대회별 목적지 변경 확인. `0017` downgrade 보호는 롤백 트랜잭션에서 확인(FIFA 경기 63건 → 중단).
- **제한:** 실제 진행 경기·실제 자정 경과 미확인. 새로고침 뒤에는 빠진 날짜와 처음부터 잘못된 URL을 구분할 수 없음(범위 안내). 375px 이하 날짜 막대 4칸(Figma 5칸). 06 순위 칩·07/08 영문 대회명은 각 채팅 인수인계.
- **검사:** ruff, 기본 pytest 316 통과/96 건너뜀, DB 포함 pytest 412, alembic check 변경 없음, lint·tsc·프런트 테스트 59·build·`git diff --check` 통과.

## 2026-11-19 (목) — 01 비회원 전체 검수 개선(헤더 높이·순환 띠·PC 패널 비모달·펼친 목록 행)

브랜치 `feat/01-header-footer`(최신 `dev` a3cda8a 병합 후 작업)에 커밋·push 후 `dev` 병합. 기준: PRD v1.13 Fix·기능 명세서 v1.13 Fix(COM-003·TOP-003)·유저 플로우 v1.12 Fix, Figma `128:3700`·`128:4408`·`308:4617`. Codex 교차 검증 1차(보완 필요: 중요 1·경미 2) 보완 후 재검증 통과. 같은 날 앞서 사용자 요청으로 주요 뉴스 제목 옆 '매시간 수집 · 전체 최신 최대 48개' 문구를 삭제했다(`fix/main-news-caption` → `dev`).

| 영역 | 변경 파일·함수 | 이유 |
| --- | --- | --- |
| 높이 | `frontend/src/components/layout/SiteHeader.tsx`(내비 위아래 여백 PC 11px·모바일 10px), `src/app/globals.css`(`--kt-header-height` 130px, 1024px 이상 118px), `HeaderHeight.tsx`(주석) | 헤더+띠 PC 68+1+48+1=118px, 모바일 64+1+64+1=130px. 로고 46/40px·버튼 44px 유지 |
| 순환 띠 | `features/top5/Top5Strip.tsx`(`TICKER_SPEED` 28, `STRIP` 48/64px) | Figma `308:4617` 28px/s 선형 |
| PC 패널 비모달 | `Top5Strip.tsx`(`inertOutside`·Tab 순환·`FOCUSABLE` 삭제, `aria-modal` 제거, 문서 click 캡처로 링크 이동·같은 페이지 메뉴 재선택 시 닫힘, Escape는 상위 모달이 없을 때만) | COM-003·TOP-003: 열린 채 헤더 로고·메뉴·인증 메뉴 사용. 닫기·Escape·딤만 띠로 포커스 복귀, 링크 이동은 이동한 페이지에 포커스 |
| 펼친 목록 행 | `features/top5/Top5List.tsx`(PC 팀 영역 420px, `MatchTeams`·`MatchStatus` 사용, 모바일 높이 420px 미만 시트 본문 스크롤 `SHEET_BODY`·`SHEET_LIST`), `top5/model.ts`(`changeText` 사유 제거), `components/common/MatchCard.tsx`(`useMatchScore`·`MatchStatus`·`MatchTeams` 분리) | 양 팀 엠블럼, 공통 경기 카드와 같은 스코어(VS·—·PK·상태 확인 중)·상태 표시. 200% 확대(640×285)에서 목록이 10px로 납작해지던 문제 |
| Codex 1차 보완 | N1 `MatchCard.tsx` 팀명 `overflow-wrap:anywhere`, N2 `top5/model.ts` `isPlainClick`(문서 캡처·목록 행 공통), N3 `lib/format/match.ts` `statusNotes`(+`MatchStatus`), `tests/top5.test.mjs` +2 | N1 320px '묀헨글라트바흐'가 카드 밖으로 넘침, N2 목록 행 Ctrl+클릭에도 패널이 닫힘, N3 중단 경기에서 제공사 사유가 사라짐 |

- **실제 확인(3000·헤드리스 Edge):** 헤더 실측 1920·1280·1024 118px, 1023·768·375·320 130px, 가로 넘침 0. 본문 시작 32/24px, 앵커 제목 top 118px, 메인 우측 패널 top 130px·구간 끝 멈춤. PC 패널: 띠 Enter → 닫기 포커스 → Shift+Tab 헤더 메뉴 → Enter 이동(패널 닫힘, 포커스는 메뉴 링크), 같은 페이지 메뉴 재선택 닫힘, Escape·닫기·딤 → 띠 포커스, 목록 경기 → 경기 상세(포커스 H1), Ctrl+클릭 유지. 1280×570 목록만 내부 스크롤(301/392). 모바일 시트: 열기·닫기·포커스 제한·띠 복귀·경기 이동, 640×285 본문 스크롤. 순환 28px/s·호버/포커스 정지와 같은 위치 재개·모션 감소 정적·접근성 트리 대진 1회. 목록 행: 실제 경기 응답으로 예정·종료(연장)·경기 중단·취소·긴 팀명, 실제 경기의 상태만 바꿔 진행 중·연기·5개 미만, 띠 상태 지난주 유지·경기 없음·지연 — 겹침·잘림 0. 콘솔 오류 0. 푸터 변경 없음·잘림 없음.
- **제한:** DB에 실제 '진행 중'·'연기' 경기가 없어 상태만 바꿔 확인. 320px 지난주 유지 상태는 기간 줄바꿈으로 헤더 150px(실측 동기화가 따라감). Figma `128:4408`의 모바일 하단 고정 의견 버튼은 사용자 결정(제거)대로 넣지 않음.
- **검사:** 프런트 lint·`tsc --noEmit`·`npm test` 55·build·`git diff --check` 통과. 외부 API 호출 0회, DB는 경기 요약 조회만(읽기 전용).

## 2026-11-18 (수) — 08 팀 상세 수정 반영

브랜치 `feat/08-team-detail`(최신 `dev` e72a3ee 병합 후 작업)에 커밋·push 후 `dev` 병합. 기준: PRD v1.12, 기능 명세서 v1.12(TEAM-002·004·005·006, NEWS-003), 유저 플로우 v1.11(UF-11·UF-15), Figma 52:1254·52:1866·472:18198·478:6886·469:6642·470:6667·471:6856. 사용자 결정: 이적료·원화 환산 제외(D-08-10), 선수 기록은 8개 대회만. Codex 교차 검증 2회(1차 차단 1·경미 5 → 보완 후 2차 통과).

| 영역 | 변경 파일·함수 | 이유 |
| --- | --- | --- |
| 선수 기록 수집 | `migrations/versions/20261118_0016_team_player_stats.py`(새: `team_player_stats`·RLS, `team_syncs.kind`에 `player_stats`), `models/team_detail.py`(`TeamPlayerStat`), `services/team_detail.py`(`parse_team_players`·`save_team_player_stats`·`_add_record_players`), `sync/team_detail.py`(`team_player_stats` 15:30 KST·`_player_units`) | 06 `player_season_stats`는 리그 줄만이라 UEFA를 못 담음 — 팀별 `/players?team=&season=` 전체 페이지, 8개 대회 줄만, 06과 행 소유 분리 |
| 선수단 응답 | `api/routes/teams.py`(`read_team_squad`·`_totals`), `services/team_detail.py`(`read_squad`·`missing_record_competitions`·`flag_url`), `seed/countries.json`(새, `/countries` 1회) | 합계·대회별 줄·국기·부분 집계, 누락은 null(0으로 채우지 않음) |
| 최근 5경기 | `services/team_detail.py`(`recent_results`·`match_result`), `routes/teams.py`(`recent`), 삭제 `ensure_form` 호출·`form_block` | 저장된 공식 경기에서 오래된 순, 요청 시 외부 호출 없음 |
| 이적 | `services/team_detail.py`(`parse_transfers` 원본 저장, `merge_transfers` (가)(나), `transfer_context`·`shown_first`·`YOUTH_SIDE`), `routes/teams.py`(반기별 `other*`) | 중복 정리는 응답 때, 표시 기준 B와 '기타 이동' |
| 기타 API | `services/news.py`(`TEAM_NEWS_LIMIT` 24), 시즌 기록 `not_participated`, 응답 필드 삭제(`TransferHalf.start/end`, `CoachInfo.photoUrl`, `TransferCounterpart.crestUrl`, `SquadSeasonStats`) | 팀 뉴스 24개, 승격 팀 문구, 작업 원칙 5 |
| 화면 | `features/team-detail/TeamDetail.tsx`(PC 2열·헤더 472:18198·URL `half`·pushState), `SquadTable.tsx`(합계·국기·대회별 기록 Dialog·부분 집계), `SeasonRecords.tsx`(시즌 버튼·빈 상태 문구·반기 탭·기타 이동), `TeamNews.tsx`(24개), `TeamMatches.tsx`, `model.ts`(`seasonText`·`currentHalf`·`pickHalf`·유형 번역), `components/ui/Tabs.tsx`(`disabled`·`trailing`), `components/ui/DataState.tsx`(`retryLabel`), `lib/api/schema.d.ts` | Figma 기준 배치·문구, '다시 시도' |
| Codex 1차 보완 | `parse_team_players`(같은 선수 반복 → 응답 전체 거부), `SquadTable`(Dialog 유지 → 포커스 복귀), `TeamNews`(빈 상태 설명 삭제), `TeamHeader`(16·12·56px), 응답 필드 삭제, `guide.md`(§6.4·§3.1·D-08-5·§2) | 차단 1(기존 기록 삭제 후 성공 처리)·경미 5 |
| 테스트 | `tests/test_team_detail.py`(`merge_transfers`·기준 B·`parse_team_players`·반복 거부·`match_result`), `tests/test_team_detail_db.py`(합계 = 줄 합, 최근 경기, not_participated, 이적 정리·표시, 뉴스 24, 반복 페이지 기록 유지, 작업 단위), `frontend/tests/team-detail.test.mjs`(유형 문구·반기 선택) | 새 규칙 회귀 |
| 문서 | `docs/guide.md`(첫 단락·§2·§3 08·§3.1·§6.3~§6.5·D-08-5~8·§11), `docs/file-feature-map.md`, 이 문서 | 사용자 요청으로 세 문서 최신화 |

실제 수집: team=50 5회 → 전체 96팀×2시즌 434회(실패 0, 8,299줄 — 2025 4,478·2026 3,821), `/countries` 1회, 맨시티 원본 비교 2회(PL 29줄 145경기·UCL 26줄 62경기 일치, League Cup·Community Shield 제외), 반복 거부 강화 후 전체 현재 시즌 재수집 192회+맨시티 2회 모두 성공. 하루 전체 호출(`sync_runs`) 11/16 1,025·11/17 1,068·11/18 1,273회. 이적 정리 2025-26 7,159→5,960·2026-27 4,559→4,355, 기준 B 팀 평균 45.4→28.3(맨시티 2026 57건 중 표시 35·기타 22). 사고: 0016 첫 적용 실패 직후 `alembic downgrade -1`이 04의 `0015`를 되돌렸다가 재적용(리뷰 0건·보호 조건으로 손실 없음 확인, Codex 판단 유지).

검수: 백엔드 ruff·pytest 313(DB 포함 403)·alembic check(head 0016), 프런트 lint·`tsc --noEmit`·npm test 53·Turbopack 빌드, `git diff --check`. 브라우저 1920·1440·375·320에서 맨시티·레알 마드리드·입스위치(승격)·토트넘(뉴스 24)·노팅엄(뉴스 없음): 최근 5경기 팝업, 선수단 10→27명·합계 = 대회별 합·국기/'—'·표 내부 가로 스크롤, Dialog 포커스 복귀, 뉴스 6→24, Stones 1건·PSV 1건·Rodri/Bernardo 방출·Anderson 영입·아칸지/에체베리 표시·기타 이동 22, 후반기 비활성·'후반기는 1월부터'·URL·뒤로 가기, 빈 상태 3종·오류 '다시 시도', 비회원 링크 흐름, 콘솔 오류 0.

## 2026-11-18 (수) — 07 팀 탐색 개선

브랜치 `feat/07-team-browse`(최신 `dev` 4bc6693 병합 후 작업)에 커밋·push 후 `dev` 병합. 기준: PRD v1.12 Fix, 기능 명세서 v1.12 Fix LEAG-003, 유저 플로우 v1.11 Fix UF-10, Figma 52:624·52:949·57:766·57:836. Codex 교차 검증 2회(1차 중요 1·경미 1 → 보완 후 2차 통과). 외부 API 호출 0회, 마이그레이션 없음.

| 영역 | 변경 파일·함수 | 이유 |
| --- | --- | --- |
| 상단 정리 | `app/teams/page.tsx`(sr-only H1), `TeamsSection`의 `FavoritesNotice`(5팀일 때만 '관심 팀은 최대 5팀까지 등록할 수 있습니다.') | LEAG-003 v1.12: 상단 소개와 상시 '관심 팀 n/5' 제거, 제한 초과만 간결하게 안내 |
| 공통 검색 | `components/common/TeamSearch.tsx`(`label`·`defaultText`·`onSubmitText`), `TeamsSection`(라벨 '팀 검색'·보조 문구, 후보는 현재 5대 리그 팀만) | 기존 페이지들의 돋보기·작은 X·자동완성 구조 재사용. 후보 선택 = 그 팀 카드, 후보 없는 Enter = 단어 검색(결과 없음은 Figma 57:766) |
| 고른 팀 조건 | `services/team_browse.py`(`team_id`), `api/routes/teams.py`(`team`), `useTeamsParams`(`team`, 32비트 상한), `queries.ts`, `lib/api`(쿼리 키·생성 타입) | 렌·바르셀로나·파리처럼 이름이 다른 팀 이름에 들어가 단어 검색으로는 고른 팀만 보일 수 없음 |
| 리그 필터 | `TeamsSection`(06 `ChipRow` 재사용) | 모바일 한 줄 가로 스크롤, 페이지 가로 스크롤 없음 |
| 상태 문구 | `TeamsSection` | 로딩·조회 실패·검색 결과 없음 57:766, 소속 미확인 57:836('강등으로 단정하지 않고 팀 링크를 잠시 보류합니다.') |
| 삭제 | `TeamsSection`의 `SearchField`(0.3초 자동 반영·연속 입력 기록 처리), `useTeamsParams`의 `urlKey`·replace | 공통 검색으로 바뀌어 쓰지 않음(작업 원칙 5) |
| 자체 검수 보완 | `TeamsSection` | 같은 조건(빈 입력 포함)의 Enter가 기록을 한 단계 더 쌓던 문제 |
| Codex 1차 보완 | `TeamSearch`(입력이 고른 팀 이름 그대로면 단어 검색으로 바꾸지 않음), `useTeamsParams`(team 2,147,483,647 초과는 요청 없이 조회 조건 안내) | 렌 선택 후 Enter가 4팀 단어 검색으로 바뀌고 기록이 늘던 문제(중요), 범위 밖 팀 번호 URL이 조회 실패로 보이던 문제(경미) |
| 테스트 | `tests/test_teams_db.py`(고른 팀만), `tests/test_teams_rules.py`(team 422 3건), `frontend/tests/teams.test.mjs`(고른 팀 조건·32비트 상한) | 새 조건과 경계값 |
| 문서 | `docs/guide.md`(첫 단락·§2·§3·§6.4·D-07-6·§11), `docs/file-feature-map.md`, 이 문서 | 사용자 요청으로 세 문서 최신화 |

검수: 백엔드 ruff·pytest 306(DB 실연동 팀 6·요청 규칙 13 별도 통과), 프런트 lint·`tsc --noEmit`·npm test 52·Turbopack 빌드, `git diff --check`. 브라우저 1440·375·320에서 맨시티·레알 마드리드·Bayern Munich·토트넘 자동완성과 선택, '맨체스터'·'레알'·'렌' 후보 여러 개, 결과 없는 검색어(드롭다운 안내 → Enter → 빈 상태 → 검색어 지우기), X 해제, 리그 전환·해제, 관심 팀 5팀 후 6번째 비활성·안내와 메인 반영, 키보드만으로 검색 → 후보 선택 → 카드 진입(`/teams/50`), 뒤로 가기 복원, `team=48`·`team=abc`·`team=2147483648` 처리, 메인·지난 경기의 공통 검색 라벨 유지, 콘솔 오류 0. 미실행: 실제 브라우저 설정의 저장소 차단(스크립트 모의), 실기기 터치·스크린리더(전체 검수 단계).

## 2026-11-17 (화) — 06 리그 순위 개선

브랜치 `feat/06-standings`(최신 `dev` 5b28189 병합 후 작업)에 커밋·push 후 `dev` 병합. Codex 교차 검증 5회(1차 사용자 결정 반영 후 요청 → 2차 차단 1·결함 3·개선 2 → 3차 결함 3 → 4차 결함 1 → 최종 통과, 최종 단계의 경기 상세 기록 보존 결함은 Codex가 보완·검증). 기획 문서 v1.11 LEAG-002·Figma '01 · 디자인' 기준, 마이그레이션 없음.

| 영역 | 변경 파일·함수 | 이유 |
| --- | --- | --- |
| 화면 구조 | `app/standings/page.tsx`, `features/standings/StandingsSection.tsx`, `ChipRow.tsx`(새), `PlayerRankings.tsx` | 보이는 제목·소개 삭제(sr-only H1), 시즌 선택·대회 칩(5대 리그, UEFA 3개)·단계 칩·본문을 흰색 영역 하나로. 5대 리그는 팀 순위(PC 좌)·선수 순위(우, 모바일 세로). 칩 줄 가로 스크롤·선택 칩 자동 표시 |
| URL 상태 | `useStandingsParams.ts`, `model.ts`(`UEFA`·`STAGES`·`competitionLabel`) | 대회·시즌·단계 복원과 뒤로 가기, UEFA는 리그 페이즈 기본, 대회 변경 시 단계 삭제 |
| 팀 순위 표 | `StandingsTable.tsx`(격자 표·`TeamCell`), `model.ts`(`leagueZone`), 삭제 `formResults`·`zoneLabel`·백엔드 `relegation_zone` | 강등권·승강 PO권을 description 문구 대신 순위 위치로 판단(EPL·라리가·세리에 A 18~20, 분데스리가·리그1 17·18 강등권·16 승강 PO권), 시즌 종료 후 결과 표기 |
| 최근 5경기 | 백엔드 `services/standings.py`(`recent_matches`), 프런트 `RecentForm.tsx`(새) | 저장된 그 대회·시즌 종료 경기 최근 5개(오래된 순·'최신'), 날짜·홈 스코어 원정 미리보기(공급사 호출 없음), 고정 헤더·표 가로 스크롤 밖에서 닫힘, 미리보기 위 호버 유지 |
| UEFA 리그 페이즈 | 백엔드 `STANDINGS_IDS`·`table_fixtures`·`check_standings`(그룹 1개·36팀·1~36위)·`sync/standings.py`, 프런트 `LeaguePhaseTable.tsx`(새, `phaseBands`) | UEFA 3개 대회 × 2시즌 순위 수집(실제 API 6회), 1~8 직행·9~24 플레이오프·25~36 탈락 구간, '현재 순위 기준'/확정 결과, 최근 5경기는 리그 페이즈만 |
| 완료 판정 | `services/standings.py`(`table_complete`) | 순위표 팀끼리 서로 다른 대진으로 판정(리그 n×(n−1), UEFA 144/108·팀별 8/6) — 뒤 라운드 미적재·승강 PO·취소 중복·같은 팀 행이 빠진 경기를 메우지 못하게 |
| 토너먼트 | 백엔드 `services/knockouts.py`(새)·`GET /knockouts`, 프런트 `KnockoutStage.tsx`(새, `legRows`) | 플레이오프~결승 대진을 저장 경기로 구성(합산·승부차기·진출/우승), 'A–B전 승자'·'상대 미정'은 저장 경기로 확정될 때만, 추첨 경로 추정 없음, 한 경기만 저장되면 차전 단정 안 함 |
| 경기 적재 보완 | `services/fixtures.py`(`upsert_fixture_items`), `services/match_detail.py`(`store_fixture_records`), `sync/fixtures.py` | 홈·원정이 같은 팀인 경기 응답 거부, 받아들인 경기만 이벤트·상세 기록 저장, 라이브 거부 경기 ID 재조회·최종 기록 보존(Codex 보완) |
| API 타입 | `lib/api/schema.d.ts`(재생성)·`types.ts`·`query-keys.ts`, `features/standings/queries.ts` | `TableRow`·`RecentMatch`·`Knockout*`, `knockoutsQuery` |
| 테스트 | `tests/test_standings.py`, `test_standings_db.py`, `test_schedule_db.py`, `frontend/tests/standings.test.mjs` | UEFA 범위·36팀·그룹, 완료 판정 재현(롤백), 토너먼트·차전, 경기 거부·기록 보존, URL·구간·차전 표기 |

검수: ruff 통과, pytest 303 통과·85 건너뜀, DB 포함 388 통과, Alembic 변경 없음, `git diff --check` 통과, 프런트 lint·tsc·테스트 51 통과, build 2회차 exit 0(1회차는 Next.js 16.4.3 보안 공지 SecurityFatalError — 보안 패치 업그레이드는 별도 결정 필요). 브라우저 1920·375·320에서 5대 리그·UEFA 리그 페이즈·토너먼트, 메인 간소 순위·팀 상세·지난 경기 회귀 확인. 실제 데이터 8개 표 2025 완료·2026 진행 중. 실제 API 호출 6회(UEFA 순위 첫 적재), 이후 보완·검증은 0회.

## 2026-11-16 (월) — 05 지난 경기 개선

브랜치 `feat/05-results`(최신 `dev` 29b5aa7 병합 후 작업)에 커밋·push 후 `dev` 병합. Codex 교차 검증 통과(지적 없음). 기능 명세서 v1.10 HIST-001 규칙 4·HIST-002, PRD v1.10 13장, 유저 플로우 v1.9 UF-09, Figma `61:883`·`53:995`·`65:1616` 기준.

| 영역 | 변경 파일·함수 | 이유 |
| --- | --- | --- |
| 상단 | `app/results/page.tsx` | 최상단 소개 문구 제거, 보이는 제목 대신 sr-only H1 — 카드가 헤더 아래 PC 32px·모바일 24px에서 시작 |
| 시즌 표기 | `components/common/SeasonSelect.tsx`(`seasonText`, 옛 `optionLabel` 삭제) | 트리거·옵션 '2025-26 시즌'. 리그 순위 Figma(`53:1353`·`61:1653`)도 같은 형식이라 표기 옵션 없이 공통 변경(리그 순위 모바일 전체 폭 유지) |
| 팀 검색 | `features/results/ResultsSection.tsx`, `components/common/TeamSearch.tsx`(`placeholder` 옵션 삭제) | 메인 일정과 같은 묶음(라벨·보조 문구·48px 입력·돋보기·44px X), 보조 문구만 선택 시즌 안내, 검색 범위는 선택 시즌 유지. 시즌 버튼 모바일 175px·sm 220px, 초기화 76px(Figma) |
| 관심 팀 버튼 | `features/favorites/FavoriteTeamButtons.tsx`(새), `features/schedule/ScheduleSection.tsx` | Figma 61:883의 '★ 관심 팀' 줄을 메인과 같은 컴포넌트로(메인 출력 동일), 지난 경기의 칩 모양 줄 삭제 |
| 테스트 | `tests/results.test.mjs` | 시즌 옵션 표기('현재/이전 시즌' 없음), 공통 관심 팀 버튼 줄 |

검수: 브라우저 1920·375·320에서 Figma 좌표 대조(PC 시즌 220×44·라벨 141·입력 195/48, 모바일 시즌 175·초기화 76), 메인·지난 경기 검색 묶음 계산 스타일 동일, 2025-26 '레알'(5팀)·'Man City'·'번리'(42경기·팀 상세 미제공)·'Aberdeen', 2026-27 'Aberdeen' 일치 없음·'번리' EFL컵 2경기, 시즌 키보드 조작·전환 시 팀·대회 유지와 첫 페이지, 리그 순위 표기·전환, 초기화·URL·뒤로 가기·상세 이동·미지원 시즌, 콘솔 오류 없음. 백엔드 ruff·pytest 307(DB 포함 377)·alembic check, 프런트 tsc·lint·테스트 47·build. 외부 API 1회(과거 경기 상세 첫 열람 보충, Codex 검증 0회).

## 2026-11-11 (수) — 04 경기 상세 개선

브랜치 `feat/04-match-detail`(최신 `dev` d5ee55a 병합 후 작업)에 커밋·push 후 `dev` 병합. Codex 교차 검증 2회(1차 수정 필요 4건(중요 2·경미 2) → 보완 후 통과). 기획 문서(PRD·기능 명세서 v1.10)의 선수명 영문 유지·평가 정책 확정 문구는 Codex가 개정.

| 영역 | 변경 파일·함수 | 이유 |
| --- | --- | --- |
| 경기 평가(백엔드) | `migrations/versions/20261111_0015_text_reviews.py`(새), `models/review.py`(`REVIEW_BODY_SPACE_CLASS`), `services/reviews.py`(`review_open`), `schemas/match_detail.py`, `api/routes/matches.py` | 별점·평균 제거, 텍스트 평가·유효 건수. 진행 중~일반 종료 공개 조회·작성 가능 서버 판정(02 쓰기 API 재사용). 사용자 지시로 추천안 확정: SUSP 닫힘·INT 열림·AWD/WO 불가. 공백만 본문은 Python `str.isspace()` 기준으로 DB에서 거부(Codex 1차) |
| 기록 조회(백엔드) | `services/match_detail.py`(`detail_fetch_due`·`_empty_status`·`_name`) | 예정·연기 라인업 반복 조회 삭제(MAT-004 규칙 4), 선수·감독 이름 HTML 엔티티 해제(`O&apos;Brien` → `O'Brien`) |
| 상단·배치 | `features/match/Scoreboard.tsx`, `MatchDetail.tsx`, `model.ts`(`areasOf`) | 로고+팀명 한 링크(`detailAvailable`만), 종료 PC 기록 좌·평가 우 384px, 진행 중 평가 아래 640px, 모바일 세로(Figma 52:151·161:4161) |
| 경기 기록 | `MatchRecords.tsx`, `icons.tsx`(새), `model.ts`(`eventKind`·`eventText`), `queries.ts` | 타임라인 아이콘 5종+텍스트·반복 문구 삭제, '경기 기록' 헤더·진행 중 '마지막 갱신', 선수 평점 팀별 카드(Figma 94:4418), 기록 재조회를 경기 정보 갱신 한 경로로(종료 전환 1회, Codex 1차) |
| 예정 | `HeadToHeadSection.tsx`, `model.ts`(`formPreview`) | 상대 전적 812·최근 5경기 444 좌우/모바일 세로, 배지 31px, 호버·포커스·탭 미리보기 '홈팀 스코어 원정팀'(미리보기 위 호버 유지, Codex 1차), 라인업 영역 없음 |
| 경기 평가(화면) | `ReviewSection.tsx`, `ReviewGuidance.tsx`, `StatusNotice.tsx`, 삭제 `public/icons/thumbs.svg`·`Icon`의 thumbs | '경기 평가'·건수, 벡터 엄지·주의사항 아이콘, 평점·후기 문구 정리 |
| 테스트 | `tests/test_review_window.py`(새), `test_match_detail.py`, `test_review_regressions.py`, `test_top5_db.py`, `frontend/tests/match-regressions.test.mjs` | 상태별 판정·공백 기준·엔티티·조회 시점·화면 규칙 회귀 |

- **선수 한글명:** Wikidata 표본 비교(3팀 96명 중 약 60%)와 중계사 라인업 매칭(경기 라인업 팀+등번호 95.1% 일치)을 검토했으나, 혼재·화면 간 불일치·오표기 위험·운영 비용으로 사용자 결정에 따라 영문 유지. 중간에 만든 한글명 테이블·시드·작업은 커밋 전 삭제.
- **실제 실행 검수:** 1920·1024·375·320에서 종료(1379344 골 취소·1557458 퇴장·1557455 엔티티), 예정(1557474), 행정 종료(1388000), 취소(1449968) 확인. 진행 중↔종료는 같은 경기 ID에서 경기 정보 응답 상태만 바꿔 재현(정보 1회당 기록 1회, 종료 전환 1회). 실제 진행 경기 검수는 사용자가 직접 진행 예정.
- **검사:** 백엔드 ruff·pytest 306(DB 포함 376)·0015 왕복·alembic check, 프런트 lint·tsc·npm test 46·build.
- **외부 호출:** API-Football 0회, Wikidata 3회(한글명 비교 표본).

## 2026-11-10 (화) — 03 경기 일정 비회원 개선

브랜치 `feat/03-schedule`(최신 `dev` 병합 후 작업)에 커밋·push 후 `dev` 병합. Codex 교차 검증 3회(1차 수정 필요 5·문서 1 → 2차 미충족 2 → 3차 통과, 3차에서 Codex가 날짜 막대 폭 200px 경계 조건 1줄 수정).

| 영역 | 변경 파일·함수 | 이유 |
| --- | --- | --- |
| 메인 배치 | `app/page.tsx`(sr-only H1, 일정·관심 팀 / 뉴스·순위 두 구간), `components/layout/StickyPanel.tsx`(새) | 소개 제거, PC 우측 패널이 자기 구간에서만 고정(헤더 아래 12px, 가용 높이 520px 이상이고 패널이 들어갈 때만 — Figma 308:4617), 모바일 순서 일정→관심 팀→뉴스→순위 |
| 날짜 막대 | `features/schedule/DateBar.tsx` | 전날(요일)·오늘부터, 양끝 화살표, 모바일 52px·막대 1/5 폭(320에서도 5일), 상태는 요일 자리(좁으면 '없음·미확인·일부'), 팀 보기 해제 시 이전 위치 복원 |
| 대회 선택 | `components/common/CompetitionFilter.tsx`, `components/ui/Dialog.tsx`(`closeButton`·`scrollArea`) | 상단 X 없이 하단 취소·선택 적용, 딤 포인터, 목록만 스크롤 |
| 일정 화면 | `features/schedule/ScheduleSection.tsx`, `useScheduleParams.ts`(`withTeam`·`withoutTeam`·`nearestMatchDate`), `components/common/TeamSearch.tsx` | Figma 간격(12·6·8·16px), 48px 검색 입력·SVG 돋보기·30px X, 수집 지연 안내, 미확인 날짜를 건너뛴 경기일 이동, 팀 선택 시 전체 대회·해제 시 날짜·막대·대회 복원(개정 기획 SCH-003·004·006), 초기화 순서(`pendingReset`) |
| 경기 카드 | `components/common/MatchCard.tsx`, `MatchStatusBadge.tsx`, `lib/format/match.ts`(`awaitingStatus`), `lib/hooks/useNow.ts`(새), `features/favorites/FavoriteStar.tsx`(새) | 등록 가능한 팀 옆 별표(이동 없이 등록·해제), 본문은 경기 상세, 스코어 카드 중앙, 킥오프 후 '상태 확인 중'·'—' |
| 관심 팀 | `features/favorites/FavoriteSchedule.tsx`, `FavoriteToggle.tsx`(`FAVORITE_REFUSALS`) | Figma Guest Favorites 다섯 상태, 팀 추가는 팀 일정 검색과 같은 UI(사용자 결정), 일정의 관심 팀 버튼은 선택 효과 없음 |
| 간소 순위·칩 | `features/standings/MainStandings.tsx`·`model.ts`, `components/ui/chip.tsx`(`ChipLabel`), 칩 사용처 `MainNews`·`ResultsSection`·`TeamsSection` | 'Bundesliga', 경기·승무패·승점, 마우스 끌기·휠 가로 이동, 칩 선택 시 폭 고정 |
| 일정 응답·이름 | 백엔드 `services/fixtures.py`(`SyncState` 확인 시각·범위·`delayed`), `schemas/schedule.py`, `api/routes/schedule.py`, `seed/team_aliases.json`(92팀) | 수집 지연 표시, 하위 리그 프로 구단 한국어 이름(아마추어는 원문 — 사용자 결정 A안) |

- **수집·예약:** `backend/.env`에 `SCHEDULER_ENABLED=true`(커밋 대상 아님). 14개 작업 예약, 실측 `news` 15:59·`fixtures` 16:04·`standings` 16:09(2026 순위 11/6 → 11/10 갱신), 수동 `fixtures` 1회, 별칭 시드 적용.
- **실제 실행 검수:** 1920·375·320·낮은 PC(1920×570·760)에서 항목 1~11과 사용자 확인 후 보완(설명 문구, 관심 팀 UI, 카드 정렬, 순위 칩·끌기, 칩 폭, 액티브 효과 제거, 패널 고정 조건, 팀 선택 규칙). DB 값은 확인용으로 잠시 바꾼 뒤 모두 원복.
- **검사:** 백엔드 ruff·pytest 286(DB 포함 356)·alembic check, 프런트 lint·tsc·npm test 39·build·`git diff --check`.
- **외부 호출:** API-Football 수동 14회 + 스케줄러 자동 실행분, 네이버는 정시 뉴스 작업만. Codex 검증 0회.
- **미실행:** 실제 진행 경기 실시간 갱신(첫 킥오프 11/11 03:00 KST), 월요일 TOP 5 자동 실행(11/16 00:00·00:05 KST).

## 2026-11-10 (화) — 01 비회원 개선(헤더 로고·TOP 5·푸터)

`dev` 작업 트리에서 작업(중간에 만든 별도 폴더 `apps-01`은 사용자 요청으로 변경을 `apps`로 옮긴 뒤 삭제). Codex 교차 검증 3회(1차 결함 4·개선 2·확인 1 → 2차 N1·N2·N3 → 3차 N4, N4는 Codex가 수정) 후 기존 `feat/01-header-footer`에 커밋·push, `dev`에 병합.

| 영역 | 변경 파일·함수 | 이유 |
| --- | --- | --- |
| 헤더 로고 | `frontend/src/components/common/Logo.tsx`(PC 46px·모바일 40px, `logo-header.svg`만), `SiteHeader.tsx`, 삭제 `public/brand/logo-footer.svg`·`logo-mobile.svg` | Figma `49:58`·`49:571`: KICKTAB 글자를 키우고 메뉴와 겹치지 않게 |
| TOP 5 띠 | `frontend/src/features/top5/Top5Strip.tsx`(`Lineup` 반복 사본으로 끊김 없는 순환, 띠 배치), `model.ts`(`weekLabel`·`PREPARING`·`lineupItems`·`periodText`), `src/app/globals.css`(띠·패널·시트 블록, 헤더 높이 144/154px) | Figma `159:923`: PC 56px·모바일 84px, 'AI 선정' 배지 복원, 1~5위 순환(24px/s), 호버·포커스·열림 정지, 모션 감소 정적 표시, 지난주 유지 시 실제 지난주 기간과 준비 상태 |
| TOP 5 펼침 | `Top5List.tsx`(PC·모바일 행 재배치, 안내 상자, 목록 아래 한 줄 안내), `Top5Strip.tsx`(`PanelHeading`, PC 패널 150ms 펼침/접힘·접힘 즉시 `inert`, 시트 `kt-top5-sheet`) | Figma `128:4251`·`159:924`: 기간·선정 시각·닫기 머리글, 중복 제목·배지·긴 안내 제거, 낮은 창은 목록만 스크롤 |
| 공통 | `src/components/layout/HeaderHeight.tsx`(새 파일, 실제 헤더 높이 → `--kt-header-height`), `src/components/ui/Dialog.tsx`(닫힘 전환 동안 내용 유지·`inert`, 늦은 close 이벤트 가드 — Codex 수정 포함) | 320px 지난주 상태에서 헤더 171px과 기준 154px 불일치, 시트 닫힘 중 목록 사라짐, 빠른 재열기 시 스크롤 잠금 해제 |
| 푸터 | `SiteFooter.tsx`, `src/app/layout.tsx`, `FeedbackButton.tsx`, 삭제 `MobileBottomBar.tsx` | Figma `304:3823`: 로고 제거·재배치, 모바일 고정 의견 버튼 제거(사용자 결정: Figma 최종) |
| TOP 5 백엔드 | `backend/app/services/top5_selection.py`(`_missed_week`, `recovery_due`, `reconcile_attempts`), `tests/test_top5_db.py`(실행 누락 지연→교체, 주 경계 테스트) | 00:00·00:05 기록이 없는 주가 지연 안내 대신 지난주 목록으로 남던 결함 |
| 정리 | `lib/format/kst.ts`(`formatPeriod` 삭제), `frontend/tests/top5.test.mjs`(새 파일) | 쓰지 않게 된 코드 삭제, 띠 문구·상태 테스트 |

- **실제 확인:** 11/9 주(실행 기록 없음)가 지난주 목록으로 표시되는 것을 확인하고 수정 후 `top5_reconcile` 1회 → 지연 공개(버전 437)·TOP 5 디스코드 알림 1회. `fixtures` 1회(API-Football 14회) 후 `top5` 수동 복구 1회 → 주 모델 504, 하위 모델 `gemini-3.5-flash-lite` 응답(Gemini 2회·API-Football 293회), 새 공개본 438(list)로 교체.
- **예약 시각(시계 주입):** `top5_weekly` 11/16 00:00 KST, `top5_retry` 11/16 00:05 KST(유예 60초). 실제 월요일 실행은 미실행 — 11/16 00:00 이후 확인 필요.
- **화면 검수:** 1920·375·320·1920×560에서 로고·띠·패널·시트·푸터, 다른 화면(지난 경기·리그 순위·팀 탐색·팀 상세·경기 상세) 회귀 없음. 모션 감소·빠른 Tab·시트 닫힘·헤더 높이는 헤드리스 Edge로 확인.
- **검사:** 백엔드 ruff·pytest 285 통과·`KICKTAB_DB_TESTS=1` 355 통과·alembic check, 프런트 lint·`npm test` 36·tsc·build 통과.
- **띠 개정(병합 후, 같은 날):** 사용자가 Figma `159:923`의 띠를 바꿔 반영. PC 56→50px, 모바일 84→68px(첫째 줄 배지·제목·기간 한 줄, 둘째 줄 대진과 오른쪽 끝 화살표, 지난주 유지 시 '이번 주 결과 준비 중'은 모바일 둘째 줄 대진 앞), PC 지연 안내 12px. 헤더 전체 높이는 PC·모바일 모두 138px(`globals.css`의 데스크톱 별도 값 삭제). 변경: `Top5Strip.tsx`(`STRIP`·`FIRST_ROW`·`SECOND_ROW`, `WeekLine` 삭제), `globals.css`, `SiteHeader.tsx`·`HeaderHeight.tsx` 주석. 1440·375·320px 확인(320px 지난주 상태는 기간 줄바꿈으로 158px, `HeaderHeight`가 따라감), lint·tsc·`npm test` 37·build 통과. 03 작업 중 수정했으나 01 범위라 `feat/01-header-footer`에 따로 커밋·push 후 `dev`에 병합.
- **사용자 결정:** 이미지 출처는 확인 중이라 더미 유지, '실제 인기 순위 아님' 안내 불필요, 모바일 고정 의견 버튼 제거, UI는 Figma 최종, 이후 작업은 `apps` 폴더에서.

## 2026-11-07 (토) — 08 팀 상세

브랜치 `feat/08-team-detail`(최신 `dev`의 작업 트리에서 분기)에 커밋·push 후 `dev`에 병합. Codex 교차 검증 통과(1차 차단 1·중요 3·경미 5, 2차 중요 2·경미 1, 3차 중요 1·경미 2, 4차 후속 N7·N8 보완). 05~07과 같이 `dev` 작업 트리에서 작업한 뒤 검증 완료 후 브랜치를 만들었다. 이로써 비회원 기준 서비스 전체(메인·경기 상세·지난 경기·리그 순위·팀 탐색·팀 상세)가 이어진다(로그인·회원가입만 02 전까지 404). 마이그레이션 `0012_team_detail`·`0013_transfer_counterpart_key`·`0014_transfer_identity_indexes`.

| 영역 | 변경 파일·함수 | 이유 |
| --- | --- | --- |
| 시작 전 처리 | `tests/test_schedule_db.py`(`test_availability_keeps_uncovered_dates_separate_from_stored_games`) | 05가 시즌 전체를 적재해 '오늘+21일에 경기 없음' 가정이 깨짐 → 저장된 마지막 경기 날짜+30일을 써서 실제 데이터·날짜와 무관하게(제품 코드 변경 없음) |
| 수집 | `sync/team_detail.py`(`team_details` 매일 15:00 KST — 감독·선수단·이번 시즌 팀 기록, 지난 시즌 기록 1회, 국적 1회 보완 / `transfers` 매일 00:00 KST), `services/team_detail.py`(파싱 `pick_coach`·`parse_squad`·`parse_statistics`·`parse_transfers`·`parse_profile_nationality`, 완전성 `check_squad`·`check_statistics`·`check_transfers`, 저장 `save_*`, 일정 `is_due`(KST 하루 1회)·`transfer_seasons`·`last_refresh_day`·`final_refresh_done`), `models/team_detail.py`, `sync/jobs.py` | TEAM-001·002·005·006: 이적은 날짜로 시즌·반기 분류, 미래 날짜 제외, 7/1 00:00 갱신까지 받은 뒤 고정(실패 시 성공할 때까지 재시도), 하루 차이 반복은 상대 팀 ID가 같고 반대 방향 이동이 없을 때만 1건. 잘린 응답은 저장값을 지우지 않고 실패 기록 |
| 공통 변경 | `services/reference.py`(`upsert_teams` 경기장 저장 — 응답에 있는 필드만, `team_detail_lookup` 팀 목록이 수집된 리그 소속만 `true`), `sync/reference.py`(venue 전달), `models/reference.py`(`teams.venue_*`), `models/standings.py`(`players.profile_checked_at`) | 경기장은 추가 호출 없이 03 `reference` 응답에서. 링크와 팀 상세 직접 URL 판정 일치(Codex 1차 지적 2) |
| API | `api/routes/teams.py`(`GET /teams/{id}`·`/fixtures`·`/squad`·`/season-stats`·`/transfers`), `schemas/team_detail.py`, `api/routes/schedule.py`·`services/news.py`(`GET /news?team=`) | 영역별 조회, 없는 팀 404·허용 밖 404 `TEAM_DETAIL_UNAVAILABLE`·소속 미확인 503 `MEMBERSHIP_UNKNOWN`, 최근 흐름은 04 `ensure_form` 요청 시 보충, 팀 뉴스는 연결 기사 최신 48개 |
| 화면 | `app/teams/[id]/page.tsx`, `features/team-detail/`(`TeamDetail`·`TeamMatches`·`SquadTable`·`SeasonRecords`·`TeamNews`·`model.ts`·`queries.ts`), `lib/api`(타입·쿼리 키·생성 타입) | Figma 52:1254/52:1866·58:356·58:738·58:924·57:836: 기본 정보·관심 팀, 경기(예정 3·최근 5·'경기 전체 보기' → `/results?team=`), 선수 표(정렬·10명 후 더 보기·'—'), 시즌 기록·이적(이번/지난 시즌), 팀 뉴스, 모바일 4탭, 영역별 `DataState` |
| 마이그레이션 | `0012_team_detail`(테이블 5개·RLS·컬럼 추가), `0013_transfer_counterpart_key`, `0014_transfer_identity_indexes`(상대 팀 ID 유무별 이적 고유 인덱스) | Codex 3차 N4·4차 N7: 파서와 DB의 이적 식별 기준 통일 |
| 테스트 | `tests/test_team_detail.py`(규칙 단위), `tests/test_team_detail_db.py`(DB 실연동·롤백), `frontend/tests/team-detail.test.mjs` | 감독 선택·반기 분류·완전성·중복 규칙·KST 하루 1회·7/1 경계, 접근 판정·링크 일치·잘린 응답·실패 기록·경기장·팀 뉴스, 정렬·누락 표시·문구 |
| 문서 | `docs/guide.md`(08 상태·§2·§6.3~§6.5·§3.1 02/09 인수인계·00 확인 요청·§10.3 D-08), `docs/file-feature-map.md`, 이 문서 | 사용자 요청으로 세 문서 최신화. 기획 문서 3종(기능 명세서 v1.7·PRD v1.7·유저 플로우 v1.6)은 사용자 결정 D-08-9(A)에 따라 Codex가 갱신 |

데이터(96팀): 경기장 96, 현직 감독 95(1팀 미제공), 선수단 2,946명(등번호 누락 0.6%·국적 누락 10.1%·이번 시즌 리그 기록 없음 12.3%), 팀 시즌 기록 이번 96·지난 83(승격 13팀 제외), 이적 2025-26 7,159·2026-27 4,446건(중복 0). 실제 API-Football 호출: 수집 실행 기록 1,382회(`reference` 22·`team_details` 783·`transfers` 577 — 규칙 보완에 따른 이적 재적재 포함) + 팀 최근 흐름 요청 시 보충 4회. 검수 중 소속 미확인·뉴스 갱신 실패 재현을 위해 EPL `teams_synced_at`·`news` 실패 기록을 잠시 바꿨다가 복구했다.

검수: 백엔드 ruff·pytest 285(DB 실연동 포함 353)·alembic upgrade·downgrade·check(공유 개발 DB `0014` head), 프런트 lint·tsc·테스트 33개·Turbopack 빌드. 브라우저 1280·375·320에서 5대 리그 각 1팀+승격 팀 6개 영역, 선수 표 정렬·더 보기·이적 선수 줄 분리, 시즌 기록·이적 전환·승격 팀 빈 상태·후반기 시작 전 안내, 경기 상세·지난 경기 이동, 팀 뉴스 원문·뉴스 없음·갱신 실패, 관심 팀 등록 → 메인 반영 → 해제·6번째 비활성·저장소 차단(스크립트 모의), 직접 URL 404·503, 04~07 진입 링크, 모바일 4탭, 비회원 전체 흐름 링크(404는 `/login`·`/signup`뿐), 콘솔 오류 0 확인. 미실행: 실제 00:00·15:00 정시 실행과 7/1 고정 시점 경과(시계 대신 테스트로 확인), 실기기 터치·스크린리더(전체 검수 단계).

## 2026-11-06 (금) — 07 팀 탐색

브랜치 `feat/07-team-browse`(최신 `dev`의 작업 트리에서 분기)에 커밋·push 후 `dev`에 병합. Codex 교차 검증 3차 통과(1차 중요 1·경미 4, 2차 중요 1·경미 1 보완). 05·06과 같이 `dev` 작업 트리에서 작업한 뒤 검증 완료 후 브랜치를 만들었다. 외부 API 호출 0회(저장 데이터만), 마이그레이션 없음.

| 영역 | 변경 파일·함수 | 이유 |
| --- | --- | --- |
| 팀 목록 API | `services/team_browse.py`(`browse_teams`·`MembershipUnknown`·`PAGE_SIZE` 12), `api/routes/teams.py`(`GET /teams?league=&q=&page=`), `schemas/teams.py`(`BrowseTeam`·`TeamsMeta`), `api/router.py` | LEAG-003: 현재 시즌 5대 리그 소속(`team_competition_seasons`)만, 리그 필터·별칭 검색·페이지. 기존 `/teams/search`는 10개 상한·컵/UEFA 팀 포함·리그 정보 없음이라 목록에 쓸 수 없어 새 API. 팀 목록 미수집이면 빈 목록 대신 503 `MEMBERSHIP_UNKNOWN`, 정수이면서 5대 리그가 아니면 404·정수가 아니면 422 |
| 검색 공유 | `services/team_search.py`(`match_teams()` 분리) | 메인 검색과 팀 탐색이 같은 별칭 매칭·정렬을 쓰도록(모호한 별칭은 후보 팀 모두), 기존 `/teams/search` 동작 유지 |
| 화면 | `app/teams/page.tsx`, `features/teams/`(`TeamsSection`·`useTeamsParams`·`queries`), `lib/api`(타입·쿼리 키 `teams.list`·`MEMBERSHIP_UNKNOWN`·생성 타입) | Figma 52:624/52:949·57:766: 리그 칩, 이름 검색, 관심 팀 안내, 카드(엠블럼·이름·영문명 · 리그, 팀 상세 링크), 12개씩 페이지, URL 상태·복원, 잘못된 URL·페이지 초과 안내, 로딩·검색 결과 없음·조회 실패·재조회 실패 시 확인된 목록 유지 |
| 관심 팀 공통 | `favorites/FavoriteToggle.tsx`(5개 꽉 참 비활성, 거부 문구를 누른 직후 목록에 묶고 목록이 바뀌면 지움), `favorites/store.ts`(`latest()`) | FAV-002 6번째 거부(Figma fav-full), 다른 탭이 먼저 5개를 저장한 경우에도 안내 상자·버튼이 같은 목록을 보이도록 |
| 공통 UI | `components/ui/DataState.tsx`(`emptyAction`) | 검색 결과 없음의 '검색어 지우기'(Figma 57:766) |
| Codex 1차 보완 | `TeamsSection`(검색창 밖 URL 변경 시 연속 입력 종료·보낸 검색 순서 기억, 페이지 초과도 재조회 실패 안내 안에서), `FavoriteToggle`(같은 목록으로 돌아와도 거부 문구 재등장 없음), `routes/teams.py`(league 0·음수 404), 가이드 테스트 수 | 2페이지 → 검색 → 뒤로 → 새 검색이 2페이지 기록을 덮어씀(중요) 외 경미 4건 |
| Codex 2차 보완 | `TeamsSection`의 `SearchField`(검색창 밖 URL 변경이면 검색어가 같아도 입력값을 URL로 맞추고 보내지 않은 글자 버림, Tab·Enter는 마지막 글자를 같은 기록 단계에 반영 후 종료) | 반영 전 검색어가 뒤로 가기 후 다시 적용됨(중요), Tab·Enter로 끝낸 검색이 기록 두 단계로 나뉨(경미) |
| 테스트 | `tests/test_teams_db.py`(DB 실연동 5개), `tests/test_teams_rules.py`(요청 규칙 10건), `frontend/tests/teams.test.mjs`(6개) | 소속 96팀·리그 순서·페이지·리그별 소속·별칭·과거 시즌/UEFA 제외·소속 미확인 503, 상태 코드, URL 상태·꽉 참 마크업·다른 탭 선저장 알림·`emptyAction` |
| 문서 | `docs/guide.md`(07 상태·§2·§6.4·§3.1 08 인수인계·§10.3 D-07·로컬 서버 확인 방법), `docs/file-feature-map.md`, 이 문서 | 사용자 요청으로 세 문서 최신화 |

데이터: 현재 시즌 5대 리그 소속 96팀(EPL·라리가·세리에 A 20, 분데스리가·리그1 18), 12개씩 8페이지. 검수 중 소속 미확인·재조회 실패 확인을 위해 개발 DB의 리그1·EPL `teams_synced_at`을 잠시 비웠다가 원래 값으로 복구했다.

검수: 백엔드 ruff·pytest 260(DB 실연동 포함 314)·alembic check, 프런트 lint·tsc·테스트 26개·Turbopack 빌드, `git diff --check`. 브라우저 1280·375·320에서 첫 진입 96팀·마지막 페이지, 리그 필터 전환·해제, 한국어·영문·모호한 별칭·리그 결합·결과 없음, 관심 팀 등록 → 메인 관심 팀 일정·버튼 반영 → 해제, 6번째 거부·다른 탭 선저장, 새로고침 유지, 저장소 차단(스크립트 모의), 팀 클릭 `/teams/[id]` 404 안내, 메인 '관리'·'팀 탐색에서 등록', URL 공유·새로고침·뒤로/앞으로, 잘못된 리그·페이지 URL, 서버 중단·소속 미확인 조회 실패와 '다시 확인', 키보드 이동·포커스, 콘솔 오류 0 확인. 미실행: 실제 브라우저 설정의 저장소 차단, 실기기 터치·스크린리더(전체 검수 단계).

## 2026-11-06 (금) — 06 리그 순위

브랜치 `feat/06-standings`(최신 `dev`의 작업 트리에서 분기)에 커밋·push 후 `dev`에 병합. Codex 교차 검증 3차 통과(1차 지적 5건 — 차단 1·결함 1·개선 3, 2차 차단 1건 보완). 05와 같이 `dev` 작업 트리에서 작업한 뒤 검증 완료 후 브랜치를 만들었다.

| 영역 | 변경 파일·함수 | 이유 |
| --- | --- | --- |
| 순위·선수 데이터 | `models/standings.py`(`Standing`·`PlayerRanking`·`Player`·`PlayerSeasonStat`·`LeagueSync`), 마이그레이션 `0011_standings`(5개 테이블·CHECK·인덱스·RLS) | LEAG-001·002·004: 리그·시즌별 팀 순위(그룹 포함, 제공값·description 그대로), 선수 순위 4종(제공 순서, red만·yellowred 별도), 08이 재사용할 리그 전체 선수 시즌 기록, 리그·시즌·종류별 수집 상태 |
| 수집·저장 | `services/standings.py`(`parse_standings`·`parse_top_list`·`parse_player_pages`, `check_standings`·`save_standings`·`save_ranking`·`save_player_stats`, `due_leagues`·`is_matchday`), `sync/standings.py`(`standings`·`player_rankings`·`player_stats`), `sync/jobs.py` | 경기일 1시간·그 외 하루 1회·이전 시즌 보관, 응답이 완전할 때만 한 트랜잭션 교체(재실행 중복 없음), 실패·잘린 응답은 기존 행·성공 시각 유지 후 실패 기록(CMP-004) |
| 완전성 검증(Codex 보완) | 같은 파일: 팀 순위 순위 1..n·행 수 감소 금지·참가 팀 안·그 시즌 3경기 이상 팀 포함, 선수 순위 목록 축소 금지, 선수 페이지 마지막 외 20명·같은 선수 반복 거부·10% 초과 감소 금지 | 1차 차단(10/20팀·10/20명·빈 2페이지가 성공으로 덮어씀), 2차 차단(페이지 번호·크기는 정상이고 내용이 반복·밀린 응답). 2025 분데스리가·리그1 참가 팀 19(승강 PO 상대 포함)라 수 일치 대신 3경기 기준 |
| 선방 집계 | `aggregate_saves`·`read_saves` | 골키퍼 기록을 팀별 합산, null이 하나라도 있으면 제외하고 인원 안내, 공동 순위(1·1·3) |
| 순위 API | `api/routes/standings.py`(`GET /standings`·`/standings/summary`·`/player-rankings`), `schemas/standings.py`, `api/router.py` | 컵·UEFA·미지원 시즌 404, 미수집 503, 잘못된 유형 422, `refreshFailed`·`excluded`·`tied`, 현재 허용 집합 `TeamRef`(소속 미확인은 강등으로 단정하지 않음) |
| 화면 | `app/standings/page.tsx`, `features/standings/`(`StandingsSection`·`StandingsTable`·`PlayerRankings`·`MainStandings`·`useStandingsParams`·`queries`·`model`), `app/page.tsx`(메인 오른쪽 열), `components/ui/Tabs.tsx`(선택 없음·스크롤 막대 숨김), `components/ui/DataState.tsx`(`partialAction`), `lib/api`(타입 별칭·쿼리 키·생성 타입) | 시즌 드롭다운·리그 탭·팀 표·선수 순위, 시즌 전환 시 유형 유지·더 보기 초기화, URL 복원·뒤로 가기, 지난 시즌 '당시 강등/승강 PO'와 '팀 상세 미제공' 구분, 메인 간소 순위(EPL·LaLiga·Serie A·BUN·Ligue 1), 로딩·빈 결과·일부 미제공(0건 뒤 갱신 실패 포함)·조회 실패 구분, 소속 확인 실패 '다시 확인'(Figma 57:599) |
| 테스트 | `tests/test_standings.py`(17개, 매개변수 포함 26건), `tests/test_standings_db.py`(11개), `frontend/tests/standings.test.mjs`(8개) | 파싱·완전성·축소·페이지 반복·선방·수집 주기·잘못된 파라미터, 실제 DB 저장 경로(1·2차 재현 사례 포함), URL 상태·표기·상태 판정·칩·`DataState` |

데이터: 팀 순위 192행(시즌마다 EPL·라리가·세리에 A 20, 분데스리가·리그1 18 — 리그1 2025-26 33경기 팀 그대로), 선수 순위 40목록 × 20명, 선수 시즌 기록 6,603줄(2025 693·793·876·680·798, 2026 537·608·651·478·489), 선수 4,284명. 선방 2025는 API 검증 문서와 5개 리그 순위 인원·제외 인원(34·51·67·42·46)·순서가 모두 일치. 2025는 원본 파일 대신 API로 받았고(운영과 같은 경로) 원본과 팀 순위·선수 순위 4종·선방 집계 모두 일치. 재실행 후 중복 0. 실제 API-Football 호출 누적 436회(팀 순위 13·선수 순위 48·선수 페이지 375 — 갱신 실패 검수의 접속 불가 주소 요청 제외). Codex 검증 단계 호출 0회, DB 검증은 롤백·원복.

검수: 백엔드 ruff·pytest 250(DB 실연동 38 별도)·alembic 왕복·check, 프런트 lint·tsc·테스트 20개·Turbopack 빌드, `git diff --check`. 브라우저 1280·375·320에서 5대 리그 × 2시즌 표, 시즌 전환·유형 유지·더 보기 초기화, 4종 목록 제공 순서·red만, 선방 제외 인원·공동 순위, 강등·승강 PO·상세 미제공·링크, 메인 칩 전환·'전체 순위 보기', URL 복원·뒤로 가기·미지원 리그/시즌/유형, 갱신 실패 유지·조회 실패·소속 미확인 '다시 확인'·0건 뒤 갱신 실패, 콘솔 오류 0 확인.

## 2026-11-05 (목) — 05 지난 경기

브랜치 `feat/05-results`(최신 `dev`의 작업 트리에서 분기)에 커밋·push 후 `dev`에 병합. Codex 교차 검증 통과(1차 지적 4건·2차 표시 문제 1건 보완). 사용자 지시로 `dev` 작업 트리에서 작업한 뒤 검증 완료 후 브랜치를 만들었다.

| 영역 | 변경 파일·함수 | 이유 |
| --- | --- | --- |
| 시즌·적재 상태 | `config.py`(`first_season`), `services/reference.py`(`managed_seasons`), `sync/reference.py`(`_save_season` — 한 번의 `/leagues` 응답으로 관리 시즌 모두 저장, 적재한 시즌은 `no_data`로 바꾸지 않음), `models/reference.py`·마이그레이션 `0010_season_fixtures`(`season_fixtures_synced_at`·`season_fixtures_failed_at`), `models/fixture.py`(인덱스 `ix_fixtures_season_status_kickoff`) | 2025·2026 시즌 관리(CMP-003·004), 21일 작업과 분리된 시즌 전체 적재 상태 |
| 시즌 전체 적재 | `sync/fixtures.py`(`fixtures_season` — 대회·시즌당 1회, 현재 시즌 매일 13:00 KST, 과거 시즌 수동, 요청 실패·저장 오류(대회 단위 롤백)·일부 저장 모두 실패로 기록), `services/fixtures.py`(`upsert_fixtures` — 이름 없는 신규 팀 경기는 저장하지 않음), `sync/fixtures.py`(`fixtures` — 일부만 저장되면 실패 기록) | HIST-001·003, 재실행 중복 없음, 실패로 기존 데이터를 덮지 않음, 이름·값을 만들지 않음 |
| 지난 경기 API | `services/results.py`(`supported_seasons`·`season_coverage`·`finished_results`), `api/routes/results.py`(`GET /results`), `api/routes/schedule.py`(`GET /seasons`, `/competitions`의 `seasons`, `/teams/search?season=`, `require_supported_season`), `services/team_search.py`(시즌 범위), `schemas/schedule.py` | 시즌 전체 종료 경기(일반·행정 종료 구분)·대회 다중·팀·10개 단위, 미지원 시즌 404, 최초 미적재 503과 갱신 실패 구분 |
| 별칭 시드 | `seed/team_aliases.json`(2025-26 5대 리그 강등 15팀 한국어 이름·별칭, 모두 `searchOnly`) | 과거 팀 한국어 검색, 뉴스 분류 불변 |
| 화면 | `app/results/page.tsx`, `features/results/`(`ResultsSection`·`useResultsParams`·`queries`), `components/common/SeasonSelect.tsx`, `components/ui/Pagination.tsx`, `lib/hooks/useHydrated.ts`, `CompetitionFilter`(`season`), `TeamSearch`(`season`·`placeholder`), `ScheduleSection`·`app/page.tsx`(하이드레이션 대기) | `/results` 필터·URL·뒤로 가기, 후보 없음·결과 없음·조회 실패·미수집·미지원 시즌·잘못된 URL 조건·페이지 초과 구분, 상세 미제공 팀 표시, 04 하이드레이션 경합 정리 |
| 테스트 | `tests/test_results_db.py`(13개), `tests/test_schedule_sources.py`(OpenAPI), `frontend/tests/results.test.mjs`(6개) | 시즌·필터·행정 종료·페이지·과거 팀 검색·상태 코드·적재 실패·이름 없는 팀·URL 조건 |

데이터: 2025 시즌 14개 대회 4,128경기(API 검증 문서·원본 14개 파일과 ID·상태·스코어·팀·킥오프 차이 0), 2026 시즌 3,290경기, 재실행 후 중복 0. 실제 API-Football 호출 79회(reference 22, fixtures_season 14×3, fixtures 14, 경기 상세 보충 1). Codex 보완 단계 호출 0회, DB 검증은 롤백.

검수: 백엔드 ruff·pytest 224(DB 포함 262)·alembic check, 프런트 tsc·lint·테스트 12개·빌드, `git diff --check`. 브라우저 1280·375·320에서 시즌 전환·대회 적용/취소·팀 검색(한국어·영문·모호·강등 팀)·팀 해제·초기화·URL 복원·뒤로/앞으로·마지막 페이지·행정 종료·승부차기·'—'·상세 이동과 복귀·상태 구분·하이드레이션 오류 없음 확인.

## 2026-11-04 (수) — 00 TOP 5 하위 모델 대체·정책 파일 삭제 반영

담당: 00 전체 조율 채팅(사용자 지시). 사용자가 Codex가 만든 md 파일(`../docs/TOP5_POLICY_2026-11-01.md`·`SCHEDULE_UX_POLICY_2026-11-02.md`·`README.md`·`handoff/`, `../wireframe/`의 검수 md, `apps/docs/design-assets/`·`design-handoff-2026-11-03.md`)을 삭제했다. 정책 기준은 기획 문서(PRD·기능 명세서·유저 플로우)와 Figma다.

- `backend/app/services/top5_selection.py`: `gemini_generate()`가 주 모델(`gemini-3.8-flash`) 호출 오류 시 같은 시도 안에서 하위 모델(`gemini-3.5-flash-lite`)을 1회 호출한다(주 모델 몫 60%, 남은 시간 10초 미만이면 생략). 둘 다 실패하면 `AllModelsFailed`, 응답한 모델은 `top5_attempts.model`에 기록. `run_attempt()`가 두 모델 모두 실패한 시도마다 운영 알림을 보낸다(00:05 재시도 실패는 기존 지연 알림 1회).
- `backend/app/notifications/discord.py`: `Top5DelayNotice`에 `kind`(`delay`·`models_failed`)·`next_retry_at` 추가, '주 모델·하위 모델 모두 실패' 알림(다음 단계: 00:05 재시도 예정 또는 수동 복구 명령).
- `backend/app/config.py`: `top5_llm_fallback_model`(기본 `gemini-3.5-flash-lite`). `.env`·`.env.example`에 `TOP5_LLM_FALLBACK_MODEL` 추가.
- 코드 주석·문서 3개에서 삭제된 정책·인계 파일 링크를 기획 문서·Figma·코드 기준으로 바꿨다.
- 테스트: `tests/test_top5.py`(대체 호출·둘 다 실패·시간 부족·대체 끔·알림 내용), `tests/test_top5_db.py`(첫 시도 두 모델 실패 알림→재시도 실패 지연 알림 1회→수동 복구 실패 알림, 대체 모델 응답 게시·기록).

검수: 백엔드 ruff 통과, pytest 224 통과·25 건너뜀, DB 실연동 249 통과. 실제 Gemini 비공개 비교 1회(후보 136개, DB 쓰기 없음): 주 모델 503 → 하위 모델 응답·검증 통과(6.8초). 실제 디스코드 알림 발송은 하지 않았다(모의 테스트로 확인).

## 2026-11-04 — 04 후기 안내·TOP 5 선정 기준

`feat/04-match-detail`: 후기 제목 옆 44px `!` 팝오버로 안내를 옮겼다. 기존 안내 문구는 유지하고, 마우스 호버·클릭 고정·모바일 탭·키보드 열기와 닫기를 제공한다. TOP 5 프롬프트 `2026-11-04.1`은 국내 시청 관심, 단계·경쟁 맥락을 앞에 두고 초반 승점 차와 더비만으로 뽑는 경우를 줄인다. 이번 주 공개 결과나 재시도 상태를 갱신하지 않았다.

검수: 1920/320px 브라우저 팝오버 경계·키보드·닫기 후 포커스, 프런트 린트·타입·테스트 6개와 백엔드 롤백 테스트 242개. 기존 공개 주의 같은 후보 136개로 비공개 비교를 2회 시도했으나 Gemini 503으로 새 순위는 확인하지 못했다.

## 2026-11-04 — 03 경기 일정·뉴스·UEFA 팀명

`feat/03-schedule`: 21일 날짜와 가까운 경기 자동 이동, 단일 대회 체크 초안, 팀 검색 X와 기간별 대회, 경기 6개에서 한 번에 전체 보기, UEFA 한국어 팀명 199개, 뉴스 정시 갱신·최근 48개·주제 분류를 적용했다. 개발 DB에서 마이그레이션 왕복 및 일치 확인 후 팀명(0회)·경기(API-Football 14회)·뉴스(네이버 8회) 수집을 완료했다. 기존 상세 링크 허용 범위는 그대로다.

검수: 백엔드 롤백 테스트 242개 및 프런트 린트·타입·테스트 6개, 1920/320px 브라우저에서 6→8경기 전체 보기, FA컵 적용과 가까운 날짜 이동, 검색 중 경기 없는 대회 비활성, 복수 대회 적용과 X 복귀를 확인했다. 개발용 뉴스 단독 예약에 정시 작업 1개가 등록되는 것도 확인했다.

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
- PRD·기능 명세·유저 플로우·와이어프레임·개발 가이드를 최신화했다. 당시 TOP 5 정책 파일을 우선했다(파일은 2026-11-04 삭제, 현재 기준은 기획 문서). 아래 기존 7가지 상태·현재 주 pending 고정 반환은 실제 코드 이력이며 신규 정책 구현 완료를 뜻하지 않는다.
- 실제 앱·Figma·주간 작업·재시도·운영 알림은 이번 범위에서 실행/수정하지 않았다. 04 및 관련 UI의 후속 구현·통합 검증 대상이다.

## 2026-11-02 (월) — 일정 탐색 정책·와이어프레임 개정

- 사용자 승인에 따라 대회 직접 단일 선택·보조 다중 선택, 메인 팀 검색/관심 팀 선택 시 오늘 포함 14일 모아 보기로 확정했다. 검색 해제는 이전 날짜·막대 위치와 현재 대회 복귀, 전체 초기화는 오늘·전체·팀 없음이다.
- PRD·기능 명세·유저 플로우(그림 4 포함)·와이어프레임·개발 가이드를 반영했다. 당시 일정 UX 정책·검수 파일을 우선했다(파일은 2026-11-04 삭제, 현재 기준은 기획 문서).
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
- 당시 TOP 5 정책 파일(2026-11-04 삭제)을 개발 가이드 P-05·P-06·수집 주기·응답 계약 인계에 반영했다. 아래 10/31의 ‘항상 표시’·평점/평가 수 계약은 당시 구현 이력이다.

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
