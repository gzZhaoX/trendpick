from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone
from collections import Counter
import feedparser, re, urllib.parse

RSS_URL = "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko"
STOPWORDS = {"기자","뉴스","속보","오늘","이번","관련","정부","이후","통해","대한","위해","정말","있다","없다","된다","이유","공개","발표","영상","사진","단독","브리핑","사건","논란","한국","서울","국내","해외","미국","중국","일본","유럽","위원회","분석","전망"}
CATEGORY_HINTS = {
    "정치": ["대통령","국회","총리","정부","여당","야당","정치","탄핵","선거","외교"],
    "경제": ["환율","금리","증시","주가","코스피","코스닥","반도체","부동산","수출","무역","달러"],
    "스포츠": ["축구","야구","농구","배구","골프","챔피언스리그","mlb","epl","선수","감독"],
    "연예": ["배우","가수","아이돌","드라마","예능","콘서트","앨범","공연","영화","결혼","열애"],
    "게임": ["게임","출시","업데이트","패치","닌텐도","플레이스테이션","스팀","모바일게임"],
}
CACHE = {"updated_at": None, "items": [], "source_url": RSS_URL, "status": "초기화 중"}

app = FastAPI(title="TrendPick API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

def extract_words(text: str):
    words = re.findall(r"[가-힣A-Za-z0-9+]{2,20}", text)
    return [w for w in words if w not in STOPWORDS and not re.fullmatch(r"\d+", w)]

def infer_category(text: str):
    lower = text.lower()
    for cat, hints in CATEGORY_HINTS.items():
        if any(h.lower() in lower for h in hints):
            return cat
    return "기타"

def build_items():
    feed = feedparser.parse(RSS_URL)
    entries = getattr(feed, "entries", [])[:80]
    if not entries:
        raise RuntimeError("No RSS entries")
    counter = Counter()
    examples = {}
    news_map = {}
    for entry in entries:
        title = getattr(entry, "title", "") or ""
        link = getattr(entry, "link", "") or ""
        for word in extract_words(title)[:8]:
            counter[word] += 1
            examples.setdefault(word, title)
            news_map.setdefault(word, []).append({"title": title, "url": link})
    items = []
    for word, cnt in counter.most_common(12):
        title = examples.get(word, word)
        cat = infer_category(title)
        items.append({
            "rank": len(items)+1,
            "keyword": word,
            "category": cat,
            "summary": f"{title} 이슈로 관심이 커졌습니다.",
            "detail": f"Google 뉴스 RSS 헤드라인에서 '{word}' 관련 언급이 늘었습니다.",
            "points": [f"헤드라인 언급 {cnt}회", f"{cat} 카테고리로 분류"],
            "news": news_map.get(word, [])[:3],
            "search_url": "https://www.google.com/search?q=" + urllib.parse.quote(word),
        })
    return items

@app.get("/")
def root():
    return {"ok": True, "name": "TrendPick API"}

@app.get("/api/trends")
def trends(refresh: int = Query(default=0)):
    global CACHE
    if refresh or not CACHE["items"]:
        try:
            CACHE = {
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "items": build_items(),
                "source_url": RSS_URL,
                "status": "실시간 RSS 데이터"
            }
        except Exception:
            if not CACHE["items"]:
                CACHE = {
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "items": [],
                    "source_url": RSS_URL,
                    "status": "데이터 없음"
                }
    return CACHE
