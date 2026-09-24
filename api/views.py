from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token

from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


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
