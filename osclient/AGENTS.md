<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-09-05 | Updated: 2026-09-05 -->

# osclient

## 목적
`openstacksdk` 얇은 래퍼. `OS_*` env 변수로 연결을 만들고 슬롯별 VM 생명주기를 구현한다: 이름 / 계정 / FIP 도출, cloud-init user_data 를 포함한 생성, Floating IP 연결, SSH 도달 대기, 삭제. Django 를 import 하지 않는 순수 라이브러리라 `probes/` 스크립트가 단독으로 쓸 수 있다.

## 주요 파일
| 파일 | 설명 |
|------|------|
| `__init__.py` | `get_conn()` → `OS_AUTH_URL`, `OS_USERNAME`, `OS_PASSWORD`, `OS_PROJECT_NAME`, `OS_USER_DOMAIN_NAME`, `OS_PROJECT_DOMAIN_NAME`, `OS_REGION_NAME`, `OS_INTERFACE`, `OS_COMPUTE_API_VERSION` 으로 `openstack.connect(...)`. `/opt/su-portal/.env` 로드. |
| `vm.py` | `name_for(n)="vm{n}"`, `user_for(n)="student{n}"`, `fip_for(n)=SU_FIP_PREFIX+str(100+n)`. `USER_DATA` cloud-config 템플릿, `build_user_data(n, pubkey)`, `wait_ssh(host, user, key_path, timeout=300)`, `create(conn, n, key_path)`, `delete(conn, server_id)`. |

## `create` 동작
1. keypair `SU_KEYPAIR` 의 공개키를 가져온다.
2. `create_server(name=vm{n}, image_id=SU_IMAGE_ID, flavor_id=SU_FLAVOR_ID, networks=[SU_NETWORK_ID], key_name=SU_KEYPAIR, security_groups=[SU_SECGROUP], user_data=...)`. user_data 는 비밀번호 없는 sudo 사용자 `student{n}` 을 만들고 `authorized_keys` 에 keypair 공개키와 `WG_PUBKEY` 를 함께 넣는다.
3. `wait_for_server(status="ACTIVE", wait=600)`.
4. **사전 할당된** Floating IP `fip_for(n)` 을 서버의 첫 포트에 연결한다. FIP 는 여기서 생성하지 않는다.
5. `wait_ssh(fip, student{n}, key_path)`. ACTIVE 는 준비 완료가 아니다. SSH 도달이 준비 완료다.

`delete` 는 `delete_server` 후 `wait_for_delete(wait=300)`. 포트 제거와 FIP 분리는 Neutron 이 처리한다(`probes/delete_vm.py` 로 확인됨).

## AI 에이전트 안내

### 이 디렉터리에서 작업할 때
- 이 모듈은 Django 의존성 없이 유지한다.
- `WG_PUBKEY` 는 필수(`os.environ["WG_PUBKEY"]`)지만 `.env.example` 에 없다. 값은 `wgclient.WarpgateClient.own_keys()` 의 ed25519 키. 없으면 `create` 가 즉시 실패하는 게 의도다.
- `n → vm{n} / student{n} / FIP` 도출 규칙은 `provisioning.services._reconcile`, `provisioning.admin`, `wgclient.provision_seat` 이 의존한다. 바꾸면 기존 서버와의 대조가 깨진다.
- `wait_ssh` 는 워커 호스트에 `ssh` 바이너리와 `key_path`(`/opt/su-portal/sdk-probe-key.pem`) 개인키가 필요하다. host key 검사는 꺼져 있다.
- 예외는 그대로 전파된다. FAILED 처리냐 재시도냐는 호출자(`services.provision`)가 결정한다.

### 테스트 요구사항
- 단위 테스트 없음. `probes/probe_parallel.py` 가 실제 개발계 클라우드에서 슬롯 2–6 에 대해 `vm.create` 를 동시 실행한다.

## 의존성

### 외부
- openstacksdk 4.18(`conn.compute`, `conn.network`), python-dotenv, 표준 라이브러리 `subprocess` / `base64`
- PATH 상의 `ssh` 클라이언트

<!-- MANUAL: 이 줄 아래에 수동으로 추가한 내용은 재생성 시 보존됨 -->
