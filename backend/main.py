from fastapi import FastAPI, Query, Body
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

# 데이터 소스 확장
CATEGORY_FEEDS = {
    "전체": "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko",
    "정치": "https://news.google.com/rss/headlines/section/topic/POLITICS?hl=ko&gl=KR&ceid=KR:ko",
    "경제": "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=ko&gl=KR&ceid=KR:ko",
    "스포츠": "https://news.google.com/rss/headlines/section/topic/SPORTS?hl=ko&gl=KR&ceid=KR:ko",
    "연예": "https://news.google.com/rss/search?q=연예 OR 배우 OR 가수 OR 드라마&hl=ko&gl=KR&ceid=KR:ko",
    "게임": "https://news.google.com/rss/search?q=게임 OR 배그 OR 스팀 OR 닌텐도&hl=ko&gl=KR&ceid=KR:ko",
    "유튜브": "https://www.youtube.com/feeds/videos.xml?chart=mostPopular&regionCode=KR",
    "웃긴대학": "http://rss.humoruniv.com/rss/best.xml",
    "보배드림": "https://m.bobaedream.co.kr/board/bbs/best/rss"
}

CACHE = {}
PREV_CACHE = {}
CACHE_TTL = 300 # 5분 캐시

VIEW_COUNTS = defaultdict(int)

def clean_title(title):
    return title.split(" - ")[0].strip()

def extract_main_keyword(title):
    words = re.findall(r"[가-힣A-Za-z0-9]{2,}", title)
    return words[0] if words else title[:5]

@app.get("/")
def root():
    return {"status": "ok", "message": "TrendPick API is running"}

@app.get("/trends")
def trends(category: str = Query("전체"), limit: int = Query(20)):
    # 1. 네이트 실검 처리 (특수 케이스)
    if category == "네이트":
        return get_nate_trends()

    # 2. 일반 RSS 처리 (구글, 유튜브, 커뮤니티)
    url = CATEGORY_FEEDS.get(category, CATEGORY_FEEDS["전체"])
    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        xml_data = ET.fromstring(res.content)
        
        result = []
        # 유튜브는 entry 태그, 나머지는 item 태그 사용
        items = xml_data.findall(".//entry") if "youtube" in url else xml_data.findall(".//item")
        
        for i, item in enumerate(items[:limit], start=1):
            title = item.findtext("title", "제목 없음")
            # 유튜브 링크와 일반 RSS 링크 방식이 다름
            link = ""
            if "youtube" in url:
                link_tag = item.find("{http://www.w3.org/2005/Atom}link")
                link = link_tag.get("href") if link_tag is not None else ""
            else:
                link = item.findtext("link", "")

            result.append({
                "keyword": clean_title(title),
                "rank": i,
                "category": category,
                "summary": title,
                "link": link,
                "views": VIEW_COUNTS.get(title, 0)
            })
        return result
    except Exception as e:
        return {"error": str(e)}

def get_nate_trends():
    url = "https://www.nate.com/js/data/keywordList.js"
    res = requests.get(url)
    content = res.content.decode('euc-kr') # 네이트는 euc-kr 사용
    matches = re.findall(r"\[\d+,\s*\"(.*?)\"", content)
    
    result = []
    for i, keyword in enumerate(matches[:10], start=1):
        result.append({
            "keyword": keyword,
            "rank": i,
            "category": "네이트",
            "summary": f"네이트 실시간 이슈: {keyword}",
            "link": f"https://search.daum.net/search?q={keyword}",
            "views": 0
        })
    return result
