from django.db import models


class ImageBuild(models.Model):
    CREATING = "CREATING"
    READY = "READY"
    SNAPSHOTTING = "SNAPSHOTTING"
    CANCELING = "CANCELING"
    CANCELED = "CANCELED"
    PUBLISHED = "PUBLISHED"
    FAILED = "FAILED"

    STATUS_CHOICES = [
        (CREATING, "제작 환경 준비 중"),
        (READY, "설정 가능"),
        (SNAPSHOTTING, "이미지 생성 중"),
        (CANCELING, "제작 취소 중"),
        (CANCELED, "제작 취소"),
        (PUBLISHED, "사용 가능"),
        (FAILED, "실패"),
    ]

    name = models.CharField(max_length=255)

    base_image_id = models.UUIDField()
    base_image_name = models.CharField(max_length=255)

    server_id = models.UUIDField(null=True, blank=True)
    glance_image_id = models.UUIDField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=CREATING,
    )

    error = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.status})"