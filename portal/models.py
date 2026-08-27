from django.db import models


class DismissedFailure(models.Model):
    """
    [Phase 0.5 임시 해결책]
    FAILED VM을 화면에서 숨기는 기록. 세션 기반의 문제(로그아웃 시 초기화)를
    당장 해결하기 위한 임시 테이블. Vm 원본은 건드리지 않음.

    TODO(Phase 1): provisioning.Vm.dismissed_at 필드로 이관 예정 (협의 필요).
    이관되면 이 모델은 삭제.
    """
    vm_id = models.IntegerField(unique=True)
    dismissed_at = models.DateTimeField(auto_now_add=True)