/**
 * 트렌드픽 2.0 - 통합 이슈 대시보드 (로딩 강화판)
 */

// 더 빠르고 안정적인 프록시로 교체
const PROXY_URL = "https://corsproxy.io/?"; 

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
  // 이벤트 바인딩 (생략 없이 모두 포함)
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

  trendList.innerHTML = '<p style="padding:40px; text-align:center; color:#9aa3b2;">데이터를 낚아올리는 중...</p>';
  sourceState.innerText = "연결 통로 확보 중...";

  try {
    // 💡 타임아웃 설정을 추가해서 무한 대기를 방지합니다.
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 8000); 

    const targetUrl = PROXY_URL + encodeURIComponent(source.url);
    const response = await fetch(targetUrl, { signal: controller.signal });
    clearTimeout(timeoutId);

    if (!response.ok) throw new Error('서버 응답 없음');
    
    const rawData = await response.text();
    const parser = new DOMParser();
    allData = [];

    if (source.type === 'rss' || source.type === 'rss-yt') {
      const xml = parser.parseFromString(rawData, "text/xml");
      const items = xml.querySelectorAll(source.type === 'rss-yt' ? "entry" : "item");

      items.forEach((item, idx) => {
        const title = item.querySelector("title")?.textContent || "제목 없음";
        let link = source.type === 'rss-yt' ? item.querySelector("link")?.getAttribute("href") : item.querySelector("link")?.textContent;
        
        allData.push({
          id: Date.now() + idx,
          rank: idx + 1,
          title: title.trim(),
          link: link || "#",
          summary: item.querySelector("description")?.textContent || "상세 내용이 없습니다.",
          source: source.name
        });
      });
    } else if (source.type === 'nate') {
      const regex = /\["(.*?)",/g;
      let match, idx = 1;
      while ((match = regex.exec(rawData)) !== null && idx <= 10) {
        allData.push({
          id: Date.now() + idx,
          rank: idx++,
          title: match[1],
          link: `https://search.daum.net/search?w=tot&q=${encodeURIComponent(match[1])}`,
          summary: "네이트 실시간 이슈 키워드입니다.",
          source: "네이트"
        });
      }
    }

    if (allData.length === 0) throw new Error('데이터 파싱 실패');

    renderList(allData);
    sourceState.innerText = "실시간 데이터 수신 성공";
    updatedAt.innerText = new Date().toLocaleString('ko-KR', { hour12: true });

  } catch (error) {
    console.error("Fetch Error:", error);
    sourceState.innerText = "신호 약함 (다시 시도해 주세요)";
    trendList.innerHTML = `
      <div style="padding:40px; text-align:center;">
        <p>데이터를 불러오지 못했습니다. 😢</p>
        <p style="font-size:12px; color:#9aa3b2; margin-bottom:20px;">네트워크나 프록시 지연 때문일 수 있습니다.</p>
        <button onclick="loadData('${sourceKey}')" class="action-btn">다시 시도</button>
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
  document.getElementById('detailSummary').innerHTML = item.summary;
  
  const isFav = favorites.some(f => f.link === item.link);
  document.getElementById('favoriteBtn').innerText = isFav ? "즐겨찾기 삭제" : "즐겨찾기 저장";
  document.getElementById('favoriteBtn').onclick = () => {
    const idx = favorites.findIndex(f => f.link === item.link);
    if (idx > -1) favorites.splice(idx, 1);
    else favorites.push(item);
    localStorage.setItem('trendPickFavs', JSON.stringify(favorites));
    closeDetail();
    alert(idx > -1 ? "삭제됨" : "저장됨");
  };

  document.getElementById('detailLinks').innerHTML = `<button class="action-btn" style="width:100%; padding:16px;" onclick="window.open('${item.link}', '_blank')">원본 열기</button>`;
  document.getElementById('sheetBackdrop').classList.remove('hidden');
  document.getElementById('detailSheet').classList.remove('hidden');
}

function closeDetail() {
  document.getElementById('sheetBackdrop').classList.add('hidden');
  document.getElementById('detailSheet').classList.add('hidden');
}

function openFavorites() {
  const container = document.getElementById('favoriteList');
  if (favorites.length === 0) {
    container.innerHTML = '<p style="text-align:center; padding:20px; color:#9aa3b2;">저장된 항목이 없습니다.</p>';
  } else {
    container.innerHTML = favorites.map(item => `
      <div class="trend-item" style="margin-bottom:12px; border-bottom:1px solid rgba(255,255,255,0.05); padding-bottom:10px;" onclick="window.open('${item.link}', '_blank')">
        <div style="font-size:16px; font-weight:700;">${item.title}</div>
        <div style="font-size:12px; color:#9aa3b2; margin-top:4px;">${item.source} (열기)</div>
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

function filterData(query) {
  const filtered = allData.filter(item => item.title.toLowerCase().includes(query.toLowerCase()));
  renderList(filtered);
}
