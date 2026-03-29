const RENDER_SERVER = "https://trendpick-api.onrender.com";
const CATEGORIES = ["전체", "정치", "경제", "스포츠", "연예", "게임", "네이트", "유튜브", "웃긴대학", "보배드림"];
let currentCategory = "전체";
let allData = [];

document.addEventListener('DOMContentLoaded', () => {
    const container = document.getElementById('categoryTabs');
    container.innerHTML = CATEGORIES.map(cat => `
        <button class="action-btn ${currentCategory === cat ? 'active' : ''}" onclick="switchCategory('${cat}')">
            ${cat}
        </button>`).join('');
    loadData(currentCategory);
    
    document.getElementById('refreshBtn').onclick = () => loadData(currentCategory);
    document.getElementById('searchInput').oninput = (e) => filterData(e.target.value);
});

function switchCategory(cat) {
    currentCategory = cat;
    document.querySelectorAll('.action-btn').forEach(btn => {
        btn.classList.toggle('active', btn.innerText === cat);
    });
    loadData(cat);
}

async function loadData(category) {
    const trendList = document.getElementById('trendList');
    const sourceState = document.getElementById('sourceState');
    trendList.innerHTML = '<p style="padding:40px; text-align:center;">데이터를 가져오고 있습니다...</p>';

    try {
        const response = await fetch(`${RENDER_SERVER}/trends?category=${encodeURIComponent(category)}`);
        allData = await response.json();
        
        if (!allData || allData.length === 0) {
            trendList.innerHTML = '<p style="padding:40px; text-align:center;">표시할 데이터가 없습니다. 😢</p>';
            return;
        }

        renderList(allData);
        sourceState.innerText = "수신 완료";
        document.getElementById('updatedAt').innerText = new Date().toLocaleTimeString();
    } catch (e) {
        sourceState.innerText = "서버 연결 대기 중";
        trendList.innerHTML = '<button onclick="location.reload()" class="action-btn" style="margin:40px auto; display:block;">서버 깨우기 (터치)</button>';
    }
}

function renderList(data) {
    const container = document.getElementById('trendList');
    container.innerHTML = data.map(item => `
        <div class="trend-item" style="margin-bottom:12px; cursor:pointer;" onclick="window.open('${item.link}', '_blank')">
            <div style="display:flex; align-items:center; gap:15px;">
                <div style="font-size:20px; font-weight:900; color:${item.category==='Error'?'#ff4d4d':'#9aa3b2'}; width:28px;">${item.rank}</div>
                <div style="flex:1;">
                    <div style="font-size:17px; font-weight:700; margin-bottom:4px;">${item.keyword}</div>
                    <div style="font-size:12px; color:#9aa3b2;">${item.category}</div>
                </div>
            </div>
        </div>`).join('');
}

function filterData(q) {
    const filtered = allData.filter(item => item.keyword.toLowerCase().includes(q.toLowerCase()));
    renderList(filtered);
}
