from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import requests
import xml.etree.ElementTree as ET
import re
from collections import Counter, defaultdict

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CATEGORY_FEEDS = {
    "전체": "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko",
    "정치": "https://news.google.com/rss/headlines/section/topic/POLITICS?hl=ko&gl=KR&ceid=KR:ko",
    "경제": "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=ko&gl=KR&ceid=KR:ko",
    "스포츠": "https://news.google.com/rss/headlines/section/topic/SPORTS?hl=ko&gl=KR&ceid=KR:ko",
    "연예": "https://news.google.com/rss/search?q=연예 OR 배우 OR 가수 OR 드라마 OR 영화 OR 아이돌 when:1d&hl=ko&gl=KR&ceid=KR:ko",
    "게임": "https://news.google.com/rss/search?q=게임 OR 모바일게임 OR 닌텐도 OR 스팀 OR 플레이스테이션 when:1d&hl=ko&gl=KR&ceid=KR:ko",
}

STOPWORDS = {
    "뉴스", "속보", "단독", "영상", "사진", "기자", "앵커",
    "오늘", "오후", "오전", "관련", "대한", "통해", "위해",
    "정부", "한국", "미국", "중국", "일본", "국내", "해외",
    "사람", "경우", "상황", "결과", "현장", "논란", "이슈",
    "발표", "공개", "확인", "진행", "예정", "최신", "종합",
    "조선일보", "연합뉴스", "뉴시스", "중앙일보", "동아일보",
    "한겨레", "경향신문", "한국경제", "매일경제", "서울신문",
    "머니투데이", "이데일리", "아시아경제", "노컷뉴스",
    "문화일보", "한경", "연합", "뉴스1", "KBS", "MBC", "SBS",
    "JTBC", "채널A", "MBN", "YTN", "TV조선", "세계일보",
    "헤럴드경제", "파이낸셜뉴스", "전자신문", "스포츠조선",
    "스포츠서울", "스포티비", "OSEN", "텐아시아", "스타뉴스",
}

BANNED_KEYWORDS = {
    "결국", "만에", "가운데", "논란", "관련", "속보", "단독",
    "가능성", "위험", "우려", "세계", "영상", "사진", "기자", "종합",
    "출시", "게임", "게임에", "업데이트", "소식", "화제", "관심", "주목",
    "보도", "기사", "이란", "미국", "정부", "한국", "중국", "일본",
    "대한민국", "이번", "오늘의", "오늘도", "최근", "당시", "현재",
    "위메이드에", "드라마에", "영화에", "배우가", "가수가"
}

CATEGORY_HINTS = {
    "정치": {"대통령", "국회", "정부", "총리", "장관", "여당", "야당", "선거", "외교", "정상회담"},
    "경제": {"환율", "증시", "주가", "금리", "반도체", "부동산", "코스피", "코스닥", "달러", "유가"},
    "스포츠": {"축구", "야구", "농구", "배구", "골프", "손흥민", "이강인", "챔피언스리그", "월드컵", "올림픽"},
    "연예": {"배우", "가수", "드라마", "영화", "예능", "컴백", "아이돌", "공연", "앨범", "방탄소년단", "블랙핑크"},
    "게임": {"게임", "모바일게임", "닌텐도", "스팀", "패치", "업데이트", "출시", "플레이스테이션", "위메이드", "넥슨", "엔씨", "크래프톤"},
}

CATEGORY_REQUIRED_HINTS = {
    "정치": {"대통령", "국회", "정부", "총리", "장관", "여당", "야당", "선거", "외교", "정상회담"},
    "경제": {"환율", "증시", "주가", "금리", "반도체", "부동산", "코스피", "코스닥", "달러", "유가"},
    "스포츠": {"축구", "야구", "농구", "배구", "골프", "손흥민", "이강인", "챔피언스리그", "월드컵", "올림픽"},
    "연예": {"배우", "가수", "드라마", "영화", "예능", "컴백", "아이돌", "공연", "앨범", "방탄소년단", "블랙핑크"},
    "게임": {"게임", "모바일게임", "닌텐도", "스팀", "패치", "업데이트", "출시", "플레이스테이션", "위메이드", "넥슨", "엔씨", "크래프톤"},
}

COMMON_SUFFIXES = [
    "에서", "으로", "에게", "한테", "처럼", "보다", "까지", "부터",
    "만의", "만을", "만이", "만에", "으로의", "과의", "와의",
    "에서의", "에게서", "에는", "에서는", "으로는",
    "이다", "였다", "한다", "했다", "됐다", "된다",
    "으로", "에게", "과", "와", "은", "는", "이", "가", "을", "를", "에", "의"
]

def clean_token(token: str) -> str:
    token = token.strip()
    token = re.sub(r"[\[\]\(\)\{\}<>\"'“”‘’.,!?…:;|/\\]", "", token)
    return token

def strip_suffixes(word: str) -> str:
    original = word
    for suffix in sorted(COMMON_SUFFIXES, key=len, reverse=True):
        if len(word) > len(suffix) + 1 and word.endswith(suffix):
            word = word[: -len(suffix)]
            break
    return word if len(word) >= 2 else original

def split_main_title(title: str) -> str:
    title = re.sub(r"\s+", " ", title).strip()
    parts = [p.strip() for p in title.split(" - ") if p.strip()]
    return parts[0] if parts else title

def pick_candidates(title: str) -> list[str]:
    main_title = split_main_title(title)
    raw_tokens = main_title.split()

    tokens = []
    for raw in raw_tokens:
        word = clean_token(raw)
        word = strip_suffixes(word)

        if len(word) < 2:
            continue
        if word in STOPWORDS or word in BANNED_KEYWORDS:
            continue
        if re.fullmatch(r"\d+", word):
            continue
        tokens.append(word)

    return tokens

def choose_keyword(title: str, requested_category: str) -> str | None:
    candidates = pick_candidates(title)
    if not candidates:
        return None

    # 탭별 우선 키워드
    if requested_category in CATEGORY_REQUIRED_HINTS:
        hints = CATEGORY_REQUIRED_HINTS[requested_category]
        prioritized = [w for w in candidates if w in hints]
        if prioritized:
            return prioritized[0]

    # 너무 일반적인 단어 제외 후 첫 후보 선택
    preferred = [
        w for w in candidates
        if w not in {
            "관련", "논란", "우려", "가능성", "관심", "주목", "예정",
            "이번", "최근", "현재", "국내", "해외"
        }
    ]

    return preferred[0] if preferred else candidates[0]

def detect_category_for_all(keyword: str, titles: list[str]) -> str:
    merged = f"{keyword} " + " ".join(titles[:3])
    for category, hints in CATEGORY_HINTS.items():
        for hint in hints:
            if hint in merged:
                return category
    return "일반"

def category_match_score(category: str, keyword: str, titles: list[str]) -> int:
    if category == "전체":
        return 1

    hints = CATEGORY_REQUIRED_HINTS.get(category, set())
    text = f"{keyword} " + " ".join(titles[:3])

    score = 0
    for hint in hints:
        if hint in text:
            score += 1
    return score

def build_summary(keyword: str, titles: list[str]) -> str:
    if not titles:
        return f"{keyword} 관련 뉴스가 주목받고 있습니다."

    title = split_main_title(titles[0]).strip()

    if len(title) > 54:
        title = title[:54] + "..."

    if keyword in {"환율", "증시", "주가", "금리", "달러", "유가"}:
        return f"{title} 영향으로 관련 검색이 늘었습니다."

    if keyword in {"대통령", "국회", "정부", "장관", "총리", "외교", "선거", "트럼프"}:
        return f"{title} 보도로 이 키워드가 많이 언급됐습니다."

    if keyword in {"축구", "야구", "농구", "배구", "골프", "손흥민", "이강인", "챔피언스리그"}:
        return f"{title} 경기·결과 소식으로 관심이 높아졌습니다."

    if keyword in {"배우", "가수", "드라마", "영화", "아이돌", "컴백"}:
        return f"{title} 관련 화제로 주목받고 있습니다."

    if keyword in {"위메이드", "넥슨", "엔씨", "크래프톤", "닌텐도", "스팀", "플레이스테이션"}:
        return f"{title} 소식으로 관심이 커졌습니다."

    return f"{title} 보도로 관심이 커졌습니다."

def parse_feed(url: str):
    res = requests.get(url, timeout=12)
    res.raise_for_status()
    root = ET.fromstring(res.content)

    items = []
    for item in root.findall(".//item"):
        title = (item.findtext("title", default="") or "").strip()
        link = (item.findtext("link", default="") or "").strip()
        pub_date = (item.findtext("pubDate", default="") or "").strip()

        if title:
            items.append({
                "title": title,
                "link": link,
                "pubDate": pub_date
            })

    return items

@app.get("/")
def root():
    return {"status": "ok", "message": "trendpick api is live"}

@app.get("/trends")
def get_trends(
    category: str = Query(default="전체"),
    limit: int = Query(default=20, ge=1, le=50)
):
    try:
        category = category if category in CATEGORY_FEEDS else "전체"
        feed_url = CATEGORY_FEEDS[category]

        items = parse_feed(feed_url)

        grouped_titles = defaultdict(list)
        grouped_links = defaultdict(list)
        grouped_scores = Counter()

        for idx, item in enumerate(items):
            title = item["title"]
            link = item["link"]
            pub_date = item["pubDate"]

            keyword = choose_keyword(title, category)
            if not keyword:
                continue

            grouped_titles[keyword].append(title)

            if link:
                grouped_links[keyword].append({
                    "title": split_main_title(title),
                    "url": link,
                    "source": "Google News",
                    "pubDate": pub_date
                })

            score = max(1, 12 - min(idx, 11))
            grouped_scores[keyword] += score

        ranked = []
        for keyword, score in grouped_scores.most_common(100):
            titles = grouped_titles[keyword][:3]
            links = grouped_links[keyword][:5]

            if len(keyword) <= 2 and score < 6:
                continue

            match_score = category_match_score(category, keyword, titles)
            if category != "전체" and match_score == 0:
                continue

            ranked.append({
                "keyword": keyword,
                "score": score + (match_score * 5),
                "titles": titles,
                "links": links
            })

        ranked.sort(key=lambda x: x["score"], reverse=True)

        data = []
        prev_score = None
        rank = 1

        for item in ranked:
            keyword = item["keyword"]
            titles = item["titles"]
            links = item["links"]
            score = item["score"]

            delta = 0
            if prev_score is not None:
                delta = max(0, prev_score - score)
            prev_score = score

            final_category = category if category != "전체" else detect_category_for_all(keyword, titles)

            data.append({
                "keyword": keyword,
                "rank": rank,
                "delta": delta,
                "category": final_category,
                "summary": build_summary(keyword, titles),
                "headlines": titles,
                "links": links
            })
            rank += 1

            if len(data) >= limit:
                break

        if not data:
            data = [{
                "keyword": "데이터 없음",
                "rank": 1,
                "delta": 0,
                "category": category if category != "전체" else "기타",
                "summary": "표시할 키워드가 없습니다.",
                "headlines": [],
                "links": []
            }]

        return JSONResponse(content=data)

    except Exception as e:
        return JSONResponse(content=[{
            "keyword": "데이터 없음",
            "rank": 1,
            "delta": 0,
            "category": category if category != "전체" else "기타",
            "summary": f"오류 발생: {str(e)}",
            "headlines": [],
            "links": []
        }])
