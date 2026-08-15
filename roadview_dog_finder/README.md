# 로드뷰 강아지 탐색기 (Naver Roadview Dog Finder)

네이버 거리뷰(로드뷰)에서 **특정 리/읍 범위**의 **마을 안길·농로(큰길 제외)**를 자동으로 훑어,
**최근 N년(기본 4년) 이내**에 촬영된 파노라마에서 **강아지가 찍힌 지점**을 찾아
**네이버 로드뷰 바로가기 링크 목록**으로 뽑아주는 로컬 도구입니다.

> 사람이 로드뷰를 5m씩 옮기며 일일이 확인하는 대신, "전부 싸게 훑고 → 강아지가 보이는 지점만 링크로 추려주는" 방식입니다.
> API/크롤링 과금 없이 오픈소스만 사용하며, 강아지 탐지는 노트북 GPU(예: RTX 3050)에서 돌아갑니다.

## 동작 방식

```
리/읍 경계  ─▶  OSM 도로망(큰길 제외)  ─▶  도로 따라 좌표 샘플링
        ─▶  streetlevel로 파노라마 조회(촬영일 4년 이내 + 최신만)
        ─▶  큐브맵 측면 4방향 이미지 다운로드
        ─▶  YOLO로 강아지 탐지(GPU)
        ─▶  강아지 지점 → 로드뷰 링크 목록(CSV/TXT) + 지도 HTML
```

## 설치 (Windows + NVIDIA GPU 기준)

Python 3.11 권장. PowerShell에서:

```powershell
# 저장소 폴더로 이동 후
python -m venv .venv
.\.venv\Scripts\activate

# 1) GPU(CUDA)용 torch 먼저 설치 (RTX 3050, CUDA 12.1 예시)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121

# 2) 나머지 의존성
pip install -r roadview_dog_finder/requirements.txt
```

GPU가 없다면 1번을 건너뛰면 됩니다(자동으로 CPU 사용, 느림). GPU 인식 확인:

```powershell
python -c "import torch; print('CUDA:', torch.cuda.is_available())"
```

## 사용법

작업 결과(이미지 포함)는 용량이 크므로 **외장 드라이브 경로**를 `--output-dir`로 지정하세요.

### 리 1곳 파일럿 (권장 시작점)

지명이 OSM에 있으면:

```powershell
python -m roadview_dog_finder.run --place "전라남도 해남군 ○○면 ○○리" --output-dir D:\rdf
```

지명이 잘 안 잡히면 중심 좌표 + 반경(미터)으로:

```powershell
python -m roadview_dog_finder.run --center 34.5001 126.6002 --radius 800 --output-dir D:\rdf
```

먼저 소규모로 테스트하려면 `--limit`로 파노라마 개수를 제한:

```powershell
python -m roadview_dog_finder.run --center 34.5001 126.6002 --radius 500 --limit 50 --output-dir D:\rdf
```

### 결과물

작업 폴더(`<output-dir>/<지역라벨>/`) 안에:

- `roadview_links.txt` — **강아지 발견 지점의 네이버 로드뷰 링크 목록**(신뢰도 높은 순)
- `results.csv` — 좌표·촬영일·강아지 수·신뢰도·로드뷰 링크
- `map.html` — 지도(핀 클릭 시 로드뷰 바로가기 + 썸네일)
- `panoramas.jsonl`, `images/`, `detections.jsonl` — 중간 산출물(이어받기용)

`roadview_links.txt`의 링크를 클릭하면 해당 지점 네이버 로드뷰가 바로 열립니다. 실제 강아지인지 눈으로 확인하고 봉사하러 가시면 됩니다.

## 단계별 실행 / 이어받기

각 단계 결과는 저장되므로 중간에 끊겨도 이어서 실행됩니다.

```powershell
# 특정 단계만 실행 (area,collect,download,detect,report)
python -m roadview_dog_finder.run --center 34.5 126.6 --radius 800 --output-dir D:\rdf --stages area,collect
python -m roadview_dog_finder.run --center 34.5 126.6 --radius 800 --output-dir D:\rdf --stages download,detect,report
```

## 주요 옵션

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--place` / `--bbox` / `--center`+`--radius` / `--geojson` | 대상 지역 지정(택1) | - |
| `--output-dir` | 작업/결과 폴더(외장 권장) | `./rdf_output` |
| `--sample-interval` | 좌표 샘플 간격(m) | 10 |
| `--max-age-years` | 촬영일 최대 경과 연수 | 4 |
| `--expand-neighbors` | 인접 파노라마까지 확장 수집(커버리지↑, 요청↑) | off |
| `--request-delay` | 요청 간격(초, 저부하 운영) | 0.7 |
| `--image-zoom` | 이미지 해상도 0~2 | 1 |
| `--all-faces` | 측면 4개 대신 6개 면 모두 | off |
| `--model` | YOLO 모델 | `yolov8n.pt` |
| `--conf` | 강아지 탐지 신뢰도 임계값 | 0.25 |
| `--device` | `cuda:0` / `cpu` | 자동 |
| `--limit` | 파노라마 처리 개수 제한 | - |

### 정확도 튜닝 팁

- **놓침이 많다** → `--conf 0.15`로 낮추거나 `--model yolov8s.pt`(더 큰 모델), `--image-zoom 2`.
- **헛검출이 많다** → `--conf 0.35~0.5`로 높이기.
- **커버리지가 부족하다** → `--expand-neighbors`, `--sample-interval 7`.

## 읍 단위로 확대

파일럿이 만족스러우면 반경을 키우거나 읍 지명으로 실행하면 됩니다. 요청량이 커지므로
`--request-delay`를 유지(0.7초 이상)해 저부하로 운영하세요. 이미지가 많이 쌓이니 외장 드라이브 필수.

## 주의사항

- 강아지 탐지는 **"완벽 자동 판별기"가 아니라 후보를 좁혀주는 도구**입니다. 최종 확인은 사람이 합니다.
- `streetlevel`은 네이버 내부 엔드포인트를 사용하는 비공식 방식이라 **차단·약관 회색지대**가 있습니다.
  개인 리서치 용도로 `--request-delay`를 지켜 저부하로 사용하세요.
- 시골 좁은 농로는 **로드뷰 커버리지 자체가 없는 구간**이 있어 빈틈이 생길 수 있습니다(정상).
- 촬영일 필터(4년)는 파노라마 메타데이터의 `date`/`is_latest`에 기반합니다.

## 오프라인 테스트

네트워크·GPU 없이 좌표 샘플링 로직만 검증:

```bash
python -m roadview_dog_finder.tests.test_area
```
