import requests
import xml.etree.ElementTree as ET
import re
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

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
        if category == "네이트":
            res = requests.get(url, timeout=5)
            res.encoding = 'euc-kr'
            # 네이트 키워드 패턴 추출
            raw_keywords = re.findall(r'\[\d+,\s*"([^"]+)"', res.text)
            return [{"keyword": k, "rank": i+1, "category": "네이트", "link": f"https://search.daum.net/search?q={k}"} for i, k in enumerate(raw_keywords[:10])]

        res = requests.get(url, headers=headers, timeout=10)
        text = res.text
        
        items = []
        try:
            # XML 이름표(Namespace) 강제 제거 (유튜브 해결 핵심)
            clean_xml = re.sub(r'\sxmlns="[^"]+"', '', text, count=1)
            root = ET.fromstring(clean_xml.encode('utf-8'))
            
            nodes = root.findall(".//entry") if "youtube" in url else root.findall(".//item")
            for i, node in enumerate(nodes[:20]):
                title = node.findtext("title", "").split(" - ")[0].strip()
                link = ""
                l_node = node.find("link")
                if l_node is not None:
                    link = l_node.get("href") or l_node.text or ""
                if title: items.append({"keyword": title, "link": link})
        except:
            # XML 파싱 실패 시 정규식으로 강제 추출 (최후의 보루)
            titles = re.findall(r'<title>(.*?)</title>', text)
            links = re.findall(r'<link>(.*?)</link>', text)
            for t, l in zip(titles[1:21], links[1:21]):
                clean_t = re.sub(r'<!\[CDATA\[|\]\]>', '', t).strip()
                if clean_t and category not in clean_t: # 채널명 제외
                    items.append({"keyword": clean_t, "link": l})

        if not items: 
            return [{"keyword": "데이터 없음 (차단 가능성)", "rank": "!", "category": "Error", "link": "#"}]
        
        return [{"keyword": it["keyword"], "rank": i+1, "category": category, "link": it["link"]} for i, it in enumerate(items)]

    except Exception as e:
        return [{"keyword": f"에러: {str(e)}", "rank": "X", "category": "Error", "link": "#"}]
