/**
 * 트렌드픽 2.0 - 통합 이슈 대시보드
 * 구글 뉴스, 네이트 실검, 유튜브 인기, 커뮤니티(웃대/보배) 통합
 */

const PROXY_URL = "https://api.allorigins.win/get?url=";

// 1. 데이터 소스 설정
const SOURCES = {
  google: {
    name: "구글 뉴스",
    url: "https://news.google.com/rss/search?q=주요뉴스&hl=ko&gl=KR&ceid=KR:ko",
    type: "rss"
  },
  nate: {
    name: "네이트 실검",
    url: "https://www.nate.com/js/data/keywordList.js",
    type: "nate"
  },
  youtube: {
    name: "유튜브 인기",
    url: "https://www.youtube.com/feeds/videos.xml?chart=mostPopular&regionCode=KR",
    type: "rss-yt"
  },
  humor: {
    name: "웃긴대학",
    url: "http://rss.humoruniv.com/rss/best.xml",
    type: "rss"
  },
  bobae: {
    name: "보배드림",
    url: "https://m.bobaedream.co.kr/board/bbs/best/rss",
    type: "rss"
  }
};

let currentSource = 'google';
let allData = []; // 현재 불러온 전체 데이터 저장 (검색용)

// 2. 초기화 및 이벤트 바인딩
document.addEventListener('DOMContentLoaded', () => {
  renderTabs();
  loadData(currentSource);

  // 새로고침 버튼
  document.getElementById('refreshBtn').addEventListener('click', () => loadData(currentSource));
  
  // 검색 기능
  document.getElementById('searchInput').addEventListener('input', (e) => {
    filterData(e.target.value);
  });

  // 상세창 닫기
  document.getElementById('closeDetailBtn').addEventListener('click', closeDetail);
  document.getElementById('sheetBackdrop').addEventListener('click', closeDetail);
});

// 3. 카테고리 탭 생성
function renderTabs() {
  const container = document.getElementById('categoryTabs');
  container.innerHTML = Object.keys(SOURCES).map(key => `
    <button class="action-btn ${currentSource === key ? 'active' : ''}" 
            onclick="switchSource('${key}')" 
            style="flex: 0 0 auto; ${currentSource === key ? 'background:#f5f7fb; color:#0f1115;' : ''}">
      ${SOURCES[key].name}
    </button>
  `).join('');
}

// 4. 소스 전환
function switchSource(sourceKey) {
  currentSource = sourceKey;
  renderTabs();
  loadData(sourceKey);
}

// 5. 데이터 불러오기 핵심 로직
async function loadData(sourceKey) {
  const source = SOURCES[sourceKey];
  const trendList = document.getElementById('trendList');
  const sourceState = document.getElementById('sourceState');
  const updatedAt = document.getElementById('updatedAt');

  trendList.innerHTML = '<p style="padding:20px; text-align:center; color:#9aa3b2;">데이터를 낚아올리는 중...</p>';
  sourceState.innerText = "서버 연결 중...";

  try {
    const response = await fetch(PROXY_URL + encodeURIComponent(source.url));
    const json = await response.json();
    const parser = new DOMParser();
    allData = [];

    if (source.type === 'rss' || source.type === 'rss-yt') {
      const xml = parser.parseFromString(json.contents, "text/xml");
      const items = xml.querySelectorAll(source.type === 'rss-yt' ? "entry" : "item");

      items.forEach((item, idx) => {
        allData.push({
          rank: idx + 1,
          title: item.querySelector("title").textContent,
          link: source.type === 'rss-yt' ? item.querySelector("link").getAttribute("href") : item.querySelector("link").textContent,
          summary: item.querySelector("description") ? item.querySelector("description").textContent : "내용 요약 없음",
          source: source.name
        });
      });
    } else if (source.type === 'nate') {
      // 네이트 실검 파싱 (특수 케이스)
      const content = json.contents;
      const regex = /\["(.*?)",/g;
      let match;
      let idx = 1;
      while ((match = regex.exec(content)) !== null) {
        if (idx > 10) break;
        allData.push({
          rank: idx++,
          title: match[1],
          link: `https://search.daum.net/search?w=tot&q=${encodeURIComponent(match[1])}`,
          summary: "현재 네이트 인기 검색어입니다.",
          source: "네이트"
        });
      }
    }

    renderList(allData);
    sourceState.innerText = "실시간 서버 데이터";
    updatedAt.innerText = new Date().toLocaleString('ko-KR', { hour12: true });

  } catch (error) {
    console.error(error);
    sourceState.innerText = "오프라인 (데이터 로드 실패)";
    trendList.innerHTML = '<p style="padding:20px; text-align:center;">데이터를 불러오지 못했습니다. 😢</p>';
  }
}

// 6. 리스트 화면에 그리기
function renderList(data) {
  const container = document.getElementById('trendList');
  container.innerHTML = data.map(item => `
    <div class="trend-item" style="margin-bottom:12px; cursor:pointer;" onclick="openDetail(${JSON.stringify(item).replace(/"/g, '&quot;')})">
      <div style="display:flex; align-items:center; gap:15px;">
        <div style="font-size:20px; font-weight:900; color:#9aa3b2; width:24px;">${item.rank}</div>
        <div style="flex:1;">
          <div style="font-size:18px; font-weight:700; margin-bottom:4px;">${item.title}</div>
          <div style="font-size:14px; color:#9aa3b2;">${item.source}</div>
        </div>
      </div>
    </div>
  `).join('');
}

// 7. 검색 필터
function filterData(query) {
  const filtered = allData.filter(item => item.title.includes(query));
  renderList(filtered);
}

// 8. 상세 시트 열기/닫기
function openDetail(item) {
  document.getElementById('detailRank').innerText = `#${item.rank} - ${item.source}`;
  document.getElementById('detailKeyword').innerText = item.title;
  document.getElementById('detailSummary').innerHTML = item.summary;
  
  const linkContainer = document.getElementById('detailLinks');
  linkContainer.innerHTML = `<button class="action-btn" style="width:100%;" onclick="window.open('${item.link}', '_blank')">원본 바로가기</button>`;

  document.getElementById('sheetBackdrop').classList.remove('hidden');
  document.getElementById('detailSheet').classList.remove('hidden');
}

function closeDetail() {
  document.getElementById('sheetBackdrop').classList.add('hidden');
  document.getElementById('detailSheet').classList.add('hidden');
}
