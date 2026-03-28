from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import requests
import xml.etree.ElementTree as ET
import re
from collections import Counter, defaultdict

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# RSS 소스
# =========================
CATEGORY_FEEDS = {
    "전체": "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko",
    "정치": "https://news.google.com/rss/headlines/section/topic/POLITICS?hl=ko&gl=KR&ceid=KR:ko",
    "경제": "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=ko&gl=KR&ceid=KR:ko",
    "스포츠": "https://news.google.com/rss/headlines/section/topic/SPORTS?hl=ko&gl=KR&ceid=KR:ko",
    "연예": "https://news.google.com/rss/search?q=연예 OR 배우 OR 가수 OR 드라마 OR 영화&hl=ko&gl=KR&ceid=KR:ko",
    "게임": "https://news.google.com/rss/search?q=게임 OR 스팀 OR 닌텐도 OR 플레이스테이션 OR 배그&hl=ko&gl=KR&ceid=KR:ko",
}

# =========================
# 제거할 단어
# =========================
STOPWORDS = {
    "뉴스", "속보", "단독", "영상", "사진", "기자", "앵커",
    "오늘", "오후", "오전", "관련", "대한", "통해", "위해",
    "정부", "한국", "미국", "중국", "일본", "국내", "해외",
    "사람", "경우", "상황", "결과", "현장", "논란", "이슈",
    "발표", "공개", "확인", "진행", "예정", "종합",
    "조선일보", "연합뉴스", "뉴시스", "중앙일보", "동아일보",
    "한겨레", "경향신문", "한국경제", "매일경제", "서울신문",
    "머니투데이", "이데일리", "아시아경제", "노컷뉴스",
    "문화일보", "뉴스1", "KBS", "MBC", "SBS", "JTBC", "YTN",
    "게임", "출시", "업데이트", "화제", "관심", "보도", "기사",
    "서비스", "기획", "특집", "현장", "포토", "사진", "그래픽"
}

BANNED = {
    "결국", "만에", "가운데", "이번", "최근", "현재",
    "가능성", "위험", "우려", "세계", "대한민국",
    "100만", "1위", "10", "20", "3", "4", "5",
    "포토", "PC방", "서비스", "사진", "현장", "기획", "특집",
    "속보", "게임에", "출시에", "관련해", "대한", "통한",
    "문제", "소식", "화제", "관심", "보도", "기사"
}

# 뒤에서 골라도 버릴 단어
WEAK_WORDS = {
    "포토", "PC방", "게임", "서비스", "사진", "현장", "특집",
    "기획", "속보", "관련", "문제", "소식", "화제", "관심"
}

CATEGORY_HINTS = {
    "정치": {"대통령", "국회", "정부", "총리", "장관", "여당", "야당", "외교", "선거"},
    "경제": {"환율", "주가", "증시", "금리", "달러", "유가", "코스피", "코스닥", "반도체"},
    "스포츠": {"축구", "야구", "농구", "배구", "골프", "리그", "챔피언스리그", "손흥민", "이강인"},
    "연예": {"배우", "가수", "드라마", "영화", "아이돌", "예능", "공연", "앨범", "컴백"},
    "게임": {"게임", "배그", "스팀", "닌텐도", "플레이스테이션", "위메이드", "넥슨", "엔씨", "크래프톤", "패치"},
}

# =========================
# 문장/단어 처리
# =========================
def clean_title(title: str) -> str:
    return title.split(" - ")[0].strip()

def clean_word(word: str) -> str:
    word = re.sub(r"[^\w가-힣]", "", word)
    word = re.sub(
        r"(에서|으로|에게|까지|부터|처럼|보다|이다|였다|했다|된다|하고|하며|이라|라며|라는|에서의|에게서|에는|으로는|은|는|이|가|을|를|에|의)$",
        "",
        word
    )
    return word

def extract_keyword(title: str):
    title = clean_title(title)
    words = title.split()

    candidates = []
    for w in words:
        w = clean_word(w)

        if len(w) < 2:
            continue
        if w in STOPWORDS or w in BANNED:
            continue
        if w.isdigit():
            continue
        if re.fullmatch(r"\d+만", w):
            continue

        candidates.append(w)

    if not candidates:
        return None

    # 뒤쪽 단어 우선: 앞쪽엔 [포토], 카테고리명, 일반 단어가 많음
    for w in reversed(candidates):
        if w not in WEAK_WORDS:
            return w

    return candidates[-1]

def detect_category(title: str, requested_category: str):
    if requested_category != "전체":
        return requested_category

    for category, hints in CATEGORY_HINTS.items():
        for hint in hints:
            if hint in title:
                return category
    return "일반"

def make_summary(keyword: str, title: str):
    title = clean_title(title)

    if len(title) > 60:
        title = title[:60] + "..."

    if keyword in {"환율", "주가", "증시", "금리", "달러", "유가"}:
        return f"{title} 영향으로 관심이 커지고 있습니다."

    if keyword in {"대통령", "국회", "정부", "총리", "장관", "외교", "선거"}:
        return f"{title} 보도로 많이 언급되고 있습니다."

    if keyword in {"축구", "야구", "농구", "배구", "골프", "손흥민", "이강인", "챔피언스리그"}:
        return f"{title} 소식으로 관심이 높아지고 있습니다."

    if keyword in {"배우", "가수", "드라마", "영화", "아이돌", "컴백"}:
        return f"{title} 화제로 주목받고 있습니다."

    if keyword in {"위메이드", "스팀", "닌텐도", "플레이스테이션", "넥슨", "엔씨", "크래프톤", "배그"}:
        return f"{title} 소식으로 관심이 커지고 있습니다."

    return f"{title} 보도로 관심이 커지고 있습니다."

# =========================
# API
# =========================
@app.get("/")
def root():
    return {"status": "ok", "message": "trendpick api is live"}

@app.get("/trends")
def trends(category: str = Query("전체"), limit: int = Query(20)):
    url = CATEGORY_FEEDS.get(category, CATEGORY_FEEDS["전체"])

    res = requests.get(url, timeout=12)
    root = ET.fromstring(res.content)

    counter = Counter()
    titles_map = defaultdict(list)
    links_map = defaultdict(list)

    for item in root.findall(".//item"):
        title = item.findtext("title", "") or ""
        link = item.findtext("link", "") or ""

        keyword = extract_keyword(title)
        if not keyword:
            continue

        counter[keyword] += 1
        titles_map[keyword].append(title)

        if link:
            links_map[keyword].append({
                "title": clean_title(title),
                "url": link,
                "source": "Google News"
            })

    result = []
    ranked_items = counter.most_common(50)

    prev_count = None

    for i, (keyword, count) in enumerate(ranked_items, start=1):
        if i > limit:
            break

        title = titles_map[keyword][0]
        delta = 0 if prev_count is None else max(0, prev_count - count)
        prev_count = count

        result.append({
            "keyword": keyword,
            "rank": i,
            "delta": delta,
            "category": detect_category(title, category),
            "summary": make_summary(keyword, title),
            "headlines": [clean_title(t) for t in titles_map[keyword][:3]],
            "links": links_map[keyword][:5]
        })

    if not result:
        result = [{
            "keyword": "데이터 없음",
            "rank": 1,
            "delta": 0,
            "category": "일반",
            "summary": "표시할 키워드가 없습니다.",
            "headlines": [],
            "links": []
        }]

    return result
