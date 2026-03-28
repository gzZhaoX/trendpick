from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import requests
from collections import Counter
import xml.etree.ElementTree as ET

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"status": "ok", "message": "trendpick api is live"}


@app.get("/trends")
def get_trends():
    try:
        url = "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko"
        res = requests.get(url, timeout=10)
        res.raise_for_status()

        root = ET.fromstring(res.content)

        titles = []
        for item in root.findall(".//item"):
            title = item.findtext("title", default="")
            if title:
                titles.append(title)

        blocked_words = {
            "기자", "뉴스", "오늘", "오후", "오전", "영상", "사진",
            "속보", "단독", "관련", "구독", "채널", "라이브", "앵커",
            "정부", "대표", "한국", "대한민국", "조선일보", "연합뉴스",
            "노컷뉴스", "한겨레", "문화일보", "한국경제", "뉴시스",
            "서울신문", "동아일보", "중앙일보", "경향신문"
        }

        counter = Counter()

        for title in titles:
            parts = [p.strip() for p in title.split(" - ") if p.strip()]
            main_text = parts[0] if parts else title

            for token in main_text.split():
                word = token.strip("[](){}<>\"'“”‘’.,!?…:;|/\\")
                if len(word) < 2:
                    continue
                if word in blocked_words:
                    continue
                counter[word] += 1

        data = []
        rank = 1

        for word, _ in counter.most_common(100):
            data.append({
                "keyword": word,
                "rank": rank,
                "delta": 0,
                "category": "일반",
                "summary": f"{word} 관련 뉴스 언급이 늘었습니다."
            })
            rank += 1
            if rank > 20:
                break

        if not data:
            data = [{
                "keyword": "데이터 없음",
                "rank": 1,
                "delta": 0,
                "category": "기타",
                "summary": "표시할 키워드가 없습니다."
            }]

        return JSONResponse(content=data)

    except Exception as e:
        return JSONResponse(content=[{
            "keyword": "데이터 없음",
            "rank": 1,
            "delta": 0,
            "category": "기타",
            "summary": f"오류 발생: {str(e)}"
        }])
