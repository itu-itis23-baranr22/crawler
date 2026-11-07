"use strict";

// The status page: one crawl, with its full log.

const statusContainer = document.getElementById("crawl-view");

const statusView = new CrawlView(statusContainer, {
  headingTag: "h1",
  subHeadingTag: "h2",
  showLog: true,
  onStatus: (status) => {
    document.title = `${hostOf(status.origin)} - Crawler`;
  },
  onGone: () => {
    const box = element("div", "gone");
    const back = element("a", "btn btn-primary", "See all crawls");
    back.href = "/";
    box.append(element("h1", "", "No crawl with this ID"), element("p", "", "It may belong to another data folder, or the address may be mistyped."), back);
    statusContainer.replaceChildren(box);
  },
});

statusView.open(window.CRAWLER_ID, { selectUrl: new URLSearchParams(window.location.search).get("address") });
setInterval(refreshTotals, 5000);
