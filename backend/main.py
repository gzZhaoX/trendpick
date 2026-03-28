from fastapi import FastAPI
import requests
from collections import Counter
import re

app = FastAPI()

@app.get("/trends")
def get_trends():
    try:
        url = "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko"
        res = requests.get(url)
res.encoding = 'utf-8'
text = res.text

words = re.findall(r"[가-힣]{2,}", text)
        counter = Counter(words)

        data = []
        for i, (word, _) in enumerate(counter.most_common(20)):
            data.append({
                "keyword": word,
                "rank": i + 1,
                "delta": 0,
                "category": "일반",
                "summary": "뉴스에서 많이 언급된 키워드입니다."
            })

        return data

    except:
        return [{"keyword": "데이터 없음", "rank": 1, "delta": 0, "category": "기타", "summary": "오류 발생"}]
