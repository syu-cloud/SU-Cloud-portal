"""Warpgate Admin API 클라이언트.

설계 원칙 (osclient 의 _reconcile 과 동일 철학):
- 서버가 진실. 로컬 상태 파일 없음.
- 모든 생성은 ensure_* 로 멱등. 몇 번을 재실행해도 같은 결과로 수렴.
- 워커 재시도(claim timeout 회수)에 안전.

엔드포인트 경로는 wg_verify.py 로 검증한 계약을 따른다.
경로가 다르면 이 파일의 상수만 고치면 됨.
"""
import os
from pathlib import Path
import secrets

import requests
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


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