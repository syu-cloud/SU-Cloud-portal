"""portal 읽기 경로 서비스 레이어. 조회·집계·조립을 HTTP 와 분리."""

import logging

from provisioning.models import Slot, Vm
from osclient import vm as osvm
from portal.labels import FAILED_DESCRIPTIONS
from catalog import services as catalog_service

log = logging.getLogger(__name__)

STATUS_LIST = [Vm.PROVISIONING, Vm.ACTIVE, Vm.DELETING, Vm.FAILED]


# ══ 목록 화면 진입점 ══════════════════════════════════════
# 아래 하위 함수들을 조회 → 집계 → 필터 → 검색 → 조립 순으로 호출한다.

def list_page_data(status_filter="", q=""):
    """목록 화면에 필요한 데이터 전부. 반환 형태 = API 응답 스키마 후보"""
    all_vms = visible_vms()
    status_counts = count_by_status(all_vms)
    total_count = all_vms.count()

    vms = apply_status_filter(all_vms, status_filter)
    vms = apply_search(vms, q)

    slots = slot_summary()
    strip_total = (
        status_counts[Vm.ACTIVE]
        + status_counts[Vm.PROVISIONING]
        + status_counts[Vm.FAILED]
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
        "show_strip": status_counts[Vm.PROVISIONING] > 0,
        "strip_total": strip_total,
        "images": image_catalog(),
    }


# ── 조회 ─────────────────────────

def visible_vms():
    """노출 대상 VM. DELETED 이력과 확인 완료된 FAILED 건은 제외한다."""
    return (
        Vm.objects
        .exclude(status=Vm.DELETED)
        .exclude(failure__acknowledged_at__isnull=False)
        .select_related("failure")
        .order_by("slot_id")
    )


# ── 집계 ─────────────────────────

def count_by_status(vms):
    """상태 필터 칩에 표시할 상태별 개수"""
    counts = {s: 0 for s in STATUS_LIST}
    for v in vms:
        counts[v.status] = counts.get(v.status, 0) + 1
    return counts


def slot_summary():
    """슬롯 사용 현황. 목록 상단과 생성 모달 진행바에서 사용"""
    taken = Slot.objects.filter(status=Slot.TAKEN).count()
    free = Slot.objects.filter(status=Slot.FREE).count()
    return {"taken": taken, "free": free, "total": taken + free}


# ── 필터 · 검색 ─────────────────────────

def apply_status_filter(vms, status_filter):
    """상태 칩 선택 시 해당 상태만. 빈 값이면 전체"""
    return vms.filter(status=status_filter) if status_filter else vms


def apply_search(vms, q):
    """이름 / FIP / 계정 / 슬롯번호 검색.
    앞 셋은 slot_id 로부터 계산되는 값이라 DB 필터가 불가해 Python 으로 순회한다"""
    if not q:
        return vms
    ql = q.lower()
    matched_ids = [
        v.id for v in vms
        if ql in osvm.name_for(v.slot_id).lower()
        or q in osvm.fip_for(v.slot_id)
        or ql in osvm.user_for(v.slot_id).lower()
        or q == str(v.slot_id)
    ]
    return vms.filter(id__in=matched_ids)


# ── 화면용 조립 ─────────────────────────

def build_rows(vms):
    """테이블 행 조립. 상태에 따라 화면 표시용 정보를 구성한다."""
    rows = []

    for v in vms:
        row = {
            "vm": v,
            "name": osvm.name_for(v.slot_id),
            "can_reclaim": v.status == Vm.ACTIVE,
        }

        if v.status == Vm.PROVISIONING:
            row["fip"] = "—"
            row["user"] = "—"
        else:
            row["fip"] = osvm.fip_for(v.slot_id)
            row["user"] = osvm.user_for(v.slot_id)

        if v.status == Vm.FAILED:
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

def free_slot_count():
    """생성 요청 개수 상한. create_view 에서 입력값 clamp 에 사용"""
    return Slot.objects.filter(status=Slot.FREE).count()
