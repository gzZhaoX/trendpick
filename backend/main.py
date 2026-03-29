import requests
import xml.etree.ElementTree as ET
import re
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# 더 안정적인 URL로 교체
FEEDS = {
    "전체": "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko",
    "정치": "https://news.google.com/rss/headlines/section/topic/POLITICS?hl=ko&gl=KR&ceid=KR:ko",
    "경제": "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=ko&gl=KR&ceid=KR:ko",
    "스포츠": "https://news.google.com/rss/headlines/section/topic/SPORTS?hl=ko&gl=KR&ceid=KR:ko",
    "연예": "https://news.google.com/rss/search?q=연예 OR 배우 OR 가수&hl=ko&gl=KR&ceid=KR:ko",
    "게임": "https://news.google.com/rss/search?q=게임 OR 스팀 OR 닌텐도&hl=ko&gl=KR&ceid=KR:ko",
    "유튜브": "https://www.youtube.com/feeds/videos.xml?chart=mostPopular&regionCode=KR",
    "웃긴대학": "http://web.humoruniv.com/rss/best.xml", # 주소 업데이트
    "보배드림": "https://m.bobaedream.co.kr/board/bbs/best/rss",
    "네이트": "https://www.nate.com/js/data/keywordList.js"
}

@app.get("/trends")
def get_trends(category: str = "전체"):
    url = FEEDS.get(category, FEEDS["전체"])
    headers = {'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1'}
    
    try:
        if category == "네이트":
            res = requests.get(url, timeout=5)
            res.encoding = 'euc-kr'
            matches = re.findall(r'\"([^\"]+)\"', res.text)
            keywords = [k for k in matches if re.search('[가-힣]', k) and len(k) > 1][:10]
            return [{"keyword": k, "rank": i+1, "category": "네이트", "link": f"https://search.daum.net/search?q={k}"} for i, k in enumerate(keywords)]

        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        
        # XML 세척 (유튜브 등 네임스페이스 제거)
        clean_xml = re.sub(r'\sxmlns(:\w+)?="[^"]+"', '', res.text)
        root = ET.fromstring(clean_xml.encode('utf-8'))
        
        items = []
        nodes = root.findall(".//entry") if "youtube" in url else root.findall(".//item")
        
        for i, node in enumerate(nodes[:20]):
            title = node.findtext("title", "").split(" - ")[0].strip()
            link = ""
            l_node = node.find("link")
            if l_node is not None:
                link = l_node.get("href") or l_node.text or ""
            if title: items.append({"keyword": title, "rank": i+1, "category": category, "link": link})
            
        return items if items else [{"keyword": "Error", "message": "No Data"}]

    except Exception as e:
        # 에러 발생 시 프론트엔드가 프록시로 갈아탈 수 있도록 에러 신호를 보냄
        return {"error": str(e)}
