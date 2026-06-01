"""
사이트 캡처 + 변경 비교 (순수 로직, UI/엔진 공용)
- (선택) 과목 탭/메뉴 클릭 → Swiper 자동재생 정지 → 애니메이션 정지 → 지정 영역만 캡처
- region_selector(CSS)로 정확한 영역을 잡고, 없으면 글자(section_anchor) 기준으로 fallback
"""
import re
import difflib
from PIL import Image, ImageChops, ImageFilter


def _stop_swipers(page):
    """페이지의 모든 Swiper 캐러셀 자동재생을 멈춘다(JS 기반이라 CSS로는 안 멈춤)."""
    try:
        page.evaluate("""() => {
            document.querySelectorAll('.swiper, [class*="swiper"]').forEach(el => {
                const sw = el.swiper;
                if (sw && sw.autoplay && sw.autoplay.stop) {
                    try { sw.autoplay.stop(); } catch (e) {}
                }
            });
        }""")
    except Exception:
        pass


def _click_selector(page, selector):
    """명시적 CSS 선택자로 탭/메뉴를 클릭. 성공하면 True."""
    try:
        loc = page.locator(selector).first
        if loc.count() == 0:
            return False
        loc.scroll_into_view_if_needed(timeout=4000)
        loc.click(timeout=4000)
        return True
    except Exception:
        return False


def _click_subject(page, subject, anchor):
    """과목/슬라이드 탭(예: '사회')을 글자 기준으로 클릭. 성공하면 True."""
    candidates = []
    if anchor:
        try:
            a = page.get_by_text(anchor, exact=False).first
            cont = a.locator("xpath=ancestor::*[self::div or self::section][3]")
            candidates.append(cont.get_by_text(subject, exact=True))
        except Exception:
            pass
    candidates.append(page.get_by_text(subject, exact=True))
    for loc in candidates:
        try:
            n = loc.count()
            if n == 0:
                continue
            target = loc.last if n > 1 else loc.first
            target.scroll_into_view_if_needed(timeout=4000)
            target.click(timeout=4000)
            return True
        except Exception:
            continue
    return False


def _wait_for_images(page, timeout=6000):
    """화면에 보이는 이미지가 모두 로드될 때까지 대기(지연 로딩으로 인한 오탐 방지)."""
    try:
        page.evaluate("""() => Promise.all(
            [...document.images]
                .filter(img => img.getBoundingClientRect().width > 0 && !img.complete)
                .map(img => new Promise(res => { img.onload = img.onerror = res; }))
        )""", timeout=timeout)
    except Exception:
        pass
    page.wait_for_timeout(500)


def _neutralize(page, ignore_selectors, freeze):
    """애니메이션 정지 + 지정 요소 가리기(자동 슬라이드 노이즈 제거). 캡처 직전 호출."""
    parts = []
    if freeze:
        parts.append("*,*::before,*::after{animation:none!important;"
                     "animation-play-state:paused!important;transition:none!important;}")
    if ignore_selectors:
        sel = ",".join(ignore_selectors)
        parts.append(f"{sel}{{visibility:hidden!important;}}")
    if parts:
        try:
            page.add_style_tag(content="".join(parts))
            page.wait_for_timeout(400)
        except Exception:
            pass


def _find_region_by_selector(page, selector):
    """명시적 CSS 선택자로 캡처할 영역(locator) 반환. 못 찾으면 None."""
    try:
        loc = page.locator(selector).first
        if loc.count() == 0:
            return None
        box = loc.bounding_box()
        if box and box["height"] > 10 and box["width"] > 10:
            return loc
    except Exception:
        return None
    return None


def _find_region(page, anchor):
    """앵커 텍스트를 포함하는, 내용까지 담을 만한 컨테이너 반환."""
    try:
        a = page.get_by_text(anchor, exact=False).first
        if a.count() == 0:
            return None
        for up in [3, 4, 2, 5]:
            cont = a.locator(f"xpath=ancestor::*[self::div or self::section][{up}]")
            try:
                box = cont.bounding_box()
                if box and box["height"] > 150 and box["width"] > 250:
                    return cont
            except Exception:
                continue
    except Exception:
        return None
    return None


def capture(url, out_png, subject=None, section_anchor=None, full_page=False,
            ignore_selectors=None, freeze_animations=True, timeout=45000,
            region_selector=None, click_selector=None, stop_swiper=False):
    """URL 접속 → (탭/메뉴 클릭) → (Swiper·애니메이션 정지) → (영역) 캡처, 텍스트 반환.

    region_selector / click_selector(CSS)가 있으면 그것을 우선 사용하고,
    없으면 기존 글자(subject / section_anchor) 기준 방식으로 fallback 한다.
    """
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1366, "height": 900})
        try:
            page.goto(url, wait_until="networkidle", timeout=timeout)
        except Exception:
            page.goto(url, wait_until="load", timeout=timeout)
        page.wait_for_timeout(2000)

        # 캐러셀 자동재생 먼저 정지 (클릭한 슬라이드가 다시 넘어가지 않도록)
        if stop_swiper:
            _stop_swipers(page)

        # 과목/슬라이드 탭 클릭: CSS 선택자 우선, 없으면 글자 기준
        if click_selector:
            if _click_selector(page, click_selector):
                page.wait_for_timeout(1500)
                if stop_swiper:
                    _stop_swipers(page)  # 클릭으로 재개됐을 수 있어 한 번 더 정지
            else:
                print(f"  [안내] 선택자 '{click_selector}' 를 못 찾아 기본 상태로 캡처합니다.")
        elif subject:
            if _click_subject(page, subject, section_anchor):
                page.wait_for_timeout(1500)  # 슬라이드가 자리 잡을 시간
            else:
                print(f"  [안내] 과목 '{subject}' 탭을 못 찾아 기본 상태로 캡처합니다.")

        _neutralize(page, ignore_selectors, freeze_animations)

        # 캡처 영역: CSS 선택자 우선, 없으면 글자 앵커 기준
        region = None
        if region_selector:
            region = _find_region_by_selector(page, region_selector)
            if region is None:
                print(f"  [안내] 선택자 '{region_selector}' 영역을 못 찾아 다른 방식으로 시도합니다.")
        if region is None and section_anchor:
            region = _find_region(page, section_anchor)

        text = None
        if region is not None:
            try:
                region.scroll_into_view_if_needed(timeout=4000)
                _wait_for_images(page)  # 지연 로딩 이미지가 다 뜬 뒤 캡처
                region.screenshot(path=out_png)
                text = region.inner_text()
            except Exception:
                region = None
        if region is None:
            _wait_for_images(page)
            page.screenshot(path=out_png, full_page=full_page)
            try:
                text = page.inner_text("body")
            except Exception:
                text = page.content()
            if region_selector or section_anchor:
                print("  [안내] 지정 영역을 못 찾아 전체 화면을 캡처합니다.")

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
    # 잡음 제거: 흩어진 1~2px 차이(안티앨리어싱·렌더링·로딩 잔여)는 erosion으로 걸러냄.
    # 진짜 변경(이미지 교체 등 큰 덩어리)은 살아남고, 고립된 잡음만 0이 된다.
    denoised = mask.filter(ImageFilter.MinFilter(3))
    hist = denoised.histogram()
    ratio = (hist[255] if len(hist) > 255 else 0) / float(W * H)
    # 빨강 강조는 잡음 제거된 마스크 기준(실제 변경만 표시)
    red = Image.new("RGB", (W, H), (255, 0, 0))
    blended = Image.blend(B, Image.composite(red, B, denoised), 0.55)
    blended.save(out_png)
    return ratio, out_png


def is_changed(added, removed, ratio, visual_thresh=0.01) -> bool:
    return bool(added) or bool(removed) or ratio > visual_thresh


def build_report(added, removed, ratio):
    """AI 없이 만드는 변경 요약 (마크다운)."""
    changed = is_changed(added, removed, ratio)
    lines = [f"**상태:** {'🔴 변경 감지됨' if changed else '🟢 변경 없음'}",
             f"**화면 변화량:** {ratio*100:.1f}%", ""]
    if added:
        lines.append("### ➕ 새로 나타난 내용")
        lines += [f"- {a}" for a in added]
        lines.append("")
    if removed:
        lines.append("### ➖ 사라진 내용")
        lines += [f"- {r}" for r in removed]
        lines.append("")
    if changed and not added and not removed:
        lines.append(f"⚠️ 글자 변화는 없는데 화면이 {ratio*100:.1f}% 바뀌었습니다. "
                     "사진/이미지 교체 가능성이 있어요. 아래 '변경 영역(빨강)' 이미지를 확인하세요.")
    elif not changed:
        lines.append("특이 변경 없음.")
    return "\n".join(lines)
