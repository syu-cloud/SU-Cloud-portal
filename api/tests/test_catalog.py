from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient, APITestCase


class ImageListApiTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/api/v1/images"

        User = get_user_model()
        self.user = User.objects.create_user(
            username="catalogtester",
            password="test-password",
        )

    def test_images_requires_authentication(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.json(),
            {
                "code": "AUTHENTICATION_REQUIRED",
                "message": "Authentication is required.",
            },
        )

    @patch("api.services.catalog_service.list_portal_images")
    def test_get_images_returns_contract_fields_only(self, mock_list):
        mock_list.return_value = [
            {
                "id": "image-uuid-1",
                "name": "Ubuntu-24.04",
                "min_disk": 20,
                "min_ram": 2048,
                "visibility": "public",
            },
            {
                "id": "image-uuid-2",
                "name": "Rocky-9",
                "min_disk": 10,
                "min_ram": 1024,
                "visibility": "public",
            },
        ]

        self.client.force_login(self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "items": [
                    {
                        "id": "image-uuid-1",
                        "name": "Ubuntu-24.04",
                    },
                    {
                        "id": "image-uuid-2",
                        "name": "Rocky-9",
                    },
                ]
            },
        )

        mock_list.assert_called_once_with()

    @patch("api.services.catalog_service.list_portal_images")
    def test_get_images_returns_empty_items_when_none_exist(self, mock_list):
        mock_list.return_value = []

        self.client.force_login(self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "items": [],
            },
        )

    @patch("api.services.catalog_service.list_portal_images")
    def test_get_images_failure_returns_500(self, mock_list):
        mock_list.side_effect = RuntimeError("OpenStack lookup failed")

        self.client.force_login(self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.json(),
            {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected server error occurred.",
            },
        )


class FlavorListApiTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/api/v1/flavors"

        User = get_user_model()
        self.user = User.objects.create_user(
            username="flavortester",
            password="test-password",
        )

    def test_flavors_requires_authentication(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.json(),
            {
                "code": "AUTHENTICATION_REQUIRED",
                "message": "Authentication is required.",
            },
        )

    @patch("api.services.catalog_service.get_portal_flavor")
    def test_get_flavors_returns_configured_flavor(self, mock_get):
        mock_get.return_value = {
            "id": "flavor-uuid",
            "name": "su-small",
            "vcpus": 2,
            "ram_mb": 2048,
            "disk_gb": 30,
        }

        self.client.force_login(self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "items": [
                    {
                        "id": "flavor-uuid",
                        "name": "su-small",
                        "vcpus": 2,
                        "ram_mb": 2048,
                        "disk_gb": 30,
                    }
                ]
            },
        )

        mock_get.assert_called_once_with()

    @patch("api.services.catalog_service.get_portal_flavor")
    def test_missing_configured_flavor_returns_500(self, mock_get):
        mock_get.return_value = None

        self.client.force_login(self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.json(),
            {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected server error occurred.",
            },
        )
