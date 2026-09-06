# SU Cloud 포털 (Phase 0.5) — portal 앱 코드 정리

> **출처**: Notion 「SU Cloud 포털 (Phase 0.5) — portal 앱 코드 정리」 · 레포 정리 2026-09-05
> 서비스 레이어 분리 **후** 구조. 이전 버전은 `06-portal-app-legacy.md`.
> 이 레포 `main` 의 `portal/` 은 아직 자리표시자이며, 여기 설명된 코드는 `origin/Phase_0.5_prod` 에 있다 (`README.md` 참고).


- Notion 페이지 (레포 미포함): <https://app.notion.com/p/3cde07c2567680058b97da69f13f221c?pvs=21> 

**범위** — `portal` 앱의 서버 코드와, 화면이 서버와 주고받는 연결 지점. 마크업·CSS·레이아웃은 제외하고, 템플릿은 값이 오가는 지점만 표로 정리.

**순서** — 계층 구조를 먼저 설명한 뒤 사용자 동작 순서(로그인 → 생성 → 조회 → 회수)로 재배열. 파일 내 함수 순서와는 다름.

---

## 0. 구성

### 기술 스택

| 구분 | 내용 |
| --- | --- |
| 서버 | Python · Django 5.2.17 |
| 화면 | Django Template + HTML5 + CSS + 바닐라 JS |

Django 기본 기능 중 `contrib.auth`(로그인·`@login_required`), `contrib.messages`(생성 결과 flash), `contrib.staticfiles`(로고), 템플릿 상속을 사용.

### 파일 지도

| 파일 | 역할 |
| --- | --- |
| `urls.py` | `/portal/` 하위 라우팅 |
| `views.py` | HTTP 처리 — 요청 해석·렌더·리다이렉트 |
| `services.py` | 조회·집계·조립·실패 사유 판정 |
| `labels.py` | FAILED 안내 문구 사전 |
| `models.py` | `DismissedFailure` — FAILED 숨김 기록 |
| `templates/portal/` | `base` / `login` / `list` |

### 계층 구조

`views.py`에 몰려 있던 로직을 세 갈래로 분리. 기준은 **HTML이든 JSON이든 똑같이 필요한가**.

| 계층 | 파일 | 담당 |
| --- | --- | --- |
| 표현 진입 | `views.py` | GET/POST 판별, 파라미터 해석, `render` · `redirect` · `messages` |
| 서비스 | `services.py` | 조회·숨김 제외·집계·필터·검색·행 조립·실패 판정 |
| 표현 데이터 | `labels.py` | 라벨 → 안내 문구 매핑 |

```
views.py ──→ portal.services ──→ provisioning.models (읽기)
         │                    ├─→ osclient.vm (계산)
         │                    └─→ portal.labels
         └──→ provisioning.services (쓰기)
```

`list_page_data()`의 반환 딕셔너리가 목록 화면 컨텍스트 전체이며, 그대로 조회 API 응답 스키마 후보가 됨.

### 외부 의존

| 대상 | 사용 방식 | 참조 위치 |
| --- | --- | --- |
| `provisioning.models` | `Slot` · `Vm` 읽기 전용 | `services.py`, `views.py`(회수 시 상태 확인) |
| `provisioning.services` | `reserve` · `request_delete` · `request_delete_all` — 요청 등록만, 실제 작업은 워커 | `views.py` |
| `osclient.vm` | `name_for` · `fip_for` · `user_for` — 슬롯 번호 기반 계산, OpenStack 미호출 | `services.py` |

`provisioning.services`는 `prov`, `portal.services`는 `services`로 별칭을 구분.

### 통신 방식

- 폼 전송(POST)과 쿼리 파라미터(GET)만 사용. AJAX·JSON API 없음.
- POST 처리 후 `redirect("portal:list")` — PRG 패턴으로 새로고침 재전송 방지.
- 상태 갱신은 클라이언트 폴링(5초 주기 `location.reload()`).

### 라우팅

```python
app_name = "portal"

urlpatterns = [
    path("", views.list_view, name="list"),             # GET 조회 / POST 회수
    path("create/", views.create_view, name="create"),  # POST 전용
]
```

진입점 `index`와 `accounts/login/`·`accounts/logout/`는 `config/urls.py`에 등록됨.

---

## 1. 로그인

`/` 접속 → `index()` 분기 → 미인증 시 로그인 화면 → 인증 성공 → `/portal/`

### 진입점

```python
def index(request):
    if request.user.is_authenticated:
        return redirect("portal:list")
    return redirect("login")
```

로그인 처리 자체는 Django 기본 `LoginView`가 담당.

### 화면 → 서버

폼은 `AuthenticationForm`이 받으므로 필드명이 정해져 있음.

| 필드명 | 값 |
| --- | --- |
| `username` · `password` | 사용자 입력 |
| `next` | 로그인 전 접근하려던 경로. 없으면 빈 값 |
| `csrfmiddlewaretoken` | `{% csrf_token %}` |

로그인 후 이동 경로는 두 단계로 결정됨.

| 순위 | 출처 | 동작 |
| --- | --- | --- |
| 1 | 폼의 `next` | 원래 가려던 주소로 복귀 (쿼리스트링 포함) |
| 2 | `settings.LOGIN_REDIRECT_URL` | `next`가 비었을 때 `portal:list` |

템플릿이 기본값을 채우던 방식(`{{ next|default:'/portal/' }}`)을 제거해, 기본 목적지는 `settings.py` 한 곳에서만 관리.

### 서버 → 화면

| 변수 | 용도 |
| --- | --- |
| `form.errors` | 존재 시 단일 문구로만 표시. 실패 사유는 비노출 |
| `user.is_authenticated` | 헤더의 계정명·로그아웃 노출 여부 |
| `user.username` | 헤더 계정명 |

로그아웃은 링크가 아니라 POST 폼. `LogoutView`가 GET을 허용하지 않기 때문.

---

## 2. 생성

`+ VM 생성` → 모달 1단계(개수) → 2단계(확인) → `POST /portal/create/` → `prov.reserve()` × N → 목록으로 리다이렉트

### 화면 → 서버

서버 요청은 모달 2단계의 폼 하나뿐. 1단계 입력값을 JS가 hidden 필드로 복사해 넘김.

| 항목 | 값 |
| --- | --- |
| 경로 · 메서드 | `/portal/create/` · POST 전용 (GET 진입 시 목록으로) |
| `count` | 생성 개수 (hidden) |
| `csrfmiddlewaretoken` | `{% csrf_token %}` |

### 서버 → 화면

`list_view()`가 렌더할 때 함께 내려보내는 값 (3장 참조).

| 변수 | 용도 |
| --- | --- |
| `free` | `<input>`의 `max`, JS 상수 `FREE`, 0이면 확인 버튼 `disabled` |
| `taken` | 여유분 게이지, JS 상수 `TAKEN` |
| `total` | 최대 슬롯 수, 게이지 폭 계산의 분모 |

```jsx
const FREE = {{ free }};
const TAKEN = {{ taken }};

// 범위를 벗어나면 다음 단계 차단 (서버에서도 재검증)
if (v > FREE || v < 1) { goConfirmBtn.disabled = true; }
```

게이지는 `total`이 0인 경우를 방어함. `widthratio`는 분모가 0이면 빈 문자열을 반환해 `width:%` 라는 깨진 값이 되므로 조건 분기로 `0%`를 내보냄.

```
<div style="width:{% if total %}{% widthratio taken total 100 %}{% else %}0{% endif %}%"></div>
```

### 처리 — `views.py`

```python
@login_required
def create_view(request):
    """생성 모달 제출 처리. 여유 슬롯을 넘는 요청은 상한으로 잘라낸다"""
    if request.method != "POST":
        return redirect("portal:list")

    # 클라이언트 검증(FREE) 이후 값이 바뀌었을 수 있어 DB에서 재확인
    free = services.free_slot_count()
    try:
        count = int(request.POST.get("count", 0))
    except ValueError:
        count = 0
    count = max(0, min(count, free))

    # 요청 등록만 수행. 실제 생성은 워커 담당
    made = sum(1 for _ in range(count) if prov.reserve(""))

    if made:
        messages.success(request, f"{made}대 생성 요청이 접수되었습니다.")
    else:
        messages.error(request, "생성 가능한 여유 슬롯이 없습니다.")

    return redirect("portal:list")
```

---

## 3. 조회

`GET /portal/` → `list_view()` → `services.list_page_data()` → 조회 → 숨김 제외 → 집계 → 필터 → 검색 → 조립 → 렌더

### 화면 → 서버

상태 칩은 링크, 검색은 GET 폼. 둘이 같은 쿼리스트링을 공유하며 서로의 값을 유지시킴.

| 파라미터 | 전달 방식 | 읽는 곳 |
| --- | --- | --- |
| `status` | 칩 링크 `?status=ACTIVE&q=...` / 검색 폼 hidden | `request.GET.get("status", "")` |
| `q` | 검색 폼 입력 / 칩 링크가 현재 값을 물고 감 | `request.GET.get("q", "").strip()` |

### 요청 접수 — `views.py`

뷰가 하는 일은 파라미터를 꺼내 서비스에 넘기고 결과를 템플릿에 전달하는 것뿐.

```python
@login_required
def list_view(request):
    """GET = 목록 조회 / POST = 선택·전체 회수"""
    if request.method == "POST":
        return _handle_reclaim(request)     # 4장

    ctx = services.list_page_data(
        status_filter=request.GET.get("status", ""),
        q=request.GET.get("q", "").strip(),
    )
    return render(request, "portal/list.html", ctx)
```

### 조합 — `services.py`

하위 함수를 조회 → 집계 → 필터 → 검색 → 조립 순으로 호출.

```python
def list_page_data(status_filter="", q=""):
    """목록 화면에 필요한 데이터 전부. 반환 형태 = API 응답 스키마 후보"""
    all_vms = visible_vms()
    status_counts = count_by_status(all_vms)
    total_count = all_vms.count()

    vms = apply_status_filter(all_vms, status_filter)
    vms = apply_search(vms, q)

    slots = slot_summary()
    strip_total = (
        status_counts[Vm.ACTIVE]
        + status_counts[Vm.PROVISIONING]
        + status_counts[Vm.FAILED]
    )

    return {
        "rows": build_rows(vms),
        "status_counts": status_counts,
        "total_count": total_count,
        "status_filter": status_filter,
        "q": q,
        "taken": slots["taken"],
        "free": slots["free"],
        "total": slots["total"],
        "show_strip": status_counts[Vm.PROVISIONING] > 0,
        "strip_total": strip_total,
    }
```

`strip_total`은 DELETING을 제외함. 상단 진행바가 생성 진행 상황만 표시하기 때문.

### 하위 함수 — `services.py`

```python
def visible_vms():
    """노출 대상 VM. Vm 은 append-only 라 DELETED 이력과 숨김 처리분을 제외한다"""
    qs = Vm.objects.exclude(status=Vm.DELETED).order_by("slot_id")
    dismissed_ids = DismissedFailure.objects.values_list("vm_id", flat=True)
    return qs.exclude(id__in=dismissed_ids)

def count_by_status(vms):
    """상태 칩에 표시할 상태별 개수. 0건 상태도 키를 유지"""
    counts = {s: 0 for s in STATUS_LIST}
    for v in vms:
        counts[v.status] = counts.get(v.status, 0) + 1
    return counts

def slot_summary():
    """슬롯 사용 현황. total 은 하드코딩하지 않고 taken + free 로 계산"""
    taken = Slot.objects.filter(status=Slot.TAKEN).count()
    free = Slot.objects.filter(status=Slot.FREE).count()
    return {"taken": taken, "free": free, "total": taken + free}

def apply_status_filter(vms, status_filter):
    """칩 선택 시 해당 상태만. 빈 값이면 전체"""
    return vms.filter(status=status_filter) if status_filter else vms

def apply_search(vms, q):
    """이름 / FIP / 계정 / 슬롯번호 검색.
    앞 셋은 slot_id 로부터 계산되는 값이라 DB 필터가 불가해 Python 으로 순회한다"""
    if not q:
        return vms
    ql = q.lower()
    matched_ids = [
        v.id for v in vms
        if ql in osvm.name_for(v.slot_id).lower()
        or q in osvm.fip_for(v.slot_id)
        or ql in osvm.user_for(v.slot_id).lower()
        or q == str(v.slot_id)
    ]
    return vms.filter(id__in=matched_ids)

def build_rows(vms):
    """테이블 행 조립. PROVISIONING 은 아직 FIP·계정이 확정 전이라 '—' 로 가린다"""
    rows = []
    for v in vms:
        row = {"vm": v, "name": osvm.name_for(v.slot_id)}
        if v.status == Vm.PROVISIONING:
            row["fip"] = "—"
            row["user"] = "—"
        else:
            row["fip"] = osvm.fip_for(v.slot_id)
            row["user"] = osvm.user_for(v.slot_id)
        if v.status == Vm.FAILED:
            label = friendly_label(v.error or "")
            row["fail_label"] = label
            row["fail_desc"] = FAILED_DESCRIPTIONS.get(label, FAILED_DESCRIPTIONS["실패"])
        rows.append(row)
    return rows
```

템플릿에서 함수 호출이 불가하므로 계산값을 여기서 미리 만들어 dict로 넘김.

### 서버 → 화면

| 변수 | 쓰임 |
| --- | --- |
| `rows` | 목록 테이블 각 행 |
| `status_counts` | 상태 칩 개수, 진행바 세그먼트 비율 |
| `total_count` | 전체 칩 개수. 0이면 빈 상태 화면으로 대체 |
| `status_filter` | 선택된 칩 표시, 검색 폼 hidden 값 |
| `q` | 검색창 값 유지, 칩 링크에 재삽입 |
| `taken` · `free` · `total` | 여유 슬롯 표기, 생성 모달 |
| `show_strip` | 진행바 노출 여부, 폴링 스크립트 삽입 여부 |
| `strip_total` | 진행바 비율 분모 |

`rows` 각 항목

| 키 | 값 | 비고 |
| --- | --- | --- |
| `vm` | `Vm` 인스턴스 | `slot_id` · `status` · `created_at` · `error` · `id` 사용 |
| `name` | `osvm.name_for()` |  |
| `fip` | `osvm.fip_for()` | PROVISIONING이면 `—` |
| `user` | `osvm.user_for()` | PROVISIONING이면 `—` |
| `fail_label` | `friendly_label()` | FAILED일 때만 |
| `fail_desc` | `FAILED_DESCRIPTIONS` 조회 | FAILED일 때만 |

### 실패 사유 판정 — `services.py`

워커가 남긴 원본 `error` 문자열을 소문자로 낮춘 뒤 키워드 우선순위로 분류. 결과는 `rows`에 실려 FAILED 팝오버에 표시됨.

```python
def friendly_label(error: str) -> str:
    """워커가 남긴 예외 문자열을 FAILED 팝오버용 라벨로 변환"""
    e = error.lower()
    if "badrequest" in e:
        return "잘못된 요청 (설정값 오류)"
    if " 401" in e:
        return "인증 만료"
    if "forbidden" in e:
        return "자원 한도 초과 (Quota)"
    # /servers/ 포함 여부로 VM 소실과 설정 오류를 구분
    if "notfound" in e or " 404" in e:
        if "/servers/" in e:
            return "VM 인스턴스 소실"
        return "리소스 없음 (image/flavor/network 설정 오류)"
    # FIP 관련이면 IP 충돌, 아니면 이름/상태 충돌
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
```

### 안내 문구 — `labels.py`

판정 결과(라벨)를 키로 쓰므로 문자열이 정확히 일치해야 함. 표현 계층이라 별도 파일로 분리했고, 프론트/백엔드 분리 시 프론트로 이동할 후보.

```python
FAILED_DESCRIPTIONS = {
    "잘못된 요청 (설정값 오류)": "image·flavor·network 설정값에 문제가 있어요. 운영자 확인이 필요해요.",
    "인증 만료": "작업 중 OpenStack 인증이 만료됐어요. 운영자 확인이 필요해요.",
    # ... 총 13개
    "실패": "원인을 특정하지 못했어요. 아래 원본 로그를 확인해주세요.",
}
```

### 상태 갱신

워커가 DB 상태를 바꾸는 동안 화면을 최신화하는 유일한 수단. 서버 푸시나 부분 갱신 없이 페이지 전체를 다시 요청함.

```jsx
{% if show_strip %}
// 모달이 열려 있거나 체크박스 선택 중이면 작업이 날아가므로 건너뜀
setInterval(() => {
  if (!dlg.open && !hasSelection()) location.reload();
}, 5000);
{% endif %}
```

---

## 4. 회수

체크박스 선택 → `선택 회수` 또는 `전체 회수` → `confirm()` → `POST /portal/` → `_handle_reclaim()` → 목록으로 리다이렉트

### 화면 → 서버

두 버튼이 같은 폼 하나를 공유하고, 어느 쪽으로 제출됐는지는 `action` 값으로 구분. 전체 회수 버튼은 폼 밖에 있으나 `form="vm-form"` 속성으로 연결됨.

| 필드명 | 값 | 읽는 곳 |
| --- | --- | --- |
| `action` | `delete_all` 또는 `delete_selected` | `request.POST.get("action")` |
| `vm_ids` | 체크된 VM의 `id` 다중 값 | `request.POST.getlist("vm_ids")` |
| `csrfmiddlewaretoken` | `{% csrf_token %}` | CSRF 미들웨어 |
- 체크박스는 ACTIVE · FAILED에서만 활성. 그 외 상태는 `disabled`이라 전송되지 않음.
- 제출 직전 JS `confirm()`으로 한 번 더 확인. `e.submitter.value`로 전체/선택을 구분해 문구를 다르게 표시.

### 처리 — `views.py`

`list_view()`의 POST 분기가 호출. 조회 경로와 섞이지 않도록 별도 함수로 분리했으나, 목록 화면과 같은 URL을 쓰므로 뷰 자체는 하나로 유지.

```python
def _handle_reclaim(request):
    """회수 처리. FAILED 는 삭제할 자원이 없어 숨김으로 대체한다"""
    action = request.POST.get("action")

    if action == "delete_all":
        prov.request_delete_all()
        services.dismiss_all_failed()

    elif action == "delete_selected":
        for vid in request.POST.getlist("vm_ids"):
            vid = int(vid)
            rec = Vm.objects.filter(pk=vid).first()
            if rec and rec.status == Vm.FAILED:
                services.dismiss(vid)
            else:
                prov.request_delete(vid)

    return redirect("portal:list")
```

뷰가 `provisioning.models.Vm`을 직접 보는 유일한 지점. 회수와 숨김을 가르는 판단이라, 처리 정책이 확정되면 서비스로 옮길 대상.

### 숨김 처리 — `services.py`

```python
def dismiss(vm_id):
    """FAILED 한 건 숨김"""
    DismissedFailure.objects.get_or_create(vm_id=vm_id)

def dismiss_all_failed():
    """전체 회수 시 FAILED 일괄 숨김. 이미 있으면 무시"""
    failed_ids = Vm.objects.filter(status=Vm.FAILED).values_list("id", flat=True)
    DismissedFailure.objects.bulk_create(
        [DismissedFailure(vm_id=vid) for vid in failed_ids],
        ignore_conflicts=True,
    )
```

### 숨김 기록 모델 — `models.py`

FAILED 숨김이 로그아웃 시 초기화되던 세션 방식을 대체하기 위한 테이블. 조회 단계의 `visible_vms()`에서 `exclude`로 소비됨.

```python
class DismissedFailure(models.Model):
    """
    [Phase 0.5 임시 해결책]
    FAILED VM을 화면에서 숨기는 기록. Vm 원본은 건드리지 않음.

    TODO(Phase 1): provisioning.Vm.dismissed_at 필드로 이관 예정 (협의 필요).
    이관되면 이 모델은 삭제.
    """
    # unique 로 중복 기록 방지 (bulk_create 의 ignore_conflicts 가 여기 의존)
    vm_id = models.IntegerField(unique=True)
    dismissed_at = models.DateTimeField(auto_now_add=True)
```
