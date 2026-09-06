<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-09-05 | Updated: 2026-09-05 -->

# catalog

## 목적
미사용 `startapp` 스캐폴드. `INSTALLED_APPS` 에 **없고**, 모델·뷰·URL·마이그레이션이 없으며, 어디서도 import 하지 않는다. 이름으로 보아 현재 `osclient/vm.py` 가 `SU_*` env 변수로 읽는 VM 카탈로그(image / flavor / network / security group / keypair)를 옮겨올 자리로 의도된 듯하다.

## 주요 파일
| 파일 | 설명 |
|------|------|
| `apps.py` | `CatalogConfig` |
| `admin.py`, `models.py`, `views.py`, `tests.py` | 빈 Django 스캐폴드 |
| `__init__.py` | 비어 있음 |

## 하위 디렉터리
| 디렉터리 | 역할 |
|----------|------|
| `migrations/` | 빈 `__init__.py` 만 있음. AGENTS.md 없음 |

## AI 에이전트 안내

### 이 디렉터리에서 작업할 때
- 이 앱이 활성화되어 있다고 가정하지 말 것. 사용하려면 `config/settings.py` 의 `INSTALLED_APPS` 에 `"catalog"` 를 추가하고 `makemigrations catalog` 를 실행한다.
- 카탈로그 데이터를 env 에서 여기로 옮기면 `osclient/vm.py` 가 직접 읽는 `SU_IMAGE_ID`, `SU_FLAVOR_ID`, `SU_NETWORK_ID`, `SU_SECGROUP`, `SU_KEYPAIR`, `SU_FIP_PREFIX` 호출 지점을 함께 바꿔야 한다.

<!-- MANUAL: 이 줄 아래에 수동으로 추가한 내용은 재생성 시 보존됨 -->
