const API_BASE = "https://trendpick-api.onrender.com";

const SAMPLE_TRENDS = [
  {
    rank: 1,
    keyword: "환율",
    category: "경제",
    summary: "환율 변동 기사와 해외 증시 이슈가 겹치며 관심이 커졌습니다.",
    headlines: ["원달러 환율 변동성 확대", "해외 증시 불안에 환율 관심 증가"],
    links: []
  },
  {
    rank: 2,
    keyword: "챔피언스리그",
    category: "스포츠",
    summary: "유럽 축구 주요 경기 결과와 하이라이트 확산으로 검색이 늘었습니다.",
    headlines: ["챔피언스리그 8강 확정", "빅매치 하이라이트 화제"],
    links: []
  }
];

const CATEGORIES = ["전체", "정치", "경제", "스포츠", "연예", "게임"];

const state = {
  category: "전체",
  search: "",
  trends: [],
  selected: null,
  favorites: loadFavorites(),
  isRefreshing: false
};

const el = {
  tabs: document.getElementById("categoryTabs"),
  list: document.getElementById("trendList"),
  updatedAt: document.getElementById("updatedAt"),
  sourceState: document.getElementById("sourceState"),
  refreshBtn: document.getElementById("refreshBtn"),
  searchInput: document.getElementById("searchInput"),
  detailSheet: document.getElementById("detailSheet"),
  detailRank: document.getElementById("detailRank"),
  detailKeyword: document.getElementById("detailKeyword"),
  detailSummary: document.getElementById("detailSummary"),
  detailLinks: document.getElementById("detailLinks"),
  closeDetailBtn: document.getElementById("closeDetailBtn"),
  sheetBackdrop: document.getElementById("sheetBackdrop"),
  favoriteBtn: document.getElementById("favoriteBtn"),
  shareBtn: document.getElementById("shareBtn"),
  showFavoritesBtn: document.getElementById("showFavoritesBtn"),
  favoritesSheet: document.getElementById("favoritesSheet"),
  favoritesBackdrop: document.getElementById("favoritesBackdrop"),
  closeFavoritesBtn: document.getElementById("closeFavoritesBtn"),
  favoriteList: document.getElementById("favoriteList")
};

function saveCache(key, value) {
  localStorage.setItem(key, JSON.stringify(value));
}

function loadCache(key) {
  const raw = localStorage.getItem(key);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function cacheKeyForCategory(category) {
  return `trendpick-last-success-${category}`;
}

function loadFavorites() {
  return loadCache("trendpick-favorites") || [];
}

function saveFavorites() {
  saveCache("trendpick-favorites", state.favorites);
}

function formatTime(date) {
  const d = new Date(date);
  return d.toLocaleString("ko-KR", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  });
}

function escapeHtml(text) {
  return String(text || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function renderTabs() {
  el.tabs.innerHTML = "";
  CATEGORIES.forEach((name) => {
    const btn = document.createElement("button");
    btn.className = "tab" + (state.category === name ? " active" : "");
    btn.textContent = name;
    btn.addEventListener("click", () => {
      state.category = name;
      renderTabs();
      showCachedOrSampleImmediately();
      fetchAndRender();
    });
    el.tabs.appendChild(btn);
  });
}

function renderStatus(kind) {
  const map = {
    loading: "불러오는 중",
    live: "실시간 서버 데이터",
    cached: "마지막 저장 데이터",
    sample: "샘플 데이터",
    updating: "업데이트 중"
  };
  el.sourceState.textContent = map[kind] || kind;
}

function filterBySearch(items) {
  if (!state.search.trim()) return items;
  const q = state.search.trim().toLowerCase();

  return items.filter((item) => {
    const keyword = String(item.keyword || "").toLowerCase();
    const summary = String(item.summary || "").toLowerCase();
    const headlines = Array.isArray(item.headlines) ? item.headlines : [];

    return (
      keyword.includes(q) ||
      summary.includes(q) ||
      headlines.some((h) => String(h).toLowerCase().includes(q))
    );
  });
}

function normalizeServerData(data) {
  if (!Array.isArray(data)) return [];
  return data.map((item, index) => ({
    rank: item.rank ?? index + 1,
    keyword: item.keyword ?? `키워드 ${index + 1}`,
    delta: item.delta ?? 0,
    category: item.category ?? "일반",
    summary: item.summary ?? "실시간 키워드입니다.",
    headlines: Array.isArray(item.headlines) ? item.headlines : [],
    links: Array.isArray(item.links) ? item.links : []
  }));
}

function renderCurrentList() {
  renderList(filterBySearch(state.trends));
}

function renderList(items) {
  if (!items.length) {
    el.list.innerHTML = '<div class="empty">보여줄 키워드가 없어요.</div>';
    return;
  }

  el.list.innerHTML = "";

  items.forEach((item) => {
    const article = document.createElement("article");
    article.className = "trend-item";

    const previewHeadlines = (item.headlines || []).slice(0, 2);
    const deltaText = item.delta > 0 ? `+${item.delta}` : "-";

    article.innerHTML = `
      <div class="trend-top">
        <div class="rank-badge">${item.rank}</div>
        <div class="trend-main">
          <div class="trend-title-row">
            <div class="trend-title">${escapeHtml(item.keyword)}</div>
            <div class="chip">${escapeHtml(item.category)}</div>
          </div>
          <div style="margin-top:6px; font-size:12px; opacity:0.72;">변동 ${deltaText}</div>
          <p class="summary">${escapeHtml(item.summary)}</p>
          <div class="headline-preview" style="margin-top:10px;">
            ${previewHeadlines.map((h) => `
              <div class="preview-item" style="margin:6px 0; opacity:0.92;">
                • ${escapeHtml(h)}
              </div>
            `).join("")}
          </div>
          <div class="item-actions">
            <button class="action-btn" data-action="detail">자세히</button>
            <button class="action-btn" data-action="favorite">${state.favorites.includes(item.keyword) ? "★ 저장됨" : "☆ 저장"}</button>
          </div>
        </div>
      </div>
    `;

    article.querySelector('[data-action="detail"]').addEventListener("click", () => openDetail(item));
    article.querySelector('[data-action="favorite"]').addEventListener("click", () => toggleFavorite(item.keyword));

    el.list.appendChild(article);
  });
}

function openDetail(item) {
  state.selected = item;
  el.detailRank.textContent = `${item.rank}위 · ${item.category}`;
  el.detailKeyword.textContent = item.keyword;
  el.detailSummary.textContent = item.summary;

  if (item.links && item.links.length) {
    el.detailLinks.innerHTML = item.links.map((link, index) => `
      <a class="link-item" href="${link.url}" target="_blank" rel="noopener noreferrer"
         style="display:block; padding:12px; margin:10px 0; border:1px solid rgba(255,255,255,0.12); border-radius:14px; text-decoration:none; color:inherit;">
        <div style="font-weight:700; margin-bottom:6px;">${index + 1}. ${escapeHtml(link.title || link.url)}</div>
        <div style="font-size:13px; opacity:0.75;">${escapeHtml(link.source || "뉴스")} ${link.pubDate ? "· " + escapeHtml(link.pubDate) : ""}</div>
      </a>
    `).join("");
  } else {
    el.detailLinks.innerHTML = '<div class="empty">현재 연결된 기사 정보가 없어요.</div>';
  }

  el.favoriteBtn.textContent = state.favorites.includes(item.keyword) ? "즐겨찾기 해제" : "즐겨찾기";
  el.detailSheet.classList.remove("hidden");
}

function closeDetail() {
  el.detailSheet.classList.add("hidden");
}

function openFavorites() {
  renderFavorites();
  el.favoritesSheet.classList.remove("hidden");
}

function closeFavorites() {
  el.favoritesSheet.classList.add("hidden");
}

function renderFavorites() {
  if (!state.favorites.length) {
    el.favoriteList.innerHTML = '<div class="empty">저장한 키워드가 아직 없어요.</div>';
    return;
  }

  const currentMap = new Map(state.trends.map((item) => [item.keyword, item]));
  el.favoriteList.innerHTML = state.favorites.map((keyword) => {
    const item = currentMap.get(keyword);
    return `
      <div class="favorite-item" data-key="${escapeHtml(keyword)}">
        <div>${escapeHtml(keyword)}</div>
        <div class="favorite-meta">${escapeHtml(item ? item.summary : "현재 목록에는 없지만 저장된 키워드입니다.")}</div>
      </div>
    `;
  }).join("");

  el.favoriteList.querySelectorAll(".favorite-item").forEach((node) => {
    node.addEventListener("click", () => {
      const item = currentMap.get(node.dataset.key);
      if (item) {
        closeFavorites();
        openDetail(item);
      }
    });
  });
}

function toggleFavorite(keyword) {
  const idx = state.favorites.indexOf(keyword);
  if (idx >= 0) {
    state.favorites.splice(idx, 1);
  } else {
    state.favorites.unshift(keyword);
  }

  saveFavorites();
  renderCurrentList();

  if (state.selected && state.selected.keyword === keyword) {
    el.favoriteBtn.textContent = state.favorites.includes(keyword) ? "즐겨찾기 해제" : "즐겨찾기";
  }

  renderFavorites();
}

function showCachedOrSampleImmediately() {
  const cached = loadCache(cacheKeyForCategory(state.category));

  if (cached && Array.isArray(cached.trends) && cached.trends.length) {
    state.trends = cached.trends;
    el.updatedAt.textContent = formatTime(cached.updatedAt || Date.now());
    renderStatus("cached");
    renderCurrentList();
    return;
  }

  state.trends = SAMPLE_TRENDS;
  el.updatedAt.textContent = formatTime(Date.now());
  renderStatus("sample");
  renderCurrentList();
}

async function fetchAndRender() {
  if (state.isRefreshing) return;
  state.isRefreshing = true;
  renderStatus("updating");

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 15000);

    const response = await fetch(
      `${API_BASE}/trends?category=${encodeURIComponent(state.category)}&limit=20`,
      {
        cache: "no-store",
        signal: controller.signal
      }
    );

    clearTimeout(timeoutId);

    if (!response.ok) {
      throw new Error("서버 응답 실패");
    }

    const data = await response.json();
    const trends = normalizeServerData(data);

    if (!trends.length) {
      throw new Error("데이터 없음");
    }

    state.trends = trends;
    saveCache(cacheKeyForCategory(state.category), {
      updatedAt: Date.now(),
      trends
    });

    el.updatedAt.textContent = formatTime(Date.now());
    renderStatus("live");
    renderCurrentList();
  } catch (error) {
    const cached = loadCache(cacheKeyForCategory(state.category));

    if (cached && Array.isArray(cached.trends) && cached.trends.length) {
      state.trends = cached.trends;
      el.updatedAt.textContent = formatTime(cached.updatedAt || Date.now());
      renderStatus("cached");
      renderCurrentList();
    } else {
      state.trends = SAMPLE_TRENDS;
      el.updatedAt.textContent = formatTime(Date.now());
      renderStatus("sample");
      renderCurrentList();
    }
  } finally {
    state.isRefreshing = false;
  }
}

function bindEvents() {
  el.refreshBtn.addEventListener("click", () => fetchAndRender());

  el.searchInput.addEventListener("input", (e) => {
    state.search = e.target.value;
    renderCurrentList();
  });

  el.closeDetailBtn.addEventListener("click", closeDetail);
  el.sheetBackdrop.addEventListener("click", closeDetail);

  el.favoriteBtn.addEventListener("click", () => {
    if (state.selected) toggleFavorite(state.selected.keyword);
  });

  el.shareBtn.addEventListener("click", async () => {
    if (!state.selected) return;
    const text = `${state.selected.keyword} - ${state.selected.summary}`;

    try {
      if (navigator.share) {
        await navigator.share({
          title: state.selected.keyword,
          text
        });
      } else {
        await navigator.clipboard.writeText(text);
        alert("요약을 복사했어요.");
      }
    } catch {}
  });

  el.showFavoritesBtn.addEventListener("click", openFavorites);
  el.closeFavoritesBtn.addEventListener("click", closeFavorites);
  el.favoritesBackdrop.addEventListener("click", closeFavorites);
}

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("./service-worker.js").catch(() => {});
  });
}

renderTabs();
bindEvents();
showCachedOrSampleImmediately();
fetchAndRender();
