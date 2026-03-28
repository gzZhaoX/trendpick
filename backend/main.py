from fastapi import FastAPI, Query
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

# =========================
# RSS
# =========================
CATEGORY_FEEDS = {
    "전체": "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko",
    "정치": "https://news.google.com/rss/headlines/section/topic/POLITICS?hl=ko&gl=KR&ceid=KR:ko",
    "경제": "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=ko&gl=KR&ceid=KR:ko",
    "스포츠": "https://news.google.com/rss/headlines/section/topic/SPORTS?hl=ko&gl=KR&ceid=KR:ko",
    "연예": "https://news.google.com/rss/search?q=연예 OR 배우 OR 가수 OR 드라마 OR 영화&hl=ko&gl=KR&ceid=KR:ko",
    "게임": "https://news.google.com/rss/search?q=게임 OR 스팀 OR 닌텐도 OR 플레이스테이션&hl=ko&gl=KR&ceid=KR:ko",
}

# =========================
# 필터 (핵심 개선)
# =========================
STOPWORDS = {
    "뉴스","속보","단독","영상","사진","기자","앵커",
    "오늘","오후","오전","관련","대한","통해","위해",
    "정부","한국","미국","중국","일본","국내","해외",
    "사람","경우","상황","결과","현장","논란","이슈",
    "발표","공개","확인","진행","예정","종합",
    "조선일보","연합뉴스","뉴시스","중앙일보","동아일보",
    "한겨레","경향신문","한국경제","매일경제","서울신문",
    "머니투데이","이데일리","아시아경제","노컷뉴스",
    "문화일보","뉴스1","KBS","MBC","SBS","JTBC","YTN",
    "게임","출시","업데이트","화제","관심","보도","기사"
}

# 🔥 추가 제거 (이상한 것들 싹 제거)
BANNED = {
    "결국","만에","가운데","이번","최근","현재",
    "가능성","위험","우려","세계","대한민국",
    "100만","1위","10","20","3","4","5"
}

# 조사 제거
def clean_word(word):
    word = re.sub(r"[^\w가-힣]", "", word)
    word = re.sub(r"(에서|으로|에게|까지|부터|처럼|보다|이다|였다|했다|된다|은|는|이|가|을|를|에|의)$", "", word)
    return word

# =========================
# 키워드 선택 (개선)
# =========================
def extract_keyword(title):
    words = title.split()

    candidates = []
    for w in words:
        w = clean_word(w)

        if len(w) < 2:
            continue
        if w in STOPWORDS or w in BANNED:
            continue
        if w.isdigit():
            continue

        candidates.append(w)

    if not candidates:
        return None

    # 🔥 너무 일반적인 단어 제외
    for w in candidates:
        if w not in {"이란","미국","정부","사람","문제"}:
            return w

    return candidates[0]

# =========================
# 제목 정리
# =========================
def clean_title(title):
    return title.split(" - ")[0].strip()

# =========================
# 요약 개선 (핵심)
# =========================
def make_summary(keyword, title):
    title = clean_title(title)

    if len(title) > 60:
        title = title[:60] + "..."

    return f"{title} 보도로 관심이 커지고 있습니다."

# =========================
# 카테고리 판단 개선
# =========================
def detect_category(title):
    if any(x in title for x in ["축구","야구","선수","경기","골","리그"]):
        return "스포츠"
    if any(x in title for x in ["게임","스팀","닌텐도","출시"]):
        return "게임"
    if any(x in title for x in ["배우","가수","드라마","영화","아이돌"]):
        return "연예"
    if any(x in title for x in ["환율","주가","경제","금리"]):
        return "경제"
    if any(x in title for x in ["대통령","정부","국회","외교"]):
        return "정치"
    return "일반"

# =========================
# API
# =========================
@app.get("/trends")
def trends(category: str = Query("전체")):
    url = CATEGORY_FEEDS.get(category, CATEGORY_FEEDS["전체"])

    res = requests.get(url)
    root = ET.fromstring(res.content)

    counter = Counter()
    titles_map = defaultdict(list)

    for item in root.findall(".//item"):
        title = item.findtext("title", "")

        keyword = extract_keyword(title)
        if not keyword:
            continue

        counter[keyword] += 1
        titles_map[keyword].append(title)

    result = []
    for i, (keyword, _) in enumerate(counter.most_common(20), start=1):
        title = titles_map[keyword][0]

        result.append({
            "keyword": keyword,
            "rank": i,
            "delta": 0,
            "category": category if category != "전체" else detect_category(title),
            "summary": make_summary(keyword, title),
            "headlines": [clean_title(t) for t in titles_map[keyword][:3]]
        })

    return result
