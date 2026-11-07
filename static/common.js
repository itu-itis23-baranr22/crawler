"use strict";

// Shared by every page. Text from crawled sites only reaches a page through
// textContent and DOM nodes, never as HTML.

const numberFormat = new Intl.NumberFormat("en-US");

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function plural(count, word) {
  return `${numberFormat.format(count)} ${word}${count === 1 ? "" : "s"}`;
}

async function getJson(url, signal) {
  let response;
  try {
    response = await fetch(url, { signal });
  } catch (error) {
    if (error.name === "AbortError") throw error;
    throw new Error("The app did not answer. Check that it is still running, then try again.");
  }
  const data = await response.json().catch(() => null);
  if (!response.ok || data === null) {
    const failure = new Error((data && data.message) || "Something failed on the server. Try again in a moment.");
    failure.status = response.status;
    throw failure;
  }
  return data;
}

// Answers with the server's own message whether the request worked or not.
async function postJson(url, body) {
  try {
    const response = await fetch(url, {
      method: "POST",
      headers: body === undefined ? {} : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    const data = await response.json().catch(() => ({}));
    return { ok: response.ok, data };
  } catch {
    return { ok: false, data: { message: "The app did not answer. Check that it is still running, then try again." } };
  }
}

function safeLink(url) {
  try {
    const { protocol } = new URL(url);
    return protocol === "http:" || protocol === "https:" ? url : null;
  } catch {
    return null;
  }
}

function readableUrl(url) {
  let text = url.replace(/^https?:\/\//, "");
  try {
    text = decodeURI(text); // shows /sayfa/türkçe rather than /sayfa/t%C3%BCrk%C3%A7e
  } catch {
    // Not valid percent-encoding, so show it as it is.
  }
  return text;
}

function hostOf(url) {
  try {
    return new URL(url).host;
  } catch {
    return url;
  }
}

// One colour for each link depth, the same on the map, in the list and in search results.
function depthTint(depth) {
  return `var(--depth-${Math.min(depth, 3)})`;
}

async function refreshTotals() {
  const node = document.getElementById("index-totals");
  try {
    const stats = await getJson("/api/stats");
    node.textContent = `${plural(stats.indexed_documents, "page")} · ${plural(stats.unique_terms, "word")} · ${stats.index_size_mb} MB`;
  } catch {
    node.textContent = "";
  }
}

refreshTotals();
