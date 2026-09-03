"""Glance 이미지 조회."""


def list_by_tag(conn, tag):
    """tag가 부여된 active 이미지를 이름순으로 반환함.

    status 미지정 시 deactivated 이미지가 포함됨.
    반환 필드는 잠정 — C단계에서 조정.
    """
    out = [
        {
            "id": img.id,
            "name": img.name,
            "min_disk": img.min_disk,
            "min_ram": img.min_ram,
            "visibility": img.visibility,
        }
        for img in conn.image.images(tag=tag, status="active")
    ]
    return sorted(out, key=lambda x: x["name"])


def get(conn, image_id):
    """단일 이미지 조회. 없으면 None."""
    img = conn.image.find_image(image_id)
    if img is None:
        return None
    return {
        "id": img.id,
        "name": img.name,
        "min_disk": img.min_disk,
        "min_ram": img.min_ram,
        "visibility": img.visibility,
        "status": img.status,
    }