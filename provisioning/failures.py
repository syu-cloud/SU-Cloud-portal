"""VM provisioning 실패 원인을 사용자 표시용 정보로 변환한다.

REST API와 legacy Django Portal이 동일한 실패 해석 규칙을 공유한다.
"""

FAILED_DESCRIPTIONS = {
    "잘못된 요청 (설정값 오류)": "image·flavor·network 설정값에 문제가 있어요. 운영자 확인이 필요해요.",
    "인증 만료": "작업 중 OpenStack 인증이 만료됐어요. 운영자 확인이 필요해요.",
    "자원 한도 초과 (Quota)": "할당된 자원(인스턴스/코어/IP) 한도를 초과했어요.",
    "리소스 없음 (image/flavor/network 설정 오류)": "설정된 flavor·image·network를 찾을 수 없어요. 운영자 확인이 필요해요.",
    "VM 인스턴스 소실": "OpenStack에 등록된 VM을 찾을 수 없어요. 수동으로 삭제됐거나 동기화 문제일 수 있어요. 운영자 확인이 필요해요.",
    "IP 충돌": "지정된 FIP가 이미 다른 VM에서 사용 중이에요.",
    "이름/상태 충돌": "같은 이름의 서버가 이미 존재하거나 상태가 충돌했어요.",
    "생성 실패 (자원 부족 또는 빌드 오류)": "서버 생성 중 오류가 발생했어요. 운영자 확인이 필요해요.",
    "생성 시간 초과": "VM이 정해진 시간 안에 준비되지 못했어요.",
    "접속 확인 시간 초과": "VM은 만들어졌지만 접속 확인이 시간 내 되지 않았어요.",
    "포트/FIP 조회 실패": "네트워크 포트 또는 FIP를 찾지 못했어요. 자원이 삭제됐거나 설정이 어긋났을 수 있어요. 운영자 확인이 필요해요.",
    "네트워크/IP 할당 실패": "네트워크 또는 외부 IP 연결에 문제가 있었어요.",
    "실패": "원인을 특정하지 못했어요. 아래 원본 로그를 확인해주세요.",
}


def friendly_label(error: str) -> str:
    """워커가 남긴 예외 문자열을 사용자 표시용 라벨로 변환한다."""
    e = error.lower()

    if "badrequest" in e:
        return "잘못된 요청 (설정값 오류)"

    if " 401" in e:
        return "인증 만료"

    if "forbidden" in e:
        return "자원 한도 초과 (Quota)"

    if "notfound" in e or " 404" in e:
        if "/servers/" in e:
            return "VM 인스턴스 소실"
        return "리소스 없음 (image/flavor/network 설정 오류)"

    if "conflict" in e or " 409" in e:
        return "IP 충돌" if ("fip" in e or "floating" in e) else "이름/상태 충돌"

    if "resourcefailure" in e:
        return "생성 실패 (자원 부족 또는 빌드 오류)"

    if "resourcetimeout" in e or "timeout" in e:
        return "접속 확인 시간 초과" if "ssh" in e else "생성 시간 초과"

    if "stopiteration" in e:
        return "포트/FIP 조회 실패"

    if "neutron" in e or "floating" in e or "port" in e:
        return "네트워크/IP 할당 실패"

    return "실패"
