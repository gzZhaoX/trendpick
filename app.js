/**
 * 트렌드픽 2.0 - 마스터 보정판 (이중 통로 시스템)
 */

const PROXY_1 = "https://corsproxy.io/?";
const PROXY_2 = "https://api.allorigins.win/raw?url=";

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
  // 버튼 연결
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

// 💡 핵심: 이중 프록시 시도 함수
async function fetchWithFallback(url) {
  try {
    // 첫 번째 통로 시도
    let response = await fetch(PROXY_1 + encodeURIComponent(url));
    if (response.ok) return await response.text();
    
    // 실패 시 두 번째 통로 시도
    response = await fetch(PROXY_2 + encodeURIComponent(url));
    if (response.ok) return await response.text();
    
    throw new Error('모든 통로가 막혔습니다.');
  } catch (e) {
    throw e;
  }
}

async function loadData(sourceKey) {
  const source = SOURCES[sourceKey];
  const trendList = document.getElementById('trendList');
  const sourceState = document.getElementById('sourceState');
  const updatedAt = document.getElementById('updatedAt');

  trendList.innerHTML = '<p style="padding:40px; text-align:center; color:#9aa3b2;">트렌드를 낚아올리는 중...</p>';
  sourceState.innerText = "안전한 통로 찾는 중...";

  try {
    const rawData = await fetchWithFallback(source.url);
    const parser = new DOMParser();
    allData = [];

    if (source.type === 'rss' || source.type === 'rss-yt') {
      const xml = parser.parseFromString(rawData, "text/xml");
      const items = xml.querySelectorAll(source.type === 'rss-yt' ? "entry" : "item");

      items.forEach((item, idx) => {
        const title = item.querySelector("title")?.textContent || "제목 없음";
        let link = source.type === 'rss-yt' ? item.querySelector("link")?.getAttribute("href") : item.querySelector("link")?.textContent;
        let desc = item.querySelector("description")?.textContent || "상세 내용 없음";
        
        allData.push({
          rank: idx + 1,
          title: title.trim(),
          link: link || "#",
          summary: desc.replace(/<[^>]*>?/gm, '').slice(0, 150), // HTML 태그 제거
          source: source.name
        });
      });
    } else if (source.type === 'nate') {
      // 네이트 전용 정교한 파싱
      const regex = /\[\d+,\s*"(.*?)"/g;
      let match, idx = 1;
      while ((match = regex.exec(rawData)) !== null && idx <= 10) {
        allData.push({
          rank: idx++,
          title: match[1],
          link: `https://search.daum.net/search?w=tot&q=${encodeURIComponent(match[1])}`,
          summary: "네이트 실시간 이슈 키워드입니다.",
          source: "네이트"
        });
      }
    }

    if (allData.length === 0) throw new Error('파싱 데이터 없음');

    renderList(allData);
    sourceState.innerText = "실시간 데이터 수신 성공";
    updatedAt.innerText = new Date().toLocaleString('ko-KR', { hour12: true });

  } catch (error) {
    sourceState.innerText = "신호 약함 (다시 시도)";
    trendList.innerHTML = `
      <div style="padding:40px; text-align:center;">
        <p>데이터 로드에 실패했습니다. 😢</p>
        <button onclick="loadData('${sourceKey}')" class="action-btn" style="margin-top:10px;">다시 시도</button>
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
          <div style="font-size:18px; font-weight:700; margin-bottom:4px; line-height:1.4;">${item.title}</div>
          <div style="font-size:13px; color:#9aa3b2;">${item.source}</div>
        </div>
      </div>
    </div>
  `).join('');
}

function openDetailByIndex(index) {
  const item = allData[index];
  document.getElementById('detailRank').innerText = `#${item.rank} - ${item.source}`;
  document.getElementById('detailKeyword').innerText = item.title;
  document.getElementById('detailSummary').innerText = item.summary;
  
  const isFav = favorites.some(f => f.link === item.link);
  document.getElementById('favoriteBtn').innerText = isFav ? "즐겨찾기 삭제" : "즐겨찾기 저장";
  document.getElementById('favoriteBtn').onclick = () => {
    const fIdx = favorites.findIndex(f => f.link === item.link);
    if (fIdx > -1) favorites.splice(fIdx, 1);
    else favorites.push(item);
    localStorage.setItem('trendPickFavs', JSON.stringify(favorites));
    closeDetail();
    alert(fIdx > -1 ? "삭제되었습니다." : "저장되었습니다!");
  };

  document.getElementById('detailLinks').innerHTML = `<button class="action-btn" style="width:100%; padding:16px;" onclick="window.open('${item.link}', '_blank')">원본 페이지 열기</button>`;
  document.getElementById('sheetBackdrop').classList.remove('hidden');
  document.getElementById('detailSheet').classList.remove('hidden');
}

function closeDetail() {
  document.getElementById('sheetBackdrop').classList.add('hidden');
  document.getElementById('detailSheet').classList.add('hidden');
}

function openFavorites() {
  const container = document.getElementById('favoriteList');
  container.innerHTML = favorites.length === 0 
    ? '<p style="text-align:center; padding:20px; color:#9aa3b2;">저장된 항목이 없습니다.</p>'
    : favorites.map(item => `
      <div class="trend-item" style="margin-bottom:12px; border-bottom:1px solid rgba(255,255,255,0.05); padding-bottom:10px;" onclick="window.open('${item.link}', '_blank')">
        <div style="font-size:16px; font-weight:700;">${item.title}</div>
        <div style="font-size:12px; color:#9aa3b2; margin-top:4px;">${item.source} (터치시 이동)</div>
      </div>
    `).join('');
  document.getElementById('favoritesBackdrop').classList.remove('hidden');
  document.getElementById('favoritesSheet').classList.remove('hidden');
}

function closeFavorites() {
  document.getElementById('favoritesBackdrop').classList.add('hidden');
  document.getElementById('favoritesSheet').classList.add('hidden');
}

function filterData(query) {
  const filtered = allData.filter(item => item.title.toLowerCase().includes(query.toLowerCase()));
  renderList(filtered);
}
