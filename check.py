"""
매일 자동 실행되는 엔진 (GitHub Actions 가 호출). AI 없는 버전.
- sites.json 의 모든 사이트(과목)를 확인
- 기준(baseline)과 비교 → 변경 요약 + 스크린샷 저장
- 변경이 있으면 알림(Slack/Discord 웹훅) 전송
"""
import os
import json
import shutil
from pathlib import Path
from datetime import datetime, timezone, timedelta
import urllib.request

import watcher

ROOT = Path(__file__).parent
SITES_FILE = ROOT / "data" / "sites.json"
STATE = ROOT / "data" / "state"
REPORTS = ROOT / "data" / "reports"
KST = timezone(timedelta(hours=9))


def today():
    return datetime.now(KST).strftime("%Y-%m-%d")


def send_alert(webhook, site_name, summary, app_url):
    if not webhook:
        return
    text = f"🔔 [{site_name}] 변경 감지\n{summary}"
    if app_url:
        text += f"\n👉 자세히 보기: {app_url}"
    payload = {"content": text} if "discord" in webhook else {"text": text}
    req = urllib.request.Request(webhook, data=json.dumps(payload).encode(),
                                headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=15)
    except Exception as e:
        print(f"[alert 실패] {e}")


def run_site(sid, info, webhook, app_url):
    name, url = info["name"], info["url"]
    print(f"== {name} ({url})")
    st_dir = STATE / sid
    st_dir.mkdir(parents=True, exist_ok=True)
    rep_dir = REPORTS / sid / today()
    rep_dir.mkdir(parents=True, exist_ok=True)

    cur_png = str(rep_dir / "current.png")
    text = watcher.capture(url, cur_png,
                           subject=info.get("subject"),
                           section_anchor=info.get("section_anchor"),
                           full_page=info.get("full_page", False),
                           ignore_selectors=info.get("ignore_selectors"),
                           freeze_animations=info.get("freeze_animations", True))

    base_png = st_dir / "baseline.png"
    base_txt = st_dir / "baseline.txt"

    if not (base_png.exists() and base_txt.exists()):
        shutil.copy(cur_png, base_png)
        base_txt.write_text(text, encoding="utf-8")
        (rep_dir / "report.md").write_text(
            f"# {name} · {today()}\n\n첫 실행으로 기준을 저장했습니다. 내일부터 변경을 비교합니다.\n",
            encoding="utf-8")
        print("  기준 저장 (최초)")
        return

    old_text = base_txt.read_text(encoding="utf-8")
    added, removed = watcher.text_diff(old_text, text)
    ratio, _ = watcher.visual_diff(str(base_png), cur_png, str(rep_dir / "diff.png"))
    changed = watcher.is_changed(added, removed, ratio)

    report = watcher.build_report(added, removed, ratio)
    shutil.copy(base_png, rep_dir / "before.png")
    (rep_dir / "report.md").write_text(f"# {name} · {today()}\n\n{report}\n", encoding="utf-8")

    # 기준 갱신
    shutil.copy(cur_png, base_png)
    base_txt.write_text(text, encoding="utf-8")

    print(f"  변경여부: {changed} (화면 {ratio*100:.1f}%)")
    if changed:
        summary = f"추가 {len(added)}건, 삭제 {len(removed)}건, 화면 {ratio*100:.1f}% 변경"
        send_alert(webhook, name, summary, app_url)


def main():
    webhook = os.environ.get("ALERT_WEBHOOK", "")
    app_url = os.environ.get("APP_URL", "")
    sites = json.loads(SITES_FILE.read_text(encoding="utf-8"))
    if not sites:
        print("등록된 사이트가 없습니다 (data/sites.json).")
        return
    for sid, info in sites.items():
        try:
            run_site(sid, info, webhook, app_url)
        except Exception as e:
            print(f"  [오류] {info.get('name', sid)}: {e}")


if __name__ == "__main__":
    main()
