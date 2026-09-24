import base64

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from osclient import vm as osvm
from provisioning.models import Slot, Vm, VmFailure


class VmListApiTests(APITestCase):
    def setUp(self):
        self.client = APIClient(enforce_csrf_checks=True)
        self.url = "/api/v1/vms"

        User = get_user_model()
        self.user = User.objects.create_user(
            username="vmtester",
            password="test-password",
        )

        # 실제 운영 구조와 동일하게 Slot 1~45를 준비한다.
        Slot.objects.bulk_create([
            Slot(n=n, status=Slot.FREE)
            for n in range(1, 46)
        ])

        self.active = self._create_vm(
            1,
            Vm.ACTIVE,
            image_name="ubuntu-24.04",
        )

        self.provisioning = self._create_vm(
            2,
            Vm.PROVISIONING,
            image_name="",
        )

        self.deleting = self._create_vm(
            3,
            Vm.DELETING,
            image_name="ubuntu-24.04",
        )

        self.failed_pending = self._create_vm(
            4,
            Vm.FAILED,
            error="ResourceTimeout: build timeout",
        )

        self.failed_cleaned = self._create_vm(
            5,
            Vm.FAILED,
            slot_status=Slot.FREE,
            error="ResourceTimeout: build timeout",
        )
        VmFailure.objects.create(
            vm=self.failed_cleaned,
            cleanup_status=VmFailure.CLEANED,
        )

        # 일반 목록에서 제외되어야 하는 이력
        self.deleted = self._create_vm(
            6,
            Vm.DELETED,
            slot_status=Slot.FREE,
        )

        self.failed_acknowledged = self._create_vm(
            7,
            Vm.FAILED,
            slot_status=Slot.FREE,
            error="ResourceTimeout: build timeout",
        )
        VmFailure.objects.create(
            vm=self.failed_acknowledged,
            cleanup_status=VmFailure.CLEANED,
            acknowledged_at=timezone.now(),
        )

    def _create_vm(
        self,
        slot_n,
        status,
        slot_status=Slot.TAKEN,
        image_name="ubuntu-24.04",
        error="",
    ):
        slot = Slot.objects.get(pk=slot_n)
        slot.status = slot_status
        slot.save(update_fields=["status"])

        return Vm.objects.create(
            slot=slot,
            status=status,
            image_name=image_name,
            error=error,
        )

    def _login(self):
        self.client.force_login(self.user)

    def test_vms_requires_session_authentication(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.json(),
            {
                "code": "AUTHENTICATION_REQUIRED",
                "message": "Authentication is required.",
            },
        )

    def test_basic_authentication_is_not_accepted(self):
        credentials = base64.b64encode(
            b"vmtester:test-password"
        ).decode()

        response = self.client.get(
            self.url,
            HTTP_AUTHORIZATION=f"Basic {credentials}",
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.json()["code"],
            "AUTHENTICATION_REQUIRED",
        )

    def test_get_vms_returns_items_and_unfiltered_summary(self):
        self._login()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

        data = response.json()

        # DELETED와 acknowledged FAILED는 일반 목록에서 제외된다.
        self.assertEqual(
            [item["slot_id"] for item in data["items"]],
            [1, 2, 3, 4, 5],
        )

        self.assertEqual(
            data["summary"],
            {
                "visible_total": 5,
                "status_counts": {
                    "ACTIVE": 1,
                    "PROVISIONING": 1,
                    "DELETING": 1,
                    "FAILED": 2,
                },
                "slots": {
                    "taken": 4,
                    "free": 41,
                    "total": 45,
                },
            },
        )

        active = data["items"][0]

        self.assertEqual(active["name"], "vm1")
        self.assertEqual(active["fip"], osvm.fip_for(1))
        self.assertEqual(active["user"], osvm.user_for(1))
        self.assertTrue(active["can_reclaim"])
        self.assertIsNone(active["failure"])
        self.assertTrue(active["created_at"].endswith("Z"))

        provisioning = data["items"][1]

        self.assertIsNone(provisioning["fip"])
        self.assertIsNone(provisioning["user"])
        self.assertIsNone(provisioning["image_name"])
        self.assertFalse(provisioning["can_reclaim"])

        failed_pending = data["items"][3]

        self.assertFalse(failed_pending["can_reclaim"])
        self.assertEqual(
            failed_pending["failure"]["cleanup_status"],
            None,
        )

        failed_cleaned = data["items"][4]

        self.assertTrue(failed_cleaned["can_reclaim"])
        self.assertEqual(
            failed_cleaned["failure"]["cleanup_status"],
            "CLEANED",
        )
        self.assertEqual(
            failed_cleaned["failure"]["label"],
            "생성 시간 초과",
        )

    def test_status_filter_changes_items_not_summary(self):
        self._login()

        response = self.client.get(
            self.url,
            {"status": "FAILED"},
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertEqual(
            [item["slot_id"] for item in data["items"]],
            [4, 5],
        )

        # summary는 Filter 적용 전 전체 현황이다.
        self.assertEqual(data["summary"]["visible_total"], 5)
        self.assertEqual(
            data["summary"]["status_counts"]["ACTIVE"],
            1,
        )
        self.assertEqual(
            data["summary"]["status_counts"]["FAILED"],
            2,
        )

    def test_search_filters_items(self):
        self._login()

        for query in (
            "VM1",
            osvm.fip_for(1),
            "STUDENT1",
        ):
            with self.subTest(query=query):
                response = self.client.get(
                    self.url,
                    {"q": query},
                )

                self.assertEqual(response.status_code, 200)

                data = response.json()

                self.assertEqual(len(data["items"]), 1)
                self.assertEqual(data["items"][0]["slot_id"], 1)
                self.assertEqual(data["summary"]["visible_total"], 5)

    def test_invalid_status_filter_returns_400(self):
        self._login()

        response = self.client.get(
            self.url,
            {"status": "DELETED"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(),
            {
                "code": "VALIDATION_ERROR",
                "message": "Unsupported status filter.",
            },
        )

    def test_search_with_no_result_returns_empty_items(self):
        self._login()

        response = self.client.get(
            self.url,
            {"q": "does-not-exist"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["items"], [])
        self.assertEqual(
            response.json()["summary"]["visible_total"],
            5,
        )
