import re
import html
import requests
import xml.etree.ElementTree as ET

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

FEEDS = {
    "전체": "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko",
    "정치": "https://news.google.com/rss/headlines/section/topic/POLITICS?hl=ko&gl=KR&ceid=KR:ko",
    "경제": "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=ko&gl=KR&ceid=KR:ko",
    "스포츠": "https://news.google.com/rss/headlines/section/topic/SPORTS?hl=ko&gl=KR&ceid=KR:ko",
    "연예": "https://news.google.com/rss/search?q=연예 OR 배우 OR 가수&hl=ko&gl=KR&ceid=KR:ko",
    "게임": "https://news.google.com/rss/search?q=게임 OR 스팀 OR 닌텐도&hl=ko&gl=KR&ceid=KR:ko",
    "유튜브": "https://www.youtube.com/feeds/videos.xml?channel_id=UC_x5XG1OV2P6uZZ5FSM9Ttw"
}

CATEGORIES = list(FEEDS.keys())


def fetch(url):
    res = requests.get(url, headers=HEADERS, timeout=10)
    res.raise_for_status()

    if not res.encoding or res.encoding == "ISO-8859-1":
        res.encoding = res.apparent_encoding

    return res.text


# 🔹 구글 RSS
def parse_rss(xml_text, category):
    root = ET.fromstring(xml_text)

    items = []
    for i, node in enumerate(root.findall(".//item")[:20]):
        title = (node.findtext("title") or "").split(" - ")[0].strip()
        link = node.findtext("link") or ""

        if not title:
            continue

        items.append({
            "keyword": html.unescape(title),
            "rank": i + 1,
            "category": category,
            "link": link
        })

    return items


# 🔹 유튜브 (정식 처리)
def parse_youtube(xml_text):
    root = ET.fromstring(xml_text)

    ns = {"atom": "http://www.w3.org/2005/Atom"}

    items = []
    for i, node in enumerate(root.findall("atom:entry", ns)[:20]):
        title = node.findtext("atom:title", default="", namespaces=ns)

        link_node = node.find("atom:link", ns)
        link = link_node.get("href") if link_node is not None else ""

        if not title:
            continue

        items.append({
            "keyword": title.strip(),
            "rank": i + 1,
            "category": "유튜브",
            "link": link
        })

    return items


# 🔹 안전 fallback (크롤링 실패 시 앱 죽지 않게)
def fallback_data(category):
    return [{
        "keyword": f"{category} 데이터를 불러올 수 없습니다",
        "rank": 1,
        "category": category,
        "link": "#"
    }]


@app.get("/trends")
def get_trends(category: str = Query(default="전체")):
    category = category if category in CATEGORIES else "전체"

    try:
        text = fetch(FEEDS[category])

        if category == "유튜브":
            data = parse_youtube(text)
        else:
            data = parse_rss(text, category)

        if not data:
            return fallback_data(category)

        return data

    except Exception as e:
        print("ERROR:", e)
        return fallback_data(category)
