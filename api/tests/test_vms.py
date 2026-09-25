import base64
from types import SimpleNamespace
from unittest.mock import patch

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


class VmCreateApiTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/api/v1/vms"

        User = get_user_model()
        self.user = User.objects.create_user(
            username="vmcreatetester",
            password="test-password",
        )

        self.image_id = "11111111-1111-1111-1111-111111111111"
        self.image = {
            "id": self.image_id,
            "name": "ubuntu-24.04",
        }

    def _login(self):
        self.client.force_login(self.user)

    @patch("api.views.api_services.create_vms")
    def test_create_vms_requires_csrf(self, mock_create_vms):
        csrf_client = APIClient(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)

        response = csrf_client.post(
            self.url,
            {
                "count": 1,
                "image_id": self.image_id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json(),
            {
                "code": "CSRF_FAILED",
                "message": "CSRF validation failed.",
            },
        )

        mock_create_vms.assert_not_called()

    def test_create_vms_requires_authentication(self):
        response = self.client.post(
            self.url,
            {
                "count": 1,
                "image_id": self.image_id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.json()["code"],
            "AUTHENTICATION_REQUIRED",
        )

    def test_create_vms_rejects_malformed_json(self):
        self._login()

        response = self.client.generic(
            "POST",
            self.url,
            '{"count": 1, "image_id":',
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["code"],
            "VALIDATION_ERROR",
        )

    def test_create_vms_rejects_non_object_body(self):
        self._login()

        response = self.client.post(
            self.url,
            [],
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["code"],
            "VALIDATION_ERROR",
        )

    @patch("api.services.catalog_service.get_portal_image")
    def test_create_vms_rejects_invalid_count(
        self,
        mock_get_image,
    ):
        self._login()

        invalid_values = (
            None,
            0,
            -1,
            "1",
            True,
            1.5,
        )

        for count in invalid_values:
            with self.subTest(count=count):
                payload = {
                    "image_id": self.image_id,
                }

                if count is not None:
                    payload["count"] = count

                response = self.client.post(
                    self.url,
                    payload,
                    format="json",
                )

                self.assertEqual(response.status_code, 400)
                self.assertEqual(
                    response.json()["code"],
                    "VALIDATION_ERROR",
                )

        mock_get_image.assert_not_called()

    @patch("api.services.catalog_service.get_portal_image")
    def test_create_vms_rejects_invalid_image_id(
        self,
        mock_get_image,
    ):
        self._login()

        for image_id in (None, "", "not-a-uuid"):
            with self.subTest(image_id=image_id):
                payload = {
                    "count": 1,
                }

                if image_id is not None:
                    payload["image_id"] = image_id

                response = self.client.post(
                    self.url,
                    payload,
                    format="json",
                )

                self.assertEqual(response.status_code, 400)
                self.assertEqual(
                    response.json()["code"],
                    "VALIDATION_ERROR",
                )

        mock_get_image.assert_not_called()

    @patch("api.services.prov.reserve")
    @patch("api.services.catalog_service.get_portal_image")
    def test_create_vms_rejects_unavailable_image(
        self,
        mock_get_image,
        mock_reserve,
    ):
        self._login()
        mock_get_image.return_value = None

        response = self.client.post(
            self.url,
            {
                "count": 1,
                "image_id": self.image_id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.json()["code"],
            "IMAGE_NOT_AVAILABLE",
        )
        mock_reserve.assert_not_called()

    @patch("api.services.prov.reserve")
    @patch("api.services.prov.free_slot_count")
    @patch("api.services.catalog_service.get_portal_image")
    def test_create_vms_rejects_request_over_capacity(
        self,
        mock_get_image,
        mock_free_slot_count,
        mock_reserve,
    ):
        self._login()

        mock_get_image.return_value = self.image
        mock_free_slot_count.return_value = 2

        response = self.client.post(
            self.url,
            {
                "count": 3,
                "image_id": self.image_id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.json()["code"],
            "INSUFFICIENT_CAPACITY",
        )
        mock_reserve.assert_not_called()

    @patch("api.services.prov.reserve")
    @patch("api.services.prov.free_slot_count")
    @patch("api.services.catalog_service.get_portal_image")
    def test_create_vms_returns_202_with_accepted_items(
        self,
        mock_get_image,
        mock_free_slot_count,
        mock_reserve,
    ):
        self._login()

        mock_get_image.return_value = self.image
        mock_free_slot_count.return_value = 5
        mock_reserve.side_effect = [
            SimpleNamespace(
                id=101,
                slot_id=1,
                status=Vm.PROVISIONING,
            ),
            SimpleNamespace(
                id=102,
                slot_id=2,
                status=Vm.PROVISIONING,
            ),
        ]

        response = self.client.post(
            self.url,
            {
                "count": 2,
                "image_id": self.image_id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 202)
        self.assertEqual(
            response.json(),
            {
                "requested_count": 2,
                "accepted_count": 2,
                "items": [
                    {
                        "id": 101,
                        "slot_id": 1,
                        "status": "PROVISIONING",
                    },
                    {
                        "id": 102,
                        "slot_id": 2,
                        "status": "PROVISIONING",
                    },
                ],
            },
        )

        self.assertEqual(mock_reserve.call_count, 2)

    @patch("api.services.prov.reserve")
    @patch("api.services.prov.free_slot_count")
    @patch("api.services.catalog_service.get_portal_image")
    def test_create_vms_allows_partial_acceptance_after_precheck(
        self,
        mock_get_image,
        mock_free_slot_count,
        mock_reserve,
    ):
        self._login()

        mock_get_image.return_value = self.image
        mock_free_slot_count.return_value = 5
        mock_reserve.side_effect = [
            SimpleNamespace(
                id=101,
                slot_id=1,
                status=Vm.PROVISIONING,
            ),
            SimpleNamespace(
                id=102,
                slot_id=2,
                status=Vm.PROVISIONING,
            ),
            None,
        ]

        response = self.client.post(
            self.url,
            {
                "count": 3,
                "image_id": self.image_id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 202)

        data = response.json()

        self.assertEqual(data["requested_count"], 3)
        self.assertEqual(data["accepted_count"], 2)
        self.assertEqual(
            [item["id"] for item in data["items"]],
            [101, 102],
        )

    @patch("api.services.prov.reserve")
    @patch("api.services.prov.free_slot_count")
    @patch("api.services.catalog_service.get_portal_image")
    def test_create_vms_returns_409_when_nothing_is_accepted(
        self,
        mock_get_image,
        mock_free_slot_count,
        mock_reserve,
    ):
        self._login()

        mock_get_image.return_value = self.image
        mock_free_slot_count.return_value = 5
        mock_reserve.return_value = None

        response = self.client.post(
            self.url,
            {
                "count": 2,
                "image_id": self.image_id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.json()["code"],
            "INSUFFICIENT_CAPACITY",
        )
