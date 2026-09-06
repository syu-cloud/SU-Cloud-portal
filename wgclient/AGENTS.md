<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-09-05 | Updated: 2026-09-05 -->

# wgclient

## 목적
Warpgate Admin API 클라이언트. 슬롯별 "좌석(seat)" 을 만들고 해제한다: Warpgate 사용자 `student{n}`, role `slot-{n}`, SSH target `vm{n}` 을 서로 연결해 각 학생이 자기 VM 에만 접근하게 한다. `osclient` 의 reconcile 과 같은 철학이다. 서버가 진실이고, 로컬 상태가 없으며, 모든 생성은 멱등한 `ensure_*` 다.

## 주요 파일
| 파일 | 설명 |
|------|------|
| `__init__.py` | `WarpgateError`, `WarpgateClient`, 팩토리 `get_wg()`. 단일 파일 패키지. |

## `WarpgateClient` 인터페이스
| 메서드 | 비고 |
|---|---|
| `__init__(base_url, token, verify, timeout=10)` | 기본값은 `WG_API_URL`, `WG_TOKEN`, `WG_VERIFY_TLS`(문자열 "true"/"false"). `requests.Session` 에 `X-Warpgate-Token`, `Content-Type: application/json` 헤더 설정. |
| `_call(method, path, json, ok_status)` | 예상 밖 상태 코드면 `WarpgateError`. 204, 빈 본문, 비 JSON 본문은 `None` 반환. |
| `ensure_user`, `ensure_role`, `ensure_ssh_target` | 컬렉션을 GET 해 `username` / `name` 으로 찾고 없으면 POST. target 은 `kind: Ssh`, `auth: {kind: PublicKey}`. |
| `set_password(user_id, password=None)` | POST `/users/{id}/credentials/passwords`. 미지정 시 `secrets.token_urlsafe(12)` 랜덤. 비밀번호 반환. |
| `bind(user_id, target_id, role_id, expiry=None)` | user→role(선택적 ISO8601 `expiry`), target→role 을 POST. 409 는 이미 연결됨으로 허용. |
| `delete_target` / `delete_user` / `delete_role` | 이름으로 찾아 DELETE, 404 허용. **`delete_role` 은 단수형 `/role/{id}` 경로 사용.** 실제 API 에서 검증된 특이점(커밋 `dec0683`). |
| `provision_seat(n, fip, ssh_user, expiry=None, password=None)` | user + role + target 을 ensure, bind, 비밀번호 설정. 비밀번호 반환. |
| `deprovision_seat(n)` | target → user → role 순으로 삭제. |
| `own_keys()` | GET `/ssh/own-keys`: Warpgate 자체 SSH 공개키. `WG_PUBKEY` 의 출처. |
| `status()` | 현재 존재하는 `students`, `vms`, `slots` 딕셔너리(접두어로 필터). |

## AI 에이전트 안내

### 이 디렉터리에서 작업할 때
- 엔드포인트 경로는 이 레포에 없는 외부 `wg_verify.py` 로 개발계 Warpgate 와 대조해 검증했다. API 가 다르면 경로 문자열만 바꾸고 ensure / 404 / 409 허용은 유지한다.
- 멱등성을 지킨다. `provision_seat` 과 `deprovision_seat` 은 워커 재시도 루프 안에서 돌며 반복 호출 시 같은 결과로 수렴해야 한다.
- `ensure_*` 는 호출마다 컬렉션 전체를 나열한다. 45좌석에는 충분하지만 확장 전에 재검토한다.
- 오류는 `WarpgateError` 로 올라온다. `services.provision` 은 어떤 예외든 Vm 을 PROVISIONING 으로 되돌리고, `services.deprovision` 은 로그만 남기고 계속한다.
- `bind` 의 `expiry` 는 학기말 자동 만료(Phase 1)용으로 준비만 되어 있고 아직 호출자가 넘기지 않는다.
- 개발계에서는 `WG_VERIFY_TLS=false` 로 TLS 검증을 끈다. `verify=False` 를 하드코딩하지 말 것.

### 테스트 요구사항
- 스모크: `/opt/su-portal` 에서 `.venv/bin/python -c "from wgclient import get_wg; print(get_wg().status())"`.
- E2E: 워커로 좌석 1개 발급 → Warpgate 웹 터미널에서 `student{n}` 로그인 → 회수 → `status()` 에서 사라졌는지 확인(`PATCH_NOTES.md` 시나리오 b, c).

## 의존성

### 외부
- requests, python-dotenv, 표준 라이브러리 `secrets`
- Warpgate Admin API `WG_API_URL`(예: `https://<host>:8888/@warpgate/admin/api`)

<!-- MANUAL: 이 줄 아래에 수동으로 추가한 내용은 재생성 시 보존됨 -->
