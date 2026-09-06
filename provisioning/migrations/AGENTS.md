<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-09-05 | Updated: 2026-09-05 -->

# migrations

## 목적
`provisioning` 앱의 Django 스키마 이력. 네 개 모두 2026-08-20 에 생성되었고 현재 `models.py` 와 일치한다.

## 주요 파일
| 파일 | 설명 |
|------|------|
| `0001_initial.py` | `Slot`(n PK, status), `Vm`(student_id, status, server_id, error, 타임스탬프, slot FK PROTECT) 생성. 인덱스 `(status, n)`, `(status, created_at)` |
| `0002_vm_claimed_at_vm_claimed_by.py` | 워커 claim 컬럼 `claimed_at`, `claimed_by` 추가 |
| `0003_alter_vm_status.py` | status choices 에 `DELETING` 추가 |
| `0004_alter_vm_student_id.py` | `student_id` 를 `blank=True` 로 변경(admin 일괄 예약 액션이 `""` 를 넘김) |
| `__init__.py` | 비어 있음 |

## AI 에이전트 안내

### 이 디렉터리에서 작업할 때
- 적용된 마이그레이션은 수정하지 않는다. `manage.py makemigrations provisioning` 으로 새로 추가한다.
- 45개 `Slot` 행을 시드하는 데이터 마이그레이션은 없다. 별도로 생성한다. 추가한다면 멱등하게(`get_or_create`) 작성할 것.
- `status` 는 `choices` 가 있는 일반 `CharField` 라서 값을 추가하면 컬럼은 그대로여도 0003 같은 `AlterField` 마이그레이션이 필요하다.

### 테스트 요구사항
- `models.py` 수정과 대응 마이그레이션 추가 후 `manage.py makemigrations --check --dry-run` 이 변경 없음을 보고해야 한다.

## 의존성

### 내부
- `provisioning/models.py`

<!-- MANUAL: 이 줄 아래에 수동으로 추가한 내용은 재생성 시 보존됨 -->
