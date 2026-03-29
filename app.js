/**
 * 트렌드픽 2.1 - 서버 연동 안정화 + 추가 카테고리 대응
 */

const RENDER_SERVER = "https://trendpick-api.onrender.com";
const CATEGORIES = ["전체", "정치", "경제", "스포츠", "연예", "게임", "네이트", "유튜브", "웃긴대학", "보배드림"];

let currentCategory = "전체";
let allData = [];

// 초기화
document.addEventListener("DOMContentLoaded", () => {
  setupCategoryTabs();
  setupRefreshButton();
  setupSearchInput();
  loadData(currentCategory);
});

// 카테고리 탭 생성
function setupCategoryTabs() {
  const tabContainer = document.getElementById("categoryTabs");
  if (!tabContainer) return;

  tabContainer.innerHTML = CATEGORIES.map(
    (cat) => `
      <button
        class="category-btn ${currentCategory === cat ? "active" : ""}"
        data-category="${escapeHtml(cat)}"
        style="
          white-space:nowrap;
          border:none;
          border-radius:12px;
          padding:12px 14px;
          font-size:15px;
          font-weight:700;
          cursor:pointer;
          background:${currentCategory === cat ? "#f5f7fb" : "#171a21"};
          color:${currentCategory === cat ? "#0f1115" : "#f5f7fb"};
        "
      >
        ${escapeHtml(cat)}
      </button>
    `
  ).join("");

  tabContainer.addEventListener("click", (e) => {
    const button = e.target.closest(".category-btn");
    if (!button) return;

    const selectedCat = button.getAttribute("data-category");
    if (!selectedCat || selectedCat === currentCategory) return;

    switchCategory(selectedCat);
  });
}

// 새로고침 버튼
function setupRefreshButton() {
  const refreshBtn = document.getElementById("refreshBtn");
  if (!refreshBtn) return;

  refreshBtn.onclick = () => {
    loadData(currentCategory);
  };
}

// 검색창
function setupSearchInput() {
  const searchInput = document.getElementById("searchInput");
  if (!searchInput) return;

  searchInput.oninput = (e) => {
    filterData(e.target.value || "");
  };
}

// 카테고리 전환
function switchCategory(category) {
  currentCategory = category;
  updateCategoryButtonStyles();
  clearSearchInput();
  loadData(category);
}

// 버튼 스타일 업데이트
function updateCategoryButtonStyles() {
  document.querySelectorAll(".category-btn").forEach((btn) => {
    const cat = btn.getAttribute("data-category");
    const isActive = cat === currentCategory;

    btn.style.background = isActive ? "#f5f7fb" : "#171a21";
    btn.style.color = isActive ? "#0f1115" : "#f5f7fb";
  });
}

// 검색창 초기화
function clearSearchInput() {
  const searchInput = document.getElementById("searchInput");
  if (searchInput) {
    searchInput.value = "";
  }
}

// 데이터 로드
async function loadData(category) {
  const trendList = document.getElementById("trendList");
  const sourceState = document.getElementById("sourceState");
  const updatedAt = document.getElementById("updatedAt");

  if (!trendList || !sourceState || !updatedAt) return;

  trendList.innerHTML = `
    <p style="padding:40px; text-align:center; color:#9aa3b2;">
      데이터를 가져오는 중...
    </p>
  `;
  sourceState.innerText = `${category} 불러오는 중...`;

  try {
    const response = await fetch(
      `${RENDER_SERVER}/trends?category=${encodeURIComponent(category)}`,
      {
        method: "GET",
        cache: "no-store",
      }
    );

    let data;
    try {
      data = await response.json();
    } catch (jsonError) {
      throw new Error("서버 응답을 해석하지 못했습니다.");
    }

    if (!response.ok) {
      throw new Error(data?.detail || `서버 오류 (${response.status})`);
    }

    if (!Array.isArray(data)) {
      throw new Error("응답 형식이 올바르지 않습니다.");
    }

    allData = data;

    if (allData.length === 0) {
      trendList.innerHTML = `
        <div style="padding:40px; text-align:center; color:#d8deea;">
          표시할 데이터가 없습니다.
        </div>
      `;
      sourceState.innerText = `${category} 데이터 없음`;
      updatedAt.innerText = new Date().toLocaleTimeString("ko-KR");
      return;
    }

    renderList(allData);
    sourceState.innerText = `수신 완료 (${category})`;
    updatedAt.innerText = new Date().toLocaleTimeString("ko-KR");
  } catch (error) {
    console.error("Load Error:", error);

    allData = [];
    sourceState.innerText = `${category} 로드 실패`;
    updatedAt.innerText = new Date().toLocaleTimeString("ko-KR");

    trendList.innerHTML = `
      <div style="padding:40px; text-align:center;">
        <p style="margin:0 0 10px; font-size:18px; font-weight:700;">
          ${escapeHtml(category)} 데이터를 불러오지 못했습니다.
        </p>
        <p style="margin:0; color:#9aa3b2; font-size:13px; line-height:1.6;">
          ${escapeHtml(error.message || "알 수 없는 오류")}
        </p>
        <button
          onclick="loadData('${escapeJsString(category)}')"
          class="action-btn"
          style="margin-top:15px; background:#f5f7fb; color:#0f1115;"
        >
          다시 시도
        </button>
      </div>
    `;
  }
}

// 리스트 렌더링
function renderList(data) {
  const container = document.getElementById("trendList");
  if (!container) return;

  container.innerHTML = data.map((item) => {
    const rank = item?.rank ?? "-";
    const keyword = item?.keyword ?? "제목 없음";
    const category = item?.category ?? "";
    const link = item?.link ?? "";

    const clickable = !!link;
    const openAction = clickable
      ? `onclick="window.open('${escapeJsString(link)}', '_blank', 'noopener,noreferrer')"`
      : "";

    return `
      <div
        class="trend-item"
        style="margin:0 14px 12px; cursor:${clickable ? "pointer" : "default"};"
        ${openAction}
      >
        <div style="display:flex; align-items:center; gap:15px;">
          <div style="font-size:20px; font-weight:900; color:#9aa3b2; width:28px;">
            ${escapeHtml(String(rank))}
          </div>
          <div style="flex:1;">
            <div style="font-size:17px; font-weight:700; margin-bottom:4px; line-height:1.45;">
              ${escapeHtml(keyword)}
            </div>
            <div style="font-size:12px; color:#9aa3b2;">
              ${escapeHtml(category)}
            </div>
          </div>
        </div>
      </div>
    `;
  }).join("");
}

// 검색 필터
function filterData(query) {
  const normalized = (query || "").trim().toLowerCase();

  if (!normalized) {
    renderList(allData);
    return;
  }

  const filtered = allData.filter((item) => {
    const keyword = (item?.keyword || "").toLowerCase();
    const category = (item?.category || "").toLowerCase();
    return keyword.includes(normalized) || category.includes(normalized);
  });

  renderList(filtered);
}

// HTML escape
function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

// JS string escape
function escapeJsString(value) {
  return String(value)
    .replace(/\\/g, "\\\\")
    .replace(/'/g, "\\'")
    .replace(/"/g, '\\"')
    .replace(/\n/g, "\\n")
    .replace(/\r/g, "\\r");
}
