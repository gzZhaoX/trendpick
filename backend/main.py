import re
import html
import requests
import xml.etree.ElementTree as ET

from fastapi import FastAPI, Query
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
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
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
    "웃긴대학": "https://m.humoruniv.com/board/humor/list.html?table=pds",
    "보배드림": "https://www.bobaedream.co.kr/list?code=best",
}

CATEGORIES = list(FEEDS.keys())


def fetch_response(url: str, timeout: int = 12):
    response = requests.get(
        url,
        headers=HEADERS,
        timeout=timeout,
        allow_redirects=True
    )
    response.raise_for_status()

    if not response.encoding or response.encoding.lower() == "iso-8859-1":
        response.encoding = response.apparent_encoding

    return response


def fetch_text(url: str, timeout: int = 12) -> str:
    return fetch_response(url, timeout=timeout).text


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def strip_html(text: str) -> str:
    text = html.unescape(text or "")
    text = re.sub(r"<br\s*/?>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return normalize_space(text)


def make_item(keyword: str, rank: int, category: str, link: str):
    return {
        "keyword": keyword,
        "rank": rank,
        "category": category,
        "link": link
    }


def fallback_data(category: str, reason: str = ""):
    message = f"{category} 데이터를 불러올 수 없습니다"
    if reason:
        message = f"{message} - {reason[:80]}"
    return [make_item(message, 1, category, "#")]


# -----------------------------
# Google RSS
# -----------------------------
def parse_google_rss(xml_text: str, category: str):
    root = ET.fromstring(xml_text)

    items = []
    for i, node in enumerate(root.findall(".//item")[:20]):
        title = (node.findtext("title") or "").strip()
        link = (node.findtext("link") or "").strip()

        if " - " in title:
            title = title.split(" - ")[0].strip()

        title = html.unescape(title)

        if not title:
            continue

        items.append(make_item(title, i + 1, category, link))

    return items


# -----------------------------
# YouTube Atom
# -----------------------------
def parse_youtube_atom(xml_text: str):
    root = ET.fromstring(xml_text)

    ns = {"atom": "http://www.w3.org/2005/Atom"}

    items = []
    entries = root.findall("atom:entry", ns)

    for i, entry in enumerate(entries[:20]):
        title = (entry.findtext("atom:title", default="", namespaces=ns) or "").strip()

        link = ""
        link_node = entry.find("atom:link", ns)
        if link_node is not None:
            link = (link_node.get("href") or "").strip()

        if not title:
            continue

        items.append(make_item(title, i + 1, "유튜브", link))

    return items


# -----------------------------
# Humoruniv
# -----------------------------
def parse_humoruniv(html_text: str):
    results = []
    seen = set()

    patterns = [
        r'href="(/board/humor/read\.html\?number=\d+&table=pds[^"]*)".{0,500}?<span[^>]*class="subject"[^>]*>(.*?)</span>',
        r'href="(/board/humor/read\.html\?number=\d+&table=pds[^"]*)".{0,500}?<div[^>]*class="tit"[^>]*>(.*?)</div>',
        r'href="(/board/humor/read\.html\?number=\d+&table=pds[^"]*)".{0,300}?title="([^"]+)"',
        r'href="(/board/humor/read\.html\?number=\d+&table=pds[^"]*)".{0,300}?>([^<]{2,120})<'
    ]

    for pattern in patterns:
        matches = re.findall(pattern, html_text, flags=re.S | re.I)
        for href, raw_title in matches:
            title = strip_html(raw_title)

            if not title or len(title) < 2:
                continue
            if title in seen:
                continue
            if title in {"이전", "다음", "목록", "더보기"}:
                continue

            seen.add(title)
            results.append(
                make_item(
                    title,
                    len(results) + 1,
                    "웃긴대학",
                    f"https://m.humoruniv.com{href}"
                )
            )

            if len(results) >= 20:
                return results

    return results


# -----------------------------
# Bobaedream
# -----------------------------
def parse_bobaedream(html_text: str):
    results = []
    seen = set()

    patterns = [
        r'href="(/view\?code=best&No=\d+[^"]*)".{0,500}?title="([^"]+)"',
        r'href="(/view\?code=best&No=\d+[^"]*)".{0,500}?<span[^>]*class="tit"[^>]*>(.*?)</span>',
        r'href="(/view\?code=best&No=\d+[^"]*)".{0,300}?>([^<]{2,120})<'
    ]

    for pattern in patterns:
        matches = re.findall(pattern, html_text, flags=re.S | re.I)
        for href, raw_title in matches:
            title = strip_html(raw_title)

            if not title or len(title) < 2:
                continue
            if title in seen:
                continue
            if title in {"베스트글", "목록", "공지", "이전", "다음"}:
                continue

            seen.add(title)
            results.append(
                make_item(
                    title,
                    len(results) + 1,
                    "보배드림",
                    f"https://www.bobaedream.co.kr{href}"
                )
            )

            if len(results) >= 20:
                return results

    return results


@app.get("/trends")
def get_trends(category: str = Query(default="전체")):
    category = category if category in CATEGORIES else "전체"
    url = FEEDS[category]

    try:
        text = fetch_text(url, timeout=12)

        if category == "유튜브":
            data = parse_youtube_atom(text)
        elif category == "웃긴대학":
            data = parse_humoruniv(text)
        elif category == "보배드림":
            data = parse_bobaedream(text)
        else:
            data = parse_google_rss(text, category)

        if not data:
            return fallback_data(category, "목록 추출 실패")

        return data

    except Exception as e:
        return fallback_data(category, str(e))


@app.get("/debug-humor")
def debug_humor():
    text = fetch_text(FEEDS["웃긴대학"], timeout=12)
    return {"snippet": text[:3000]}


@app.get("/debug-bobae")
def debug_bobae():
    text = fetch_text(FEEDS["보배드림"], timeout=12)
    return {"snippet": text[:3000]}


@app.get("/debug-youtube")
def debug_youtube():
    text = fetch_text(FEEDS["유튜브"], timeout=12)
    return {"snippet": text[:1500]}
