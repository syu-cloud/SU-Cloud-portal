<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-09-05 | Updated: 2026-09-05 -->

# docs

## 목적
Notion 「SU-CLOUD」 에서 옮겨온 설계·구축·코드 해설 문서(00~06)와 레포에서 작성한 의사결정 문서(07). 읽는 순서, 문서와 코드의 차이, 정리 시 바꾼 것은 `README.md` 에 있다.

## 주요 파일
| 파일 | 설명 |
|------|------|
| `README.md` | 읽기 순서표, 문서↔코드 차이(`main` / `Phase_0.5_prod`), 정리 시 변경 사항 |
| `00-phase-0.5-roadmap.md` | Phase 0.5 작업 목차. Notion 링크만 있음 |
| `01-warpgate-dev-setup.md` | 개발계 Warpgate·nginx·SG·keypair 구축과 검증 절차 (2026-08-14 실측) |
| `02-provisioning-backend.md` | Slot/Vm 모델, 서비스 흐름, 워커, 실패 복구, DB-as-queue 근거, systemd 유닛 |
| `03-warpgate-backend.md` | wgclient 해설과 services·osclient·.env 의 Warpgate 수정 지점 |
| `04-warpgate-patch-files.md` | Warpgate 연동 4개 파일 원본 전문 (`Phase_0.5_prod` 시점) |
| `05-portal-app.md` | portal 웹 앱 구조 (서비스 레이어 분리 후) |
| `06-portal-app-legacy.md` | portal 웹 앱 구조 (서비스 레이어 분리 전) |
| `07-decision-90vm-two-sections.md` | 90대 2분반 운영 전환 현안·의사결정 항목. 살아 있는 문서 |

## 하위 디렉터리
| 디렉터리 | 역할 |
|----------|------|
| `images/provisioning/` | 02 문서 스크린샷 12장 (`NN-설명.png`) |
| `images/warpgate-setup/` | 01 문서 스크린샷 2장 |

## AI 에이전트 안내

### 이 디렉터리에서 작업할 때
- 00~06 은 원문 스냅샷이다. 코드가 바뀌었다고 본문을 고치지 말고, 차이는 `README.md` 「문서와 코드의 차이」 또는 07 에 기록한다.
- 코드 인용의 진실은 문서가 아니라 `git` 이다. 문서와 코드가 다르면 코드를 따른다.
- 비밀 정보(비밀번호·토큰)를 문서에 적지 않는다. 01 의 마스킹을 유지한다.
- 새 문서는 번호를 이어 붙이고 `README.md` 표에 추가한다. 이미지는 `images/<문서슬러그>/NN-설명.png` 로 넣고 본문에서 상대 경로로 참조한다.
- 07 은 결정이 내려지면 해당 항목에 결정 내용·일자·근거를 덧붙인다. 항목을 지우지 않는다.
- 각 문서 상단의 `> **출처**` 메타 블록은 유지한다.

### 테스트 요구사항
- 이미지 참조가 모두 실제 파일을 가리키는지 확인: `grep -ho '](images/[^)]*)' *.md` 로 뽑은 경로가 존재해야 한다.

## 의존성

### 내부
- 07 이 참조하는 코드: `provisioning/services.py`, `provisioning/models.py`, `osclient/vm.py`, `wgclient/__init__.py`, `provisioning/management/commands/`

<!-- MANUAL: 이 줄 아래에 수동으로 추가한 내용은 재생성 시 보존됨 -->
