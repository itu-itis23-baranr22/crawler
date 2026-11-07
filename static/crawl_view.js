"use strict";

// One crawl on screen: its map, its legend and its list of addresses.
// Every mark on the map is one real address. The rings are link depth from the start, and each
// part of the site runs out from the start along its own road. Roads are laid in the order parts
// first appear, and a mark's place follows from its road, address and depth, so a placed mark never
// moves, and a crawl draws the same way wherever it is opened.

const SVG_NS = "http://www.w3.org/2000/svg";
const MAP_SIZE = 640;
const MAP_CENTRE = MAP_SIZE / 2;
const MAP_RADIUS = 254;
const MAP_INSET = 56; // the ring nearly fills what the page shows
const MAP_VIEW = MAP_SIZE - MAP_INSET * 2;
const START_RADIUS = 46;
const MAX_RINGS = 8;
const MAX_MARKS = 3000; // matches MAX_VISITS_SHOWN on the server
const PICK_DISTANCE = 16;
const LABEL_COUNT = 6;
const LABEL_GAP = 60; // how far, in screen pixels, a name may sit from the end of its road
const FIRST_ROAD = -Math.PI / 3;
const ROAD_STEP = Math.PI * (3 - Math.sqrt(5)); // the golden angle spreads any number of roads evenly
const ROAD_SPREAD = (34 / 180) * Math.PI;
const DEPTH_BEARING = (-135 / 180) * Math.PI;

const OUTCOMES = [
  { key: "indexed", label: "Indexed", counter: "pages_crawled" },
  { key: "skipped", label: "Skipped", counter: "skipped_pages" },
  { key: "failed", label: "Failed", counter: "failed_pages" },
  { key: "redirected", label: "Redirected", counter: "redirected_pages" },
  { key: "waiting", label: "Waiting", counter: "queue_size" },
];

// Filters read in the order someone checking a crawl cares about.
const FILTERS = [
  { key: null, label: "All" },
  { key: "failed", label: "Failed", counter: "failed_pages" },
  { key: "skipped", label: "Skipped", counter: "skipped_pages" },
  { key: "redirected", label: "Redirected", counter: "redirected_pages" },
  { key: "indexed", label: "Indexed", counter: "pages_crawled" },
  { key: "waiting", label: "Waiting", counter: "queue_size" },
];

const PROBLEMS_FIRST = { failed: 0, skipped: 1, redirected: 2, indexed: 3 };

const ACTIONS_FOR = {
  running: ["pause", "stop", "restart"],
  paused: ["resume", "stop", "restart"],
  interrupted: ["resume", "stop", "restart"],
  stopped: ["restart"],
  completed: ["restart"],
  failed: ["restart"],
};

const ACTION_LABELS = { pause: "Pause", resume: "Resume", stop: "Stop", restart: "Restart" };

function svgNode(tag, attributes = {}, parent = null) {
  const node = document.createElementNS(SVG_NS, tag);
  for (const [name, value] of Object.entries(attributes)) node.setAttribute(name, value);
  if (parent) parent.append(node);
  return node;
}

function clamp(value, low, high) {
  return Math.min(high, Math.max(low, value));
}

function boxesMeet(a, b) {
  return a.left < b.right && a.right > b.left && a.top < b.bottom && a.bottom > b.top;
}

// Whether a straight road passes through a box.
function segmentMeetsBox({ x1, y1, x2, y2 }, box) {
  let enter = 0;
  let leave = 1;
  const dx = x2 - x1;
  const dy = y2 - y1;
  for (const [step, room] of [
    [-dx, x1 - box.left],
    [dx, box.right - x1],
    [-dy, y1 - box.top],
    [dy, box.bottom - y1],
  ]) {
    if (step === 0) {
      if (room < 0) return false;
    } else if (step < 0) {
      enter = Math.max(enter, room / step);
    } else {
      leave = Math.min(leave, room / step);
    }
    if (enter > leave) return false;
  }
  return true;
}

function markIcon(outcome) {
  const icon = svgNode("svg", { class: "mark-icon", viewBox: "-5 -5 10 10", "aria-hidden": "true" });
  svgNode("use", { href: `#mark-${outcome}` }, icon);
  return icon;
}

// A number from 0 to 1 that is always the same for the same text.
function hashText(text) {
  let hash = 2166136261;
  for (let i = 0; i < text.length; i += 1) {
    hash ^= text.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  // Addresses often differ only at the end, so mix the bits or their marks would clump together.
  hash ^= hash >>> 16;
  hash = Math.imul(hash, 0x85ebca6b);
  hash ^= hash >>> 13;
  hash = Math.imul(hash, 0xc2b2ae35);
  hash ^= hash >>> 16;
  return (hash >>> 0) / 4294967296;
}

function addressCount(count) {
  return `${numberFormat.format(count)} ${count === 1 ? "address" : "addresses"}`;
}

// The folder of the starting address, so /wiki/Web_crawler divides its site by what follows /wiki/.
function sectionPrefix(origin) {
  try {
    const parts = new URL(origin).pathname.split("/");
    parts.pop();
    return parts.filter(Boolean);
  } catch {
    return [];
  }
}

function sectionOf(url, prefix) {
  let parts;
  try {
    parts = new URL(url).pathname.split("/").filter(Boolean);
  } catch {
    return "/";
  }
  const insideFolder = parts.length > prefix.length && prefix.every((part, index) => parts[index] === part);
  const first = insideFolder ? parts[prefix.length] : parts[0];
  if (!first) return "/";
  try {
    return `/${decodeURIComponent(first)}`;
  } catch {
    return `/${first}`;
  }
}

function describeOutcome(record) {
  const label = OUTCOMES.find((outcome) => outcome.key === record.outcome).label;
  return record.reason ? `${label}: ${record.reason}` : label;
}

function detailLabel(record) {
  if (record.outcome === "indexed") return "Title";
  if (record.outcome === "redirected" || record.reason === "redirects off site") return "Moved to";
  if (record.reason === "copy of another page") return "Copy of";
  if (record.reason === "not HTML") return "Content type";
  return "Detail";
}

function sleep(milliseconds, signal) {
  return new Promise((resolve) => {
    const timer = setTimeout(resolve, milliseconds);
    if (signal) {
      signal.addEventListener("abort", () => {
        clearTimeout(timer);
        resolve();
      });
    }
  });
}

class CrawlMap {
  constructor({ onHover, onSelect } = {}) {
    this.onHover = onHover;
    this.onSelect = onSelect;
    this.node = svgNode("svg", { viewBox: `${MAP_INSET} ${MAP_INSET} ${MAP_VIEW} ${MAP_VIEW}`, role: "img", "aria-label": "Map of the crawl" });
    this.bandLayer = svgNode("g", {}, this.node);
    this.roadLayer = svgNode("g", {}, this.node);
    this.labelLayer = svgNode("g", {}, this.node); // under the marks, so a name never hides an address
    this.markLayer = svgNode("g", {}, this.node);
    this.waitingLayer = svgNode("g", {}, this.node);
    this.depthLayer = svgNode("g", {}, this.node);
    svgNode("path", { class: "map-start", d: `M${MAP_CENTRE} ${MAP_CENTRE - 11}L${MAP_CENTRE + 10} ${MAP_CENTRE + 7}H${MAP_CENTRE - 10}Z` }, this.node);
    this.selectedRing = svgNode("circle", { class: "map-selected", r: 8, visibility: "hidden" }, this.node);
    this.unit = 1;
    this.configure({ seed: "crawl", origin: "", maxDepth: 2 });
    new ResizeObserver(() => this.measure()).observe(this.node);
    this.node.addEventListener("pointermove", (event) => this.pointerMoved(event));
    this.node.addEventListener("pointerleave", () => {
      cancelAnimationFrame(this.hoverFrame);
      this.hoverFrame = null;
      if (this.onHover) this.onHover(null);
    });
    this.node.addEventListener("click", (event) => {
      if (this.onSelect) this.onSelect(this.pick(event));
    });
  }

  // Text and marks keep their size on screen however small the map is drawn.
  measure() {
    const box = this.node.getBoundingClientRect();
    const drawn = Math.min(box.width, box.height);
    if (!drawn) return;
    this.unit = MAP_VIEW / drawn;
    this.node.style.setProperty("--map-unit", this.unit.toFixed(3));
    this.selectedRing.setAttribute("r", (7 * this.unit).toFixed(1));
    this.drawRoads();
  }

  configure({ seed, origin, maxDepth }) {
    this.seed = hashText(seed) * Math.PI * 2;
    this.prefix = sectionPrefix(origin);
    this.maxDepth = maxDepth;
    this.rings = Math.max(2, Math.min(MAX_RINGS, maxDepth + 1));
    this.clear();
    this.drawBands();
  }

  clear() {
    this.records = new Map();
    this.waiting = [];
    this.roads = new Map();
    this.selectedId = null;
    this.filter = null;
    this.node.removeAttribute("data-filter");
    this.markLayer.replaceChildren();
    this.waitingLayer.replaceChildren();
    this.selectedRing.setAttribute("visibility", "hidden");
    this.drawRoads();
  }

  ringRadius(ring) {
    return START_RADIUS + ((MAP_RADIUS - START_RADIUS) * ring) / (this.rings - 1);
  }

  drawBands() {
    this.bandLayer.replaceChildren();
    for (let ring = this.rings - 1; ring >= 0; ring -= 1) {
      const radius = this.ringRadius(ring);
      const wobble = Math.min(5, ((MAP_RADIUS - START_RADIUS) / (this.rings - 1)) * 0.1);
      const phase = this.seed + ring * 1.7;
      const points = [];
      for (let i = 0; i < 96; i += 1) {
        const angle = (i / 96) * Math.PI * 2;
        const distance = radius + wobble * Math.sin(3 * angle + phase) + (wobble / 2) * Math.sin(7 * angle + phase * 2);
        points.push(`${(MAP_CENTRE + distance * Math.cos(angle)).toFixed(1)} ${(MAP_CENTRE + distance * Math.sin(angle)).toFixed(1)}`);
      }
      svgNode("path", { class: "map-contour", d: `M${points.join("L")}Z`, style: `fill:${depthTint(ring)}` }, this.bandLayer);
    }
  }

  road(name) {
    let road = this.roads.get(name);
    if (!road) {
      road = { name, angle: FIRST_ROAD + this.roads.size * ROAD_STEP, visited: 0, waiting: 0, deepest: 1 };
      this.roads.set(name, road);
    }
    return road;
  }

  position(record) {
    const ring = Math.min(record.depth, this.rings - 1);
    const across = hashText(record.url);
    const along = hashText(`${record.url}#`);
    if (ring === 0) {
      const radius = 16 + along * (START_RADIUS - 24);
      const angle = across * Math.PI * 2;
      return [MAP_CENTRE + radius * Math.cos(angle), MAP_CENTRE + radius * Math.sin(angle)];
    }
    const inner = this.ringRadius(ring - 1);
    const outer = this.ringRadius(ring);
    const padding = Math.min(9, (outer - inner) / 4);
    const radius = inner + padding + (outer - inner - padding * 2) * along;
    const angle = this.road(sectionOf(record.url, this.prefix)).angle + ROAD_SPREAD * (across - 0.5);
    return [MAP_CENTRE + radius * Math.cos(angle), MAP_CENTRE + radius * Math.sin(angle)];
  }

  drawMark(record, parent, isNew) {
    [record.x, record.y] = this.position(record);
    record.node = svgNode(
      "g",
      {
        class: `mark m-${record.outcome}${isNew ? " m-new" : ""}`,
        "data-id": record.id,
        transform: `translate(${record.x.toFixed(1)} ${record.y.toFixed(1)})`,
      },
      parent
    );
    svgNode("use", { href: `#mark-${record.outcome}` }, record.node);
  }

  update(visits, waiting, animate) {
    for (const visit of visits) {
      const record = { ...visit };
      this.drawMark(record, this.markLayer, animate);
      if (record.depth > 0) {
        const road = this.road(sectionOf(record.url, this.prefix));
        road.visited += 1;
        road.deepest = Math.max(road.deepest, record.depth);
      }
      this.records.set(record.id, record);
    }
    while (this.records.size > MAX_MARKS) {
      const [oldestId, oldest] = this.records.entries().next().value;
      oldest.node.remove();
      this.records.delete(oldestId);
    }

    for (const road of this.roads.values()) road.waiting = 0;
    this.waitingLayer.replaceChildren();
    this.waiting = waiting.map((item) => {
      const record = { id: `waiting:${item.url}`, url: item.url, depth: item.depth, outcome: "waiting", reason: "", detail: "" };
      this.drawMark(record, this.waitingLayer, false);
      if (record.depth > 0) {
        const road = this.road(sectionOf(record.url, this.prefix));
        road.waiting += 1;
        road.deepest = Math.max(road.deepest, record.depth);
      }
      return record;
    });

    this.drawRoads();
    this.moveSelection();
    this.node.setAttribute("aria-label", `Map of ${addressCount(this.records.size)} by link depth`);
  }

  // Roads and place names for the largest parts of the site, with the names set on the sheet.
  drawRoads() {
    this.roadLayer.replaceChildren();
    this.labelLayer.replaceChildren();
    this.depthLayer.replaceChildren();
    const size = (road) => road.visited + road.waiting;
    const largest = [...this.roads.values()]
      .filter((road) => size(road) >= 2)
      .sort((a, b) => size(b) - size(a) || a.angle - b.angle)
      .slice(0, LABEL_COUNT);
    const marks = this.markGrid();
    const lines = new Map(largest.map((road) => [road, this.roadLine(road)]));
    const taken = [];
    const overlaps = (box) => taken.some((other) => boxesMeet(box, other));
    for (const road of largest) {
      const line = lines.get(road);
      const label = svgNode("text", { class: "map-label" }, this.labelLayer);
      label.textContent = road.name.length > 13 ? `${road.name.slice(0, 12)}…` : road.name;
      let width = 0;
      try {
        width = label.getComputedTextLength();
      } catch {
        // not laid out yet: the estimate below stands in
      }
      if (!width) width = label.textContent.length * 7.4 * this.unit;
      const others = [...lines.values()].filter((other) => other !== line);
      const placed = this.placeLabel(road, line, width, { marks, others, overlaps });
      if (!placed) {
        label.remove(); // no room: the caption counts it among the unlabelled parts
        road.label = null;
        continue;
      }
      road.label = placed;
      taken.push(placed.box);
      svgNode("line", { class: "map-road", ...Object.fromEntries(Object.entries(line).map(([key, value]) => [key, value.toFixed(1)])) }, this.roadLayer);
      label.setAttribute("x", placed.x.toFixed(1));
      label.setAttribute("y", placed.y.toFixed(1));
      label.setAttribute("text-anchor", placed.anchor);
    }
    this.labelledRoads = taken.length;

    // Depth numerals step along their ring if a place name or a mark is in the way.
    for (let ring = 1; ring < this.rings; ring += 1) {
      const radius = this.ringRadius(ring);
      let bearing = DEPTH_BEARING;
      let fallback = null;
      for (let tries = 0; tries < 12; tries += 1, bearing += 0.2) {
        const x = MAP_CENTRE + radius * Math.cos(bearing);
        const y = MAP_CENTRE + radius * Math.sin(bearing);
        const box = { left: x - 10 * this.unit, right: x + 10 * this.unit, top: y - 9 * this.unit, bottom: y + 9 * this.unit };
        if (overlaps(box)) continue;
        if (fallback === null) fallback = bearing;
        if (!marks.count(box, 0)) {
          fallback = bearing;
          break;
        }
      }
      bearing = fallback ?? DEPTH_BEARING;
      const label = svgNode(
        "text",
        {
          class: "map-depth",
          x: (MAP_CENTRE + radius * Math.cos(bearing)).toFixed(1),
          y: (MAP_CENTRE + radius * Math.sin(bearing) + 4 * this.unit).toFixed(1),
          "text-anchor": "middle",
        },
        this.depthLayer
      );
      label.textContent = this.maxDepth + 1 > MAX_RINGS && ring === this.rings - 1 ? `${ring}+` : ring;
    }
  }

  // A road runs from just outside the start to where its part's marks end. Both ends stop short of
  // the rings, which wobble, so a road never pokes through one.
  roadLine(road) {
    const cos = Math.cos(road.angle);
    const sin = Math.sin(road.angle);
    const reach = this.ringRadius(Math.min(road.deepest, this.rings - 1)) - 8;
    return {
      x1: MAP_CENTRE + (START_RADIUS + 8) * cos,
      y1: MAP_CENTRE + (START_RADIUS + 8) * sin,
      x2: MAP_CENTRE + reach * cos,
      y2: MAP_CENTRE + reach * sin,
    };
  }

  // Every mark on the sheet, sorted into squares so a name can ask what lies under it.
  markGrid() {
    const cell = 24;
    const columns = Math.ceil(MAP_SIZE / cell) + 1;
    const squares = new Map();
    const square = (x, y) => Math.max(0, Math.floor(x / cell)) * columns + Math.max(0, Math.floor(y / cell));
    for (const record of [...this.records.values(), ...this.waiting]) {
      const key = square(record.x, record.y);
      if (!squares.has(key)) squares.set(key, []);
      squares.get(key).push(record);
    }
    return {
      count(box, pad) {
        let count = 0;
        const left = box.left - pad;
        const right = box.right + pad;
        const top = box.top - pad;
        const bottom = box.bottom + pad;
        for (let column = Math.max(0, Math.floor(left / cell)); column <= Math.floor(right / cell); column += 1) {
          for (let row = Math.max(0, Math.floor(top / cell)); row <= Math.floor(bottom / cell); row += 1) {
            for (const record of squares.get(column * columns + row) || []) {
              if (record.x >= left && record.x <= right && record.y >= top && record.y <= bottom) count += 1;
            }
          }
        }
        return count;
      },
    };
  }

  // A name goes beside the end of its road, in the nearest spot that is clear of marks, other roads
  // and other names. Where a crawl is too dense for that, it takes the spot that covers the fewest
  // marks, and it stays where it was while that spot is still as good, so names don't jump as marks arrive.
  placeLabel(road, line, width, { marks, others, overlaps }) {
    const unit = this.unit;
    const height = 17 * unit;
    const cos = Math.cos(road.angle);
    const sin = Math.sin(road.angle);
    const low = MAP_INSET + 2 * unit;
    const high = MAP_SIZE - MAP_INSET - 2 * unit;
    let best = null;
    const consider = (x, y, anchor, bonus) => {
      // Italic letters lean past the ends of the text, so the box takes a little room on each side.
      const left = (anchor === "end" ? x - width : anchor === "start" ? x : x - width / 2) - 2 * unit;
      const box = { left, right: left + width + 4 * unit, top: y - height * 0.8, bottom: y + height * 0.2 };
      if (box.left < low || box.right > high || box.top < low || box.bottom > high || overlaps(box)) return;
      const nearestX = clamp(MAP_CENTRE, box.left, box.right);
      const nearestY = clamp(MAP_CENTRE, box.top, box.bottom);
      if (Math.hypot(nearestX - MAP_CENTRE, nearestY - MAP_CENTRE) < START_RADIUS + 4) return;
      const gap = Math.hypot(line.x2 - clamp(line.x2, box.left, box.right), line.y2 - clamp(line.y2, box.top, box.bottom)) / unit;
      if (gap > LABEL_GAP) return;
      const off = Math.hypot(line.x2 - (box.left + box.right) / 2, line.y2 - (box.top + box.bottom) / 2) / unit;
      const covered = marks.count(box, 4 * unit);
      const crossed = others.filter((other) => segmentMeetsBox(other, box)).length;
      const score = covered * 40 + crossed * 20 + gap + off / 20 - bonus;
      if (!best || score < best.score) best = { x, y, anchor, box, score };
    };
    if (road.label) consider(road.label.x, road.label.y, road.label.anchor, 6);
    for (let along = -90; along <= 60; along += 5) {
      for (const across of [0, -9, 9, -18, 18, -27, 27]) {
        const x = line.x2 + (along * cos - across * sin) * unit;
        const y = line.y2 + (along * sin + across * cos + 4) * unit;
        for (const anchor of ["start", "middle", "end"]) consider(x, y, anchor, 0);
      }
    }
    return best;
  }

  // Parts of the site with no name on the map, so nothing looks as if it belongs to a nearby label.
  unlabelledParts() {
    return Math.max(0, [...this.roads.values()].filter((road) => road.visited + road.waiting > 0).length - this.labelledRoads);
  }

  setFilter(key) {
    this.filter = key;
    if (key) this.node.setAttribute("data-filter", key);
    else this.node.removeAttribute("data-filter");
  }

  find(id) {
    return this.records.get(id) || this.waiting.find((record) => record.id === id) || null;
  }

  select(id) {
    this.selectedId = id;
    this.moveSelection();
  }

  moveSelection() {
    const record = this.selectedId === null ? null : this.find(this.selectedId);
    if (!record) {
      this.selectedRing.setAttribute("visibility", "hidden");
      return;
    }
    this.selectedRing.setAttribute("cx", record.x.toFixed(1));
    this.selectedRing.setAttribute("cy", record.y.toFixed(1));
    this.selectedRing.setAttribute("visibility", "visible");
  }

  pick(event) {
    const matrix = this.node.getScreenCTM();
    if (!matrix) return null;
    const point = new DOMPoint(event.clientX, event.clientY).matrixTransform(matrix.inverse());
    let best = null;
    let bestDistance = PICK_DISTANCE * this.unit;
    const consider = (record) => {
      if (this.filter && record.outcome !== this.filter) return;
      const distance = Math.hypot(record.x - point.x, record.y - point.y);
      if (distance < bestDistance) {
        best = record;
        bestDistance = distance;
      }
    };
    this.records.forEach(consider);
    this.waiting.forEach(consider);
    return best;
  }

  pointerMoved(event) {
    if (this.hoverFrame) return;
    this.hoverFrame = requestAnimationFrame(() => {
      this.hoverFrame = null;
      const picked = this.pick(event);
      this.node.style.cursor = picked ? "pointer" : "";
      if (this.onHover) this.onHover(picked);
    });
  }
}

class CrawlView {
  constructor(container, { headingTag = "h2", subHeadingTag = "h3", showLog = false, showFullStatus = false, onStatus, onGone } = {}) {
    this.options = { headingTag, subHeadingTag, showLog, showFullStatus, onStatus, onGone };
    this.container = container;
    this.controller = null;
    this.build();
  }

  build() {
    const { headingTag, subHeadingTag, showLog } = this.options;
    this.root = element("div", "crawl-view");

    const head = element("header", "crawl-head");
    const title = element("div", "crawl-title");
    this.heading = element(headingTag);
    this.stateLine = element("p", "crawl-state");
    title.append(this.heading, this.stateLine);
    this.actions = element("div", "crawl-actions");
    head.append(title, this.actions);

    this.note = element("p", "crawl-note");
    this.note.setAttribute("role", "status");
    this.note.hidden = true;

    const body = element("div", "crawl-body");
    const figure = element("figure", "crawl-map");
    this.map = new CrawlMap({
      onHover: (record) => this.showTip(record),
      onSelect: (record) => this.selectRecord(record, { fromMap: true }),
    });
    this.tip = element("div", "map-tip");
    this.tip.hidden = true;
    this.mapCaption = element("figcaption");
    figure.append(this.map.node, this.tip, this.mapCaption);
    this.figure = figure;

    const side = element("aside", "crawl-side");
    this.legend = element("ul", "legend");
    this.legendRows = {};
    for (const outcome of OUTCOMES) {
      const item = element("li");
      const row = element("button", "legend-row");
      row.type = "button";
      row.setAttribute("aria-pressed", "false");
      const count = element("span", "legend-count", "0");
      row.append(markIcon(outcome.key), element("span", "", outcome.label), count);
      row.addEventListener("click", () => this.setFilter(this.filter === outcome.key ? null : outcome.key));
      const reasons = element("ul", "reasons");
      item.append(row, reasons);
      this.legend.append(item);
      this.legendRows[outcome.key] = { row, count, reasons };
    }
    this.dropped = element("p", "dropped");
    this.dropped.hidden = true;
    this.record = element("section", "record");
    this.record.setAttribute("aria-live", "polite");
    side.append(this.legend, this.dropped, this.record);
    body.append(figure, side);

    const activity = element("section", "activity");
    const activityHead = element("div", "activity-head");
    this.activityTitle = element(subHeadingTag, "", "Every address");
    this.activityCount = element("span", "activity-count");
    activityHead.append(this.activityTitle, this.activityCount);
    this.filterBar = element("div", "filters");
    this.filterBar.setAttribute("role", "group");
    this.filterBar.setAttribute("aria-label", "Show addresses by result");
    this.filterButtons = FILTERS.map((filter) => {
      const button = element("button", "filter");
      button.type = "button";
      button.setAttribute("aria-pressed", "false");
      button.addEventListener("click", () => this.setFilter(filter.key));
      this.filterBar.append(button);
      return { filter, button };
    });
    this.visitList = element("ul", "visits");
    this.moreButton = element("button", "btn btn-secondary show-more", "Show more");
    this.moreButton.type = "button";
    this.moreButton.hidden = true;
    this.moreButton.addEventListener("click", () => {
      this.shown += 100;
      this.renderActivity();
    });
    activity.append(activityHead, this.filterBar, this.visitList, this.moreButton);
    this.activity = activity;

    this.root.append(head, this.note, body, activity);

    if (showLog) {
      this.log = element("details", "log");
      this.log.append(element("summary", "", "Log, latest 500 lines"));
      this.logLines = element("pre");
      this.logLines.tabIndex = 0;
      this.log.append(this.logLines);
      this.log.addEventListener("toggle", () => {
        if (this.log.open) this.refreshLog();
      });
      this.root.append(this.log);
    }
  }

  // ---------- Opening and closing ----------
  resetRecords() {
    this.visits = [];
    this.waiting = [];
    this.lastId = 0;
    this.knownTotal = 0;
    this.filter = null;
    this.selected = null;
    this.selectedRecord = null;
    this.shown = 50;
    if (this.status) this.map.configure({ seed: this.crawlerId, origin: this.status.origin, maxDepth: this.status.max_depth });
    this.showTip(null);
    for (const { row } of Object.values(this.legendRows)) row.setAttribute("aria-pressed", "false");
    this.renderRecord();
    this.renderActivity();
  }

  async open(crawlerId, { selectUrl = null } = {}) {
    this.close();
    const controller = new AbortController();
    this.controller = controller;
    this.crawlerId = crawlerId;
    this.base = `/api/crawlers/${encodeURIComponent(crawlerId)}`;
    this.status = null;
    this.actionKey = null;
    this.infoNote = "";
    this.setNote("");
    this.resetRecords();
    if (!this.root.isConnected) this.container.replaceChildren(this.root);
    try {
      const status = await getJson(this.base, controller.signal);
      this.status = status;
      this.map.configure({ seed: crawlerId, origin: status.origin, maxDepth: status.max_depth });
      this.renderStatus(status);
      await this.refreshVisits(controller.signal);
      if (selectUrl) {
        const found = this.visits.find((visit) => visit.url === selectUrl);
        if (found) this.selectRecord(this.map.find(found.id));
        else this.infoNote = "That address isn't on this map. It may be older than the latest 3,000, or the page may have been reached under another address.";
        this.setNote(this.noteFor(this.status));
      }
    } catch (error) {
      if (error.name === "AbortError") return;
      if (error.status === 404) {
        if (this.options.onGone) this.options.onGone();
        return;
      }
      this.setNote(error.message, true);
    }
    this.poll(controller);
  }

  close() {
    if (this.controller) this.controller.abort();
    this.controller = null;
  }

  async poll(controller) {
    const { signal } = controller;
    while (!signal.aborted) {
      try {
        const version = this.status ? this.status.status_version : 0;
        // After losing contact, ask without waiting, so the warning clears as soon as the app answers.
        const payload = await getJson(`${this.base}/wait-status?since_version=${version}&timeout=${this.offline ? 0 : 20}`, signal);
        if (signal.aborted) return;
        if (this.offline) {
          this.offline = false;
          this.setNote("");
        }
        this.renderStatus(payload.crawler);
        if (payload.changed) await this.refreshVisits(signal);
        await sleep(300, signal);
      } catch (error) {
        if (error.name === "AbortError") return;
        this.offline = true;
        this.setNote("Lost contact with the app. Trying again…", true);
        await sleep(2000, signal);
      }
    }
  }

  async refreshVisits(signal) {
    const data = await getJson(`${this.base}/visits?after=${this.lastId}`, signal);
    if (data.total < this.knownTotal) {
      // The crawl was restarted, perhaps from another tab, so its old marks no longer count.
      this.resetRecords();
      return this.refreshVisits(signal);
    }
    this.knownTotal = data.total;
    const animate = this.lastId > 0;
    this.map.update(data.visits, data.waiting, animate);
    this.visits.push(...data.visits);
    if (this.visits.length > MAX_MARKS) this.visits.splice(0, this.visits.length - MAX_MARKS);
    if (data.visits.length) this.lastId = data.visits[data.visits.length - 1].id;
    this.waiting = data.waiting;
    this.renderReasons(data.reasons);
    this.renderCaption();
    this.renderActivity();
    if (this.log && this.log.open) this.refreshLog();
    return undefined;
  }

  async refreshLog() {
    try {
      const data = await getJson(`${this.base}/logs?last_n=500`);
      this.logLines.textContent = data.logs.length ? data.logs.join("\n") : "Nothing logged yet.";
    } catch {
      this.logLines.textContent = "The log could not be loaded.";
    }
  }

  // ---------- Status ----------
  renderStatus(status) {
    this.status = status;
    if (this.options.onStatus) this.options.onStatus(status);
    this.heading.textContent = hostOf(status.origin);

    const state = element("strong", `status-${status.status}`, status.status);
    let start = "";
    try {
      const { pathname, search } = new URL(status.origin);
      if (pathname !== "/" || search) start = ` · ${readableUrl(pathname + search)}`;
    } catch {
      // The heading already shows what can be shown of it.
    }
    let line = `${start} · depth ${status.max_depth}, up to ${plural(status.max_pages, "page")}, ${status.hit_rate} per second`;
    if (status.recoveries) line += ` · resumed after ${plural(status.recoveries, "interruption")}, finished pages kept`;
    this.stateLine.replaceChildren(state, line);
    this.heading.title = status.origin;

    for (const outcome of OUTCOMES) {
      this.legendRows[outcome.key].count.textContent = numberFormat.format(status[outcome.counter] || 0);
    }
    this.dropped.hidden = !status.dropped_links;
    this.dropped.textContent = `${plural(status.dropped_links, "link")} dropped because the queue was full. Raise the queue limit to keep them.`;

    this.renderActions(status);
    if (!this.busy && !this.offline && !this.noteIsError) this.setNote(this.noteFor(status));
    this.renderFilters();
    this.renderCount();
  }

  // What the crawl itself needs comes first, and a missing address never hides it.
  noteFor(status) {
    return [this.statusNote(status), this.infoNote].filter(Boolean).join(" ");
  }

  statusNote(status) {
    if (status.status === "interrupted") return "The app closed while this crawl was running. Finished pages are safe, and Resume continues from where it stopped.";
    if (status.status === "failed") return "Something unexpected stopped this crawl. The log says what happened, and Restart tries again.";
    if (status.status === "completed" && !status.pages_crawled) return "This crawl finished without indexing anything. The reasons are listed beside the map.";
    return "";
  }

  setNote(text, isError = false) {
    this.noteIsError = isError;
    this.note.hidden = !text;
    this.note.textContent = text;
    this.note.classList.toggle("is-error", isError);
    this.root.classList.toggle("has-note", Boolean(text));
  }

  renderActions(status) {
    const valid = ACTIONS_FOR[status.status] || [];
    const key = `${valid.join()}|${this.busy ? 1 : 0}`;
    if (key === this.actionKey) return;
    this.actionKey = key;
    const buttons = valid.map((action) => {
      const button = element("button", "btn btn-secondary", ACTION_LABELS[action]);
      button.type = "button";
      button.disabled = Boolean(this.busy);
      button.addEventListener("click", () => this.act(action));
      return button;
    });
    if (this.options.showFullStatus) {
      const full = element("a", "btn btn-secondary", "Full status");
      full.href = `/crawler/${encodeURIComponent(this.crawlerId)}`;
      buttons.push(full);
    }
    const search = element("a", "btn btn-primary", "Search pages");
    search.href = "/search-page";
    buttons.push(search);
    this.actions.replaceChildren(...buttons);
  }

  async act(action) {
    const { controller } = this;
    this.busy = true;
    this.actionKey = null;
    this.setNote(action === "restart" ? "Restarting. This waits for the page in progress to finish…" : "");
    this.renderActions(this.status);
    const result = await postJson(`${this.base}/${action}`);
    this.busy = false;
    this.actionKey = null;
    if (controller !== this.controller) return;
    this.setNote(result.ok ? "" : result.data.message || "That did not work.", !result.ok);
    try {
      const status = await getJson(this.base, controller.signal);
      if (action === "restart" && result.ok) this.resetRecords();
      this.renderStatus(status);
      await this.refreshVisits(controller.signal);
    } catch (error) {
      if (error.name !== "AbortError") this.setNote(error.message, true);
    }
  }

  renderCaption() {
    const hidden = this.map.unlabelledParts();
    const parts = hidden ? ` ${plural(hidden, "smaller part")} of the site ${hidden === 1 ? "has" : "have"} no label.` : "";
    this.mapCaption.textContent = `The triangle is the starting address. Each ring is one more link away, each road a part of the site, and each mark one address.${parts}`;
  }

  // ---------- Legend and filters ----------
  renderReasons(reasons) {
    for (const key of ["skipped", "failed"]) {
      const rows = reasons
        .filter((entry) => entry.outcome === key)
        .map((entry) => {
          const row = element("li");
          row.append(element("span", "", entry.reason || "other"), element("span", "", numberFormat.format(entry.count)));
          return row;
        });
      this.legendRows[key].reasons.replaceChildren(...rows);
    }
  }

  setFilter(key) {
    this.filter = key;
    this.map.setFilter(key);
    for (const [name, { row }] of Object.entries(this.legendRows)) {
      row.setAttribute("aria-pressed", String(name === key));
    }
    this.shown = 50;
    this.visitList.scrollTop = 0;
    this.renderActivity();
  }

  renderFilters() {
    for (const { filter, button } of this.filterButtons) {
      const count = filter.counter ? (this.status ? this.status[filter.counter] || 0 : 0) : this.knownTotal || 0;
      button.replaceChildren(element("span", "", filter.label), element("span", "filter-count", numberFormat.format(count)));
      button.setAttribute("aria-pressed", String(filter.key === (this.filter || null)));
    }
  }

  // ---------- Activity ----------
  // While a crawl runs the newest come first. Once it stops, anything that went wrong comes first.
  isLive() {
    return Boolean(this.status) && this.status.status === "running";
  }

  filteredRecords() {
    if (this.filter === "waiting") return this.waiting.map((item) => ({ id: `waiting:${item.url}`, ...item, outcome: "waiting", reason: "", detail: "" }));
    const newestFirst = [...this.visits].reverse();
    if (this.filter) return newestFirst.filter((visit) => visit.outcome === this.filter);
    if (this.isLive()) return newestFirst;
    return newestFirst.sort((a, b) => PROBLEMS_FIRST[a.outcome] - PROBLEMS_FIRST[b.outcome] || b.id - a.id);
  }

  renderCount() {
    const total = this.knownTotal || 0;
    let text = addressCount(total);
    if (!this.filter && total) text += this.isLive() ? ", newest first" : ", problems first";
    if (total > this.visits.length) text += `. The map and this list show the latest ${numberFormat.format(this.visits.length)}, and the counts cover all of them`;
    this.activityCount.textContent = text;
  }

  rowReason(record) {
    if (record.outcome === "indexed") return record.detail ? `Indexed: ${record.detail}` : "Indexed, no title";
    return describeOutcome(record);
  }

  addressText(record) {
    const originHost = this.status ? hostOf(this.status.origin) : "";
    return hostOf(record.url) === originHost ? readableUrl(record.url).slice(originHost.length) || "/" : readableUrl(record.url);
  }

  renderActivity() {
    const records = this.filteredRecords();
    const rows = records.slice(0, this.shown).map((record) => {
      const item = element("li");
      const row = element("button", "visit");
      row.type = "button";
      row.title = record.url;
      row.dataset.id = record.id;
      const isSelected = this.selected === record.id;
      row.setAttribute("aria-pressed", String(isSelected));
      const depth = element("span", "depth-chip", `depth ${record.depth}`);
      depth.style.background = depthTint(record.depth);
      row.append(markIcon(record.outcome), element("span", "visit-url", this.addressText(record)), depth, element("span", `visit-why w-${record.outcome}`, this.rowReason(record)));
      row.addEventListener("click", () => this.selectRecord(this.map.find(record.id) || record));
      item.append(row);
      if (isSelected) item.append(this.inlineRecord(record));
      return item;
    });
    if (!rows.length) {
      const message = this.filter ? "No addresses of this kind." : "Nothing has been visited yet.";
      rows.push(element("li", "no-visits", message));
    }
    const focused = document.activeElement && this.visitList.contains(document.activeElement) ? document.activeElement.dataset.id : null;
    const scroll = this.visitList.scrollTop;
    this.visitList.replaceChildren(...rows);
    this.visitList.scrollTop = scroll;
    if (focused) {
      const again = this.findRow(focused);
      if (again) again.focus({ preventScroll: true });
    }
    this.moreButton.hidden = records.length <= this.shown;
    this.renderFilters();
    this.renderCount();
  }

  findRow(id) {
    return [...this.visitList.querySelectorAll(".visit")].find((row) => row.dataset.id === String(id)) || null;
  }

  // ---------- One address ----------
  // A mark and its row are one record: selecting either marks both.
  selectRecord(record, { fromMap = false } = {}) {
    this.selected = record ? record.id : null;
    this.selectedRecord = record;
    this.map.select(this.selected);
    if (record) {
      if (this.filter && this.filter !== record.outcome) this.setFilter(null);
      const position = this.filteredRecords().findIndex((item) => item.id === record.id);
      if (position >= this.shown) this.shown = position + 25;
    }
    this.renderRecord();
    this.renderActivity();
    if (record && fromMap) {
      this.showTip(record);
      this.scrollListTo(record.id);
    }
  }

  scrollListTo(id) {
    const row = this.findRow(id);
    if (!row) return;
    const list = this.visitList.getBoundingClientRect();
    const box = row.getBoundingClientRect();
    this.visitList.scrollTop += box.top - list.top - 40;
  }

  showInList(record) {
    const row = this.findRow(record.id);
    if (!row) return;
    row.scrollIntoView({ block: "center" });
    row.focus({ preventScroll: true });
  }

  recordDetails(record) {
    const list = element("dl");
    const add = (label, value) => {
      const description = element("dd");
      if (value instanceof Node) description.append(value);
      else description.textContent = value;
      list.append(element("dt", "", label), description);
    };
    const href = safeLink(record.url);
    if (href) {
      const link = element("a", "", readableUrl(record.url));
      link.href = href;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      add("Address", link);
    } else {
      add("Address", record.url);
    }
    add("Result", describeOutcome(record));
    add("Depth", String(record.depth));
    if (record.detail && record.detail !== record.reason) add(detailLabel(record), record.detail);
    return list;
  }

  inlineRecord(record) {
    const box = element("div", "visit-record");
    const button = element("button", "text-button", "Show on the map");
    button.type = "button";
    button.addEventListener("click", () => this.figure.scrollIntoView({ block: "center" }));
    box.append(this.recordDetails(record), button);
    return box;
  }

  renderRecord() {
    const record = this.selected === null ? null : this.selectedRecord;
    if (!record) {
      this.record.replaceChildren(element("h3", "", "Selected address"), element("p", "", "Select a mark on the map or an address in the list to see what happened to it."));
      return;
    }
    const button = element("button", "text-button", "Show in the list");
    button.type = "button";
    button.addEventListener("click", () => this.showInList(record));
    this.record.replaceChildren(element("h3", "", "Selected address"), this.recordDetails(record), button);
  }

  showTip(record) {
    const matrix = this.map.node.getScreenCTM();
    if (!record || !matrix) {
      this.tip.hidden = true;
      return;
    }
    this.tip.replaceChildren(document.createTextNode(readableUrl(record.url)), element("span", "", describeOutcome(record)));
    this.tip.hidden = false;
    const point = new DOMPoint(record.x, record.y).matrixTransform(matrix);
    const figureBox = this.figure.getBoundingClientRect();
    const half = Math.min(this.tip.offsetWidth / 2, figureBox.width / 2);
    this.tip.style.left = `${Math.max(half, Math.min(figureBox.width - half, point.x - figureBox.left))}px`;
    this.tip.style.top = `${point.y - figureBox.top}px`;
  }
}
