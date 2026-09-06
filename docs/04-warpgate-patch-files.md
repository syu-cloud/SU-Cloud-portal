# Warpgate API 관련 수정 파일 원본

> **출처**: Notion 「Warpgate API 관련 수정 파일 원본」 · 레포 정리 2026-09-05
> 기준 브랜치 `Phase_0.5_prod`. 해설은 `03-warpgate-backend.md`.


기준: `syu-cloud/SU-Cloud-portal` `Phase_0.5_prod`

Warpgate API 사용을 위해 손댄 파일은 4개.

| 파일 | 구분 | 내용 |
| --- | --- | --- |
| `wgclient/__init__.py` | 신규 | Warpgate Admin API 클라이언트 |
| `provisioning/services.py` | 수정 | Warpgate 등록/해제 + 실패 복구 (`[ADDED]`/`[CHANGED]` 주석이 수정 지점) |
| `osclient/vm.py` | 수정 | cloud-init에 WG_PUBKEY 주입 |
| `.env.example` | 수정 | warpgate 섹션 추가 |

`config/settings.py`엔 Warpgate 관련 코드 없음 — WG_* 환경변수는 wgclient가 직접 `os.environ`으로 읽음.

---

## `wgclient/__init__.py` — 신규

```python
"""Warpgate Admin API 클라이언트.

설계 원칙 (osclient 의 _reconcile 과 동일 철학):
- 서버가 진실. 로컬 상태 파일 없음.
- 모든 생성은 ensure_* 로 멱등. 몇 번을 재실행해도 같은 결과로 수렴.
- 워커 재시도(claim timeout 회수)에 안전.

엔드포인트 경로는 wg_verify.py 로 검증한 계약을 따른다.
경로가 다르면 이 파일의 상수만 고치면 됨.
"""
import os
import secrets

import requests
from dotenv import load_dotenv

load_dotenv("/opt/su-portal/.env")

class WarpgateError(RuntimeError):
    pass

class WarpgateClient:
    def __init__(self, base_url=None, token=None, verify=None, timeout=10):
        self.base = (base_url or os.environ["WG_API_URL"]).rstrip("/")
        self.token = token or os.environ["WG_TOKEN"]
        if verify is None:
            verify = os.environ.get("WG_VERIFY_TLS", "true").lower() == "true"
        self.verify = verify
        self.timeout = timeout
        self.s = requests.Session()
        # wg_verify.py 로 검증된 인증 방식
        self.s.headers["X-Warpgate-Token"] = self.token
        self.s.headers["Content-Type"] = "application/json"

    # ── 저수준 ─────────────────────────────────────────────

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

    # ── ensure: 있으면 반환, 없으면 생성 ────────────────────

    def ensure_user(self, username):
        for u in self._call("GET", "/users"):
            if u["username"] == username:
                return u
        return self._call("POST", "/users", {"username": username, "credential_policy": None})

    def set_password(self, user_id, password=None):
        """비밀번호 크리덴셜 설정. 반환값의 password 를 학생에게 전달."""
        password = password or secrets.token_urlsafe(12)
        self._call("POST", f"/users/{user_id}/credentials/passwords", {"password": password})
        return password

    def ensure_role(self, name):
        for r in self._call("GET", "/roles"):
            if r["name"] == name:
                return r
        return self._call("POST", "/roles", {"name": name})

    def ensure_ssh_target(self, name, host, port=22, username="ubuntu"):
        for t in self._call("GET", "/targets"):
            if t["name"] == name:
                return t
        return self._call("POST", "/targets", {
            "name": name,
            "options": {
                "kind": "Ssh",
                "host": host,
                "port": port,
                "username": username,
                "auth": {"kind": "PublicKey"},
            },
        })

    def bind(self, user_id, target_id, role_id, expiry=None):
        """user↔role, target↔role 연결. role 이 1:1 격리의 join.
        expiry(ISO8601): 학기말 자동 만료용. user-role 에만 적용."""
        body = {"expiry": expiry} if expiry else {}
        self._call("POST", f"/users/{user_id}/roles/{role_id}", json=body,
                   ok_status=(200, 201, 204, 409))   # 409 = 이미 연결됨 → 멱등
        self._call("POST", f"/targets/{target_id}/roles/{role_id}",
                   ok_status=(200, 201, 204, 409))

    # ── 삭제 (404 허용 → 멱등) ─────────────────────────────

    def delete_target(self, name):
        for t in self._call("GET", "/targets"):
            if t["name"] == name:
                self._call("DELETE", f"/targets/{t['id']}", ok_status=(200, 204, 404))
                return

    def delete_user(self, username):
        for u in self._call("GET", "/users"):
            if u["username"] == username:
                self._call("DELETE", f"/users/{u['id']}", ok_status=(200, 204, 404))
                return

    def delete_role(self, name):
        for r in self._call("GET", "/roles"):
            if r["name"] == name:
                self._call("DELETE", f"/role/{r['id']}", ok_status=(200, 204, 404))
                return

    # ── 고수준: 포털 워커가 부르는 단위 ─────────────────────

    def provision_seat(self, n, fip, ssh_user, expiry=None, password=None):
        """슬롯 n 발급: user student{n} + role slot-{n} + target vm{n} 을 만들고 연결.
        password 미지정 시 랜덤 생성 (반환값으로 전달)."""
        user = self.ensure_user(f"student{n}")
        role = self.ensure_role(f"slot-{n}")
        target = self.ensure_ssh_target(f"vm{n}", host=fip, username=ssh_user)
        self.bind(user["id"], target["id"], role["id"], expiry=expiry)
        return self.set_password(user["id"], password)

    def deprovision_seat(self, n):
        """슬롯 n 회수: target → user → role 순서로 제거."""
        self.delete_target(f"vm{n}")
        self.delete_user(f"student{n}")
        self.delete_role(f"slot-{n}")

    def own_keys(self):
        """Warpgate 자체 SSH 공개키 목록.
        운영계 전환 시 이 키를 OpenStack keypair 로 등록해야 VM 접속 가능."""
        return self._call("GET", "/ssh/own-keys")

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

def get_wg():
    return WarpgateClient()
```

---

## `provisioning/services.py` — 수정

```python
import logging
import os
from datetime import timedelta

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from osclient import get_conn, vm as osvm
from wgclient import get_wg                       # [ADDED]
from .models import Slot, Vm

log = logging.getLogger(__name__)

KEYFILE = os.environ.get("SU_KEYFILE", "/opt/su-portal/sdk-probe-key.pem")
CLAIM_TIMEOUT = timedelta(minutes=10)

# ── 요청 접수 ──────────────────────────────────────────────

def reserve(student_id):
    """빈 슬롯 예약"""
    with transaction.atomic():
        slot = (
            Slot.objects
            .select_for_update(skip_locked=True)
            .filter(status=Slot.FREE)
            .order_by("n")
            .first()
        )
        if slot is None:
            return None

        slot.status = Slot.TAKEN
        slot.save(update_fields=["status"])

        return Vm.objects.create(slot=slot, student_id=student_id)

def request_delete(vm_id):
    """회수 예약"""
    with transaction.atomic():
        rec = Vm.objects.select_for_update().get(pk=vm_id)
        if rec.status != Vm.ACTIVE:
            return None

        rec.status = Vm.DELETING
        rec.claimed_at = None
        rec.claimed_by = ""
        rec.save(update_fields=["status", "claimed_at", "claimed_by", "updated_at"])
        return rec

def request_delete_all():
    """전체 회수 예약"""
    ids = list(
        Vm.objects.filter(status=Vm.ACTIVE)
        .order_by("slot_id")
        .values_list("id", flat=True)
    )
    return [rec for i in ids if (rec := request_delete(i)) is not None]

# ── 작업 실행 ──────────────────────────────────────────────

def claim(worker_id):
    """작업 집기 · 유실분 포함"""
    stale = timezone.now() - CLAIM_TIMEOUT
    with transaction.atomic():
        rec = (
            Vm.objects
            .select_for_update(skip_locked=True)
            .filter(status__in=[Vm.PROVISIONING, Vm.DELETING])
            .filter(Q(claimed_at__isnull=True) | Q(claimed_at__lt=stale))
            .order_by("created_at")
            .first()
        )
        if rec is None:
            return None

        rec.claimed_at = timezone.now()
        rec.claimed_by = worker_id
        rec.save(update_fields=["claimed_at", "claimed_by", "updated_at"])
        return rec

def provision(vm_id):
    """VM 생성 + Warpgate 등록"""
    vm_rec = Vm.objects.get(pk=vm_id)
    conn = get_conn()

    adopted = _reconcile(conn, vm_rec)            # [CHANGED] 입양돼도 WG 등록은 계속 진행

    if not adopted:
        try:
            server = osvm.create(conn, vm_rec.slot_id, KEYFILE)
        except Exception as e:
            _mark_failed(conn, vm_rec, f"{type(e).__name__}: {e}")
            raise
        _mark_active(vm_rec, server.id)

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

    return vm_rec

def deprovision(vm_id):
    """Warpgate 해제 + VM 삭제 · 슬롯 반납"""
    vm_rec = Vm.objects.get(pk=vm_id)
    if vm_rec.status == Vm.DELETED:
        return

    # [ADDED] VM 삭제 전에 Warpgate 접근부터 끊는다 (죽은 target 로 로그인 시도 방지)
    try:
        get_wg().deprovision_seat(vm_rec.slot_id)
    except Exception:
        log.exception("warpgate deprovision failed for vm%s (continuing)", vm_rec.slot_id)

    conn = get_conn()

    if vm_rec.server_id:
        server = conn.compute.find_server(str(vm_rec.server_id))
        if server is not None and server.status != "DELETED":
            osvm.delete(conn, server.id)

    _release(vm_rec)

# ── 내부 ────────────────────────────────────────────────────

def _reconcile(conn, vm_rec):
    """실제 상태 대조 · 기존 VM 입양"""
    name = osvm.name_for(vm_rec.slot_id)
    server = next(
        (s for s in conn.compute.servers(name=name) if s.name == name and s.status != "DELETED"),
        None,
    )
    if server is None:
        return False

    if server.status == "ACTIVE":
        log.info("reconcile: %s already ACTIVE, adopting", name)
        _mark_active(vm_rec, server.id)
        return True

    log.info("reconcile: %s in %s, deleting for retry", name, server.status)
    osvm.delete(conn, server.id)
    return False

def _mark_active(vm_rec, server_id):
    """생성 완료 기록"""
    with transaction.atomic():
        vm_rec.status = Vm.ACTIVE
        vm_rec.server_id = server_id
        vm_rec.save(update_fields=["status", "server_id", "updated_at"])

def _mark_failed(conn, vm_rec, err):
    """실패 기록 · 잔여물 정리"""
    with transaction.atomic():
        vm_rec.status = Vm.FAILED
        vm_rec.error = err[:2000]
        vm_rec.save(update_fields=["status", "error", "updated_at"])

    name = osvm.name_for(vm_rec.slot_id)
    try:
        server = next(
            (s for s in conn.compute.servers(name=name) if s.name == name and s.status != "DELETED"),
            None,
        )
        if server is not None:
            osvm.delete(conn, server.id)
    except Exception:
        log.exception("cleanup failed for %s - slot stays TAKEN", name)
        return

    _free_slot(vm_rec.slot_id)

def _release(vm_rec):
    """회수 기록 · 이력 보존"""
    with transaction.atomic():
        vm_rec.status = Vm.DELETED
        vm_rec.save(update_fields=["status", "updated_at"])

        slot = Slot.objects.select_for_update().get(pk=vm_rec.slot_id)
        slot.status = Slot.FREE
        slot.save(update_fields=["status"])

def _free_slot(n):
    """슬롯 해제"""
    with transaction.atomic():
        slot = Slot.objects.select_for_update().get(pk=n)
        slot.status = Slot.FREE
        slot.save(update_fields=["status"])
```

---

## `osclient/vm.py` — 수정

```python
import base64
import os
import subprocess
import time

USER_DATA = """#cloud-config
users:
  - name: student{n}
    groups: [sudo]
    sudo: ALL=(ALL) NOPASSWD:ALL
    shell: /bin/bash
    ssh_authorized_keys:
      - {pubkey}
      - {wg_pubkey}
"""

def name_for(n):
    return f"vm{n}"

def user_for(n):
    return f"student{n}"

def fip_for(n):
    return os.environ["SU_FIP_PREFIX"] + str(100 + n)

def build_user_data(n, pubkey):
    """관리용 키(pubkey) + Warpgate 자체 키(WG_PUBKEY) 를 함께 주입.
    WG_PUBKEY 가 없으면 Warpgate 가 VM 에 접속할 수 없으므로 즉시 실패시킴.
    값은 wgclient.own_keys() 의 ed25519 public_key 를 .env 에 넣는다."""
    ud = USER_DATA.format(n=n, pubkey=pubkey, wg_pubkey=os.environ["WG_PUBKEY"])
    return base64.b64encode(ud.encode()).decode()

def wait_ssh(host, user, key_path, timeout=300):
    """SSH 도달까지 대기. ACTIVE는 준비 완료 신호가 아님."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = subprocess.run(
            ["ssh", "-i", key_path,
             "-o", "StrictHostKeyChecking=no",
             "-o", "UserKnownHostsFile=/dev/null",
             "-o", "ConnectTimeout=3",
             f"{user}@{host}", "true"],
            capture_output=True,
        )
        if r.returncode == 0:
            return
        time.sleep(5)
    raise TimeoutError(f"ssh unreachable: {user}@{host}")

def create(conn, n, key_path):
    """VM 생성 → FIP 연결 → SSH 도달까지. 실패 시 예외를 올림."""
    keypair = os.environ["SU_KEYPAIR"]
    pubkey = conn.compute.get_keypair(keypair).public_key

    server = conn.compute.create_server(
        name=name_for(n),
        image_id=os.environ["SU_IMAGE_ID"],
        flavor_id=os.environ["SU_FLAVOR_ID"],
        networks=[{"uuid": os.environ["SU_NETWORK_ID"]}],
        key_name=keypair,
        security_groups=[{"name": os.environ["SU_SECGROUP"]}],
        user_data=build_user_data(n, pubkey),
    )
    server = conn.compute.wait_for_server(server, status="ACTIVE", wait=600)

    port = next(conn.network.ports(device_id=server.id))
    fip = next(conn.network.ips(floating_ip_address=fip_for(n)))
    conn.network.update_ip(fip, port_id=port.id)

    wait_ssh(fip_for(n), user_for(n), key_path)
    return server

def delete(conn, server_id):
    """포트·FIP는 Neutron이 함께 정리함."""
    conn.compute.delete_server(server_id)
    conn.compute.wait_for_delete(conn.compute.get_server(server_id), wait=300)
```

---

## `.env.example` — 수정

```bash
# 복사해서 /opt/su-portal/.env 로 저장 후 실제 값 입력
# .env 는 절대 커밋하지 않는다 (.gitignore 처리됨)

# --- django ---
DJANGO_SECRET_KEY=change-me
DJANGO_DEBUG=true
# 쉼표 구분. 개발계: 210.94.240.180,localhost,127.0.0.1
DJANGO_ALLOWED_HOSTS=210.94.240.180,localhost,127.0.0.1
# 쉼표 구분. 운영계: https://su-portal.su-cloud.syu.ac.kr
DJANGO_CSRF_TRUSTED_ORIGINS=

# --- openstack (개발계) ---
OS_AUTH_URL=
OS_USERNAME=
OS_PASSWORD=
OS_PROJECT_NAME=
OS_USER_DOMAIN_NAME=Default
OS_PROJECT_DOMAIN_NAME=Default
OS_REGION_NAME=RegionOne
OS_INTERFACE=public
OS_COMPUTE_API_VERSION=2.79
# TODO(운영 전환 전): admin 패스워드 대신 application credential 로 교체

# --- catalog (개발계 .180) ---
SU_IMAGE_ID=
SU_FLAVOR_ID=
SU_NETWORK_ID=
SU_SECGROUP=
SU_KEYPAIR=
SU_FIP_PREFIX=

# --- database ---
DB_NAME=
DB_USER=
DB_PASSWORD=
DB_HOST=127.0.0.1
DB_PORT=5432
# 워커 wait_ssh 용 키 경로 (dev: sdk-probe-key.pem / prod: su-ops.pem)
SU_KEYFILE=/opt/su-portal/sdk-probe-key.pem

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
