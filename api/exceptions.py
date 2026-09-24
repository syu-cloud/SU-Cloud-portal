from rest_framework import status
from rest_framework.exceptions import NotAuthenticated, PermissionDenied
from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is None:
        return None

    # 보호 API의 미인증 응답을 Contract의 401 형식으로 변환
    if isinstance(exc, NotAuthenticated):
        response.status_code = status.HTTP_401_UNAUTHORIZED
        response.data = {
            "code": "AUTHENTICATION_REQUIRED",
            "message": "Authentication is required.",
        }
        return response

    # DRF CSRF 오류를 API 공통 Error Schema로 변환
    if (
        isinstance(exc, PermissionDenied)
        and str(exc.detail).startswith("CSRF Failed:")
    ):
        response.data = {
            "code": "CSRF_FAILED",
            "message": "CSRF validation failed.",
        }

    return response
