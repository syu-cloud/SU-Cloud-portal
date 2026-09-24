"""REST API용 Application Service."""

from catalog import services as catalog_service
from osclient import vm as osvm
from portal.labels import FAILED_DESCRIPTIONS
from portal.services import friendly_label
from provisioning import services as prov
from provisioning.models import Vm, VmFailure


VALID_VM_STATUSES = (
    Vm.ACTIVE,
    Vm.PROVISIONING,
    Vm.DELETING,
    Vm.FAILED,
)


def list_vms(status_filter="", q=""):
    """VM 목록과 검색·필터 적용 전 전체 현황을 반환한다."""
    if status_filter and status_filter not in VALID_VM_STATUSES:
        raise ValueError("unsupported status filter")

    # DELETED와 acknowledged FAILED는 provisioning 계층에서 제외된다.
    all_vms = prov.list_visible_vms()

    # summary는 검색·필터 적용 전 전체 Portal 현황이다.
    status_counts = {status: 0 for status in VALID_VM_STATUSES}

    for vm in all_vms:
        if vm.status in status_counts:
            status_counts[vm.status] += 1

    # items에만 status / q 조건을 적용한다.
    filtered_vms = all_vms

    if status_filter:
        filtered_vms = [
            vm
            for vm in filtered_vms
            if vm.status == status_filter
        ]

    if q:
        filtered_vms = [
            vm
            for vm in filtered_vms
            if _matches_search(vm, q)
        ]

    return {
        "items": [_serialize_vm(vm) for vm in filtered_vms],
        "summary": {
            "visible_total": len(all_vms),
            "status_counts": status_counts,
            "slots": prov.slot_summary(),
        },
    }


def _matches_search(vm, q):
    """기존 Portal과 동일하게 이름·FIP·계정·Slot 번호를 검색한다."""
    q_lower = q.lower()

    return (
        q_lower in osvm.name_for(vm.slot_id).lower()
        or q in osvm.fip_for(vm.slot_id)
        or q_lower in osvm.user_for(vm.slot_id).lower()
        or q == str(vm.slot_id)
    )


def _serialize_vm(vm):
    """Vm 모델을 REST API Contract의 primitive JSON 구조로 변환한다."""
    fip = None
    user = None

    # 기존 Portal 동작을 유지한다.
    if vm.status != Vm.PROVISIONING:
        fip = osvm.fip_for(vm.slot_id)
        user = osvm.user_for(vm.slot_id)

    can_reclaim = vm.status == Vm.ACTIVE
    failure_data = None

    if vm.status == Vm.FAILED:
        failure = getattr(vm, "failure", None)
        cleanup_status = failure.cleanup_status if failure is not None else None

        label = friendly_label(vm.error or "")

        failure_data = {
            "label": label,
            "description": FAILED_DESCRIPTIONS.get(
                label,
                FAILED_DESCRIPTIONS["실패"],
            ),
            "detail": vm.error or None,
            "cleanup_status": cleanup_status,
        }

        can_reclaim = cleanup_status == VmFailure.CLEANED

    return {
        "id": vm.id,
        "slot_id": vm.slot_id,
        "name": osvm.name_for(vm.slot_id),
        "image_name": vm.image_name or None,
        "fip": fip,
        "user": user,
        "status": vm.status,
        "created_at": _iso_utc(vm.created_at),
        "can_reclaim": can_reclaim,
        "failure": failure_data,
    }


def _iso_utc(value):
    """Contract의 UTC ISO 8601 형식으로 변환한다."""
    return value.isoformat().replace("+00:00", "Z")


# ══ Image 조회 ═════════════════════════════════════════

def list_images():
    """Portal에서 사용할 수 있는 Image 목록을 API 형식으로 반환한다."""
    images = catalog_service.list_portal_images()

    return {
        "items": [
            {
                "id": image["id"],
                "name": image["name"],
            }
            for image in images
        ],
    }
