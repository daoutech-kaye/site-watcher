"""
대성마이맥 학습 Q&A 게시판 글 수 집계 (HTTP 크롤링, 브라우저/로그인 불필요).

- POST /tcher/studyQna/getStudyQnaProcess.ds (tcd, currPage) → HTML 조각(EUC-KR)
- 페이지당 15건, 최신순. 실제 질문글만 .date 를 가짐(상단 공지/정오표는 날짜 없음 → 제외)
- 인기 강사는 수만 건이라 전 페이지 순회는 불가 → 날짜 '이분탐색'으로 빠르게 계산:
    기간 내 글 수 = n_ge(시작일) - n_ge(종료일 다음날)
  (n_ge(X) = 작성일 ≥ X 인 글 수. 글이 최신순이라 X 미만이 처음 나오는 '경계 페이지'만 찾으면 됨)
"""
import re
from datetime import date, timedelta

import requests

ENDPOINT = "https://www.mimacstudy.com/tcher/studyQna/getStudyQnaProcess.ds"
LIST_PAGE = "https://www.mimacstudy.com/tcher/studyQna/getStudyQnaList.ds?tcd={tcd}"
PER_PAGE = 15

_POST_RE = re.compile(r"qnaDetail\('(\d+)'\)(.*?)(?=qnaDetail\('|\Z)", re.S)
_DATE_RE = re.compile(r'class="date">\s*(20\d\d)[./](\d\d)[./](\d\d)')


def _parse_posts(html):
    """(글ID, 작성일) 목록. 날짜 없는 항목(공지/정오표)은 제외. 최신순 유지."""
    posts = []
    for m in _POST_RE.finditer(html):
        d = _DATE_RE.search(m.group(2))
        if d:
            posts.append((m.group(1), date(int(d.group(1)), int(d.group(2)), int(d.group(3)))))
    return posts


class Board:
    """한 강사(tcd)의 Q&A 게시판. 연결을 재사용하고 페이지를 캐시한다."""

    def __init__(self, tcd):
        self.tcd = str(tcd)
        self.cache = {}
        self._verify = True
        self.s = requests.Session()
        self.s.headers.update({
            "User-Agent": "Mozilla/5.0",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": LIST_PAGE.format(tcd=self.tcd),
        })

    def _post(self, page):
        data = {"tcd": self.tcd, "tcdTabType": "tcdHome", "myQna": "N",
                "currPage": str(page), "isScrtN": "N"}
        try:
            r = self.s.post(ENDPOINT, data=data, timeout=20, verify=self._verify)
        except requests.exceptions.SSLError:
            # 회사 프록시(자체서명 인증서) 환경 폴백 (배포 환경에선 정상 검증됨)
            self._verify = False
            try:
                requests.packages.urllib3.disable_warnings()
            except Exception:
                pass
            r = self.s.post(ENDPOINT, data=data, timeout=20, verify=False)
        r.encoding = "euc-kr"
        return r.text

    def page(self, p):
        """p페이지의 (글ID, 작성일) 목록 (캐시)."""
        if p not in self.cache:
            self.cache[p] = _parse_posts(self._post(p))
        return self.cache[p]

    def n_ge(self, x):
        """작성일 ≥ x 인 질문글 수. (글이 최신순이라 경계 페이지만 찾으면 됨)"""
        def below(p):  # 이 페이지가 비었거나, 가장 오래된 글이 x 미만이면 경계 이상
            posts = self.page(p)
            return (not posts) or posts[-1][1] < x

        # 1) 지수 탐색으로 경계를 포함하는 상한 페이지 hi 확보
        hi = 1
        while not below(hi):
            hi *= 2
            if hi > 1 << 20:  # 안전장치
                break
        lo = hi // 2 if hi > 1 else 1  # below(lo)는 False (경계 이전)
        # 2) below(p) 가 처음 True 가 되는 페이지 b 를 이분탐색
        while lo < hi:
            mid = (lo + hi) // 2
            if below(mid):
                hi = mid
            else:
                lo = mid + 1
        b = lo
        # 3) 경계 페이지 b 앞쪽(1..b-1)은 모두 x 이상. b 페이지 내 x 이상만 추가
        bp = self.page(b)
        if bp:  # b가 걸치는 페이지
            return PER_PAGE * (b - 1) + sum(1 for _, d in bp if d >= x)
        # b가 빈 페이지(= x 가 가장 오래된 글보다 과거) → b-1이 마지막 실제 페이지(부분일 수 있음)
        if b <= 1:
            return 0
        return PER_PAGE * (b - 2) + len(self.page(b - 1))

    def count(self, start, end):
        """[start, end](양끝 포함) 기간의 질문글 수."""
        return self.n_ge(start) - self.n_ge(end + timedelta(days=1))


def count_posts(tcd, start, end):
    """tcd 강사의 [start, end] 기간 질문글 수. start/end 는 datetime.date."""
    return Board(tcd).count(start, end)
