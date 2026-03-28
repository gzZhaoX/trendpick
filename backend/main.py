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
    "연예": "https://news.google.com/rss/search?q=연예 when:1d&hl=ko&gl=KR&ceid=KR:ko",
    "게임": "https://news.google.com/rss/search?q=게임 when:1d&hl=ko&gl=KR&ceid=KR:ko",
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
    "스포츠서울", "스포티비", "OSEN", "텐아시아", "스타뉴스"
}

BANNED_KEYWORDS = {
    "결국", "만에", "가운데", "논란", "관련", "속보", "단독",
    "가능성", "위험", "우려", "정부", "미국", "한국", "중국",
    "일본", "세계", "영상", "사진", "기자", "종합"
}

CATEGORY_HINTS = {
    "정치": {"대통령", "국회", "정부", "총리", "장관", "여당", "야당", "선거", "외교", "정상회담"},
    "경제": {"환율", "증시", "주가", "금리", "반도체", "부동산", "코스피", "코스닥", "달러", "유가"},
    "스포츠": {"축구", "야구", "농구", "배구", "골프", "손흥민", "이강인", "챔피언스리그", "월드컵", "올림픽"},
    "연예": {"배우", "가수", "드라마", "영화", "예능", "컴백", "아이돌", "공연", "앨범"},
    "게임": {"게임", "모바일게임", "닌텐도", "스팀", "패치", "업데이트", "출시", "확률형", "플레이스테이션"},
}

def clean_token(token: str) -> str:
    token = token.strip()
    token = re.sub(r"[\[\]\(\)\{\}<>\"'“”‘’.,!?…:;|/\\]", "", token)
    return token

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
        if len(word) < 2:
            continue
        if word in STOPWORDS or word in BANNED_KEYWORDS:
            continue
        if re.fullmatch(r"\d+", word):
            continue
        tokens.append(word)

    return tokens

def choose_keyword(title: str) -> str | None:
    candidates = pick_candidates(title)
    if not candidates:
        return None

    preferred = [
        w for w in candidates
        if len(w) >= 2 and w not in {"이란", "미국", "정부", "후티", "이스라엘"}
    ]

    return preferred[0] if preferred else candidates[0]

def detect_category(keyword: str, titles: list[str], fallback: str) -> str:
    if fallback != "전체":
        return fallback

    merged = f"{keyword} " + " ".join(titles[:3])
    for category, hints in CATEGORY_HINTS.items():
        for hint in hints:
            if hint in merged:
                return category
    return "일반"

def build_summary(keyword: str, titles: list[str]) -> str:
    if not titles:
        return f"{keyword} 관련 보도가 이어지고 있습니다."

    title = split_main_title(titles[0])
    if len(title) > 44:
        title = title[:44] + "..."
    return f"{keyword} 관련 이슈가 이어지고 있습니다. 예: {title}"

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

            keyword = choose_keyword(title)
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

            # 위에 나오는 기사일수록 가중치 높게
            score = max(1, 12 - min(idx, 11))
            grouped_scores[keyword] += score

        ranked = []
        for keyword, score in grouped_scores.most_common(100):
            titles = grouped_titles[keyword][:3]
            links = grouped_links[keyword][:5]

            if len(keyword) <= 2 and score < 6:
                continue

            ranked.append({
                "keyword": keyword,
                "score": score,
                "titles": titles,
                "links": links
            })

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

            data.append({
                "keyword": keyword,
                "rank": rank,
                "delta": delta,
                "category": detect_category(keyword, titles, category),
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
                "category": "기타",
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
            "category": "기타",
            "summary": f"오류 발생: {str(e)}",
            "headlines": [],
            "links": []
        }])
