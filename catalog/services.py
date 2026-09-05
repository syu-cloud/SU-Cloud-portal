from osclient import get_conn
from osclient import image as osimage


PORTAL_IMAGE_TAG = "su-portal"


def list_portal_images():
    """Portal에서 선택 가능한 Image 목록."""
    conn = get_conn()
    return osimage.list_by_tag(conn, PORTAL_IMAGE_TAG)


def get_portal_image(image_id):
    """VM 생성에 사용할 수 있는 Portal Image인지 확인."""
    if not image_id:
        return None

    conn = get_conn()
    image = osimage.get(conn, image_id)

    if image is None:
        return None

    if image["status"] != "active":
        return None

    if PORTAL_IMAGE_TAG not in image["tags"]:
        return None

    return image