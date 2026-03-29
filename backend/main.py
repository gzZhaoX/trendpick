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

FEEDS = {
    "전체": "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko",
    "정치": "https://news.google.com/rss/headlines/section/topic/POLITICS?hl=ko&gl=KR&ceid=KR:ko",
    "경제": "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=ko&gl=KR&ceid=KR:ko",
    "스포츠": "https://news.google.com/rss/headlines/section/topic/SPORTS?hl=ko&gl=KR&ceid=KR:ko",
    "연예": "https://news.google.com/rss/search?q=연예 OR 배우 OR 가수&hl=ko&gl=KR&ceid=KR:ko",
    "게임": "https://news.google.com/rss/search?q=게임 OR 스팀 OR 닌텐도&hl=ko&gl=KR&ceid=KR:ko",
    "유튜브": "https://www.youtube.com/feeds/videos.xml?chart=mostPopular&regionCode=KR",
    "웃긴대학": "http://rss.humoruniv.com/rss/best.xml",
    "보배드림": "https://m.bobaedream.co.kr/board/bbs/best/rss",
    "네이트": "https://www.nate.com/js/data/keywordList.js"
}

@app.get("/trends")
def get_trends(category: str = "전체"):
    url = FEEDS.get(category, FEEDS["전체"])
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}

    try:
        # 1. 네이트 전용 (가장 단순한 방식으로 추출)
        if category == "네이트":
            res = requests.get(url, timeout=5)
            res.encoding = 'euc-kr'
            keywords = re.findall(r'"([^"]+)"', res.text) # 모든 따옴표 안의 글자 추출
            # 순위 데이터만 필터링 (한글이 포함된 2글자 이상 키워드)
            result = []
            rank = 1
            for k in keywords:
                if re.search('[가-힣]', k) and len(k) >= 2 and k != "up" and k != "down":
                    result.append({"keyword": k, "rank": rank, "category": "네이트", "link": f"https://search.daum.net/search?q={k}"})
                    rank += 1
                    if rank > 10: break
            return result

        # 2. RSS (유튜브, 구글, 커뮤니티) - 무조건 파싱하는 방식
        res = requests.get(url, headers=headers, timeout=10)
        # XML 이름표(Namespace)를 싹 지워서 파싱 에러 방지
        xml_content = re.sub(r'\sxmlns="[^"]+"', '', res.text)
        xml_content = re.sub(r'\sxmlns:[^=]+="[^"]+"', '', xml_content)
        root = ET.fromstring(xml_content.encode('utf-8'))
        
        items = []
        # 'item' 태그나 'entry' 태그를 모두 찾음
        for node in root.findall(".//item") or root.findall(".//entry"):
            title = node.findtext("title", "").split(" - ")[0].strip()
            # 링크 찾기 (유튜브는 link 태그의 href 속성, RSS는 link 태그의 텍스트)
            link = ""
            link_node = node.find("link")
            if link_node is not None:
                link = link_node.get("href") or link_node.text or ""
            
            if title:
                items.append({"title": title, "link": link})

        return [{
            "keyword": item["title"],
            "rank": i,
            "category": category,
            "link": item["link"]
        } for i, item in enumerate(items[:20], start=1)]

    except Exception as e:
        return [{"keyword": f"{category} 로딩 실패", "rank": "!", "category": "Error", "link": "#"}]
