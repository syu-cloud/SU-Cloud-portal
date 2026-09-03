import base64
import os
import subprocess
import time

USER_DATA = """#cloud-config
users:
  - name: student{n}
    groups: [sudo]
    sudo: ALL=(ALL) NOPASSWD:ALL
    shell: /bin/bash
    ssh_authorized_keys:
      - {pubkey}
      - {wg_pubkey}
"""


def name_for(n):
    return f"vm{n}"


def user_for(n):
    return f"student{n}"


def fip_for(n):
    return os.environ["SU_FIP_PREFIX"] + str(100 + n)


def build_user_data(n, pubkey):
    """관리용 키(pubkey) + Warpgate 자체 키(WG_PUBKEY) 를 함께 주입.
    WG_PUBKEY 가 없으면 Warpgate 가 VM 에 접속할 수 없으므로 즉시 실패시킴.
    값은 wgclient.own_keys() 의 ed25519 public_key 를 .env 에 넣는다."""
    ud = USER_DATA.format(n=n, pubkey=pubkey, wg_pubkey=os.environ["WG_PUBKEY"])
    return base64.b64encode(ud.encode()).decode()


def wait_ssh(host, user, key_path, timeout=300):
    """SSH 도달까지 대기. ACTIVE는 준비 완료 신호가 아님."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = subprocess.run(
            ["ssh", "-i", key_path,
             "-o", "StrictHostKeyChecking=no",
             "-o", "UserKnownHostsFile=/dev/null",
             "-o", "ConnectTimeout=3",
             f"{user}@{host}", "true"],
            capture_output=True,
        )
        if r.returncode == 0:
            return
        time.sleep(5)
    raise TimeoutError(f"ssh unreachable: {user}@{host}")


def create(conn, n, key_path, image_id=None):
    """VM 생성 → FIP 연결 → SSH 도달까지. 실패 시 예외를 올림."""
    keypair = os.environ["SU_KEYPAIR"]
    pubkey = conn.compute.get_keypair(keypair).public_key

    server = conn.compute.create_server(
        name=name_for(n),
        image_id=image_id or os.environ["SU_IMAGE_ID"],
        flavor_id=os.environ["SU_FLAVOR_ID"],
        networks=[{"uuid": os.environ["SU_NETWORK_ID"]}],
        key_name=keypair,
        security_groups=[{"name": os.environ["SU_SECGROUP"]}],
        user_data=build_user_data(n, pubkey),
    )
    server = conn.compute.wait_for_server(server, status="ACTIVE", wait=600)

    port = next(conn.network.ports(device_id=server.id))
    fip = next(conn.network.ips(floating_ip_address=fip_for(n)))
    conn.network.update_ip(fip, port_id=port.id)

    wait_ssh(fip_for(n), user_for(n), key_path)
    return server


def delete(conn, server_id):
    """포트·FIP는 Neutron이 함께 정리함."""
    conn.compute.delete_server(server_id)
    conn.compute.wait_for_delete(conn.compute.get_server(server_id), wait=300)