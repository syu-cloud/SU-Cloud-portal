<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-09-05 | Updated: 2026-09-05 -->

# portal

## 목적
학생·운영자용 웹 앱. `INSTALLED_APPS` 에 설치되어 있고 `config/urls.py` 에서 `/` 에 마운트되지만 현재는 자리표시자다. 유일한 뷰가 `"HELLO WORLD!"` 를 반환한다. 실제 UI(학생에게 Warpgate 비밀번호를 전달하는 방식 포함)는 `PATCH_NOTES.md` "미결" 항목이다.

## 주요 파일
| 파일 | 설명 |
|------|------|
| `views.py` | `index(request)` → `HttpResponse("HELLO WORLD!")` |
| `apps.py` | `PortalConfig` |
| `admin.py`, `models.py`, `tests.py` | 빈 Django 스캐폴드 |
| `__init__.py` | 비어 있음 |

## 하위 디렉터리
| 디렉터리 | 역할 |
|----------|------|
| `migrations/` | 빈 `__init__.py` 만 있음(모델 없음). AGENTS.md 없음 |

## AI 에이전트 안내

### 이 디렉터리에서 작업할 때
- 학생 대면 기능은 여기에 둔다. 도메인 로직은 `provisioning.services` 에 있으니 호출만 하고 복제하지 않는다.
- templates 디렉터리가 아직 없다. `APP_DIRS=True` 라서 `portal/templates/` 를 만들면 자동 인식된다.
- 비밀번호는 DB 에 저장하지 않는다. 자격증명을 보여주는 UI 는 전달 방식 설계가 선행되어야 한다.
- 모델을 추가하면 `manage.py makemigrations portal` 이 필요하다.

### 테스트 요구사항
- `manage.py check`. 실제 뷰가 들어오기 전까지 `/` 요청 시 자리표시자 본문이 나오면 정상.

## 의존성

### 내부
- `config/urls.py` 에서 라우팅

### 외부
- Django views / templates

<!-- MANUAL: 이 줄 아래에 수동으로 추가한 내용은 재생성 시 보존됨 -->
