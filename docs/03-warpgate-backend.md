# WARPGATE 백엔드 코드 정리

> **출처**: Notion 「WARPGATE 백엔드 코드 정리」 · 레포 정리 2026-09-05
> 기준 브랜치 `Phase_0.5_prod`. 원본 파일 전문은 `04-warpgate-patch-files.md`.


기준: `syu-cloud/SU-Cloud-portal` `Phase_0.5_prod`

| 파일 | 구분 | 이 문서에서 다루는 범위 |
| --- | --- | --- |
| `wgclient/__init__.py` | 신규 | 전체 (1부) |
| `provisioning/services.py` | 수정 | WG 등록/해제/실패복구 블록만 (2부) |
| `osclient/vm.py` | 수정 | WG_PUBKEY 주입 2곳만 (2부) |
| `.env.example` | 수정 | warpgate 섹션만 (2부) |

---

# 1부. wgclient/**init**.py — 151줄 전체

`wgclient`는 Warpgate Admin API를 호출하는 순수 파이썬 패키지다 (Django 앱 아님). 워커의 `services.provision()` / `services.deprovision()`이 유일한 실사용처이고, 진단용으로 셸에서 단독 호출도 한다.

## 1. 모듈 docstring — 설계 원칙

```python
"""Warpgate Admin API 클라이언트.

설계 원칙 (osclient 의 _reconcile 과 동일 철학):
- 서버가 진실. 로컬 상태 파일 없음.
- 모든 생성은 ensure_* 로 멱등. 몇 번을 재실행해도 같은 결과로 수렴.
- 워커 재시도(claim timeout 회수)에 안전.

엔드포인트 경로는 wg_verify.py 로 검증한 계약을 따른다.
경로가 다르면 이 파일의 상수만 고치면 됨.
"""
```

이 세 원칙이 파일 전체를 지배한다. "student3이 Warpgate에 등록됐는지"를 어디에도 기록하지 않고(파일도 DB 컬럼도 없음) **필요할 때마다 Warpgate에 물어본다**. 그래서 워커가 도중에 죽고 다른 워커가 같은 작업을 처음부터 다시 실행해도, 이미 만들어진 건 건너뛰고 없는 것만 만들면서 같은 최종 상태로 수렴한다. 이 멱등성이 `services.provision()`의 "WG 실패 시 PROVISIONING으로 되돌려 재시도" 설계가 성립하는 전제 조건이다.

## 2. import와 모듈 로드 시점

```python
import os
import secrets

import requests
from dotenv import load_dotenv

load_dotenv("/opt/su-portal/.env")
```

- `secrets` — 암호학적 난수 표준 라이브러리. `random`과 달리 비밀번호 생성에 안전.
- `requests` — Warpgate엔 openstacksdk 같은 SDK가 없어 REST를 직접 호출.
- `load_dotenv`가 **import 시점**에 실행된다. `import wgclient`만 해도 `.env`가 환경변수로 로드됨. Django 경유면 `settings.py`가 이미 로드했지만, `load_dotenv`는 기존 환경변수를 덮지 않아 중복 무해. 이 줄 덕에 Django 없이 `python -c "from wgclient import get_wg; ..."` 단독 실행이 가능하다.

## 3. 예외 클래스

```python
class WarpgateError(RuntimeError):
    pass
```

내용 없는 서브클래스지만 역할이 있다. 호출부는 `except Exception:`으로 잡더라도 로그에 `WarpgateError: POST /users -> 401: ...`로 찍혀 **OpenStack 예외와 Warpgate 예외가 한눈에 구분**된다. 예외 타입 = 어느 시스템이 죽었는지의 라벨.

## 4. `__init__` — 클라이언트 초기화

```python
def __init__(self, base_url=None, token=None, verify=None, timeout=10):
    self.base = (base_url or os.environ["WG_API_URL"]).rstrip("/")
    self.token = token or os.environ["WG_TOKEN"]
    if verify is None:
        verify = os.environ.get("WG_VERIFY_TLS", "true").lower() == "true"
    self.verify = verify
    self.timeout = timeout
    self.s = requests.Session()
    self.s.headers["X-Warpgate-Token"] = self.token
    self.s.headers["Content-Type"] = "application/json"
```

| 줄 | 의미 |
| --- | --- |
| `base_url or os.environ[...]` | 인자 우선, 없으면 `.env`. 테스트/REPL에서 다른 Warpgate를 겨눌 구멍 |
| `.rstrip("/")` | `.env`에 `…/api/`로 넣어도 `…/api//users` 이중 슬래시 방지 |
| `if verify is None` | `verify=False`를 명시할 수 있어야 하는데 `False or x`는 `x`가 되므로 `or` 패턴 불가 → `None`일 때만 `.env` 참조 |
| `"false".lower() == "true"` | **환경변수는 항상 문자열.** `WG_VERIFY_TLS=false`도 파이썬엔 truthy 문자열 `"false"`로 들어오므로 명시 비교 필요 |
| `requests.Session()` | ① 커넥션 재사용 — `provision_seat` 한 번에 호출 7~8번, 세션 없으면 매번 TLS 핸드셰이크. ② 공통 헤더를 한 번만 설정 |
| `X-Warpgate-Token` | Warpgate Admin API 인증 방식. `Authorization: Bearer`가 아님 — `wg_verify.py` 실측으로 확정한 계약 |
| `Content-Type: application/json` 강제 | Warpgate는 **body 없는 POST**(bind 등)에도 이 헤더가 없으면 415를 낸다. `requests`는 `json=` 인자가 없으면 안 붙이므로 세션 기본 헤더로 박음. GET에도 붙지만 무해 |
| `timeout=10` | 같은 서버라 10초면 충분. 없으면 requests 기본이 무한 대기 — Warpgate가 행 걸리면 워커가 영원히 멈춘다 |

## 5. `_call` — 모든 HTTP의 단일 통로

```python
def _call(self, method, path, json=None, ok_status=(200, 201, 204)):
    r = self.s.request(
        method, f"{self.base}{path}",
        json=json, verify=self.verify, timeout=self.timeout,
    )
    if r.status_code not in ok_status:
        raise WarpgateError(f"{method} {path} -> {r.status_code}: {r.text[:300]}")
    if r.status_code == 204 or not r.content:
        return None
    try:
        return r.json()
    except ValueError:
        return None
```

- `self.s.request(method, ...)` — get/post/delete를 문자열 인자 하나로 통일.
- **`ok_status`를 호출부가 오버라이드** — 멱등성 구현의 핵심 장치. bind는 `(…, 409)`로 "이미 연결됨"을 성공 취급, delete는 `(…, 404)`로 "이미 없음"을 성공 취급.
- 실패 시 응답 본문 300자를 예외 메시지에 포함 — Warpgate의 에러 JSON이 원인 파악에 필요.
- 반환 3단: 204/빈 body → `None`, JSON 파싱 실패 → `None`(일부 DELETE가 non-JSON body를 주는 실측 케이스), 나머지 → dict/list.

통로를 이 함수 하나로 좁혀놨기 때문에 인증·TLS·타임아웃·에러 포맷이 전부 한 곳에 있고, docstring의 "경로가 다르면 이 파일만 고치면 됨"이 성립한다.

## 6. `ensure_*` 3형제 — 멱등 생성

패턴은 셋 다 동일: **전체 목록 GET → 이름으로 선형 탐색 → 있으면 그 객체 반환, 없으면 POST 후 생성된 객체 반환.** 반환 객체에 `id`(UUID)가 있어 이후 호출(`bind`, `set_password`)이 그 id를 쓴다. 이름→id 해석을 매번 서버에 물어보므로 로컬에 id를 저장할 필요가 없다.

```python
def ensure_user(self, username):
    for u in self._call("GET", "/users"):
        if u["username"] == username:
            return u
    return self._call("POST", "/users", {"username": username, "credential_policy": None})
```

`credential_policy: None` — 유저별 인증 정책(비밀번호+OTP 강제 등)을 쓰지 않고 전역 정책을 따른다.

```python
def ensure_role(self, name):
    # GET /roles → 없으면 POST /roles {"name": name}
```

```python
def ensure_ssh_target(self, name, host, port=22, username="ubuntu"):
    for t in self._call("GET", "/targets"):
        if t["name"] == name:
            return t
    return self._call("POST", "/targets", {
        "name": name,
        "options": {
            "kind": "Ssh",
            "host": host,                     # VM의 FIP
            "port": port,
            "username": username,             # student{n} — VM 안의 리눅스 계정
            "auth": {"kind": "PublicKey"},
        },
    })
```

- `options.kind: "Ssh"` — Warpgate 타깃 종류(SSH/HTTP/MySQL/Postgres) 중 SSH.
- `auth.kind: "PublicKey"` — **Warpgate가 VM에 들어갈 때** 자기 개인키로 인증. 이게 되는 이유는 `osclient/vm.py`의 cloud-init이 `WG_PUBKEY`(Warpgate 자체 공개키)를 VM `authorized_keys`에 심어두기 때문. 인증이 두 구간으로 분리돼 있다: 학생↔Warpgate = 비밀번호, Warpgate↔VM = 공개키.
- `username="ubuntu"` 기본값은 안전장치일 뿐, 실제 호출은 항상 `student{n}` 명시.

**주의 — ensure는 이름만 비교한다.** `vm3` 타깃이 존재하는데 host(FIP)가 다르면 갱신 없이 그대로 반환한다. 현재는 FIP가 슬롯 번호로 결정돼 바뀔 일이 없지만, deprovision 없이 재발급하는 비정상 경로가 생기면 stale host가 남을 수 있는 지점.

## 7. `set_password`

```python
def set_password(self, user_id, password=None):
    """비밀번호 크리덴셜 설정. 반환값의 password 를 학생에게 전달."""
    password = password or secrets.token_urlsafe(12)
    self._call("POST", f"/users/{user_id}/credentials/passwords", {"password": password})
    return password
```

- `password=None`이면 `secrets.token_urlsafe(12)` — 12바이트 난수의 URL-safe base64, 16자 문자열.
- **반환값이 유일한 전달 경로.** Warpgate는 해시만 저장하므로 다시 조회 불가 — 호출부가 반환값을 안 받으면 비밀번호는 증발한다.
- 현재 `services.provision()`은 `password=f"Student{n}!"` 고정값을 넘기고 반환값을 워커 로그에만 남긴다. `password=` 인자를 빼는 순간 랜덤 발급으로 전환되며, 그때는 반환값을 학생에게 보여줄 UI가 필요 (후속 과제).
- 이 엔드포인트는 "credential 추가"라 재실행 시 비밀번호 credential이 하나 더 쌓일 수 있다(둘 다 로그인 가능). 멱등이 완벽하진 않지만 해가 없는 방향이라 허용.

## 8. `bind` — role을 join으로

```python
def bind(self, user_id, target_id, role_id, expiry=None):
    """user↔role, target↔role 연결. role 이 1:1 격리의 join.
    expiry(ISO8601): 학기말 자동 만료용. user-role 에만 적용."""
    body = {"expiry": expiry} if expiry else {}
    self._call("POST", f"/users/{user_id}/roles/{role_id}", json=body,
               ok_status=(200, 201, 204, 409))   # 409 = 이미 연결됨 → 멱등
    self._call("POST", f"/targets/{target_id}/roles/{role_id}",
               ok_status=(200, 201, 204, 409))
```

Warpgate 권한 모델엔 user→target 직접 연결이 없다. **user는 role을 갖고, target은 role을 허용한다**:

```
student3 ──(user-role)──▶ slot-3 ◀──(target-role)── vm3
```

`slot-3` role을 student3만 갖고 vm3만 허용하므로 student3 눈에는 vm3 하나만 보인다 — 45명 격리가 role 45개로 구현된 것. POST 두 번이 그 간선 두 개다.

- **409를 성공 취급** — 이미 연결돼 있으면 Warpgate가 409 Conflict. ensure가 목록 조회로 멱등을 구현했다면 bind는 에러코드 허용으로 멱등을 구현 — 연결 목록 조회보다 쏘고 409를 삼키는 게 싸다.
- `expiry` — ISO8601 시각을 주면 user-role 연결에 만료. 학기 종료일을 넣으면 그날 이후 학생이 타깃을 못 보게 되는 기능. 현재 `provision_seat`이 인자를 안 넘겨 미사용. 만료는 user-role의 속성이라 첫 호출에만 적용.

## 9. `delete_*` 3형제 — 멱등 삭제

```python
def delete_target(self, name):
    for t in self._call("GET", "/targets"):
        if t["name"] == name:
            self._call("DELETE", f"/targets/{t['id']}", ok_status=(200, 204, 404))
            return

def delete_user(self, username):
    # 동일 패턴, /users/{id}

def delete_role(self, name):
    for r in self._call("GET", "/roles"):
        if r["name"] == name:
            self._call("DELETE", f"/role/{r['id']}", ok_status=(200, 204, 404))
            return
```

ensure의 거울상: 목록에서 이름으로 찾아 **id로** 삭제.

- 못 찾으면 조용히 리턴 — "없음 = 이미 삭제됨 = 성공".
- 찾은 뒤 DELETE가 404여도 성공 취급 — 목록 조회와 DELETE 사이에 다른 워커가 지웠을 수 있다(워커 여러 개가 도는 세계의 방어).
- **`/role/{id}` — 단수.** users/targets는 복수 경로인데 role 삭제만 단수. Warpgate API 자체의 비일관성으로, `/roles/{id}`로 보내면 404가 나서 "삭제했는데 안 지워짐"을 겪은 뒤 실측으로 확정한 값. docstring의 "wg_verify.py로 검증한 계약"의 대표 사례.

## 10. 고수준 두 함수 — services.py가 부르는 단위

```python
def provision_seat(self, n, fip, ssh_user, expiry=None, password=None):
    """슬롯 n 발급: user student{n} + role slot-{n} + target vm{n} 을 만들고 연결.
    password 미지정 시 랜덤 생성 (반환값으로 전달)."""
    user = self.ensure_user(f"student{n}")
    role = self.ensure_role(f"slot-{n}")
    target = self.ensure_ssh_target(f"vm{n}", host=fip, username=ssh_user)
    self.bind(user["id"], target["id"], role["id"], expiry=expiry)
    return self.set_password(user["id"], password)
```

저수준 5개를 한 단위로 묶었지만 **트랜잭션은 아니다** — 중간에 죽으면 user만 있고 role은 없는 상태가 남을 수 있다. 그래도 전 단계가 멱등이라 **재실행이 곧 복구**. `services.py`가 WG 실패 시 상태를 PROVISIONING으로 되돌리기만 하면 되는 이유가 이것. 슬롯 번호 `n` 하나에서 이름 셋(`student{n}`, `slot-{n}`, `vm{n}`)이 결정되는 네이밍 규칙이 여기서도 계약으로 작동한다.

```python
def deprovision_seat(self, n):
    """슬롯 n 회수: target → user → role 순서로 제거."""
    self.delete_target(f"vm{n}")
    self.delete_user(f"student{n}")
    self.delete_role(f"slot-{n}")
```

순서: 접속 경로(target)부터 끊고, 양쪽 연결이 사라진 role을 마지막에. 셋 다 멱등이라 순서가 바뀌어도 수렴하지만, 중간에 실패해도 "학생이 접속 못 하는 상태"가 먼저 확보되는 순서다.

## 11. 진단용 두 함수

```python
def own_keys(self):
    """Warpgate 자체 SSH 공개키 목록.
    운영계 전환 시 이 키를 OpenStack keypair 로 등록해야 VM 접속 가능."""
    return self._call("GET", "/ssh/own-keys")
```

Warpgate 인스턴스 자신의 SSH 공개키. 이 중 ed25519 공개키가 두 곳으로 간다 — `.env`의 `WG_PUBKEY`(cloud-init 주입), OpenStack keypair. **운영계 이관 때 dev와 키가 다른 걸 놓치면 Warpgate가 VM에 못 들어간다** — docstring 경고가 그 얘기. 응답이 오면 URL/토큰/TLS가 전부 정상이라는 뜻이라 헬스체크로도 쓴다:

```bash
.venv/bin/python -c "import wgclient; print(wgclient.get_wg().own_keys())"
```

```python
def status(self):
    """현재 발급 현황 요약."""
    users = [u["username"] for u in self._call("GET", "/users")]
    targets = [t["name"] for t in self._call("GET", "/targets")]
    roles = [r["name"] for r in self._call("GET", "/roles")]
    return {
        "students": sorted(u for u in users if u.startswith("student")),
        "vms": sorted(t for t in targets if t.startswith("vm")),
        "slots": sorted(r for r in roles if r.startswith("slot-")),
    }
```

우리 네이밍 규칙에 맞는 것만 필터 — `admin` 계정이나 수동 생성 타깃은 자동으로 빠진다. **세 리스트 길이가 같아야 정상**. 다르면 provision이 중간에 끊긴 좌석이 있다는 신호. 셸에서 빠른 건강검진용.

## 12. `get_wg`

```python
def get_wg():
    return WarpgateClient()
```

`osclient.get_conn()`과 짝 맞춘 팩토리. 매번 새 인스턴스(=새 requests 세션) — 캐싱하지 않는 건 장시간 도는 워커에서 낡은 커넥션 문제를 피하고, 작업 하나당 세션 하나면 충분해서. 호출부는 생성자 시그니처를 몰라도 된다.

## 13. 전체를 관통하는 것

이 파일엔 상태가 없다. 저장하는 건 연결 정보(`base/token/verify/timeout/session`)뿐이고, "무엇이 만들어져 있는지"는 전부 Warpgate에 물어본다. 그래서 워커 몇 개가 동시에 돌든, 재시도가 몇 번 겹치든 최종 상태는 항상 다음으로 수렴한다:

```
user student{n} + role slot-{n} + target vm{n} + bind 간선 2개 + password credential
```

`services.py`의 재시도 설계와 `worker.py`의 claim 타임아웃 복구가 전부 이 파일의 멱등성 위에 서 있다.

### 멱등성 구현 기법 정리

| 기법 | 적용 함수 |
| --- | --- |
| 목록 조회 후 있으면 반환 | `ensure_user` / `ensure_role` / `ensure_ssh_target` |
| 에러코드 성공 취급 (409) | `bind` |
| 에러코드 성공 취급 (404) + 없으면 무시 | `delete_target` / `delete_user` / `delete_role` |
| 재실행 무해 (credential 중복 허용) | `set_password` |

### API 계약 요약 (wg_verify.py 실측)

| 항목 | 값 |
| --- | --- |
| 인증 | `X-Warpgate-Token` 헤더 |
| Content-Type | body 없는 POST에도 `application/json` 필수 (없으면 415) |
| role 삭제 경로 | `/role/{id}` — **단수** (조회/생성은 `/roles`) |
| bind 중복 | 409 반환 |
| 삭제 대상 없음 | 404 반환 |
| user↔target | 직접 연결 없음, role 경유 |

---

# 2부. 나머지 파일의 Warpgate 수정 부분

기존 백엔드(슬롯 예약·claim·OpenStack 생성)는 그대로 두고, 그 파이프라인의 세 지점에 Warpgate를 끼워 넣은 수정이다. 아래는 그 수정 부분만.

## 1. services.py — import 추가

```python
from wgclient import get_wg                       # [ADDED]
```

이 파일에서 Warpgate를 위해 추가된 유일한 import. services는 OpenStack(`get_conn`)과 Warpgate(`get_wg`)를 **둘 다 아는 유일한 계층**이고, 그 아래 osclient/wgclient는 서로의 존재를 모른다. 두 시스템의 순서 조율(VM 먼저 → WG 등록, WG 해제 먼저 → VM 삭제)이 전부 이 파일에서 일어나는 이유.

## 2. services.py — `provision()`의 Warpgate 등록 블록

```python
    adopted = _reconcile(conn, vm_rec)            # [CHANGED] 입양돼도 WG 등록은 계속 진행
```

`[CHANGED]`가 붙은 이유: 원래는 `_reconcile`이 기존 VM을 입양하면 거기서 함수가 끝났다. 이제는 입양 여부만 `adopted`에 담고 **어느 경로든 아래 Warpgate 블록으로 흘러가게** 바꿨다. 이 한 줄이 없으면 "WG 실패 → 되돌림 → 재집기 → VM 입양 → 끝"이 돼서 WG 재시도가 영영 일어나지 않는다. 복구 루프의 연결 고리.

```python
    # [ADDED] Warpgate 등록 — ensure_* 라 재실행에 안전.
    # 실패 시 PROVISIONING 으로 되돌려 워커 재시도 루프에 복귀시킴.
    # (ACTIVE 로 남기면 claim 조건에서 빠져 영원히 재시도 안 됨 — 8/20 vm2 사례)
    n = vm_rec.slot_id
    try:
        wg = get_wg()
        password = wg.provision_seat(
            n=n,
            fip=osvm.fip_for(n),
            ssh_user=osvm.user_for(n),
            password=f"Student{n}!",
        )
        log.info("wg provisioned: student%s", n)
        # TODO(Phase 0.5): 비밀번호 전달 경로는 포털 UI 확정 후 결정.
        # 임시로 워커 로그에만 남김. DB 평문 저장 금지.
        log.info("wg provisioned: student%s / %s", n, password)
    except Exception:
        log.exception(
            "warpgate provision failed for vm%s, reverting to PROVISIONING for retry", n
        )
        with transaction.atomic():
            vm_rec.status = Vm.PROVISIONING
            vm_rec.claimed_at = None
            vm_rec.claimed_by = ""
            vm_rec.save(update_fields=["status", "claimed_at", "claimed_by", "updated_at"])
        raise
```

**호출부 (try 블록)**

- 인자 세 개가 전부 슬롯 번호 `n`에서 파생: `osvm.fip_for(n)`(FIP 계산식), `osvm.user_for(n)`(`student{n}`), `password=f"Student{n}!"`. osclient의 네이밍 함수를 그대로 가져다 써서 **OpenStack의 VM과 Warpgate의 target이 같은 좌표계를 공유**한다 — 두 시스템의 정합성이 매핑 테이블이 아니라 네이밍 규칙 하나로 보장되는 구조.
- `password=f"Student{n}!"` — 프로젝트 전체에서 학생 비밀번호가 결정되는 유일한 지점. 규칙 기반이라 교수 공지 한 문장으로 45명 배포 완료. 이 인자를 지우면 wgclient의 `secrets.token_urlsafe(12)` 랜덤 발급으로 전환된다(Phase 1 카드).
- 반환된 password는 `log.info`로 워커 로그에만 남고 버려진다 — TODO 주석대로 임시. 확정안은 포털 결과 화면 표시 시점에 `set_password()` 재호출로 1회 표시, DB 저장 없음. (`log.info` 두 번은 중복 — 위쪽 줄이 잉여, 정리 대상)

**실패 복구 (except 블록) — 8/20 vm2 버그의 수정본**

원래 흐름의 결함: `_mark_active()`가 WG 등록보다 먼저 실행되므로 WG가 실패해도 DB는 이미 ACTIVE. 그런데 워커의 `claim()`은 PROVISIONING/DELETING 상태만 집으므로, 이 행은 **영원히 재시도되지 않는다.** VM은 살아 있고 DB는 정상처럼 보이는데 학생 계정만 없는 반쪽 좌석 — 실제 8/20에 vm2가 이 상태로 굳었다.

수정의 동작:

1. 상태를 `PROVISIONING`으로 되돌리고 `claimed_at/claimed_by`를 비운다 → claim 조건에 다시 들어간다
2. 다음 워커가 집는다 → `_reconcile`이 살아 있는 VM을 입양한다(재생성 없음)
3. `[CHANGED]` 덕에 입양 후에도 WG 블록으로 진행 → **Warpgate 단계만 재시도**
4. wgclient가 전부 멱등(`ensure_*`)이라 지난 시도에서 절반 만들어졌어도 이어서 수렴

일시적 WG 장애(컨테이너 재시작 등)면 사람 개입 없이 몇 사이클 안에 자동 복구된다.

- 마지막 `raise` — 상태는 복구해 두되 예외는 위로 올린다. 워커 로그에 실패가 기록되고 워커는 다음 작업으로 넘어간다. 조용히 삼키면 실패가 안 보인다.

## 3. services.py — `deprovision()`의 Warpgate 선(先)해제 블록

```python
    # [ADDED] VM 삭제 전에 Warpgate 접근부터 끊는다 (죽은 target 로 로그인 시도 방지)
    try:
        get_wg().deprovision_seat(vm_rec.slot_id)
    except Exception:
        log.exception("warpgate deprovision failed for vm%s (continuing)", vm_rec.slot_id)
```

**순서가 핵심.** Warpgate 해제가 VM 삭제보다 먼저다. 뒤집으면 VM은 죽었는데 target은 남아서, 학생이 로그인해 멀쩡히 보이는 target을 클릭 → 접속 실패라는 혼란 상태가 생긴다. 접근부터 끊으면 최악의 경우에도 "로그인하면 아무것도 안 보임"으로 끝난다.

**실패 처리가 provision과 정반대인 것도 의도.**

|  | Warpgate 실패 시 | 이유 |
| --- | --- | --- |
| provision | PROVISIONING 되돌려 **재시도** | WG 등록 없는 VM은 학생에게 무용지물 — 반드시 완성돼야 함 |
| deprovision | 로그만 남기고 **계속 진행** | 회수의 목적은 자원(VM) 회수 — WG 잔여물 때문에 VM 삭제를 막을 이유 없음 |

남은 user/role/target은 해가 없다 — 다음 발급 때 같은 슬롯의 `ensure_*`가 그대로 재사용(입양)하므로 자연 수렴한다.

## 4. osclient/vm.py — WG_PUBKEY 주입 (2곳)

osclient는 원래 순수 OpenStack 코드였고, Warpgate를 위해 손댄 곳은 아래 둘뿐이다.

**① USER_DATA 템플릿 — `{wg_pubkey}` 줄 추가**

```python
USER_DATA = """#cloud-config
users:
  - name: student{n}
    groups: [sudo]
    sudo: ALL=(ALL) NOPASSWD:ALL
    shell: /bin/bash
    ssh_authorized_keys:
      - {pubkey}
      - {wg_pubkey}          # ← [수정] Warpgate 자체 공개키 추가
"""
```

cloud-init이 VM 첫 부팅 때 `student{n}` 계정을 만들면서 `authorized_keys`에 키 두 개를 심는다. `{pubkey}`(관리키)는 원래 있던 것이고, **`{wg_pubkey}` 한 줄이 Warpgate 수정의 전부**다.

이 줄이 wgclient의 target 등록과 짝을 이룬다:

```
wgclient: ensure_ssh_target(..., auth={"kind": "PublicKey"})   ← Warpgate가 "공개키로 들어가겠다" 선언
osclient: ssh_authorized_keys: - {wg_pubkey}                   ← VM이 "그 키를 받아주겠다" 준비
```

둘 중 하나만 있으면 접속이 안 된다. 이 짝이 완성돼야 "VM 생성 즉시, 수동 키 작업 0으로 Warpgate 웹터미널 접속 가능"이 성립한다. 인증 2구간 분리(학생↔Warpgate = 비밀번호, Warpgate↔VM = 공개키)의 뒷구간이 물리적으로 심어지는 자리.

**② build_user_data — fail-fast**

```python
def build_user_data(n, pubkey):
    """관리용 키(pubkey) + Warpgate 자체 키(WG_PUBKEY) 를 함께 주입.
    WG_PUBKEY 가 없으면 Warpgate 가 VM 에 접속할 수 없으므로 즉시 실패시킴.
    값은 wgclient.own_keys() 의 ed25519 public_key 를 .env 에 넣는다."""
    ud = USER_DATA.format(n=n, pubkey=pubkey, wg_pubkey=os.environ["WG_PUBKEY"])
    return base64.b64encode(ud.encode()).decode()
```

- `os.environ["WG_PUBKEY"]` — `.get()`이 아니라 대괄호 접근. **환경변수가 없으면 KeyError로 VM 생성 자체가 즉시 실패한다.** 의도된 설계: 키 없이 VM을 만들면 겉으론 성공인데 Warpgate만 못 들어가는 VM이 나오고, 이건 45대를 다 만들고 학생이 접속해본 뒤에야 발견되는 최악의 실패 모드다. 시작조차 못 하게 막는 게 낫다.
- docstring이 값의 출처를 명시 — `wgclient.own_keys()`의 ed25519 public_key. **운영 이관 주의사항이 코드에 박혀 있는 것**: prod Warpgate는 자기 키를 새로 생성하므로, own_keys로 다시 뽑아 `.env`를 갱신하지 않으면 dev 키가 심어져 prod Warpgate가 전 VM에 접속 불가가 된다.

참고 — 파일의 나머지(`wait_ssh`, `create`의 FIP 로직 등)는 수정 없이 Warpgate 연동의 **전제**로 작동한다: `wait_ssh` 통과 = cloud-init이 키를 다 심었다는 보장이라, services가 그 다음에야 `provision_seat`을 부르는 순서가 안전해진다. FIP가 슬롯 번호로 고정(`fip_for`)이라 target의 host가 재발급 후에도 안 변하는 것도 기존 로직의 부산물.

## 5. .env.example — warpgate 섹션 추가

```bash
# --- warpgate (개발계) ---
# Admin API 베이스 URL. 예: https://<dev-warpgate-host>:8888/@warpgate/admin/api
WG_API_URL=
# 개발계 Warpgate 에서 발급한 portal-backend 전용 API 토큰
WG_TOKEN=
# 개발계 자체 서명/사설 인증서면 false
WG_VERIFY_TLS=false
# wgclient.own_keys() 의 ed25519 public_key 값
WG_PUBKEY=
```

| 변수 | 읽는 곳 | 의미 |
| --- | --- | --- |
| `WG_API_URL` | wgclient | Admin API 베이스 URL — `/@warpgate/admin/api`까지 포함. 운영계는 공인 도메인 경유가 아니라 `127.0.0.1:9443` 직결이 정답 (외부 왕복 제거) |
| `WG_TOKEN` | wgclient | `portal-backend` 라벨로 발급한 전용 API 토큰. `X-Warpgate-Token` 헤더로 실려 나감. admin 계정 공유가 아닌 전용 토큰 — 유출 시 이것만 폐기 |
| `WG_VERIFY_TLS` | wgclient | TLS 인증서 검증 여부. dev=사설 인증서라 false, prod=정식 와일드카드라 true |
| `WG_PUBKEY` | osclient | Warpgate 자체 ed25519 공개키. cloud-init으로 전 VM에 주입. **dev/prod 키가 다르므로 이관 시 재발급 필수** |

네 변수의 관계: 앞의 셋은 **포털이 Warpgate에 말을 걸기 위한** 값(wgclient), 마지막 하나는 **Warpgate가 VM에 들어가기 위한** 값(osclient). 연동이 양방향이라 변수도 양쪽에 하나씩 걸쳐 있다.

---

# 전체 조감 — 수정 지점이 파이프라인에서 맞물리는 자리

```
[worker] provision()
   ├ _reconcile()                        [CHANGED] 입양돼도 아래로 계속
   ├ osvm.create()
   │    └ user_data 에 {wg_pubkey}       [수정]   ← Warpgate→VM 인증 준비
   └ wg.provision_seat(...)              [ADDED]  ← 포털→Warpgate 등록 (1부의 wgclient)
        └ 실패 시 PROVISIONING 되돌림    [ADDED]  ← 자동 재시도 루프

[worker] deprovision()
   └ wg.deprovision_seat() 를 VM 삭제보다 먼저  [ADDED]

.env: WG_API_URL / WG_TOKEN / WG_VERIFY_TLS (→wgclient) + WG_PUBKEY (→osclient)  [추가]
```

한 줄 요약 — Warpgate 연동은 ① 전용 클라이언트를 새로 만들고(1부, wgclient 멱등 설계), ② 기존 파이프라인의 세 지점에 끼워 넣었다(2부): VM이 Warpgate를 받아들이게(키 주입), 포털이 Warpgate에 등록하게(provision_seat + 실패 복구), 회수 때 Warpgate부터 끊게(선해제).
