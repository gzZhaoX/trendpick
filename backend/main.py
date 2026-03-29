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
    "웃긴대학": "https://m.humoruniv.com/board/humor/list.html?table=pds",
    "보배드림": "https://m.bobaedream.co.kr/board/new_writing/nsfw"
}

CATEGORIES = list(FEEDS.keys())


def fetch(url: str) -> str:
    res = requests.get(url, headers=HEADERS, timeout=12)
    res.raise_for_status()

    if not res.encoding or res.encoding == "ISO-8859-1":
        res.encoding = res.apparent_encoding

    return res.text


def clean_text(text: str) -> str:
    text = html.unescape(text or "")
    text = re.sub(r"<br\\s*/?>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\\s+", " ", text)
    return text.strip()


def item(keyword: str, rank: int, category: str, link: str):
    return {
        "keyword": keyword,
        "rank": rank,
        "category": category,
        "link": link
    }


def fallback(category: str, msg: str = ""):
    text = f"{category} 데이터를 불러올 수 없습니다"
    if msg:
        text = f"{text} - {msg[:60]}"
    return [item(text, 1, category, "#")]


# ---------------------------
# Google RSS
# ---------------------------
def parse_rss(xml_text: str, category: str):
    root = ET.fromstring(xml_text)

    results = []
    for i, node in enumerate(root.findall(".//item")[:20]):
        title = (node.findtext("title") or "").strip()
        link = (node.findtext("link") or "").strip()

        if " - " in title:
            title = title.split(" - ")[0].strip()

        title = clean_text(title)
        if not title:
            continue

        results.append(item(title, i + 1, category, link))

    return results


# ---------------------------
# YouTube Atom
# ---------------------------
def parse_youtube(xml_text: str):
    root = ET.fromstring(xml_text)
    ns = {"atom": "http://www.w3.org/2005/Atom"}

    results = []
    entries = root.findall("atom:entry", ns)

    for i, entry in enumerate(entries[:20]):
        title = entry.findtext("atom:title", default="", namespaces=ns).strip()

        link = ""
        link_node = entry.find("atom:link", ns)
        if link_node is not None:
            link = (link_node.get("href") or "").strip()

        if not title:
            continue

        results.append(item(title, i + 1, "유튜브", link))

    return results


# ---------------------------
# Humoruniv
# ---------------------------
def parse_humoruniv(html_text: str):
    results = []
    seen = set()

    patterns = [
        r'href="(/board/humor/read\\.html\\?number=\\d+&table=pds[^"]*)".{0,500}?>(.*?)<',
        r'href="(/board/humor/read\\.html\\?number=\\d+&table=pds[^"]*)".{0,500}?title="([^"]+)"',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, html_text, flags=re.S | re.I)
        for href, raw_title in matches:
            title = clean_text(raw_title)

            if not title or len(title) < 2:
                continue
            if title in seen:
                continue
            if title in {"이전", "다음", "목록", "더보기"}:
                continue

            seen.add(title)
            results.append(
                item(
                    title,
                    len(results) + 1,
                    "웃긴대학",
                    f"https://m.humoruniv.com{href}"
                )
            )

            if len(results) >= 20:
                return results

    return results


# ---------------------------
# Bobaedream mobile "신유머/이슈/움짤"
# ---------------------------
def parse_bobaedream(html_text: str):
    results = []
    seen = set()

    patterns = [
        r'href="(/board/bbs_view/nsfw/\\d+[^"]*)".{0,500}?>(.*?)<',
        r'href="(/board/bbs_view/nsfw/\\d+[^"]*)".{0,500}?title="([^"]+)"',
        r'href="(https://m\\.bobaedream\\.co\\.kr/board/bbs_view/nsfw/\\d+[^"]*)".{0,500}?>(.*?)<'
    ]

    for pattern in patterns:
        matches = re.findall(pattern, html_text, flags=re.S | re.I)
        for href, raw_title in matches:
            title = clean_text(raw_title)

            if not title or len(title) < 2:
                continue
            if title in seen:
                continue
            if title in {"목록", "이전", "다음", "공지", "글쓰기"}:
                continue

            seen.add(title)

            if href.startswith("http"):
                full_link = href
            else:
                full_link = f"https://m.bobaedream.co.kr{href}"

            results.append(
                item(
                    title,
                    len(results) + 1,
                    "보배드림",
                    full_link
                )
            )

            if len(results) >= 20:
                return results

    return results


@app.get("/trends")
def get_trends(category: str = Query(default="전체")):
    category = category if category in CATEGORIES else "전체"

    try:
        text = fetch(FEEDS[category])

        if category == "유튜브":
            data = parse_youtube(text)
        elif category == "웃긴대학":
            data = parse_humoruniv(text)
        elif category == "보배드림":
            data = parse_bobaedream(text)
        else:
            data = parse_rss(text, category)

        if not data:
            return fallback(category, "목록 추출 실패")

        return data

    except Exception as e:
        return fallback(category, str(e))


@app.get("/debug-bobae")
def debug_bobae():
    text = fetch(FEEDS["보배드림"])
    return {"snippet": text[:3000]}
