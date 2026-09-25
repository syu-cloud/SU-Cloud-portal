from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient, APITestCase


class SessionApiTests(APITestCase):
    def setUp(self):
        # 실제 브라우저와 가깝게 CSRF 검사를 활성화한다.
        self.client = APIClient(enforce_csrf_checks=True)
        self.url = "/api/v1/auth/session"

        User = get_user_model()
        self.user = User.objects.create_user(
            username="phase1test",
            password="test-password",
        )

    def _prepare_csrf(self):
        """GET /auth/session으로 CSRF Cookie를 준비한다."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertIn("suportal_csrftoken", self.client.cookies)

        return self.client.cookies["suportal_csrftoken"].value

    def _login(self):
        """정상 로그인 후 Response를 반환한다."""
        csrf = self._prepare_csrf()

        response = self.client.post(
            self.url,
            {
                "username": "phase1test",
                "password": "test-password",
            },
            format="json",
            HTTP_X_CSRFTOKEN=csrf,
        )

        self.assertEqual(response.status_code, 200)

        return response

    def test_get_session_anonymous_sets_csrf_cookie(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "authenticated": False,
                "user": None,
            },
        )
        self.assertIn("suportal_csrftoken", self.client.cookies)

    def test_login_without_csrf_returns_403(self):
        response = self.client.post(
            self.url,
            {
                "username": "phase1test",
                "password": "test-password",
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

    def test_login_rejects_non_object_json(self):
        csrf = self._prepare_csrf()

        response = self.client.post(
            self.url,
            [],
            format="json",
            HTTP_X_CSRFTOKEN=csrf,
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(),
            {
                "code": "VALIDATION_ERROR",
                "message": "Request body must be a JSON object.",
            },
        )

    @patch("api.views.authenticate")
    def test_login_rejects_non_string_credentials(
        self,
        mock_authenticate,
    ):
        csrf = self._prepare_csrf()

        invalid_payloads = (
            {
                "username": ["phase1test"],
                "password": "test-password",
            },
            {
                "username": "phase1test",
                "password": {"value": "test-password"},
            },
            {
                "username": 123,
                "password": "test-password",
            },
        )

        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                response = self.client.post(
                    self.url,
                    payload,
                    format="json",
                    HTTP_X_CSRFTOKEN=csrf,
                )

                self.assertEqual(response.status_code, 400)
                self.assertEqual(
                    response.json(),
                    {
                        "code": "VALIDATION_ERROR",
                        "message": (
                            "username and password must be strings."
                        ),
                    },
                )

        mock_authenticate.assert_not_called()

    def test_login_with_missing_credentials_returns_400(self):
        csrf = self._prepare_csrf()

        response = self.client.post(
            self.url,
            {},
            format="json",
            HTTP_X_CSRFTOKEN=csrf,
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(),
            {
                "code": "VALIDATION_ERROR",
                "message": "username and password are required.",
            },
        )

    def test_login_with_wrong_credentials_returns_401(self):
        csrf = self._prepare_csrf()

        response = self.client.post(
            self.url,
            {
                "username": "phase1test",
                "password": "wrong-password",
            },
            format="json",
            HTTP_X_CSRFTOKEN=csrf,
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.json(),
            {
                "code": "INVALID_CREDENTIALS",
                "message": "Invalid username or password.",
            },
        )

    def test_login_success_and_session_lookup(self):
        csrf_before_login = self._prepare_csrf()

        response = self.client.post(
            self.url,
            {
                "username": "phase1test",
                "password": "test-password",
            },
            format="json",
            HTTP_X_CSRFTOKEN=csrf_before_login,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "authenticated": True,
                "user": {
                    "username": "phase1test",
                },
            },
        )

        self.assertIn("suportal_sessionid", self.client.cookies)
        self.assertIn("suportal_csrftoken", self.client.cookies)

        csrf_after_login = self.client.cookies["suportal_csrftoken"].value

        # Django login() 이후 CSRF Token이 회전했는지 확인한다.
        self.assertNotEqual(csrf_before_login, csrf_after_login)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "authenticated": True,
                "user": {
                    "username": "phase1test",
                },
            },
        )

    def test_logout_without_csrf_returns_403_and_keeps_session(self):
        self._login()

        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json(),
            {
                "code": "CSRF_FAILED",
                "message": "CSRF validation failed.",
            },
        )

        # 거절된 로그아웃 요청 때문에 기존 Session이 사라지면 안 된다.
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["authenticated"])
        self.assertEqual(
            response.json()["user"]["username"],
            "phase1test",
        )

    def test_logout_success(self):
        self._login()

        # login() 시 CSRF가 회전하므로 현재 Cookie 값을 다시 사용한다.
        csrf = self.client.cookies["suportal_csrftoken"].value

        response = self.client.delete(
            self.url,
            HTTP_X_CSRFTOKEN=csrf,
        )

        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "authenticated": False,
                "user": None,
            },
        )

    def test_login_with_invalid_csrf_returns_403(self):
        self._prepare_csrf()

        response = self.client.post(
            self.url,
            {
                "username": "phase1test",
                "password": "test-password",
            },
            format="json",
            HTTP_X_CSRFTOKEN="invalid-csrf-token",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json(),
            {
                "code": "CSRF_FAILED",
                "message": "CSRF validation failed.",
            },
        )
