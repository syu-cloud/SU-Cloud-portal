"""C-1: create() image_id 전달 검증 — 실제 VM 생성 없음."""
import os
from types import SimpleNamespace
from osclient import vm as osvm

captured = {}


class FakeCompute:
    def get_keypair(self, name):
        return SimpleNamespace(public_key="ssh-rsa TEST")

    def create_server(self, **kwargs):
        captured["image_id"] = kwargs["image_id"]
        raise RuntimeError("STOP")


class FakeConn:
    compute = FakeCompute()


for k, v in {
    "SU_KEYPAIR": "test-key",
    "SU_IMAGE_ID": "fallback-image",
    "SU_FLAVOR_ID": "test-flavor",
    "SU_NETWORK_ID": "test-network",
    "SU_SECGROUP": "test-sg",
    "WG_PUBKEY": "ssh-ed25519 TEST",
}.items():
    os.environ.setdefault(k, v)


def run(**kw):
    captured.clear()
    try:
        osvm.create(FakeConn(), 1, "/tmp/not-used", **kw)
    except RuntimeError as e:
        if str(e) != "STOP":
            raise
    assert "image_id" in captured, "create_server 미도달"
    return captured["image_id"]


print("명시 image_id  →", run(image_id="selected-image"))
print("기존 호출 형태 →", run())

assert run(image_id="selected-image") == "selected-image"
assert run() == os.environ["SU_IMAGE_ID"]
print("OK")