---
name: Crawler
description: A search engine on your own machine that shows what it did to every address.
colors:
  water: "#0f4a5c"
  water-deep: "#0a3744"
  water-soft: "#cfe3e8"
  water-tint: "#e6f1f2"
  ink: "#10323c"
  ink-soft: "#4a666c"
  paper: "#ffffff"
  ground: "#f1f4ea"
  ground-soft: "#f7f9f2"
  rule: "#cbd7d0"
  rule-strong: "#7e9aa0"
  depth-0: "#a9d3de"
  depth-1: "#c4e1e6"
  depth-2: "#dcedec"
  depth-3: "#edf4ea"
  contour: "#a9673a"
  contour-text: "#85501f"
  road: "#c8321e"
  road-text: "#ad2a18"
  road-tint: "#fbeae7"
  wood: "#27693f"
  amber: "#875a10"
  wait: "#6f97a3"
  wait-bar: "#c4d6da"
  pin: "#f2c14e"
  highlight: "#fbe7a1"
  visited: "#5b4b8a"
typography:
  brand:
    fontFamily: "Barlow, Segoe UI, system-ui, sans-serif"
    fontSize: "21px"
    fontWeight: 700
  title:
    fontFamily: "Barlow, Segoe UI, system-ui, sans-serif"
    fontSize: "24px"
    fontWeight: 700
    lineHeight: 1.2
  section:
    fontFamily: "Barlow, Segoe UI, system-ui, sans-serif"
    fontSize: "18px"
    fontWeight: 700
  result-title:
    fontFamily: "Barlow, Segoe UI, system-ui, sans-serif"
    fontSize: "19px"
    fontWeight: 600
    lineHeight: 1.3
  count:
    fontFamily: "Barlow, Segoe UI, system-ui, sans-serif"
    fontSize: "19px"
    fontWeight: 700
    fontFeature: "tnum"
  body:
    fontFamily: "Barlow, Segoe UI, system-ui, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.45
  label:
    fontFamily: "Barlow, Segoe UI, system-ui, sans-serif"
    fontSize: "14px"
    fontWeight: 400
  small:
    fontFamily: "Barlow, Segoe UI, system-ui, sans-serif"
    fontSize: "13px"
    fontWeight: 400
  place-name:
    fontFamily: "Barlow, Segoe UI, system-ui, sans-serif"
    fontSize: "14px"
    fontWeight: 500
  log:
    fontFamily: "ui-monospace, Cascadia Mono, Consolas, Menlo, monospace"
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.5
rounded:
  sm: "2px"
  md: "4px"
spacing:
  xs: "6px"
  sm: "8px"
  md: "12px"
  lg: "24px"
  edge: "28px"
components:
  button-primary:
    backgroundColor: "{colors.water}"
    textColor: "{colors.paper}"
    rounded: "{rounded.md}"
    padding: "0 16px"
    height: "40px"
  button-primary-hover:
    backgroundColor: "{colors.water-deep}"
  button-secondary:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.water}"
    rounded: "{rounded.md}"
    padding: "0 16px"
    height: "40px"
  button-secondary-hover:
    backgroundColor: "{colors.water-tint}"
  input:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    padding: "0 10px"
    height: "40px"
  filter:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.water}"
    rounded: "{rounded.md}"
    padding: "0 10px"
    height: "34px"
  filter-pressed:
    backgroundColor: "{colors.water}"
    textColor: "{colors.paper}"
---

# Design System: Crawler

## Overview

**Creative North Star: "The Survey Sheet"**

A crawl is a survey of a site, so the app reads like a good national map: exact, legible at a glance, and with a key that accounts for every symbol. The map is the one expressive object. Everything around it is standard web controls set in ruled rows, because a person checking a crawl should know where everything is before they notice the style.

The system exists to make one claim believable: nothing goes missing unseen. Skipped and failed addresses are drawn as plainly as indexed ones, and each has a reason. It deliberately avoids the look of an ordinary SaaS dashboard, which the owner named as the one thing that would feel wrong.

**Key Characteristics:**
- One map, drawn only from real records, as the focal element.
- One drawing of each mark, shared by the map, the legend and the list.
- Ruled rows at one hairline weight instead of padded cards.
- Colour that means something: state on the marks, depth on the tints.
- No metric cards.

## Colors

The palette comes from a topographic sheet: deep water, map white, woodland tints, sienna contours and road red.

### Primary
- **Deep Water** (`water`): the shell bar, primary buttons, links, pressed filters and the start triangle.
- **Deeper Water** (`water-deep`): primary button hover and the map tip.

### Secondary
- **Depth Tints** (`depth-0` to `depth-3`): one tint per link depth, darkest at the start and palest from depth 3 outward. The same tint marks a depth on the map, in the address list and in search results.
- **Survey Pin** (`pin`): the brand triangle and the current page's underline in the shell, and nowhere else.

### Tertiary
- **Sienna Contour** (`contour`, text `contour-text`): contour lines, the skipped mark and skipped text.
- **Road Red** (`road`, text `road-text`, ground `road-tint`): failure only.
- **Woodland** (`wood`): a running crawl, and result addresses on the search page.
- **Amber** (`amber`): a paused or interrupted crawl, and the dropped links warning.
- **Waiting Blue** (`wait`, bar `wait-bar`): addresses still in the queue.

### Neutral
- **Survey Ink** (`ink`): text and the indexed mark.
- **Faded Ink** (`ink-soft`): secondary text, at least 4.5:1 on every ground used.
- **Map White** (`paper`): the working area and inputs.
- **Woodland Ground** (`ground`, `ground-soft`): the search page, and the crawl list column.
- **Hairlines** (`rule`, `rule-strong`): dividers, and control borders and roads.
- **Marker Yellow** (`highlight`): matched words and text selection.

### Named Rules
**The Red Means Failure Rule.** Road red marks something that failed. A Stop button is an ordinary button.

**The Key Rule.** A colour on a mark or a depth means the same thing on all three pages, so what someone learns on the map still holds in the list and in search.

## Typography

**Display Font:** Barlow, self-hosted (with Segoe UI, system-ui, sans-serif)
**Body Font:** Barlow
**Label/Mono Font:** the system monospace, for the log only

**Character:** One workhorse grotesque with road-sign ancestry. It suits a map and stays clear at small sizes, and it covers Turkish letters through its latin-ext files.

### Hierarchy
- **Title** (700, 24px, 1.2): the crawl's host.
- **Section** (700, 18px): the heading over the address list.
- **Result title** (600, 19px, 1.3): search results, clamped to two lines.
- **Count** (700, 19px, tabular): legend counts.
- **Body** (400, 15px, 1.45): running text, and snippets at up to 72ch.
- **Label** (400, 14px): form labels and record details.
- **Small** (400, 13px, tabular for numbers): counts, captions and reasons.
- **Place name** (italic 500, 14px on screen): names on the map, and the only italics in the system.
- **Log** (400, 13px, 1.5): the raw log, because it is a machine record.

### Named Rules
**The Lined-Up Numbers Rule.** Every number that can change uses tabular figures.

**The One Italic Rule.** Italics are for place names on the map, as on a real map. Emphasis elsewhere comes from weight.

## Layout

Dashboard: a water-blue shell bar, a white row for starting a crawl, then the crawl list in about a third of the width beside the selected crawl. Within a crawl, the map takes the remaining width next to a 300px legend, with the address list below them. The status page uses the same view at up to 1240px with the log added. Search is one 860px column on the ground.

Density comes from ruled rows, with 6, 8 and 12px gaps inside groups, 24px between columns and 28px at the page edge. Below 1240px the legend moves under the map. Below 820px the list stacks above the crawl, and picking a crawl scrolls to it. Below 700px the limits fold behind a Limits button and the edge is 16px. The address list scrolls inside a 460px area, except on phones, where the page scrolls instead.

## Elevation & Depth

The system is flat, with no shadows. Depth is conveyed by tone: map white on woodland ground, and the depth tints on the map. The tip over the map is the only thing that overlaps, and it uses the darker water colour rather than a shadow.

### Named Rules
**The Flat Sheet Rule.** Nothing casts a shadow. A printed map has no shadows, and these surfaces don't need them.

## Shapes

Small, square corners: 4px on controls and the tip, 2px on depth chips and highlighted words. Lists have no rounding, and rules are one pixel of one weight. The only organic shapes are the map's contours, which are real data boundaries with a slight wobble, seeded by the crawl so each crawl keeps its own outline.

## Components

### Buttons
- **Shape:** gently squared (4px), 40px tall.
- **Primary:** water ground with white text, used once per area for the main action.
- **Hover / Focus:** a colour change over 150ms. Focus is a 2px water outline, or pin yellow in the shell.
- **Secondary:** white with a water border and text. Only the actions valid right now are shown.

### Filters
- **Style:** 34px tall, with a label and a tabular count.
- **State:** pressed fills with water. They share their state with the legend rows, so either control changes both.

### Inputs / Fields
- **Style:** 40px, white, one-pixel `rule-strong` border, with the label above in 14px.
- **Focus:** the 2px water outline.
- **Error:** the server's message in road text beneath the form, never an alert.

### Navigation
- **Style:** white 600-weight links in the shell, with a 3px underline in `water-soft` on hover and `pin` on the current page.

### Crawl Row
A full-width button with host, status, a 6px bar split by outcome, and a line of counts. The selected row turns white and gains a small triangle.

### The Crawl Map (signature)
An SVG sheet. The triangle is the starting address, each ring is one more link away, and a hairline road runs out to each of the largest parts of the site, ending where that part's marks end, with its name on the sheet beside the end. Names sit under the marks so they never hide an address. Roads are laid in the order parts first appear, and a mark's place follows from its road, address and depth, so a placed mark never moves, and a crawl draws the same way wherever it is opened. Text and marks are counter-scaled so they keep their size on a phone. A new mark lands with a 200ms fade and scale, which is the only motion here, and it is removed under reduced motion. Selecting a mark rings it, shows its record beside the map, and finds its row in the list. Selecting a row does the reverse.

### Legend
Ruled rows with a mark, a label and a count, with reasons listed under Skipped and Failed. Each row also acts as a filter.

### Address List
One row per address, with its mark, address, depth chip and result. While a crawl runs the newest come first, and once it stops, problems come first. A selected row shows its record in place.

## Do's and Don'ts

### Do:
- **Do** draw every mark from a real record, and label anything left unlabelled honestly, as the map's caption does.
- **Do** show failed and skipped addresses as plainly as indexed ones, each with its reason.
- **Do** use the shared mark drawings and the depth tints whenever a mark or a depth appears.
- **Do** keep controls standard: real buttons, inputs, selects and links.
- **Do** put text from crawled pages on the page only as text, never as HTML.
- **Do** serve everything from the app, with no other hosts at runtime.

### Don't:
- **Don't** use metric cards or a row of big numbers above a table. It reads as an ordinary SaaS dashboard, the one look the owner ruled out.
- **Don't** use road red for anything but failure.
- **Don't** add shadows or a second line weight.
- **Don't** move a mark once it is placed.
- **Don't** add marks to the map for decoration.
