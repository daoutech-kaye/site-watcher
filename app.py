"""
대성마이맥 모니터 - 팀 공용 웹 화면 (Streamlit Cloud 배포용). AI 없는 버전.
- 과목(사회/한국사)을 고르면 메인·최신소식·교재패스 배너를 카테고리별로 한 화면에 모아 보여줌
- GitHub Actions 가 매일 기록한 변경 요약/이력을 날짜별로 확인
- 각 항목마다 '지금 바로 확인' 버튼으로 즉석 비교도 가능
"""
import os
import json
import tempfile
from pathlib import Path

import streamlit as st
import watcher

ROOT = Path(__file__).parent
SITES_FILE = ROOT / "data" / "sites.json"
STATE = ROOT / "data" / "state"
REPORTS = ROOT / "data" / "reports"

# 과목/카테고리 표시 순서 (없으면 자동 생략)
SUBJECT_ORDER = ["사회", "한국사"]
CATEGORY_ORDER = ["메인 페이지", "강사 최신소식", "강사 교재패스 배너"]


@st.cache_resource
def _ensure_browser():
    os.system("playwright install chromium >/dev/null 2>&1")
    return True


def get_secret(key, default=""):
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.environ.get(key, default)


def report_dates(sid):
    """해당 항목의 자동 기록 날짜 목록(최신순)."""
    d = REPORTS / sid
    if not d.exists():
        return []
    return sorted([p.name for p in d.glob("*") if p.is_dir()], reverse=True)


def status_badge(report_text):
    """리포트 본문에서 상태 추출 → (라벨, 이모지, 펼침기본값).
    🔴 변경 큼 / 🟠 변경 감지 / 🟡 변경 가능성 / 🟢 변경 없음."""
    if report_text is None:
        return "기록 없음", "⚪", False
    if "첫 실행" in report_text:
        return "기준 저장", "⚪", False
    # 상태 줄의 이모지 우선순위대로 판정 (🔴·🟠는 자동 펼침)
    for emoji, label, opened in [("🔴", "변경 큼", True), ("🟠", "변경 감지", True),
                                 ("🟡", "변경 가능성", False), ("🟢", "변경 없음", False)]:
        if emoji in report_text:
            return label, emoji, opened
    return "기록 없음", "⚪", False


def do_live_check(site):
    """현재 상태를 마지막 기준과 즉석 비교. 결과 dict 반환."""
    sid_state = STATE / site["_sid"]
    base_png = sid_state / "baseline.png"
    base_txt = sid_state / "baseline.txt"
    if not (base_png.exists() and base_txt.exists()):
        return {"error": "아직 기준이 없습니다. 자동 실행이 한 번 돌아야 비교가 가능합니다."}
    _ensure_browser()
    tmp = Path(tempfile.mkdtemp())
    cur, diff = str(tmp / "cur.png"), str(tmp / "diff.png")
    text = watcher.capture(site["url"], cur,
                           subject=site.get("subject"),
                           section_anchor=site.get("section_anchor"),
                           full_page=site.get("full_page", False),
                           ignore_selectors=site.get("ignore_selectors"),
                           freeze_animations=site.get("freeze_animations", True),
                           region_selector=site.get("region_selector"),
                           click_selector=site.get("click_selector"),
                           stop_swiper=site.get("stop_swiper", False))
    added, removed = watcher.text_diff(base_txt.read_text(encoding="utf-8"), text)
    ratio, _ = watcher.visual_diff(str(base_png), cur, diff)
    return {"report": watcher.build_report(added, removed, ratio),
            "base": str(base_png), "cur": cur, "diff": diff}


def render_images(*pairs):
    """(경로, 캡션) 쌍들을 가로로 표시 (존재하는 것만)."""
    pairs = [(p, c) for p, c in pairs if p and Path(p).exists()]
    if not pairs:
        return
    cols = st.columns(len(pairs))
    for col, (p, c) in zip(cols, pairs):
        col.image(str(p), caption=c, use_container_width=True)


def render_item(sid, info, date):
    """항목 하나: 상태 배지 + 펼침(리포트·이미지·즉석확인)."""
    rep_dir = REPORTS / sid / date if date else None
    md = rep_dir / "report.md" if rep_dir else None
    report_text = md.read_text(encoding="utf-8") if (md and md.exists()) else None
    label, emoji, default_open = status_badge(report_text)

    open_key, res_key = f"open_{sid}", f"live_{sid}"
    expanded = st.session_state.get(open_key, default_open)
    with st.expander(f"{emoji}  {info['name']}  ·  {label}", expanded=expanded):
        if report_text:
            st.markdown(report_text)
        else:
            st.caption("이 날짜의 자동 기록이 없습니다.")
        if rep_dir:
            render_images((rep_dir / "before.png", "이전"),
                          (rep_dir / "current.png", "현재"),
                          (rep_dir / "diff.png", "변경 영역(빨강)"))

        st.divider()
        if st.button("⚡ 지금 바로 확인", key=f"btn_{sid}", use_container_width=True):
            site = dict(info, _sid=sid)
            with st.spinner("사이트 접속 & 비교 중..."):
                st.session_state[res_key] = do_live_check(site)
            st.session_state[open_key] = True
            st.rerun()

        res = st.session_state.get(res_key)
        if res:
            st.markdown("##### ⚡ 즉석 확인 결과 (기록은 저장되지 않음)")
            if res.get("error"):
                st.warning(res["error"])
            else:
                st.markdown(res["report"])
                render_images((res["base"], "기준"), (res["cur"], "현재"),
                              (res["diff"], "변경 영역(빨강)"))


# ─────────────────────────────────────────────────────────────
st.set_page_config(page_title="대성마이맥 모니터", page_icon="🔍", layout="wide")

APP_PASSWORD = get_secret("APP_PASSWORD")
if APP_PASSWORD and not st.session_state.get("authed"):
    st.title("🔒 대성마이맥 모니터")
    pw = st.text_input("접속 비밀번호", type="password")
    if st.button("입장"):
        if pw == APP_PASSWORD:
            st.session_state["authed"] = True
            st.rerun()
        else:
            st.error("비밀번호가 틀렸습니다.")
    st.stop()

st.title("🔍 대성마이맥 모니터")
st.caption("경쟁사 대성마이맥의 과목별 강사 소개·배너·공지 변경을 매일 자동으로 추적합니다.")

if not SITES_FILE.exists():
    st.info("data/sites.json 이 없습니다. GitHub 저장소에 사이트를 등록하세요.")
    st.stop()

sites = json.loads(SITES_FILE.read_text(encoding="utf-8"))
if not sites:
    st.info("등록된 사이트가 없습니다. GitHub 의 data/sites.json 을 편집해 추가하세요.")
    st.stop()

# 과목 목록 (정해진 순서대로, 데이터에 있는 것만)
subjects = [s for s in SUBJECT_ORDER
            if any(v.get("ui_subject") == s for v in sites.values())]

c1, c2 = st.columns([1, 1])
with c1:
    subject = st.selectbox("과목", subjects)
# 선택 과목의 항목들
items = {k: v for k, v in sites.items() if v.get("ui_subject") == subject}
# 날짜(해당 과목 항목들의 기록 합집합)
all_dates = sorted({d for sid in items for d in report_dates(sid)}, reverse=True)
with c2:
    date = st.selectbox("기준 날짜", all_dates) if all_dates else None

if not all_dates:
    st.info("아직 자동 기록이 없습니다. 매일 자동 실행이 한 번 돌면 여기 쌓입니다.")

# 카테고리별 섹션
shown_categories = [c for c in CATEGORY_ORDER
                    if any(v.get("ui_category") == c for v in items.values())]
for cat in shown_categories:
    st.subheader(cat)
    cat_items = {k: v for k, v in items.items() if v.get("ui_category") == cat}
    for sid, info in cat_items.items():
        render_item(sid, info, date)
