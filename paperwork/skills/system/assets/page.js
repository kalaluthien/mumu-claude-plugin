(() => {
  "use strict";
  const read = id => JSON.parse(document.getElementById(id).textContent);
  const TAGS = read("page-tags"), FORMULAS = read("page-formulas");
  const $ = id => document.getElementById(id);
  const make = (name, attributes = {}, ...children) => {
    const element = document.createElement(name);
    for (const [key, value] of Object.entries(attributes)) key === "class" ? (element.className = value) : element.setAttribute(key, value);
    element.append(...children);
    return element;
  };
  const draw = (name, attributes) => {
    const element = document.createElementNS("http://www.w3.org/2000/svg", name);
    for (const [key, value] of Object.entries(attributes)) element.setAttribute(key, value);
    return element;
  };
  const still = () => matchMedia("(prefers-reduced-motion: reduce)").matches;

  let terms = [], contract, records, levelOf, openers, entries, shownLevel = null, boxes = {}, curves = {}, blocks = [], faces = {}, plans = {};
  const view = { level: null, at: null, scenario: null, step: 0 };

  // ---- the contract's records ----
  function load(data) {
    contract = data;
    records = {}; levelOf = {}; openers = {};
    for (const level of contract.levels) {
      records[level.id] = { kind: "level", record: level };
      for (const [kind, group] of [["area", level.areas || []], ["node", level.nodes], ["edge", level.edges || []]])
        for (const record of group) { records[record.id] = { kind, record }; levelOf[record.id] = level.id; }
    }
    for (const level of contract.levels) for (const node of level.nodes) if (node.opens) (openers[node.opens] = openers[node.opens] || []).push(node.id);
    for (const scenario of contract.scenarios || []) records[scenario.id] = { kind: "scenario", record: scenario };
    for (const property of contract.properties || []) records[property.id] = { kind: "property", record: property };
    terms = (contract.terms || []).map(entry => ({ entry, pattern: new RegExp(String.raw`(?<![\p{L}\p{N}./-])` + entry.term.trim().split(/\s+/).map(word => word.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join(String.raw`\s+`)
      + (/[가-힣]$/.test(entry.term) ? "" : String.raw`(?:e?s)?(?![\p{L}\p{N}-]|[./][\p{L}\p{N}])`), "iu") })); // a Korean term takes a particle after it; a file name is no term
    entries = index();
  }
  const label = id => records[id] ? (records[id].record.label || records[id].record.title || id) : id;
  // a quote, a formula or a named record in a text; the formula's pattern is tex_mathml.py's, which make-page.py drew each one by
  const MARKS = /(```[\s\S]*?```|`[^`]+`)|\$\$([^$`]+?)\$\$|\$(?!\{[A-Z_]+\})([^\s$`](?:[^$`]*?[^\s$`])?)\$(?!\d)|\{([a-z0-9-]+)\}/g;
  const words = text => String(text).replace(MARKS, (whole, quote, block, inline, id) => (id && records[id] ? label(id) : whole));
  const bare = text => words(text).replace(/`([^`]+)`/g, "$1"); // text drawn where no code face can show, such as a tooltip, keeps a code span's words without its marks
  const tagName = tag => String(tag).replace(/[A-Z]/g, letter => " " + letter.toLowerCase()); // a tag's id as the words it joins
  const sentence = edge => edge.tag === "transition"
    ? `${label(edge.from)} → ${label(edge.to)} on ${words(edge.label)}`
    : `${label(edge.from)} ${words(edge.label)} ${label(edge.to)}.`;
  const home = id => { // the level a record is seen on
    const found = records[id];
    if (!found) return null;
    if (found.kind === "level") return id;
    if (levelOf[id]) return levelOf[id];
    if (found.kind === "scenario") return home(found.record.steps[0].at);
    return (found.record.on || []).map(home).find(Boolean) || contract.levels[0].id;
  };

  // ---- layout ----
  function layered(items, links, gapMain, gapCross, down) {
    const main = item => down ? item.h : item.w, cross = item => down ? item.w : item.h;
    const out = new Map(items.map(item => [item.id, []])), beside = new Map(items.map(item => [item.id, []]));
    const seen = {}, back = new Set(), order = [], rank = {};
    for (const [from, to] of links) if (from !== to && out.has(from) && out.has(to)) out.get(from).push(to);
    const visit = id => {
      seen[id] = 1;
      for (const next of out.get(id)) { if (seen[next] === 1) back.add(id + ">" + next); else if (!seen[next]) visit(next); }
      seen[id] = 2; order.unshift(id);
    };
    items.forEach(item => seen[item.id] || visit(item.id));
    for (const id of order) {
      rank[id] = rank[id] || 0;
      for (const next of out.get(id)) if (!back.has(id + ">" + next)) rank[next] = Math.max(rank[next] || 0, rank[id] + 1);
    }
    for (const [from, to] of links) if (out.has(from) && out.has(to) && from !== to) { beside.get(to).push(from); beside.get(from).push(to); }
    const columns = [];
    for (const item of items) (columns[rank[item.id]] = columns[rank[item.id]] || []).push(item);
    const place = {};
    columns.forEach(column => column.forEach((item, i) => (place[item.id] = i)));
    for (let sweep = 0; sweep < 6; sweep++) {
      for (const column of sweep % 2 ? [...columns].reverse() : columns) {
        const weight = item => { const near = beside.get(item.id).filter(id => rank[id] !== rank[item.id]); return near.length ? near.reduce((sum, id) => sum + place[id], 0) / near.length : place[item.id]; };
        const weights = new Map(column.map(item => [item.id, weight(item)]));
        column.sort((a, b) => weights.get(a.id) - weights.get(b.id));
        column.forEach((item, i) => (place[item.id] = i));
      }
    }
    const spans = columns.map(column => column.reduce((sum, item) => sum + cross(item), 0) + gapCross * (column.length - 1));
    const span = Math.max(...spans);
    const at = {};
    let far = 0;
    columns.forEach((column, c) => {
      const deep = Math.max(...column.map(main));
      let side = (span - spans[c]) / 2;
      for (const item of column) {
        const a = far + (deep - main(item)) / 2;
        at[item.id] = down ? { x: side, y: a, w: item.w, h: item.h } : { x: a, y: side, w: item.w, h: item.h };
        side += cross(item) + gapCross;
      }
      far += deep + gapMain;
    });
    return down ? { at, w: span, h: far - gapMain } : { at, w: far - gapMain, h: span };
  }

  const FONT = 'ui-sans-serif, system-ui, -apple-system, "Segoe UI", "Apple SD Gothic Neo", "Malgun Gothic", sans-serif';
  const ROOM = { side: 40, top: 76, bottom: 76 };
  const FITS = [ // a level's drawings from roomy to dense; inner and outer hold the gap along a flow down, along a flow across, then beside each
    { inner: [52, 72, 28, 22], outer: [64, 96, 44, 36], pad: 17, head: 32, labels: true },
    { inner: [44, 52, 24, 18], outer: [52, 60, 36, 28], pad: 17, head: 32 },
    { inner: [30, 36, 14, 12], outer: [38, 44, 22, 18], pad: 9, head: 26, dense: true },
    { inner: [22, 26, 10, 10], outer: [28, 30, 14, 12], pad: 9, head: 26, dense: true },
  ];
  const pen = document.createElement("canvas").getContext("2d"), LID = 10;
  function size(level, fit, grown = 1) { // a node as wide as its label needs: every node of a roomy level alike, each its own on a dense one
    pen.font = `500 ${fit.dense ? 12 : 14}px ${FONT}`;
    const most = fit.dense ? 260 : 320, beside = node => (node.opens ? 32 : 0) + (fit.dense ? 26 : 30), text = node => Math.ceil(pen.measureText(node.label).width * 1.1 * grown);
    const need = node => text(node) + beside(node);
    const lines = node => need(node) <= most ? 1 : Math.ceil(text(node) * 1.15 / (most - beside(node))); // a label too long for the widest box goes on over more lines
    const widest = Math.min(most, Math.max(196, ...level.nodes.map(need))), tallest = 58 + 20 * (Math.max(...level.nodes.map(lines)) - 1);
    const lid = node => node.tag === "dataStore" ? LID : 0; // a data store's cylinder lid sits above its label
    return Object.fromEntries(level.nodes.map(node => [node.id, fit.dense ? { w: Math.min(most, Math.max(96, need(node))), h: 40 + 16 * (lines(node) - 1) + lid(node) } : { w: widest, h: tallest + lid(node) }]));
  }
  const heading = (area, fit) => { // an area as wide as its header's label and tag, so neither reaches past its frame
    pen.font = `500 12px ${FONT}`;
    const label = pen.measureText(area.label).width;
    pen.font = `400 12px ${FONT}`;
    return Math.ceil(label + 4 + pen.measureText(tagName(area.tag)).width) + 2 * fit.pad;
  };
  const wide = edges => Math.max(0, ...edges.map(edge => words(edge.label).length)) * 6.4 + 56;
  const across = () => innerWidth - 2 * ROOM.side, down = () => innerHeight - ROOM.top - ROOM.bottom;
  const fill = plan => Math.min(across() / plan.w, down() / plan.h);
  function arrange(level) {
    const used = plan => { const scale = Math.min(fill(plan), 1.3); return Math.min(plan.w * scale / across(), plan.h * scale / down()); };
    const spread = plan => { // the side with room to spare gets wider gaps, never larger type
      for (let wider = 1, taller = 1, turns = 0; turns < 16; turns++) {
        const steps = [[wider * 1.25, taller], [wider, taller * 1.25]];
        if (plan.w / across() > plan.h / down()) steps.reverse();
        const gain = steps.filter(step => Math.max(...step) <= 3).map(step => ({ step, next: { ...plan, ...attempt(level, plan.fit, plan.sizes, plan.outerDown, plan.innerDown, ...step) } }))
          .find(({ next }) => Math.min(fill(next), 1) >= Math.min(fill(plan), 1) - .001 && used(next) > used(plan) + .001);
        if (!gain) break;
        [wider, taller] = gain.step;
        plan = gain.next;
      }
      return plan;
    };
    for (const fit of FITS) { // the roomiest drawing that fits near full size, turned the way that uses the window most
      const least = fit.dense ? 1 : .85;
      const pick = sizes => {
        const plans = [false, true].flatMap(outerDown => [false, true].map(innerDown => spread({ ...attempt(level, fit, sizes, outerDown, innerDown, 1, 1), fit, sizes, outerDown, innerDown })));
        const fitting = plans.filter(plan => fill(plan) >= least);
        return fitting.length ? fitting.reduce((a, b) => used(b) > used(a) + .01 ? b : a) : plans.reduce((a, b) => fill(b) > fill(a) + .01 ? b : a);
      };
      let best = pick(size(level, fit));
      for (let turn = 0; turn < 2 && fill(best) < 1; turn++) best = pick(size(level, fit, 1 / Math.max(fill(best), .85))); // a level drawn smaller keeps its type's size, so its nodes are measured for the larger type
      if (fill(best) >= least || fit === FITS[FITS.length - 1]) return best;
    }
  }
  function attempt(level, fit, sizes, outerDown, innerDown, across, along) {
    const gaps = (four, down, edges) => down ? [along * four[0], across * four[2]] : [across * Math.max(four[1], fit.labels ? wide(edges) : 0), along * four[3]];
    const groups = new Map();
    for (const area of level.areas || []) groups.set(area.id, { id: area.id, area, nodes: [] });
    for (const node of level.nodes) {
      const key = groups.has(node.area) ? node.area : "alone " + node.id;
      if (!groups.has(key)) groups.set(key, { id: key, nodes: [] });
      groups.get(key).nodes.push(node);
    }
    const groupOf = {}, edges = level.edges || [];
    const used = [...groups.values()].filter(group => group.nodes.length);
    for (const group of used) {
      group.nodes.forEach(node => (groupOf[node.id] = group.id));
      const inner = edges.filter(edge => groupOf[edge.from] === group.id && group.nodes.some(node => node.id === edge.to));
      group.inside = layered(group.nodes.map(node => ({ id: node.id, ...sizes[node.id] })), inner.map(edge => [edge.from, edge.to]), ...gaps(fit.inner, innerDown, inner), innerDown);
      group.w = Math.max(group.inside.w + (group.area ? 2 * fit.pad : 0), group.area ? heading(group.area, fit) : 0);
      group.h = group.inside.h + (group.area ? fit.pad + fit.head : 0);
    }
    const between = edges.filter(edge => groupOf[edge.from] !== groupOf[edge.to]);
    const outer = layered(used.map(group => ({ id: group.id, w: group.w, h: group.h })), between.map(edge => [groupOf[edge.from], groupOf[edge.to]]), ...gaps(fit.outer, outerDown, between), outerDown);
    const box = {};
    for (const group of used) {
      const spot = outer.at[group.id];
      if (group.area) box[group.id] = { ...spot };
      for (const node of group.nodes) {
        const inner = group.inside.at[node.id];
        box[node.id] = { x: spot.x + inner.x + (group.area ? fit.pad : 0), y: spot.y + inner.y + (group.area ? fit.head : 0), ...sizes[node.id] };
      }
    }
    return { box, w: outer.w, h: outer.h };
  }

  function route(level, box, width, height) { // each edge the cheapest path of straight runs that passes under no node
    const STEP = 10, CLEAR = 5, OUT = 4, TURN = 4;
    const columns = Math.ceil(width / STEP) + 2 * OUT + 1, rows = Math.ceil(height / STEP) + 2 * OUT + 1;
    const x = c => (c - OUT) * STEP, y = r => (r - OUT) * STEP, column = at => Math.round(at / STEP) + OUT;
    const blocked = new Uint8Array(columns * rows), used = new Uint8Array(columns * rows), dear = new Uint8Array(columns * rows);
    const cover = (spot, grid, by) => {
      for (let r = Math.max(0, column(spot.y - by)); r < rows && y(r) < spot.y + spot.h + by; r++) if (y(r) > spot.y - by)
        for (let c = Math.max(0, column(spot.x - by)); c < columns && x(c) < spot.x + spot.w + by; c++) if (x(c) > spot.x - by) grid[r * columns + c] = 1;
    };
    for (const node of level.nodes) cover(box[node.id], blocked, CLEAR);
    for (const area of level.areas || []) if (box[area.id]) {
      const frame = box[area.id];
      cover({ ...frame, h: 22 }, dear, 0);
      for (const side of [{ ...frame, h: 0 }, { ...frame, y: frame.y + frame.h, h: 0 }, { ...frame, w: 0 }, { ...frame, x: frame.x + frame.w, w: 0 }]) cover(side, dear, 8);
    }
    const MOVES = [[1, 0], [-1, 0], [0, 1], [0, -1]];
    const ports = spot => {
      const list = [], add = (c, r, way, px, py, off) => { if (c >= 0 && r >= 0 && c < columns && r < rows && !blocked[r * columns + c]) list.push({ c, r, way, px, py, off: off * .4 }); };
      for (let r = column(spot.y + 12); y(r) <= spot.y + spot.h - 12; r++) if (y(r) >= spot.y + 12) {
        const off = Math.abs(y(r) - spot.y - spot.h / 2) / STEP;
        add(Math.ceil((spot.x + spot.w + CLEAR) / STEP) + OUT, r, 0, spot.x + spot.w, y(r), off);
        add(Math.floor((spot.x - CLEAR) / STEP) + OUT, r, 1, spot.x, y(r), off);
      }
      for (let c = column(spot.x + 16); x(c) <= spot.x + spot.w - 16; c++) if (x(c) >= spot.x + 16) {
        const off = Math.abs(x(c) - spot.x - spot.w / 2) / STEP;
        add(c, Math.ceil((spot.y + spot.h + CLEAR) / STEP) + OUT, 2, x(c), spot.y + spot.h, off);
        add(c, Math.floor((spot.y - CLEAR) / STEP) + OUT, 3, x(c), spot.y, off);
      }
      return list;
    };
    const path = (from, to) => {
      const goals = new Map(ports(to).map(port => [(port.r * columns + port.c) * 4 + (port.way ^ 1), port]));
      const far = new Float32Array(columns * rows * 4).fill(Infinity), came = new Int32Array(columns * rows * 4).fill(-1), began = new Map(), heap = [];
      const guess = (c, r) => (Math.max(to.x - x(c), 0, x(c) - to.x - to.w) + Math.max(to.y - y(r), 0, y(r) - to.y - to.h)) / STEP;
      const push = (cost, state) => { let i = heap.push([cost, state]) - 1; for (; i && heap[(i - 1) >> 1][0] > cost; i = (i - 1) >> 1) [heap[i], heap[(i - 1) >> 1]] = [heap[(i - 1) >> 1], heap[i]]; };
      const pop = () => {
        const first = heap[0], last = heap.pop();
        if (heap.length) {
          heap[0] = last;
          for (let i = 0; ;) {
            let least = i;
            for (const k of [2 * i + 1, 2 * i + 2]) if (k < heap.length && heap[k][0] < heap[least][0]) least = k;
            if (least === i) break;
            [heap[i], heap[least]] = [heap[least], heap[i]]; i = least;
          }
        }
        return first;
      };
      for (const port of ports(from)) {
        const at = port.r * columns + port.c, state = at * 4 + port.way, cost = 1 + port.off + (used[at] ? 6 : 0);
        if (cost < far[state]) { far[state] = cost; began.set(state, port); push(cost + guess(port.c, port.r), state); }
      }
      while (heap.length) {
        const [, state] = pop(), at = state >> 2, way = state & 3, c = at % columns, r = (at - c) / columns;
        if (goals.has(state)) {
          const cells = [];
          let one = state;
          for (; came[one] >= 0; one = came[one]) cells.unshift(one);
          cells.unshift(one);
          const start = began.get(one), end = goals.get(state), points = [{ x: start.px, y: start.py }];
          cells.forEach((each, k) => {
            const spot = each >> 2;
            used[spot] |= (each & 3) < 2 ? 1 : 2;
            if (k && (cells[k - 1] & 3) !== (each & 3)) { used[cells[k - 1] >> 2] |= 3; points.push({ x: x((cells[k - 1] >> 2) % columns), y: y(Math.floor((cells[k - 1] >> 2) / columns)) }); }
          });
          points.push({ x: end.px, y: end.py });
          return points;
        }
        for (let turn = 0; turn < 4; turn++) {
          if (turn === (way ^ 1)) continue;
          const nc = c + MOVES[turn][0], nr = r + MOVES[turn][1], next = nr * columns + nc;
          if (nc < 0 || nr < 0 || nc >= columns || nr >= rows || blocked[next]) continue;
          const same = turn < 2 ? 1 : 2, goal = goals.get(next * 4 + turn);
          const cost = far[state] + 1 + (turn !== way ? TURN : 0) + (used[next] & same ? 6 : 0) + (used[next] & (3 - same) ? 1.5 : 0) + dear[next] * 4 + (goal ? goal.off : 0);
          if (cost < far[next * 4 + turn]) { far[next * 4 + turn] = cost; came[next * 4 + turn] = state; push(cost + guess(nc, nr), next * 4 + turn); }
        }
      }
      return [{ x: from.x + from.w / 2, y: from.y + from.h }, { x: to.x + to.w / 2, y: to.y }];
    };
    const span = edge => Math.abs(box[edge.from].x - box[edge.to].x) + Math.abs(box[edge.from].y - box[edge.to].y);
    const curve = {};
    for (const edge of [...(level.edges || [])].sort((a, b) => span(a) - span(b) || a.id.localeCompare(b.id))) {
      const points = path(box[edge.from], box[edge.to]);
      let d = `M${points[0].x},${points[0].y}`;
      for (let k = 1; k < points.length - 1; k++) {
        const [before, corner, after] = [points[k - 1], points[k], points[k + 1]];
        const round = Math.min(8, Math.hypot(corner.x - before.x, corner.y - before.y) / 2, Math.hypot(after.x - corner.x, after.y - corner.y) / 2);
        const toward = (other) => { const long = Math.hypot(other.x - corner.x, other.y - corner.y) || 1; return { x: corner.x + (other.x - corner.x) / long * round, y: corner.y + (other.y - corner.y) / long * round }; };
        const a = toward(before), b = toward(after);
        d += ` L${a.x},${a.y} Q${corner.x},${corner.y} ${b.x},${b.y}`;
      }
      const last = points[points.length - 1], prior = points[points.length - 2];
      curve[edge.id] = { points, d: d + ` L${last.x},${last.y}`, turn: Math.atan2(last.y - prior.y, last.x - prior.x) * 180 / Math.PI };
    }
    return curve;
  }
  const along = (points, t) => { // the point a share T of the way along a path of straight runs
    const runs = points.slice(1).map((point, i) => Math.hypot(point.x - points[i].x, point.y - points[i].y));
    let left = runs.reduce((sum, run) => sum + run, 0) * t;
    for (let i = 0; i < runs.length; i++) {
      if (left <= runs[i] || i === runs.length - 1) { const share = runs[i] ? left / runs[i] : 0; return { x: points[i].x + (points[i + 1].x - points[i].x) * share, y: points[i].y + (points[i + 1].y - points[i].y) * share }; }
      left -= runs[i];
    }
    return points[0];
  };

  // ---- drawing a level ----
  const OPEN = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 3h6v6"/><path d="M10 14 21 3"/><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/></svg>';
  const lap = (spot, others) => others.reduce((sum, other) => sum + Math.max(0, Math.min(spot.x + spot.w, other.x + other.w) - Math.max(spot.x, other.x)) * Math.max(0, Math.min(spot.y + spot.h, other.y + other.h) - Math.max(spot.y, other.y)), 0);
  const runs = ids => ids.flatMap(id => curves[id].points.slice(1).map((point, k) => { // the straight runs of some edges' lines, as thin boxes
    const start = curves[id].points[k];
    return { x: Math.min(start.x, point.x) - 3, y: Math.min(start.y, point.y) - 3, w: Math.abs(point.x - start.x) + 6, h: Math.abs(point.y - start.y) + 6 };
  }));
  function seat(id, w, h, taken, wires, far) { // the place on an edge's line where its label covers least; `far` also tries places a label or two off the line
    const stage = $("stage");
    let best = null;
    for (let k = 0; k <= 20; k++) {
      const t = .5 + (k % 2 ? 1 : -1) * Math.ceil(k / 2) * .04, on = along(curves[id].points, t), ahead = along(curves[id].points, t + .01);
      const upright = Math.abs(ahead.y - on.y) > Math.abs(ahead.x - on.x);
      for (const side of far ? [0, 1, -1, 2, -2, 3, -3] : [0, 1, -1]) { // on a level run of its line, else on an upright one, else beside the line
        const reach = Math.sign(side) * ((upright ? w / 2 + 6 : h / 2 + 4) + (Math.abs(side) - 1) * ((upright ? w : h) + 8));
        const point = { x: on.x + (upright ? reach : 0), y: on.y + (upright ? 0 : reach) };
        const spot = { x: point.x - w / 2 - 2, y: point.y - h / 2 - 2, w: w + 4, h: h + 4 };
        const outside = spot.x < 0 || spot.y < 0 || spot.x + spot.w > +stage.dataset.w || spot.y + spot.h > +stage.dataset.h, over = lap(spot, taken) + (outside ? w * h : 0), cross = lap(spot, wires), price = (over ? 1e9 + over : 0) + (cross ? 1e5 + cross : 0) + (side ? 2000 * Math.abs(side) : upright ? 1000 : 0) + k;
        if (!best || price < best.price) best = { point, spot, over, cross, price };
      }
    }
    return best;
  }
  function settle(shown, first) { // a label with no free place at rest takes one among the lines and labels now lit
    const taken = [...blocks, ...Object.values(faces).filter(face => !face.text.classList.contains("tucked")).map(face => face.spot)];
    const lines = [...shown].filter(id => curves[id]);
    for (const id of Object.keys(faces).filter(id => faces[id].text.classList.contains("tucked")).sort((a, b) => (b === first) - (a === first))) {
      const face = faces[id], best = shown.has(id) ? seat(id, face.w, face.h, taken, runs(lines.filter(other => other !== id)), id === first) : null, seen = !!best && (!best.over || id === first), point = seen ? best.point : face.point;
      face.text.classList.toggle("shown", seen);
      face.text.style.left = point.x + "px"; face.text.style.top = point.y + "px";
      if (seen) taken.push(best.spot);
    }
  }
  function paint(level) {
    const stage = $("stage"), key = `${level.id} ${innerWidth} ${innerHeight}`; // a level is laid out once per window size, since a scenario comes back to it
    if (!plans[key]) { const plan = arrange(level); plans[key] = { plan, lines: route(level, plan.box, plan.w, plan.h), seats: {} }; }
    const plan = plans[key].plan;
    boxes = plan.box; curves = plans[key].lines;
    stage.replaceChildren();
    stage.style.width = plan.w + "px"; stage.style.height = plan.h + "px";
    stage.dataset.w = plan.w; stage.dataset.h = plan.h;
    stage.classList.toggle("dense", !!plan.fit.dense);
    fit();
    const bands = (level.areas || []).filter(area => (area.tag === "lane" || area.tag === "phase") && boxes[area.id])
      .sort((a, b) => boxes[a.id].y - boxes[b.id].y || boxes[a.id].x - boxes[b.id].x).map(area => area.id); // a level's bands take three tints in turn, so neighbours differ
    for (const area of level.areas || []) {
      const spot = boxes[area.id], band = bands.indexOf(area.id);
      if (spot) stage.append(make("div", { class: "area", "data-id": area.id, "data-tag": area.tag, ...(band < 0 ? {} : { "data-band": band % 3 }), style: `left:${spot.x}px;top:${spot.y}px;width:${spot.w}px;height:${spot.h}px` },
        make("header", {}, area.label, make("small", {}, tagName(area.tag)))));
    }
    const svg = draw("svg", { width: plan.w, height: plan.h });
    stage.append(svg);
    for (const node of level.nodes) {
      const spot = boxes[node.id];
      const card = make("div", { class: "node", "data-id": node.id, "data-tag": node.tag, tabindex: 0, style: `left:${spot.x}px;top:${spot.y}px;width:${spot.w}px;height:${spot.h}px` },
        make("b", {}, node.label), make("small", {}, tagName(node.tag)));
      const region = (level.areas || []).find(area => area.id === node.area && area.tag === "region");
      if (region && region.info && region.info.initial === node.id) card.classList.add("first");
      if (node.opens) {
        const name = `Open ${bare(label(node.opens))}`, open = make("button", { class: "open", type: "button", "aria-label": name, title: name });
        open.innerHTML = OPEN;
        open.addEventListener("click", event => { event.stopPropagation(); go({ level: node.opens, at: null }); });
        card.append(open);
      }
      stage.append(card);
    }
    blocks = level.nodes.map(node => ({ ...boxes[node.id] }));
    for (const header of stage.querySelectorAll(".area > header")) {
      const spot = boxes[header.parentElement.dataset.id];
      blocks.push({ x: spot.x, y: spot.y, w: header.scrollWidth, h: plan.fit.head });
    }
    const taken = [...blocks], frames = (level.areas || []).filter(area => boxes[area.id]).flatMap(area => {
      const frame = boxes[area.id];
      return [{ x: frame.x - 3, y: frame.y - 3, w: frame.w + 6, h: 6 }, { x: frame.x - 3, y: frame.y + frame.h - 3, w: frame.w + 6, h: 6 }, { x: frame.x - 3, y: frame.y - 3, w: 6, h: frame.h + 6 }, { x: frame.x + frame.w - 3, y: frame.y - 3, w: 6, h: frame.h + 6 }];
    });
    faces = {};
    for (const edge of level.edges || []) {
      const group = draw("g", { class: "edge", "data-id": edge.id, "data-tag": edge.tag });
      const tip = curves[edge.id].points[curves[edge.id].points.length - 1];
      group.append(draw("path", { class: "line", d: curves[edge.id].d }), draw("path", { class: "hit", d: curves[edge.id].d }),
        draw("path", { class: "head", d: "M-7,-3.5 L0,0 L-7,3.5 z", transform: `translate(${tip.x},${tip.y}) rotate(${curves[edge.id].turn})` }));
      svg.append(group);
      const text = make("div", { class: "label", "data-edge": edge.id }, ...prose(edge.label, true));
      stage.append(text);
      if (!plans[key].seats[edge.id]) {
        const w = text.offsetWidth, h = text.offsetHeight, best = seat(edge.id, w, h, taken, runs(level.edges.filter(other => other !== edge).map(other => other.id)).concat(frames));
        plans[key].seats[edge.id] = { w, h, point: best.point, spot: best.spot, tucked: !!(best.over || best.cross) };
      }
      const place = plans[key].seats[edge.id];
      if (place.tucked) text.classList.add("tucked"); else taken.push(place.spot);
      faces[edge.id] = { text, w: place.w, h: place.h, point: place.point, spot: place.spot };
      text.style.left = place.point.x + "px"; text.style.top = place.point.y + "px";
    }
    stage.append(make("div", { id: "token" }));
  }
  function fit() {
    const stage = $("stage"), w = +stage.dataset.w, h = +stage.dataset.h;
    const x = scale => ROOM.side + (across() - w * scale) / 2, y = scale => ROOM.top + (down() - h * scale) / 2;
    const scale = Math.min(fill({ w, h }), 1.3);
    stage.style.setProperty("--grow", 1 / Math.max(scale, .85)); // type keeps its size while the boxes around it grow or give a little
    Object.assign(stage.dataset, { x: x(scale), y: y(scale), scale });
    stage.style.transform = `translate(${x(scale)}px, ${y(scale)}px) scale(${scale})`;
  }
  const found = id => document.querySelector(`#stage [data-id="${CSS.escape(id)}"]`);
  const face = id => records[id] && records[id].kind === "edge" ? document.querySelector(`#stage .label[data-edge="${CSS.escape(id)}"]`) : found(id);
  const lies = id => { // where a record's face rests in the window, whatever move is under way
    const stage = $("stage"), text = boxes[id] ? null : face(id), head = records[id] && records[id].kind === "area" && found(id) && found(id).firstChild; // an area's face is its header
    const spot = head ? { x: boxes[id].x, y: boxes[id].y, w: head.offsetWidth, h: head.offsetHeight } : boxes[id] || (text && { x: text.offsetLeft - text.offsetWidth / 2, y: text.offsetTop - text.offsetHeight / 2, w: text.offsetWidth, h: text.offsetHeight });
    if (!spot) return null;
    const scale = +stage.dataset.scale, left = +stage.dataset.x + spot.x * scale, top = +stage.dataset.y + spot.y * scale;
    return { left, top, right: left + spot.w * scale, bottom: top + spot.h * scale, width: spot.w * scale, height: spot.h * scale };
  };
  const line = id => { // points along an edge's line, in the window
    const stage = $("stage"), scale = +stage.dataset.scale;
    return curves[id] ? Array.from({ length: 17 }, (_, k) => along(curves[id].points, k / 16)).map(point => ({ x: +stage.dataset.x + point.x * scale, y: +stage.dataset.y + point.y * scale })) : [];
  };
  const door = (opened, held) => (openers[opened] || []).find(id => levelOf[id] === held); // the node of one level that opens the other

  // ---- one history for every move ----
  const address = state => "#" + ["level", "at", "scenario"].filter(key => state[key]).map(key => key + "=" + encodeURIComponent(state[key])).concat(state.scenario ? ["step=" + state.step] : []).join("&");
  function parse() {
    const state = { level: contract.levels[0].id, at: null, scenario: null, step: 0 };
    for (const part of location.hash.slice(1).split("&")) {
      const [key, value] = part.split("=");
      if (key in state && value) state[key] = key === "step" ? +value : decodeURIComponent(value);
    }
    if (!records[state.level] || records[state.level].kind !== "level") state.level = contract.levels[0].id;
    if (state.at && !records[state.at]) state.at = null;
    if (state.scenario && !(records[state.scenario] && records[state.scenario].kind === "scenario")) state.scenario = null;
    if (!state.scenario || !(state.step >= 0 && state.step <= records[state.scenario].record.steps.length)) state.step = 0; // one past the last step is the scenario's end
    return state;
  }
  function go(change, replace) {
    const next = { ...view, ...change };
    if (!next.scenario) next.step = 0;
    if (address(next) === address(view)) return;
    history[replace ? "replaceState" : "pushState"](next, "", address(next));
    show(next);
  }
  const LEAVE = "cubic-bezier(.4, 0, .6, 1)", ARRIVE = "cubic-bezier(.3, .6, .2, 1)", MOVE = { leave: 280, wait: 220, arrive: 680 }; // the level left is gone before the level entered shows
  let late = 0, leftLevel = null; // how long a scenario's mark waits for its level to arrive, and the level a move is leaving
  const whole = spot => ({ left: spot.x, top: spot.y, width: spot.w * spot.scale, height: spot.h * spot.scale });
  function outline(source, ends, named, timing, quiet) { // the node the level entered grows from, or shrinks back into, framed while the move is under way, its label shown where the frame ends on it
    const frame = rect => ({ left: rect.left + "px", top: rect.top + "px", width: rect.width + "px", height: rect.height + "px" });
    const mark = make("div", { id: "origin", "data-for": source }, ...(named ? [make("span", {}, label(source))] : []));
    document.body.append(mark);
    mark.animate(quiet ? [frame(ends[1]), frame(ends[1])] : ends.map(frame), quiet ? { duration: 1, fill: "both" } : { ...timing, fill: "both" });
    mark.animate([{ opacity: 1 }, { opacity: 1, offset: .8 }, { opacity: 0 }], { duration: quiet ? 600 : MOVE.wait + MOVE.arrive + 200, fill: "both" }).finished.then(() => mark.remove(), () => mark.remove());
  }
  function show(next) {
    Object.assign(view, next);
    const stage = $("stage"), from = shownLevel, idle = () => { document.body.dataset.busy = ""; };
    hovered = null;
    hide();
    if (from !== view.level) {
      const down = from && door(view.level, from), up = from && door(from, view.level);
      const placed = (one = stage) => ({ x: +one.dataset.x, y: +one.dataset.y, scale: +one.dataset.scale, w: +one.dataset.w, h: +one.dataset.h });
      const at = spot => `translate(${spot.x}px, ${spot.y}px) scale(${spot.scale})`;
      const within = (spot, rect) => { // a level drawn inside the node that opens it
        const scale = Math.min(rect.width / spot.w, rect.height / spot.h);
        return at({ x: rect.left + rect.width / 2 - spot.w * scale / 2, y: rect.top + rect.height / 2 - spot.h * scale / 2, scale });
      };
      const about = (spot, rect, by) => { // a level zoomed about that node
        const x = rect.left + rect.width / 2, y = rect.top + rect.height / 2;
        return at({ x: x + (spot.x - x) * by, y: y + (spot.y - y) * by, scale: spot.scale * by });
      };
      const drawn = one => { const style = getComputedStyle(one); return { transform: style.transform, opacity: +style.opacity }; };
      const fading = document.querySelector(".stage.old"), seen = fading && drawn(fading).opacity > drawn(stage).opacity ? fading : stage, held = drawn(seen); // a move turned back mid-way goes on from the level still seen
      const back = seen === fading && leftLevel === view.level, old = from === null || back ? null : seen.cloneNode(true), before = old && placed(seen), entered = down && lies(down), was = back && placed(stage);
      if (seen === stage) leftLevel = from;
      for (const left of document.querySelectorAll(".stage.old, #origin")) left.remove();
      for (const one of stage.getAnimations()) one.cancel();
      shownLevel = view.level;
      paint(records[view.level].record);
      if (old) {
        const after = placed(), left = up && lies(up), middle = { left: innerWidth / 2, top: innerHeight / 2, width: 0, height: 0 }, quiet = still();
        old.removeAttribute("id");
        old.querySelectorAll("[id]").forEach(part => part.removeAttribute("id"));
        old.classList.add("old");
        stage.after(old);
        old.animate(quiet ? [{ opacity: held.opacity }, { opacity: 0 }] : [{ transform: held.transform, opacity: held.opacity }, { transform: entered ? about(before, entered, 2.4) : left ? within(before, left) : about(before, middle, 1.04), opacity: 0 }],
          { duration: quiet ? 180 : MOVE.leave, easing: quiet ? "ease-out" : LEAVE, fill: "forwards" }).finished.then(() => old.remove(), () => old.remove());
        stage.animate(quiet ? [{ opacity: 0 }, { opacity: 1 }] : [{ transform: entered ? within(after, entered) : left ? about(after, left, 2.4) : about(after, middle, .96), opacity: 0 }, { transform: at(after), opacity: 1 }],
          { duration: quiet ? 240 : MOVE.arrive, delay: quiet ? 0 : MOVE.wait, easing: quiet ? "ease-out" : ARRIVE, fill: "backwards" }).finished.then(idle, () => {});
        late = quiet ? 0 : MOVE.wait + 40;
        const source = down || up;
        if (source) outline(source, entered ? [entered, whole(after)] : [whole(before), left], !!entered, entered ? { duration: MOVE.arrive, delay: MOVE.wait, easing: ARRIVE } : { duration: MOVE.leave, easing: LEAVE }, quiet);
      } else if (back) {
        const source = down || up;
        if (source && lies(source)) outline(source, [whole(was), lies(source)], false, { duration: MOVE.arrive, easing: ARRIVE }, still());
        stage.animate(still() ? [{ opacity: held.opacity }, { opacity: 1 }] : [held, { transform: at(placed()), opacity: 1 }], { duration: still() ? 240 : MOVE.arrive, easing: still() ? "ease-out" : ARRIVE })
          .finished.then(idle, () => {});
      }
      document.body.dataset.busy = old || back ? "1" : "";
    }
    Object.assign(document.body.dataset, { level: view.level, step: view.scenario ? view.step : "" });
    crumbs(); mark(); play();
    late = 0;
  }

  function crumbs() {
    const path = [];
    for (let id = view.level, guard = 0; id && guard < 20; guard++) {
      path.unshift(id);
      id = openers[id] ? levelOf[openers[id][0]] : null;
    }
    const bar = $("crumbs");
    bar.replaceChildren();
    path.forEach((id, i) => {
      if (i) bar.append(make("span", { class: "sep" }, "/"));
      const item = make("button", { type: "button", "data-level": id, ...(i === path.length - 1 ? { "aria-current": "page" } : {}) }, ...prose(records[id].record.title, true));
      item.addEventListener("click", () => go({ level: id, at: null, scenario: null }));
      bar.append(item);
    });
  }

  // ---- hover, pin and the overlay ----
  let rest = null, leave = null, hovered = null, apart = Infinity, nearing = false;
  function approach(event) { // a pointer that closes on the open overlay is on its way there, so what it crosses waits
    const box = $("card");
    if (!box.classList.contains("show")) { apart = Infinity; nearing = false; return; }
    const spot = box.getBoundingClientRect();
    const far = Math.hypot(Math.max(spot.left - event.clientX, 0, event.clientX - spot.right), Math.max(spot.top - event.clientY, 0, event.clientY - spot.bottom));
    if (far !== apart) nearing = far < apart; // one move reaches here more than once
    apart = far;
  }
  function near(id) {
    const kind = records[id] && records[id].kind, level = records[view.level].record, set = new Set([id]);
    if (kind === "node") for (const edge of level.edges || []) if (edge.from === id || edge.to === id) [edge.id, edge.from, edge.to].forEach(one => set.add(one));
    if (kind === "edge") [records[id].record.from, records[id].record.to].forEach(one => set.add(one));
    if (kind === "area") for (const node of level.nodes) if (node.area === id) set.add(node.id);
    if (kind === "property") (records[id].record.on || []).forEach(one => set.add(one));
    for (const one of [...set]) if (records[one] && records[one].kind === "node" && records[one].record.area) set.add(records[one].record.area);
    return set;
  }
  const TONES = ["ahead", "past", "next", "step"]; // how far a playing scenario's walk has come at a record, the later name winning
  function mark() {
    const stage = $("stage"), scenario = view.scenario ? records[view.scenario].record : null, step = scenario ? scenario.steps[view.step] : null;
    const focus = hovered || view.at || (step && step.at);
    const lit = !focus ? new Set() : focus === (step && step.at) && records[focus].kind === "node" ? new Set([focus, records[focus].record.area]) : near(focus);
    const tone = {}, held = new Set();
    if (scenario) scenario.steps.forEach((one, i) => {
      const id = levelOf[one.at] === view.level ? one.at : i === view.step + 1 ? door(levelOf[one.at], view.level) : null; // a next step on another level is hinted at the node that opens it
      const is = i < view.step ? "past" : i === view.step ? "step" : i === view.step + 1 ? "next" : "ahead";
      if (id && TONES.indexOf(is) > TONES.indexOf(tone[id])) tone[id] = is;
      if (id && records[id].record.area) held.add(records[id].record.area);
    });
    stage.classList.toggle("playing", !!scenario && !hovered && !view.at);
    for (const element of stage.querySelectorAll("[data-id], .label")) {
      const id = element.dataset.id || element.dataset.edge;
      element.classList.toggle("on", lit.has(id));
      element.classList.toggle("pinned", id === view.at);
      for (const is of TONES) element.classList.toggle(is, tone[id] === is);
      element.classList.toggle("dim", !!(focus || scenario) && !lit.has(id) && !tone[id] && !held.has(id));
    }
    settle(new Set([...lit, ...Object.keys(tone).filter(id => tone[id] === "step" || tone[id] === "next")]), focus);
    if (hovered) card(hovered); else if (view.at) card(view.at); else hide();
  }
  const quoted = text => words(text).split(/(`[^`]+`)/).filter(Boolean).map(part => part[0] === "`" ? make("em", {}, part.slice(1, -1)) : part); // a code span inside code has no code face to take, so it reads as a literal term
  let glossed = new Set(); // the terms the card has marked, each at its first match only
  const spoken = piece => { // a run of prose: a `(guess)` as a badge, and the first match of each term the card has not marked as a term
    const guess = piece.search(/\(guess\)/i);
    let first = null;
    for (const one of terms) if (!glossed.has(one.entry.term)) { const found = one.pattern.exec(piece); if (found && (!first || found.index < first.found.index)) first = { one, found }; }
    if (guess >= 0 && (!first || guess < first.found.index)) return [...spoken(piece.slice(0, guess)), make("span", { class: "badge guess" }, "guess"), ...spoken(piece.slice(guess + 7))];
    if (!first) return piece ? [piece] : [];
    glossed.add(first.one.entry.term);
    const { index } = first.found, text = first.found[0];
    return [...spoken(piece.slice(0, index)), make("dfn", { class: "term", tabindex: "0", "data-term": first.one.entry.term, "data-meaning": first.one.entry.meaning }, text), ...spoken(piece.slice(index + text.length))];
  };
  const literal = quote => { // a fence as a block that keeps its lines, its first line's language word left out; a span as inline code, broken after each slash
    if (quote.startsWith("```")) return make("pre", { class: "fence" }, make("code", {}, quote.slice(3, -3).replace(/^[\w+-]*\n/, "").replace(/\n$/, "")));
    return make("code", {}, ...quote.slice(1, -1).split(/(?<=\/)/).flatMap((piece, i) => i ? [make("wbr"), piece] : [piece]));
  };
  const formula = (tex, display) => { // the MathML make-page.py drew, or the TeX as code where it drew none
    const markup = FORMULAS[(display ? "$$" : "$") + tex];
    if (!markup) return make("code", {}, tex);
    const holder = document.createElement("template");
    holder.innerHTML = markup;
    return holder.content.firstChild;
  };
  const prose = (text, plain = false) => { // a text with its quotes, formulas, named records, terms and guesses drawn; PLAIN, for a text outside a card's rows, draws names as words and marks no term or guess
    const all = String(text), out = [];
    let last = 0;
    for (const found of all.matchAll(MARKS)) {
      const [whole, quote, block, inline, id] = found;
      if (id && !records[id]) continue;
      out.push(...(plain ? [all.slice(last, found.index)].filter(Boolean) : spoken(all.slice(last, found.index))));
      last = found.index + whole.length;
      if (quote) out.push(literal(quote));
      else if (id && plain) out.push(label(id));
      else if (id) out.push(make("span", { class: "ref", "data-ref": id }, label(id)));
      else out.push(formula(block || inline, !!block));
    }
    return out.concat(plain ? [all.slice(last)].filter(Boolean) : spoken(all.slice(last)));
  };
  const value = (form, data) => {
    if (form === "list" && Array.isArray(data)) return [make("ul", {}, ...data.map(item => make("li", {}, ...prose(item))))];
    if (form === "table" && data && data.columns) {
      const table = make("table", {}, make("thead", {}, make("tr", {}, ...data.columns.map(name => make("th", {}, name)))));
      table.append(make("tbody", {}, ...data.rows.map(row => make("tr", {}, ...row.map(cell => make("td", {}, ...prose(cell)))))));
      return [table];
    }
    if (form === "tree" && Array.isArray(data)) {
      const branch = list => make("ul", {}, ...list.map(item => make("li", {}, make("code", {}, ...quoted(item.name)), ...(item.note ? [" ", ...prose(item.note)] : []), ...(item.children ? [branch(item.children)] : []))));
      return [branch(data)];
    }
    if (form === "code") return [make("pre", {}, make("code", {}, ...quoted(data)))];
    return [make("span", {}, ...prose(typeof data === "string" ? data : JSON.stringify(data)))];
  };
  function rows(id) {
    const { kind, record } = records[id], list = [], add = (name, form, data) => data !== undefined && data !== null && data !== "" && list.push([name, form, data]);
    if (kind === "edge") add(record.tag === "transition" ? "transition" : "sentence", "text", record.tag === "transition" ? `{${record.from}} → {${record.to}} on ${record.label}` : `{${record.from}} ${record.label} {${record.to}}.`);
    if (kind === "property") { add("statement", "text", record.statement); add("on", "list", (record.on || []).map(one => `{${one}}`)); add("fault", "text", record.fault); }
    if (kind === "scenario") add("steps", "list", record.steps.map(step => `{${step.at}}` + (step.note ? " · " + step.note : "")));
    add("purpose", "text", record.purpose);
    const items = TAGS[kind] && TAGS[kind][record.tag] ? TAGS[kind][record.tag].items.concat(TAGS.common[kind] || []) : [];
    for (const [name, data] of Object.entries(record.info || {})) {
      const item = items.find(one => one.name === name);
      add(item ? item.label : name, item ? item.form : Array.isArray(data) ? "list" : "text", name === "initial" ? `{${data}}` : data);
    }
    if (record.opens) add("opens", "text", `{${record.opens}}`);
    if (record.evidence) add("evidence", "list", record.evidence.map(entry => {
      const [source, line] = entry.split(":"), known = (contract.sources || []).find(one => one.id === source);
      return (known ? known.path : source) + (line ? ":" + line : "");
    }));
    return list;
  }
  function beside(id, w, h, apart = .6, open = false) { // the spot nearest a record that covers neither it nor what the reader follows from it; `apart` is what covering another node costs, and an OPEN spot also leaves every lane header and shown edge label readable
    const spot = lies(id), tied = near(id), dear = [];
    if (!spot) return { left: innerWidth / 2 - w / 2, top: 68 };
    const keep = (rect, by, weight) => dear.push({ left: rect.left - by, top: rect.top - by, right: rect.right + by, bottom: rect.bottom + by, weight });
    const points = (one, weight) => line(one).forEach(point => keep({ left: point.x, top: point.y, right: point.x, bottom: point.y }, 6, weight));
    keep(spot, 8, 400);
    points(id, 400);
    for (const one of tied) if (one !== id && records[one] && records[one].kind !== "area") { if (lies(one)) keep(lies(one), 4, records[one].kind === "node" ? 400 : 40); points(one, 12); }
    for (const node of records[view.level].record.nodes) if (!tied.has(node.id)) keep(lies(node.id), 0, apart);
    for (const [one, face] of Object.entries(faces)) if ((open || one !== id) && (!face.text.classList.contains("tucked") || face.text.classList.contains("shown"))) keep(lies(one), 2, open ? 400 : tied.has(one) || face.text.matches(".past, .next") ? 40 : 4);
    if (open) for (const area of records[view.level].record.areas || []) if (lies(area.id)) keep(lies(area.id), 2, 400);
    for (const bar of [$("tools"), $("crumbs"), $("play")]) if (bar.id !== "play" || bar.classList.contains("show")) keep(bar.getBoundingClientRect(), 8, 400);
    const covers = (x, y, least) => dear.reduce((sum, held) => held.weight < least ? sum : sum + held.weight * Math.max(0, Math.min(x + w, held.right) - Math.max(x, held.left)) * Math.max(0, Math.min(y + h, held.bottom) - Math.max(y, held.top)), 0);
    const price = (x, y) => { // a spot twice as far costs four times as much, so a far clear spot loses to a near one that covers a little
      const far = Math.hypot(Math.max(spot.left - x - w, x - spot.right, 0), Math.max(spot.top - y - h, y - spot.bottom, 0));
      return covers(x, y, 0) + 20 * far + far * far / 4;
    };
    let best = null;
    const weigh = (x, y) => { // a spot clear of what is tied beats any that covers it, however near
      const left = Math.min(Math.max(8, x), innerWidth - w - 8), top = Math.min(Math.max(8, y), innerHeight - h - 8), cost = price(left, top), tied = covers(left, top, 400);
      if (!best || (tied > 0) < (best.tied > 0) || (tied > 0) === (best.tied > 0) && cost < best.cost) best = { left, top, cost, tied };
    };
    for (let k = 0; k <= 8; k++) {
      for (const x of [spot.right + 12, spot.left - 12 - w]) weigh(x, spot.top - h + (h + spot.height) * k / 8);
      for (const y of [spot.bottom + 12, spot.top - 12 - h]) weigh(spot.left - w + (w + spot.width) * k / 8, y);
    }
    for (let x = 8; x <= innerWidth - w - 8; x += 40) for (let y = 8; y <= innerHeight - h - 8; y += 40) weigh(x, y);
    if (best.tied) { // a gap the grid steps over may still hold the card clear, so the spots flush with each edge of what it must not cover are tried
      const walls = dear.filter(held => held.weight >= 400), xs = [8, ...walls.flatMap(held => [held.right, held.left - w])], ys = [8, ...walls.flatMap(held => [held.bottom, held.top - h])];
      for (const x of xs) for (const y of ys) weigh(x, y);
    }
    const rough = best;
    for (let x = -32; x <= 32; x += 8) for (let y = -32; y <= 32; y += 8) weigh(rough.left + x, rough.top + y); // the spots between those tried
    return best; // `tied` is what the spot still covers of the record and of what is tied to it
  }
  let leaf = 0; // the page of rows the card shows
  function card(id) { // one card for a record, the same under the pointer and kept, its rows over pages its height holds
    const { kind, record } = records[id], box = $("card"), kept = view.at === id, all = rows(id);
    if (box.dataset.for !== id) leaf = 0;
    const tags = make("div", {}, make("span", { class: "tag fill" }, tagName(record.tag || record.kind || kind)));
    for (const extra of [record.basis, record.strength, record.many ? "many" : ""]) if (extra) tags.append(make("span", { class: "tag" }, extra));
    if (record.status && record.status !== "holds") tags.append(make("span", { class: `tag badge ${record.status}` }, record.status)); // a settled statement needs no mark
    if (record.evidence) tags.append(make("button", { class: "tag cite", type: "button", "aria-label": "Sources" }, `${record.evidence.length} ${record.evidence.length === 1 ? "source" : "sources"}`));
    const list = make("dl"), foot = make("footer", {}, make("kbd", {}, "esc"));
    box.replaceChildren(make("h2", {}, ...prose(record.label || record.title || record.id, true)), tags, list, foot);
    box.dataset.for = id;
    box.classList.toggle("kept", kept);
    const limit = Math.floor(Math.min(innerHeight * .46, 400));
    const lay = (from, most, cap) => { // the rows from FROM on that CAP pixels of the card hold, MOST at most, and the row after them
      box.classList.remove("long");
      box.style.maxHeight = "none";
      list.replaceChildren();
      glossed = new Set();
      let to = from;
      for (; to < all.length && to - from < most; to++) {
        const [name, form, data] = all[to];
        list.append(make("div", { "data-form": form }, make("dt", {}, name), make("dd", {}, ...value(form, data))));
        if (to > from && box.offsetHeight > cap) { list.lastChild.remove(); break; }
      }
      return to;
    };
    const hint = (key, text) => make("span", {}, make("kbd", {}, key), text);
    const fill = (most, page) => { // the card with MOST rows a page at most on its PAGE-th page, placed by its first page, its later pages growing up from the same foot, a row taller than the room above scrolling under its fixed foot
      const sign = (from, to, paged, next) => {
        const turn = make("button", { class: "turn", type: "button", "aria-label": "More rows" }, `${from + 1}–${to} of ${all.length} ›`);
        turn.addEventListener("click", () => { leaf = next; card(id); });
        foot.replaceChildren(...(paged ? [turn] : []), make("span", { class: "hints" }, kept ? hint("esc", "close") : hint("click", "keep"), ...(record.opens ? [hint("double-click", "open")] : [])));
      };
      const firstEnd = lay(0, most, limit);
      sign(0, firstEnd, firstEnd < all.length, 0);
      const first = Math.min(box.offsetHeight, limit), place = beside(id, box.offsetWidth, first), bottom = place.top + first, cap = Math.min(limit, bottom - 8);
      const starts = [0];
      for (let to = firstEnd; to < all.length; to = lay(to, most, cap)) starts.push(to);
      const shown = Math.min(page, starts.length - 1);
      sign(starts[shown], lay(starts[shown], most, shown ? cap : limit), starts.length > 1, (shown + 1) % starts.length);
      const height = shown ? cap : limit;
      box.style.maxHeight = height + "px";
      box.classList.toggle("long", box.scrollHeight > height + 1);
      return { ...place, bottom, most, page: shown };
    };
    let at = fill(Infinity, 0);
    for (let most = list.children.length - 1, tried = at; tried.tied && most >= 1; most--) { // a card no place holds clear of what is tied sheds rows a page until one does
      tried = fill(most, 0);
      if ((tried.tied > 0) < (at.tied > 0) || (tried.tied > 0) === (at.tied > 0) && tried.cost < at.cost) at = tried;
    }
    at = fill(at.most, leaf);
    leaf = at.page;
    box.style.left = at.left + "px";
    box.style.top = "auto";
    box.style.bottom = innerHeight - at.bottom + "px"; // the foot, and the button that turns the pages, stay put as the pages turn
    box.classList.add("show");
  }
  const toward = id => { // ID when the shown level holds it, else the node of the shown level that opens the levels down to ID's level, or nothing
    if (!records[id] || !["node", "edge", "area", "level"].includes(records[id].kind)) return null;
    let one = id;
    for (let level = home(id), seen = new Set(); level !== view.level; seen.add(level), level = levelOf[one]) {
      one = (openers[level] || [])[0];
      if (!one || seen.has(level)) return null;
    }
    return one;
  };
  function light(id) { // the record a chip in the card names, marked in the diagram
    const stage = $("stage"), one = id && toward(id);
    stage.querySelectorAll(".named").forEach(element => element.classList.remove("named"));
    if (one) stage.querySelectorAll(`[data-id="${one}"], .label[data-edge="${one}"]`).forEach(element => element.classList.add("named"));
  }
  function gloss(anchor, ...children) { // a note over the card, above what it explains or else below it
    const box = $("gloss"), at = anchor.getBoundingClientRect();
    box.replaceChildren(...children);
    box.classList.add("show");
    const w = box.offsetWidth, h = box.offsetHeight;
    box.style.left = Math.min(Math.max(8, at.left), innerWidth - w - 8) + "px";
    box.style.top = (at.top - h - 6 >= 8 ? at.top - h - 6 : Math.min(at.bottom + 6, innerHeight - h - 8)) + "px";
  }
  const unGloss = () => { $("gloss").classList.remove("show"); $("gloss").replaceChildren(); };
  const sources = record => record.evidence.map(entry => { // each source a record cites, by its path and the line cited, with what it says
    const [source, line] = entry.split(":"), known = (contract.sources || []).find(one => one.id === source);
    return make("div", { class: "source" }, make("code", {}, (known ? known.path : source) + (line ? ":" + line : "")), ...(known && known.says ? [make("blockquote", {}, words(known.says))] : []));
  });
  const halt = () => { clearTimeout(rest); clearTimeout(leave); };
  function hide() {
    halt();
    unGloss();
    light(null);
    $("card").classList.remove("show"); $("card").dataset.for = "";
  }
  function hover(id) {
    halt();
    if (hovered === id) return;
    const rested = () => { // no card rises over a level still on its way
      if (document.body.dataset.busy) rest = setTimeout(rested, 80);
      else { hovered = id; mark(); }
    };
    rest = setTimeout(rested, hovered ? (nearing ? 420 : 60) : 140);
  }
  function unhover() {
    halt();
    leave = setTimeout(() => { hovered = null; mark(); }, nearing ? 420 : 220);
  }
  const hit = target => {
    const element = target.closest && target.closest("#stage .node, #stage .edge, #stage .label, #stage .area > header");
    return element ? element.dataset.id || element.dataset.edge || element.parentElement.dataset.id : null;
  };

  // ---- scenario play ----
  let auto = false, timer = null; // a scenario that plays by itself, and its next step
  function transport() {
    const bar = $("play"), scenario = records[view.scenario].record, steps = scenario.steps, ended = view.step === steps.length;
    bar.querySelector(".count").textContent = ended ? "Done" : `${view.step + 1}/${steps.length}`;
    bar.querySelector(".title").replaceChildren(...prose(scenario.title, true));
    const dots = bar.querySelector(".dots");
    if (dots.dataset.for !== view.scenario) dots.replaceChildren(...steps.map((one, i) => { // kept while the scenario plays, so a pressed one keeps the focus
      const dot = make("button", { type: "button", "aria-label": `Step ${i + 1}`, title: bare(label(one.at)) });
      dot.addEventListener("click", () => go({ step: i, level: home(one.at), at: null }));
      return dot;
    }));
    dots.dataset.for = view.scenario;
    [...dots.children].forEach((dot, i) => { dot.className = i < view.step ? "done" : i === view.step ? "now" : ""; });
    $("run").setAttribute("aria-label", auto ? "Pause" : "Play");
    $("run").dataset.on = auto ? "1" : "";
    $("run").hidden = ended;
    $("prev").disabled = view.step === 0;
    $("next").disabled = ended;
    $("again").hidden = !ended;
    $("onward").hidden = !ended || contract.scenarios.length < 2;
    const next = steps[view.step + 1], away = next && home(next.at) !== view.level ? home(next.at) : null;
    $("onto").hidden = !away;
    $("onto").textContent = away ? `Next: ${bare(records[away].record.title)}` : "";
    bar.classList.add("show");
  }
  function play() {
    const chip = $("chip"), token = $("token");
    clearTimeout(timer);
    chip.classList.remove("show");
    if (!view.scenario) { auto = false; $("play").classList.remove("show"); if (token) { token.classList.remove("run", "carry"); token.dataset.at = ""; } return; }
    const step = records[view.scenario].record.steps[view.step];
    if (!step) auto = false;
    transport();
    if (!step) return;
    if (step.note) {
      chip.replaceChildren(...prose(step.note, true));
      chip.style.left = chip.style.top = "0px"; // measured where the window's edge cuts no line short
      const at = beside(step.at, chip.offsetWidth, chip.offsetHeight, 12, true); // a note is small enough to keep off every node
      chip.style.left = at.left + "px";
      chip.style.top = at.top + "px";
      chip.classList.add("show");
    }
    if (auto) timer = setTimeout(() => stride(1), 1300 + late + (step.note || "").length * 20);
    if (!token) return;
    token.classList.remove("run", "carry");
    const from = token.dataset.at ? token.dataset.at.split(",").map(Number) : null;
    let way = null, end = null;
    if (curves[step.at]) {
      const points = curves[step.at].points;
      way = (from && Math.hypot(from[0] - points[0].x, from[1] - points[0].y) > 2 ? `M${from[0]},${from[1]} L` : "M") + curves[step.at].d.slice(1);
      end = points[points.length - 1];
    } else if (boxes[step.at]) {
      end = { x: boxes[step.at].x + boxes[step.at].w / 2, y: boxes[step.at].y };
      way = `M${from ? from[0] : end.x},${from ? from[1] : end.y - 28} L${end.x},${end.y}`;
    }
    if (!way) { token.dataset.at = ""; return; }
    token.style.offsetPath = `path("${way}")`;
    token.style.animationDelay = late + "ms";
    token.dataset.at = `${end.x},${end.y}`;
    token.getBoundingClientRect();
    token.classList.add("run"); token.classList.toggle("carry", !!from);
  }
  function stride(by) {
    if (!view.scenario) return;
    const steps = records[view.scenario].record.steps, step = view.step + by;
    if (step >= 0 && step <= steps.length) go({ step, at: null, ...(steps[step] ? { level: home(steps[step].at) } : {}) });
  }
  const start = id => go({ scenario: id, step: 0, level: home(id), at: null });
  function run() { // the walk starts at once and stops where it stands
    if (!view.scenario) return;
    auto = !auto;
    if (!auto) { clearTimeout(timer); return transport(); }
    if (view.step === records[view.scenario].record.steps.length) start(view.scenario); else stride(1);
  }

  // ---- search ----
  const LEAD = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ", VOWEL = ["ㅏ", "ㅐ", "ㅑ", "ㅒ", "ㅓ", "ㅔ", "ㅕ", "ㅖ", "ㅗ", "ㅗㅏ", "ㅗㅐ", "ㅗㅣ", "ㅛ", "ㅜ", "ㅜㅓ", "ㅜㅔ", "ㅜㅣ", "ㅠ", "ㅡ", "ㅡㅣ", "ㅣ"];
  const TAIL = ["", "ㄱ", "ㄲ", "ㄱㅅ", "ㄴ", "ㄴㅈ", "ㄴㅎ", "ㄷ", "ㄹ", "ㄹㄱ", "ㄹㅁ", "ㄹㅂ", "ㄹㅅ", "ㄹㅌ", "ㄹㅍ", "ㄹㅎ", "ㅁ", "ㅂ", "ㅂㅅ", "ㅅ", "ㅆ", "ㅇ", "ㅈ", "ㅊ", "ㅋ", "ㅌ", "ㅍ", "ㅎ"];
  const PAIRS = { "ㄳ": "ㄱㅅ", "ㄵ": "ㄴㅈ", "ㄶ": "ㄴㅎ", "ㄺ": "ㄹㄱ", "ㄻ": "ㄹㅁ", "ㄼ": "ㄹㅂ", "ㄽ": "ㄹㅅ", "ㄾ": "ㄹㅌ", "ㄿ": "ㄹㅍ", "ㅀ": "ㄹㅎ", "ㅄ": "ㅂㅅ", "ㅘ": "ㅗㅏ", "ㅙ": "ㅗㅐ", "ㅚ": "ㅗㅣ", "ㅝ": "ㅜㅓ", "ㅞ": "ㅜㅔ", "ㅟ": "ㅜㅣ", "ㅢ": "ㅡㅣ" };
  const KEYS = { "ㅂ": "q", "ㅈ": "w", "ㄷ": "e", "ㄱ": "r", "ㅅ": "t", "ㅛ": "y", "ㅕ": "u", "ㅑ": "i", "ㅐ": "o", "ㅔ": "p", "ㅁ": "a", "ㄴ": "s", "ㅇ": "d", "ㄹ": "f", "ㅎ": "g", "ㅗ": "h", "ㅓ": "j", "ㅏ": "k", "ㅣ": "l", "ㅋ": "z", "ㅌ": "x", "ㅊ": "c", "ㅍ": "v", "ㅠ": "b", "ㅜ": "n", "ㅡ": "m", "ㅃ": "q", "ㅉ": "w", "ㄸ": "e", "ㄲ": "r", "ㅆ": "t", "ㅒ": "o", "ㅖ": "p" };
  const typed = text => [...text].map(letter => { // the Latin keys pressed when a Korean two-set layout was left on
    const code = letter.charCodeAt(0) - 0xac00;
    const parts = code >= 0 && code < 11172 ? LEAD[Math.floor(code / 588)] + VOWEL[Math.floor(code % 588 / 28)] + TAIL[code % 28] : PAIRS[letter] || letter;
    return [...parts].map(part => KEYS[part] || part).join("");
  }).join("");
  const plain = text => String(text).toLowerCase().replace(/[^a-z0-9ㄱ-ㆎ가-힣]+/g, " ").trim();
  const flat = value => typeof value === "string" ? words(value).replace(/`/g, "") : Array.isArray(value) ? value.map(flat).join("; ")
    : value && typeof value === "object" ? Object.entries(value).map(([key, item]) => `${key}: ${flat(item)}`).join("; ") : String(value);
  function index() { // each record's fields as the search weighs them, and its texts as a hit shows them, by name
    const list = [], add = (id, kind, name, note, fields, shown) => list.push({ id, kind, name: name.replace(/`/g, ""), note, fields: fields.filter(([text]) => text).map(([text, place]) => ({ text: plain(text), tokens: plain(text).split(" "), place })),
      shown: shown.filter(([, text]) => text).map(([field, text]) => ({ field, text: flat(text) })) });
    const texts = info => words(JSON.stringify(info || {})).replace(/["{}\[\],:]+/g, " ");
    const details = info => Object.entries(info || {});
    const aliased = record => (record.aliases || []).map(alias => [alias, 0]), said = record => (record.aliases || []).map(alias => ["matched alias:", alias]); // an alias weighs as the record's name
    for (const level of contract.levels) {
      add(level.id, "level", words(level.title), "level", [[words(level.title), 0], [level.id, 1], [level.about && words(level.about), 3]], [["id", level.id], ["about", level.about]]);
      for (const node of level.nodes) add(node.id, "node", node.label, tagName(node.tag), [[node.label, 0], ...aliased(node), [node.id, 1], [node.tag, 2], [node.purpose && words(node.purpose), 3], [texts(node.info), 4]], [...said(node), ["id", node.id], ["tag", tagName(node.tag)], ["purpose", node.purpose], ...details(node.info)]);
      for (const area of level.areas || []) add(area.id, "area", area.label, tagName(area.tag), [[area.label, 0], ...aliased(area), [area.id, 1], [area.tag, 2], [texts(area.info), 4]], [...said(area), ["id", area.id], ["tag", tagName(area.tag)], ...details(area.info)]);
      for (const edge of level.edges || []) add(edge.id, "edge", sentence(edge), tagName(edge.tag), [[words(edge.label), 0], [edge.id, 1], [edge.tag, 2], [sentence(edge), 3], [texts(edge.info), 4]], [["id", edge.id], ["tag", tagName(edge.tag)], ...details(edge.info)]);
    }
    for (const scenario of contract.scenarios || []) add(scenario.id, "scenario", words(scenario.title), `${scenario.steps.length} steps`, [[words(scenario.title), 0], [scenario.id, 1], [scenario.purpose && words(scenario.purpose), 3]], [["id", scenario.id], ["purpose", scenario.purpose]]);
    for (const property of contract.properties || []) add(property.id, "property", property.title, property.kind, [[property.title, 0], [property.id, 1], [property.kind, 2], [words(property.statement), 3]], [["id", property.id], ["kind", property.kind], ["statement", property.statement]]);
    for (const question of contract.questions || []) add(question.id, "question", words(question.asks), question.answers ? "question" : "open question", [[words(question.asks), 0], [question.id, 1]], [["id", question.id]]);
    for (const entry of list) entry.terms = entry.fields.flatMap(field => field.tokens).map(stem);
    lengths = list.reduce((sum, entry) => sum + entry.terms.length, 0) / Math.max(1, list.length);
    return list;
  }
  const slips = (a, b, most) => { // edits between two words, a swap of neighbours counted once
    if (Math.abs(a.length - b.length) > most) return most + 1;
    let last = null, row = Array.from({ length: b.length + 1 }, (_, i) => i);
    for (let i = 1; i <= a.length; i++) {
      const next = [i];
      for (let j = 1; j <= b.length; j++) {
        next[j] = Math.min(row[j] + 1, next[j - 1] + 1, row[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
        if (last && j > 1 && a[i - 1] === b[j - 2] && a[i - 2] === b[j - 1]) next[j] = Math.min(next[j], last[j - 2] + 1);
      }
      last = row; row = next;
    }
    return row[b.length];
  };
  const KINDS = { node: "Nodes", level: "Levels", area: "Areas", edge: "Edges", scenario: "Scenarios", property: "Properties", question: "Questions" };
  const ORDER = Object.keys(KINDS);
  function match(token, field) { // how well TOKEN matches FIELD, best first: the whole field, a word, a word's start, the words' initials, inside a word, one slip, two slips; -1 for none
    if (field.text === token) return 0;
    if (field.tokens.includes(token)) return 1;
    if (field.text.startsWith(token) || field.tokens.some(word => word.startsWith(token))) return 2;
    if (token.length > 1 && field.tokens.length >= token.length && field.tokens.map(word => word[0]).join("").startsWith(token)) return 3;
    if (token.length > 2 && field.text.includes(token)) return 4;
    const most = token.length >= 8 ? 2 : token.length >= 4 ? 1 : 0;
    let least = most + 1;
    for (const word of most ? field.tokens : []) {
      const key = token + " " + word;
      if (!slipping.has(key)) slipping.set(key, slips(token, word.length > token.length + most ? word.slice(0, token.length) : word, most));
      least = Math.min(least, slipping.get(key));
      if (least === 1) break;
    }
    return least <= most ? 4 + least : -1;
  }
  const slipping = new Map(); // a query word's slips from a record's word, kept while one query ranks, since the same words recur across records
  const termed = query => (contract.terms || []).flatMap(term => (term.aliases || []).filter(alias => ` ${query} `.includes(` ${plain(alias)} `)).map(alias => [alias, term.term])); // the term aliases a query holds whole, each with its term
  const forms = query => { // a query read as typed and as the keys of a Korean layout, then each with its term aliases read as their terms
    const read = [plain(query), plain(typed(query))];
    return read.concat(read.filter(form => termed(form).length).map(form => termed(form).reduce((done, [alias, term]) => ` ${done} `.replace(` ${plain(alias)} `, ` ${plain(term)} `).trim(), form)));
  };
  const stem = word => word.length > 4 ? word.replace(/(ies|es|ed|ing|s|e)$/, "") : word;
  const RANKERS = { field: 6, quality: 3, bm25: .25, coverage: 1 }; // each ranker's weight in the fused rank, tuned by the mean reciprocal rank over fixtures/ranking-queries.json
  function measure(entry, tokens, rare, partial) { // what each ranker reads of one record for one query, each the less the better; none for a record missing a word unless PARTIAL
    let field = 0, quality = 0, covered = 0;
    for (const token of tokens) { // the token's match in the first field it matches, the field ranked before the match
      let place = 5, grade = 7, size = 0;
      for (const one of entry.fields) { const got = match(token, one); if (got >= 0 && (one.place < place || one.place === place && got < grade)) { place = one.place; grade = got; size = one.text.length; } }
      if (grade === 7 && !partial) return null;
      covered += grade < 7 ? 1 : 0; field += place; quality += grade < 7 ? grade + 1 - token.length / Math.max(size, token.length) : grade; // within a grade, the more of the text the word covers the better
    }
    field /= tokens.length; quality /= tokens.length;
    if (tokens.length > 1) for (const one of entry.fields) { const got = match(tokens.join(" "), one); if (got >= 0) { field = Math.min(field, one.place); quality = Math.min(quality, got); } }
    let bm25 = 0;
    for (const [term, weight] of rare) { // BM25, k1 1.2 and b 0.75, over every text of the record
      const count = entry.terms.filter(word => word === term).length;
      bm25 += weight * count * 2.2 / (count + 1.2 * (.25 + .75 * entry.terms.length / lengths));
    }
    return { entry, covered, field, quality, bm25: -bm25, coverage: -covered / tokens.length };
  }
  let lengths = 1;
  function rank(query) { // the records a query finds, by reciprocal rank fusion of its rankers, k = 60
    const scored = new Map();
    slipping.clear();
    for (const form of new Set(forms(query))) {
      const tokens = form.split(" ").filter(Boolean);
      if (!tokens.length) continue;
      const rare = [...new Set(tokens.map(stem))].map(term => { const held = entries.filter(entry => entry.terms.includes(term)).length; return [term, Math.log(1 + (entries.length - held + .5) / (held + .5))]; });
      const pool = tokens.length < 3 ? entries.map(entry => measure(entry, tokens, rare, false)).filter(Boolean) // a sentence a person types seldom matches a record in every word, so the share of words ranks it
        : entries.map(entry => measure(entry, tokens, rare, true)).filter(row => row.covered || row.bm25 < 0);
      const score = new Map(pool.map(row => [row.entry, 0]));
      for (const [ranker, weight] of Object.entries(RANKERS)) { // a record's rank is one more than the records ahead of it, ties sharing one
        const sorted = pool.map(row => row[ranker]).sort((a, b) => a - b);
        for (const row of pool) { let ahead = 0, past = sorted.length; while (ahead < past) { const middle = (ahead + past) >> 1; if (sorted[middle] < row[ranker]) ahead = middle + 1; else past = middle; } score.set(row.entry, score.get(row.entry) + weight / (60 + 1 + ahead)); }
      }
      for (const [entry, value] of score) if (value > (scored.get(entry) || 0)) scored.set(entry, value);
    }
    return [...scored].sort((a, b) => b[1] - a[1] || ORDER.indexOf(a[0].kind) - ORDER.indexOf(b[0].kind) || a[0].name.length - b[0].name.length || a[0].id.localeCompare(b[0].id)).map(([entry]) => entry);
  }
  const folds = new Map();
  const fold = text => { // TEXT as `plain` reads it, with the place in TEXT of each letter kept
    if (folds.has(text)) return folds.get(text);
    let folded = "", at = [], gap = false;
    for (let i = 0; i < text.length; i++) {
      const letter = text[i].toLowerCase();
      if (letter.length !== 1 || !/[a-z0-9ㄱ-ㆎ가-힣]/.test(letter)) { gap = true; continue; }
      if (gap && folded) { folded += " "; at.push(i); }
      folded += letter; at.push(i); gap = false;
    }
    folds.set(text, { folded, at });
    return folds.get(text);
  };
  function spans(text, tokens) { // the letters of TEXT each query word matched, by the first way `match` would take
    const { folded, at } = fold(text), found = [], starts = [];
    for (const word of folded.matchAll(/\S+/g)) starts.push([word.index, word.index + word[0].length]);
    const mark = (start, end) => found.push([at[start], at[end - 1] + 1]);
    for (const token of tokens) {
      const heads = starts.filter(([start]) => folded.startsWith(token, start));
      if (heads.length) { heads.forEach(([start]) => mark(start, start + token.length)); continue; }
      if (token.length > 1 && starts.length >= token.length && starts.slice(0, token.length).every(([start], i) => folded[start] === token[i])) { starts.slice(0, token.length).forEach(([start]) => mark(start, start + 1)); continue; }
      const kin = starts.filter(([start, end]) => stem(folded.slice(start, end)) === stem(token));
      if (kin.length) { kin.forEach(([start, end]) => mark(start, end)); continue; }
      if (token.length > 2 && folded.includes(token)) { for (let i = folded.indexOf(token); i >= 0; i = folded.indexOf(token, i + token.length)) mark(i, i + token.length); continue; }
      const most = token.length >= 8 ? 2 : token.length >= 4 ? 1 : 0;
      for (const [start, end] of most ? starts : []) {
        const word = folded.slice(start, end), cut = word.length > token.length + most ? token.length : word.length;
        if (slips(token, word.slice(0, cut), most) <= most) mark(start, start + cut);
      }
    }
    return found;
  }
  const matches = (text, pattern) => [...text.matchAll(pattern)].filter(one => one[0]).slice(0, 50).map(one => [one.index, one.index + one[0].length]);
  const marked = (text, found) => { // TEXT with each found span in a mark
    const parts = [];
    let done = 0;
    for (const [start, end] of [...found].sort((a, b) => a[0] - b[0])) {
      if (end <= done) continue;
      const from = Math.max(start, done);
      parts.push(text.slice(done, from), make("mark", {}, text.slice(from, end)));
      done = end;
    }
    return parts.concat(text.slice(done));
  };
  function excerpt(text, found) { // about twelve words of TEXT around its first match, cut ends shown by an ellipsis
    const all = [...text.matchAll(/\S+/g)], first = Math.min(...found.map(span => span[0]));
    let from = Math.max(0, all.findIndex(word => word.index + word[0].length > first) - 4);
    const to = Math.min(all.length, from + 12);
    from = Math.max(0, to - 12);
    const start = all[from].index, end = all[to - 1].index + all[to - 1][0].length;
    const shifted = found.filter(([a, b]) => b > start && a < end).map(([a, b]) => [Math.max(a, start) - start, Math.min(b, end) - start]);
    return [...(from ? ["… "] : []), ...marked(text.slice(start, end), shifted), ...(to < all.length ? [" …"] : [])];
  }
  function sought() { // the pattern the box holds in the regular expression mode, or the reason it is none
    try { return { pattern: new RegExp($("query").value, "gi") }; } catch (error) { return { error: error.message.replace(/^.*: /, "") }; }
  }
  function grep(pattern) { // the records whose name or other texts the pattern matches, the name counting most
    const found = [];
    for (const entry of entries) {
      const named = matches(entry.name, pattern).length > 0;
      if (named || entry.shown.some(part => matches(part.text, pattern).length)) found.push([entry, named ? 2 : 1]);
    }
    return found.sort((a, b) => b[1] - a[1] || ORDER.indexOf(a[0].kind) - ORDER.indexOf(b[0].kind) || a[0].name.length - b[0].name.length || a[0].id.localeCompare(b[0].id)).map(([entry]) => entry);
  }
  let chosen = 0, listed = [], scope = null, regular = false, memory = null;
  const shelf = () => `paperwork-system-recent ${contract.title} ${location.pathname}`; // every file:// page shares one storage
  const recalled = () => { // the last queries a pick was made from, the tab's own once the storage throws
    if (!memory) try { return JSON.parse(localStorage.getItem(shelf()) || "[]"); } catch { memory = []; }
    return memory;
  };
  const remember = queries => {
    if (!memory) try { return localStorage.setItem(shelf(), JSON.stringify(queries)); } catch { memory = queries; }
    memory = queries;
  };
  const CLOCK = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>';
  const CROSS = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M18 6 6 18M6 6l12 12"/></svg>';
  function list() {
    const query = $("query").value.trim(), box = $("hits"), input = $("query");
    box.replaceChildren();
    const typing = regular ? [] : [...new Set(forms(query))].map(form => form.split(" ").filter(Boolean)), tokens = [...new Set(typing.flat())]; // a query read as typed and as the keys of a Korean layout
    const asked = regular && query ? sought() : {}, theirs = regular ? [] : termed(plain(query));
    const find = text => asked.pattern ? matches(text, asked.pattern) : spans(text, tokens);
    const found = !query || asked.error ? [] : (asked.pattern ? grep(asked.pattern) : rank(query)).slice(0, 8);
    const before = scope ? [] : recalled().filter(text => !query || text.toLowerCase().startsWith(query.toLowerCase()) && text.length > query.length).map(text => ({ recent: text }));
    const groups = [["Recent", before], ...(query ? [...new Set(found.map(entry => entry.kind))].map(kind => [KINDS[kind], found.filter(entry => entry.kind === kind)])
      : [["Questions", "question"], ["Scenarios", "scenario"], ["Levels", "level"], ["Properties", "property"]].filter(group => !scope || group[0] === scope).map(([title, kind]) => [title, entries.filter(entry => entry.kind === kind)]))];
    listed = groups.flatMap(group => group[1]);
    if (chosen < 0) chosen = query && found.length ? before.length : 0; // a typed query's Enter opens its top record; a recent one is a move away
    chosen = Math.min(chosen, Math.max(0, listed.length - 1));
    input.setAttribute("aria-invalid", String(!!asked.error));
    input.removeAttribute("aria-activedescendant");
    const option = (item, ...children) => make("div", { class: "hit", role: "option", id: `hit-${listed.indexOf(item)}`, "aria-selected": String(listed[chosen] === item) }, ...children);
    for (const [title, hits] of groups) {
      if (!hits.length) continue;
      box.append(make("h3", {}, title));
      for (const item of hits) {
        if (item.recent) { // the typed part plain, the rest of the kept query bold
          const row = option(item, make("span", { class: "clock" }), make("div", { class: "text" }, make("span", { class: "recent" }, item.recent.slice(0, query.length), make("b", {}, item.recent.slice(query.length)))),
            make("button", { class: "tool icon quiet forget", type: "button", "aria-label": `Remove ${item.recent} from recent searches`, title: "Remove" }));
          row.dataset.recent = item.recent;
          row.querySelector(".clock").innerHTML = CLOCK; row.querySelector(".forget").innerHTML = CROSS;
          row.addEventListener("click", event => event.target.closest(".forget") ? forget(item.recent) : recall(item.recent));
          box.append(row);
          continue;
        }
        const entry = item, named = query ? find(entry.name) : [], text = [make("b", {}, ...marked(entry.name, named))];
        const form = query && !asked.pattern && (typing.find(words => words.every(token => [entry.name, ...entry.shown.map(one => one.text)].some(text => spans(text, [token]).length))) || typing[0]);
        const missing = asked.pattern ? !named.length : !!form && form.some(token => !spans(entry.name, [token]).length);
        const part = missing && entry.shown.map(one => ({ ...one, found: find(one.text), titled: find(one.field) })).filter(one => one.found.length + one.titled.length).sort((a, b) => b.found.length + b.titled.length - a.found.length - a.titled.length)[0];
        const through = theirs.length && plain(query).split(" ").some(token => !spans(entry.name, [token]).length) ? [make("i", {}, "matched alias:"), " ", make("mark", {}, theirs[0][0]), ` (${theirs[0][1]})`] : []; // found through a term's alias, read as its term
        if (part || through.length) text.push(make("span", { class: "where" }, ...through, ...(part ? [...(through.length ? [" · "] : []), make("i", {}, ...marked(part.field, part.titled)), " ", ...excerpt(part.text, part.found.length ? part.found : [[0, 0]])] : [])));
        const row = option(entry, make("div", { class: "text" }, text[0], make("small", {}, entry.note), ...text.slice(1)));
        row.dataset.hit = entry.id;
        row.addEventListener("click", () => pick(entry));
        box.append(row);
      }
    }
    if (asked.error) box.append(make("div", { class: "none error", role: "alert" }, make("b", {}, "Not a regular expression"), make("span", {}, asked.error)));
    else if (query && !found.length) box.append(make("div", { class: "none", role: "status" }, make("b", {}, `No results for “${query}”`),
      make("span", {}, regular ? "Check the pattern, or turn regular expressions off with Alt+R." : "Try fewer or other words, or turn on regular expressions with Alt+R.")));
    const current = box.querySelector('[aria-selected="true"]');
    if (current) { current.scrollIntoView({ block: "nearest" }); input.setAttribute("aria-activedescendant", current.id); }
  }
  function recall(text) { $("query").value = text; chosen = -1; $("query").focus(); list(); }
  function forget(text) { remember(recalled().filter(one => one !== text)); $("query").focus(); list(); }
  function regex(on) {
    regular = on; chosen = -1;
    $("regex").setAttribute("aria-pressed", String(on));
    $("query").focus();
    list();
  }
  function ask(only) {
    scope = only || null; chosen = 0;
    $("query").value = "";
    $("veil").classList.add("show"); $("palette").classList.add("show");
    document.body.dataset.palette = "1";
    list();
    $("query").focus();
  }
  function shut() {
    $("veil").classList.remove("show"); $("palette").classList.remove("show");
    document.body.dataset.palette = "";
    $("query").blur();
  }
  function pick(entry) {
    const query = $("query").value.trim();
    if (entry.recent) return recall(entry.recent);
    if (query && document.body.dataset.palette) remember([query, ...recalled().filter(one => one.toLowerCase() !== query.toLowerCase())].slice(0, 8));
    shut();
    if (entry.kind === "question") { // a question leads to the first record that answers it, or to the gap it is left to
      const question = contract.questions.find(one => one.id === entry.id);
      return pick(entries.find(one => one.id === (question.answers || [question.gap])[0]));
    }
    if (entry.kind === "scenario") return start(entry.id);
    if (entry.kind === "level") return go({ level: entry.id, at: null, scenario: null });
    go({ level: home(entry.id), at: entry.id, scenario: null });
  }

  // ---- wiring ----
  function wire() {
    const stage = $("stage");
    addEventListener("pointermove", approach);
    stage.addEventListener("pointerover", event => { const id = hit(event.target); approach(event); if (id) hover(id); });
    stage.addEventListener("pointerout", event => { approach(event); if (hit(event.target)) unhover(); });
    stage.addEventListener("click", event => { const id = hit(event.target); if (id && event.detail < 2) go({ at: view.at === id ? null : id }); }); // a double click's second click would undo its first
    stage.addEventListener("dblclick", event => { const id = hit(event.target); if (id && records[id].record.opens) go({ level: records[id].record.opens, at: null }, true); }); // in place of the view its first click added
    stage.addEventListener("keydown", event => {
      const id = hit(event.target);
      if (id && event.key === "Enter") go(records[id].record.opens && view.at === id ? { level: records[id].record.opens, at: null } : { at: id });
    });
    $("diagram").addEventListener("click", event => { if (event.target === $("diagram") || event.target === stage) go({ at: null }); });
    $("card").addEventListener("pointerenter", halt);
    $("card").addEventListener("pointerover", event => {
      const chip = event.target.closest(".ref"), term = event.target.closest(".term");
      if (chip) light(chip.dataset.ref);
      if (term) gloss(term, make("strong", {}, term.dataset.term), make("p", {}, ...prose(term.dataset.meaning, true)));
    });
    $("card").addEventListener("pointerout", event => {
      if (event.target.closest(".ref") && !(event.relatedTarget && event.relatedTarget.closest && event.relatedTarget.closest(".ref"))) light(null);
      if (event.target.closest(".term")) unGloss();
    });
    $("card").addEventListener("click", event => {
      const cite = event.target.closest(".cite"), shown = $("gloss").classList.contains("show") && $("gloss").dataset.for === $("card").dataset.for;
      if (!cite || shown) return unGloss();
      gloss(cite, ...sources(records[$("card").dataset.for].record));
      $("gloss").dataset.for = $("card").dataset.for;
    });
    $("card").addEventListener("pointerleave", () => { if (hovered) unhover(); });
    $("search").addEventListener("click", () => ask());
    $("scenarios").addEventListener("click", () => ask("Scenarios"));
    $("properties").addEventListener("click", () => ask("Properties"));
    $("veil").addEventListener("click", shut);
    $("query").addEventListener("input", () => { chosen = -1; list(); });
    $("regex").addEventListener("click", () => regex(!regular));
    $("prev").addEventListener("click", () => stride(-1));
    $("next").addEventListener("click", () => stride(1));
    $("stop").addEventListener("click", () => go({ scenario: null }));
    $("run").addEventListener("click", run);
    $("again").addEventListener("click", () => start(view.scenario));
    $("onward").addEventListener("click", () => start(contract.scenarios[(contract.scenarios.indexOf(records[view.scenario].record) + 1) % contract.scenarios.length].id));
    addEventListener("keydown", event => {
      if (document.body.dataset.palette) {
        if (event.key === "Escape") shut();
        else if (event.altKey && event.code === "KeyR") regex(!regular); // by the key's place, since Option on a Mac turns R into another letter
        else if (event.key === "ArrowDown" || event.key === "ArrowUp") { chosen = (chosen + (event.key === "ArrowDown" ? 1 : listed.length - 1)) % Math.max(1, listed.length); list(); }
        else if (event.key === "Enter" && listed[chosen] && !event.target.closest("button")) pick(listed[chosen]); // a focused button takes its own Enter
        else return;
        return event.preventDefault();
      }
      if ((event.key === "k" && (event.metaKey || event.ctrlKey)) || (event.key === "/" && !event.metaKey && !event.ctrlKey)) { event.preventDefault(); return ask(); }
      if (event.metaKey || event.ctrlKey || event.altKey) return;
      if (event.key === "Escape") { if (view.at) go({ at: null }); else if (view.scenario) go({ scenario: null }); else { hovered = null; mark(); } }
      else if (event.key === " " && view.scenario && !event.target.closest("button, input")) { event.preventDefault(); run(); }
      else if (event.key === "ArrowRight") stride(1);
      else if (event.key === "ArrowLeft") stride(-1);
      else if (event.key === "[") history.back();
      else if (event.key === "]") history.forward();
    });
    addEventListener("popstate", () => show(parse()));
    addEventListener("resize", () => { paint(records[view.level].record); mark(); play(); });
  }

  window.pageRender = data => {
    load(data);
    shownLevel = null;
    const state = parse();
    history.replaceState(state, "", address(state));
    document.title = contract.title;
    $("scenarios").hidden = !(contract.scenarios || []).length;
    $("properties").hidden = !(contract.properties || []).length;
    show(state);
  };
  wire();
  window.pageRender(read("page-data"));
})();
