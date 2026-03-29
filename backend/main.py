import re
import json
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
    "유튜브": "https://www.youtube.com/feeds/videos.xml?channel_id=UC_x5XG1OV2P6uZZ5FSM9Ttw",
    "웃긴대학": "https://web.humoruniv.com/rss/best.xml",
    "보배드림": "https://m.bobaedream.co.kr/board/bbs/best/rss",
    "네이트": "https://www.nate.com/main/srv/news/data/keywordList.today.json"
}


def fetch_response(url: str, timeout: int = 10):
    res = requests.get(url, headers=HEADERS, timeout=timeout)
    res.raise_for_status()
    return res


def fetch_text(url: str, timeout: int = 10) -> str:
    res = fetch_response(url, timeout=timeout)
    return res.text


def fetch_nate_json(url: str, timeout: int = 10) -> dict:
    res = fetch_response(url, timeout=timeout)

    # 중요: text 쓰지 말고 bytes -> utf-8 직접 디코드
    raw = res.content.decode("utf-8", errors="strict")
    return json.loads(raw)


def strip_namespaces(xml_text: str) -> str:
    return re.sub(r'\sxmlns(:\w+)?="[^"]+"', '', xml_text)


def parse_rss(xml_text: str, category: str):
    xml_text = strip_namespaces(xml_text)
    root = ET.fromstring(xml_text.encode("utf-8"))

    items = []
    for i, node in enumerate(root.findall(".//item")[:20]):
        title = (node.findtext("title") or "").strip()
        link = (node.findtext("link") or "").strip()

        if " - " in title:
            title = title.split(" - ")[0].strip()

        if not title:
            continue

        items.append({
            "keyword": title,
            "rank": i + 1,
            "category": category,
            "link": link
        })

    return items


def parse_youtube(xml_text: str):
    xml_text = strip_namespaces(xml_text)
    root = ET.fromstring(xml_text.encode("utf-8"))

    items = []
    for i, node in enumerate(root.findall(".//entry")[:20]):
        title = (node.findtext("title") or "").strip()
        link_node = node.find("link")
        link = link_node.get("href") if link_node is not None else ""

        if not title:
            continue

        items.append({
            "keyword": title,
            "rank": i + 1,
            "category": "유튜브",
            "link": link
        })

    return items


def clean_html_text(text: str) -> str:
    text = html.unescape(text)
    text = re.sub(r"<br\s*/?>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_nate(payload: dict):
    raw_data = payload.get("data", {})
    if not isinstance(raw_data, dict):
        raise HTTPException(status_code=502, detail="네이트 data 구조가 이상합니다.")

    items = []
    blocked_exact = {
        "message", "ok", "data", "result", "service_dtm", "server_dtm",
        "update_dtm", "keyword_sq", "count", "score", "create_dtm",
        "mod_dtm", "keyword_service", "ctgr_cd"
    }

    def sort_key(k):
        try:
            return int(k)
        except Exception:
            return 999999

    for key in sorted(raw_data.keys(), key=sort_key):
        entry = raw_data.get(key, {})
        if not isinstance(entry, dict):
            continue

        keyword = str(entry.get("keyword_name", "")).strip()
        keyword = clean_html_text(keyword)

        if not keyword:
            continue
        if len(keyword) < 2:
            continue
        if keyword.lower() in blocked_exact:
            continue
        if re.fullmatch(r"[0-9:\- ]+", keyword):
            continue

        items.append({
            "keyword": keyword,
            "rank": len(items) + 1,
            "category": "네이트",
            "link": f"https://search.nate.com/search/all.html?q={requests.utils.quote(keyword)}"
        })

        if len(items) >= 10:
            break

    return items


@app.get("/trends")
def get_trends(category: str = Query(default="전체")):
    category = category if category in FEEDS else "전체"
    url = FEEDS[category]

    try:
        if category == "네이트":
            payload = fetch_nate_json(url, timeout=10)
            data = parse_nate(payload)
        elif category == "유튜브":
            text = fetch_text(url, timeout=10)
            data = parse_youtube(text)
        else:
            text = fetch_text(url, timeout=10)
            data = parse_rss(text, category)

        if not data:
            raise HTTPException(status_code=502, detail=f"{category} 데이터 없음")

        return data

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/debug-nate")
def debug_nate():
    payload = fetch_nate_json(FEEDS["네이트"], timeout=10)
    return {
        "result": payload.get("result"),
        "message": payload.get("message"),
        "first_item": payload.get("data", {}).get("0", {})
    }
