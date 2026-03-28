from fastapi import FastAPI, Query
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

# =========================
# RSS
# =========================
CATEGORY_FEEDS = {
    "전체": "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko",
    "정치": "https://news.google.com/rss/headlines/section/topic/POLITICS?hl=ko&gl=KR&ceid=KR:ko",
    "경제": "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=ko&gl=KR&ceid=KR:ko",
    "스포츠": "https://news.google.com/rss/headlines/section/topic/SPORTS?hl=ko&gl=KR&ceid=KR:ko",
    "연예": "https://news.google.com/rss/search?q=연예 OR 배우 OR 가수 OR 드라마&hl=ko&gl=KR&ceid=KR:ko",
    "게임": "https://news.google.com/rss/search?q=게임 OR 배그 OR 스팀 OR 닌텐도&hl=ko&gl=KR&ceid=KR:ko",
}

# =========================
# 캐싱 (🔥 속도 핵심)
# =========================
CACHE = {}
CACHE_TTL = 60  # 60초

def get_cache(key):
    data = CACHE.get(key)
    if not data:
        return None

    if time.time() - data["time"] > CACHE_TTL:
        return None

    return data["value"]

def set_cache(key, value):
    CACHE[key] = {
        "time": time.time(),
        "value": value
    }

# =========================
# 텍스트 정리
# =========================
def clean_title(title):
    return title.split(" - ")[0].strip()

def extract_main_keyword(title):
    words = re.findall(r"[가-힣]{2,}", title)

    stop = {
        "기자","뉴스","속보","단독","영상","사진","관련","대한",
        "정부","한국","미국","중국","일본","국내","해외",
        "오늘","오전","오후","이번","최근","현재"
    }

    for w in words:
        if w not in stop:
            return w

    return words[0] if words else None

# =========================
# API
# =========================
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
    root = ET.fromstring(res.content)

    grouped = defaultdict(list)

    for item in root.findall(".//item"):
        title = clean_title(item.findtext("title", ""))
        link = item.findtext("link", "")

        keyword = extract_main_keyword(title)
        if not keyword:
            continue

        grouped[keyword].append({
            "title": title,
            "url": link
        })

    result = []

    sorted_items = sorted(grouped.items(), key=lambda x: len(x[1]), reverse=True)

    for i, (keyword, items) in enumerate(sorted_items[:limit], start=1):
        result.append({
            "keyword": keyword,
            "rank": i,
            "delta": 0,
            "category": category if category != "전체" else "일반",
            "summary": items[0]["title"],
            "headlines": [x["title"] for x in items[:3]],
            "links": items[:5]
        })

    set_cache(cache_key, result)
    return result
