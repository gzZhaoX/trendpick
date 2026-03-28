const categories = ["전체", "정치", "연예", "스포츠", "경제", "게임"];

const baseTrends = [
  {
    keyword: "환율",
    category: "경제",
    summary: "원달러 환율 변동성 확대 소식으로 관심이 빠르게 커졌습니다.",
    reasons: ["환율 급등락 기사 증가", "해외 증시와 금리 이슈", "생활물가 영향 관심 확대"],
  },
  {
    keyword: "챔피언스리그",
    category: "스포츠",
    summary: "유럽 축구 빅매치 일정과 결과 때문에 검색량이 급증했습니다.",
    reasons: ["주요 경기 결과 발표", "하이라이트 영상 확산", "국내 팬 커뮤니티 반응 증가"],
  },
  {
    keyword: "미세먼지",
    category: "정치",
    summary: "대기질 악화 예보로 외출 전 확인 수요가 늘었습니다.",
    reasons: ["주말 예보 관심 집중", "건강 관련 검색 동반 상승", "지역별 농도 차이 확인 수요"],
  },
  {
    keyword: "신작 모바일게임",
    category: "게임",
    summary: "사전예약과 출시 이벤트 소식이 퍼지며 검색이 늘었습니다.",
    reasons: ["출시 기념 보상 공개", "스트리머 방송 노출", "커뮤니티 공략글 증가"],
  },
  {
    keyword: "배우 인터뷰",
    category: "연예",
    summary: "방송 출연과 인터뷰 영상이 화제가 되며 관심이 커졌습니다.",
    reasons: ["예능 출연 직후 검색 증가", "클립 영상 확산", "관련 작품 관심 재상승"],
  },
  {
    keyword: "프로야구 개막",
    category: "스포츠",
    summary: "개막전 일정과 선발 라인업 때문에 야구 팬 검색이 몰렸습니다.",
    reasons: ["개막전 선발 발표", "티켓 예매 경쟁", "팀별 전망 기사 증가"],
  },
  {
    keyword: "금리",
    category: "경제",
    summary: "기준금리 전망 기사와 대출 이자 관심이 겹치며 검색이 늘었습니다.",
    reasons: ["정책 발표 전망", "부동산 연관 이슈", "예적금 비교 검색 증가"],
  },
  {
    keyword: "총선 공약",
    category: "정치",
    summary: "주요 공약 비교 기사와 토론 이슈가 검색량을 끌어올렸습니다.",
    reasons: ["비교 기사 증가", "커뮤니티 토론 확산", "이슈별 후보 공약 확인 수요"],
  },
  {
    keyword: "신작 드라마",
    category: "연예",
    summary: "첫 방송 반응과 배우 화제성이 겹쳐 관심이 커졌습니다.",
    reasons: ["첫 방송 직후 반응 급증", "명장면 클립 확산", "OST 검색 동반 증가"],
  },
  {
    keyword: "벚꽃축제",
    category: "연예",
    summary: "주말 나들이 수요와 개화 시기 검색이 겹치며 급상승했습니다.",
    reasons: ["지역 축제 일정 공개", "개화 예측 기사 증가", "주말 여행 검색과 연동"],
  }
];

let currentCategory = "전체";
let trends = [];
let favorites = JSON.parse(localStorage.getItem("trendpick-favorites") || "[]");
let selectedTrend = null;

const updatedAtEl = document.getElementById("updatedAt");
const favoriteCountEl = document.getElementById("favoriteCount");
const categoryTabsEl = document.getElementById("categoryTabs");
const trendListEl = document.getElementById("trendList");
const favoriteListEl = document.getElementById("favoriteList");
const currentCategoryLabelEl = document.getElementById("currentCategoryLabel");
const detailModalEl = document.getElementById("detailModal");
const refreshBtn = document.getElementById("refreshBtn");
const closeModalBtn = document.getElementById("closeModalBtn");
const modalBackdrop = document.getElementById("modalBackdrop");
const detailFavoriteBtn = document.getElementById("detailFavoriteBtn");
const copyBtn = document.getElementById("copyBtn");

function nowText() {
  return new Date().toLocaleString("ko-KR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function shuffle(array) {
  return [...array]
    .map((item) => ({ item, sort: Math.random() }))
    .sort((a, b) => a.sort - b.sort)
    .map(({ item }) => item);
}

function buildTrendData() {
  const mixed = shuffle(baseTrends).map((item, idx) => {
    const deltaSeed = Math.floor(Math.random() * 7) - 2;
    return {
      ...item,
      rank: idx + 1,
      delta: deltaSeed,
      isNew: Math.random() > 0.84,
    };
  });
  trends = mixed.sort((a, b) => a.rank - b.rank);
  updatedAtEl.textContent = nowText();
}

function renderTabs() {
  categoryTabsEl.innerHTML = "";
  categories.forEach((cat) => {
    const btn = document.createElement("button");
    btn.className = `tab-btn ${cat === currentCategory ? "active" : ""}`;
    btn.textContent = cat;
    btn.addEventListener("click", () => {
      currentCategory = cat;
      renderTabs();
      renderTrends();
    });
    categoryTabsEl.appendChild(btn);
  });
}

function filteredTrends() {
  if (currentCategory === "전체") return trends;
  return trends.filter((item) => item.category === currentCategory);
}

function deltaBadge(delta, isNew) {
  if (isNew) return '<span class="delta up">NEW</span>';
  if (delta > 0) return `<span class="delta up">▲ ${delta}</span>`;
  if (delta < 0) return `<span class="delta down">▼ ${Math.abs(delta)}</span>`;
  return '<span class="delta same">-</span>';
}

function renderTrends() {
  const items = filteredTrends();
  currentCategoryLabelEl.textContent = currentCategory;
  trendListEl.innerHTML = "";

  if (!items.length) {
    trendListEl.innerHTML = '<div class="empty">이 카테고리에는 표시할 키워드가 없습니다.</div>';
    return;
  }

  items.forEach((item) => {
    const card = document.createElement("button");
    card.type = "button";
    card.className = "trend-item";
    card.innerHTML = `
      <div class="rank-badge">${item.rank}</div>
      <div class="trend-body">
        <p class="trend-title">${item.keyword}</p>
        <p class="meta">${item.category}</p>
        <p class="summary">${item.summary}</p>
      </div>
      ${deltaBadge(item.delta, item.isNew)}
    `;
    card.addEventListener("click", () => openDetail(item));
    trendListEl.appendChild(card);
  });
}

function renderFavorites() {
  favoriteCountEl.textContent = `${favorites.length}개`;
  if (!favorites.length) {
    favoriteListEl.className = "favorite-list empty";
    favoriteListEl.textContent = "저장한 키워드가 없습니다.";
    return;
  }
  favoriteListEl.className = "favorite-list";
  favoriteListEl.innerHTML = "";
  favorites.forEach((keyword) => {
    const item = document.createElement("div");
    item.className = "favorite-item";
    item.innerHTML = `
      <p class="fav-keyword">${keyword}</p>
      <button class="ghost-btn">삭제</button>
    `;
    item.querySelector("button").addEventListener("click", () => toggleFavorite(keyword));
    favoriteListEl.appendChild(item);
  });
}

function saveFavorites() {
  localStorage.setItem("trendpick-favorites", JSON.stringify(favorites));
  renderFavorites();
}

function toggleFavorite(keyword) {
  if (favorites.includes(keyword)) {
    favorites = favorites.filter((item) => item !== keyword);
  } else {
    favorites.unshift(keyword);
  }
  saveFavorites();
  if (selectedTrend && selectedTrend.keyword === keyword) {
    updateDetailFavoriteButton();
  }
}

function openDetail(item) {
  selectedTrend = item;
  document.getElementById("detailCategory").textContent = item.category;
  document.getElementById("detailKeyword").textContent = item.keyword;
  document.getElementById("detailRank").textContent = `현재 순위 ${item.rank}위`;
  document.getElementById("detailSummary").textContent = item.summary;
  const reasonsEl = document.getElementById("detailReasons");
  reasonsEl.innerHTML = "";
  item.reasons.forEach((reason) => {
    const li = document.createElement("li");
    li.textContent = reason;
    reasonsEl.appendChild(li);
  });
  updateDetailFavoriteButton();
  detailModalEl.classList.remove("hidden");
  detailModalEl.setAttribute("aria-hidden", "false");
}

function closeDetail() {
  detailModalEl.classList.add("hidden");
  detailModalEl.setAttribute("aria-hidden", "true");
}

function updateDetailFavoriteButton() {
  if (!selectedTrend) return;
  detailFavoriteBtn.textContent = favorites.includes(selectedTrend.keyword) ? "즐겨찾기 해제" : "즐겨찾기";
}

refreshBtn.addEventListener("click", () => {
  buildTrendData();
  renderTrends();
});
closeModalBtn.addEventListener("click", closeDetail);
modalBackdrop.addEventListener("click", closeDetail);
detailFavoriteBtn.addEventListener("click", () => {
  if (selectedTrend) toggleFavorite(selectedTrend.keyword);
});
copyBtn.addEventListener("click", async () => {
  if (!selectedTrend) return;
  try {
    await navigator.clipboard.writeText(selectedTrend.keyword);
    copyBtn.textContent = "복사됨";
    setTimeout(() => (copyBtn.textContent = "키워드 복사"), 1000);
  } catch {
    copyBtn.textContent = "복사 실패";
    setTimeout(() => (copyBtn.textContent = "키워드 복사"), 1000);
  }
});

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => navigator.serviceWorker.register("./service-worker.js"));
}

buildTrendData();
renderTabs();
renderTrends();
renderFavorites();
