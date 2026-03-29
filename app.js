/**
 * 트렌드픽 2.0 - 통합 이슈 대시보드 (최종 보정판)
 * 수정사항: 데이터 로딩 안정성 강화 및 프록시 주소 최적화
 */

const PROXY_URL = "https://api.allorigins.win/raw?url="; // 더 안정적인 RAW 방식으로 변경

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

  document.getElementById('refreshBtn').addEventListener('click', () => loadData(currentSource));
  document.getElementById('searchInput').addEventListener('input', (e) => filterData(e.target.value));
  document.getElementById('closeDetailBtn').addEventListener('click', closeDetail);
  document.getElementById('sheetBackdrop').addEventListener('click', closeDetail);
  document.getElementById('showFavoritesBtn').addEventListener('click', openFavorites);
  document.getElementById('closeFavoritesBtn').addEventListener('click', closeFavorites);
  document.getElementById('favoritesBackdrop').addEventListener('click', closeFavorites);
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
  sourceState.innerText = "서버 연결 중...";

  try {
    const response = await fetch(PROXY_URL + encodeURIComponent(source.url));
    if (!response.ok) throw new Error('Network response was not ok');
    
    const rawData = await response.text(); // JSON이 아닌 텍스트로 바로 받음
    const parser = new DOMParser();
    allData = [];

    if (source.type === 'rss' || source.type === 'rss-yt') {
      const xml = parser.parseFromString(rawData, "text/xml");
      const items = xml.querySelectorAll(source.type === 'rss-yt' ? "entry" : "item");

      items.forEach((item, idx) => {
        const title = item.querySelector("title")?.textContent || "제목 없음";
        let link = "";
        if(source.type === 'rss-yt') {
          link = item.querySelector("link")?.getAttribute("href") || "#";
        } else {
          link = item.querySelector("link")?.textContent || "#";
        }
        
        allData.push({
          id: Date.now() + idx,
          rank: idx + 1,
          title: title,
          link: link,
          summary: item.querySelector("description")?.textContent || "내용 요약 없음",
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
          summary: "네이트 실시간 인기 검색어입니다.",
          source: "네이트"
        });
      }
    }

    renderList(allData);
    sourceState.innerText = "실시간 서버 데이터";
    updatedAt.innerText = new Date().toLocaleString('ko-KR', { hour12: true });

  } catch (error) {
    console.error("Error:", error);
    sourceState.innerText = "데이터 로드 실패 (재시도 필요)";
    trendList.innerHTML = `<p style="padding:40px; text-align:center;">데이터를 불러오지 못했습니다. 😢<br><br><button onclick="loadData('${sourceKey}')" class="action-btn">다시 시도</button></p>`;
  }
}

function renderList(data) {
  const container = document.getElementById('trendList');
  if (data.length === 0) {
    container.innerHTML = '<p style="padding:20px; text-align:center; color:#9aa3b2;">검색 결과가 없습니다.</p>';
    return;
  }
  
  // onclick 이벤트 내 문자열 에러 방지를 위해 인덱스 방식으로 변경
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

// 상세 시트용 변수
let currentItem = null;

function openDetailByIndex(index) {
  const item = allData[index];
  currentItem = item;
  document.getElementById('detailRank').innerText = `#${item.rank} - ${item.source}`;
  document.getElementById('detailKeyword').innerText = item.title;
  document.getElementById('detailSummary').innerHTML = item.summary;
  
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

function toggleFavorite() {
  const index = favorites.findIndex(f => f.link === currentItem.link);
  if (index > -1) {
    favorites.splice(index, 1);
  } else {
    favorites.push(currentItem);
  }
  localStorage.setItem('trendPickFavs', JSON.stringify(favorites));
  closeDetail();
  alert(index > -1 ? "삭제되었습니다." : "저장되었습니다!");
}

function openFavorites() {
  const container = document.getElementById('favoriteList');
  if (favorites.length === 0) {
    container.innerHTML = '<p style="text-align:center; padding:20px; color:#9aa3b2;">저장된 항목이 없습니다.</p>';
  } else {
    // 즐겨찾기는 별도 배열이므로 item 자체를 인덱스 대신 전달하는 방식 고민 필요하나 우선 단순화
    container.innerHTML = favorites.map((item) => `
      <div class="trend-item" style="margin-bottom:12px; border-bottom:1px solid rgba(255,255,255,0.05); padding-bottom:10px;" onclick="window.open('${item.link}', '_blank')">
        <div style="font-size:16px; font-weight:700;">${item.title}</div>
        <div style="font-size:12px; color:#9aa3b2; margin-top:4px;">${item.source} (터치시 이동)</div>
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
