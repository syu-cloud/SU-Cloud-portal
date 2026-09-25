"""REST API용 Application Service."""

from catalog import services as catalog_service
from osclient import vm as osvm
from provisioning import services as prov
from provisioning.failures import FAILED_DESCRIPTIONS, friendly_label
from provisioning.models import Vm, VmFailure


VALID_VM_STATUSES = (
    Vm.ACTIVE,
    Vm.PROVISIONING,
    Vm.DELETING,
    Vm.FAILED,
)


class ImageNotAvailable(Exception):
    pass


class InsufficientCapacity(Exception):
    pass


def create_vms(count, image_id):
    """검증된 생성 요청을 기존 provisioning 예약 계층에 접수한다."""
    image = catalog_service.get_portal_image(image_id)

    if image is None:
        raise ImageNotAvailable

    # 사전 검사 시점에 요청 수 전체를 수용할 수 없으면 0대 접수한다.
    if count > prov.free_slot_count():
        raise InsufficientCapacity

    accepted = []

    for _ in range(count):
        vm = prov.reserve(
            "",
            image_id=image["id"],
            image_name=image["name"],
        )

        # 사전 검사 이후 동시 요청으로 Slot이 소진될 수 있다.
        if vm is None:
            break

        accepted.append({
            "id": vm.id,
            "slot_id": vm.slot_id,
            "status": vm.status,
        })

    if not accepted:
        raise InsufficientCapacity

    return {
        "requested_count": count,
        "accepted_count": len(accepted),
        "items": accepted,
    }


def reclaim_vms(scope, vm_ids=None):
    """기존 provisioning 회수 로직을 호출하고 건별 처리 결과를 반환한다."""
    if scope == "all":
        vm_ids = [
            vm.id
            for vm in prov.list_visible_vms()
            if _is_reclaimable(vm)
        ]
    else:
        vm_ids = list(vm_ids or [])

    results = []
    accepted = 0
    active_accepted = 0

    for vm_id in vm_ids:
        vm = Vm.objects.filter(pk=vm_id).first()

        if vm is None:
            results.append({
                "vm_id": vm_id,
                "accepted": False,
                "code": "VM_NOT_FOUND",
            })
            continue

        was_active = vm.status == Vm.ACTIVE
        reclaimed = prov.request_reclaim(vm_id)

        if reclaimed is None:
            results.append({
                "vm_id": vm_id,
                "accepted": False,
                "code": "VM_NOT_RECLAIMABLE",
            })
            continue

        accepted += 1

        if was_active:
            active_accepted += 1

        results.append({
            "vm_id": vm_id,
            "accepted": True,
        })

    payload = {
        "summary": {
            "requested": len(vm_ids),
            "accepted": accepted,
            "rejected": len(vm_ids) - accepted,
        },
        "results": results,
    }

    return payload, active_accepted


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
            "reclaimable_total": sum(
                1
                for vm in all_vms
                if _is_reclaimable(vm)
            ),
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


def _is_reclaimable(vm):
    """현재 Portal 정책상 사용자가 회수 처리할 수 있는 VM인지 판단한다."""
    if vm.status == Vm.ACTIVE:
        return True

    if vm.status != Vm.FAILED:
        return False

    failure = getattr(vm, "failure", None)

    return (
        failure is not None
        and failure.cleanup_status == VmFailure.CLEANED
    )


def _serialize_vm(vm):
    """Vm 모델을 REST API Contract의 primitive JSON 구조로 변환한다."""
    fip = None
    user = None

    # 기존 Portal 동작을 유지한다.
    if vm.status != Vm.PROVISIONING:
        fip = osvm.fip_for(vm.slot_id)
        user = osvm.user_for(vm.slot_id)

    can_reclaim = _is_reclaimable(vm)
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


# ══ Flavor 조회 ════════════════════════════════════════

def list_flavors():
    """현재 Portal에서 사용하는 고정 Flavor 정보를 반환한다."""
    flavor = catalog_service.get_portal_flavor()

    if flavor is None:
        raise RuntimeError("configured flavor not found")

    return {
        "items": [flavor],
    }
