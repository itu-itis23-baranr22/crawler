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

  if (["running", "completed", "ready"].includes(normalized)) return "green";
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

function summarizeStatuses(crawlers) {
  let running = 0;
  let paused = 0;
  let finished = 0;

  let totalIndexedDocuments = 0;
  let totalUniqueTerms = 0;
  let totalPostings = 0;
  let totalBucketFiles = 0;

  for (const crawler of crawlers) {
    const status = (crawler.status || "").toLowerCase();

    if (status === "running") running += 1;
    else if (status === "paused") paused += 1;
    else if (["completed", "stopped"].includes(status)) finished += 1;

    totalIndexedDocuments = Math.max(
      totalIndexedDocuments,
      Number(crawler.indexed_documents || 0)
    );
    totalUniqueTerms = Math.max(
      totalUniqueTerms,
      Number(crawler.unique_terms || 0)
    );
    totalPostings = Math.max(
      totalPostings,
      Number(crawler.total_postings || 0)
    );
    totalBucketFiles = Math.max(
      totalBucketFiles,
      Number(crawler.bucket_files || 0)
    );
  }

  return {
    total: crawlers.length,
    running,
    paused,
    finished,
    totalIndexedDocuments,
    totalUniqueTerms,
    totalPostings,
    totalBucketFiles,
  };
}

function goToCrawlerStatus(crawlerId) {
  window.location.href = `/crawler/${encodeURIComponent(crawlerId)}`;
}

function buildCrawlerCard(crawler) {
  const status = crawler.status || "unknown";
  const badgeClass = getStatusBadgeClass(status);

  return `
    <div class="activity-card" style="margin-bottom: 16px;">
      <div class="row" style="align-items: flex-start;">
        <div style="flex: 1;">
          <h3 style="margin-bottom: 8px;">${escapeHtml(crawler.crawler_id || "unknown crawler")}</h3>
          <div class="url-text" style="margin-bottom: 8px;">${escapeHtml(crawler.origin || "")}</div>

          <div class="tag-row">
            <span class="tag">Status: ${escapeHtml(status)}</span>
            <span class="tag">Depth: ${escapeHtml(String(crawler.max_depth ?? "-"))}</span>
            <span class="tag">Max Pages: ${escapeHtml(String(crawler.max_pages ?? "-"))}</span>
            <span class="tag">Pages Crawled: ${escapeHtml(String(crawler.pages_crawled ?? 0))}</span>
            <span class="tag">Visited: ${escapeHtml(String(crawler.visited_count ?? 0))}</span>
            <span class="tag">Failed: ${escapeHtml(String(crawler.failed_pages ?? 0))}</span>
            <span class="tag">Queue Size: ${escapeHtml(String(crawler.queue_size ?? 0))}</span>
            <span class="tag">Hit Rate: ${escapeHtml(String(crawler.hit_rate ?? "-"))}</span>
          </div>

          <div class="tag-row" style="margin-top: 10px;">
            <span class="tag">Indexed Docs: ${escapeHtml(String(crawler.indexed_documents ?? 0))}</span>
            <span class="tag">Unique Terms: ${escapeHtml(String(crawler.unique_terms ?? 0))}</span>
            <span class="tag">Postings: ${escapeHtml(String(crawler.total_postings ?? 0))}</span>
            <span class="tag">Buckets: ${escapeHtml(String(crawler.bucket_files ?? 0))}</span>
          </div>

          <div class="muted-small" style="margin-top: 10px;">
            Created: ${escapeHtml(formatTimestamp(crawler.created_at))}
          </div>
          <div class="muted-small" style="margin-top: 4px;">
            Updated: ${escapeHtml(formatTimestamp(crawler.updated_at_iso || crawler.updated_at))}
          </div>
        </div>

        <span class="badge ${badgeClass}">${escapeHtml(status)}</span>
      </div>

      <div class="button-row" style="margin-top: 16px;">
        <button type="button" class="btn-primary" onclick="goToCrawlerStatus('${escapeHtml(crawler.crawler_id || "")}')">View Status</button>
        <button type="button" class="btn-secondary" onclick="pauseCrawler('${escapeHtml(crawler.crawler_id || "")}')">Pause</button>
        <button type="button" class="btn-secondary" onclick="resumeCrawler('${escapeHtml(crawler.crawler_id || "")}')">Resume</button>
        <button type="button" class="btn-danger" onclick="stopCrawler('${escapeHtml(crawler.crawler_id || "")}')">Stop</button>
        <button type="button" class="btn-secondary" onclick="restartCrawler('${escapeHtml(crawler.crawler_id || "")}')">Restart</button>
        <button type="button" class="btn-primary" onclick="loadLogs('${escapeHtml(crawler.crawler_id || "")}')">View Logs</button>
      </div>
    </div>
  `;
}

async function createCrawler(payload) {
  const response = await fetch("/api/crawlers", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  return await response.json();
}

async function fetchCrawlers() {
  const response = await fetch("/api/crawlers");
  return await response.json();
}

async function postCrawlerAction(crawlerId, action) {
  const response = await fetch(`/api/crawlers/${encodeURIComponent(crawlerId)}/${action}`, {
    method: "POST",
  });

  return await response.json();
}

async function fetchLogs(crawlerId) {
  const response = await fetch(`/api/crawlers/${encodeURIComponent(crawlerId)}/logs?last_n=100`);
  return await response.json();
}

async function refreshCrawlerList() {
  const data = await fetchCrawlers();
  const crawlers = data.crawlers || [];

  const listEl = document.getElementById("crawler-list");
  const countLabel = document.getElementById("crawler-count-label");

  countLabel.textContent = `${crawlers.length} crawlers`;

  if (crawlers.length === 0) {
    listEl.innerHTML = `<div class="result-card">No crawlers created yet.</div>`;
  } else {
    listEl.innerHTML = crawlers.map(buildCrawlerCard).join("");
  }

  const summary = summarizeStatuses(crawlers);

  document.getElementById("total-crawlers").textContent = summary.total;
  document.getElementById("running-crawlers").textContent = summary.running;
  document.getElementById("paused-crawlers").textContent = summary.paused;
  document.getElementById("finished-crawlers").textContent = summary.finished;

  document.getElementById("loaded-jobs").textContent = summary.total;
  document.getElementById("running-jobs").textContent = summary.running;
  document.getElementById("paused-jobs").textContent = summary.paused;
  document.getElementById("finished-jobs").textContent = summary.finished;

  document.getElementById("total-indexed-documents").textContent = summary.totalIndexedDocuments;
  document.getElementById("total-unique-terms").textContent = summary.totalUniqueTerms;
  document.getElementById("total-postings").textContent = summary.totalPostings;
  document.getElementById("total-bucket-files").textContent = summary.totalBucketFiles;

  const systemHealth = document.getElementById("system-health");
  if (summary.running > 0) {
    systemHealth.textContent = "Running";
    systemHealth.className = "badge green";
  } else if (summary.paused > 0) {
    systemHealth.textContent = "Paused";
    systemHealth.className = "badge yellow";
  } else {
    systemHealth.textContent = "Ready";
    systemHealth.className = "badge green";
  }
}

async function loadLogs(crawlerId) {
  const data = await fetchLogs(crawlerId);
  const logs = data.logs || [];

  document.getElementById("selected-log-label").textContent = crawlerId;

  const logViewer = document.getElementById("log-viewer");
  if (logs.length === 0) {
    logViewer.textContent = "No logs found.";
    return;
  }

  logViewer.textContent = logs.join("\n");
}

async function pauseCrawler(crawlerId) {
  const data = await postCrawlerAction(crawlerId, "pause");
  showAlert(data.message || "Pause request sent.");
  await refreshCrawlerList();
}

async function resumeCrawler(crawlerId) {
  const data = await postCrawlerAction(crawlerId, "resume");
  showAlert(data.message || "Resume request sent.");
  await refreshCrawlerList();
}

async function stopCrawler(crawlerId) {
  const data = await postCrawlerAction(crawlerId, "stop");
  showAlert(data.message || "Stop request sent.");
  await refreshCrawlerList();
}

async function restartCrawler(crawlerId) {
  const data = await postCrawlerAction(crawlerId, "restart");
  showAlert(data.message || "Restart request sent.");
  await refreshCrawlerList();
}

async function initializeDashboard() {
  const form = document.getElementById("crawler-form");
  const refreshBtn = document.getElementById("refresh-btn");

  if (form) {
    form.addEventListener("submit", async (event) => {
      event.preventDefault();

      const payload = {
        origin: document.getElementById("origin").value,
        max_depth: Number(document.getElementById("max_depth").value),
        max_pages: Number(document.getElementById("max_pages").value),
        hit_rate: Number(document.getElementById("hit_rate").value),
        queue_limit: Number(document.getElementById("queue_limit").value),
      };

      const data = await createCrawler(payload);
      showAlert(data.message || "Crawler created.");
      await refreshCrawlerList();
    });
  }

  if (refreshBtn) {
    refreshBtn.addEventListener("click", refreshCrawlerList);
  }

  await refreshCrawlerList();
  setInterval(refreshCrawlerList, 5000);
}

initializeDashboard();