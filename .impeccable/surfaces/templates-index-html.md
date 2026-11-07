---
version: 1
slug: "templates-index-html"
primary_target: "templates/index.html"
related_targets: ["templates/crawler_status.html","templates/search.html"]
---

# Crawler app: dashboard, crawl status and search

Mode: Operate, on all three pages. They share one shell and one visual world.

Audience and job: a portfolio reviewer who runs the app once, starts a crawl, watches it and searches the result. They should see within minutes what it did and why. Task order on the dashboard: start a crawl, watch crawls, read one crawl's accounting.

Must stay: every existing function (create, pause, resume, stop, restart, logs, long polling, search, lucky, pagination, address-bar state), text from crawled pages reaching the page only as text, no runtime dependency on other hosts, English copy.

Must not read as an ordinary SaaS dashboard: the user named this as the one thing that would feel wrong.

Memorable moment: the map filling in live as a crawl runs, each mark landing where the site's structure puts it.

## Direction contract

THESIS: A crawl is a survey of a site. Every address it touches becomes one mark on one map, kept by outcome and reason, so nothing can go missing unseen. It refuses the category default of metric cards above a table.

OWN-WORLD: Deep water-blue shell, map white and woodland-tinted grounds, depth tints running from blue at the start outward to pale, sienna contours, road red for failure. Barlow for all text, with italics only for map place labels. Every rule is one pixel of one weight. Controls are the standard web ones, with small square corners. Raised from the data field: every mark is a real record, nothing decorative. Raised from high-density pages: ruled rows instead of padded cards, so one crawl's account fits one row. Raised from the catalog: a map mark and its list row are one record, and selecting one finds the other. Raised from reference setting: one hairline weight everywhere.

STORY: The visitor understands what the crawl did to each address, believes it hid nothing because skipped and failed are shown as plainly as indexed, and goes on to start a crawl and search its pages.

FIRST VIEWPORT: Dashboard. Water-blue bar at the top with name, Crawls and Search navigation, and index totals. Below it a white row with the address field, limits and Start crawl. Under that, the crawl list in a left column of about a third of the width, each row a host, status, outcome bar and counts. The right two thirds show the selected crawl: host, status and the actions valid right now, then the map at about 600 pixels beside its legend, counts and reasons. With no crawls, this area teaches how to start one.

FORM: Topographic survey sheet, third on my ordered list. seed:2f999e32aced9527. Signature move: the crawl map, with the start at the centre, rings for link depth, and a road running out from the start for each part of the site, ending where that part's marks end and named on the sheet. This replaces the wedges first planned, because wedge boundaries would have to move as parts appear. Roads are laid in the order parts first appear, and a placed mark never moves. Motion grammar: a new mark lands with a short fade and scale, and nothing else moves. Selecting a mark or a row marks the other and shows its record.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
