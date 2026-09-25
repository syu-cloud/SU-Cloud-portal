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
    if not isinstance(request.data, dict):
        return Response(
            {
                "code": "VALIDATION_ERROR",
                "message": "Request body must be a JSON object.",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    username = request.data.get("username")
    password = request.data.get("password")

    if (
        username is None
        or password is None
        or username == ""
        or password == ""
    ):
        return Response(
            {
                "code": "VALIDATION_ERROR",
                "message": "username and password are required.",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if (
        not isinstance(username, str)
        or not isinstance(password, str)
    ):
        return Response(
            {
                "code": "VALIDATION_ERROR",
                "message": "username and password must be strings.",
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



@api_view(["POST"])
@permission_classes([IsAuthenticated])
def vm_reclaim_view(request):
    """선택 또는 전체 VM 회수 요청을 접수한다."""
    if not isinstance(request.data, dict):
        return Response(
            {
                "code": "VALIDATION_ERROR",
                "message": "Request body must be a JSON object.",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    scope = request.data.get("scope")

    if scope not in ("selected", "all"):
        return Response(
            {
                "code": "VALIDATION_ERROR",
                "message": "scope must be selected or all.",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if scope == "all":
        if "vm_ids" in request.data:
            return Response(
                {
                    "code": "VALIDATION_ERROR",
                    "message": "vm_ids must not be provided for all scope.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        vm_ids = None

    else:
        vm_ids = request.data.get("vm_ids")

        if not isinstance(vm_ids, list) or not vm_ids:
            return Response(
                {
                    "code": "VALIDATION_ERROR",
                    "message": "vm_ids must be a non-empty array.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if any(type(vm_id) is not int for vm_id in vm_ids):
            return Response(
                {
                    "code": "VALIDATION_ERROR",
                    "message": "vm_ids must contain integers.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(vm_ids) != len(set(vm_ids)):
            return Response(
                {
                    "code": "VALIDATION_ERROR",
                    "message": "vm_ids must not contain duplicates.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    data, active_accepted = api_services.reclaim_vms(
        scope=scope,
        vm_ids=vm_ids,
    )

    accepted = data["summary"]["accepted"]

    # scope=all에서 대상 자체가 없으면 정상적인 no-op이다.
    if scope == "all" and data["summary"]["requested"] == 0:
        return Response(
            data,
            status=status.HTTP_200_OK,
        )

    # 하나도 처리할 수 없으면 공통 Error Schema + 건별 결과를 반환한다.
    if accepted == 0:
        return Response(
            {
                "code": "VM_NOT_RECLAIMABLE",
                "message": "No requested VMs can be reclaimed.",
                "details": data,
            },
            status=status.HTTP_409_CONFLICT,
        )

    # 실제 삭제 작업이 필요한 ACTIVE가 하나라도 접수되면 비동기 202.
    if active_accepted > 0:
        return Response(
            data,
            status=status.HTTP_202_ACCEPTED,
        )

    # FAILED+CLEANED acknowledge만 수행된 경우 즉시 완료이므로 200.
    return Response(
        data,
        status=status.HTTP_200_OK,
    )
