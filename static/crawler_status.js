const crawlerId = window.CRAWLER_ID;
let lastVersion = 0;
let stoppedPolling = false;

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text ?? "";
  return div.innerHTML;
}

function showAlert(message) {
  alert(message);
}

function getStatusBadgeClass(status) {
  const normalized = (status || "").toLowerCase();

  if (["running", "completed"].includes(normalized)) return "green";
  if (["paused", "created"].includes(normalized)) return "yellow";
  if (["stopped", "failed", "error"].includes(normalized)) return "red";
  return "blue";
}

function formatTimestamp(ts) {
  if (!ts) return "-";

  if (typeof ts === "number") {
    return new Date(ts * 1000).toLocaleString();
  }

  const parsed = new Date(ts);
  if (!Number.isNaN(parsed.getTime())) {
    return parsed.toLocaleString();
  }

  return String(ts);
}

function renderCrawlerStatus(crawler) {
  document.getElementById("crawler-title").textContent = crawler.crawler_id || crawlerId;
  document.getElementById("crawler-id-box").textContent = crawler.crawler_id || crawlerId;

  document.getElementById("origin-value").textContent = crawler.origin || "-";
  document.getElementById("depth-value").textContent = crawler.max_depth ?? "-";
  document.getElementById("queue-value").textContent = crawler.queue_size ?? "-";
  document.getElementById("visited-value").textContent = crawler.visited_count ?? "-";

  document.getElementById("pages-value").textContent = crawler.pages_crawled ?? "-";
  document.getElementById("failed-value").textContent = crawler.failed_pages ?? "-";
  document.getElementById("terms-value").textContent = crawler.unique_terms ?? "-";
  document.getElementById("postings-value").textContent = crawler.total_postings ?? "-";

  document.getElementById("docs-value").textContent = crawler.indexed_documents ?? "-";
  document.getElementById("buckets-value").textContent = crawler.bucket_files ?? "-";
  document.getElementById("version-value").textContent = crawler.status_version ?? 0;

  document.getElementById("created-value").textContent = formatTimestamp(crawler.created_at);
  document.getElementById("updated-value").textContent = formatTimestamp(crawler.updated_at_iso || crawler.updated_at);
  document.getElementById("last-version").textContent = crawler.status_version ?? 0;
  document.getElementById("last-updated").textContent = formatTimestamp(crawler.updated_at_iso || crawler.updated_at);

  const badge = document.getElementById("crawler-status-badge");
  badge.textContent = crawler.status || "unknown";
  badge.className = `badge ${getStatusBadgeClass(crawler.status)}`;

  lastVersion = crawler.status_version || 0;
}

async function fetchLogs() {
  const response = await fetch(`/api/crawlers/${encodeURIComponent(crawlerId)}/logs?last_n=200`);
  const data = await response.json();
  const logs = data.logs || [];

  const viewer = document.getElementById("log-viewer");
  viewer.textContent = logs.length ? logs.join("\n") : "No logs found.";
}

async function pollStatus() {
  while (!stoppedPolling) {
    try {
      const response = await fetch(
        `/api/crawlers/${encodeURIComponent(crawlerId)}/wait-status?since_version=${encodeURIComponent(lastVersion)}&timeout=20`
      );

      const data = await response.json();

      if (data.crawler) {
        renderCrawlerStatus(data.crawler);
      }

      if (data.changed) {
        await fetchLogs();
      }
    } catch (error) {
      console.error("Long polling failed:", error);
      await new Promise(resolve => setTimeout(resolve, 1500));
    }
  }
}

async function postAction(action) {
  const response = await fetch(`/api/crawlers/${encodeURIComponent(crawlerId)}/${action}`, {
    method: "POST",
  });

  const data = await response.json();
  showAlert(data.message || `${action} request sent.`);
}

async function initializePage() {
  document.getElementById("pause-btn").addEventListener("click", async () => {
    await postAction("pause");
  });

  document.getElementById("resume-btn").addEventListener("click", async () => {
    await postAction("resume");
  });

  document.getElementById("stop-btn").addEventListener("click", async () => {
    await postAction("stop");
  });

  document.getElementById("restart-btn").addEventListener("click", async () => {
    await postAction("restart");
  });

  document.getElementById("refresh-logs-btn").addEventListener("click", async () => {
    await fetchLogs();
  });

  const initialResponse = await fetch(`/api/crawlers/${encodeURIComponent(crawlerId)}`);
  const initialData = await initialResponse.json();

  if (initialData.message) {
    showAlert(initialData.message);
    return;
  }

  renderCrawlerStatus(initialData);
  await fetchLogs();
  pollStatus();
}

initializePage();

window.addEventListener("beforeunload", () => {
  stoppedPolling = true;
});