<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-09-05 | Updated: 2026-09-05 -->

# provisioning

## 목적
핵심 도메인 앱. `Slot` 풀과 append-only `Vm` 이력, Vm 을 `PROVISIONING → ACTIVE → DELETING → DELETED`(또는 `FAILED`)로 옮기는 서비스 계층, 운영자 UI 역할을 하는 Django admin, 작업을 예약·실행하는 management 명령(`issue`, `reclaim`, `worker`)을 소유한다.

## 주요 파일
| 파일 | 설명 |
|------|------|
| `models.py` | `Slot(n PK, status FREE/TAKEN)`: 1..45 고정, 재사용. `Vm(slot FK PROTECT, student_id, status, server_id UUID, error, created_at, updated_at, claimed_at, claimed_by)`: append-only. 인덱스 `(status, n)`, `(status, created_at)`. |
| `services.py` | 모든 상태 전이. 공개: `reserve`, `request_delete`, `request_delete_all`, `claim`, `provision`, `deprovision`. 내부: `_reconcile`, `_mark_active`, `_mark_failed`, `_release`, `_free_slot`. 상수 `KEYFILE="/opt/su-portal/sdk-probe-key.pem"`, `CLAIM_TIMEOUT=10분`. |
| `admin.py` | `SlotAdmin`: 추가/삭제 불가, FIP·계정 계산 컬럼, 액션 "선택한 개수만큼 VM 생성 요청"(선택된 FREE 슬롯 수만큼 `services.reserve("")` 호출). `VmAdmin`: 전 필드 읽기 전용, 액션 "선택한 VM 회수"(`services.request_delete` 호출). |
| `apps.py` | `ProvisioningConfig` |
| `views.py`, `tests.py` | 빈 Django 스캐폴드 |
| `__init__.py` | 비어 있음 |

## 하위 디렉터리
| 디렉터리 | 역할 |
|----------|------|
| `management/` | `manage.py` 명령 컨테이너(`management/AGENTS.md` 참고) |
| `migrations/` | 스키마 이력 0001–0004(`migrations/AGENTS.md` 참고) |

## 서비스 의미론 (`services.py` 수정 전 필독)
| 함수 | 잠금 | 효과 |
|---|---|---|
| `reserve(student_id)` | 가장 낮은 FREE 슬롯에 `select_for_update(skip_locked)` | Slot→TAKEN, `Vm(PROVISIONING)` 생성. 풀이 비면 `None`. |
| `request_delete(vm_id)` | 해당 Vm 에 `select_for_update` | ACTIVE 일 때만 →DELETING 후 claim 초기화. 아니면 `None`. |
| `request_delete_all()` | `request_delete` 경유 | 모든 ACTIVE Vm 을 슬롯 순으로. |
| `claim(worker_id)` | `select_for_update(skip_locked)` | 미할당 **또는** 10분 넘게 할당된(stale 워커 복구) PROVISIONING/DELETING 중 가장 오래된 행. `claimed_at` / `claimed_by` 기록. |
| `provision(vm_id)` | 최상위 잠금 없음 | `_reconcile`(이미 ACTIVE 인 `vm{n}` 입양, 비 ACTIVE 잔여물은 삭제) → `osvm.create` → `_mark_active` → `wg.provision_seat(password="Student{n}!")`. OpenStack 실패 → `_mark_failed`(FAILED, 정리, 슬롯 FREE). Warpgate 실패 → **PROVISIONING 으로 되돌리고** claim 을 지워 워커가 재시도하게 함. ACTIVE 로 두면 영원히 방치됨(2026-08-20 vm2 사례). 예외는 다시 던진다. |
| `deprovision(vm_id)` | 최상위 잠금 없음 | 이미 DELETED 면 no-op. Warpgate 해제 먼저(오류는 로그만, 던지지 않음) → `server_id` 가 있고 서버가 DELETED 가 아니면 OpenStack 삭제 → `_release`(한 트랜잭션에서 Vm→DELETED, Slot→FREE). |

- OpenStack 이 진실이다. `_reconcile` 은 이름으로 서버를 찾고 `server_id` 만 믿지 않는다.
- `_mark_failed` 는 잔여물 정리가 성공했을 때만 슬롯을 해제한다. 정리 실패 시 슬롯은 의도적으로 TAKEN 으로 남는다.
- Warpgate 비밀번호는 워커 로그(`log.info("wg provisioned: student%s / %s")`)에만 남는다. DB 평문 저장 금지(TODO Phase 0.5).

## AI 에이전트 안내

### 이 디렉터리에서 작업할 때
- 모든 상태 변경은 `transaction.atomic()` 안에서 `save(update_fields=[...])` 로 하고, 모델에 있으면 `updated_at` 도 포함한다.
- `provision` / `deprovision` 에 새 부작용을 넣으면 멱등해야 한다. 워커가 크래시나 claim timeout 뒤에 다시 실행한다.
- `Vm` 은 append-only 유지. 행을 `.delete()` 하지 않는다. Slot FK 가 `PROTECT` 인 이유다.
- admin 클래스는 추가/삭제를 막아 두었다. 운영자 인터페이스는 두 개의 예약 액션으로 한정한다.
- status 값을 추가하려면 `AlterField` 마이그레이션이 필요하다(`migrations/0003_alter_vm_status.py` 참고).
- `osvm.create` 의 SSH 도달 확인에 `KEYFILE` 이 워커 호스트에 존재해야 한다.

### 테스트 요구사항
- 단위 테스트 없음. 통합 확인: `probes/probe_reserve.py`(50스레드 reserve, 슬롯 중복 없음), `probes/probe_provision.py`, `probes/probe_deprovision.py`. 모두 실제 개발계를 치며 DB·클라우드 상태를 바꾼다.
- 모델 변경 후: `manage.py makemigrations provisioning && manage.py migrate`, 이어서 `manage.py check`.

### 공통 패턴
- 큐 claim: `.select_for_update(skip_locked=True).filter(...).order_by(...).first()`.
- 일괄 작업은 단건 서비스(`reserve("")`, `request_delete(id)`)를 반복 호출한다. 잠금 로직을 복제하지 않는다.

## 의존성

### 내부
- `osclient.get_conn`, `osclient.vm`(`create`, `delete`, `name_for`, `user_for`, `fip_for`)
- `wgclient.get_wg`(`provision_seat`, `deprovision_seat`)

### 외부
- Django ORM / admin / `BaseCommand`. `skip_locked` 때문에 PostgreSQL 필수

<!-- MANUAL: 이 줄 아래에 수동으로 추가한 내용은 재생성 시 보존됨 -->
