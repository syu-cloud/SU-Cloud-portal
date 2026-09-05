"""portal 화면용 서비스 레이어. provisioning 조회 결과를 화면 데이터로 조립한다."""

import logging

from provisioning import services as prov
from osclient import vm as osvm
from portal.labels import FAILED_DESCRIPTIONS
from catalog import services as catalog_service

log = logging.getLogger(__name__)


# provisioning과 공유하는 VM 상태 계약.
# portal은 provisioning.models를 직접 import하지 않는다.
STATUS_PROVISIONING = "PROVISIONING"
STATUS_ACTIVE = "ACTIVE"
STATUS_DELETING = "DELETING"
STATUS_FAILED = "FAILED"

STATUS_LIST = [
    STATUS_PROVISIONING,
    STATUS_ACTIVE,
    STATUS_DELETING,
    STATUS_FAILED,
]


# ══ 목록 화면 진입점 ══════════════════════════════════════

def list_page_data(status_filter="", q=""):
    """목록 화면에 필요한 데이터를 조회하고 화면용 데이터로 조립한다."""
    all_vms = visible_vms()

    status_counts = count_by_status(all_vms)
    total_count = len(all_vms)

    vms = apply_status_filter(all_vms, status_filter)
    vms = apply_search(vms, q)

    slots = slot_summary()

    strip_total = (
        status_counts[STATUS_ACTIVE]
        + status_counts[STATUS_PROVISIONING]
        + status_counts[STATUS_FAILED]
    )

    return {
        "rows": build_rows(vms),
        "status_counts": status_counts,
        "total_count": total_count,
        "status_filter": status_filter,
        "q": q,
        "taken": slots["taken"],
        "free": slots["free"],
        "total": slots["total"],
        "show_strip": status_counts[STATUS_PROVISIONING] > 0,
        "strip_total": strip_total,
        "images": image_catalog(),
    }


# ── 조회 요청 ─────────────────────────

def visible_vms():
    """노출 대상 VM 조회를 provisioning 계층에 요청한다."""
    return prov.list_visible_vms()


def slot_summary():
    """슬롯 사용 현황 조회를 provisioning 계층에 요청한다."""
    return prov.slot_summary()


def free_slot_count():
    """사용 가능한 슬롯 수 조회를 provisioning 계층에 요청한다."""
    return prov.free_slot_count()


# ── 집계 ─────────────────────────

def count_by_status(vms):
    """상태 필터 칩에 표시할 상태별 개수"""
    counts = {s: 0 for s in STATUS_LIST}

    for v in vms:
        counts[v.status] = counts.get(v.status, 0) + 1

    return counts


# ── 필터 · 검색 ─────────────────────────

def apply_status_filter(vms, status_filter):
    """상태 칩 선택 시 해당 상태만 표시한다. 빈 값이면 전체."""
    if not status_filter:
        return vms

    return [
        v
        for v in vms
        if v.status == status_filter
    ]


def apply_search(vms, q):
    """이름 / FIP / 계정 / 슬롯번호를 검색한다.

    VM 목록은 provisioning 계층에서 이미 조회된 상태이므로
    portal에서는 추가 ORM 조회 없이 화면용 검색만 수행한다.
    """
    if not q:
        return vms

    ql = q.lower()

    return [
        v
        for v in vms
        if ql in osvm.name_for(v.slot_id).lower()
        or q in osvm.fip_for(v.slot_id)
        or ql in osvm.user_for(v.slot_id).lower()
        or q == str(v.slot_id)
    ]


# ── 화면용 조립 ─────────────────────────

def build_rows(vms):
    """테이블 행 조립. 상태에 따라 화면 표시용 정보를 구성한다."""
    rows = []

    for v in vms:
        row = {
            "vm": v,
            "name": osvm.name_for(v.slot_id),
            "can_reclaim": v.status == STATUS_ACTIVE,
        }

        if v.status == STATUS_PROVISIONING:
            row["fip"] = "—"
            row["user"] = "—"
        else:
            row["fip"] = osvm.fip_for(v.slot_id)
            row["user"] = osvm.user_for(v.slot_id)

        if v.status == STATUS_FAILED:
            label = friendly_label(v.error or "")

            row["fail_label"] = label
            row["fail_desc"] = FAILED_DESCRIPTIONS.get(
                label,
                FAILED_DESCRIPTIONS["실패"],
            )

            failure = getattr(v, "failure", None)

            row["can_reclaim"] = (
                failure is not None
                and failure.cleanup_status == failure.CLEANED
            )

        rows.append(row)

    return rows


def friendly_label(error: str) -> str:
    """워커가 남긴 예외 문자열을 FAILED 팝오버용 라벨로 변환"""
    e = error.lower()

    if "badrequest" in e:
        return "잘못된 요청 (설정값 오류)"

    if " 401" in e:
        return "인증 만료"

    if "forbidden" in e:
        return "자원 한도 초과 (Quota)"

    if "notfound" in e or " 404" in e:
        if "/servers/" in e:
            return "VM 인스턴스 소실"
        return "리소스 없음 (image/flavor/network 설정 오류)"

    if "conflict" in e or " 409" in e:
        return "IP 충돌" if ("fip" in e or "floating" in e) else "이름/상태 충돌"

    if "resourcefailure" in e:
        return "생성 실패 (자원 부족 또는 빌드 오류)"

    if "resourcetimeout" in e or "timeout" in e:
        return "접속 확인 시간 초과" if "ssh" in e else "생성 시간 초과"

    if "stopiteration" in e:
        return "포트/FIP 조회 실패"

    if "neutron" in e or "floating" in e or "port" in e:
        return "네트워크/IP 할당 실패"

    return "실패"


# ══ 생성 화면 보조 ══════════════════════════════════════

def image_catalog():
    """생성 화면용 Image 목록."""
    try:
        return catalog_service.list_portal_images()
    except Exception:
        log.exception("image catalog lookup failed")
        return []
