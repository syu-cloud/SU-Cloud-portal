"""
Glance 이미지 카탈로그 조회.

포털이 사용자에게 보여줄 이미지 목록을 반환함.
선별 기준은 Glance tag이며, 태그 이름은 호출부가 지정함.

SDK property 필터는 무시되어 전량이 반환되므로 사용하지 않음
(probes/inspect_image_filter.py 참조).
"""


def catalog(conn, tag):
    """tag가 부여된 active 이미지 목록을 이름순으로 반환함."""
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