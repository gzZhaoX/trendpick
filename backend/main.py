from fastapi import FastAPI
import requests
from collections import Counter
import re

app = FastAPI()

# ❌ 제거할 단어들 (핵심)
STOPWORDS = set([
    "뉴스", "속보", "단독", "영상", "사진", "기자",
    "연합뉴스", "뉴시스", "조선일보", "중앙일보", "동아일보",
    "한겨레", "경향신문", "한국경제", "매일경제", "서울신문",
    "머니투데이", "이데일리", "아시아경제",
    "오늘", "지금", "관련", "대한", "이란", "대한민국",
    "정부", "한국", "미국", "중국", "일본",
    "사람", "경우", "내용", "결과", "상황",
    "확인", "진행", "발표", "논란", "이슈"
])

@app.get("/trends")
def get_trends():
    try:
        url = "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko"
        res = requests.get(url)
        res.encoding = "utf-8"

        text = res.text

        # 한글 2글자 이상 추출
        words = re.findall(r"[가-힣]{2,}", text)

        # ❗ 필터링 (핵심)
        filtered = [
            w for w in words
            if w not in STOPWORDS
            and len(w) >= 2
        ]

        counter = Counter(filtered)

        data = []
        for i, (word, _) in enumerate(counter.most_common(20)):
            data.append({
                "keyword": word,
                "rank": i + 1,
                "delta": 0,
                "category": "일반",
                "summary": f"{word} 관련 뉴스 언급이 늘었습니다."
            })

        return data

    except:
        return [{
            "keyword": "데이터 없음",
            "rank": 1,
            "delta": 0,
            "category": "일반",
            "summary": "데이터를 불러오지 못했습니다."
        }]
