import logging
from datetime import timedelta

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from osclient import get_conn, vm as osvm
from wgclient import get_wg                       # [ADDED]
from .models import Slot, Vm

log = logging.getLogger(__name__)

KEYFILE = "/opt/su-portal/su-ops.pem"
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
        (s for s in conn.compute.servers(name=name) if s.status != "DELETED"),
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
            (s for s in conn.compute.servers(name=name) if s.status != "DELETED"),
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