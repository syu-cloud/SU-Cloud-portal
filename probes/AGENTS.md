<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-09-05 | Updated: 2026-09-05 -->

# probes

## 목적
파이프라인을 만들면서 작성한 일회성 탐색·부하 테스트 스크립트. **실제 개발계 OpenStack 테넌트와 운영 중인 PostgreSQL DB** 를 대상으로 하고, 개발계 UUID·IP 가 하드코딩되어 있으며, 여러 개가 상태를 변경하거나 파괴한다. 테스트가 아니고 애플리케이션 코드가 import 하지도 않는다.

`osclient` 와 `config` 가 import 되도록 `/opt/su-portal` 에서 실행한다: `.venv/bin/python probes/<name>.py`.

## 주요 파일

### OpenStack 전용 (`osclient` import, Django 없음)
| 파일 | 설명 | 부작용 |
|------|------|--------|
| `check_sdk.py` | `OS_*` 변수로 연결해 compute 쿼터 사용량 출력 | 읽기 전용 |
| `inspect_resources.py` | image, flavor, network, keypair, security group, Neutron 쿼터 나열 | 읽기 전용 |
| `inspect2.py` | Neutron 쿼터 원본, 라우터와 포트, ingress SG 규칙, 서버, FIP 덤프 | 읽기 전용 |
| `create_vm.py` | keypair `sdk-probe-key` 가 없으면 생성(`.pem` 기록) 후 cirros `sdk-probe-01` 부팅 | VM·키 파일 생성 |
| `create_ubuntu.py` | ubuntu `sdk-probe-02` 부팅, FIP `.179` 연결, `ubuntu` / `root` SSH 도달 시간 측정 | VM 생성 |
| `create_ubuntu_ud.py` | 위와 같되 cloud-config user_data 로 사용자 `student` 생성(`sdk-probe-03`, FIP `.181`). `osclient.vm.USER_DATA` 의 원형 | VM 생성 |
| `attach_fip.py` | 하드코딩된 서버에 FIP `.28` 연결 후 `cirros` 로 SSH 대기 | 네트워크 변경 |
| `delete_vm.py` | 하드코딩된 서버 삭제 후 포트와 FIP 잔존 여부 보고 | VM 삭제 |
| `probe_parallel.py` | 슬롯 2–6 에 대해 5스레드로 `osclient.vm.create`, 소요 시간 출력 | VM 5대 생성 |

### Django 기반 (`django.setup()` 호출, `provisioning.services` 사용)
| 파일 | 설명 | 부작용 |
|------|------|--------|
| `probe_reserve.py` | 50스레드가 `reserve()` 호출. 정확히 45건 성공·슬롯 중복 없음 확인 | 45슬롯 전부 TAKEN, 최대 45개 `Vm(PROVISIONING)` 행 생성 |
| `probe_provision.py` | **모든 Slot 을 TAKEN 으로 바꾸고 2–6 만 FREE 로 연 뒤** 5건을 병렬 reserve + provision | Slot 테이블 재작성, VM·Warpgate 좌석 생성 |
| `probe_deprovision.py` | **모든 ACTIVE Vm** 을 5스레드로 deprovision | 활성 VM 전부와 Warpgate 좌석 삭제 |

## AI 에이전트 안내

### 이 디렉터리에서 작업할 때
- **운영자의 명시적 의사 없이 어떤 probe 도 실행하지 말 것.** Django 기반 3개는 개발계 DB 를 다시 쓰고, `create_*` / `delete_*` / `attach_*` 는 실제 클라우드 자원을 건드린다.
- 하드코딩된 ID(image `36fdb4fc…`, flavor `f62c57b7…`, network `16dfa71b…`, FIP `192.168.100.x`, 서버 UUID)는 2026-08 시점 개발계 테넌트의 것이며 지금은 없을 수 있다.
- 스레드 기반 Django probe 는 `finally: connection.close()` 로 스레드별 DB 연결을 닫는다. 패턴을 복사할 때 유지할 것.
- 클라우드 없이 검증 가능한 것은 새 probe 대신 `provisioning/tests.py` 에 추가하는 편이 낫다.

### 테스트 요구사항
- 이 스크립트들이 현재의 통합 검증 수단이다. 출력은 눈으로 읽는다. assertion 프레임워크는 없다.

## 의존성

### 내부
- `osclient`, `provisioning.models`, `provisioning.services`, `config.settings`

### 외부
- openstacksdk, Django, 표준 라이브러리 `concurrent.futures`, `subprocess`(`ssh`)

<!-- MANUAL: 이 줄 아래에 수동으로 추가한 내용은 재생성 시 보존됨 -->
