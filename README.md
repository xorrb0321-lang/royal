# KakaoTalk Instagram Collector

카카오톡 PC 오픈채팅방에서 Instagram 프로필 링크를 실시간 수집하는 Windows 프로그램입니다.

## 요구 사항

- Windows 10/11
- Python 3.11+
- 카카오톡 PC 실행
- 오픈채팅방 10~20개 이상 열어둔 상태

## 설치

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Windows 전용 UI Automation:

```bash
pip install uiautomation
```

## 실행

### Headless (24시간 실행)

```bash
python main.py --headless
```

### GUI

```bash
python main.py --gui
```

## 설정

- `config/settings.yaml` — DB 경로, 폴링 주기, 재연결 간격
- `config/selectors.yaml` — UI Automation selector (Phase 0 정찰 후 조정)

### 채팅방 화이트리스트

`config/settings.yaml`:

```yaml
parser:
  room_title_whitelist:
    - "오픈채팅"
```

비어 있으면 열린 채팅방 전체를 감시합니다.

## DB

SQLite `data/instagram.db`

```sql
instagram_accounts (id, username UNIQUE, created_at)
```

## Phase 0 (필수)

Windows에서 카카오톡 UI를 정찰한 뒤 `config/selectors.yaml`을 조정하세요.

자세한 내용: `docs/ui-map.md`

## 테스트

```bash
pip install pytest
pytest
```

## 아키텍처

```
app/         오케스트레이션
collector/   Windows UI Automation
parser/      URL / Instagram 정규화
database/    SQLite
config/      설정
utils/       로그, 캐시, 재시도
ui/          Tkinter UI (비즈니스 로직 없음)
```

## 주의

- 카카오 공식 API를 사용하지 않습니다.
- UI 구조 변경 시 selector 업데이트가 필요할 수 있습니다.
- 이용 약관 및 관련 법규를 준수하여 사용하세요.
