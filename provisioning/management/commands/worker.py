import os
import signal
import socket
import time

from django.core.management.base import BaseCommand

from provisioning import services
from provisioning.models import Vm


class Command(BaseCommand):
    help = "PROVISIONING / DELETING 상태의 Vm 레코드를 집어 처리함"

    def add_arguments(self, parser):
        parser.add_argument("--interval", type=float, default=3.0)

    def handle(self, *args, **opts):
        if os.environ.get("SU_WORKER_ENABLED", "false").lower() != "true":
            self.stderr.write(
                "Worker is disabled in this environment "
                "(SU_WORKER_ENABLED=false)."
            )
            return

        worker_id = f"{socket.gethostname()}-{os.getpid()}"
        stopping = False

        def stop(signum, frame):
            nonlocal stopping
            stopping = True

        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)

        self.stdout.write(f"worker {worker_id} started")

        while not stopping:
            rec = services.claim(worker_id)
            if rec is None:
                time.sleep(opts["interval"])
                continue

            self.stdout.write(f"claim vm{rec.slot_id} ({rec.status})")
            try:
                if rec.status == Vm.DELETING:
                    services.deprovision(rec.id)
                    self.stdout.write(f"  vm{rec.slot_id} DELETED")
                else:
                    services.provision(rec.id)
                    self.stdout.write(f"  vm{rec.slot_id} ACTIVE")
            except Exception as e:
                self.stdout.write(f"  vm{rec.slot_id} ERROR: {type(e).__name__}: {e}")

        self.stdout.write("worker stopped")