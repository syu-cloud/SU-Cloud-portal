from rest_framework.exceptions import PermissionDenied
from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is None:
        return None

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
