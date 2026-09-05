#!/usr/bin/env bash

set -u

BUILD_USER="imagebuilder"

# 이 스크립트는 systemd-run으로 분리 실행하는 것을 전제로 한다.
# SSH 요청이 정상 종료될 시간을 조금 준다.
sleep 3

# ── Build VM 전용 계정 제거 ───────────────────────────────

pkill -KILL -u "${BUILD_USER}" 2>/dev/null || true

userdel -r "${BUILD_USER}" 2>/dev/null || true

# cloud-init이 만든 sudoers 항목이 남아 있으면 제거
for file in /etc/sudoers.d/*; do
    [ -f "${file}" ] || continue
    sed -i "/^${BUILD_USER}[[:space:]]/d" "${file}" || true
done

# ── SSH 인증 키 제거 ───────────────────────────────────────

rm -f /root/.ssh/authorized_keys

# ── cloud-init 초기화 ─────────────────────────────────────

cloud-init clean --logs || true

rm -rf /var/lib/cloud/instances/*


# ── 머신 고유 정보 초기화 ────────────────────────────────

truncate -s 0 /etc/machine-id

if [ -f /var/lib/dbus/machine-id ] && [ ! -L /var/lib/dbus/machine-id ]; then
    rm -f /var/lib/dbus/machine-id
fi


# ── SSH Host Key 제거 ─────────────────────────────────────

rm -f /etc/ssh/ssh_host_*


# ── 임시 파일 정리 ────────────────────────────────────────

rm -rf /tmp/*
rm -rf /var/tmp/*


# 최종 이미지에는 cleanup 스크립트 자체도 남기지 않는다.
rm -f /usr/local/sbin/su-image-cleanup.sh

sync

# 이후 Nova Snapshot을 뜰 수 있도록 VM을 종료한다.
poweroff
