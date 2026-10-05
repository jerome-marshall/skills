# Highlight

Paint what the caption names. Generic DOM only. One paint per beat.

| Caption names | Paint |
| --- | --- |
| A **node** (the control) | Outline that node (`highlight`, walk-up). |
| A **region** (panel, dialog, section) | Overlay that box (resolve, then `highlightRegion`). |
| A **relation** between A and B | Overlay its declared gap, seam, or overlap (`highlightRelation`). |
| Paint would cover the claim pixels | Caption and hold. Optional pointer **outside** those pixels. |

Outline tracks scroll. Overlay (`page.screencast.showOverlay`) is a frozen snapshot — still regions and relations only.

Done when: each beat's paint matches its caption class. Relation geometry
matches its declared axis, order, and state.

## Node

```ts
async function highlight(locator: Locator, color = "#0ea5e9", walk = true) {
  await locator.evaluate((n, { c, walk: doWalk }) => {
    const CONTROL = "input,select,textarea,button,[role=combobox]";
    const el = n as HTMLElement;
    const area = (e: HTMLElement) => {
      const r = e.getBoundingClientRect();
      return r.width * r.height;
    };
    const controlsIn = (root: ParentNode) =>
      [...root.querySelectorAll(CONTROL)] as HTMLElement[];
    const paint = (best: HTMLElement) => {
      if (!best.dataset.prDemoHl) {
        best.dataset.prDemoHl = JSON.stringify({
          outline: best.style.outline,
          outlineOffset: best.style.outlineOffset,
        });
      }
      best.style.outline = `3px solid ${c}`;
      best.style.outlineOffset = "4px";
    };
    let best = el;
    if (doWalk) {
      const t = area(el);
      for (
        let d = 0, cur = el.parentElement;
        d < 4 && cur;
        d++, cur = cur.parentElement
      ) {
        if (area(cur) > t * 2.5) break;
        if (controlsIn(cur).length > 2) break;
        const siblings = controlsIn(cur).filter(
          (x) => x !== el && !best.contains(x) && !x.contains(el),
        );
        if (siblings.length) break;
        best = cur;
      }
    }
    paint(best);
  }, { c: color, walk });
  return { kind: "node" };
}
```

Paint outline and offset only on the node. `#0ea5e9` = before / disabled. `#22c55e` = after / enabled.

## Region and relation

A relation's locators are the two exact **visual** pieces. Declare its axis,
order, and state: `gap`, `flush`, or `overlap`. Locator resolution never walks
to a guessed descendant. Geometry that does not match the declaration throws
before recording.

Keep `overlays` next to these helpers. Overlay HTML is `position:absolute` with the box's `x/y/width/height`.

```ts
const overlays = [];

async function overlayRect(page, r, color) {
  if (!r || r.width <= 0 || r.height <= 0) {
    throw new Error("required preview paint has no visible rectangle");
  }
  const d = await page.screencast.showOverlay(`
    <div style="position:absolute;left:${r.x}px;top:${r.y}px;width:${r.width}px;height:${r.height}px;
      box-sizing:border-box;border:3px solid ${color};background:${color}33;"></div>`);
  overlays.push(d);
}

async function highlightRegion(page, locator, color = "#0ea5e9") {
  await overlayRect(page, await locator.boundingBox(), color);
  return { kind: "region" };
}

function relationRect(a, b, {
  axis = "vertical",
  order = "a-before-b",
  kind = "gap",
} = {}) {
  const [first, second] = order === "a-before-b" ? [a, b] : [b, a];
  const vertical = axis === "vertical";
  if (!vertical && axis !== "horizontal") throw new Error(`bad axis: ${axis}`);
  if (!["a-before-b", "b-before-a"].includes(order)) {
    throw new Error(`bad order: ${order}`);
  }
  if (!["gap", "flush", "overlap"].includes(kind)) {
    throw new Error(`bad relation kind: ${kind}`);
  }
  const crossStart = Math.max(
    vertical ? first.x : first.y,
    vertical ? second.x : second.y,
  );
  const crossEnd = Math.min(
    vertical ? first.x + first.width : first.y + first.height,
    vertical ? second.x + second.width : second.y + second.height,
  );
  if (crossEnd <= crossStart) {
    throw new Error("relation anchors have no perpendicular overlap");
  }
  const firstEnd = vertical
    ? first.y + first.height
    : first.x + first.width;
  const secondStart = vertical ? second.y : second.x;
  const delta = secondStart - firstEnd;
  if (kind === "gap" && delta <= 0) throw new Error(`expected gap, got ${delta}`);
  if (kind === "flush" && Math.abs(delta) > 1) {
    throw new Error(`expected flush, got ${delta}`);
  }
  if (kind === "overlap" && delta >= 0) {
    throw new Error(`expected overlap, got ${delta}`);
  }
  const primaryStart = kind === "flush"
    ? firstEnd - 1.5
    : Math.min(firstEnd, secondStart);
  const primarySize = kind === "flush" ? 3 : Math.abs(delta);
  return vertical
    ? { x: crossStart, y: primaryStart, width: crossEnd - crossStart,
        height: primarySize, distance: delta }
    : { x: primaryStart, y: crossStart, width: primarySize,
        height: crossEnd - crossStart, distance: delta };
}

async function highlightRelation(page, a, b, options = {}) {
  const ba = await a.boundingBox();
  const bb = await b.boundingBox();
  if (!ba || !bb) throw new Error("relation anchor is not visible");
  const config = {
    axis: "vertical",
    order: "a-before-b",
    kind: "gap",
    ...options,
  };
  const r = relationRect(ba, bb, config);
  await overlayRect(page, r, config.color || "#0ea5e9");
  return {
    kind: "relation",
    axis: config.axis,
    order: config.order,
    state: config.kind,
    distance: r.distance,
  };
}
```

Store the returned object as the workflow beat's `paint`; its `distance` is
the served spacing fingerprint. A caption
which says “below” uses `axis: "vertical", order: "a-before-b"`; a caption
which says “beside” uses the horizontal equivalent. The review frame must show
that the overlay touches both named anchors and no unrelated region.

Region captions resolve the locator below, then `highlightRegion`:

- Accordion: `closest("details[open]")`, else the panel id in `aria-controls`
  on the nearest `[aria-expanded=true]`, else the nearest `[role=region]`
  that contains the control.
- Modal: `closest("dialog, [role=dialog]")` — the dialog panel, not the
  dimmed backdrop.
- Section: `closest("section, article, header")`.

## Clear

```ts
async function clearHighlights(page: Page) {
  try {
    await page.evaluate(() => {
      document.querySelectorAll("[data-pr-demo-hl]").forEach((n) => {
        const e = n as HTMLElement;
        const previous = JSON.parse(e.dataset.prDemoHl || "{}");
        e.style.outline = previous.outline || "";
        e.style.outlineOffset = previous.outlineOffset || "";
        delete e.dataset.prDemoHl;
      });
    });
  } finally {
    const current = overlays.splice(0);
    await Promise.allSettled(current.map((d) => d.dispose()));
  }
}
```

`clearHighlights` restores the exact prior node styles and disposes every
overlay. The hero calls it in `finally`; stills use a fresh page regardless.

## Style

Inject during recording. Node outline plus offset, not padding or margin —
those shift layout mid-take. Hold for the full caption window;
`clearHighlights` before the next beat. Bake the paint into the recording;
ffmpeg is captions only.
