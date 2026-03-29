import re
import json
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
    "유튜브": "https://www.youtube.com/feeds/videos.xml?channel_id=UC_x5XG1OV2P6uZZ5FSM9Ttw",
    "웃긴대학": "https://web.humoruniv.com/rss/best.xml",
    "보배드림": "https://m.bobaedream.co.kr/board/bbs/best/rss",
    "네이트": "https://www.nate.com/main/srv/news/data/keywordList.today.json"
}


def fetch_text(url):
    res = requests.get(url, headers=HEADERS, timeout=10)
    res.raise_for_status()
    return res.text


def parse_rss(xml_text, category):
    xml_text = re.sub(r'\sxmlns(:\w+)?="[^"]+"', '', xml_text)
    root = ET.fromstring(xml_text.encode("utf-8"))

    items = []
    nodes = root.findall(".//item")

    for i, node in enumerate(nodes[:20]):
        title = (node.findtext("title") or "").split(" - ")[0].strip()
        link = node.findtext("link") or ""

        if title:
            items.append({
                "keyword": title,
                "rank": i + 1,
                "category": category,
                "link": link
            })

    return items


def parse_youtube(xml_text):
    xml_text = re.sub(r'\sxmlns(:\w+)?="[^"]+"', '', xml_text)
    root = ET.fromstring(xml_text.encode("utf-8"))

    items = []
    nodes = root.findall(".//entry")

    for i, node in enumerate(nodes[:20]):
        title = node.findtext("title") or ""
        link_node = node.find("link")
        link = link_node.get("href") if link_node is not None else ""

        if title:
            items.append({
                "keyword": title,
                "rank": i + 1,
                "category": "유튜브",
                "link": link
            })

    return items


# 🔥 핵심: 네이트 전용 파서
def parse_nate(text):
    result = []

    try:
        outer = json.loads(text)

        # data 안에 있음
        inner_data = outer.get("data", {})

        for i, key in enumerate(inner_data):
            item = inner_data[key]

            raw = item.get("keyword_name", "")

            # 🔥 unicode decode
            keyword = raw.encode().decode("unicode_escape")

            # <br> 제거
            keyword = re.sub(r"<.*?>", "", keyword).strip()

            if keyword:
                result.append({
                    "keyword": keyword,
                    "rank": len(result) + 1,
                    "category": "네이트",
                    "link": f"https://search.nate.com/search/all.html?q={keyword}"
                })

            if len(result) >= 10:
                break

    except Exception as e:
        print("NATE ERROR:", e)

    return result


@app.get("/trends")
def get_trends(category: str = Query(default="전체")):
    url = FEEDS.get(category, FEEDS["전체"])

    try:
        text = fetch_text(url)

        if category == "네이트":
            data = parse_nate(text)

        elif category == "유튜브":
            data = parse_youtube(text)

        else:
            data = parse_rss(text, category)

        if not data:
            raise HTTPException(502, detail=f"{category} 데이터 없음")

        return data

    except Exception as e:
        raise HTTPException(502, detail=str(e))
