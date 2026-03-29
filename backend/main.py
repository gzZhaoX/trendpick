from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import requests
import xml.etree.ElementTree as ET
import re

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
    "연예": "https://news.google.com/rss/search?q=연예 OR 배우 OR 가수 OR 드라마&hl=ko&gl=KR&ceid=KR:ko",
    "게임": "https://news.google.com/rss/search?q=게임 OR 배그 OR 스팀 OR 닌텐도&hl=ko&gl=KR&ceid=KR:ko",
    "유튜브": "https://www.youtube.com/feeds/videos.xml?chart=mostPopular&regionCode=KR",
    "웃긴대학": "http://rss.humoruniv.com/rss/best.xml",
    "보배드림": "https://m.bobaedream.co.kr/board/bbs/best/rss"
}

@app.get("/trends")
def trends(category: str = Query("전체")):
    # 1. 네이트 실검 처리
    if category == "네이트":
        try:
            res = requests.get("https://www.nate.com/js/data/keywordList.js", timeout=5)
            res.encoding = 'euc-kr'
            matches = re.findall(r"\[\d+,\s*\"(.*?)\"", res.text)
            return [{"keyword": k, "rank": i, "category": "네이트", "summary": k, "link": f"https://search.daum.net/search?q={k}"} for i, k in enumerate(matches[:10], start=1)]
        except: return []

    # 2. RSS 기반 처리
    url = CATEGORY_FEEDS.get(category, CATEGORY_FEEDS["전체"])
    try:
        # 💡 보배드림 등 해외 서버 차단 방지용 헤더 강화
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        }
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        
        # XML 파싱
        root = ET.fromstring(res.content)
        result = []
        is_yt = "youtube" in url
        
        # 유튜브(Atom)와 일반 RSS 아이템 찾기
        items = root.findall(".//{http://www.w3.org/2005/Atom}entry") if is_yt else root.findall(".//item")
        
        for i, item in enumerate(items[:20], start=1):
            title = item.findtext("{http://www.w3.org/2005/Atom}title") if is_yt else item.findtext("title")
            link = ""
            if is_yt:
                link_tag = item.find("{http://www.w3.org/2005/Atom}link")
                link = link_tag.get("href") if link_tag is not None else ""
            else:
                link = item.findtext("link")

            if title:
                result.append({
                    "keyword": title.split(" - ")[0].strip(),
                    "rank": i,
                    "category": category,
                    "summary": title.strip(),
                    "link": link
                })
        
        # 만약 데이터가 없으면 '샘플 데이터'라도 반환해서 작동 확인
        if not result:
            return [{"keyword": f"{category} 데이터를 가져오는 중...", "rank": 1, "category": category, "summary": "잠시 후 다시 시도해주세요", "link": "#"}]
            
        return result
    except Exception as e:
        print(f"Error: {e}")
        return [{"keyword": "데이터 연결 실패", "rank": "!", "category": category, "summary": str(e), "link": "#"}]
