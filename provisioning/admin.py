from django.contrib import admin, messages

from osclient import vm as osvm

from . import services
from .models import Slot, Vm


# ── VM 현황 ────────────────────────────────────────────────────
@admin.register(Slot)
class SlotAdmin(admin.ModelAdmin):
    list_display = ("n", "status", "fip", "account")
    list_filter = ("status",)
    ordering = ("n",)
    actions = ["provision_selected", "reclaim_selected"]

    @admin.display(description="FIP")
    def fip(self, obj):
        return osvm.fip_for(obj.n)

    @admin.display(description="계정")
    def account(self, obj):
        return osvm.user_for(obj.n)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.action(description="선택한 개수만큼 VM 생성 요청")
    def provision_selected(self, request, queryset):
        n = queryset.filter(status=Slot.FREE).count()
        if n == 0:
            self.message_user(request, "빈 슬롯이 없음", messages.WARNING)
            return
        made = [r for _ in range(n) if (r := services.reserve(""))]
        self.message_user(request, f"{len(made)}건 예약. 워커가 처리함", messages.SUCCESS)

    @admin.action(description="선택한 슬롯의 VM 회수")
    def reclaim_selected(self, request, queryset):
        vms = Vm.objects.filter(slot__in=queryset, status=Vm.ACTIVE)
        done = sum(1 for v in vms if services.request_delete(v.id))
        self.message_user(request, f"{done}건 회수 예약", messages.SUCCESS)


# ── VM Log ────────────────────────────────────────────────────
@admin.register(Vm)
class VmAdmin(admin.ModelAdmin):
    list_display = ("id", "slot_id", "status", "fip", "server_id",
                    "claimed_by", "created_at", "updated_at")
    list_filter = ("status",)
    ordering = ("-updated_at",)
    readonly_fields = [f.name for f in Vm._meta.fields]

    @admin.display(description="FIP")
    def fip(self, obj):
        return osvm.fip_for(obj.slot_id)

    def has_add_permission(self, request):
        return False