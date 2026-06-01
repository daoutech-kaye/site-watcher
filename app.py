"""
대성마이맥 모니터 - 팀 공용 웹 화면 (Streamlit Cloud 배포용). AI 없는 버전.
- 과목(사회/한국사)을 고르면 메인·최신소식·교재패스 배너를 카테고리별로 한 화면에 모아 보여줌
- GitHub Actions 가 매일 기록한 변경 요약/이력을 날짜별로 확인
- 각 항목마다 '지금 바로 확인' 버튼으로 즉석 비교도 가능
"""
import os
import io
import json
import time
import tempfile
import threading
from pathlib import Path
from datetime import date, timedelta

import streamlit as st
import watcher
import qna

ROOT = Path(__file__).parent
SITES_FILE = ROOT / "data" / "sites.json"
TEACHERS_FILE = ROOT / "data" / "teachers.json"
STATE = ROOT / "data" / "state"
REPORTS = ROOT / "data" / "reports"

# 과목/카테고리 표시 순서
ALL_SUBJECTS = ["국어", "수학", "영어", "사회", "과학", "한국사", "대학별"]
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


def render_monitoring():
    """과목별 변경 모니터링 화면."""
    if not SITES_FILE.exists():
        st.info("data/sites.json 이 없습니다. GitHub 저장소에 사이트를 등록하세요.")
        return
    sites = json.loads(SITES_FILE.read_text(encoding="utf-8"))
    if not sites:
        st.info("등록된 사이트가 없습니다. GitHub 의 data/sites.json 을 편집해 추가하세요.")
        return

    items = {k: v for k, v in sites.items() if v.get("ui_subject") == "사회"}  # 기본
    c1, c2 = st.columns([1, 1])
    with c1:
        subject = st.selectbox("과목", ALL_SUBJECTS,
                               index=ALL_SUBJECTS.index("사회"), key="mon_subject")
    items = {k: v for k, v in sites.items() if v.get("ui_subject") == subject}
    if not items:
        st.info(f"'{subject}' 과목은 아직 모니터링 항목이 준비 중입니다. (현재 사회·한국사 운영 중)")
        return
    all_dates = sorted({d for sid in items for d in report_dates(sid)}, reverse=True)
    with c2:
        sel_date = st.selectbox("기준 날짜", all_dates) if all_dates else None

    if not all_dates:
        st.info("아직 자동 기록이 없습니다. 매일 자동 실행이 한 번 돌면 여기 쌓입니다.")

    shown = [c for c in CATEGORY_ORDER
             if any(v.get("ui_category") == c for v in items.values())]
    for cat in shown:
        st.subheader(cat)
        for sid, info in {k: v for k, v in items.items() if v.get("ui_category") == cat}.items():
            render_item(sid, info, sel_date)


def _run_qna_job(job, selected, start, end):
    """백그라운드 스레드에서 강사별 집계. job(dict)를 제자리 갱신한다(st.* 호출 금지)."""
    for i, (subj, t) in enumerate(selected):
        job["current"] = t["name"]
        try:
            cnt = qna.count_posts(t["tcd"], start, end)
        except Exception as e:  # noqa: BLE001
            cnt = None
            job["errors"].append(f"{t['name']}: {e}")
        job["rows"].append({"과목": subj, "상세 과목": t.get("detail", ""),
                            "선생님": t["name"], "게시글 수": cnt})
        job["done"] = i + 1
    job["current"] = ""
    job["status"] = "done"


def render_qna():
    """학습 Q&A 게시글 수 집계 화면."""
    if not TEACHERS_FILE.exists():
        st.info("data/teachers.json 이 없습니다.")
        return
    teachers = json.loads(TEACHERS_FILE.read_text(encoding="utf-8"))
    flat = [(subj, t) for subj, lst in teachers.items() for t in lst]

    st.caption("기간과 선생님을 고르고 집계하면, 강사별 학습 Q&A 게시글 수를 세어 표로 보여줍니다.")

    # 상태 기본값 초기화 (기간: 최근 1주일 / 선생님: 전체 선택)
    if "qna_start" not in st.session_state:
        st.session_state["qna_start"] = date.today() - timedelta(days=7)
        st.session_state["qna_end"] = date.today()
        st.session_state["chk_all"] = True
        for _, t in flat:
            st.session_state[f"chk_{t['tcd']}"] = True

    def _toggle_all():
        for _, t in flat:
            st.session_state[f"chk_{t['tcd']}"] = st.session_state["chk_all"]

    settings, _spacer = st.columns([2, 1])
    with settings:
        # ── 기간 ──
        with st.container(border=True):
            st.markdown("**기간**")
            PRESETS = [("오늘", 0), ("1주일", 7), ("1개월", 30), ("3개월", 90)]
            for col, (label, days) in zip(st.columns(len(PRESETS)), PRESETS):
                if col.button(label, use_container_width=True):
                    st.session_state["qna_start"] = date.today() - timedelta(days=days)
                    st.session_state["qna_end"] = date.today()
            d1, d2 = st.columns(2)
            start = d1.date_input("시작일", key="qna_start")
            end = d2.date_input("종료일", key="qna_end")

        # ── 집계할 선생님 (아코디언, 과목별 왼쪽 정렬) ──
        chosen = sum(1 for _, t in flat if st.session_state.get(f"chk_{t['tcd']}", True))
        with st.expander(f"집계할 선생님  ({chosen}/{len(flat)}명 선택)", expanded=False):
            st.checkbox("전체", key="chk_all", on_change=_toggle_all)
            st.divider()
            selected = []
            for subj, lst in teachers.items():
                st.caption(subj)
                for t in lst:
                    label = f"{t['name']} · {t['detail']}" if t.get("detail") else t["name"]
                    if st.checkbox(label, key=f"chk_{t['tcd']}"):
                        selected.append((subj, t))

        job = st.session_state.get("qna_job")
        running = bool(job and job["status"] == "running")
        run = st.button("📊 집계 시작", type="primary", use_container_width=True,
                        disabled=not selected or running)

    if start > end:
        st.error("시작일이 종료일보다 늦습니다.")
        return

    # 집계 시작 → 백그라운드 스레드 (다른 메뉴로 가도 계속 진행)
    if run and selected:
        job = {"status": "running", "total": len(selected), "done": 0,
               "current": "", "rows": [], "errors": [],
               "range": (str(start), str(end))}
        st.session_state["qna_job"] = job
        threading.Thread(target=_run_qna_job,
                         args=(job, list(selected), start, end), daemon=True).start()

    job = st.session_state.get("qna_job")
    if not job:
        if not selected:
            st.info("집계할 선생님을 한 명 이상 선택하세요.")
        return

    rng = job["range"]
    if job["status"] == "running":
        st.markdown(f"#### ⏳ 집계 중  ·  {rng[0]} ~ {rng[1]}")
        cur = f" · {job['current']} 집계 중" if job["current"] else ""
        st.progress(job["done"] / max(job["total"], 1),
                    text=f"{job['done']}/{job['total']} 완료{cur}")
        st.caption("백그라운드에서 진행 중입니다. 다른 메뉴로 이동해도 계속 집계됩니다.")
        time.sleep(2)
        st.rerun()
        return

    # 완료
    st.markdown(f"#### 집계 결과  ·  {rng[0]} ~ {rng[1]}")
    for e in job.get("errors", []):
        st.warning(f"집계 실패 - {e}")
    rows = job["rows"]
    if not rows:
        return

    import pandas as pd
    df = pd.DataFrame(rows)
    valid = df[df["게시글 수"].notna()].copy()

    # 과목별 합계 지표 (천단위 콤마)
    by_subj = valid.groupby("과목")["게시글 수"].sum()
    metric_cols = st.columns(len(by_subj) + 1)
    metric_cols[0].metric("전체 합계", f"{int(valid['게시글 수'].sum()):,}")
    for col, (subj, total) in zip(metric_cols[1:], by_subj.items()):
        col.metric(f"{subj} 합계", f"{int(total):,}")

    # 표 (게시글 수 천단위 콤마, 상세 과목 포함)
    disp = df.copy()
    disp["게시글 수"] = disp["게시글 수"].map(
        lambda v: f"{int(v):,}" if pd.notna(v) else "집계 실패")
    st.dataframe(disp, use_container_width=True, hide_index=True)

    # 막대차트 (동명이인 방지용 표시명)
    chart = valid.copy()
    chart["표시명"] = chart["선생님"] + "(" + chart["상세 과목"] + ")"
    st.bar_chart(chart, x="표시명", y="게시글 수", color="과목")

    # 엑셀 다운로드
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, index=False, sheet_name="강사별")
        by_subj.rename("게시글 수").to_frame().to_excel(w, sheet_name="과목별 합계")
    st.download_button("⬇️ 엑셀 다운로드", buf.getvalue(),
                       file_name=f"게시글집계_{rng[0]}_{rng[1]}.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


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

mode = st.radio("메뉴", ["🖥️ 변경 모니터링", "📊 게시글 집계"],
                horizontal=True, label_visibility="collapsed")
st.divider()
if mode.startswith("🖥️"):
    render_monitoring()
else:
    render_qna()
