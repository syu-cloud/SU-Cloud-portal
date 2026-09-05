"""Portal에서 사용할 Glance Image 정책."""

from osclient import get_conn
from osclient import image as osimage


# VM 생성 화면에서 선택할 수 있는 이미지
PORTAL_IMAGE_TAG = "su-portal"

# Custom Image 제작의 기반으로 사용할 수 있는 이미지
IMAGEBUILD_BASE_TAG = "su-imagebuild-base"


# ══ VM 생성용 Image ══════════════════════════════════════

def list_portal_images():
    """VM 생성 화면에서 선택 가능한 Image 목록."""
    conn = get_conn()

    return osimage.list_by_tag(
        conn,
        PORTAL_IMAGE_TAG,
    )


def get_portal_image(image_id):
    """VM 생성에 사용할 수 있는 Portal Image인지 확인."""

    return _get_tagged_image(
        image_id,
        PORTAL_IMAGE_TAG,
    )


# ══ Image Build 기반 Image ═══════════════════════════════

def list_imagebuild_base_images():
    """Custom Image 제작의 기반으로 선택 가능한 Image 목록."""
    conn = get_conn()

    return osimage.list_by_tag(
        conn,
        IMAGEBUILD_BASE_TAG,
    )


def get_imagebuild_base_image(image_id):
    """Image Build 기반 Image로 허용된 이미지인지 확인."""

    return _get_tagged_image(
        image_id,
        IMAGEBUILD_BASE_TAG,
    )


# ══ 내부 ═════════════════════════════════════════════════

def _get_tagged_image(image_id, required_tag):
    """active 상태이며 required_tag가 부여된 Image만 반환."""

    if not image_id:
        return None

    conn = get_conn()

    image = osimage.get(
        conn,
        image_id,
    )

    if image is None:
        return None

    if image["status"] != "active":
        return None

    if required_tag not in image["tags"]:
        return None

    return image