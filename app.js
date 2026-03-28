const API_BASE = "https://trendpick-api.onrender.com";
const CATEGORY_FEEDS = {
  "전체": "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko",
  "정치": "https://news.google.com/rss/headlines/section/topic/POLITICS?hl=ko&gl=KR&ceid=KR:ko",
  "경제": "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=ko&gl=KR&ceid=KR:ko",
  "스포츠": "https://news.google.com/rss/headlines/section/topic/SPORTS?hl=ko&gl=KR&ceid=KR:ko",
  "연예": "https://news.google.com/rss/search?q=%EC%97%B0%EC%98%88&hl=ko&gl=KR&ceid=KR:ko",
  "게임": "https://news.google.com/rss/search?q=%EA%B2%8C%EC%9E%84&hl=ko&gl=KR&ceid=KR:ko"
};

const SAMPLE_TRENDS = [
  { keyword:"환율", category:"경제", summary:"환율 변동 기사와 해외 증시 이슈가 겹치며 관심이 커졌습니다.", headlines:["원달러 환율 변동성 확대", "해외 증시 불안에 환율 관심 증가"], links:[] },
  { keyword:"챔피언스리그", category:"스포츠", summary:"유럽 축구 주요 경기 결과와 하이라이트 확산으로 검색이 늘었습니다.", headlines:["챔피언스리그 8강 확정", "빅매치 하이라이트 화제"], links:[] },
  { keyword:"미세먼지", category:"전체", summary:"대기질 예보와 외출 전 확인 수요가 겹치며 다시 검색량이 올랐습니다.", headlines:["전국 초미세먼지 농도 상승", "주말 미세먼지 예보 관심"], links:[] },
  { keyword:"신작 모바일게임", category:"게임", summary:"신작 출시와 사전예약 보상 소식이 퍼지며 관심이 모였습니다.", headlines:["모바일 신작 출시 예고", "사전예약 보상 공개"], links:[] }
];

const STOPWORDS = new Set([
  "속보","단독","라이브","뉴스","영상","사진","기자","오늘","내일","오전","오후","관련","대한","에서","으로","했다","있다","위해","대한민국",
  "정부","한국","서울","국내","세계","미국","중국","일본","이슈","발표","공개","진행","주요","최신","공식","현장","문제","사건","결과","논란",
  "사람들","이유","반응","확인","현황","대응","후보","대통령","대표","국회","장관","대해","요약","분석","취재","보도"
]);

const state = {
  category: "전체",
  search: "",
  trends: [],
  selected: null,
  favorites: loadFavorites()
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
  try { return JSON.parse(raw); } catch { return null; }
}

function loadFavorites() {
  return loadCache("trendpick-favorites") || [];
}

function saveFavorites() {
  saveCache("trendpick-favorites", state.favorites);
}

function renderTabs() {
  el.tabs.innerHTML = "";
  Object.keys(CATEGORY_FEEDS).forEach((name) => {
    const btn = document.createElement("button");
    btn.className = "tab" + (state.category === name ? " active" : "");
    btn.textContent = name;
    btn.addEventListener("click", () => {
      state.category = name;
      renderTabs();
      fetchAndRender();
    });
    el.tabs.appendChild(btn);
  });
}

function setLoading() {
  el.list.innerHTML = '<div class="loading-card">뉴스에서 키워드를 불러오는 중...</div>';
}

function setError(message) {
  el.list.innerHTML = `<div class="error-card">${message}</div>`;
}

function formatTime(date) {
  const d = new Date(date);
  return d.toLocaleString("ko-KR", { month:"2-digit", day:"2-digit", hour:"2-digit", minute:"2-digit" });
}

function normalizeText(text) {
  return text
    .replace(/&quot;|&#39;|&amp;/g, " ")
    .replace(/\[[^\]]+\]/g, " ")
    .replace(/[()"'.,!?~:;|/\\\-]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function extractKeywords(title) {
  const text = normalizeText(title);
  const matches = text.match(/[가-힣A-Za-z0-9]{2,}/g) || [];
  return matches.filter(token => {
    const lower = token.toLowerCase();
    if (STOPWORDS.has(token) || STOPWORDS.has(lower)) return false;
    if (/^\d+$/.test(token)) return false;
    if (token.length < 2) return false;
    if (token.length > 18) return false;
    return true;
  });
}

function summarize(keyword, headlines, category) {
  const pieces = [];
  if (headlines[0]) pieces.push(`'${keyword}' 관련 기사 노출이 늘었습니다.`);
  if (category === "경제") pieces.push("시장과 생활 영향 이슈가 함께 묶여 관심이 커진 모습입니다.");
  else if (category === "스포츠") pieces.push("경기 결과나 일정, 하이라이트 확산이 검색량을 끌어올린 것으로 보입니다.");
  else if (category === "연예") pieces.push("방송 출연이나 인터뷰, 화제성 높은 소식이 관심을 모으는 중입니다.");
  else if (category === "게임") pieces.push("출시 소식이나 업데이트, 커뮤니티 반응이 함께 붙고 있습니다.");
  else if (category === "정치") pieces.push("정책 발표나 인물 관련 보도가 연달아 이어지며 주목도가 올라간 흐름입니다.");
  else pieces.push("비슷한 제목의 기사가 짧은 시간에 늘어나며 급상승 키워드로 잡혔습니다.");
  return pieces.join(" ");
}

function trendFromArticles(items, category) {
  const keywordMap = new Map();

  items.forEach((item) => {
    const title = normalizeText(item.title || "");
    if (!title) return;
    const keywords = extractKeywords(title).slice(0, 6);
    keywords.forEach((keyword) => {
      if (!keywordMap.has(keyword)) {
        keywordMap.set(keyword, {
          keyword,
          category,
          score: 0,
          headlines: [],
          links: []
        });
      }
      const entry = keywordMap.get(keyword);
      entry.score += 1;
      if (entry.headlines.length < 4 && !entry.headlines.includes(title)) {
        entry.headlines.push(title);
      }
      if (entry.links.length < 5 && item.link) {
        entry.links.push({
          title,
          url: item.link,
          source: item.author || item.source || "뉴스",
          pubDate: item.pubDate || item.published
        });
      }
    });
  });

  const trends = Array.from(keywordMap.values())
    .filter(item => item.score >= 2 || item.headlines.length >= 2)
    .sort((a, b) => b.score - a.score)
    .slice(0, 20)
    .map((item, index) => ({
      rank: index + 1,
      keyword: item.keyword,
      category,
      summary: summarize(item.keyword, item.headlines, category),
      headlines: item.headlines,
      links: item.links
    }));

  return trends.length ? trends : SAMPLE_TRENDS.map((x, i) => ({...x, category: category === "전체" ? x.category : category, rank: i + 1}));
}

async function fetchRss(category) {
  const rssUrl = CATEGORY_FEEDS[category];
  const proxy = "https://api.rss2json.com/v1/api.json?rss_url=" + encodeURIComponent(rssUrl);
  const response = await fetch(proxy, { cache: "no-store" });
  if (!response.ok) throw new Error("rss2json 응답 실패");
  const data = await response.json();
  if (!data.items || !Array.isArray(data.items)) throw new Error("기사 목록 없음");
  return data.items;
}

function filterBySearch(items) {
  if (!state.search.trim()) return items;
  const q = state.search.trim().toLowerCase();
  return items.filter((item) =>
    item.keyword.toLowerCase().includes(q) ||
    item.summary.toLowerCase().includes(q) ||
    item.headlines.some(h => h.toLowerCase().includes(q))
  );
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
    article.innerHTML = `
      <div class="trend-top">
        <div class="rank-badge">${item.rank}</div>
        <div class="trend-main">
          <div class="trend-title-row">
            <div class="trend-title">${item.keyword}</div>
            <div class="chip">${item.category}</div>
          </div>
          <p class="summary">${item.summary}</p>
          <div class="headline-preview">
            ${item.headlines.slice(0, 3).map(h => `<div class="preview-item">${escapeHtml(h)}</div>`).join("")}
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

function escapeHtml(text) {
  return text
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function openDetail(item) {
  state.selected = item;
  el.detailRank.textContent = `${item.rank}위 · ${item.category}`;
  el.detailKeyword.textContent = item.keyword;
  el.detailSummary.textContent = item.summary;
  el.detailLinks.innerHTML = item.links.length
    ? item.links.map(link => `
      <a class="link-item" href="${link.url}" target="_blank" rel="noopener noreferrer">
        <div>${escapeHtml(link.title)}</div>
        <div class="link-source">${escapeHtml(link.source || "뉴스")} · ${link.pubDate ? formatTime(link.pubDate) : ""}</div>
      </a>
    `).join("")
    : '<div class="empty">연결된 기사 정보가 아직 없어요.</div>';

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
  const currentMap = new Map(state.trends.map(item => [item.keyword, item]));
  el.favoriteList.innerHTML = state.favorites.map(keyword => {
    const item = currentMap.get(keyword);
    return `
      <div class="favorite-item" data-key="${keyword}">
        <div>${keyword}</div>
        <div class="favorite-meta">${item ? item.summary : "현재 목록에는 없지만 저장된 키워드입니다."}</div>
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
  if (idx >= 0) state.favorites.splice(idx, 1);
  else state.favorites.unshift(keyword);
  saveFavorites();
  renderList(filterBySearch(state.trends));
  if (state.selected && state.selected.keyword === keyword) {
    el.favoriteBtn.textContent = state.favorites.includes(keyword) ? "즐겨찾기 해제" : "즐겨찾기";
  }
  renderFavorites();
}

async function fetchAndRender() {
  setLoading();
  el.sourceState.textContent = "불러오는 중";
  try {
    const items = await fetchRss(state.category);
    const trends = trendFromArticles(items, state.category);
    state.trends = trends;
    saveCache("trendpick-last-success", { updatedAt: Date.now(), category: state.category, trends });
    el.updatedAt.textContent = formatTime(Date.now());
    el.sourceState.textContent = "실시간 뉴스";
    renderList(filterBySearch(trends));
  } catch (error) {
    const cached = loadCache("trendpick-last-success");
    if (cached && cached.trends?.length) {
      state.trends = cached.trends;
      el.updatedAt.textContent = formatTime(cached.updatedAt);
      el.sourceState.textContent = "마지막 저장 데이터";
      renderList(filterBySearch(cached.trends));
    } else {
      state.trends = SAMPLE_TRENDS.map((item, index) => ({ ...item, rank: index + 1, category: state.category === "전체" ? item.category : state.category }));
      el.updatedAt.textContent = formatTime(Date.now());
      el.sourceState.textContent = "샘플 데이터";
      renderList(filterBySearch(state.trends));
    }
  }
}

function bindEvents() {
  el.refreshBtn.addEventListener("click", fetchAndRender);
  el.searchInput.addEventListener("input", (e) => {
    state.search = e.target.value;
    renderList(filterBySearch(state.trends));
  });
  el.closeDetailBtn.addEventListener("click", closeDetail);
  el.sheetBackdrop.addEventListener("click", closeDetail);
  el.favoriteBtn.addEventListener("click", () => {
    if (state.selected) toggleFavorite(state.selected.keyword);
  });
  el.shareBtn.addEventListener("click", async () => {
    if (!state.selected) return;
    const text = `${state.selected.keyword} - ${state.selected.summary}`;
    if (navigator.share) {
      await navigator.share({ title: state.selected.keyword, text });
    } else {
      await navigator.clipboard.writeText(text);
      alert("요약을 복사했어요.");
    }
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
fetchAndRender();
