<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-09-05 | Updated: 2026-09-05 -->

# commands

## 목적
운영자 CLI 를 구성하는 `manage.py` 하위 명령. `issue` 와 `reclaim` 은 `Vm` status 행을 써서 작업을 예약만 하고, `worker` 는 그 행을 claim 해 OpenStack / Warpgate 연동을 실제 수행하는 상주 프로세스다.

## 주요 파일
| 파일 | 설명 |
|------|------|
| `issue.py` | `manage.py issue [-n COUNT] [--student ID]`: `services.reserve` 를 최대 COUNT 회 호출, FREE 슬롯이 없으면 조기 중단. 슬롯마다 "예약 vm{n}" 출력, 부족 시 경고. |
| `reclaim.py` | `manage.py reclaim [--yes]`: 모든 ACTIVE Vm 을 나열하고 `--yes` 가 없으면 문자열 `yes` 입력을 요구한 뒤 `services.request_delete_all()`. |
| `worker.py` | `manage.py worker [--interval SEC]`(기본 3.0): `worker_id="{hostname}-{pid}"`. `services.claim` → DELETING 이면 `deprovision`, 아니면 `provision` 을 반복. 작업별 예외를 전부 잡고 루프 유지. SIGTERM / SIGINT 는 플래그만 세워 현재 작업 후 정상 종료. |
| `__init__.py` | 비어 있음 |

## AI 에이전트 안내

### 이 디렉터리에서 작업할 때
- `worker` 외의 명령은 예약 전용을 유지한다. `issue` / `reclaim` 에서 `provision` / `deprovision` 을 호출하지 않는다.
- `worker` 는 예외를 삼켜 Vm 하나가 루프를 죽이지 못하게 한다. 실패 처리(예: PROVISIONING 되돌리기)는 여기가 아니라 `services` 에 둔다.
- 워커 여러 개를 동시에 돌릴 수 있다(`skip_locked` + `claimed_by`). stale claim 은 `CLAIM_TIMEOUT` 후 다시 집힌다.
- 출력 문자열은 한국어이고 운영자가 읽는 것이므로 안정적으로 유지한다. Warpgate 비밀번호는 `services` 로깅을 통해 워커 로그 출력에만 나타난다.
- `reclaim` 은 `input()` 을 쓴다. 자동화에서는 `--yes` 를 넘겨야 한다.

### 테스트 요구사항
- 수동: `manage.py issue -n 1` → 다른 터미널에서 `manage.py worker` 실행 후 "vm{n} ACTIVE" 확인 → `manage.py reclaim --yes` 후 "vm{n} DELETED" 확인. `PATCH_NOTES.md` 시나리오 b, c 참고.

## 의존성

### 내부
- `provisioning.services`, `provisioning.models.Vm`

### 외부
- Django `BaseCommand`, 표준 라이브러리 `signal`, `socket`, `time`

<!-- MANUAL: 이 줄 아래에 수동으로 추가한 내용은 재생성 시 보존됨 -->
