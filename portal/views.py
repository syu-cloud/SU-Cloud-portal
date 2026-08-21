from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils.dateparse import parse_datetime

from provisioning.models import Slot, Vm
from provisioning import services
from osclient import vm as osvm

STATUS_LIST = [Vm.PROVISIONING, Vm.ACTIVE, Vm.DELETING, Vm.FAILED]


def friendly_label(error: str) -> str:
    e = error.lower()
    if "badrequest" in e or " 400" in e:
        return "잘못된 요청 (설정값 오류)"
    if "unauthorized" in e or " 401" in e:
        return "인증 만료"
    if "forbidden" in e or " 403" in e:
        return "자원 한도 초과 (Quota)"
    if "notfound" in e or " 404" in e:
        return "리소스 없음 (image/flavor/network 설정 오류)"
    if "conflict" in e or " 409" in e:
        return "IP 충돌" if ("fip" in e or "floating" in e) else "이름/상태 충돌"
    if "novalidhost" in e:
        return "배치 실패 (가용 호스트 없음)"
    if "resourcefailure" in e or " error" in e:
        return "생성 실패 (자원 부족 또는 빌드 오류)"
    if "resourcetimeout" in e or "timeout" in e:
        return "접속 확인 시간 초과" if "ssh" in e else "생성 시간 초과"
    if "neutron" in e or "floating" in e or "port" in e:
        return "네트워크/IP 할당 실패"
    return "실패"


FAILED_DESCRIPTIONS = {
    "잘못된 요청 (설정값 오류)": "image·flavor·network 설정값에 문제가 있어요. 운영자 확인이 필요해요.",
    "인증 만료": "작업 중 OpenStack 인증이 만료됐어요. 운영자 확인이 필요해요.",
    "자원 한도 초과 (Quota)": "할당된 자원(인스턴스/코어/IP) 한도를 초과했어요.",
    "리소스 없음 (image/flavor/network 설정 오류)": "설정된 flavor·image·network를 찾을 수 없어요. 운영자 확인이 필요해요.",
    "IP 충돌": "지정된 FIP가 이미 다른 VM에서 사용 중이에요.",
    "이름/상태 충돌": "같은 이름의 서버가 이미 존재하거나 상태가 충돌했어요.",
    "배치 실패 (가용 호스트 없음)": "지금 배치할 수 있는 서버 자원이 없어요.",
    "생성 실패 (자원 부족 또는 빌드 오류)": "서버 생성 중 오류가 발생했어요. 운영자 확인이 필요해요.",
    "생성 시간 초과": "VM이 정해진 시간 안에 준비되지 못했어요.",
    "접속 확인 시간 초과": "VM은 만들어졌지만 접속 확인이 시간 내 되지 않았어요.",
    "네트워크/IP 할당 실패": "네트워크 또는 외부 IP 연결에 문제가 있었어요.",
    "실패": "원인을 특정하지 못했어요. 아래 원본 로그를 확인해주세요.",
}


def index(request):
    return redirect("login")

@login_required
def list_view(request):
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "delete_all":
            services.request_delete_all()
            from django.utils import timezone
            request.session["hide_failed_before"] = timezone.now().isoformat()
        elif action == "delete_selected":
            for vid in request.POST.getlist("vm_ids"):
                services.request_delete(int(vid))
        return redirect("portal:list")

    all_vms = Vm.objects.exclude(status=Vm.DELETED).order_by("slot_id")

    hide_before = request.session.get("hide_failed_before")
    if hide_before:
        cutoff = parse_datetime(hide_before)
        all_vms = all_vms.exclude(status=Vm.FAILED, created_at__lt=cutoff)

    status_counts = {s: 0 for s in STATUS_LIST}
    for v in all_vms:
        status_counts[v.status] = status_counts.get(v.status, 0) + 1
    total_count = all_vms.count()

    status_filter = request.GET.get("status", "")
    vms = all_vms.filter(status=status_filter) if status_filter else all_vms

    q = request.GET.get("q", "").strip()
    if q:
        ql = q.lower()
        matched_ids = [
            v.id for v in vms
            if ql in osvm.name_for(v.slot_id).lower()
            or q in osvm.fip_for(v.slot_id)
            or ql in osvm.user_for(v.slot_id).lower()
            or q == str(v.slot_id)
        ]
        vms = vms.filter(id__in=matched_ids)

    rows = []
    for v in vms:
        row = {"vm": v, "name": osvm.name_for(v.slot_id)}
        if v.status == Vm.PROVISIONING:
            row["fip"] = "—"
            row["user"] = "—"
        else:
            row["fip"] = osvm.fip_for(v.slot_id)
            row["user"] = osvm.user_for(v.slot_id)
        if v.status == Vm.FAILED:
            label = friendly_label(v.error or "")
            row["fail_label"] = label
            row["fail_desc"] = FAILED_DESCRIPTIONS.get(label, FAILED_DESCRIPTIONS["실패"])
        rows.append(row)

    taken = Slot.objects.filter(status=Slot.TAKEN).count()
    free = Slot.objects.filter(status=Slot.FREE).count()
    strip_total = status_counts[Vm.ACTIVE] + status_counts[Vm.PROVISIONING] + status_counts[Vm.FAILED]

    return render(request, "portal/list.html", {
        "rows": rows,
        "status_counts": status_counts,
        "total_count": total_count,
        "status_filter": status_filter,
        "q": q,
        "taken": taken,
        "free": free,
        "total": 45,
        "show_strip": status_counts[Vm.PROVISIONING] > 0,
        "strip_total": strip_total,
    })

@login_required
def create_view(request):
    if request.method != "POST":
        return redirect("portal:list")

    free = Slot.objects.filter(status=Slot.FREE).count()
    try:
        count = int(request.POST.get("count", 0))
    except ValueError:
        count = 0
    count = max(0, min(count, free))

    made = 0
    for _ in range(count):
        if services.reserve(""):
            made += 1

    if made:
        messages.success(request, f"{made}대 생성 요청이 접수되었습니다.")
    else:
        messages.error(request, "생성 가능한 여유 슬롯이 없습니다.")

    return redirect("portal:list")