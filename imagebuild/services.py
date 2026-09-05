import os
from pathlib import Path

from catalog.services import PORTAL_IMAGE_TAG
from osclient import get_conn
from osclient import imagebuild as osimagebuild
from wgclient import get_wg

from .models import ImageBuild


CLEANUP_SCRIPT_PATH = (
    Path(__file__).resolve().parent
    / "scripts"
    / "cleanup.sh"
)

KEYFILE = os.environ.get(
    "SU_KEYFILE",
    "/opt/su-portal/sdk-probe-key.pem",
)

BUILD_USER = osimagebuild.BUILD_USER
WG_ROLE_NAME = "image-build"

ACTIVE_STATUSES = [
    ImageBuild.CREATING,
    ImageBuild.READY,
    ImageBuild.SNAPSHOTTING,
    ImageBuild.CANCELING,
]

AUTO_REFRESH_STATUSES = [
    ImageBuild.CREATING,
    ImageBuild.SNAPSHOTTING,
    ImageBuild.CANCELING,
]


# =========================================================
# 조회
# =========================================================

def list_build_data():
    """이미지 관리 화면에 필요한 제작 상태를 반환한다."""

    active_build = (
        ImageBuild.objects
        .filter(status__in=ACTIVE_STATUSES)
        .order_by("-created_at")
        .first()
    )

    published_builds = (
        ImageBuild.objects
        .filter(status=ImageBuild.PUBLISHED)
        .order_by("-created_at")
    )

    failed_builds = (
        ImageBuild.objects
        .filter(status=ImageBuild.FAILED)
        .order_by("-created_at")[:3]
    )

    auto_refresh = (
        active_build is not None
        and active_build.status
        in AUTO_REFRESH_STATUSES
    )

    return {
        "active_build": active_build,
        "published_builds": published_builds,
        "failed_builds": failed_builds,
        "auto_refresh": auto_refresh,
    }


# =========================================================
# 요청
# =========================================================

def request_build(name, base_image):
    """새 Image Build를 CREATING 상태로 등록한다."""

    # Phase 0.5에서는 동시에 하나의 제작 작업만 허용한다.
    if ImageBuild.objects.filter(
        status__in=ACTIVE_STATUSES
    ).exists():
        return None

    return ImageBuild.objects.create(
        name=name,
        base_image_id=base_image["id"],
        base_image_name=base_image["name"],
        status=ImageBuild.CREATING,
    )


def request_publish(build_id):
    """READY 상태의 Build를 이미지 생성 대기 상태로 전환한다."""

    build = (
        ImageBuild.objects
        .filter(pk=build_id)
        .first()
    )

    if build is None:
        return None

    if build.status != ImageBuild.READY:
        return None

    build.status = ImageBuild.SNAPSHOTTING
    build.error = ""

    build.save(
        update_fields=[
            "status",
            "error",
            "updated_at",
        ]
    )

    return build


def request_cancel(build_id):
    """READY 상태의 Build를 제작 취소 대기 상태로 전환한다."""

    build = (
        ImageBuild.objects
        .filter(pk=build_id)
        .first()
    )

    if build is None:
        return None

    # Phase 0.5에서는 READY 상태에서만 취소한다.
    if build.status != ImageBuild.READY:
        return None

    build.status = ImageBuild.CANCELING
    build.error = ""

    build.save(
        update_fields=[
            "status",
            "error",
            "updated_at",
        ]
    )

    return build


# =========================================================
# Worker 실행
# =========================================================

def provision(build_id):
    """Build VM과 Warpgate 접속 환경을 준비하고 READY로 전환한다."""

    build = ImageBuild.objects.get(
        pk=build_id
    )

    if build.status != ImageBuild.CREATING:
        return build

    try:
        conn = get_conn()

        cleanup_script = (
            CLEANUP_SCRIPT_PATH.read_text(
                encoding="utf-8"
            )
        )

        server = osimagebuild.create(
            conn=conn,
            build_id=build.id,
            image_id=build.base_image_id,
            key_path=KEYFILE,
            cleanup_script=cleanup_script,
        )

        # Warpgate 단계가 실패해도 생성된 VM은 추적할 수 있게 저장한다.
        build.server_id = server.id

        build.save(
            update_fields=[
                "server_id",
                "updated_at",
            ]
        )

        _ensure_warpgate(build)

    except Exception as error:
        _save_failed(
            build,
            error,
        )
        raise

    build.status = ImageBuild.READY
    build.error = ""

    build.save(
        update_fields=[
            "status",
            "error",
            "updated_at",
        ]
    )

    return build


def publish(build_id):
    """Build VM을 Snapshot으로 만들고 Portal Image로 발행한다."""

    build = ImageBuild.objects.get(
        pk=build_id
    )

    if build.status != ImageBuild.SNAPSHOTTING:
        return build

    try:
        conn = get_conn()

        if not build.server_id:
            raise RuntimeError(
                "image build server_id is missing"
            )

        # 이미 Snapshot이 생성된 경우 중복 생성하지 않는다.
        if not build.glance_image_id:
            osimagebuild.prepare_snapshot(
                conn=conn,
                server_id=str(build.server_id),
                key_path=KEYFILE,
            )

            image = osimagebuild.create_snapshot(
                conn=conn,
                server_id=str(build.server_id),
                image_name=build.name,
            )

            build.glance_image_id = image.id

            build.save(
                update_fields=[
                    "glance_image_id",
                    "updated_at",
                ]
            )

        # Snapshot 완료 후 임시 제작 자원을 정리한다.
        _delete_runtime_resources(
            build,
            conn,
        )

        # 정리가 끝난 이미지만 VM 생성 화면에 공개한다.
        conn.image.add_tag(
            str(build.glance_image_id),
            PORTAL_IMAGE_TAG,
        )

    except Exception as error:
        _save_failed(
            build,
            error,
        )
        raise

    build.status = ImageBuild.PUBLISHED
    build.error = ""

    build.save(
        update_fields=[
            "status",
            "error",
            "updated_at",
        ]
    )

    return build


def cancel(build_id):
    """취소 요청된 Build의 Warpgate Target과 VM을 정리한다."""

    build = ImageBuild.objects.get(
        pk=build_id
    )

    if build.status != ImageBuild.CANCELING:
        return build

    try:
        conn = get_conn()

        _delete_runtime_resources(
            build,
            conn,
        )

    except Exception as error:
        _save_failed(
            build,
            error,
        )
        raise

    build.status = ImageBuild.CANCELED
    build.error = ""

    build.save(
        update_fields=[
            "status",
            "error",
            "updated_at",
        ]
    )

    return build


# =========================================================
# 복구
# =========================================================

def provision_warpgate(build_id):
    """READY Build의 Warpgate 구성을 다시 보장한다."""

    build = ImageBuild.objects.get(
        pk=build_id
    )

    if build.status != ImageBuild.READY:
        raise ValueError(
            "image build is not READY"
        )

    return _ensure_warpgate(
        build
    )


# =========================================================
# 내부
# =========================================================

def _ensure_warpgate(build):
    """Image Build 전용 Warpgate User, Role, Target을 준비한다."""

    wg = get_wg()

    target_name = (
        f"image-build-{build.id}"
    )

    user = wg.ensure_user(
        BUILD_USER
    )

    role = wg.ensure_role(
        WG_ROLE_NAME
    )

    target = wg.ensure_ssh_target(
        target_name,
        host=osimagebuild.fip_for(),
        username=BUILD_USER,
    )

    wg.bind(
        user["id"],
        target["id"],
        role["id"],
    )

    wg.set_password(
        user["id"],
        password=os.environ[
            "SU_IMAGE_BUILD_WG_PASSWORD"
        ],
    )

    return {
        "username": BUILD_USER,
        "target_name": target_name,
    }


def _delete_runtime_resources(
    build,
    conn,
):
    """
    Build의 Warpgate Target과 VM을 정리한다.

    한쪽 정리가 실패해도 다른 자원 정리는 계속 시도한다.
    """

    errors = []

    try:
        get_wg().delete_target(
            f"image-build-{build.id}"
        )

    except Exception as error:
        errors.append(
            "Warpgate target cleanup failed: "
            f"{type(error).__name__}: {error}"
        )

    if build.server_id:
        try:
            osimagebuild.delete_build_server(
                conn=conn,
                server_id=str(build.server_id),
            )

        except Exception as error:
            errors.append(
                "Build VM cleanup failed: "
                f"{type(error).__name__}: {error}"
            )

    else:
        errors.append(
            "image build server_id is missing"
        )

    if errors:
        raise RuntimeError(
            " | ".join(errors)
        )


def _save_failed(build, error):
    """작업 실패 상태와 오류 내용을 DB에 기록한다."""

    build.status = ImageBuild.FAILED
    build.error = (
        f"{type(error).__name__}: {error}"
    )[:2000]

    build.save(
        update_fields=[
            "status",
            "error",
            "updated_at",
        ]
    )