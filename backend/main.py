from fastapi import FastAPI, Query, Body
from fastapi.middleware.cors import CORSMiddleware
import requests
import xml.etree.ElementTree as ET
import time
import re
from collections import defaultdict

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
    "연예": "https://news.google.com/rss/search?q=연예 OR 배우 OR 가수 OR 드라마&hl=ko&gl=KR&ceid=KR:ko",
    "게임": "https://news.google.com/rss/search?q=게임 OR 배그 OR 스팀 OR 닌텐도&hl=ko&gl=KR&ceid=KR:ko",
}

CACHE = {}
PREV_CACHE = {}
CACHE_TTL = 60

# 조회수 기반 트렌드 준비용 저장소
VIEW_COUNTS = defaultdict(int)

STOPWORDS = {
    "기자", "뉴스", "속보", "단독", "영상", "사진", "관련", "대한",
    "정부", "한국", "미국", "중국", "일본", "국내", "해외",
    "오늘", "오전", "오후", "이번", "최근", "현재"
}

def get_cache(key):
    data = CACHE.get(key)
    if not data:
        return None
    if time.time() - data["time"] > CACHE_TTL:
        return None
    return data["value"]

def set_cache(key, value):
    old_value = CACHE.get(key, {}).get("value", [])
    PREV_CACHE[key] = old_value
    CACHE[key] = {
        "time": time.time(),
        "value": value
    }

def clean_title(title):
    return title.split(" - ")[0].strip()

def extract_main_keyword(title):
    words = re.findall(r"[가-힣A-Za-z0-9]{2,}", title)

    for w in words:
        if w not in STOPWORDS:
            return w

    return words[0] if words else None

def compute_delta(category, current_items):
    prev_items = PREV_CACHE.get(category, [])
    prev_rank_map = {item["keyword"]: item["rank"] for item in prev_items}

    result = []
    for item in current_items:
        keyword = item["keyword"]
        current_rank = item["rank"]
        prev_rank = prev_rank_map.get(keyword)

        if prev_rank is None:
            delta = 0
        else:
            delta = max(0, prev_rank - current_rank)

        new_item = dict(item)
        new_item["delta"] = delta
        result.append(new_item)

    return result

@app.get("/")
def root():
    return {"status": "ok"}

@app.get("/trends")
def trends(category: str = Query("전체"), limit: int = Query(20)):
    cache_key = f"{category}"
    cached = get_cache(cache_key)
    if cached:
        return cached

    url = CATEGORY_FEEDS.get(category, CATEGORY_FEEDS["전체"])

    res = requests.get(url, timeout=8)
    res.raise_for_status()
    root = ET.fromstring(res.content)

    grouped = defaultdict(list)

    for item in root.findall(".//item"):
        title = clean_title(item.findtext("title", "") or "")
        link = item.findtext("link", "") or ""

        keyword = extract_main_keyword(title)
        if not keyword:
            continue

        grouped[keyword].append({
            "title": title,
            "url": link
        })

    sorted_items = sorted(grouped.items(), key=lambda x: len(x[1]), reverse=True)

    result = []
    for i, (keyword, items) in enumerate(sorted_items[:limit], start=1):
        result.append({
            "keyword": keyword,
            "rank": i,
            "delta": 0,
            "category": category if category != "전체" else "일반",
            "summary": items[0]["title"],
            "headlines": [x["title"] for x in items[:3]],
            "links": [
                {
                    "title": x["title"],
                    "url": x["url"],
                    "source": "Google News"
                }
                for x in items[:5]
            ],
            "views": VIEW_COUNTS.get(keyword, 0),
        })

    result = compute_delta(cache_key, result)
    set_cache(cache_key, result)
    return result

# 4번 준비용: 상세 보기 눌렀을 때 조회수 기록
@app.post("/track-view")
def track_view(payload: dict = Body(...)):
    keyword = str(payload.get("keyword", "")).strip()
    if keyword:
        VIEW_COUNTS[keyword] += 1
    return {"ok": True, "keyword": keyword, "views": VIEW_COUNTS.get(keyword, 0)}

# 4번 준비용: 조회수 기반 인기 목록
@app.get("/popular")
def popular(limit: int = Query(10)):
    items = sorted(VIEW_COUNTS.items(), key=lambda x: x[1], reverse=True)[:limit]
    return [{"keyword": k, "views": v} for k, v in items]
