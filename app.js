/**
 * 트렌드픽 2.0 - 버튼 먹통 해결 및 서버 연동 완성본
 */

const RENDER_SERVER = "https://trendpick-api.onrender.com";
const CATEGORIES = ["전체", "정치", "경제", "스포츠", "연예", "게임", "네이트", "유튜브", "웃긴대학", "보배드림"];

let currentCategory = "전체";
let allData = [];

// 1. 초기화 및 이벤트 바인딩
document.addEventListener('DOMContentLoaded', () => {
    // 카테고리 버튼 생성
    const tabContainer = document.getElementById('categoryTabs');
    if (tabContainer) {
        tabContainer.innerHTML = CATEGORIES.map(cat => `
            <button class="category-btn ${currentCategory === cat ? 'active' : ''}" data-category="${cat}">
                ${cat}
            </button>
        `).join('');

        // 💡 버튼 클릭 이벤트 바인딩 (가장 확실한 방식)
        tabContainer.addEventListener('click', (e) => {
            if (e.target.classList.contains('category-btn')) {
                const selectedCat = e.target.getAttribute('data-category');
                switchCategory(selectedCat);
            }
        });
    }

    // 새로고침 버튼 연결
    const refreshBtn = document.getElementById('refreshBtn');
    if (refreshBtn) refreshBtn.onclick = () => loadData(currentCategory);

    // 검색창 연결
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.oninput = (e) => filterData(e.target.value);
    }

    // 첫 데이터 로드
    loadData(currentCategory);
});

// 2. 카테고리 전환 함수
function switchCategory(cat) {
    currentCategory = cat;
    
    // 버튼 스타일 업데이트
    document.querySelectorAll('.category-btn').forEach(btn => {
        if (btn.innerText.trim() === cat) {
            btn.style.background = "#f5f7fb";
            btn.style.color = "#0f1115";
        } else {
            btn.style.background = "#171a21";
            btn.style.color = "#f5f7fb";
        }
    });

    loadData(cat);
}

// 3. 데이터 로드 핵심 함수
async function loadData(category) {
    const trendList = document.getElementById('trendList');
    const sourceState = document.getElementById('sourceState');
    const updatedAt = document.getElementById('updatedAt');

    trendList.innerHTML = '<p style="padding:40px; text-align:center; color:#9aa3b2;">데이터를 가져오는 중...</p>';
    sourceState.innerText = "서버 연결 중...";

    try {
        // 렌더 서버 호출
        const response = await fetch(`${RENDER_SERVER}/trends?category=${encodeURIComponent(category)}`);
        
        if (!response.ok) throw new Error("Server Busy");

        allData = await response.json();
        
        if (!allData || allData.length === 0) {
            trendList.innerHTML = '<p style="padding:40px; text-align:center;">표시할 데이터가 없습니다.</p>';
            return;
        }

        renderList(allData);
        sourceState.innerText = "수신 완료 (Render Server)";
        updatedAt.innerText = new Date().toLocaleTimeString();

    } catch (error) {
        console.error("Load Error:", error);
        sourceState.innerText = "서버 연결 실패 (재시도 필요)";
        trendList.innerHTML = `
            <div style="padding:40px; text-align:center;">
                <p>서버가 응답하지 않습니다. 😴</p>
                <button onclick="location.reload()" class="action-btn" style="margin-top:15px; background:#f5f7fb; color:#0f1115;">앱 다시 시작</button>
            </div>`;
    }
}

// 4. 리스트 화면에 그리기
function renderList(data) {
    const container = document.getElementById('trendList');
    container.innerHTML = data.map((item) => `
        <div class="trend-item" style="margin-bottom:12px; cursor:pointer;" onclick="window.open('${item.link}', '_blank')">
            <div style="display:flex; align-items:center; gap:15px;">
                <div style="font-size:20px; font-weight:900; color:#9aa3b2; width:28px;">${item.rank}</div>
                <div style="flex:1;">
                    <div style="font-size:17px; font-weight:700; margin-bottom:4px;">${item.keyword}</div>
                    <div style="font-size:12px; color:#9aa3b2;">${item.category}</div>
                </div>
            </div>
        </div>
    `).join('');
}

// 5. 검색 필터링
function filterData(query) {
    const filtered = allData.filter(item => 
        item.keyword.toLowerCase().includes(query.toLowerCase())
    );
    renderList(filtered);
}
