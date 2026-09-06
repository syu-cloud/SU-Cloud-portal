<!-- Generated: 2026-09-05 | Updated: 2026-09-05 -->

# SU-Cloud-portal (su-portal)

## 목적
SU 클라우드 포털의 Django 5.2 백엔드. 고정 45개 슬롯 풀에서 학생 1명당 OpenStack VM 1대를 발급하고, 각 VM 을 Warpgate(배스천 / 웹 터미널)의 SSH target 으로 등록해 학생이 `student{n}` 계정으로 로그인할 수 있게 한다. 아직 실제 웹 UI 는 없다. 운영자는 Django admin 액션과 `manage.py` 명령으로 작업을 예약하고, 상주 프로세스인 `manage.py worker` 가 OpenStack / Warpgate 호출을 비동기로 수행한다.

배포 위치는 `/opt/su-portal`(개발계 호스트 `210.94.240.180`), `.venv` 사용. 환경 의존 값은 전부 `/opt/su-portal/.env` 에서 읽는다.

## 주요 파일
| 파일 | 설명 |
|------|------|
| `manage.py` | 표준 Django 진입점. `DJANGO_SETTINGS_MODULE=config.settings` 기본값 |
| `requirements.txt` | 고정 버전 의존성: Django 5.2.17, openstacksdk 4.18.0, psycopg 3, requests, python-dotenv |
| `.env.example` | `/opt/su-portal/.env` 템플릿: Django, OpenStack `OS_*`, 카탈로그 `SU_*`, DB `DB_*`, Warpgate `WG_*` |
| `.gitignore` | `.env`, `*.pem`, `.venv/`, `db.sqlite3`, `/staticfiles/` 제외 |
| `PATCH_NOTES.md` | 2026-08-20 env 설정 + Warpgate 통합 패치의 배포 노트. 수동 검증 시나리오와 미결 항목 포함 |
| `CLAUDE.md` | Claude Code 작업 규칙(한국어 사용, 검증 절차). 구조 설명은 이 문서와 하위 AGENTS.md 에 위임 |

## 하위 디렉터리
| 디렉터리 | 역할 |
|----------|------|
| `config/` | Django 프로젝트 settings, 루트 URLconf, WSGI/ASGI (`config/AGENTS.md` 참고) |
| `provisioning/` | 핵심 도메인: Slot/Vm 모델, reserve→provision→deprovision 서비스, admin, 워커 명령 (`provisioning/AGENTS.md` 참고) |
| `osclient/` | OpenStack SDK 연결 + 슬롯별 VM 생성/삭제/이름 규칙 헬퍼 (`osclient/AGENTS.md` 참고) |
| `wgclient/` | 멱등 `ensure_*` 패턴의 Warpgate Admin API 클라이언트 (`wgclient/AGENTS.md` 참고) |
| `portal/` | 웹 앱. 현재 "HELLO WORLD" index 뷰만 존재 (`portal/AGENTS.md` 참고) |
| `catalog/` | 빈 Django 앱 스캐폴드. `INSTALLED_APPS` 에 없음 (`catalog/AGENTS.md` 참고) |
| `probes/` | 개발계 클라우드·DB 를 직접 치는 임시 스크립트. 일부는 파괴적 (`probes/AGENTS.md` 참고) |
| `docs/` | Notion 에서 옮긴 설계·구축·코드 해설 문서(00~06)와 의사결정 문서(07). 읽기 순서와 코드와의 차이는 `docs/README.md` (`docs/AGENTS.md` 참고) |

## 아키텍처

### 요청 → 워커 흐름
```
admin 액션 / manage.py issue    ─▶ services.reserve()         ─▶ Slot FREE→TAKEN, Vm(PROVISIONING) 생성
admin 액션 / manage.py reclaim  ─▶ services.request_delete()  ─▶ Vm ACTIVE→DELETING
manage.py worker (3초 루프)     ─▶ services.claim()           ─▶ 미할당 또는 stale 한 PROVISIONING|DELETING 중 가장 오래된 행
    ├─ provision():   osclient.vm.create → Vm ACTIVE → wgclient.provision_seat (비밀번호 Student{n}!)
    └─ deprovision(): wgclient.deprovision_seat → osclient.vm.delete → Vm DELETED, Slot FREE
```

### Vm 상태 머신
`PROVISIONING → ACTIVE → DELETING → DELETED`, 그리고 `PROVISIONING → FAILED`. `Vm` 행은 append-only 이력이며 절대 삭제하지 않는다. `Slot` 행(n = 1..45)은 재사용된다.

### 슬롯 n 이름 규칙 (전역 공통, 반드시 일치 유지)
| 대상 | 값 | 정의 위치 |
|---|---|---|
| OpenStack 서버 이름 | `vm{n}` | `osclient.vm.name_for` |
| 리눅스 계정 + Warpgate 사용자 | `student{n}` | `osclient.vm.user_for` |
| Floating IP | `SU_FIP_PREFIX + str(100 + n)` | `osclient.vm.fip_for` |
| Warpgate role | `slot-{n}` | `wgclient.WarpgateClient.provision_seat` |
| Warpgate target | `vm{n}` | `wgclient.WarpgateClient.provision_seat` |
| 비밀번호 (phase 0.5) | `Student{n}!` | `provisioning.services.provision` |

## AI 에이전트 안내

### 이 디렉터리에서 작업할 때
- **설정은 env 전용.** `config/settings.py`, `osclient/__init__.py`, `wgclient/__init__.py` 가 각각 `load_dotenv("/opt/su-portal/.env")` 를 절대 경로로 호출하고 `os.environ[...]` 로 읽는다. 기본값을 추가하지 말 것. 변수가 없으면 부팅 시 죽는 게 의도된 동작이다.
- **`WG_PUBKEY` 는 필수인데 `.env.example` 에 없다.** `osclient/vm.py` 가 cloud-init 에 주입해 Warpgate 가 VM 에 SSH 접속할 수 있게 한다. 값은 `get_wg().own_keys()` 로 얻는다.
- **Slot 행은 어떤 마이그레이션도 시드하지 않는다.** 45개 `Slot` 행은 별도로 생성한다. 새 DB 에는 하나도 없다.
- **PostgreSQL 필수.** 슬롯·claim 잠금에 `select_for_update(skip_locked=True)` 를 쓰며 SQLite 는 지원하지 않는다.
- **비밀 정보 커밋 금지.** `.env`, `*.pem` 은 gitignore 됨. `PATCH_NOTES.md` 4단계처럼 push 전 `git log --all -- sdk-probe-key.pem` 이 비어 있는지 확인한다.
- **프로젝트 언어는 한국어.** 주석, docstring, admin 라벨, 명령 출력 모두 한국어. 유지할 것. 인라인 `[ADDED]` / `[CHANGED]` 마커는 2026-08-20 패치 지점 표시다.
- **멱등성이 설계 원칙.** `_reconcile` 은 OpenStack 을 진실로 본다. `wgclient.ensure_*` 는 재실행 시 같은 결과로 수렴한다. 부작용이 있는 단계를 새로 넣으면 워커가 죽었다가 재시도(claim timeout 10분)해도 안전해야 한다.
- **비밀번호는 워커 로그에만.** `services.provision` 이 `wg provisioned: student{n} / <password>` 를 로그로 남긴다. 포털 UI 확정 전까지 DB 저장은 명시적으로 금지.
- `catalog` 는 설치돼 있지 않다. `INSTALLED_APPS` 에 추가하지 않고 코드를 연결하지 말 것.
- **설계 배경은 `docs/` 에.** 백엔드 수정 전 `docs/02`·`03`, 90대 2분반 전환 관련은 `docs/07` 을 먼저 읽는다. 문서와 코드가 다르면 코드가 진실이다 (`docs/README.md` 「문서와 코드의 차이」).

### 테스트 요구사항
- 자동화 테스트 없음. 모든 `tests.py` 는 Django 스캐폴드. 검증은 개발계 대상 수동 절차(`PATCH_NOTES.md` "검증 시나리오").
- 변경 후 최소 확인: `/opt/su-portal` 에서 `.venv/bin/python manage.py check`.
- 동시성·통합 검증은 `probes/` 에 있고 실제 클라우드·DB 를 건드린다. 실행 전 `probes/AGENTS.md` 를 먼저 읽을 것.

### 공통 패턴
- 모든 상태 전이는 `transaction.atomic()` 안에서 `save(update_fields=[...])` 로 저장한다.
- 큐 방식 claim: `select_for_update(skip_locked=True).filter(...).order_by(...).first()`.
- management 명령은 예약만 한다("워커가 처리함" 으로 끝남). 실제 실행은 워커.

## 의존성

### 외부 라이브러리
- Django 5.2.17: admin, ORM, management 명령
- openstacksdk 4.18.0: `conn.compute.*` / `conn.network.*`
- requests: Warpgate Admin API
- psycopg 3: PostgreSQL 드라이버
- python-dotenv: `.env` 로딩
- 워커 호스트의 `ssh` 바이너리(`osclient.vm.wait_ssh` 가 서브프로세스로 호출)

### 외부 시스템
- OpenStack(개발계 테넌트): image / flavor / network / secgroup / keypair ID 는 `SU_*` env 변수. Floating IP 는 사전 할당되어 있음
- Warpgate Admin API `WG_API_URL`(예: `https://<host>:8888/@warpgate/admin/api`), 인증 헤더 `X-Warpgate-Token`
- PostgreSQL(`DB_*` env 변수)

<!-- MANUAL: 이 줄 아래에 수동으로 추가한 내용은 재생성 시 보존됨 -->
