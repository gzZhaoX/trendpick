/**
 * 트렌드픽 2.0 - 통합 이슈 대시보드 (최종 완성본)
 * 기능: 구글뉴스/네이트/유튜브/웃대/보배드림 통합 + 검색 + 즐겨찾기(로컬저장)
 */

const PROXY_URL = "https://api.allorigins.win/get?url=";

// 1. 데이터 소스 설정
const SOURCES = {
  google: { name: "구글 뉴스", url: "https://news.google.com/rss/search?q=주요뉴스&hl=ko&gl=KR&ceid=KR:ko", type: "rss" },
  nate: { name: "네이트 실검", url: "https://www.nate.com/js/data/keywordList.js", type: "nate" },
  youtube: { name: "유튜브 인기", url: "https://www.youtube.com/feeds/videos.xml?chart=mostPopular&regionCode=KR", type: "rss-yt" },
  humor: { name: "웃긴대학", url: "http://rss.humoruniv.com/rss/best.xml", type: "rss" },
  bobae: { name: "보배드림", url: "https://m.bobaedream.co.kr/board/bbs/best/rss", type: "rss" }
};

let currentSource = 'google';
let allData = []; 
let favorites = JSON.parse(localStorage.getItem('trendPickFavs')) || []; // 브라우저에 저장된 즐겨찾기 불러오기

// 2. 초기화
document.addEventListener('DOMContentLoaded', () => {
  renderTabs();
  loadData(currentSource);

  // 이벤트 리스너 바인딩
  document.getElementById('refreshBtn').addEventListener('click', () => loadData(currentSource));
  document.getElementById('searchInput').addEventListener('input', (e) => filterData(e.target.value));
  document.getElementById('closeDetailBtn').addEventListener('click', closeDetail);
  document.getElementById('sheetBackdrop').addEventListener('click', closeDetail);
  
  // 즐겨찾기 시트 관련
  document.getElementById('showFavoritesBtn').addEventListener('click', openFavorites);
  document.getElementById('closeFavoritesBtn').addEventListener('click', closeFavorites);
  document.getElementById('favoritesBackdrop').addEventListener('click', closeFavorites);
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

function switchSource(sourceKey) {
  currentSource = sourceKey;
  renderTabs();
  loadData(sourceKey);
}

// 4. 데이터 로드 (RSS / JSON / Special)
async function loadData(sourceKey) {
  const source = SOURCES[sourceKey];
  const trendList = document.getElementById('trendList');
  const sourceState = document.getElementById('sourceState');
  const updatedAt = document.getElementById('updatedAt');

  trendList.innerHTML = '<p style="padding:40px; text-align:center; color:#9aa3b2;">트렌드를 낚아올리는 중...</p>';
  sourceState.innerText = "데이터 연결 중...";

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
          id: Date.now() + idx, // 고유 ID
          rank: idx + 1,
          title: item.querySelector("title").textContent,
          link: source.type === 'rss-yt' ? item.querySelector("link").getAttribute("href") : item.querySelector("link").textContent,
          summary: item.querySelector("description") ? item.querySelector("description").textContent : "내용 요약 없음",
          source: source.name
        });
      });
    } else if (source.type === 'nate') {
      const regex = /\["(.*?)",/g;
      let match, idx = 1;
      while ((match = regex.exec(json.contents)) !== null && idx <= 10) {
        allData.push({
          id: Date.now() + idx,
          rank: idx++,
          title: match[1],
          link: `https://search.daum.net/search?w=tot&q=${encodeURIComponent(match[1])}`,
          summary: "네이트 실시간 인기 검색어입니다.",
          source: "네이트"
        });
      }
    }

    renderList(allData);
    sourceState.innerText = "실시간 서버 데이터";
    updatedAt.innerText = new Date().toLocaleString('ko-KR', { hour12: true });

  } catch (error) {
    sourceState.innerText = "로드 실패 (오프라인)";
    trendList.innerHTML = '<p style="padding:40px; text-align:center;">데이터를 불러오지 못했습니다. 😢</p>';
  }
}

// 5. 리스트 렌더링
function renderList(data) {
  const container = document.getElementById('trendList');
  if (data.length === 0) {
    container.innerHTML = '<p style="padding:20px; text-align:center; color:#9aa3b2;">검색 결과가 없습니다.</p>';
    return;
  }
  container.innerHTML = data.map(item => `
    <div class="trend-item" style="margin-bottom:12px; cursor:pointer;" onclick='openDetail(${JSON.stringify(item).replace(/'/g, "&apos;")})'>
      <div style="display:flex; align-items:center; gap:15px;">
        <div style="font-size:20px; font-weight:900; color:#9aa3b2; width:28px;">${item.rank}</div>
        <div style="flex:1;">
          <div style="font-size:18px; font-weight:700; margin-bottom:4px; line-height:1.4;">${item.title}</div>
          <div style="font-size:13px; color:#9aa3b2;">${item.source}</div>
        </div>
      </div>
    </div>
  `).join('');
}

// 6. 상세 시트 및 즐겨찾기 로직
let currentItem = null;

function openDetail(item) {
  currentItem = item;
  document.getElementById('detailRank').innerText = `#${item.rank} - ${item.source}`;
  document.getElementById('detailKeyword').innerText = item.title;
  document.getElementById('detailSummary').innerHTML = item.summary;
  
  // 즐겨찾기 버튼 텍스트 설정
  const isFav = favorites.some(f => f.link === item.link);
  document.getElementById('favoriteBtn').innerText = isFav ? "즐겨찾기 삭제" : "즐겨찾기 저장";
  document.getElementById('favoriteBtn').onclick = toggleFavorite;

  document.getElementById('detailLinks').innerHTML = `
    <button class="action-btn" style="width:100%; padding:16px;" onclick="window.open('${item.link}', '_blank')">원본 페이지 열기</button>
  `;

  document.getElementById('sheetBackdrop').classList.remove('hidden');
  document.getElementById('detailSheet').classList.remove('hidden');
}

function closeDetail() {
  document.getElementById('sheetBackdrop').classList.add('hidden');
  document.getElementById('detailSheet').classList.add('hidden');
}

// 즐겨찾기 토글 (추가/삭제)
function toggleFavorite() {
  const index = favorites.findIndex(f => f.link === currentItem.link);
  if (index > -1) {
    favorites.splice(index, 1);
    alert("즐겨찾기에서 삭제되었습니다.");
  } else {
    favorites.push(currentItem);
    alert("즐겨찾기에 저장되었습니다!");
  }
  localStorage.setItem('trendPickFavs', JSON.stringify(favorites));
  closeDetail();
}

// 즐겨찾기 목록 보기
function openFavorites() {
  const container = document.getElementById('favoriteList');
  if (favorites.length === 0) {
    container.innerHTML = '<p style="text-align:center; padding:20px; color:#9aa3b2;">저장된 항목이 없습니다.</p>';
  } else {
    container.innerHTML = favorites.map(item => `
      <div class="trend-item" style="margin-bottom:12px; border-bottom:1px solid rgba(255,255,255,0.05); padding-bottom:10px;" onclick='openDetail(${JSON.stringify(item).replace(/'/g, "&apos;")})'>
        <div style="font-size:16px; font-weight:700;">${item.title}</div>
        <div style="font-size:12px; color:#9aa3b2; margin-top:4px;">${item.source}</div>
      </div>
    `).join('');
  }
  document.getElementById('favoritesBackdrop').classList.remove('hidden');
  document.getElementById('favoritesSheet').classList.remove('hidden');
}

function closeFavorites() {
  document.getElementById('favoritesBackdrop').classList.add('hidden');
  document.getElementById('favoritesSheet').classList.add('hidden');
}

// 7. 검색 필터
function filterData(query) {
  const filtered = allData.filter(item => item.title.toLowerCase().includes(query.toLowerCase()));
  renderList(filtered);
}
