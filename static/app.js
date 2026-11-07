"use strict";

// The dashboard: start a crawl, see them all, and watch the selected one.

const LIST_REFRESH_MS = 2500;

const crawlerForm = document.getElementById("crawler-form");
const formError = document.getElementById("form-error");
const crawlerList = document.getElementById("crawler-list");
const crawlDetail = document.getElementById("crawl-detail");
const limitsToggle = document.getElementById("limits-toggle");

let crawlers = [];
let selectedId = new URLSearchParams(window.location.search).get("crawl");
let openedId = null;

const crawlView = new CrawlView(crawlDetail, {
  showFullStatus: true,
  onStatus: (status) => {
    const index = crawlers.findIndex((crawler) => crawler.crawler_id === status.crawler_id);
    if (index === -1) return;
    crawlers[index] = status;
    renderList();
  },
  onGone: () => {
    selectedId = null;
    openedId = null;
    refreshList();
  },
});

function barSegments(crawler) {
  const parts = [
    ["indexed", crawler.pages_crawled],
    ["skipped", crawler.skipped_pages],
    ["failed", crawler.failed_pages],
    ["redirected", crawler.redirected_pages],
    ["waiting", crawler.queue_size],
  ];
  const total = parts.reduce((sum, [, count]) => sum + count, 0);
  const bar = element("div", "bar");
  bar.setAttribute("aria-hidden", "true");
  if (total) {
    for (const [name, count] of parts) {
      if (!count) continue;
      const segment = element("i", `b-${name}`);
      segment.style.width = `${(count / total) * 100}%`;
      bar.append(segment);
    }
  }
  return bar;
}

function buildRow(crawler) {
  const item = element("li");
  const row = element("button", "job");
  row.type = "button";
  row.dataset.id = crawler.crawler_id;
  row.setAttribute("aria-current", String(crawler.crawler_id === selectedId));
  const top = element("div", "job-top");
  top.append(element("span", "job-host", hostOf(crawler.origin)), element("span", `job-status status-${crawler.status}`, crawler.status));
  const counts = [
    `${numberFormat.format(crawler.pages_crawled)} indexed`,
    `${numberFormat.format(crawler.skipped_pages)} skipped`,
    `${numberFormat.format(crawler.failed_pages)} failed`,
    `${numberFormat.format(crawler.redirected_pages)} redirected`,
    `${numberFormat.format(crawler.queue_size)} waiting`,
  ].join(" · ");
  row.append(top, barSegments(crawler), element("div", "job-counts", counts));
  row.addEventListener("click", () => selectCrawler(crawler.crawler_id, { reveal: true }));
  item.append(row);
  return item;
}

function renderList() {
  const focusedId = document.activeElement && document.activeElement.classList.contains("job") ? document.activeElement.dataset.id : null;
  if (!crawlers.length) {
    crawlerList.replaceChildren(element("li", "no-crawls", "No crawls yet."));
    return;
  }
  crawlerList.replaceChildren(...crawlers.map(buildRow));
  if (focusedId) {
    const again = crawlerList.querySelector(`[data-id="${CSS.escape(focusedId)}"]`);
    if (again) again.focus({ preventScroll: true });
  }
}

function showFirstRun() {
  crawlView.close();
  if (crawlDetail.querySelector(".first-run")) return;
  const box = element("div", "first-run");
  const words = element("div");
  const demo = element("button", "btn btn-primary first-run-demo", "Crawl the demo site");
  demo.type = "button";
  demo.addEventListener("click", startDemo);
  words.append(
    element("h2", "", "Start your first crawl"),
    element("p", "", "Enter a starting address above and press Start crawl. Each address the crawler reaches appears here on a map, with the reason it was indexed, skipped or failed."),
    element("p", "", "To see it work first, crawl the demo site that comes with the app: a small recipe site served from this computer, with a few broken links and blocked pages on purpose."),
    demo,
    element("p", "", "Pages can be searched as soon as they are indexed. If the app closes during a crawl, finished pages are safe and the crawl can be resumed."),
    element("p", "", "On sites you don't own, keep the page limit and the speed low.")
  );
  const map = new CrawlMap();
  map.configure({ seed: "first run", origin: "", maxDepth: 2 });
  map.node.setAttribute("aria-label", "An empty crawl map");
  box.append(words, map.node);
  crawlDetail.replaceChildren(box);
}

// The demo site is served by this app. The crawler asks for it at 127.0.0.1, where the app listens,
// even if this page was opened as localhost. The form is filled in so it shows what was asked for.
function startDemo() {
  const port = window.location.port ? `:${window.location.port}` : "";
  crawlerForm.origin.value = `http://127.0.0.1${port}/demo/`;
  crawlerForm.max_depth.value = "3";
  crawlerForm.max_pages.value = "200";
  crawlerForm.hit_rate.value = "8";
  crawlerForm.requestSubmit();
}

function selectCrawler(id, { reveal = false } = {}) {
  selectedId = id;
  const url = new URL(window.location.href);
  url.searchParams.set("crawl", id);
  window.history.replaceState(null, "", url);
  renderList();
  if (id !== openedId) {
    openedId = id;
    crawlView.open(id);
  }
  // Where the list sits above the crawl, picking one should bring it into view.
  if (reveal && window.matchMedia("(max-width: 820px)").matches) crawlDetail.scrollIntoView({ block: "start" });
}

async function refreshList() {
  let data;
  try {
    data = await getJson("/api/crawlers");
  } catch {
    return; // the selected crawl's view already reports lost contact
  }
  crawlers = data.crawlers.reverse(); // newest first
  if (!crawlers.length) {
    renderList();
    showFirstRun();
    return;
  }
  if (!crawlers.some((crawler) => crawler.crawler_id === selectedId)) {
    const running = crawlers.find((crawler) => crawler.status === "running");
    selectCrawler((running || crawlers[0]).crawler_id);
    return;
  }
  renderList();
  if (selectedId !== openedId) selectCrawler(selectedId);
}

crawlerForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  formError.hidden = true;
  const submit = crawlerForm.querySelector("button[type=submit]");
  submit.disabled = true;
  const result = await postJson("/api/crawlers", {
    origin: crawlerForm.origin.value,
    max_depth: crawlerForm.max_depth.value,
    max_pages: crawlerForm.max_pages.value,
    hit_rate: crawlerForm.hit_rate.value,
    queue_limit: crawlerForm.queue_limit.value,
  });
  submit.disabled = false;
  if (!result.ok) {
    formError.textContent = result.data.message || "The crawl could not be started.";
    formError.hidden = false;
    setLimitsOpen(true); // the problem may be one of them, and on a phone they start hidden
    crawlerForm.origin.focus();
    return;
  }
  crawlerForm.origin.value = "";
  crawlers.unshift(result.data.crawler);
  selectCrawler(result.data.crawler.crawler_id, { reveal: true });
});

function setLimitsOpen(isOpen) {
  limitsToggle.setAttribute("aria-expanded", String(isOpen));
  document.getElementById("limits").classList.toggle("is-open", isOpen);
}

limitsToggle.addEventListener("click", () => setLimitsOpen(limitsToggle.getAttribute("aria-expanded") !== "true"));

refreshList();
setInterval(() => {
  refreshList();
  refreshTotals();
}, LIST_REFRESH_MS);
