from fastapi import FastAPI
from fastapi.responses import JSONResponse
import requests
from collections import Counter
import re

app = FastAPI()


@app.get("/")
def root():
    return {"status": "ok", "message": "trendpick api is live"}


@app.get("/trends")
def get_trends():
    try:
        url = "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko"
        res = requests.get(url, timeout=10)

        text = res.content.decode("utf-8", errors="ignore")
        words = re.findall(r"[가-힣]{2,}", text)
        counter = Counter(words)

        data = []
        blocked_words = {
            "기자", "뉴스", "오늘", "오후", "오전", "영상", "사진",
            "속보", "단독", "관련", "구독", "채널", "라이브"
        }

        rank = 1
        for word, _ in counter.most_common(100):
            if word in blocked_words:
                continue

            data.append({
                "keyword": word,
                "rank": rank,
                "delta": 0,
                "category": "일반",
                "summary": "뉴스에서 많이 언급된 키워드입니다."
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

        return JSONResponse(content=data, media_type="application/json; charset=utf-8")

    except Exception:
        return JSONResponse(
            content=[{
                "keyword": "데이터 없음",
                "rank": 1,
                "delta": 0,
                "category": "기타",
                "summary": "오류 발생"
            }],
            media_type="application/json; charset=utf-8"
        )
