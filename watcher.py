"""
사이트 캡처 + 변경 비교 (순수 로직, UI/엔진 공용)
- 과목 탭 클릭 후, 지정한 영역(예: '마이맥 선생님')만 집중 캡처
"""
import re
import difflib
from PIL import Image, ImageChops


def _click_subject(page, subject, anchor):
    """과목 탭(예: '사회')을 글자 기준으로 클릭. 성공하면 True."""
    candidates = []
    if anchor:
        try:
            a = page.get_by_text(anchor, exact=False).first
            cont = a.locator("xpath=ancestor::*[self::div or self::section][2]")
            candidates.append(cont.get_by_text(subject, exact=True))
        except Exception:
            pass
    candidates.append(page.get_by_text(subject, exact=True))
    for loc in candidates:
        try:
            n = loc.count()
            if n == 0:
                continue
            target = loc.last if n > 1 else loc.first  # 강사 영역 탭이 보통 더 아래
            target.scroll_into_view_if_needed(timeout=4000)
            target.click(timeout=4000)
            return True
        except Exception:
            continue
    return False


def _find_region(page, anchor):
    """'마이맥 선생님' 같은 앵커 텍스트를 포함하는, 카드까지 담을 만한 컨테이너 반환."""
    try:
        a = page.get_by_text(anchor, exact=False).first
        if a.count() == 0:
            return None
        for up in [3, 4, 2, 5]:
            cont = a.locator(f"xpath=ancestor::*[self::div or self::section][{up}]")
            try:
                box = cont.bounding_box()
                if box and box["height"] > 200 and box["width"] > 300:
                    return cont
            except Exception:
                continue
    except Exception:
        return None
    return None


def capture(url, out_png, subject=None, section_anchor=None, full_page=False, timeout=45000):
    """URL 접속 → (과목 클릭) → (영역) 스크린샷 저장, 텍스트 반환."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1366, "height": 900})
        try:
            page.goto(url, wait_until="networkidle", timeout=timeout)
        except Exception:
            page.goto(url, wait_until="load", timeout=timeout)
        page.wait_for_timeout(2000)

        if subject:
            if _click_subject(page, subject, section_anchor):
                page.wait_for_timeout(1500)
            else:
                print(f"  [안내] 과목 '{subject}' 탭을 못 찾아 기본 화면을 캡처합니다.")

        region = _find_region(page, section_anchor) if section_anchor else None
        text = None
        if region is not None:
            try:
                region.scroll_into_view_if_needed(timeout=4000)
                region.screenshot(path=out_png)
                text = region.inner_text()
            except Exception:
                region = None
        if region is None:
            page.screenshot(path=out_png, full_page=full_page)
            try:
                text = page.inner_text("body")
            except Exception:
                text = page.content()
            if section_anchor:
                print(f"  [안내] '{section_anchor}' 영역을 못 찾아 전체 화면을 캡처합니다.")

        browser.close()
    return text


def _clean_lines(text: str):
    out = []
    for raw in text.splitlines():
        s = raw.strip()
        if not s:
            continue
        s = re.sub(r"\d{1,2}:\d{2}(:\d{2})?", "<시각>", s)
        out.append(s)
    return out


def text_diff(old_text: str, new_text: str):
    diff = list(difflib.unified_diff(
        _clean_lines(old_text), _clean_lines(new_text), lineterm="", n=0))
    added, removed = [], []
    for line in diff:
        if line.startswith("+") and not line.startswith("+++"):
            added.append(line[1:].strip())
        elif line.startswith("-") and not line.startswith("---"):
            removed.append(line[1:].strip())
    return [a for a in added if a], [r for r in removed if r]


def visual_diff(old_png: str, new_png: str, out_png: str, threshold: int = 30):
    a = Image.open(old_png).convert("RGB")
    b = Image.open(new_png).convert("RGB")
    W, H = max(a.width, b.width), max(a.height, b.height)
    A = Image.new("RGB", (W, H), (255, 255, 255)); A.paste(a, (0, 0))
    B = Image.new("RGB", (W, H), (255, 255, 255)); B.paste(b, (0, 0))
    mask = ImageChops.difference(A, B).convert("L").point(lambda x: 255 if x > threshold else 0)
    hist = mask.histogram()
    ratio = (hist[255] if len(hist) > 255 else 0) / float(W * H)
    red = Image.new("RGB", (W, H), (255, 0, 0))
    blended = Image.blend(B, Image.composite(red, B, mask), 0.55)
    blended.save(out_png)
    return ratio, out_png


def is_changed(added, removed, ratio, visual_thresh=0.004) -> bool:
    return bool(added) or bool(removed) or ratio > visual_thresh
