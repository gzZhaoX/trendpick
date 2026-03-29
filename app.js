const RENDER_SERVER = "https://trendpick-api.onrender.com";
const CATEGORIES = ["전체", "정치", "경제", "스포츠", "연예", "게임", "네이트", "유튜브", "웃긴대학", "보배드림"];
const CLIENT_PROXY = "https://corsproxy.io/?"; // 서버 실패 시 사용할 백업 통로

let currentCategory = "전체";
let allData = [];

document.addEventListener('DOMContentLoaded', () => {
    const container = document.getElementById('categoryTabs');
    container.innerHTML = CATEGORIES.map(cat => `<button class="action-btn ${currentCategory === cat ? 'active' : ''}" onclick="switchCategory('${cat}')">${cat}</button>`).join('');
    loadData(currentCategory);
    document.getElementById('refreshBtn').onclick = () => loadData(currentCategory);
});

async function loadData(category) {
    const trendList = document.getElementById('trendList');
    trendList.innerHTML = '<p style="padding:40px; text-align:center;">최신 트렌드를 확인하는 중...</p>';

    try {
        // 1. 먼저 전용 서버(Render)에 물어봅니다.
        const response = await fetch(`${RENDER_SERVER}/trends?category=${encodeURIComponent(category)}`);
        const result = await response.json();

        if (result.error || (result.length === 1 && result[0].keyword === "Error")) {
            throw new Error("Server Blocked"); // 서버가 차단되었거나 에러면 백업으로 이동
        }

        allData = result;
        renderList(allData);
        document.getElementById('sourceState').innerText = "수신 완료 (Render Server)";
    } catch (e) {
        // 2. 서버가 실패하면 폰이 직접 'corsproxy'를 통해 가져옵니다 (최종 병기)
        console.log("서버 차단됨. 백업 통로로 직접 연결합니다.");
        document.getElementById('sourceState').innerText = "백업 통로 연결 중...";
        await loadDataDirectly(category);
    }
    document.getElementById('updatedAt').innerText = new Date().toLocaleTimeString();
}

async function loadDataDirectly(category) {
    const FEEDS = {
        "유튜브": "https://www.youtube.com/feeds/videos.xml?chart=mostPopular&regionCode=KR",
        "웃긴대학": "http://web.humoruniv.com/rss/best.xml",
        "보배드림": "https://m.bobaedream.co.kr/board/bbs/best/rss"
    };
    
    const url = FEEDS[category];
    if (!url) {
        document.getElementById('trendList').innerHTML = '<p style="padding:40px; text-align:center;">해당 카테고리는 현재 서버 점검 중입니다.</p>';
        return;
    }

    try {
        const res = await fetch(CLIENT_PROXY + encodeURIComponent(url));
        const text = await res.text();
        const parser = new DOMParser();
        const xml = parser.parseFromString(text, "text/xml");
        const items = xml.querySelectorAll(category === "유튜브" ? "entry" : "item");
        
        allData = Array.from(items).slice(0, 20).map((node, i) => ({
            rank: i + 1,
            keyword: node.querySelector("title").textContent.split(" - ")[0],
            category: category,
            link: category === "유튜브" ? node.querySelector("link").getAttribute("href") : node.querySelector("link").textContent
        }));
        
        renderList(allData);
        document.getElementById('sourceState').innerText = "수신 완료 (Direct Backup)";
    } catch (err) {
        document.getElementById('trendList').innerHTML = '<p style="padding:40px; text-align:center;">데이터를 불러올 수 없습니다. 😢</p>';
    }
}

function renderList(data) {
    document.getElementById('trendList').innerHTML = data.map(item => `
        <div class="trend-item" style="margin-bottom:12px; cursor:pointer;" onclick="window.open('${item.link}', '_blank')">
            <div style="display:flex; align-items:center; gap:15px;">
                <div style="font-size:20px; font-weight:900; color:#9aa3b2; width:28px;">${item.rank}</div>
                <div style="flex:1;">
                    <div style="font-size:17px; font-weight:700; margin-bottom:4px;">${item.keyword}</div>
                    <div style="font-size:12px; color:#9aa3b2;">${item.category}</div>
                </div>
            </div>
        </div>`).join('');
}
