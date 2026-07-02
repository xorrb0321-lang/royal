# KakaoTalk Export → Instagram Collector

카카오톡 PC **대화보내기(.txt)** 파일에서 Instagram 프로필 링크를 추출하는 프로그램입니다.

## 특징

- **안전**: 카카오 API·UI 자동화·패킷 스니핑 없음
- **파싱**: [kakaotalk-msg-preprocessor](https://github.com/uoneway/kakaotalk_msg_preprocessor) 오픈소스 사용
- **Instagram만**: 프로필 URL → `username` 추출 (`/p/`, `/reel/` 제외)
- **중복 제거**: 동일 username 1회만 저장 (SQLite + CSV)
- **자동화**: `exports/` 폴더 감시 + 수동 파일 선택

## 설치

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 사용법

### 1. 카카오톡에서 대화보내기

1. 오픈채팅방 입장
2. `Ctrl + S` (또는 메뉴 → 대화 내용 → 대화보내기)
3. `exports` 폴더에 저장

### 2. 프로그램 실행

```bash
# GUI (기본)
python main.py

# 콘솔 백그라운드
python main.py --headless

# 파일 1개 직접 처리
python main.py --headless --file exports\방이름.txt

# exports 폴더 1회 스캔
python main.py --headless --scan-once
```

### 3. 결과 확인

- `output/instagram_accounts.csv` — 엑셀에서 열기
- `data/state.db` — 중복 체크용 (내부)

## CSV 컬럼

| 컬럼 | 설명 |
|------|------|
| username | Instagram 계정 (예: abc) |
| first_seen_at | 프로그램이 처음 저장한 시각 |
| message_datetime | 대화 메시지 시각 |
| author | 작성자 닉네임 |
| room_name | 채팅방 (파일명 추정) |
| source_url | 원본 Instagram URL |

## 운영 주의사항

- PC 카카오톡 **로그아웃 금지** (오픈채팅 과거 대화 복구 불가)
- 오픈채팅방 **퇴장 금지**
- **실시간 아님** — 보내기할 때마다 새 링크 반영
- 2~3시간마다 방마다 `Ctrl+S` 보내기 권장

자세한 내용: `docs/OPERATIONS.md`

## 프로젝트 구조

```
adapters/     kakaotalk-msg-preprocessor 래퍼
ingest/       파일 로드, 폴더 감시, 분할 txt 병합
filters/      시스템 메시지 제외, Instagram 추출
parser/       URL 정규식, Instagram 정규화
state/        SQLite (중복, fingerprint)
exporter/     CSV 저장
app/          파이프라인, 애플리케이션
ui/           Tkinter GUI
```

## 테스트

```bash
pip install pytest
pytest
```

## 설정

`config/settings.yaml`:

```yaml
ingest:
  watch_dir: "exports"
  incremental: true

export:
  output_dir: "output"
  csv_filename: "instagram_accounts.csv"
```
