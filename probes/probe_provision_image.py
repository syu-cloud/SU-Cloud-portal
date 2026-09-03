"""C-4: Vm.image_id가 provision()을 거쳐 osvm.create()에 전달되는지 검증.
OpenStack / Warpgate 호출 없이 전체 DB 변경은 rollback.
"""
import os
import django
import uuid

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from types import SimpleNamespace
from unittest.mock import patch
from django.db import transaction

from provisioning import services
from provisioning.services import reserve


IMAGE_ID = "3836095d-ec16-4560-81a2-72bf810d5289"
SERVER_ID = str(uuid.uuid4())

captured = {}


class FakeCompute:
    def servers(self, **kwargs):
        return iter([])


class FakeConn:
    compute = FakeCompute()


class FakeWg:
    def provision_seat(self, **kwargs):
        return "test-password"


def fake_create(conn, n, key_path, image_id=None):
    captured["image_id"] = image_id
    captured["slot"] = n
    return SimpleNamespace(id=SERVER_ID)


with transaction.atomic():
    vm = reserve("probe", image_id=IMAGE_ID, image_name="su-img-test-1")
    assert vm is not None, "빈 슬롯 없음"

    with patch.object(services, "get_conn", return_value=FakeConn()), \
         patch.object(services.osvm, "create", side_effect=fake_create), \
         patch.object(services, "get_wg", return_value=FakeWg()):

        result = services.provision(vm.id)

    print("DB image_id       :", vm.image_id)
    print("전달된 image_id   :", captured.get("image_id"))
    print("slot              :", captured.get("slot"))
    print("status            :", result.status)

    assert captured["image_id"] == IMAGE_ID
    assert captured["slot"] == vm.slot_id
    assert result.status == "ACTIVE"

    transaction.set_rollback(True)

print("OK — rollback 완료")