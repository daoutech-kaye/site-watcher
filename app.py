"""
사이트 변경 모니터 - 팀 공용 웹 화면 (Streamlit Cloud 배포용). AI 없는 버전.
- GitHub Actions 가 매일 기록한 변경 요약/이력을 보여줌
- '지금 바로 확인' 버튼으로 즉석 확인도 가능
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


st.set_page_config(page_title="사이트 변경 모니터", page_icon="🔍", layout="wide")

APP_PASSWORD = get_secret("APP_PASSWORD")
if APP_PASSWORD:
    if not st.session_state.get("authed"):
        st.title("🔒 사이트 변경 모니터")
        pw = st.text_input("접속 비밀번호", type="password")
        if st.button("입장"):
            if pw == APP_PASSWORD:
                st.session_state["authed"] = True
                st.rerun()
            else:
                st.error("비밀번호가 틀렸습니다.")
        st.stop()

st.title("🔍 사이트 변경 모니터")
st.caption("매일 자동으로 사이트를 확인하고 변경 내용을 정리해 줍니다.")

if not SITES_FILE.exists():
    st.info("data/sites.json 이 없습니다. GitHub 저장소에 사이트를 등록하세요.")
    st.stop()

sites = json.loads(SITES_FILE.read_text(encoding="utf-8"))
if not sites:
    st.info("등록된 사이트가 없습니다. GitHub 의 data/sites.json 을 편집해 추가하세요.")
    st.stop()

sid = st.selectbox("사이트(과목)", list(sites.keys()),
                   format_func=lambda s: f"{sites[s]['name']}  ·  {sites[s]['url']}")
site = sites[sid]

tab_history, tab_live = st.tabs(["📚 자동 기록 보기", "⚡ 지금 바로 확인"])

with tab_history:
    rep_root = REPORTS / sid
    dates = sorted([p.name for p in rep_root.glob("*") if p.is_dir()], reverse=True) if rep_root.exists() else []
    if not dates:
        st.info("아직 자동 기록이 없습니다. 매일 자동 실행이 한 번 돌면 여기 쌓입니다.")
    else:
        day = st.selectbox("날짜", dates)
        rep_dir = rep_root / day
        md = rep_dir / "report.md"
        if md.exists():
            st.markdown(md.read_text(encoding="utf-8"))
        cols = st.columns(3)
        for col, fn, cap in [(cols[0], "before.png", "이전"),
                             (cols[1], "current.png", "현재"),
                             (cols[2], "diff.png", "변경 영역(빨강)")]:
            f = rep_dir / fn
            if f.exists():
                col.image(str(f), caption=cap, use_container_width=True)

with tab_live:
    st.write("현재 사이트 상태를 마지막 기준과 즉석 비교합니다. (기록은 저장되지 않음)")
    if st.button("⚡ 지금 바로 확인", type="primary", use_container_width=True):
        base_png = STATE / sid / "baseline.png"
        base_txt = STATE / sid / "baseline.txt"
        if not (base_png.exists() and base_txt.exists()):
            st.warning("아직 기준이 없습니다. 자동 실행이 한 번 돌아야 비교가 가능합니다.")
            st.stop()
        try:
            _ensure_browser()
            tmp = Path(tempfile.mkdtemp())
            with st.spinner("사이트 접속 & 캡처 중..."):
                text = watcher.capture(site["url"], str(tmp / "cur.png"),
                                       subject=site.get("subject"),
                                       section_anchor=site.get("section_anchor"),
                                       full_page=site.get("full_page", False),
                                       ignore_selectors=site.get("ignore_selectors"),
                                       freeze_animations=site.get("freeze_animations", True))
            with st.spinner("변경 분석 중..."):
                added, removed = watcher.text_diff(base_txt.read_text(encoding="utf-8"), text)
                ratio, _ = watcher.visual_diff(str(base_png), str(tmp / "cur.png"), str(tmp / "diff.png"))
            st.markdown(watcher.build_report(added, removed, ratio))
            c1, c2, c3 = st.columns(3)
            c1.image(str(base_png), caption="기준", use_container_width=True)
            c2.image(str(tmp / "cur.png"), caption="현재", use_container_width=True)
            c3.image(str(tmp / "diff.png"), caption="변경 영역(빨강)", use_container_width=True)
        except Exception as e:
            st.error(f"오류: {e}")
