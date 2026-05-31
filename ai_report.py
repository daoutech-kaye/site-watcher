"""변경 내용을 Claude(Anthropic API)로 한국어 보고서화. (경쟁사 모니터링용)"""
import io
import base64
from PIL import Image
import anthropic


def _img_b64(path: str, max_w: int = 900) -> str:
    img = Image.open(path).convert("RGB")
    if img.width > max_w:
        img = img.resize((max_w, int(img.height * max_w / img.width)))
    if img.height > 2600:
        img = img.crop((0, 0, img.width, 2600))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=72)
    return base64.b64encode(buf.getvalue()).decode()


def generate_report(api_key, url, added, removed, ratio,
                    old_png, new_png, model="claude-sonnet-4-6", focus=None):
    client = anthropic.Anthropic(api_key=api_key)
    text_block = (
        "추가된 내용:\n" + ("\n".join(f"- {a}" for a in added) if added else "(없음)")
        + "\n\n사라진 내용:\n" + ("\n".join(f"- {r}" for r in removed) if removed else "(없음)")
    )
    focus_line = f"\n[중점 확인사항] {focus}\n" if focus else ""

    prompt = f"""당신은 경쟁사 웹사이트 모니터링 보조원입니다.
'{url}' 페이지를 이전 기준일과 오늘 비교한 결과입니다. 첨부된 두 스크린샷(이전/현재)도 직접 비교해 참고하세요.
{focus_line}
[텍스트 변경]
{text_block}

[화면 변화량] 전체 중 약 {ratio*100:.1f}% 픽셀이 달라졌습니다.

특히 다음을 놓치지 말고 확인하세요:
- 강사 추가 / 삭제 (목록에서 새로 생기거나 빠진 사람)
- 강사 소개 문구·홍보 카피 변경
- 강사 사진 교체 (화면 변화량과 첨부 이미지로 판단)
- 공지/최신소식 글 추가·변경 ([공지][EVENT][OPEN] 등)
- 하단 교재패스 등 프로모션 배너의 문구·디자인 변경
- NEW 같은 배지 변경

아래 형식의 한국어 보고서를 작성하세요. 비개발자 담당자가 그대로 보고에 쓸 수 있게 간결·명확하게.

## 한 줄 요약
(변경 있음/없음 + 핵심 한 문장)

## 주요 변경사항
(의미 있는 변경만 중요도 순 불릿. 없으면 "특이 변경 없음")

## 확인 필요 / 제안
(경쟁 대응 관점에서 신경 쓸 부분. 없으면 생략)

자동으로 돌아가는 메인 슬라이드(배너 캐러셀), 시계/날짜, 조회수처럼 매일 저절로 바뀌는 것은 변경으로 취급하지 마세요."""

    content = [{"type": "text", "text": prompt}]
    for label, path in [("이전", old_png), ("현재", new_png)]:
        content.append({"type": "text", "text": f"--- {label} 스크린샷 ---"})
        content.append({"type": "image", "source": {
            "type": "base64", "media_type": "image/jpeg", "data": _img_b64(path)}})

    msg = client.messages.create(model=model, max_tokens=1600,
                                 messages=[{"role": "user", "content": content}])
    return "".join(b.text for b in msg.content if b.type == "text")
