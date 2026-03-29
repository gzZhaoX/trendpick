/**
 * 트렌드픽 2.0 - 렌더(Render) 서버 연동 버전
 */

// 1. 사용자님의 전용 서버 주소 세팅
const RENDER_SERVER = "https://trendpick-api.onrender.com";

const SOURCES = {
  google: { name: "구글 뉴스", url: "https://news.google.com/rss/search?q=주요뉴스&hl=ko&gl=KR&ceid=KR:ko", type: "rss" },
  nate: { name: "네이트 실검", url: "https://www.nate.com/js/data/keywordList.js", type: "nate" },
  youtube: { name: "유튜브 인기", url: "https://www.youtube.com/feeds/videos.xml?chart=mostPopular&regionCode=KR", type: "rss-yt" },
  humor: { name: "웃긴대학", url: "http://rss.humoruniv.com/rss/best.xml", type: "rss" },
  bobae: { name: "보배드림", url: "https://m.bobaedream.co.kr/board/bbs/best/rss", type: "rss" }
};

let currentSource = 'google';
let allData = []; 
let favorites = JSON.parse(localStorage.getItem('trendPickFavs')) || [];

document.addEventListener('DOMContentLoaded', () => {
  renderTabs();
  loadData(currentSource);
  
  // 버튼 바인딩
  document.getElementById('refreshBtn').onclick = () => loadData(currentSource);
  document.getElementById('searchInput').oninput = (e) => filterData(e.target.value);
  document.getElementById('closeDetailBtn').onclick = closeDetail;
  document.getElementById('sheetBackdrop').onclick = closeDetail;
  document.getElementById('showFavoritesBtn').onclick = openFavorites;
  document.getElementById('closeFavoritesBtn').onclick = closeFavorites;
  document.getElementById('favoritesBackdrop').onclick = closeFavorites;
});

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

function switchSource(sourceKey) {
  currentSource = sourceKey;
  renderTabs();
  loadData(sourceKey);
}

async function loadData(sourceKey) {
  const source = SOURCES[sourceKey];
  const trendList = document.getElementById('trendList');
  const sourceState = document.getElementById('sourceState');
  const updatedAt = document.getElementById('updatedAt');

  // 서버가 깨어나는 중일 수 있음을 알림
  trendList.innerHTML = `
    <div style="padding:40px; text-align:center; color:#9aa3b2;">
      <p>전용 서버에서 데이터를 가져오는 중...</p>
      <p style="font-size:12px; margin-top:10px;">(무료 서버라 첫 로딩은 최대 1분 정도 걸릴 수 있습니다)</p>
    </div>`;
  sourceState.innerText = "서버 호출 중...";

  try {
    // 💡 렌더 서버에 데이터를 요청합니다. 
    // 쳇지피티가 만든 main.py가 프록시 역할을 한다고 가정하고 url을 파라미터로 보냅니다.
    const response = await fetch(`${RENDER_SERVER}/proxy?url=${encodeURIComponent(source.url)}`);
    
    if (!response.ok) throw new Error('Server Busy');

    const rawData = await response.text();
    const parser = new DOMParser();
    allData = [];

    // 데이터 파싱 로직 (기존과 동일)
    if (source.type === 'rss' || source.type === 'rss-yt') {
      const xml = parser.parseFromString(rawData, "text/xml");
      const items = xml.querySelectorAll(source.type === 'rss-yt' ? "entry" : "item");
      items.forEach((item, idx) => {
        allData.push({
          rank: idx + 1,
          title: item.querySelector("title")?.textContent || "제목 없음",
          link: source.type === 'rss-yt' ? item.querySelector("link")?.getAttribute("href") : item.querySelector("link")?.textContent,
          summary: "터치하여 상세 내용을 확인하세요.",
          source: source.name
        });
      });
    } else if (source.type === 'nate') {
      const matches = rawData.match(/\[\d+,\s*"(.*?)"/g);
      if (matches) {
        matches.slice(0, 10).forEach((m, idx) => {
          const keyword = m.match(/"(.*?)"/)[1];
          allData.push({ rank: idx + 1, title: keyword, link: `https://search.daum.net/search?w=tot&q=${encodeURIComponent(keyword)}`, summary: "네이트 인기 검색어", source: "네이트" });
        });
      }
    }

    renderList(allData);
    sourceState.innerText = "전용 서버 수신 성공";
    updatedAt.innerText = new Date().toLocaleTimeString();

  } catch (error) {
    console.error(error);
    sourceState.innerText = "서버 대기 중 (재시도 필요)";
    trendList.innerHTML = `
      <div style="padding:40px; text-align:center;">
        <p>서버가 아직 자고 있는 것 같아요. 😴</p>
        <button onclick="loadData('${sourceKey}')" class="action-btn" style="margin-top:15px;">서버 깨우기 (재시도)</button>
      </div>`;
  }
}

function renderList(data) {
  const container = document.getElementById('trendList');
  container.innerHTML = data.map((item, index) => `
    <div class="trend-item" style="margin-bottom:12px; cursor:pointer;" onclick="openDetailByIndex(${index})">
      <div style="display:flex; align-items:center; gap:15px;">
        <div style="font-size:20px; font-weight:900; color:#9aa3b2; width:28px;">${item.rank}</div>
        <div style="flex:1;">
          <div style="font-size:18px; font-weight:700; margin-bottom:4px;">${item.title}</div>
          <div style="font-size:13px; color:#9aa3b2;">${item.source}</div>
        </div>
      </div>
    </div>
  `).join('');
}

function openDetailByIndex(index) {
  const item = allData[index];
  document.getElementById('detailKeyword').innerText = item.title;
  document.getElementById('detailSummary').innerText = item.summary;
  document.getElementById('detailLinks').innerHTML = `<button class="action-btn" style="width:100%;" onclick="window.open('${item.link}', '_blank')">원본 열기</button>`;
  document.getElementById('sheetBackdrop').classList.remove('hidden');
  document.getElementById('detailSheet').classList.remove('hidden');
}

function closeDetail() {
  document.getElementById('sheetBackdrop').classList.add('hidden');
  document.getElementById('detailSheet').classList.add('hidden');
}

function openFavorites() { /* 위와 동일 */ }
function closeFavorites() { /* 위와 동일 */ }
function filterData(query) { /* 위와 동일 */ }
