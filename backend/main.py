import re
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
    "네이트": "https://www.nate.com/"
}


def fetch_response(url: str, timeout: int = 10):
    res = requests.get(url, headers=HEADERS, timeout=timeout)
    res.raise_for_status()
    return res


def fetch_text(url: str, timeout: int = 10) -> str:
    res = fetch_response(url, timeout=timeout)
    return res.text


def strip_namespaces(xml_text: str) -> str:
    return re.sub(r'\sxmlns(:\w+)?="[^"]+"', '', xml_text)


def normalize_title(title: str) -> str:
    title = (title or "").strip()
    if " - " in title:
        title = title.split(" - ")[0].strip()
    return title


def parse_rss(xml_text: str, category: str):
    xml_text = strip_namespaces(xml_text)
    root = ET.fromstring(xml_text.encode("utf-8"))

    items = []
    for i, node in enumerate(root.findall(".//item")[:20]):
        title = normalize_title(node.findtext("title") or "")
        link = (node.findtext("link") or "").strip()

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


def strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;|&#160;", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def parse_nate_homepage(html_text: str):
    text = html_text

    # "실시간 이슈 키워드" 섹션 근처만 잘라서 사용
    marker = "실시간 이슈 키워드"
    start = text.find(marker)
    if start == -1:
        raise HTTPException(status_code=502, detail="네이트 실시간 이슈 키워드 섹션을 찾지 못했습니다.")

    sliced = text[start:start + 5000]

    # 숫자 순위 + 키워드 패턴 추출
    # 예: 1. 6 프리지아 갤럭시 유저 상승 29
    pattern = re.findall(r'>\s*(\d+)\.\s*(?:\d+\s+)?([^<]+?)\s*(?:상승|하락|new|동일)', sliced, flags=re.I)

    results = []
    seen = set()

    for _, raw_keyword in pattern:
        keyword = strip_html(raw_keyword)
        keyword = re.sub(r"\s+", " ", keyword).strip()

        if not keyword or len(keyword) < 2:
            continue
        if keyword in seen:
            continue

        seen.add(keyword)
        results.append({
            "keyword": keyword,
            "rank": len(results) + 1,
            "category": "네이트",
            "link": f"https://search.nate.com/search/all.html?q={requests.utils.quote(keyword)}"
        })

        if len(results) >= 10:
            break

    # 혹시 위 패턴이 안 맞으면 예비 패턴
    if not results:
        fallback = re.findall(r'실시간 이슈 키워드.*?(?:<li[^>]*>.*?</li>){1,15}', sliced, flags=re.S)
        if fallback:
            block = fallback[0]
            li_texts = re.findall(r'<li[^>]*>(.*?)</li>', block, flags=re.S)
            for li in li_texts:
                cleaned = strip_html(li)
                cleaned = re.sub(r'^\d+\s*', '', cleaned)
                cleaned = re.sub(r'\b(상승|하락|new|동일)\b.*$', '', cleaned, flags=re.I).strip()

                if not cleaned or len(cleaned) < 2:
                    continue
                if cleaned in seen:
                    continue

                seen.add(cleaned)
                results.append({
                    "keyword": cleaned,
                    "rank": len(results) + 1,
                    "category": "네이트",
                    "link": f"https://search.nate.com/search/all.html?q={requests.utils.quote(cleaned)}"
                })

                if len(results) >= 10:
                    break

    if not results:
        raise HTTPException(status_code=502, detail="네이트 키워드를 추출하지 못했습니다.")

    return results


@app.get("/trends")
def get_trends(category: str = Query(default="전체")):
    category = category if category in FEEDS else "전체"
    url = FEEDS[category]

    try:
        if category == "네이트":
            html_text = fetch_text(url, timeout=10)
            data = parse_nate_homepage(html_text)
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
    html_text = fetch_text(FEEDS["네이트"], timeout=10)
    marker = "실시간 이슈 키워드"
    start = html_text.find(marker)
    snippet = html_text[start:start + 3000] if start != -1 else html_text[:3000]
    return {
        "found_marker": start != -1,
        "snippet": snippet
    }
