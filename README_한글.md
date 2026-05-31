# 🔍 사이트 변경 모니터 (대성마이맥 강사 모니터링) — 설치 안내서

매일 정해진 시각에 **대성마이맥의 과목별 강사 영역**을 자동으로 확인하고,
**무엇이 바뀌었는지(강사 추가/삭제·소개문구·사진)** 를 정리해 줍니다.
동료들은 **웹 주소만 열면** 되고, 별도 계정이 필요 없습니다. **AI 없이 완전 무료**로 동작합니다.

## 어떻게 잡아내나
- **글자 변화**(강사 이름·소개문구·이벤트 배지 등): 추가/삭제 목록으로 표시
- **사진/이미지 변화**: 이전·현재 화면을 픽셀 비교 → 바뀐 부분을 **빨강으로 강조한 이미지**로 표시
  (글자는 그대로인데 사진만 바뀐 경우도 "사진 교체 가능성" 경고로 알려줌)

## 전체 그림
```
[GitHub Actions]  매일 자동 → 과목 탭 클릭 → 강사 영역 캡처 → 비교 → 기록 → (변경 시 알림)
        ▼ 커밋
[GitHub 저장소]  변경 요약·스크린샷·이력 영구 보관
        ▼ 자동 갱신
[Streamlit Cloud]  팀이 다 같이 보는 웹 화면 + "지금 바로 확인" 버튼
```

---

## 준비물 (모두 무료, AI 계정 불필요)
1. GitHub 계정 — https://github.com
2. Streamlit 계정 — https://share.streamlit.io (GitHub 로 로그인)

---

## 설치 (약 10분, 코딩 필요 없음)

### 1단계. GitHub 저장소 만들기 + 파일 올리기
1. GitHub **New repository** → 이름 입력 → **Private** → Create
2. 루트의 일반 파일들(app.py, check.py, watcher.py, requirements.txt, packages.txt, README_한글.md)은 **드래그로 업로드**
3. 숨김/중첩 파일 2개는 **Add file → Create new file** 로 경로를 직접 타이핑해서 생성:
   - `.github/workflows/daily.yml`  (내용 붙여넣기)
   - `data/sites.json`  (아래 '사이트 추가' 참고)
   - (state/reports 폴더는 실행 시 자동 생성되니 안 올려도 됨)

### 2단계. 자동 실행 켜기 + 첫 기준 만들기
저장소 → **Actions** 탭 → 워크플로 활성화 → **"매일 사이트 변경 확인" → Run workflow**
→ 첫 실행은 "오늘 상태"를 기준으로 저장. (다음 실행부터 비교 시작)
→ **별도 알림 설정 없이 바로 실행됩니다.** (알림은 맨 아래 '선택' 항목 참고)

### 3단계. Streamlit Cloud 배포
https://share.streamlit.io → **Create app** → 저장소 선택 → Main file 에 `app.py` → Deploy
→ 배포된 주소가 **팀이 공유할 웹 주소**.

### 4단계. (선택) 접속 비밀번호 걸기
Streamlit 앱 → **⋮ → Settings → Secrets** 에:
```toml
APP_PASSWORD = "팀이쓸접속비밀번호"
```

---

## 모니터링할 과목 추가/변경 — `data/sites.json`
```json
{
  "maimac_social": {
    "name": "대성마이맥 - 사회 강사",
    "url": "https://여기에_실제_페이지_주소",
    "subject": "사회",
    "section_anchor": "마이맥 선생님",
    "full_page": false
  },
  "maimac_history": {
    "name": "대성마이맥 - 한국사 강사",
    "url": "https://여기에_실제_페이지_주소",
    "subject": "한국사",
    "section_anchor": "마이맥 선생님",
    "full_page": false
  }
}
```
- `url`: 강사 목록이 보이는 실제 페이지 주소로 **반드시 교체**하세요.
- `subject`: 클릭할 과목 탭 글자 (예: 국어/수학/영어/사회/과학/한국사/대학별)
- `section_anchor`: 그 영역을 찾는 기준 글자 (대성마이맥은 "마이맥 선생님")
- 과목을 더 추가하려면 블록을 복사하고 키(`maimac_social` 등)만 다르게 하세요.

## 자동 실행 시간 — `.github/workflows/daily.yml`
`cron: "0 0 * * *"` 수정 (UTC 기준). 한국시간 09시 → `0 0 * * *`, 18시 → `0 9 * * *`

---

## 사용법
- **자동 기록 보기** 탭: 날짜별 변경 요약 + 이전/현재/변경영역(빨강) 이미지
- **지금 바로 확인** 탭: 버튼 한 번으로 현재 상태를 마지막 기준과 즉석 비교

## 알아둘 점 / 한계
- 첫날은 비교 대상이 없어 **기준 저장만** 합니다. 비교는 다음 실행부터.
- 과목 탭 클릭·강사 영역 캡처는 **화면 글자("사회", "마이맥 선생님") 기준**으로 찾습니다.
  못 찾으면 전체 화면을 캡처하니, 첫 실행 결과 이미지가 의도한 강사 영역인지 한 번 확인하세요.
  (영역이 어긋나면 결과 화면을 공유해 주시면 맞춰드립니다.)
- 로그인이 필요한 페이지(관심쌤 등)는 이 버전 미지원.
- AI 를 쓰지 않으므로 광고/배너 변동이 목록에 섞일 수 있습니다. `section_anchor` 로 강사 영역만 보면 노이즈가 크게 줄어요.

## (선택) 변경 시 Slack/Discord 알림 받기
설치를 다 끝낸 뒤, 알림을 원할 때만 추가하면 됩니다. (없어도 자동 실행은 정상 작동)
저장소 → **Settings → Secrets and variables → Actions → New repository secret**
- 이름 `ALERT_WEBHOOK`, 값에 Slack/Discord 웹훅 주소
- (선택) 이름 `APP_URL`, 값에 Streamlit 주소 (알림에 링크로 들어감)

## (선택) 내 컴퓨터에서 먼저 테스트
- Mac/Linux: `bash setup.sh` → `bash run.sh`
- Windows: `setup.bat` 더블클릭 → `run.bat` 더블클릭
