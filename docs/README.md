# SU Cloud Portal 문서

Notion 워크스페이스 「SU-CLOUD」의 설계·구축·코드 해설 문서를 개발 참고용으로 옮긴 것(00~06)과, 레포에서 직접 작성한 의사결정 문서(07)를 모아 둔다. 정리일 2026-09-05.

## 읽는 순서

| 순서 | 문서 | 내용 | 언제 읽나 |
|---|---|---|---|
| 0 | [00-phase-0.5-roadmap.md](00-phase-0.5-roadmap.md) | Phase 0.5 작업 목차. 본문은 Notion 링크 | 프로젝트 범위를 처음 볼 때 |
| 1 | [01-warpgate-dev-setup.md](01-warpgate-dev-setup.md) | 개발계(.180) 인프라 실측값, Warpgate 설치·nginx·보안그룹·keypair·테스트 VM, 검증 절차와 실패 원인표 | 접속 경로·네트워크를 이해해야 할 때. 백엔드 문서의 전제 |
| 2 | [02-provisioning-backend.md](02-provisioning-backend.md) | Slot/Vm 모델, reserve→claim→provision→deprovision 흐름, 실패·워커 사망 복구, DB-as-queue 설계 근거, systemd 유닛 | 백엔드 코드를 만지기 전 필독 |
| 3 | [03-warpgate-backend.md](03-warpgate-backend.md) | wgclient 한 줄 단위 해설, services·osclient·.env 의 Warpgate 수정 지점 | Warpgate 연동을 만질 때 |
| 4 | [04-warpgate-patch-files.md](04-warpgate-patch-files.md) | 위 수정 4개 파일의 원본 전문 | 3번을 읽으며 원본을 대조할 때 |
| 5 | [05-portal-app.md](05-portal-app.md) | portal 웹 앱 구조(views/services/labels), 로그인→생성→조회→회수 데이터 흐름 | 포털 UI 작업 시 |
| 6 | [06-portal-app-legacy.md](06-portal-app-legacy.md) | 서비스 레이어 분리 전 portal 앱 | 5번의 변경 배경이 궁금할 때. 참고용 |
| 7 | [07-decision-90vm-two-sections.md](07-decision-90vm-two-sections.md) | 90대 2분반 운영 전환의 현안 정의와 의사결정 항목 (레포 작성, 살아 있는 문서) | Phase 1 첫 작업 방향을 정할 때 |

빠른 경로
- 백엔드만: 2 → 3 → 7
- 인프라만: 1 → 7 (인프라 절)
- 포털 UI만: 5 → 7 (포털 절)

## 문서와 코드의 차이 (반드시 확인)

문서 0~6 은 `origin/Phase_0.5_prod` 브랜치 작업 중 각 시점에 작성된 스냅샷이다. 이 레포의 `main` 과도, 현재 `Phase_0.5_prod` HEAD 와도 다르다.

### `main` (이 브랜치) 대비
- `main` 에는 백엔드(provisioning·osclient·wgclient)만 있고 `portal/` 은 "HELLO WORLD" 자리표시자다. 문서 5·6 의 포털 코드는 `main` 에 없다.
- 문서 2·3·4 의 코드는 `main` 과 거의 같고 다음만 다르다.
  - `KEYFILE`: main 은 하드코딩, 문서는 `os.environ.get("SU_KEYFILE", ...)`.
  - `_reconcile` / `_mark_failed`: 문서는 `s.name == name` 정확 일치 필터를 추가.
  - `.env.example`: 문서에는 `DJANGO_CSRF_TRUSTED_ORIGINS`, `SU_KEYFILE`, `WG_PUBKEY` 가 있고 main 에는 없다. `WG_PUBKEY` 는 main 의 `osclient/vm.py` 도 필수로 요구한다.

### `origin/Phase_0.5_prod` HEAD 대비
- HEAD 는 문서보다 더 나아가 있다: 포털 UI 전체, `imagebuild` 앱(커스텀 이미지 빌드), 이미지 카탈로그(`reserve(student_id, image_id, image_name)`, `Vm.image_id/image_name`, `osclient.vm.create(..., image_id)`), `VmFailure` 모델과 `acknowledge_failure`.
- 문서 5·6 의 `DismissedFailure` 는 이후 `portal/migrations/0002_delete_dismissedfailure.py` 로 삭제되었다.
- 현재 진실은 코드다. `git log origin/Phase_0.5_prod`, `git diff main origin/Phase_0.5_prod` 로 확인할 것.

## 정리 시 바꾼 것
- 파일명: Notion 해시 제거, 읽기 순서 번호 + ASCII 이름.
- 이미지: `images/<문서>/NN-설명.png` 로 이름을 바꾸고 본문 경로를 갱신. 캡션이 없던 5장에 캡션 추가.
- Notion 내부 링크(`‣`): URL 을 노출하고 "레포 미포함" 표기.
- 01 문서: Warpgate admin 비밀번호 마스킹(테스트 계정 2021001/2021002 는 유지), 본문 중간의 H1 메모를 인용구로 변경.
- 각 문서 상단에 출처·기준 브랜치 메타 블록 추가.
- 그 외 본문은 원문 그대로. 사실 오류가 보이면 원문을 고치지 말고 07 문서나 이슈에 기록.

## 원본
- Notion 「SU-CLOUD」 내보내기 (`~/Downloads/su-cloud-portal-docs`, 2026-09-05)
- 주간회의록(2026-08-30)과 운영계 오버커밋 검증 문서(2026-09-04)는 Notion 에만 있다. 07 문서가 의사결정에 필요한 범위만 요약한다.
