import fcntl
import os
import time

from django.core.management.base import BaseCommand

from imagebuild import services
from imagebuild.models import ImageBuild


LOCK_FILE = "/tmp/su-imagebuild-worker.lock"

WORK_STATUSES = [
    ImageBuild.CREATING,
    ImageBuild.SNAPSHOTTING,
    ImageBuild.CANCELING,
]


class Command(BaseCommand):
    help = (
        "ImageBuild 생성, 발행, 취소 요청을 "
        "처리하는 단일 worker"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--interval",
            type=float,
            default=3.0,
        )

    def handle(self, *args, **opts):
        """단일 worker lock을 획득한 뒤 작업을 계속 처리한다."""

        with open(LOCK_FILE, "w") as lock_file:
            if not self._acquire_lock(lock_file):
                return

            lock_file.write(str(os.getpid()))
            lock_file.flush()

            self.stdout.write(
                self.style.SUCCESS(
                    "imagebuild worker started "
                    f"(pid={os.getpid()})"
                )
            )

            self._run_loop(
                interval=opts["interval"]
            )

    def _acquire_lock(self, lock_file):
        """같은 호스트에서 ImageBuild worker가 하나만 실행되게 한다."""

        try:
            fcntl.flock(
                lock_file.fileno(),
                fcntl.LOCK_EX
                | fcntl.LOCK_NB,
            )

        except BlockingIOError:
            self.stdout.write(
                self.style.WARNING(
                    "imagebuild worker is already running"
                )
            )
            return False

        return True

    def _run_loop(self, interval):
        """처리할 ImageBuild를 조회해 상태에 맞는 작업을 실행한다."""

        while True:
            build = self._next_build()

            if build is None:
                time.sleep(interval)
                continue

            self.stdout.write(
                f"build #{build.id} "
                f"{build.name} "
                f"{build.status} "
                "processing"
            )

            try:
                result = self._process_build(
                    build
                )

                self.stdout.write(
                    self.style.SUCCESS(
                        f"build #{build.id} "
                        f"{result.status}"
                    )
                )

            except Exception as error:
                self.stdout.write(
                    self.style.ERROR(
                        f"build #{build.id} "
                        "FAILED: "
                        f"{type(error).__name__}: "
                        f"{error}"
                    )
                )

    def _next_build(self):
        """가장 오래된 처리 대기 작업 1건을 반환한다."""

        return (
            ImageBuild.objects
            .filter(status__in=WORK_STATUSES)
            .order_by("created_at")
            .first()
        )

    def _process_build(self, build):
        """현재 상태에 맞는 ImageBuild service를 호출한다."""

        if build.status == ImageBuild.CREATING:
            return services.provision(
                build.id
            )

        if build.status == ImageBuild.SNAPSHOTTING:
            return services.publish(
                build.id
            )

        if build.status == ImageBuild.CANCELING:
            return services.cancel(
                build.id
            )

        raise ValueError(
            f"unsupported image build status: "
            f"{build.status}"
        )