from uuid import UUID

from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token

from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from . import services as api_services


@api_view(["GET", "POST", "DELETE"])
@permission_classes([AllowAny])
def session_view(request):
    # 인증 상태 조회 및 CSRF 준비
    if request.method == "GET":
        get_token(request)

        if request.user.is_authenticated:
            return Response({
                "authenticated": True,
                "user": {
                    "username": request.user.username,
                },
            })

        return Response({
            "authenticated": False,
            "user": None,
        })

    # POST / DELETE 공통 CSRF 검증
    SessionAuthentication().enforce_csrf(request)

    # 로그아웃
    if request.method == "DELETE":
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)

    # 로그인 요청 값 검증
    username = request.data.get("username")
    password = request.data.get("password")

    if not username or not password:
        return Response(
            {
                "code": "VALIDATION_ERROR",
                "message": "username and password are required.",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # 사용자 인증
    user = authenticate(
        request=request,
        username=username,
        password=password,
    )

    if user is None:
        return Response(
            {
                "code": "INVALID_CREDENTIALS",
                "message": "Invalid username or password.",
            },
            status=status.HTTP_401_UNAUTHORIZED,
        )

    # 로그인 Session 생성
    login(request, user)

    return Response({
        "authenticated": True,
        "user": {
            "username": user.username,
        },
    })


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def vm_list_view(request):
    if request.method == "POST":
        return _create_vms(request)

    # 검색 · 상태 Filter
    status_filter = request.query_params.get("status", "")
    q = request.query_params.get("q", "").strip()

    try:
        data = api_services.list_vms(
            status_filter=status_filter,
            q=q,
        )
    except ValueError:
        return Response(
            {
                "code": "VALIDATION_ERROR",
                "message": "Unsupported status filter.",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Response(data)


def _create_vms(request):
    """VM 생성 요청의 HTTP 입력 검증 및 응답 변환."""
    if not isinstance(request.data, dict):
        return Response(
            {
                "code": "VALIDATION_ERROR",
                "message": "Request body must be a JSON object.",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    count = request.data.get("count")

    # bool은 Python에서 int의 하위 타입이므로 명시적으로 제외한다.
    if type(count) is not int or count < 1:
        return Response(
            {
                "code": "VALIDATION_ERROR",
                "message": "count must be an integer greater than or equal to 1.",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    image_id = request.data.get("image_id")

    if not isinstance(image_id, str) or not image_id:
        return Response(
            {
                "code": "VALIDATION_ERROR",
                "message": "image_id must be a valid UUID.",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        UUID(image_id)
    except ValueError:
        return Response(
            {
                "code": "VALIDATION_ERROR",
                "message": "image_id must be a valid UUID.",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        data = api_services.create_vms(
            count=count,
            image_id=image_id,
        )
    except api_services.ImageNotAvailable:
        return Response(
            {
                "code": "IMAGE_NOT_AVAILABLE",
                "message": "The selected image is not available.",
            },
            status=status.HTTP_409_CONFLICT,
        )
    except api_services.InsufficientCapacity:
        return Response(
            {
                "code": "INSUFFICIENT_CAPACITY",
                "message": "There are not enough free slots.",
            },
            status=status.HTTP_409_CONFLICT,
        )

    return Response(
        data,
        status=status.HTTP_202_ACCEPTED,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def image_list_view(request):
    # VM 생성에 사용할 수 있는 Image 조회
    return Response(api_services.list_images())


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def flavor_list_view(request):
    # 현재 Portal에서 사용하는 고정 Flavor 조회
    return Response(api_services.list_flavors())
