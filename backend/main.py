from fastapi import FastAPI
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
    "JTBC", "채널A", "MBN", "YTN", "TV조선"
}

CATEGORY_RULES = {
    "정치": {"대통령", "국회", "정부", "총리", "장관", "여당", "야당", "외교", "선거"},
    "경제": {"환율", "증시", "주가", "금리", "반도체", "부동산", "코스피", "코스닥", "달러"},
    "스포츠": {"야구", "축구", "농구", "배구", "골프", "월드컵", "올림픽", "챔피언스리그", "손흥민"},
    "연예": {"아이돌", "가수", "배우", "드라마", "영화", "컴백", "예능", "공연"},
    "게임": {"게임", "모바일게임", "닌텐도", "플레이스테이션", "스팀", "출시", "업데이트"},
}

def clean_token(token: str) -> str:
    token = token.strip()
    token = re.sub(r"[\[\]\(\)\{\}<>\"'“”‘’.,!?…:;|/\\]", "", token)
    return token

def pick_keyword(title: str) -> str | None:
    title = re.sub(r"\s+", " ", title).strip()
    parts = [p.strip() for p in title.split(" - ") if p.strip()]
    main_text = parts[0] if parts else title

    candidates = []
    for raw in main_text.split():
        word = clean_token(raw)
        if len(word) < 2:
            continue
        if word in STOPWORDS:
            continue
        if re.fullmatch(r"\d+", word):
            continue
        candidates.append(word)

    if not candidates:
        return None

    preferred = [
        w for w in candidates
        if len(w) >= 2
        and w not in {"관련", "우려", "논란", "결국", "만에", "위험", "가능성", "급증", "확산"}
    ]

    if preferred:
        return preferred[0]

    return candidates[0]

def classify_category(keyword: str, title: str) -> str:
    text = f"{keyword} {title}"
    for category, words in CATEGORY_RULES.items():
        for w in words:
            if w in text:
                return category
    return "일반"

def build_summary(keyword: str, titles: list[str]) -> str:
    if not titles:
        return f"{keyword} 관련 뉴스가 늘었습니다."

    top_title = titles[0]

    if len(top_title) > 46:
        top_title = top_title[:46] + "..."

    return f"{keyword} 관련 보도가 이어지고 있습니다. 예: {top_title}"

@app.get("/")
def root():
    return {"status": "ok", "message": "trendpick api is live"}

@app.get("/trends")
def get_trends():
    try:
        url = "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko"
        res = requests.get(url, timeout=10)
        res.raise_for_status()

        root = ET.fromstring(res.content)

        grouped_titles = defaultdict(list)
        grouped_links = defaultdict(list)
        grouped_category = {}

        for item in root.findall(".//item"):
            title = (item.findtext("title", default="") or "").strip()
            link = (item.findtext("link", default="") or "").strip()

            if not title:
                continue

            keyword = pick_keyword(title)
            if not keyword:
                continue

            grouped_titles[keyword].append(title)

            if link:
                grouped_links[keyword].append({
                    "title": title,
                    "url": link,
                    "source": "Google News"
                })

            if keyword not in grouped_category:
                grouped_category[keyword] = classify_category(keyword, title)

        counts = Counter({k: len(v) for k, v in grouped_titles.items()})

        data = []
        rank = 1

        for keyword, _ in counts.most_common(20):
            titles = grouped_titles[keyword][:3]
            links = grouped_links[keyword][:5]

            data.append({
                "keyword": keyword,
                "rank": rank,
                "delta": 0,
                "category": grouped_category.get(keyword, "일반"),
                "summary": build_summary(keyword, titles),
                "headlines": titles,
                "links": links
            })
            rank += 1

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
