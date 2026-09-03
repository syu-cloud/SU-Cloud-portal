"""
Glance 이미지 조회.

선별 기준(어떤 태그를 쓸지)은 호출부가 결정함.
osclient는 태그의 의미를 알지 않음.

[실측 근거]
- SDK의 임의 property 필터는 무시되어 전량 반환됨 → 사용 불가
- SDK images(tag=...) 는 서버측 필터로 동작함
- status="active" 조합 유효. 미지정 시 deactivated 이미지가 포함됨
"""


def list_active_by_tag(conn, tag):
    """tag가 부여된 active 이미지를 이름순으로 반환함.

    반환 필드는 잠정임 — C단계에서 포털이 실제 사용하는 항목 확인 후 조정함.
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