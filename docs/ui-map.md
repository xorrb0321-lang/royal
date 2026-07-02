# Phase 0 UI 정찰 결과를 여기에 기록하세요.

## 도구

- Accessibility Insights for Windows
- Inspect.exe (Windows SDK)
- FlaUInspect

## 확인 항목

1. KakaoTalk.exe 프로세스명
2. 채팅방 창 ClassName / Name
3. 메시지 List 컨테이너 ControlType
4. ListItem 내 Text / Hyperlink 구조
5. StructureChanged 이벤트 발생 여부

## selectors.yaml 업데이트

정찰 후 `config/selectors.yaml`의 class_name, search_depth 등을 조정하세요.
