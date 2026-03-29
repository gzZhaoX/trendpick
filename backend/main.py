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

# 데이터 소스 정의
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
            url = "https://www.nate.com/js/data/keywordList.js"
            res = requests.get(url, timeout=5)
            # 네이트 특유의 인코딩(EUC-KR) 강제 설정
            res.encoding = 'euc-kr' 
            content = res.text
            # 키워드 추출용 정규식
            matches = re.findall(r"\[\d+,\s*\"(.*?)\"", content)
            
            return [{
                "keyword": k, "rank": i, "category": "네이트",
                "summary": f"네이트 실시간 이슈: {k}",
                "link": f"https://search.daum.net/search?q={k}"
            } for i, k in enumerate(matches[:10], start=1)]
        except:
            return []

    # 2. 구글/유튜브/커뮤니티 처리
    url = CATEGORY_FEEDS.get(category, CATEGORY_FEEDS["전체"])
    try:
        # 차단 방지를 위한 User-Agent 추가
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=8)
        root = ET.fromstring(res.content)
        
        result = []
        # 유튜브(Atom 형식)와 일반 RSS 형식 구분
        is_youtube = "youtube" in url
        items = root.findall(".//{http://www.w3.org/2005/Atom}entry") if is_youtube else root.findall(".//item")
        
        for i, item in enumerate(items[:20], start=1):
            title = ""
            link = ""
            
            if is_youtube:
                title = item.findtext("{http://www.w3.org/2005/Atom}title", "제목 없음")
                link_tag = item.find("{http://www.w3.org/2005/Atom}link")
                link = link_tag.get("href") if link_tag is not None else ""
            else:
                title = item.findtext("title", "제목 없음").split(" - ")[0]
                link = item.findtext("link", "")

            result.append({
                "keyword": title.strip(),
                "rank": i,
                "category": category,
                "summary": title.strip(),
                "link": link
            })
        return result
    except:
        return []
