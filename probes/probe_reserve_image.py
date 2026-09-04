"""C-3: reserve()가 image 값을 DB에 저장하는지 확인 — rollback."""
import os, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.db import transaction
from provisioning.services import reserve

IMAGE_ID = "3836095d-ec16-4560-81a2-72bf810d5289"

with transaction.atomic():
    vm = reserve("probe", image_id=IMAGE_ID, image_name="su-img-test-1")
    assert vm is not None, "빈 슬롯 없음"
    print(f"vm={vm.id} slot={vm.slot_id} image_id={vm.image_id} name={vm.image_name!r}")
    assert str(vm.image_id) == IMAGE_ID
    assert vm.image_name == "su-img-test-1"

    vm2 = reserve("probe2")
    print(f"vm={vm2.id} image_id={vm2.image_id} name={vm2.image_name!r}")
    assert vm2.image_id is None
    assert vm2.image_name == ""

    transaction.set_rollback(True)

print("OK — rollback 완료")