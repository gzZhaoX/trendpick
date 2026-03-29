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

# PC 브라우저처럼 요청해야 네이트가 모바일로 안 튕김
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
    "웃긴대학": "https://web.humoruniv.com/rss/best.xml",
    "보배드림": "https://m.bobaedream.co.kr/board/bbs/best/rss",
    "네이트": "https://www.nate.com/"
}


def fetch_response(url: str, timeout: int = 10):
    response = requests.get(
        url,
        headers=HEADERS,
        timeout=timeout,
        allow_redirects=True
    )
    response.raise_for_status()
    return response


def fetch_text(url: str, timeout: int = 10) -> str:
    response = fetch_response(url, timeout=timeout)

    # 네이트 HTML은 cp949/euc-kr 계열일 가능성이 높아서 우선 시도
    for encoding in ("cp949", "euc-kr", "utf-8"):
        try:
            return response.content.decode(encoding)
        except Exception:
            continue

    return response.text


def strip_namespaces(xml_text: str) -> str:
    return re.sub(r'\sxmlns(:\w+)?="[^"]+"', '', xml_text)


def normalize_title(title: str) -> str:
    text = (title or "").strip()
    if " - " in text:
        text = text.split(" - ")[0].strip()
    return text


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
        link = ""
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


def strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;|&#160;", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def parse_nate_homepage(html_text: str):
    # 모바일 리다이렉트 감지
    if "location.href='http://m.nate.com/" in html_text or 'location.href="http://m.nate.com/' in html_text:
        raise HTTPException(status_code=502, detail="네이트가 모바일 페이지로 리다이렉트되었습니다.")

    marker = "실시간 이슈 키워드"
    start = html_text.find(marker)

    if start == -1:
        raise HTTPException(status_code=502, detail="네이트 실시간 이슈 키워드 영역을 찾지 못했습니다.")

    sliced = html_text[start:start + 15000]

    results = []
    seen = set()

    # 1차: 현재 네이트 구조 기준
    items = re.findall(
        r'<li>\s*<div class="slide-content">.*?<span class="num_rank">(\d+)</span>.*?'
        r'<a[^>]*?href="([^"]+)".*?<span class="txt_rank">(.+?)</span>.*?'
        r'<span class="fc\s+(?:up|down|same|new)">',
        sliced,
        flags=re.S | re.I
    )

    for _, href, raw_keyword in items:
        keyword = strip_html(raw_keyword)

        if not keyword or len(keyword) < 2:
            continue
        if keyword in seen:
            continue

        seen.add(keyword)

        full_link = href
        if full_link.startswith("/"):
            full_link = "https://www.nate.com" + full_link

        results.append({
            "keyword": keyword,
            "rank": len(results) + 1,
            "category": "네이트",
            "link": full_link
        })

        if len(results) >= 10:
            break

    # 2차 예비 패턴
    if not results:
        fallback = re.findall(
            r'<span class="num_rank">(\d+)</span>.*?<span class="txt_rank">(.+?)</span>',
            sliced,
            flags=re.S | re.I
        )

        for _, raw_keyword in fallback:
            keyword = strip_html(raw_keyword)

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
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"{category} 요청 실패: {str(e)}")
    except ET.ParseError as e:
        raise HTTPException(status_code=502, detail=f"{category} XML 파싱 실패: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"{category} 처리 실패: {str(e)}")


@app.get("/debug-nate")
def debug_nate():
    html_text = fetch_text(FEEDS["네이트"], timeout=10)
    marker = "실시간 이슈 키워드"
    start = html_text.find(marker)

    snippet = html_text[start:start + 3000] if start != -1 else html_text[:3000]

    return {
        "found_marker": start != -1,
        "final_url": FEEDS["네이트"],
        "snippet": snippet
    }
