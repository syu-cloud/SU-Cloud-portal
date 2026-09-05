from django.db import models


class Slot(models.Model):
    """1~45 고정. 예약 대상이며 재사용됨."""

    FREE = "FREE"
    TAKEN = "TAKEN"
    STATUS = [(FREE, FREE), (TAKEN, TAKEN)]

    n = models.PositiveSmallIntegerField(primary_key=True)
    status = models.CharField(max_length=8, choices=STATUS, default=FREE)

    class Meta:
        indexes = [models.Index(fields=["status", "n"])]

    def __str__(self):
        return f"slot{self.n}({self.status})"


class Vm(models.Model):
    """append-only 이력. 회수해도 삭제하지 않음."""

    PROVISIONING = "PROVISIONING"
    ACTIVE = "ACTIVE"
    FAILED = "FAILED"
    DELETED = "DELETED"
    DELETING = "DELETING"
    STATUS = [(s, s) for s in (PROVISIONING, ACTIVE, DELETING, FAILED, DELETED)]

    slot = models.ForeignKey(Slot, on_delete=models.PROTECT, related_name="vms")
    student_id = models.CharField(max_length=32, blank=True)

    image_id = models.UUIDField(null=True, blank=True)
    image_name = models.CharField(max_length=255, blank=True)
    
    status = models.CharField(max_length=16, choices=STATUS, default=PROVISIONING)

    server_id = models.UUIDField(null=True, blank=True)
    error = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    claimed_at = models.DateTimeField(null=True, blank=True)
    claimed_by = models.CharField(max_length=64, blank=True)

    class Meta:
        indexes = [models.Index(fields=["status", "created_at"])]

    def __str__(self):
        return f"vm{self.slot_id}/{self.student_id}({self.status})"


class VmFailure(models.Model):
    """FAILED VM의 잔여 자원 정리 및 확인 상태."""

    CLEANED = "CLEANED"
    CLEANUP_FAILED = "CLEANUP_FAILED"

    CLEANUP_STATUS = [
        (CLEANED, CLEANED),
        (CLEANUP_FAILED, CLEANUP_FAILED),
    ]

    vm = models.OneToOneField(
        Vm,
        on_delete=models.PROTECT,
        related_name="failure",
    )

    # FAILED 이후 잔여 자원 정리 결과
    cleanup_status = models.CharField(
        max_length=16,
        choices=CLEANUP_STATUS,
    )

    # 잔여 자원 정리 중 발생한 오류
    cleanup_error = models.TextField(
        blank=True,
        default="",
    )

    # cleanup 완료된 FAILED 건을 사용자가 확인한 시각
    # 값이 있으면 일반 VM 목록에서 제외
    acknowledged_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    def __str__(self):
        return f"VmFailure(vm={self.vm_id}, cleanup={self.cleanup_status})"