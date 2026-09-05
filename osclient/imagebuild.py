import base64
import os
import subprocess
import time

from osclient.vm import wait_ssh


BUILD_USER = "imagebuilder"

CLEANUP_PATH = (
    "/usr/local/sbin/"
    "su-image-cleanup.sh"
)

CLEANUP_UNIT = "su-image-cleanup"


# =========================================================
# 기본 정보
# =========================================================

def name_for(build_id):
    """Image Build VM 이름을 반환한다."""

    return f"image-build-{build_id}"


def fip_for():
    """Image Build 전용 Floating IP를 반환한다."""

    return os.environ[
        "SU_IMAGE_BUILD_FIP"
    ]


def build_user_data(
    pubkey,
    cleanup_script,
):
    """Build VM용 cloud-init user-data를 생성한다."""

    wg_pubkey = os.environ[
        "WG_PUBKEY"
    ]

    cleanup_b64 = (
        base64.b64encode(
            cleanup_script.encode()
        )
        .decode()
    )

    user_data = f"""#cloud-config
users:
  - name: {BUILD_USER}
    groups: [sudo]
    sudo: ALL=(ALL) NOPASSWD:ALL
    shell: /bin/bash
    ssh_authorized_keys:
      - {pubkey}
      - {wg_pubkey}

write_files:
  - path: {CLEANUP_PATH}
    owner: root:root
    permissions: '0700'
    encoding: b64
    content: {cleanup_b64}
"""

    return (
        base64.b64encode(
            user_data.encode()
        )
        .decode()
    )


# =========================================================
# Build VM 생성
# =========================================================

def create(
    conn,
    build_id,
    image_id,
    key_path,
    cleanup_script,
):
    """Build VM을 생성하고 전용 FIP와 SSH 접속까지 준비한다."""

    if not image_id:
        raise ValueError(
            "image_id is required"
        )

    name = name_for(
        build_id
    )

    server = _find_existing_server(
        conn,
        name,
    )

    # worker 재실행 시 같은 이름의 VM이 있으면 재사용한다.
    if server is None:
        server = _create_server(
            conn=conn,
            name=name,
            image_id=image_id,
            cleanup_script=cleanup_script,
        )

    server = conn.compute.wait_for_server(
        server,
        status="ACTIVE",
        failures=["ERROR"],
        interval=2,
        wait=600,
    )

    port = _get_server_port(
        conn,
        server.id,
    )

    fip = _get_build_fip(
        conn
    )

    # Build 전용 FIP가 다른 VM에 연결되어 있으면 탈취하지 않는다.
    if (
        fip.port_id
        and fip.port_id != port.id
    ):
        raise RuntimeError(
            f"image build FIP "
            f"{fip.floating_ip_address} "
            "is already attached to "
            f"another port: {fip.port_id}"
        )

    if fip.port_id != port.id:
        conn.network.update_ip(
            fip,
            port_id=port.id,
        )

    wait_ssh(
        fip_for(),
        BUILD_USER,
        key_path,
    )

    return server


# =========================================================
# Snapshot 준비 / 생성
# =========================================================

def prepare_snapshot(
    conn,
    server_id,
    key_path,
):
    """Build VM을 cleanup한 뒤 SHUTOFF 상태까지 기다린다."""

    server = conn.compute.get_server(
        server_id
    )

    if server is None:
        raise RuntimeError(
            f"server not found: "
            f"{server_id}"
        )

    # worker 재실행 시 cleanup을 중복 수행하지 않는다.
    if server.status == "SHUTOFF":
        return server

    if server.status != "ACTIVE":
        raise RuntimeError(
            "unexpected server status "
            "before snapshot: "
            f"{server.status}"
        )

    cleanup(
        conn=conn,
        server_id=server_id,
        key_path=key_path,
    )

    server = conn.compute.get_server(
        server_id
    )

    return conn.compute.wait_for_server(
        server,
        status="SHUTOFF",
        failures=["ERROR"],
        interval=2,
        wait=300,
    )


def cleanup(
    conn,
    server_id,
    key_path,
):
    """Build VM 내부 cleanup 스크립트를 별도 systemd unit으로 실행한다."""

    server = conn.compute.get_server(
        server_id
    )

    if server is None:
        raise RuntimeError(
            f"server not found: "
            f"{server_id}"
        )

    cmd = [
        "ssh",
        "-i",
        key_path,
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "UserKnownHostsFile=/dev/null",
        "-o",
        "ConnectTimeout=5",
        f"{BUILD_USER}@{fip_for()}",
        (
            "sudo systemd-run "
            f"--unit={CLEANUP_UNIT} "
            "--collect "
            f"{CLEANUP_PATH}"
        ),
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=30,
    )

    if result.returncode != 0:
        raise RuntimeError(
            "cleanup start failed: "
            f"{result.stderr.strip()}"
        )

    return result.stdout.strip()


def create_snapshot(
    conn,
    server_id,
    image_name,
):
    """SHUTOFF 상태의 Build VM에서 Glance Snapshot을 생성한다."""

    server = conn.compute.get_server(
        server_id
    )

    if server is None:
        raise RuntimeError(
            f"server not found: "
            f"{server_id}"
        )

    if server.status != "SHUTOFF":
        raise RuntimeError(
            "server must be SHUTOFF "
            "before snapshot: "
            f"{server.status}"
        )

    return conn.compute.create_server_image(
        server,
        name=image_name,
        wait=True,
        timeout=600,
    )


# =========================================================
# Build VM 삭제
# =========================================================

def delete_build_server(
    conn,
    server_id,
):
    """Build VM을 삭제하고 전용 FIP가 미할당 상태가 될 때까지 기다린다."""

    conn.compute.delete_server(
        server_id,
        ignore_missing=True,
    )

    deadline = (
        time.monotonic()
        + 120
    )

    while time.monotonic() < deadline:
        fip = _get_build_fip(
            conn
        )

        if not fip.port_id:
            return

        time.sleep(2)

    raise TimeoutError(
        "image build FIP was not detached: "
        f"{fip_for()}"
    )


# =========================================================
# 내부
# =========================================================

def _find_existing_server(
    conn,
    name,
):
    """동일 이름의 기존 Build VM을 찾는다."""

    return next(
        (
            server
            for server in conn.compute.servers(
                name=name
            )
            if (
                server.name == name
                and server.status != "DELETED"
            )
        ),
        None,
    )


def _create_server(
    conn,
    name,
    image_id,
    cleanup_script,
):
    """OpenStack에 새 Build VM을 생성한다."""

    keypair_name = os.environ[
        "SU_KEYPAIR"
    ]

    keypair = (
        conn.compute.get_keypair(
            keypair_name
        )
    )

    return conn.compute.create_server(
        name=name,
        image_id=str(image_id),
        flavor_id=os.environ[
            "SU_IMAGE_BUILD_FLAVOR_ID"
        ],
        networks=[
            {
                "uuid": os.environ[
                    "SU_NETWORK_ID"
                ]
            }
        ],
        key_name=keypair_name,
        security_groups=[
            {
                "name": os.environ[
                    "SU_SECGROUP"
                ]
            }
        ],
        user_data=build_user_data(
            keypair.public_key,
            cleanup_script,
        ),
    )


def _get_server_port(
    conn,
    server_id,
):
    """Build VM의 Neutron port를 반환한다."""

    port = next(
        conn.network.ports(
            device_id=server_id
        ),
        None,
    )

    if port is None:
        raise RuntimeError(
            "server port not found: "
            f"{server_id}"
        )

    return port


def _get_build_fip(conn):
    """Image Build 전용 Floating IP 객체를 반환한다."""

    fip_address = fip_for()

    fip = next(
        conn.network.ips(
            floating_ip_address=(
                fip_address
            )
        ),
        None,
    )

    if fip is None:
        raise RuntimeError(
            "image build FIP not found: "
            f"{fip_address}"
        )

    return fip