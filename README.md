# royal

Instagram Private API(instagrapi) 기반 **모바일-PC 세션 연동** 모듈입니다.

challenge(블록/검증)로 세션 등록이 실패하는 문제를 줄이기 위해, **한 번 통과한 Android 디바이스 지문 + 쿠키**를 저장하고 PC에서 재사용합니다.

## 설치

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2FA(TOTP) 계정은 추가로:

```bash
pip install pyotp
```

## 설정

`.env.example`을 복사해 `.env`를 만듭니다.

```bash
cp .env.example .env
```

| 변수 | 설명 |
|------|------|
| `IG_USERNAME` | Instagram 사용자명 |
| `IG_PASSWORD` | 비밀번호 |
| `IG_TOTP_SECRET` | (선택) Authenticator 2FA secret |
| `IG_PROXY` | (권장) 계정별 고정 residential proxy |
| `SESSION_STORAGE` | `file`(기본) 또는 `redis` |
| `SESSION_FILE` | 파일 저장 경로 (기본: `sessions/session.json`) |

## 사용법

### 1. 최초 로그인 (challenge 통과 후 세션 저장)

```bash
python main.py login
```

challenge 발생 시 터미널에서 SMS/이메일 인증코드를 입력합니다.  
앱 승인 유형이면 Instagram 앱에서 "본인입니다"를 승인한 뒤 계속 진행합니다.

### 2. 이후 실행 (저장된 세션 재사용)

```bash
python main.py verify
```

`load_settings` → `login` → `dump_settings` 흐름으로 **동일 디바이스 identity**를 유지합니다.

### 3. 코드에서 사용

```python
from auth import get_client

client = get_client()
feed = client.get_timeline_feed()
```

## 아키텍처

```
auth/
├── challenge_handler.py   # SMS/Email/TOTP challenge 처리
├── session_manager.py     # file / Redis 세션 저장
└── login.py               # UUID 유지 relogin 포함 best-practice 로그인
config.py                  # 계정, proxy, locale 설정
```

## 모바일-PC 연동 핵심 원칙

1. **`load_settings()`는 반드시 `login()` 이전**에 호출
2. challenge 통과 직후 **`dump_settings()`로 세션 저장**
3. 세션 만료 시 **device UUID는 유지**하고 relogin
4. **계정당 1개의 고정 residential proxy** 사용
5. `session.json` / Redis 키는 **절대 git에 커밋하지 않음**

## sessionid 로그인 (비권장, 테스트용)

```bash
python main.py sessionid "<browser_sessionid>"
```

브라우저 `sessionid`는 Mobile API에서 자주 거부됩니다. 운영 환경에서는 `login` + `dump_settings` 방식을 사용하세요.

## Redis 세션 저장

`.env`에서:

```
SESSION_STORAGE=redis
REDIS_URL=redis://localhost:6379/0
REDIS_SESSION_KEY=ig:session:your_username
```

## 문제 해결

- **challenge_required 반복**: Instagram 앱/웹에서 수동 해제 후 24~48시간 대기
- **LoginRequired**: `python main.py login`으로 UUID 유지 relogin
- **proxy_address_is_blocked**: residential proxy IP 교체
- **please_wait_a_few_minutes**: 자동화 중단 및 cooldown
