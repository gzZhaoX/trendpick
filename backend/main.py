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
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/16.0 Mobile/15E148 Safari/604.1"
    )
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


def fetch_text(url: str, timeout: int = 10, encoding=None) -> str:
    response = requests.get(url, headers=HEADERS, timeout=timeout)
    response.raise_for_status()

    if encoding:
        response.encoding = encoding

    return response.text


def clean_xml_text(xml_text: str) -> str:
    return re.sub(r'\sxmlns(:\w+)?="[^"]+"', '', xml_text)


def normalize_title(title: str) -> str:
    text = title.strip()
    if " - " in text:
        text = text.split(" - ")[0].strip()
    return text


def parse_standard_rss(xml_text: str, category: str):
    cleaned = clean_xml_text(xml_text)
    root = ET.fromstring(cleaned.encode("utf-8"))

    items = []
    nodes = root.findall(".//item")

    for i, node in enumerate(nodes[:20]):
        title = (node.findtext("title", "") or "").strip()
        link = (node.findtext("link", "") or "").strip()

        if not title:
            continue

        items.append({
            "keyword": normalize_title(title),
            "rank": i + 1,
            "category": category,
            "link": link
        })

    return items


def parse_youtube_atom(xml_text: str):
    cleaned = clean_xml_text(xml_text)
    root = ET.fromstring(cleaned.encode("utf-8"))

    items = []
    nodes = root.findall(".//entry")

    for i, node in enumerate(nodes[:20]):
        title = (node.findtext("title", "") or "").strip()
        link = ""

        link_node = node.find("link")
        if link_node is not None:
            link = link_node.get("href") or (link_node.text or "")

        if not title:
            continue

        items.append({
            "keyword": title,
            "rank": i + 1,
            "category": "유튜브",
            "link": link
        })

    return items


def find_keywords_deep(obj, found):
    if isinstance(obj, dict):
        for key in ["keyword", "name", "txt", "text", "query", "title", "k"]:
            value = obj.get(key)
            if isinstance(value, str):
                value = value.strip()
                if len(value) >= 2 and value not in found:
                    found.append(value)

        for value in obj.values():
            find_keywords_deep(value, found)

    elif isinstance(obj, list):
        for item in obj:
            find_keywords_deep(item, found)


def parse_nate_response(text: str):
    text = text.strip()
    found = []

    # 1차: JSON 파싱 시도
    try:
        data = json.loads(text)
        find_keywords_deep(data, found)
    except Exception:
        pass

    # 2차: 문자열 패턴에서 키워드 후보 추출
    if not found:
        matches = re.findall(r'"([^"]{2,40})"', text)
        for m in matches:
            value = m.strip()
            if not re.search(r"[가-힣A-Za-z0-9]", value):
                continue
            if value in found:
                continue
            found.append(value)

    blocked = {
        "success", "result", "data", "list", "keyword",
        "news", "tab", "value", "rank", "on", "off", "true", "false"
    }

    cleaned = []
    for value in found:
        if value.lower() in blocked:
            continue
        if len(value) < 2:
            continue
        cleaned.append(value)
        if len(cleaned) >= 10:
            break

    return [
        {
            "keyword": keyword,
            "rank": i + 1,
            "category": "네이트",
            "link": f"https://search.nate.com/search/all.html?q={keyword}"
        }
        for i, keyword in enumerate(cleaned)
    ]


def clean_item_list(items: list, category: str, limit: int = 20):
    cleaned = []

    for item in items:
        keyword = str(item.get("keyword", "")).strip()
        link = str(item.get("link", "")).strip()

        if not keyword:
            continue

        cleaned.append({
            "keyword": keyword,
            "rank": len(cleaned) + 1,
            "category": category,
            "link": link
        })

        if len(cleaned) >= limit:
            break

    return cleaned


@app.get("/trends")
def get_trends(category: str = Query(default="전체")):
    selected_category = category if category in FEEDS else "전체"
    url = FEEDS[selected_category]

    try:
        if selected_category == "네이트":
            text = fetch_text(url, timeout=8, encoding="utf-8")
            data = parse_nate_response(text)
            data = clean_item_list(data, "네이트", 10)

        elif selected_category == "유튜브":
            text = fetch_text(url, timeout=10)
            data = parse_youtube_atom(text)
            data = clean_item_list(data, "유튜브", 20)

        elif selected_category == "웃긴대학":
            text = fetch_text(url, timeout=10)
            data = parse_standard_rss(text, "웃긴대학")
            data = clean_item_list(data, "웃긴대학", 20)

        elif selected_category == "보배드림":
            text = fetch_text(url, timeout=10)
            data = parse_standard_rss(text, "보배드림")
            data = clean_item_list(data, "보배드림", 20)

        else:
            text = fetch_text(url, timeout=10)
            data = parse_standard_rss(text, selected_category)
            data = clean_item_list(data, selected_category, 20)

        if not data:
            raise HTTPException(
                status_code=502,
                detail=f"{selected_category} 데이터가 비어 있습니다."
            )

        return data

    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=502,
            detail=f"{selected_category} 요청 실패: {str(e)}"
        )
    except ET.ParseError as e:
        raise HTTPException(
            status_code=502,
            detail=f"{selected_category} XML 파싱 실패: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"{selected_category} 처리 실패: {str(e)}"
        )


@app.get("/debug-nate")
def debug_nate():
    url = FEEDS["네이트"]
    text = fetch_text(url, timeout=8, encoding="utf-8")
    return {"preview": text[:3000]}
