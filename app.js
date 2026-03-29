const RENDER_SERVER = "https://trendpick-api.onrender.com";

const CATEGORIES = ["전체", "정치", "경제", "스포츠", "연예", "게임", "네이트", "유튜브", "웃긴대학", "보배드림"];

let currentCategory = "전체";
let allData = [];
let favorites = JSON.parse(localStorage.getItem('trendPickFavs')) || [];

document.addEventListener('DOMContentLoaded', () => {
    renderTabs();
    loadData(currentCategory);
    
    document.getElementById('refreshBtn').onclick = () => loadData(currentCategory);
    document.getElementById('searchInput').oninput = (e) => filterData(e.target.value);
    document.getElementById('closeDetailBtn').onclick = closeDetail;
    document.getElementById('sheetBackdrop').onclick = closeDetail;
    document.getElementById('showFavoritesBtn').onclick = openFavorites;
    document.getElementById('closeFavoritesBtn').onclick = closeFavorites;
});

function renderTabs() {
    const container = document.getElementById('categoryTabs');
    container.innerHTML = CATEGORIES.map(cat => `
        <button class="action-btn ${currentCategory === cat ? 'active' : ''}" 
                onclick="switchCategory('${cat}')" 
                style="flex: 0 0 auto; ${currentCategory === cat ? 'background:#f5f7fb; color:#0f1115;' : ''}">
            ${cat}
        </button>
    `).join('');
}

function switchCategory(cat) {
    currentCategory = cat;
    renderTabs();
    loadData(cat);
}

async function loadData(category) {
    const trendList = document.getElementById('trendList');
    const sourceState = document.getElementById('sourceState');
    const updatedAt = document.getElementById('updatedAt');

    trendList.innerHTML = '<p style="padding:40px; text-align:center; color:#9aa3b2;">서버에서 데이터를 낚아오는 중...</p>';
    sourceState.innerText = "서버 호출 중...";

    try {
        const response = await fetch(`${RENDER_SERVER}/trends?category=${encodeURIComponent(category)}`);
        if (!response.ok) throw new Error('Server starting...');

        allData = await response.json();
        renderList(allData);
        
        sourceState.innerText = "수신 완료 (Render Server)";
        updatedAt.innerText = new Date().toLocaleTimeString();
    } catch (error) {
        sourceState.innerText = "서버 깨우는 중 (재시도 필요)";
        trendList.innerHTML = `
            <div style="padding:40px; text-align:center;">
                <p>무료 서버가 잠을 자고 있네요. 😴</p>
                <button onclick="loadData('${category}')" class="action-btn" style="margin-top:10px;">서버 깨우기</button>
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
                    <div style="font-size:18px; font-weight:700; margin-bottom:4px;">${item.keyword}</div>
                    <div style="font-size:13px; color:#9aa3b2;">${item.category}</div>
                </div>
            </div>
        </div>
    `).join('');
}

function openDetailByIndex(index) {
    const item = allData[index];
    document.getElementById('detailKeyword').innerText = item.keyword;
    document.getElementById('detailSummary').innerText = item.summary;
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

function openFavorites() { /* 즐겨찾기 로직 동일 */ }
function closeFavorites() { /* 즐겨찾기 로직 동일 */ }
function filterData(q) { /* 검색 로직 동일 */ }
