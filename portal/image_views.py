"""Image Build 관리 화면의 HTTP 요청/응답 처리."""

import os

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from catalog import services as catalog_service
from imagebuild import services as imagebuild_service


LIST_ROUTE = "imagebuild:list"


# =========================================================
# 목록
# =========================================================

@login_required
def list_view(request):
    """이미지 제작 현황과 생성된 이미지 목록을 표시한다."""

    try:
        images = (
            catalog_service
            .list_imagebuild_base_images()
        )
    except Exception:
        # 기반 이미지 조회 실패가
        # 이미지 관리 화면 전체를 막지는 않도록 한다.
        images = []

    build_data = (
        imagebuild_service.list_build_data()
    )

    return render(
        request,
        "portal/image_list.html",
        {
            "images": images,
            "active_build": (
                build_data["active_build"]
            ),
            "published_builds": (
                build_data["published_builds"]
            ),
            "failed_builds": (
                build_data["failed_builds"]
            ),
            "auto_refresh": (
                build_data["auto_refresh"]
            ),
            "warpgate_url": (
                os.environ
                .get("WG_WEB_URL", "")
                .strip()
            ),
            "warpgate_username": (
                imagebuild_service.BUILD_USER
            ),
        },
    )


# =========================================================
# 제작 요청
# =========================================================

@login_required
@require_POST
def create_view(request):
    """새 Image Build 제작 요청을 등록한다."""

    name = (
        request.POST
        .get("name", "")
        .strip()
    )

    image_id = (
        request.POST
        .get("base_image_id", "")
        .strip()
    )

    if not name:
        messages.error(
            request,
            "이미지 이름을 입력해주세요.",
        )
        return redirect(LIST_ROUTE)

    if not image_id:
        messages.error(
            request,
            "기반 이미지를 선택해주세요.",
        )
        return redirect(LIST_ROUTE)

    try:
        base_image = (
            catalog_service
            .get_imagebuild_base_image(
                image_id
            )
        )
    except Exception:
        messages.error(
            request,
            "이미지 정보를 확인할 수 없습니다.",
        )
        return redirect(LIST_ROUTE)

    if base_image is None:
        messages.error(
            request,
            "선택한 기반 이미지를 "
            "사용할 수 없습니다.",
        )
        return redirect(LIST_ROUTE)

    build = (
        imagebuild_service.request_build(
            name,
            base_image,
        )
    )

    if build is None:
        messages.error(
            request,
            "이미지 제작 작업은 "
            "한 번에 하나만 진행할 수 있습니다.",
        )
        return redirect(LIST_ROUTE)

    messages.success(
        request,
        f"{build.name} 이미지 제작 요청을 "
        "등록했습니다.",
    )

    return redirect(LIST_ROUTE)


@login_required
@require_POST
def publish_view(
    request,
    build_id,
):
    """READY Build의 이미지 생성을 요청한다."""

    build = (
        imagebuild_service.request_publish(
            build_id
        )
    )

    if build is None:
        messages.error(
            request,
            "현재 상태에서는 "
            "이미지를 생성할 수 없습니다.",
        )
        return redirect(LIST_ROUTE)

    messages.success(
        request,
        f"{build.name} 이미지 생성을 "
        "시작했습니다.",
    )

    return redirect(LIST_ROUTE)


@login_required
@require_POST
def cancel_view(
    request,
    build_id,
):
    """READY Build의 제작 취소를 요청한다."""

    build = (
        imagebuild_service.request_cancel(
            build_id
        )
    )

    if build is None:
        messages.error(
            request,
            "현재 상태에서는 "
            "제작을 취소할 수 없습니다.",
        )
        return redirect(LIST_ROUTE)

    messages.success(
        request,
        f"{build.name} 이미지 제작 취소를 "
        "요청했습니다.",
    )

    return redirect(LIST_ROUTE)