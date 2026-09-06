# 90대 2분반 운영 전환 — 현안 정의 및 의사결정 항목

> **작성**: 2026-09-05 · **상태**: 의사결정 대기 · **성격**: 살아 있는 문서 (결정되면 해당 항목에 결정·일자·근거를 덧붙임)
> **근거 자료**
> - SU Cloud 주간회의 (2026-08-30) — Phase 0.5 시연 검토, Phase 1 범위·설계 과제
> - 90대 운영 방식 — 운영계 오버커밋 검증 (2026-09-04, su-cloud-prod .179)
> - 레포 코드: `main`, `origin/Phase_0.5_prod` (2026-09-05 기준) 및 `docs/02`·`03`
> - 개인 정보·자격증명·예산 세부는 회의록 원문(Notion)에만 두고 여기에는 적지 않음

---

## 1. 한눈에 보기

- 결정된 것: 이번 학기 두 분반을 **오버커밋(ram 2.0 / cpu 6.0 / disk 1.0) + 45대씩 stop/start 교대**로 운영. shelve(디스크 압박)·컨테이너(현 상태와 차이 없음)는 기각
- 검증된 것: 운영계에서 90대 등록, 45↔45 전환 2회(각 149초), IP 보존, 90대 삭제까지 완료. 운영계는 현재 VM 0대·ratio 2.0 상태로 대기 중
- 남은 것: 포털을 "45대 단일 분반" 에서 "90대 2분반 + 전원 전환" 으로 바꾸는 설계 결정 8건이 코딩을 막고 있음 (§5 차단 항목)
- 가장 급한 결정: 플레이버 디스크 크기(D1), Slot 분반 표현(D2), 명명 규칙 오프셋 불일치 해소(D3), `_reconcile` 의 SHUTOFF 처리(D7)
- 새로 드러난 위험: 오버커밋을 켜면 `NoValidHost` 인프라 방어선이 사라져 "45대만 켠다" 는 규칙을 **포털 코드와 운영 절차가 대신 지켜야 함**

---

## 2. 배경과 현재 위치

- Phase 0.5 시연 완료 (08-30): 임시 로그인 → VM 일괄 생성 → FIP 연결 → Warpgate user·role·target 등록 → 웹터미널 접속 → 선택/전체 회수까지 연결됨. 45대 생성 약 3분 30초
- 교수 요구: 두 수업(분반) 운영, "45대 기동 / 45대 정지" 로 단순 전환. 개강 완료, 수업 투입 임박
- 09-04 운영계 검증으로 방식 확정. 검증은 포털·Warpgate 를 건드리지 않고 CLI 로만 수행 → **포털 반영은 전부 미착수**
- 코드 위치
  - `main`: 백엔드만 (provisioning·osclient·wgclient). `portal/` 은 자리표시자
  - `origin/Phase_0.5_prod`: 포털 UI, `imagebuild` 앱, 이미지 카탈로그(`reserve(student_id, image_id, image_name)`), `VmFailure` 포함. 실제 운영 코드
- 운영계 잔존 상태 (09-04 종료 시점)

| 항목 | 상태 |
|---|---|
| VM | 0대 (장부 used 0) |
| nova-compute.conf | ram 2.0 / cpu 6.0 / disk 1.0 유지 |
| Quota (admin) | instances 100 / cores 200 / ram 200,000 / fip 100 |
| 플레이버 | `su-test-20` (2 vCPU / 2048 MB / 20 GB) 신설, `su-small` 30 GB 미변경 |
| FIP | 46개 (.101~.145, .151) |
| 포털 Slot | FREE 45 (A분반 상당) |
| 워커 | `su-portal-worker@{1..8}` 활성 |

---

## 3. 확정된 사실 (재논의 불필요)

- 90대 동시 기동 불가. 45대 풀가동만으로 RAM 114 GB → 물리 125 GiB 수용 불가. **45대 교대는 선택이 아니라 필수**
- 45대 교대는 안전. 부하 시 103 GB 까지 올라가도 swap 0, 부하 해제 시 자동 회수
- 전환 구간에 90대가 잠시 겹쳐도 안전 (유휴 90대 약 94 GB). 따라서 **start 를 먼저, stop 을 나중에** 실행 가능 → 수업 전 선행 기동 가능
- 디스크는 씬 프로비저닝. 장부 1,800 GB 대비 실사용 7.3 GB (0.4%)
- OVN 에서 stop/start 시 고정 IP 보존 (개발계 OVS 에 이어 운영계도 확인)
- 전환 소요 149초는 CLI 순차 기준. 워커 8개 병렬 시 단축 예상 (45대 발급 시 워커 대당 4.8초 실측)
- `ram_allocation_ratio` 는 설정 파일 삭제로 원복되지 않음. Placement DB 값이므로 롤백 시 `= 1.0` 명시 또는 `inventory set`
- `resume_guests_state_on_host_boot` 기본값 false 유지 확인 (개발계 재부팅 실측). 켜지면 재부팅 시 90대 동시 기동 → 가장 현실적인 사고 시나리오
- 검증 수치

| 항목 | 결과 |
|---|---|
| 90대 등록 (45 ACTIVE / 45 SHUTOFF) | 성공 |
| MEMORY_MB 장부 | 184,320 / 215,812 |
| VCPU 장부 | 180 / 192 |
| DISK_GB 장부 | 1,800 / 1,876 (여유 76 GB) |
| 물리 RAM (90대 등록, 유휴) | 36 GB, swap 0 |
| 45↔45 전환 1·2회차 | 149초 / 149초 |
| IP 보존 | 90대 전량 일치 |
| 90대 삭제 (병렬 10) | 20초 |

---

## 4. 현안 정의 — 지금 고민하는 것

### 4-1. 인프라
- 플레이버 디스크: `su-small` 30 GB 유지 시 90 × 30 = 2,700 GB > 장부 1,876 GB. 20 GB 면 1,800 GB 로 들어감. 플레이버는 불변 객체라 재생성 시 UUID 변경
- 교수 VM(`su-xlarge`, 디스크 100 GB) 복귀 시 20 GB 로도 1,900 > 1,876 → 그 시점에 `disk_allocation_ratio` 1.1 필요
- as-built 문서의 `/var/lib/nova` 용량 1,905 GB 는 Placement 실제값 1,876 GB 와 불일치 → 정정 필요
- FIP 할당 풀이 `.101~.200` 이라 자기서비스용 `.201+` 사용 불가 → 풀 확장(비파괴) 선행 필요
- 테넌트 서브넷 분반 분리 여부와 분반 간 격리 수준. Provider 네트워크는 분리하지 않음(VLAN/NIC 필요, 실익 없음)
- 분반별 Keystone 프로젝트 분리 여부 (Quota 강제 vs 포털 인증 구조 전면 변경)

### 4-2. 포털 데이터 모델
- `Slot` 은 `n` 이 PK(1~45) 이고 분반 개념이 없음. 90개로 늘리면서 분반을 어떻게 표현할지
- `Vm.status` 는 PROVISIONING / ACTIVE / DELETING / FAILED / DELETED 만 있음. SHUTOFF 가 **정상 상태**로 추가되어야 하고, START/STOP 작업을 큐에 어떻게 표현할지
- 학생이 VM 안에서 `sudo poweroff` 하면 Nova 는 SHUTOFF, 포털 DB 는 ACTIVE 로 어긋남 → 동시 기동 카운트의 진실 원천

### 4-3. 명명 규칙과 외부 연동
- "번호 하나가 호스트명·FIP·계정·비밀번호를 결정" 하는 원칙은 유지하되 분반 접두사와 FIP 오프셋을 분기해야 함
- **원문 불일치**: 검증 문서 §6-4 는 B분반 FIP 를 `.150+N` (.151~.195) 으로, §7-2·§7-7 은 `FIP_BASE B=155` (vm-b7 → .162, vm-b1 → .156) 으로 적음. 하나로 확정하지 않으면 FIP 충돌
- 규칙이 코드 여러 곳에 흩어져 있음: `osclient/vm.py` (`name_for`/`user_for`/`fip_for`), `wgclient/__init__.py` (`provision_seat` 내부의 `student{n}`/`slot-{n}`/`vm{n}` f-string), `provisioning/services.py` (비밀번호 `Student{n}!`), `provisioning/admin.py`·`portal/services.py` (표시·검색)
- Warpgate role 이름 `slot-{n}` 도 분반을 포함해야 함 (검증 문서는 계정·호스트만 언급)

### 4-4. 워커·서비스 로직
- 45↔45 전환 커맨드가 없음 (현재 `issue`·`reclaim` 만). start 선행 → stop 후행 순서, 워커 병렬 처리, 완료 후 Nova → DB 동기화가 필요
- `_reconcile` 은 "서버가 ACTIVE 면 입양, **그 외 상태면 삭제 후 재생성**". SHUTOFF 가 정상이 되면 정지 중인 VM 이 재시도 경로에서 삭제될 수 있음 → 반드시 수정
- 오버커밋으로 인프라 방어선이 사라짐 → 동시 기동 상한(45) 가드를 포털이 가질지, 운영 절차로 둘지
- Warpgate 타깃 90개가 학기 내내 유지됨 → 정지 분반 학생이 접속하면 연결 실패. 안내 방법
- 워커 재시도 상한 없음, 드리프트 감지 없음 (08-30 회의 이월). 이번 범위에 넣을지

### 4-5. 브랜치·배포·구조 (08-30 회의 이월)
- 작업 기준 브랜치: 90대 작업은 포털 UI·admin·issue 커맨드를 모두 건드리므로 `main` 이 아닌 `Phase_0.5_*` 계열이어야 함. `main` 정리 시점
- systemd 네이티브(`su-portal-web`, `su-portal-worker@{1..8}`) → 최소 Docker 컨테이너화 시점
- DB polling 유지 vs Celery/Redis. 이번 학기 유지에 합의했으나 전환 경계 미정
- 프론트/백 분리, 가입 승인·프로젝트·Quota·자격증명 전달 self-service flow (Phase 1)
- 자격증명 전달: 현재 규칙 기반 비밀번호를 워커 로그에만 출력. 90대에서 로그 의존은 운영 부담

### 4-6. 하드웨어·운영 (08-30 회의 이월)
- P520 인수 가능성·일정, 교수 PC 구매, RTX 5090 배치, 예산 범위, 컨트롤러 노드 신규 여부, 메모리 증설 → 교수 확인 대기. 전달 내용이 서로 충돌하므로 확인 전 결정으로 기록하지 않음
- 90대 운영은 현 운영계(W-2295 18C/36T, 125 GiB)로 검증 완료 → **하드웨어 결정이 이번 전환을 차단하지 않음**

---

## 5. 의사결정 항목

- 표기: **[차단]** = 결정 전 코딩 착수 불가, **[병행]** = 코딩과 병행 가능, **[후속]** = 이번 학기 이후 가능

### D1. 플레이버 디스크 크기와 disk_allocation_ratio **[차단]**

| 선택지 | 90대 요구 | 필요 ratio | 비고 |
|---|---|---|---|
| (a) 20 GB | 1,800 GB | 1.0 | 오버커밋 불필요. Docker 실습 여유 감소 |
| (b) 25 GB | 2,250 GB | 1.2 | 절충 |
| (c) 30 GB 유지 | 2,700 GB | 1.5 | 여유 크나 ENOSPC 시 90명 동시 피해 |

- 권고: (a) 20 GB. 장부 초과를 인프라가 막지 못하는 구조에서 디스크 ratio 는 1.0 으로 두는 것이 안전. 실사용 0.4% 라 학생 체감 여유는 충분
- 조건부 후속: 교수 VM(100 GB) 복귀 시 1,900 > 1,876 → 그때 `disk_allocation_ratio 1.1` 별도 결정
- 영향: 플레이버 재생성 → UUID 변경. 포털은 `SU_FLAVOR_ID` 로 **ID 참조**(`osclient/vm.py`) → 운영계 `.env` 갱신 + 워커 8개 재시작. `imagebuild` 의 `SU_IMAGE_BUILD_FLAVOR_ID` 도 점검
- 부수: as-built 문서 1,905 → 1,876 GB 정정

### D2. Slot 모델의 분반 표현 **[차단]**

| 선택지 | 내용 | 장점 | 단점 |
|---|---|---|---|
| (a) 검증 문서안 | `Slot(section, number)` + `unique_together`, PK 교체 | 의미 명확 | 현재 PK 가 `n` 이고 `Vm.slot` FK 와 append-only 이력(300+ 행)이 참조 → PK 교체 마이그레이션이 침습적 |
| (b) 대안 | `n` PK 유지·1~90 확장 + `section` 필드 (1~45=A, 46~90=B). 분반 내 번호는 `n` 또는 `n-45` 로 계산 | 이력 FK 무변경, `*_for(n)` 시그니처 유지 가능(내부에서 분반 도출), 시딩 45건 추가로 끝 | 번호 의미가 두 겹(`n` 과 분반 내 번호) |

- 권고: (b). 학기 중 긴급 작업이므로 마이그레이션 위험 최소화 우선. `section` 은 저장 필드로 두되 `n` 과의 일관성을 `save()`/시딩에서 강제
- 영향: `reserve()` 가 가장 낮은 FREE 슬롯을 집으므로 분반 필터 인자 필요. `issue --section`, admin 액션, 포털 생성 모달에 분반 선택 추가

### D3. 명명 규칙 확정 **[차단]**

| 대상 | 현재 (`n`) | 제안 (분반 A, 번호 N) | 제안 (분반 B, 번호 N) | 결정 포인트 |
|---|---|---|---|---|
| 호스트명 / Warpgate target | `vm{n}` | `vm-a{N}` | `vm-b{N}` | 하이픈 도입. `_reconcile` 이 이름으로 서버 조회하므로 일관성 필수 |
| FIP | `.100+n` | `.100+N` (.101~.145) | **`.150+N` (.151~.195) vs `.155+N`** | 원문 불일치 해소. 권고 **150** (§6-4 표, 예비 .196~.200, 자기서비스 .201~ 과 정합) |
| Warpgate user / 리눅스 계정 | `student{n}` | `student-a{N}` | `student-b{N}` | cloud-init `USER_DATA` 도 동일 계정 생성 |
| Warpgate role | `slot-{n}` | `slot-a{N}` | `slot-b{N}` | 검증 문서 미언급. 추가 결정 |
| 비밀번호 (임시 규칙) | `Student{n}!` | `Student-a{N}!` 등 | 동일 | 분반 포함 여부. 공지 문구 명확성 위해 포함 권고 |
| 자기서비스 (후속) | — | `rvm{M}` / `user{M}` / `.200+M` | — | 이번 범위 밖, 대역만 예약 |

- 권고: 규칙을 **한 모듈**(예: `provisioning/naming.py`)에 모으고 osclient·wgclient·services·admin·portal 이 전부 참조. 현재 4곳 이상 분산되어 있어 한 곳만 바꾸면 OpenStack 과 Warpgate 의 좌표계가 어긋남
- 영향: `wgclient.provision_seat(n, ...)`/`deprovision_seat(n)` 이 내부에서 이름을 만들므로 이름 세트를 인자로 받도록 변경. `osclient.vm.fip_for`/`user_for`/`name_for` 호출부 전수 수정

### D4. 테넌트 네트워크 분리와 분반 간 격리 수준 **[차단]**

| 선택지 | 내용 | 비용 | 비고 |
|---|---|---|---|
| (a) 서브넷 분리 + SG CIDR 차단 | `class-a 10.10.10.0/24`, `class-b 10.10.20.0/24`, 분반 간 CIDR 기준 차단 | 네트워크 2개, SG 분반별 | 완전 격리. `--remote-group` 은 FIP 헤어핀 NAT 로 동작 안 함 → CIDR 만 가능 |
| (b) 서브넷 분리, 통신 허용 | 같은 라우터, L3 라우팅 허용 | 네트워크 2개 | IP 로 분반 판별 가능, 격리는 없음 |
| (c) 미분리 | 현 `internal.network` 단일 | 0 | 분반 판별 불가 |

- 권고: 검증 문서와 동일하게 분리(a 또는 b). 비용이 거의 없고 실익 있음. 격리 요구 수준은 교수 확인
- 영향: `SU_NETWORK_ID` 단일 env → 분반별 매핑. (a) 면 `SU_SECGROUP` 도 분반별. 프로젝트 분리(D5)를 하지 않으면 SG 는 한 프로젝트 안에서 2개 생성

### D5. 분반별 Keystone 프로젝트 분리 **[후속]**
- 얻는 것: Nova 가 API 접수 단계에서 Quota 45 강제, 실패 메시지 명확(`Quota exceeded`), 학기말 회수 프로젝트 단위
- 주의: Quota 는 SHUTOFF 도 1대로 셈 → "소유 45" 이지 "동시 기동 45" 가 아님. 동시 기동 제한은 여전히 포털 몫
- 비용: 포털이 단일 서비스 계정(`get_conn()`) 으로 동작 → 프로젝트별 계정 또는 `project_id` 분기. 모든 OpenStack 호출 경로에 영향. 프로젝트별 default SG 반복 생성
- 권고: **이번 학기 보류**, Phase 1 항목 (검증 문서 §9-5 동일)

### D6. 전원 상태·작업 타입 모델링 **[차단]**

| 선택지 | 내용 | 비고 |
|---|---|---|
| (a) `Vm.status` 확장 | `STARTING` / `STOPPING` / `SHUTOFF` 추가, `claim()` 필터에 STARTING·STOPPING 포함, `powered_at` 추가 | 기존 DB-as-queue 구조 그대로. `AlterField` 마이그레이션 수준 |
| (b) 별도 Job 테이블 | `Job(type=PROVISION/DELETE/START/STOP, vm, claimed_*)` | 상태와 작업 분리로 깔끔하나 워커·admin·포털 전면 수정 |

- 권고: (a). 속도 우선. 상태가 "생명주기 + 작업" 을 겸하는 점은 문서화로 감수
- 영향: 상태 추가 시 표현 계층 동반 수정 — `portal.services.STATUS_LIST`, admin `list_filter`, 진행바 계산, `friendly_label`

### D7. 진실 원천·카운트 기준과 `_reconcile` 의 SHUTOFF 처리 **[차단]**
- 동시 기동 카운트: (a) **Nova API 기준** (권고, 검증 문서 §7-3) vs (b) DB 기준. 학생 `sudo poweroff` 로 어긋나므로 (a). 학기당 수십 회라 API 비용 무시 가능
- `_reconcile` 수정 필수: 현재 ACTIVE 만 입양하고 나머지는 삭제·재생성. → **SHUTOFF 도 입양**(상태 SHUTOFF 로 기록), BUILD·ERROR 등만 삭제하도록 변경. 미수정 시 정지 분반 VM 이 재시도 경로에서 삭제될 위험
- 주기적 drift 감지(`_reconcile` 주기 실행, systemd timer)와 재시도 상한(`retry_count`)은 08-30 이월 항목. 이번 범위 포함 여부 결정. 권고: 전환 커맨드의 "완료 후 Nova → DB 동기화" 로 최소 커버, 주기 실행은 후속

### D8. 동시 기동 상한 가드 (ACTIVE_LIMIT 45) **[병행]**
- 검증 문서: 후순위. 학생은 Keystone 계정이 없고 기동 경로가 관리자 경유 → 46번째 기동 시나리오는 구조적으로 없음. 실제 위험은 관리자 실수(일괄 스크립트 오작동, 전환 시 이전 분반 정지 누락)
- 권고: 완전 가드는 후순위 유지. 단 `switch` 커맨드에 최소 방어 내장 — 대상 분반 start 큐 투입 전 다른 분반 stop 이 함께 큐에 들어가는지 검사, 실행 전 요약 출력, `--yes` 확인(기존 `reclaim` 과 동일 패턴)
- 운영 절차: 재부팅 시 `resume_guests_state_on_host_boot=false` 확인을 체크리스트에. 롤백 절차(45대 이하 축소 → ratio 1.0 **명시** → deploy → inventory 확인) 문서화

### D9. Warpgate 90 타깃 상시 등록과 정지 분반 접속 처리 **[병행]**
- 현재: 발급 시 등록, 회수 시 삭제. 90대 운영에서는 타깃·계정·role 90세트가 학기 내내 유지
- 정지 분반 학생이 접속 시도 → 연결 실패

| 선택지 | 내용 | 비고 |
|---|---|---|
| (a) 학생 공지 | "수업 시간 외 접속 불가" 안내 | 즉시 가능 |
| (b) 전환 시 role 바인딩 해제/복원 | 정지 분반 타깃을 학생 화면에서 숨김 | `wgclient.bind` 는 멱등이라 재바인딩 가능. 해제 API 는 미검증 → Warpgate 내부 DB·API 조사(08-30 액션) 후 |
| (c) Warpgate 레벨 안내 메시지 | — | 지원 여부 미확인 |

- 권고: (a) 로 시작, (b) 는 조사 결과 후. 90대에서도 고아 0 (users=targets=roles=90) 을 `status()` 로 검증

### D10. 작업 기준 브랜치와 `main` 정리 **[차단]**
- `main`: 백엔드만. `Phase_0.5_prod`: 포털 UI·imagebuild·이미지 카탈로그·VmFailure 포함. 90대 작업은 포털·admin·커맨드를 모두 건드림
- 권고: `Phase_0.5_dev` 에서 작업 → `Phase_0.5_prod` 병합 (기존 흐름 유지). `docs/`·`AGENTS.md`·`CLAUDE.md` 도 같은 브랜치로. `main` 은 전환 후 prod 를 병합해 정리
- 부수: `docs/00~06` 은 prod 중간 시점 스냅샷 → 전환 작업 후 `docs/02`·`03` 갱신

### D11. 컨테이너화 시점 **[후속]**
- 08-30 회의: 최소 Docker 전제. 09-04 검증: 컨테이너는 90대 문제엔 차이 없음
- 권고: 90대 전환 작업 **이후**. 지금은 env 전용 설정과 `su-portal-worker@{1..8}` 구조를 유지해 전환 비용 최소화

### D12. 큐 구조 **[후속]**
- 권고: 이번 학기 DB polling 유지 (회의 합의). `provisioning.services` 함수 경계를 큐 추상화 경계로 고정 → Celery 전환 시 `worker.py` 만 교체. START/STOP 도 같은 경계 안에 둠
- 전환 검토 조건(검증 문서): 워커 수십 개 규모, 작업 종류 다변화(스냅샷·백업·이미지 빌드), 초당 수십 건, 복잡 워크플로

### D13. 자격증명 전달 경로 **[후속]**
- 현재: 규칙 기반 비밀번호, 워커 로그에만 출력, DB 저장 금지
- 선택지: 규칙 공지 유지 / 포털 결과 화면 1회 표시(`set_password` 재호출) / 랜덤 + 1회 표시
- 권고: 이번 학기 규칙 기반 유지 + 포털에 규칙 안내 문구. Phase 1 에서 1회 표시. 로그 출력 줄은 중복(두 번 `log.info`) 정리

### D14. 하드웨어·예산 **[후속, 교수 확인 대기]**
- P520 인수 일정·소유, 교수 PC 구매 경로, RTX 5090 배치, 예산 범위, 컨트롤러 노드 신규 여부, 메모리 증설 조건
- 이번 전환은 현 운영계로 검증 완료 → 차단 아님. 확인 결과는 Phase 1 배치 설계(컨트롤러·컴퓨트 분리) 입력

### D15. FIP 할당 풀 확장과 대역 예약 **[차단, 비파괴]**
- 현재 풀 `.101~.200`. B분반(.151~.195) 은 들어가지만 자기서비스(.201~.245) 는 불가
- 권고: 지금 `.101~.245` 로 확장. 서브넷 재생성 불필요, 기존 FIP 유지, br-ex 가 `/24` 이고 MASQUERADE 도 `/24` 라 iptables 무변경
- 원칙: FIP 는 **주소를 명시해 생성**. 미지정 시 Neutron 임의 배정으로 결정론적 매핑이 깨짐
- 대역 계획 (자기서비스는 이번 범위 밖, 예약만)

| 구간 | 용도 |
|---|---|
| .1 / .2 | br-ex 게이트웨이 / tenant_router 외부 포트 |
| .101~.145 / .146~.150 | class-a / 예비 |
| .151~.195 / .196~.200 | class-b / 예비 |
| .201~.245 / .246~.254 | self-service / 예비 |

### 차단 항목 요약

| 항목 | 차단 여부 | 권고 |
|---|---|---|
| D1 플레이버 20 GB | 차단 | (a) 20 GB, ratio 1.0 |
| D2 Slot 분반 표현 | 차단 | (b) `n` 1~90 + `section` |
| D3 명명 규칙 | 차단 | B FIP base 150, naming 모듈 단일화 |
| D4 네트워크 분리 | 차단 | 서브넷 분리, 격리 수준은 교수 확인 |
| D6 상태·작업 모델 | 차단 | (a) `Vm.status` 확장 |
| D7 진실 원천·reconcile | 차단 | Nova 기준, SHUTOFF 입양 |
| D10 브랜치 | 차단 | `Phase_0.5_dev` |
| D15 FIP 풀 | 차단(비파괴) | 지금 `.245` 로 확장 |
| D8 / D9 | 병행 | 최소 방어 + 공지 |
| D5 / D11 / D12 / D13 / D14 | 후속 | Phase 1 |

---

## 6. 결정 후 실행 순서 (제안)

- 0 운영계 준비 (코드 무관, D1·D4·D15 결정 즉시)
  - 20 GB 플레이버 확정·`su-small` 교체 → `.env` `SU_FLAVOR_ID` 갱신 → 워커 재시작
  - FIP 풀 `.101~.245` 확장, B분반 FIP 45개 **주소 명시** 생성
  - `class-a`/`class-b` 네트워크·서브넷, 분반별 SG(선택) → `.env` 매핑
  - 검증: `openstack flavor show`, `floating ip list`, `network list`
- 1 명명 모듈 (`naming.py`) + `fip_for`/`hostname_for`/계정/role 분반 분기, osclient·wgclient·services·admin·portal 참조 교체
  - 검증: B분반 1번 → `vm-b1`, `.151`, `student-b1`, `slot-b1`
- 2 `Slot.section` 추가 + 46~90 시딩 마이그레이션 (멱등 `get_or_create`)
  - 검증: A/B 각 45 FREE
- 3 `issue --section`, admin 액션·포털 생성 모달에 분반 선택
  - 검증: B분반 1대 발급 → ACTIVE → Warpgate 등록 → 웹터미널 접속
- 4 `Vm.status` 에 STARTING/STOPPING/SHUTOFF + `powered_at`, `claim()` 필터 확장, `_reconcile` SHUTOFF 입양, Nova 기준 `active_count()`
  - 검증: 수동 `openstack server stop` 후 동기화 시 DB SHUTOFF 반영, 재시도 경로에서 삭제되지 않음
- 5 `switch --to A` 커맨드 (대상 검증 → start 큐 → stop 큐 → 워커 병렬 → 완료 후 Nova→DB 동기화, `--yes`)
  - 검증: 45↔45 전환 성공, 소요 시간 측정(CLI 149초 대비), 전환 중 `free -h`
- 6 Warpgate 90 타깃 통합 검증: `get_wg().status()` 세 리스트 길이 90, 고아 0. 정지 분반 접속 안내 공지
- 7 (후순위) ACTIVE_LIMIT 가드 — 분반별 45 + 전체 45 동시 검사
  - 검증: 46번째 기동 거부
- 8 문서: as-built 1,905 → 1,876 정정, `docs/02`·`03` 갱신, 운영 체크리스트(전환 절차·롤백·재부팅 설정·`.env` 항목)
- 소요 감: 1~3 은 기존 코드 수정, 5 가 신규 작성으로 가장 큼 (검증 문서 §7-7 과 동일 판단)

---

## 7. 08-30 회의 액션 아이템 진행 상태

| 액션 | 상태 | 근거 |
|---|---|---|
| 두 수업 90대 시 CPU·RAM 반환 확인 | **완료** | 09-04 운영계 검증 |
| 임시 failed-filter DB(DismissedFailure) 정리 | **완료** | `Phase_0.5_prod` `portal/migrations/0002_delete_dismissedfailure.py`, `VmFailure`·`acknowledge_failure` 도입 |
| 커스텀 Glance 이미지 (교수 피드백) | **진행 중** | `Phase_0.5_prod` `imagebuild` 앱, 이미지 카탈로그 |
| Warpgate 내부 DB·API 결과 검증 방법 | 미완 | D9 (b) 의 전제 |
| drift·idempotency·timeout·FAILED cleanup 기준 문서화 | 부분 | `docs/02`·`03` 이 현행 기준. 90대 반영은 D7 이후 |
| DB polling 유지 여부·큐 전환 조건·경계 | 제안됨 | D12 |
| 프론트/백 분리안, 가입 승인·프로젝트·Quota·자격증명 flow | 미완 | Phase 1, D13 |
| Python·Django 지속, 프론트 프레임워크, 배포 구조 비교 | 미완 | Phase 1 |
| 최소 Docker 컨테이너 준비, K8s·OpenStack-Helm 학습 | 미완 | D11 |
| 하드웨어 확인 (P520·5090·예산) | 미완 | D14, 교수 확인 대기 |
| 교수 피드백 → Phase 0.5 보완 / Phase 1 요구사항 분류 | 부분 | 본 문서 §4 가 90대 관련분 |
| Discord 공유·새 참여자 초대, 다음 회의 22:00 확정 | 운영 | — |

---

## 8. 리스크

| 리스크 | 발생 조건 | 영향 | 완화 |
|---|---|---|---|
| 안전장치 이동 | 오버커밋으로 `NoValidHost` 방어선 소멸 | 관리자 실수(전환 시 stop 누락, 스크립트 오작동) → OOM | D8 최소 방어, 운영 체크리스트, 후속 가드 |
| 재부팅 시 90대 동시 기동 | `resume_guests_state_on_host_boot=true` | 호스트 OOM | 설정 변경 시 값 확인 절차, 체크리스트 |
| 정지 VM 삭제 | `_reconcile` 미수정 상태에서 SHUTOFF 슬롯 재시도 | 학생 VM 소실 | D7 필수 선행 |
| FIP 충돌 | B분반 오프셋 150/155 미확정 | 두 VM 이 같은 FIP 요구, `create` 실패 | D3 확정, naming 모듈 단일화 |
| 발급 실패 | 플레이버 재생성 후 `.env` `SU_FLAVOR_ID` 미갱신 | 전 발급 `NotFound` | 실행 순서 0, 배포 체크리스트 |
| 디스크 ENOSPC | 30 GB 유지 + ratio 1.5 선택 시 | 90명 동시 피해 | D1 (a) |
| 롤백 실패 | 90대 등록 상태에서 ratio 1.0 시도 | Placement 거부(used > capacity) | 45대 이하 축소 선행, 값 **명시** |
| 상태 어긋남 | 학생 `sudo poweroff`, 수동 Horizon 조작 | DB ACTIVE / Nova SHUTOFF | Nova 기준 카운트(D7), 전환 후 동기화 |
| 문서·코드 괴리 | `docs/00~06` 은 prod 중간 스냅샷 | 오래된 코드 기준으로 수정 | `README.md` 차이 절, 전환 후 갱신 |

---

## 9. 코드 근거 (변경 지점 찾기)

- 슬롯·상태 모델: `provisioning/models.py` (`Slot.n` PK, `Vm.status` choices) → D2·D6
- 큐·전이: `provisioning/services.py` — `reserve` (가장 낮은 FREE), `claim` (status 필터), `provision` (`_reconcile` → `osvm.create` → `wg.provision_seat`, 비밀번호 `Student{n}!`), `_reconcile` (ACTIVE 외 삭제) → D3·D6·D7
- 명명: `osclient/vm.py` `name_for`/`user_for`/`fip_for`, `USER_DATA` 의 `student{n}`; `wgclient/__init__.py` `provision_seat`/`deprovision_seat` 의 f-string → D3
- 환경변수 단일값: `SU_FLAVOR_ID`, `SU_NETWORK_ID`, `SU_SECGROUP`, `SU_FIP_PREFIX` (`osclient/vm.py`) → D1·D4·D15
- 커맨드: `provisioning/management/commands/{issue,reclaim,worker}.py` — `switch` 신규, `issue --section` → D8, 실행 순서 3·5
- 표현 계층: `provisioning/admin.py`, `portal/services.py`(`Phase_0.5_prod`) 의 상태 목록·검색·표시 → D6
- Warpgate 상태 점검: `wgclient.WarpgateClient.status()` (users/targets/roles 길이 비교) → D9

<!-- 결정 기록: 아래에 "YYYY-MM-DD · Dn · 결정 · 근거" 형식으로 추가 -->
