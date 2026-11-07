"use strict";

const PAGE_SIZES = [10, 25, 50, 100];
const DEFAULT_PAGE_SIZE = 10;
const LOADING_DELAY_MS = 150; // most searches finish sooner, and a flash of loading looks like a glitch

const form = document.getElementById("search-form");
const queryInput = document.getElementById("search-query");
const sortSelect = document.getElementById("search-sort");
const sizeSelect = document.getElementById("search-size");
const luckyButton = document.getElementById("lucky-btn");
const panel = document.getElementById("search-panel");
const summary = document.getElementById("results-summary");
const resultsArea = document.getElementById("results-area");
const pagination = document.getElementById("pagination");
const prevButton = document.getElementById("prev-page-btn");
const nextButton = document.getElementById("next-page-btn");
const pageLabel = document.getElementById("page-label");

const state = { query: "", sort: "relevance", size: DEFAULT_PAGE_SIZE, page: 1 };
let luckyWord = null;
let currentRequest = null;
let loadingTimer = null;

// ---------- Address bar ----------
function readUrl() {
  const params = new URLSearchParams(window.location.search);
  const size = Number(params.get("size"));
  const page = Number(params.get("page"));
  state.query = (params.get("q") || "").trim();
  state.sort = params.get("sort") === "depth" ? "depth" : "relevance";
  state.size = PAGE_SIZES.includes(size) ? size : DEFAULT_PAGE_SIZE;
  state.page = Number.isInteger(page) && page > 0 ? page : 1;
}

function urlForState() {
  const params = new URLSearchParams();
  if (state.query) params.set("q", state.query);
  if (state.sort !== "relevance") params.set("sort", state.sort);
  if (state.size !== DEFAULT_PAGE_SIZE) params.set("size", String(state.size));
  if (state.page > 1) params.set("page", String(state.page));
  const text = params.toString();
  return text ? `${window.location.pathname}?${text}` : window.location.pathname;
}

function rememberState() {
  const url = urlForState();
  if (url !== window.location.pathname + window.location.search) {
    window.history.pushState(null, "", url);
  }
}

function syncForm() {
  queryInput.value = state.query;
  sortSelect.value = state.sort;
  sizeSelect.value = String(state.size);
}

// ---------- Talking to the server ----------
function beginRequest() {
  if (currentRequest) currentRequest.abort();
  currentRequest = new AbortController();
  clearTimeout(loadingTimer);
  loadingTimer = setTimeout(showLoading, LOADING_DELAY_MS);
  return currentRequest;
}

function endLoading() {
  clearTimeout(loadingTimer);
  resultsArea.removeAttribute("aria-busy");
}

// ---------- Small pieces ----------
function setSummary(...parts) {
  summary.replaceChildren(...parts);
}

function hidePagination() {
  pagination.hidden = true;
}

// ---------- States ----------
function showState({ title, text, action, alert = false }) {
  const box = element("div", "search-state");
  if (alert) box.setAttribute("role", "alert");
  box.append(element("h2", "", title), element("p", "", text));
  if (action) box.append(action);
  resultsArea.replaceChildren(box);
  hidePagination();
}

function dashboardLink() {
  const link = element("a", "btn btn-primary", "Start a crawl");
  link.href = "/";
  return link;
}

function showNothingIndexed() {
  setSummary();
  showState({
    title: "Nothing to search yet",
    text: "Start a crawl from the dashboard. Pages can be searched as soon as they are indexed.",
    action: dashboardLink(),
  });
}

function showLoading() {
  resultsArea.setAttribute("aria-busy", "true");
  if (resultsArea.querySelector(".result")) return; // keep the old results, dimmed, until the new ones arrive
  setSummary("Searching…");
  hidePagination();
  const skeleton = element("div", "skeleton");
  skeleton.setAttribute("aria-hidden", "true");
  for (let n = 0; n < 3; n += 1) {
    const row = element("div", "skeleton-result");
    row.append(element("div", "skeleton-line skeleton-title"), element("div", "skeleton-line"), element("div", "skeleton-line skeleton-short"));
    skeleton.append(row);
  }
  resultsArea.replaceChildren(skeleton);
}

function showError(message) {
  setSummary();
  const retry = element("button", "btn btn-secondary", "Try again");
  retry.type = "button";
  retry.addEventListener("click", () => runSearch());
  showState({ title: "Search did not work", text: message, action: retry, alert: true });
}

async function showStart(signal) {
  setSummary();
  hidePagination();
  const stats = await getJson("/api/stats", signal);
  if (!stats.indexed_documents) {
    showNothingIndexed();
    return;
  }
  showState({
    title: "What are you looking for?",
    text: `${plural(stats.indexed_documents, "page")} and ${plural(stats.unique_terms, "different word")} are ready to search. Capitals and accents don't matter, so "turkiye" finds "Türkiye".`,
  });
}

async function showNoResults(signal) {
  const stats = await getJson("/api/stats", signal).catch((error) => {
    if (error.name === "AbortError") throw error;
    return null;
  });
  if (stats && !stats.indexed_documents) {
    showNothingIndexed();
    return;
  }
  setSummary("0 results");
  showState({
    title: `No pages contain "${state.query}"`,
    text: "Check the spelling or try fewer words. Only pages you have crawled are searched, so a new crawl may find it.",
  });
}

// ---------- Results ----------
function appendHighlighted(parent, text, highlights) {
  // The server counts characters. JavaScript strings count UTF-16 units, which differ after an emoji.
  const characters = Array.from(text);
  let position = 0;
  for (const [start, end] of highlights) {
    if (start < position || end > characters.length) continue;
    parent.append(characters.slice(position, start).join(""));
    parent.append(element("mark", "", characters.slice(start, end).join("")));
    position = end;
  }
  parent.append(characters.slice(position).join(""));
}

function buildResult(result) {
  const item = element("li", "result");
  const heading = element("h2", "result-title");
  const titleText = result.title || readableUrl(result.url);
  const href = safeLink(result.url);
  if (href) {
    const link = element("a", "", titleText);
    link.href = href;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    heading.append(link);
  } else {
    heading.textContent = titleText;
  }
  item.append(heading);

  const address = element("div", "result-url", readableUrl(result.url));
  address.title = result.url;
  item.append(address);

  if (result.snippet) {
    const snippet = element("p", "result-snippet");
    appendHighlighted(snippet, result.snippet, result.highlights || []);
    item.append(snippet);
  }

  if (result.missing_terms && result.missing_terms.length) {
    const missing = element("p", "result-missing", "Missing: ");
    result.missing_terms.forEach((term, index) => {
      if (index) missing.append(", ");
      missing.append(element("s", "", term));
    });
    item.append(missing);
  }

  const meta = element("div", "result-meta");
  const depth = element("span", "depth-chip", `Depth ${result.depth}`);
  depth.style.background = depthTint(result.depth);
  meta.append(depth, element("span", "", `Found ${plural(result.frequency, "time")}`), element("span", "", `Relevance ${result.relevance_score}`));
  const origin = element("span", "", `From ${hostOf(result.origin)}`);
  origin.title = result.origin;
  meta.append(origin);
  if (result.crawler_id) {
    const onMap = element("a", "", "See it on its map");
    onMap.href = `/crawler/${encodeURIComponent(result.crawler_id)}?address=${encodeURIComponent(result.url)}`;
    meta.append(onMap);
  }
  item.append(meta);
  return item;
}

function showResults(payload) {
  const count = plural(payload.total_results, "result");
  const query = element("strong", "", payload.query);
  if (luckyWord) {
    setSummary(`Lucky word `, query, `: ${count}`);
  } else {
    setSummary(`${count} for `, query);
  }

  const list = element("ol", "results");
  list.start = (payload.page - 1) * payload.page_size + 1;
  list.append(...payload.results.map(buildResult));
  resultsArea.replaceChildren(list);

  pagination.hidden = payload.total_pages <= 1;
  pageLabel.textContent = `Page ${numberFormat.format(payload.page)} of ${numberFormat.format(payload.total_pages)}`;
  prevButton.disabled = !payload.has_prev;
  nextButton.disabled = !payload.has_next;
}

// ---------- Searching ----------
async function runSearch() {
  const request = beginRequest();
  document.title = state.query ? `${state.query} - Search` : "Search";
  try {
    if (state.query) {
      await searchAndShow(request.signal);
    } else {
      await showStart(request.signal);
    }
  } catch (error) {
    if (error.name !== "AbortError") showError(error.message); // aborted means a newer search owns the screen
  } finally {
    if (request === currentRequest) endLoading();
  }
}

async function searchAndShow(signal) {
  const params = new URLSearchParams({
    query: state.query,
    sortBy: state.sort,
    page: String(state.page),
    page_size: String(state.size),
  });
  const payload = await getJson(`/search?${params}`, signal);
  if (!payload.terms.length) {
    setSummary();
    showState({ title: "Nothing to look for", text: "Search for at least one letter or number." });
  } else if (!payload.total_results) {
    await showNoResults(signal);
  } else {
    if (payload.page !== state.page) {
      state.page = payload.page; // the page asked for no longer exists, so the server gave the last one
      window.history.replaceState(null, "", urlForState());
    }
    showResults(payload);
  }
}

function newSearch() {
  state.page = 1;
  luckyWord = null;
  rememberState();
  runSearch();
}

async function goToPage(page) {
  state.page = page;
  rememberState();
  await runSearch();
  // Start reading the new page from the top, and keep keyboard users in the same place.
  if (panel.getBoundingClientRect().top < 0) panel.scrollIntoView({ block: "start" });
  summary.focus({ preventScroll: true });
}

async function feelingLucky() {
  const request = beginRequest();
  try {
    const lucky = await getJson("/lucky?page_size=1", request.signal);
    if (!lucky.term) {
      endLoading();
      state.query = "";
      syncForm();
      rememberState();
      showNothingIndexed();
      return;
    }
    state.query = lucky.term;
    state.page = 1;
    luckyWord = lucky.term;
    syncForm();
    rememberState();
    runSearch();
  } catch (error) {
    if (error.name === "AbortError") return;
    endLoading();
    showError(error.message);
  }
}

// ---------- Controls ----------
form.addEventListener("submit", (event) => {
  event.preventDefault();
  state.query = queryInput.value.trim();
  newSearch();
});

sortSelect.addEventListener("change", () => {
  state.sort = sortSelect.value;
  newSearch();
});

sizeSelect.addEventListener("change", () => {
  state.size = Number(sizeSelect.value);
  newSearch();
});

luckyButton.addEventListener("click", feelingLucky);
prevButton.addEventListener("click", () => goToPage(state.page - 1));
nextButton.addEventListener("click", () => goToPage(state.page + 1));

window.addEventListener("popstate", () => {
  luckyWord = null;
  readUrl();
  syncForm();
  runSearch();
});

readUrl();
syncForm();
if (!state.query) queryInput.focus();
runSearch();
