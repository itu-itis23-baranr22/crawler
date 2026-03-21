let currentQuery = "";
let currentPage = 1;
let currentPageSize = 10;
let currentMode = "search"; // search | assignment | lucky

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text ?? "";
  return div.innerHTML;
}

function showAlert(message) {
  alert(message);
}

function setSearchStatus(text, className = "green") {
  const el = document.getElementById("search-status");
  const summary = document.getElementById("summary-status");
  if (el) {
    el.textContent = text;
    el.className = `badge ${className}`;
  }
  if (summary) {
    summary.textContent = text;
  }
}

function updateTopStats(results) {
  const countEl = document.getElementById("stat-result-count");
  const depthEl = document.getElementById("stat-top-depth");
  const freqEl = document.getElementById("stat-top-frequency");
  const scoreEl = document.getElementById("stat-top-score");

  const count = results.length;
  countEl.textContent = String(count);

  if (count === 0) {
    depthEl.textContent = "-";
    freqEl.textContent = "-";
    scoreEl.textContent = "-";
    return;
  }

  const top = results[0];
  depthEl.textContent = String(top.depth ?? "-");
  freqEl.textContent = String(top.frequency ?? "-");
  scoreEl.textContent = String(top.score ?? "-");
}

function updatePagination(payload) {
  const label = document.getElementById("pagination-label");
  const prevBtn = document.getElementById("prev-page-btn");
  const nextBtn = document.getElementById("next-page-btn");

  if (!label || !prevBtn || !nextBtn) return;

  const page = payload.page ?? 1;
  const totalPages = payload.total_pages ?? 1;

  label.textContent = `Page ${page} of ${totalPages} • Total results: ${payload.total_results ?? 0}`;
  prevBtn.disabled = !payload.has_prev;
  nextBtn.disabled = !payload.has_next;
}

function buildResultCard(result) {
  const matchedTerms = Array.isArray(result.matched_terms)
    ? result.matched_terms
    : [];

  const matchedTermsHtml = matchedTerms.length
    ? matchedTerms
        .map(term => `<span class="tag">${escapeHtml(term)}</span>`)
        .join("")
    : `<span class="tag">No matched terms info</span>`;

  return `
    <div class="result-card" style="margin-bottom: 14px;">
      <div class="row" style="align-items: flex-start;">
        <div style="flex: 1;">
          <h3 style="margin-bottom: 8px;">${escapeHtml(result.url || "No URL")}</h3>
          <div class="url-text" style="margin-bottom: 8px;">
            Origin: ${escapeHtml(result.origin || "-")}
          </div>

          <div class="tag-row">
            <span class="tag">Depth: ${escapeHtml(String(result.depth ?? 0))}</span>
            <span class="tag">Score: ${escapeHtml(String(result.score ?? 0))}</span>
            <span class="tag">Frequency: ${escapeHtml(String(result.frequency ?? 0))}</span>
          </div>

          <div class="tag-row" style="margin-top: 10px;">
            ${matchedTermsHtml}
          </div>
        </div>
      </div>
    </div>
  `;
}

function renderNormalResults(payload) {
  const resultsEl = document.getElementById("search-results");
  const resultLabel = document.getElementById("result-label");
  const summaryQuery = document.getElementById("summary-query");
  const summaryCount = document.getElementById("summary-count");
  const summaryLucky = document.getElementById("summary-lucky");

  const results = payload.results || [];

  summaryQuery.textContent = payload.query || "-";
  summaryCount.textContent = String(payload.total_results ?? payload.count ?? 0);
  summaryLucky.textContent = payload.term || "-";
  resultLabel.textContent = `${results.length} results on this page`;

  updateTopStats(results);
  updatePagination(payload);

  if (results.length === 0) {
    resultsEl.innerHTML = `<div class="result-card">No results found.</div>`;
    return;
  }

  resultsEl.innerHTML = results.map(buildResultCard).join("");
}

function renderAssignmentResults(payload) {
  const el = document.getElementById("assignment-results");
  const results = payload.results || [];

  updatePagination(payload);

  if (results.length === 0) {
    el.textContent = "No assignment-format results found.";
    return;
  }

  const lines = results.map(item => {
    const url = item[0] ?? "";
    const origin = item[1] ?? "";
    const depth = item[2] ?? 0;
    return `(${url}, ${origin}, ${depth})`;
  });

  el.textContent = lines.join("\n");
}

async function performSearch(query, page, pageSize) {
  setSearchStatus("Searching...", "blue");

  const response = await fetch(
    `/api/search?query=${encodeURIComponent(query)}&page=${encodeURIComponent(page)}&page_size=${encodeURIComponent(pageSize)}`
  );
  const data = await response.json();

  renderNormalResults(data);
  setSearchStatus("Ready", "green");
}

async function performLucky(pageSize) {
  setSearchStatus("Lucky...", "blue");

  const response = await fetch(
    `/api/lucky?page_size=${encodeURIComponent(pageSize)}`
  );
  const data = await response.json();

  renderNormalResults(data);

  if (data.message) {
    showAlert(data.message);
  }

  setSearchStatus("Ready", "green");
}

async function performAssignmentSearch(query, page, pageSize) {
  setSearchStatus("Formatting...", "blue");

  const response = await fetch(
    `/api/search/assignment?query=${encodeURIComponent(query)}&page=${encodeURIComponent(page)}&page_size=${encodeURIComponent(pageSize)}`
  );
  const data = await response.json();

  renderAssignmentResults(data);
  setSearchStatus("Ready", "green");
}

async function rerunCurrentMode() {
  if (currentMode === "search") {
    await performSearch(currentQuery, currentPage, currentPageSize);
  } else if (currentMode === "assignment") {
    await performAssignmentSearch(currentQuery, currentPage, currentPageSize);
  } else if (currentMode === "lucky") {
    await performLucky(currentPageSize);
  }
}

async function initializeSearchPage() {
  const form = document.getElementById("search-form");
  const luckyBtn = document.getElementById("lucky-btn");
  const assignmentBtn = document.getElementById("assignment-btn");
  const prevBtn = document.getElementById("prev-page-btn");
  const nextBtn = document.getElementById("next-page-btn");

  if (form) {
    form.addEventListener("submit", async (event) => {
      event.preventDefault();

      currentQuery = document.getElementById("search-query").value.trim();
      currentPageSize = Number(document.getElementById("search-limit").value);
      currentPage = 1;
      currentMode = "search";

      if (!currentQuery) {
        showAlert("Please enter a query.");
        return;
      }

      try {
        await performSearch(currentQuery, currentPage, currentPageSize);
      } catch (error) {
        console.error(error);
        setSearchStatus("Error", "red");
        showAlert("Search request failed.");
      }
    });
  }

  if (luckyBtn) {
    luckyBtn.addEventListener("click", async () => {
      currentPageSize = Number(document.getElementById("search-limit").value);
      currentPage = 1;
      currentMode = "lucky";

      try {
        await performLucky(currentPageSize);
      } catch (error) {
        console.error(error);
        setSearchStatus("Error", "red");
        showAlert("Lucky request failed.");
      }
    });
  }

  if (assignmentBtn) {
    assignmentBtn.addEventListener("click", async () => {
      currentQuery = document.getElementById("search-query").value.trim();
      currentPageSize = Number(document.getElementById("search-limit").value);
      currentPage = 1;
      currentMode = "assignment";

      if (!currentQuery) {
        showAlert("Please enter a query.");
        return;
      }

      try {
        await performAssignmentSearch(currentQuery, currentPage, currentPageSize);
      } catch (error) {
        console.error(error);
        setSearchStatus("Error", "red");
        showAlert("Assignment-format request failed.");
      }
    });
  }

  if (prevBtn) {
    prevBtn.addEventListener("click", async () => {
      if (currentPage > 1) {
        currentPage -= 1;
        try {
          await rerunCurrentMode();
        } catch (error) {
          console.error(error);
          setSearchStatus("Error", "red");
          showAlert("Previous page request failed.");
        }
      }
    });
  }

  if (nextBtn) {
    nextBtn.addEventListener("click", async () => {
      currentPage += 1;
      try {
        await rerunCurrentMode();
      } catch (error) {
        console.error(error);
        setSearchStatus("Error", "red");
        showAlert("Next page request failed.");
      }
    });
  }
}

initializeSearchPage();