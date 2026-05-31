# 🔍 사이트 변경 모니터 — 설치 안내서

매일 정해진 시각에 웹사이트를 자동으로 확인하고, **AI가 무엇이 바뀌었는지 한국어로 정리**해 줍니다.
동료들은 **웹 주소만 열면** 되고, 클로드 계정이 없어도 됩니다.

## 전체 그림
```
[GitHub Actions]  매일 자동 실행 → 사이트 확인 → AI 보고서 → 저장소에 기록 → (변경 시 알림)
        │ 기록을 커밋
        ▼
[GitHub 저장소]  보고서·스크린샷·변경 이력 보관 (= 영구 기록)
        │ 화면이 자동 갱신
        ▼
[Streamlit Cloud]  팀이 다 같이 보는 웹 화면 + "지금 바로 확인" 버튼
```

---

## 준비물 (모두 무료)
1. GitHub 계정 — https://github.com
2. Streamlit 계정 — https://share.streamlit.io (GitHub 로 로그인)
3. Anthropic API 키 — https://console.anthropic.com  (※ claude.ai 구독과 별개. 사용한 만큼만 과금, 보통 1회 확인에 몇 원~몇십 원)

---

## 설치 (약 15분, 코딩 필요 없음)

### 1단계. GitHub 저장소 만들기
1. GitHub 에서 **New repository** → 이름 입력 → **Private** 선택 → Create
2. 이 폴더의 모든 파일을 저장소에 올리기 (웹에서 **Add file → Upload files** 로 드래그 업로드 가능)

### 2단계. AI 키를 GitHub 에 등록 (자동 실행용)
저장소 → **Settings → Secrets and variables → Actions → New repository secret**
- 이름 `ANTHROPIC_API_KEY`, 값에 본인 API 키 입력 → 저장
- (선택) 알림 받기: 이름 `ALERT_WEBHOOK`, 값에 Slack/Discord 웹훅 주소
- (선택) 이름 `APP_URL`, 값에 4단계에서 받을 Streamlit 주소 (알림에 링크로 들어감)

### 3단계. 자동 실행 켜기 + 첫 기준 만들기
1. 저장소 → **Actions** 탭 → 워크플로 활성화
2. **"매일 사이트 변경 확인" → Run workflow** 를 한 번 눌러 수동 실행
   → 첫 실행은 "오늘 상태"를 기준으로 저장합니다. (다음날부터 비교 시작)

### 4단계. Streamlit Cloud 에 웹 화면 배포
1. https://share.streamlit.io → **Create app** → 방금 만든 저장소 선택
2. Main file 에 `app.py` 입력 → Deploy
3. 배포된 주소(예: `https://...streamlit.app`)가 **팀이 공유할 웹 주소**입니다.

### 5단계. 웹 화면에 키·비밀번호 등록
Streamlit 앱 화면 → 우상단 **⋮ → Settings → Secrets** 에 아래를 붙여넣기:
```toml
ANTHROPIC_API_KEY = "sk-ant-본인키"
APP_PASSWORD = "팀이쓸접속비밀번호"
AI_MODEL = "claude-sonnet-4-6"
```
저장하면 끝. 이제 동료들은 주소를 열고 비밀번호만 입력하면 됩니다.

---

## 모니터링 항목 설정 (대성마이맥)
저장소의 `data/sites.json` 을 GitHub 웹에서 편집합니다. 두 가지 감시 유형이 있어요.

### 유형 A — 과목별 강사 목록 (강사 추가/삭제·소개문구·사진)
메인 페이지에서 과목 탭을 클릭하고 "마이맥 선생님" 영역만 캡처합니다.
```json
"maimac_social": {
  "name": "대성마이맥 - 사회 강사 목록",
  "url": "https://www.mimacstudy.com",
  "subject": "사회",
  "section_anchor": "마이맥 선생님",
  "full_page": false,
  "focus": "강사 추가/삭제, 소개 문구, 사진 변경 확인"
}
```

### 유형 B — 강사 개별 페이지 (최신소식/공지 + 배너)
강사 페이지에 들어가 공지·배너 변경을 봅니다. **그 강사 페이지를 브라우저에서 연 뒤 주소창 URL을 복사해 넣으세요.**
```json
"teacher_lim_notice": {
  "name": "임정환(사회) 최신소식",
  "url": "여기에_그_강사_페이지_주소",
  "section_anchor": "최신소식",
  "focus": "공지·EVENT·OPEN 글 추가/변경만 확인"
},
"teacher_lim_page": {
  "name": "임정환(사회) 배너·전체",
  "url": "여기에_그_강사_페이지_주소",
  "full_page": true,
  "focus": "하단 교재패스 배너 문구·디자인 변경 확인. 상단 자동 슬라이드는 무시"
}
```

### 각 항목 설명
- `name`: 화면에 표시될 이름 (자유)
- `url`: 확인할 주소
- `subject`: (선택) 먼저 클릭할 과목 탭 글자. 예: "사회", "한국사". 없으면 클릭 안 함
- `section_anchor`: (선택) 이 글자가 있는 영역만 캡처. 예: "마이맥 선생님", "최신소식". 없으면 전체
- `full_page`: 페이지 전체 캡처 여부 (배너 감시는 보통 true)
- `focus`: (선택) AI에게 "이 부분을 중점적으로 봐줘" 라고 알려주는 메모
- 맨 앞 키(`maimac_social` 등)는 항목마다 겹치지 않게

> 감시할 강사를 늘리려면 위 B 블록을 복사해 이름·URL만 바꿔 추가하면 됩니다.

### ⚠️ 첫 실행 후 한 번 맞춰보기
이 도구는 사이트 화면을 직접 못 본 상태에서 "글자 기준"으로 영역을 찾습니다.
첫 자동 실행 뒤 **자동 기록 보기** 탭에서 캡처된 이미지가 원하는 영역(강사 목록/최신소식/배너)을 제대로 담았는지 확인하세요.
엉뚱한 곳이 잡혔다면 그 캡처 이미지를 클로드에게 보여주면 `subject`/`section_anchor` 값을 정확히 맞춰 드립니다.

## 자동 실행 시간 바꾸기
`.github/workflows/daily.yml` 의 `cron: "0 0 * * *"` 수정 (UTC 기준).
- 매일 한국시간 09시 → `0 0 * * *`
- 매일 한국시간 18시 → `0 9 * * *`

---

## 사용법
- **자동 기록 보기** 탭: 매일 자동으로 쌓인 날짜별 보고서와 이전/현재/변경영역 이미지를 확인
- **지금 바로 확인** 탭: 버튼 한 번으로 현재 상태를 마지막 기준과 즉석 비교

## 알아두면 좋은 점 / 한계
- **첫날은 비교 대상이 없어 "기준 저장"만** 합니다. 변경 비교는 그 다음 실행부터.
- 로그인이 필요한 사이트는 이 버전에서 지원하지 않습니다 (요청 주시면 추가 가능).
- 비용은 `ANTHROPIC_API_KEY` 주인에게만 청구됩니다. 키 보호를 위해 `APP_PASSWORD` 를 꼭 설정하세요.
- 광고·시계 같은 자잘한 변동은 AI가 알아서 걸러 보고합니다.
- 더 저렴하게: `AI_MODEL` 을 `claude-haiku-4-5-20251001` 로 바꾸면 더 빠르고 저렴합니다.

## (선택) 내 컴퓨터에서 먼저 테스트
- Mac/Linux: 터미널에서 `bash setup.sh` → `bash run.sh`
- Windows: `setup.bat` 더블클릭 → `run.bat` 더블클릭
