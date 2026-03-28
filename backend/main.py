from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import requests
import xml.etree.ElementTree as ET

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
    "연예": "https://news.google.com/rss/search?q=연예 OR 배우 OR 가수 OR 드라마 OR 영화&hl=ko&gl=KR&ceid=KR:ko",
    "게임": "https://news.google.com/rss/search?q=게임 OR 스팀 OR 닌텐도 OR 플레이스테이션 OR 배그&hl=ko&gl=KR&ceid=KR:ko",
}

def clean_title(title: str) -> str:
    if " - " in title:
        return title.split(" - ")[0].strip()
    return title.strip()

def parse_feed(url: str):
    res = requests.get(url, timeout=10)
    res.raise_for_status()
    root = ET.fromstring(res.content)

    items = []
    seen = set()

    for item in root.findall(".//item"):
        title = item.findtext("title", "") or ""
        link = item.findtext("link", "") or ""

        title = clean_title(title)
        if not title:
            continue

        if title in seen:
            continue
        seen.add(title)

        items.append({
            "title": title,
            "link": link
        })

    return items

@app.get("/")
def root():
    return {"status": "ok"}

@app.get("/trends")
def trends(category: str = Query("전체"), limit: int = Query(20)):
    url = CATEGORY_FEEDS.get(category, CATEGORY_FEEDS["전체"])
    items = parse_feed(url)

    result = []
    for i, item in enumerate(items[:limit], start=1):
        result.append({
            "keyword": item["title"],   # 제목 자체를 표시
            "rank": i,
            "delta": 0,
            "category": category if category != "전체" else "일반",
            "summary": item["title"],
            "headlines": [item["title"]],
            "links": [{
                "title": item["title"],
                "url": item["link"],
                "source": "Google News"
            }]
        })

    if not result:
        return [{
            "keyword": "데이터 없음",
            "rank": 1,
            "delta": 0,
            "category": "일반",
            "summary": "표시할 데이터가 없습니다.",
            "headlines": [],
            "links": []
        }]

    return result
