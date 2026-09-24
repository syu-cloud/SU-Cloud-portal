"""Nova Flavor 조회."""


def get(conn, flavor_id):
    """단일 Flavor를 조회하고 API에서 사용할 기본 정보를 반환한다."""
    flavor = conn.compute.find_flavor(
        flavor_id,
        ignore_missing=True,
    )

    if flavor is None:
        return None

    return {
        "id": flavor.id,
        "name": flavor.name,
        "vcpus": flavor.vcpus,
        "ram_mb": flavor.ram,
        "disk_gb": flavor.disk,
    }
