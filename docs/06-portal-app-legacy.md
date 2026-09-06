# portal 앱 코드 정리 (서비스 레이어 분리 전)

> **출처**: Notion 「portal 앱 코드 정리 (서비스 레이어 분리 전)」 · 레포 정리 2026-09-05
> 서비스 레이어 분리 **전** 구조. 현재 구조는 `05-portal-app.md`. 변경 배경 파악용 참고 문서.


**범위** — `portal` 앱의 서버 코드와, 화면이 서버와 주고받는 **연결 지점**만 다룸.
마크업 구조·CSS·레이아웃 등 표현 영역은 제외. 템플릿은 값이 오가는 지점(폼 필드명, 쿼리 파라미터, 컨텍스트 변수)만 표로 정리.

**순서** — 사용자 동작 순서(**로그인 분기 → 생성 → 조회 → 회수**)로 재배열. `views.py`의 함수 순서와는 다르며, 각 섹션 머리에 원본 위치를 표기.

---

## 사용 언어 및 기술 스택

| 구분 | 언어 | 사용 파일 |
| --- | --- | --- |
| 서버 | Python | `views.py`, `urls.py`, `models.py` |
| 화면 | Django Template Language | `base.html`, `list.html`, `login.html` |
| 화면 | HTML5 | 위 3개 템플릿 |
| 화면 | CSS | `base.html` `<style>` 전역 정의 + 템플릿 내 인라인 style |
| 화면 | JavaScript (바닐라) | `list.html` 하단 `<script>` — 모달·선택·확인·폴링 |

| 프레임워크 | 버전 |
| --- | --- |
| Django | 5.2.17 |

포털이 사용하는 Django 기본 기능

- `django.contrib.auth` — 로그인/로그아웃 뷰, `@login_required`
- `django.contrib.messages` — 생성 결과 flash 메시지
- `django.contrib.staticfiles` — 로고 이미지
- Django Template 상속 — `{% extends %}` / `{% block %}`

---

## 0. 구성 개요

### 파일 지도

| 파일 | 역할 |
| --- | --- |
| `portal/urls.py` | `/portal/` 하위 라우팅 (목록, 생성) |
| `portal/views.py` | 진입점·목록·생성·에러 라벨링 |
| `portal/models.py` | `DismissedFailure` — FAILED 숨김 기록 |
| `portal/templates/portal/*.html` | 화면 3종 (`base` / `login` / `list`) |

### 통신 방식

- 화면 ↔ 서버는 **폼 전송(POST)과 쿼리 파라미터(GET)** 만 사용. AJAX·JSON API 없음.
- 모든 POST 처리는 완료 후 `redirect("portal:list")` — PRG 패턴으로 새로고침 재전송 방지.
- 상태 갱신은 서버 푸시가 아니라 **클라이언트 폴링**(5초 주기 `location.reload()`).

### 외부 의존

`views.py` 상단 주석 기준, 앱 밖을 참조하는 지점은 3개뿐.

| 대상 | 사용 방식 |
| --- | --- |
| `provisioning.models.Slot`, `Vm` | 읽기 전용 조회 |
| `provisioning.services` | `reserve` / `request_delete` / `request_delete_all` 만 호출 (요청 등록만 수행, 실제 작업은 워커 담당) |
| `osclient.vm` (`osvm`) | `name_for` / `fip_for` / `user_for` — 슬롯 번호 기반 계산, OpenStack 미호출 |

```python
# portal/views.py L8~18
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from provisioning.models import Slot, Vm
from portal.models import DismissedFailure
from provisioning import services
from osclient import vm as osvm

# ── 화면에 노출할 상태 목록 (DELETED 제외) ──
STATUS_LIST = [Vm.PROVISIONING, Vm.ACTIVE, Vm.DELETING, Vm.FAILED]
```

### 라우팅

```python
# portal/urls.py
app_name = "portal"

urlpatterns = [
    path("", views.list_view, name="list"),            # 목록 화면 (GET 조회 / POST 회수)
    path("create/", views.create_view, name="create"),  # 생성 처리 (POST 전용)
]
```

> 진입점(`index`)과 `accounts/login/`·`accounts/logout/`는 앱 밖(`config/urls.py`)에 등록됨.
> 

---

## 1. 로그인 분기

**흐름** — `/` 접속 → `index()` 분기 → 미인증 시 로그인 화면 → 인증 성공 → `/portal/`

### 1-1. 진입점 `index()`

> 원본: `portal/views.py` L22~25
> 

```python
# ── 인증 상태면 목록으로, 아니면 로그인 화면으로 ──
# ── 로그인 처리 자체는 Django 기본 LoginView가 담당 ──
def index(request):
    if request.user.is_authenticated:
        return redirect("portal:list")
    return redirect("login")
```

### 1-2. 화면 → 서버 전달값

> `login.html`의 폼은 Django 기본 `AuthenticationForm`이 받으므로 필드명이 정해져 있음.
> 

| 필드명 | 값 | 받는 쪽 |
| --- | --- | --- |
| `username` | 사용자 입력 | `AuthenticationForm` |
| `password` | 사용자 입력 | `AuthenticationForm` |
| `next` | 로그인 후 이동 경로, 기본 `/portal/` | `LoginView` |
| `csrfmiddlewaretoken` | `{% csrf_token %}` | CSRF 미들웨어 |

### 1-3. 서버 → 화면 전달값

| 변수 | 용도 |
| --- | --- |
| `form.errors` | 존재 시 단일 문구로만 표시. 실패 사유는 노출하지 않음 |
| `user.is_authenticated` | `base.html` 헤더의 계정명·로그아웃 노출 여부 |
| `user.username` | 헤더 계정명 |

> 로그아웃은 링크가 아니라 `POST` + `{% csrf_token %}` 폼. Django `LogoutView`가 GET을 허용하지 않기 때문.
> 

---

## 2. 생성

**흐름** — `+ VM 생성` 클릭 → 모달 1단계(개수 입력) → 2단계(확인) → `POST /portal/create/` → `create_view()` → `services.reserve()` × N → 목록으로 리다이렉트

### 2-1. 화면 → 서버 전달값

> 실제 서버 요청은 모달 2단계의 폼 하나뿐. 1단계 입력값을 JS가 hidden 필드로 복사해 넘김.
> 

| 항목 | 값 |
| --- | --- |
| 전송 경로 | `{% url 'portal:create' %}` → `/portal/create/` |
| 메서드 | POST 전용 (GET 진입 시 목록으로 되돌림) |
| `count` | 생성 개수. `<input type="hidden" name="count" id="hidden-count">` |
| `csrfmiddlewaretoken` | `{% csrf_token %}` |

### 2-2. 서버 → 화면 전달값

> 생성 모달이 쓰는 값. `list_view()`가 렌더할 때 함께 내려보냄 (3장 참조).
> 

| 변수 | 용도 |
| --- | --- |
| `free` | `<input>`의 `max` 속성, JS 상수 `FREE`, 0이면 확인 버튼 `disabled` |
| `taken` | 여유분 게이지, JS 상수 `TAKEN` |
| `total` | 최대 슬롯 수 표기 |

`free`·`taken`은 템플릿 변수로 JS에 직접 주입되어 클라이언트 검증에 쓰임.

```jsx
// list.html L214~215 — 서버 값을 JS 상수로 고정
const FREE = {{ free }};
const TAKEN = {{ taken }};

// ── 입력값이 범위를 벗어나면 다음 단계 차단 (서버에서도 재검증) ──
if (v > FREE || v < 1) { goConfirmBtn.disabled = true; }
```

### 2-3. 생성 처리 `create_view()`

> 원본: `portal/views.py` L114~136
> 

```python
# ── 로그인 사용자만 접근 ──
@login_required
def create_view(request):
    # ── POST 전용. GET으로 들어오면 목록으로 되돌림 ──
    if request.method != "POST":
        return redirect("portal:list")

    # ── 서버 측 재검증: 여유 슬롯 수를 DB에서 다시 확인 ──
    # ── 클라이언트 검증(FREE)은 통과했더라도 그 사이 바뀌었을 수 있음 ──
    free = Slot.objects.filter(status=Slot.FREE).count()
    try:
        count = int(request.POST.get("count", 0))
    except ValueError:
        count = 0
    # ── 0 미만·여유 슬롯 초과 요청을 범위 안으로 강제 ──
    count = max(0, min(count, free))

    # ── 요청 등록만 수행. 실제 생성은 워커가 담당 ──
    # ── reserve()는 슬롯 확보 실패 시 falsy 반환 ──
    made = 0
    for _ in range(count):
        if services.reserve(""):
            made += 1

    # ── 결과는 flash 메시지로 전달, base.html에서 출력 ──
    if made:
        messages.success(request, f"{made}대 생성 요청이 접수되었습니다.")
    else:
        messages.error(request, "생성 가능한 여유 슬롯이 없습니다.")

    return redirect("portal:list")
```

---

## 3. 조회

**흐름** — `GET /portal/` → `list_view()` GET 분기 → 전체조회 → 숨김 제외 → 집계 → 상태 필터 → 검색 → 화면용 조립 → 렌더

### 3-1. 화면 → 서버 전달값

> 상태 칩은 링크(`<a href>`), 검색은 GET 폼. 둘 다 같은 쿼리스트링을 공유하며 서로의 값을 유지시킴.
> 

| 파라미터 | 전달 방식 | 서버에서 읽는 곳 |
| --- | --- | --- |
| `status` | 상태 칩 링크 `?status=ACTIVE&q=...` / 검색 폼의 hidden | `request.GET.get("status", "")` |
| `q` | 검색 폼 입력 / 칩 링크가 현재 값을 그대로 물고 감 | `request.GET.get("q", "").strip()` |

### 3-2. 목록 조회 `list_view()` 뒷부분 (GET)

> 원본: `portal/views.py` L53~110. 같은 함수의 앞부분(POST)은 4장 참조.
> 

```python
# ── 1) 전체 조회: 회수 완료(DELETED) 이력은 제외, 슬롯 번호 순 정렬 ──
all_vms = Vm.objects.exclude(status=Vm.DELETED).order_by("slot_id")

# ── 2) 숨김 제외: 사용자가 화면에서 치운 FAILED 항목 ──
dismissed_ids = DismissedFailure.objects.values_list("vm_id", flat=True)
all_vms = all_vms.exclude(id__in=dismissed_ids)

# ── 3) 집계: 상태 칩에 표시할 개수. 0건 상태도 키를 유지 ──
status_counts = {s: 0 for s in STATUS_LIST}
for v in all_vms:
    status_counts[v.status] = status_counts.get(v.status, 0) + 1
total_count = all_vms.count()

# ── 4) 상태 필터: ?status= 없으면 전체 ──
status_filter = request.GET.get("status", "")
vms = all_vms.filter(status=status_filter) if status_filter else all_vms

# ── 5) 검색: 이름·FIP·계정은 DB 컬럼이 아니라 slot_id 기반 계산값 ──
# ── 따라서 DB 쿼리로 못 걸고 파이썬에서 매칭 후 id로 재필터 ──
q = request.GET.get("q", "").strip()
if q:
    ql = q.lower()
    matched_ids = [
        v.id for v in vms
        if ql in osvm.name_for(v.slot_id).lower()
        or q in osvm.fip_for(v.slot_id)
        or ql in osvm.user_for(v.slot_id).lower()
        or q == str(v.slot_id)
    ]
    vms = vms.filter(id__in=matched_ids)
```

```python
# ── 6) 화면용 데이터 조립: osvm 계산 + FAILED 라벨링 결합 ──
# ── 템플릿에서 함수 호출이 불가하므로 여기서 미리 계산해 dict로 넘김 ──
rows = []
for v in vms:
    row = {"vm": v, "name": osvm.name_for(v.slot_id)}
    # ── 생성 중에는 FIP/계정이 아직 유효하지 않아 '—' 표시 ──
    if v.status == Vm.PROVISIONING:
        row["fip"] = "—"
        row["user"] = "—"
    else:
        row["fip"] = osvm.fip_for(v.slot_id)
        row["user"] = osvm.user_for(v.slot_id)
    # ── FAILED면 원본 error 문자열을 사람이 읽는 라벨·설명으로 변환 ──
    if v.status == Vm.FAILED:
        label = friendly_label(v.error or "")
        row["fail_label"] = label
        row["fail_desc"] = FAILED_DESCRIPTIONS.get(label, FAILED_DESCRIPTIONS["실패"])
    rows.append(row)

# ── 7) 슬롯 현황: 생성 모달의 여유분 표시에 사용 ──
# ── total은 하드코딩하지 않고 taken + free로 계산 ──
taken = Slot.objects.filter(status=Slot.TAKEN).count()
free = Slot.objects.filter(status=Slot.FREE).count()

# ── 8) 상단 진행바 분모: DELETING 제외 (생성 진행 상황만 표시) ──
strip_total = status_counts[Vm.ACTIVE] + status_counts[Vm.PROVISIONING] + status_counts[Vm.FAILED]
```

### 3-3. 서버 → 화면 전달값 (렌더 컨텍스트)

```python
return render(request, "portal/list.html", {
    "rows": rows,
    "status_counts": status_counts,
    "total_count": total_count,
    "status_filter": status_filter,
    "q": q,
    "taken": taken,
    "free": free,
    "total": taken + free,
    # ── 생성 중인 VM이 있을 때만 진행바·자동 새로고침 활성 ──
    "show_strip": status_counts[Vm.PROVISIONING] > 0,
    "strip_total": strip_total,
})
```

| 변수 | 화면에서의 쓰임 |
| --- | --- |
| `rows` | 목록 테이블 각 행 |
| `status_counts` | 상태 칩 개수, 진행바 세그먼트 비율 |
| `total_count` | 전체 칩 개수. 0이면 빈 상태 화면으로 대체 |
| `status_filter` | 현재 선택된 칩 표시, 검색 폼 hidden 값 |
| `q` | 검색창 값 유지, 칩 링크에 재삽입 |
| `taken` / `free` / `total` | 여유 슬롯 표기, 생성 모달 (2장) |
| `show_strip` | 진행바 노출 여부, 폴링 스크립트 삽입 여부 |
| `strip_total` | 진행바 비율 계산 분모 |

`rows` 각 항목의 구조

| 키 | 값 | 비고 |
| --- | --- | --- |
| `vm` | `Vm` 인스턴스 | `slot_id`, `status`, `created_at`, `error`, `id` 사용 |
| `name` | `osvm.name_for()` 결과 |  |
| `fip` | `osvm.fip_for()` 결과 | PROVISIONING이면 `—` |
| `user` | `osvm.user_for()` 결과 | PROVISIONING이면 `—` |
| `fail_label` | `friendly_label()` 결과 | FAILED일 때만 존재 |
| `fail_desc` | `FAILED_DESCRIPTIONS` 조회 결과 | FAILED일 때만 존재 |

### 3-4. 에러 라벨링 헬퍼 `friendly_label()`

> 원본: `portal/views.py` L140~162. 원본 `error` 문자열을 소문자로 낮춘 뒤 키워드 우선순위로 분류. 결과는 `rows`에 실려 FAILED 팝오버에 표시됨.
> 

```python
def friendly_label(error: str) -> str:
    e = error.lower()
    # ── 요청 자체가 잘못된 경우 (설정값 오류) ──
    if "badrequest" in e:
        return "잘못된 요청 (설정값 오류)"
    # ── 인증 / 권한·한도 ──
    if " 401" in e:
        return "인증 만료"
    if "forbidden" in e:
        return "자원 한도 초과 (Quota)"
    # ── 404: /servers/ 포함 여부로 VM 소실과 설정 오류를 구분 ──
    if "notfound" in e or " 404" in e:
        if "/servers/" in e:
            return "VM 인스턴스 소실"
        return "리소스 없음 (image/flavor/network 설정 오류)"
    # ── 409: FIP 관련이면 IP 충돌, 아니면 이름/상태 충돌 ──
    if "conflict" in e or " 409" in e:
        return "IP 충돌" if ("fip" in e or "floating" in e) else "이름/상태 충돌"
    # ── 빌드 실패 / 타임아웃 ──
    if "resourcefailure" in e:
        return "생성 실패 (자원 부족 또는 빌드 오류)"
    if "resourcetimeout" in e or "timeout" in e:
        return "접속 확인 시간 초과" if "ssh" in e else "생성 시간 초과"
    # ── 네트워크 계열 ──
    if "stopiteration" in e:
        return "포트/FIP 조회 실패"
    if "neutron" in e or "floating" in e or "port" in e:
        return "네트워크/IP 할당 실패"
    # ── 분류 실패 시 기본값 ──
    return "실패"
```

```python
# ── 라벨 → 사용자 설명 문구 매핑 (L165~179) ──
# ── friendly_label()의 반환값을 키로 사용하므로 문자열이 정확히 일치해야 함 ──
FAILED_DESCRIPTIONS = {
    "잘못된 요청 (설정값 오류)": "image·flavor·network 설정값에 문제가 있어요. 운영자 확인이 필요해요.",
    "인증 만료": "작업 중 OpenStack 인증이 만료됐어요. 운영자 확인이 필요해요.",
    # ... (총 13개 항목)
    "실패": "원인을 특정하지 못했어요. 아래 원본 로그를 확인해주세요.",
}
```

### 3-5. 상태 갱신 방식

> 워커가 DB 상태를 바꾸는 동안 화면을 최신화하는 유일한 수단. 서버 푸시나 부분 갱신 없이 페이지 전체를 다시 요청함.
> 

```jsx
// list.html L284~288 — show_strip이 참일 때만 스크립트가 삽입됨
{% if show_strip %}
// ── 생성 중일 때만 5초 주기 새로고침 ──
// ── 모달이 열려 있거나 체크박스 선택 중이면 작업이 날아가므로 건너뜀 ──
setInterval(() => {
  if (!dlg.open && !hasSelection()) location.reload();
}, 5000);
{% endif %}
```

---

## 4. 회수

**흐름** — 체크박스 선택 → `선택 회수`(또는 `전체 회수`) → `confirm()` → `POST /portal/` → `list_view()` POST 분기 → `services.request_delete*()` 또는 숨김 처리 → 목록으로 리다이렉트

### 4-1. 화면 → 서버 전달값

> 전체 회수와 선택 회수가 **같은 폼 하나**를 공유하고, 어느 버튼으로 제출됐는지는 `action` 값으로 구분. 전체 회수 버튼은 폼 밖에 있으나 `form="vm-form"` 속성으로 연결됨.
> 

| 필드명 | 값 | 서버에서 읽는 곳 |
| --- | --- | --- |
| `action` | `delete_all` 또는 `delete_selected` (submit 버튼의 `value`) | `request.POST.get("action")` |
| `vm_ids` | 체크된 VM의 `id` 다중 값 | `request.POST.getlist("vm_ids")` |
| `csrfmiddlewaretoken` | `{% csrf_token %}` | CSRF 미들웨어 |
- 체크박스는 `ACTIVE` / `FAILED` 상태에서만 활성. 그 외 상태는 `disabled`이라 전송되지 않음.
- 제출 직전 JS `confirm()`으로 한 번 더 확인. `e.submitter.value`로 전체/선택을 구분해 문구를 다르게 표시.

### 4-2. 회수 처리 `list_view()` 앞부분 (POST)

> 원본: `portal/views.py` L29~51. 같은 함수의 뒷부분(GET)은 3장 참조.
`services` 호출은 포털 전체에서 이 블록과 `create_view()` 두 곳뿐.
> 

```python
@login_required
def list_view(request):
    # ── POST면 회수 처리 후 리다이렉트 (PRG 패턴: 새로고침 재전송 방지) ──
    if request.method == "POST":
        # ── 어느 버튼으로 제출됐는지 구분 ──
        action = request.POST.get("action")

        # ── 전체 회수 ──
        if action == "delete_all":
            # ── 실제 삭제 요청 등록 (대상은 services가 판단) ──
            services.request_delete_all()
            # ── FAILED는 삭제할 실체가 없으므로 숨김 기록만 남김 ──
            failed_ids = Vm.objects.filter(status=Vm.FAILED).values_list("id", flat=True)
            # ── 여러 건을 한 번에 저장, 이미 있으면 무시 ──
            DismissedFailure.objects.bulk_create(
                [DismissedFailure(vm_id=vid) for vid in failed_ids],
                ignore_conflicts=True,
            )

        # ── 선택 회수: 전체 회수와 동일한 판단 기준을 건별로 적용 ──
        elif action == "delete_selected":
            for vid in request.POST.getlist("vm_ids"):
                vid = int(vid)
                rec = Vm.objects.filter(pk=vid).first()
                # ── FAILED면 숨김, 그 외에는 삭제 요청 등록 ──
                if rec and rec.status == Vm.FAILED:
                    DismissedFailure.objects.get_or_create(vm_id=vid)
                else:
                    services.request_delete(vid)

        return redirect("portal:list")

    # (이하 GET 조회 — 3장 참조)
```

### 4-3. 숨김 기록 모델 `DismissedFailure`

> 원본: `portal/models.py`. FAILED 숨김이 로그아웃 시 초기화되던 세션 방식을 대체하기 위한 테이블. 조회 단계 2)에서 `exclude`로 소비됨.
> 

```python
class DismissedFailure(models.Model):
    """
    [Phase 0.5 임시 해결책]
    FAILED VM을 화면에서 숨기는 기록. Vm 원본은 건드리지 않음.

    TODO(Phase 1): provisioning.Vm.dismissed_at 필드로 이관 예정 (협의 필요).
    이관되면 이 모델은 삭제.
    """
    # ── unique로 중복 숨김 기록 방지 (bulk_create의 ignore_conflicts가 여기 의존) ──
    vm_id = models.IntegerField(unique=True)
    dismissed_at = models.DateTimeField(auto_now_add=True)
```
