import os
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import SimpleTestCase

from provisioning import services


class InfraWriteSafetyTests(SimpleTestCase):
    def test_missing_infra_write_flag_blocks(self):
        """설정 자체가 빠져도 실제 인프라 쓰기는 기본 차단된다."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("SU_INFRA_WRITES_ENABLED", None)

            with self.assertRaisesMessage(
                RuntimeError,
                "Infrastructure writes are disabled in this environment",
            ):
                services._require_infra_writes_enabled()

    def test_explicit_true_allows_infra_write_guard(self):
        """운영 전환 시 명시적으로 true를 준 경우에만 guard를 통과한다."""
        with patch.dict(
            os.environ,
            {"SU_INFRA_WRITES_ENABLED": "true"},
        ):
            services._require_infra_writes_enabled()

    def test_provision_and_deprovision_block_before_side_effects(self):
        """Phase 1에서는 public write service 진입점 자체가 차단된다."""
        with (
            patch.dict(
                os.environ,
                {"SU_INFRA_WRITES_ENABLED": "false"},
            ),
            patch.object(services, "get_conn") as mock_get_conn,
            patch.object(services, "get_wg") as mock_get_wg,
        ):
            for func in (
                services.provision,
                services.deprovision,
            ):
                with self.subTest(func=func.__name__):
                    with self.assertRaises(RuntimeError):
                        func(-1)

            mock_get_conn.assert_not_called()
            mock_get_wg.assert_not_called()

    def test_provision_passes_configured_keyfile_to_osvm_create(self):
        """실제 provisioning 경로가 SU_KEYFILE 값을 osvm.create()에 전달한다."""
        from types import SimpleNamespace

        vm = SimpleNamespace(
            id=1,
            slot_id=1,
            image_id="image-uuid",
        )
        server = SimpleNamespace(id="server-uuid")

        fake_wg = SimpleNamespace(
            provision_seat=lambda **kwargs: "test-password",
        )

        with (
            patch.dict(
                os.environ,
                {
                    "SU_INFRA_WRITES_ENABLED": "true",
                    "SU_KEYFILE": "/tmp/test-key.pem",
                },
            ),
            patch.object(services.Vm.objects, "get", return_value=vm),
            patch.object(services, "get_conn") as mock_get_conn,
            patch.object(services, "_reconcile", return_value=False),
            patch.object(
                services.osvm,
                "create",
                return_value=server,
            ) as mock_create,
            patch.object(services, "_mark_active"),
            patch.object(services, "get_wg", return_value=fake_wg),
        ):
            services.provision(vm.id)

        mock_create.assert_called_once_with(
            mock_get_conn.return_value,
            1,
            "/tmp/test-key.pem",
            image_id="image-uuid",
        )

    def test_missing_worker_flag_blocks_worker(self):
        """Worker도 설정 누락 시 시작하지 않는다."""
        stderr = StringIO()

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("SU_WORKER_ENABLED", None)

            with patch(
                "provisioning.management.commands.worker.services.claim"
            ) as mock_claim:
                call_command(
                    "worker",
                    stderr=stderr,
                )

        mock_claim.assert_not_called()
        self.assertIn(
            "Worker is disabled in this environment",
            stderr.getvalue(),
        )
