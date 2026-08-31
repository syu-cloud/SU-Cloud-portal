"""portal 화면 진입점. HTTP 처리만 담당."""

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from provisioning.models import Vm
from provisioning import services as prov
from portal import services


# ── 진입점 / 로그인 분기 ─────────────────────────

def index(request):
    """로그인 상태면 목록으로, 아니면 로그인 화면으로"""
    if request.user.is_authenticated:
        return redirect("portal:list")
    return redirect("login")


# ── 생성 ─────────────────────────

@login_required
def create_view(request):
    """생성 모달 제출 처리. 여유 슬롯을 넘는 요청은 상한으로 잘라낸다"""
    if request.method != "POST":
        return redirect("portal:list")

    free = services.free_slot_count()
    try:
        count = int(request.POST.get("count", 0))
    except ValueError:
        count = 0
    count = max(0, min(count, free))

    made = sum(1 for _ in range(count) if prov.reserve(""))

    if made:
        messages.success(request, f"{made}대 생성 요청이 접수되었습니다.")
    else:
        messages.error(request, "생성 가능한 여유 슬롯이 없습니다.")

    return redirect("portal:list")


# ── 조회 · 회수 ─────────────────────────
# 목록 화면(GET)과 회수 처리(POST)가 같은 URL 을 쓴다.
# 회수 폼이 목록 안에 있어 분리하면 PRG 리다이렉트 경로가 늘어나므로 한 뷰로 유지.

@login_required
def list_view(request):
    """GET = 목록 조회 / POST = 선택·전체 회수"""
    if request.method == "POST":
        return _handle_reclaim(request)

    ctx = services.list_page_data(
        status_filter=request.GET.get("status", ""),
        q=request.GET.get("q", "").strip(),
    )
    return render(request, "portal/list.html", ctx)


def _handle_reclaim(request):
    """회수 처리. FAILED 는 삭제할 자원이 없어 숨김으로 대체한다"""
    action = request.POST.get("action")

    if action == "delete_all":
        prov.request_delete_all()
        services.dismiss_all_failed()

    elif action == "delete_selected":
        for vid in request.POST.getlist("vm_ids"):
            vid = int(vid)
            rec = Vm.objects.filter(pk=vid).first()
            if rec and rec.status == Vm.FAILED:
                services.dismiss(vid)
            else:
                prov.request_delete(vid)

    return redirect("portal:list")