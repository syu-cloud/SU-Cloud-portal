<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-09-05 | Updated: 2026-09-05 -->

# config

## 목적
Django 프로젝트 패키지: settings, 루트 URLconf, WSGI/ASGI 진입점. `manage.py`, `wsgi.py`, `asgi.py` 모두 `DJANGO_SETTINGS_MODULE` 기본값이 `config.settings` 다.

## 주요 파일
| 파일 | 설명 |
|------|------|
| `settings.py` | `/opt/su-portal/.env` 를 로드한 뒤 환경 의존 값을 전부 `os.environ[...]` 로 읽는다. `portal`, `provisioning` 설치(`catalog` 는 미설치). PostgreSQL 백엔드 전용. 쿠키 이름 `suportal_sessionid` / `suportal_csrftoken` 커스텀. |
| `urls.py` | `admin/` → Django admin, `""` → `portal.views.index`. 그 외 라우트 없음. |
| `wsgi.py` | 표준 WSGI `application` |
| `asgi.py` | 표준 ASGI `application`(현재 배포에서는 미사용) |
| `__init__.py` | 빈 패키지 마커 |

## AI 에이전트 안내

### 이 디렉터리에서 작업할 때
- `settings.py` docstring 대로 이 파일은 개발계/운영계 전환 시 수정하지 않는다. 환경 차이는 `.env` 로 처리한다.
- 필수 env 변수(없으면 KeyError): `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`(쉼표 구분), `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`. `DJANGO_DEBUG` 는 기본 false.
- `.env` 경로가 절대 경로다. `/opt/su-portal` 밖에서 실행하려면 변수를 다른 방식으로 export 해야 한다.
- 새 Django 앱은 여기 `INSTALLED_APPS` 에 추가하고, 새 라우트는 `urls.py` 에 넣는다.
- `TIME_ZONE="UTC"`, `USE_TZ=True`. `provisioning.services.claim` 의 stale 비교가 aware datetime 을 전제로 한다.

### 테스트 요구사항
- `.venv/bin/python manage.py check` 로 settings 부팅 확인. env 변수 누락은 여기서 의도적으로 실패한다.

## 의존성

### 내부
- `portal.views.index`(`urls.py` 가 import)

### 외부
- Django 5.2, python-dotenv, psycopg(PostgreSQL 백엔드)

<!-- MANUAL: 이 줄 아래에 수동으로 추가한 내용은 재생성 시 보존됨 -->
