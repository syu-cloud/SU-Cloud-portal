# SU-Cloud-portal 작업 규칙

## 언어
- 사용자와의 모든 대화, 설명, 요약, 질문, 계획은 **한국어**로 한다.
- 코드 주석, docstring, admin 라벨, management 명령 출력은 기존 관례대로 한국어를 유지한다.
- 커밋 메시지는 기존 이력에 맞춰 영어 conventional commit 형식(`feat:`, `fix:`, `chore:`)을 유지한다.
- 식별자(변수·함수·클래스·env 키), 파일 경로, 명령어, 에러 메시지 원문은 번역하지 않고 그대로 쓴다.
- 루트와 각 디렉터리의 `AGENTS.md` 는 한국어로 작성되어 있다. `/oh-my-claudecode:deepinit` 으로 재생성하거나 갱신할 때도 한국어로 유지하고, `<!-- MANUAL: -->` 아래 내용은 보존한다.

## 코드베이스 안내
- 구조, 규칙, 주의사항은 루트 `AGENTS.md` 와 해당 디렉터리의 `AGENTS.md` 를 먼저 읽는다. 여기에 중복 기재하지 않는다.
- 설계 배경·검증 결과·의사결정 현황은 `docs/` 에 있다. `docs/README.md` 의 읽기 순서를 따르고, 문서와 코드가 다르면 코드를 따른다. 새 문서는 번호를 이어 붙이고 README 표에 추가한다.
- 핵심 원칙 요약: env 전용 설정(`/opt/su-portal/.env`), PostgreSQL 필수, `Vm` 은 append-only, 모든 부작용은 멱등, 비밀번호 DB 저장 금지, `.env` / `*.pem` 커밋 금지.

## 검증
- 변경 후 `.venv/bin/python manage.py check` 를 기본 확인으로 한다.
- `probes/` 스크립트는 실제 개발계 클라우드와 DB 를 변경한다. 사용자의 명시적 지시 없이 실행하지 않는다.
