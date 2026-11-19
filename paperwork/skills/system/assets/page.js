(() => {
  "use strict";
  const read = id => JSON.parse(document.getElementById(id).textContent);
  const TAGS = read("page-tags");
  const $ = id => document.getElementById(id);
  const make = (name, attributes = {}, ...children) => {
    const element = document.createElement(name);
    for (const [key, value] of Object.entries(attributes)) key === "class" ? (element.className = value) : element.setAttribute(key, value);
    element.append(...children);
    return element;
  };
  const draw = (name, attributes = {}) => {
    const element = document.createElementNS("http://www.w3.org/2000/svg", name);
    for (const [key, value] of Object.entries(attributes)) element.setAttribute(key, value);
    return element;
  };
  const still = () => matchMedia("(prefers-reduced-motion: reduce)").matches;

  let contract, records, levelOf, openers, entries, shownLevel = null, boxes = {}, curves = {}, blocks = [], faces = {}, plans = {};
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
    entries = index();
  }
  const label = id => records[id] ? (records[id].record.label || records[id].record.title || id) : id;
  const words = text => String(text).replace(/\{([a-z0-9-]+)\}/g, (whole, id, at, all) => { // a named record, with a capital where a sentence opens
    if (!records[id]) return whole;
    const name = label(id);
    if (/[ㄱ-ㆎ가-힣]/.test(all)) return name.replace(/^(?:an?|the)\s+/i, ""); // Korean has no article and no capital
    const plain = !/[./_\d]|[a-z][A-Z]/.test(name.split(/\s+/)[0]); // a file name stays as written
    return plain && (at === 0 || all.slice(0, at).endsWith(". ")) ? name[0].toUpperCase() + name.slice(1) : name;
  });
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
    { inner: [52, 72, 28, 22], outer: [64, 96, 44, 36], pad: 16, head: 30, labels: true },
    { inner: [44, 52, 24, 18], outer: [52, 60, 36, 28], pad: 16, head: 30 },
    { inner: [30, 36, 14, 12], outer: [38, 44, 22, 18], pad: 10, head: 24, dense: true },
    { inner: [22, 26, 10, 10], outer: [28, 30, 14, 12], pad: 8, head: 22, dense: true },
  ];
  const pen = document.createElement("canvas").getContext("2d");
  function size(level, fit, grown = 1) { // a node as wide as its label needs: every node of a roomy level alike, each its own on a dense one
    pen.font = `500 ${fit.dense ? 12 : 14}px ${FONT}`;
    const most = fit.dense ? 260 : 320, beside = node => (node.opens ? 32 : 0) + (fit.dense ? 22 : 30), text = node => Math.ceil(pen.measureText(node.label).width * 1.1 * grown);
    const need = node => text(node) + beside(node);
    const lines = node => need(node) <= most ? 1 : Math.ceil(text(node) * 1.15 / (most - beside(node))); // a label too long for the widest box goes on over more lines
    const widest = Math.min(most, Math.max(196, ...level.nodes.map(need))), tallest = 58 + 20 * (Math.max(...level.nodes.map(lines)) - 1);
    return Object.fromEntries(level.nodes.map(node => [node.id, fit.dense ? { w: Math.min(most, Math.max(96, need(node))), h: 40 + 16 * (lines(node) - 1) } : { w: widest, h: tallest }]));
  }
  const wide = edges => Math.max(0, ...edges.map(edge => words(edge.label).length)) * 6.4 + 56;
  const fill = plan => Math.min((innerWidth - 2 * ROOM.side) / plan.w, (innerHeight - ROOM.top - ROOM.bottom) / plan.h);
  function arrange(level) {
    const across = innerWidth - 2 * ROOM.side, down = innerHeight - ROOM.top - ROOM.bottom;
    const used = plan => { const scale = Math.min(fill(plan), 1.3); return Math.min(plan.w * scale / across, plan.h * scale / down); };
    const spread = plan => { // the side with room to spare gets wider gaps, never larger type
      for (let wider = 1, taller = 1, turns = 0; turns < 16; turns++) {
        const steps = [[wider * 1.25, taller], [wider, taller * 1.25]];
        if (plan.w / across > plan.h / down) steps.reverse();
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
      group.w = group.inside.w + (group.area ? 2 * fit.pad : 0);
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
    for (const area of level.areas || []) {
      const spot = boxes[area.id];
      if (spot) stage.append(make("div", { class: "area", "data-id": area.id, "data-tag": area.tag, style: `left:${spot.x}px;top:${spot.y}px;width:${spot.w}px;height:${spot.h}px` },
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
        const open = make("button", { class: "open", type: "button", "aria-label": `Open ${words(label(node.opens))}`, title: `Open ${words(label(node.opens))}` });
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
      const text = make("div", { class: "label", "data-edge": edge.id }, words(edge.label));
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
    const x = scale => ROOM.side + (innerWidth - 2 * ROOM.side - w * scale) / 2, y = scale => ROOM.top + (innerHeight - ROOM.top - ROOM.bottom - h * scale) / 2;
    const scale = Math.min((innerWidth - 2 * ROOM.side) / w, (innerHeight - ROOM.top - ROOM.bottom) / h, 1.3);
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
  function show(next) {
    Object.assign(view, next);
    const stage = $("stage"), from = shownLevel;
    hovered = null;
    hide(true);
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
      const back = seen === fading && leftLevel === view.level, old = from === null || back ? null : seen.cloneNode(true), before = old && placed(seen), entered = down && lies(down);
      if (seen === stage) leftLevel = from;
      for (const left of document.querySelectorAll(".stage.old")) left.remove();
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
          { duration: quiet ? 240 : MOVE.arrive, delay: quiet ? 0 : MOVE.wait, easing: quiet ? "ease-out" : ARRIVE, fill: "backwards" }).finished.then(() => { document.body.dataset.busy = ""; }, () => {});
        late = quiet ? 0 : MOVE.wait + 40;
      } else if (back) {
        stage.animate(still() ? [{ opacity: held.opacity }, { opacity: 1 }] : [held, { transform: at(placed()), opacity: 1 }], { duration: still() ? 240 : MOVE.arrive, easing: still() ? "ease-out" : ARRIVE })
          .finished.then(() => { document.body.dataset.busy = ""; }, () => {});
      }
      document.body.dataset.busy = old || back ? "1" : "";
    }
    Object.assign(document.body.dataset, { level: view.level, at: view.at || "", scenario: view.scenario || "", step: view.scenario ? view.step : "" });
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
      const item = make("button", { type: "button", "data-level": id, ...(i === path.length - 1 ? { "aria-current": "page" } : {}) }, words(records[id].record.title));
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
    if (hovered) card(hovered); else if (view.at) card(view.at); else hide(true);
  }
  const prose = text => words(text).split(/(`[^`]+`)/).filter(Boolean).map(part => part[0] === "`" ? make("code", {}, ...part.slice(1, -1).split(/(?<=\/)/).flatMap((piece, i) => i ? [make("wbr"), piece] : [piece])) : part);
  const FOLD = { list: 4, table: 3, tree: 4, code: 5 }; // the items a row of the resting card shows
  const value = (form, data, most) => {
    const rest = count => count > most ? [make("small", { class: "more" }, `+${count - most} more`)] : [];
    if (form === "list" && Array.isArray(data)) return [make("ul", {}, ...data.slice(0, most).map(item => make("li", {}, ...prose(item)))), ...rest(data.length)];
    if (form === "table" && data && data.columns) {
      const table = make("table", {}, make("thead", {}, make("tr", {}, ...data.columns.map(name => make("th", {}, name)))));
      table.append(make("tbody", {}, ...data.rows.slice(0, most).map(row => make("tr", {}, ...row.map(cell => make("td", {}, ...prose(cell)))))));
      return [table, ...rest(data.rows.length)];
    }
    if (form === "tree" && Array.isArray(data)) {
      const branch = list => make("ul", {}, ...list.map(item => make("li", {}, make("code", {}, words(item.name)), ...(item.note ? [" ", ...prose(item.note)] : []), ...(item.children ? [branch(item.children)] : []))));
      return [branch(data.slice(0, most)), ...rest(data.length)];
    }
    if (form === "code") { const lines = String(data).split("\n"); return [make("pre", {}, make("code", {}, lines.slice(0, most).join("\n"))), ...rest(lines.length)]; }
    return [make("span", most < Infinity ? { class: "clamp" } : {}, ...prose(typeof data === "string" ? data : JSON.stringify(data)))];
  };
  function rows(id) {
    const { kind, record } = records[id], list = [], add = (name, form, data) => data !== undefined && data !== null && data !== "" && list.push([name, form, data]);
    if (kind === "edge") add(record.tag === "transition" ? "transition" : "sentence", "text", sentence(record));
    if (kind === "property") { add("statement", "text", record.statement); add("on", "list", (record.on || []).map(label)); add("fault", "text", record.fault); }
    if (kind === "scenario") add("steps", "list", record.steps.map(step => label(step.at) + (step.note ? " · " + step.note : "")));
    add("purpose", "text", record.purpose);
    const items = TAGS[kind] && TAGS[kind][record.tag] ? TAGS[kind][record.tag].items.concat(TAGS.common[kind] || []) : [];
    for (const [name, data] of Object.entries(record.info || {})) {
      const item = items.find(one => one.name === name);
      add(item ? item.label : name, item ? item.form : Array.isArray(data) ? "list" : "text", name === "initial" ? label(data) : data);
    }
    if (record.opens) add("opens", "text", words(label(record.opens)));
    if (record.evidence) add("evidence", "list", record.evidence.map(entry => {
      const [source, line] = entry.split(":"), known = (contract.sources || []).find(one => one.id === source);
      return (known ? known.path : source) + (line ? ":" + line : "");
    }));
    return list;
  }
  function beside(id, w, h, apart = .6) { // the spot nearest a record that covers neither it nor what the reader follows from it; `apart` is what covering another node costs
    const spot = lies(id), tied = near(id), dear = [];
    if (!spot) return { left: innerWidth / 2 - w / 2, top: 68 };
    const keep = (rect, by, weight) => dear.push({ left: rect.left - by, top: rect.top - by, right: rect.right + by, bottom: rect.bottom + by, weight });
    const points = (one, weight) => line(one).forEach(point => keep({ left: point.x, top: point.y, right: point.x, bottom: point.y }, 6, weight));
    keep(spot, 8, 400);
    points(id, 400);
    for (const one of tied) if (one !== id && records[one] && records[one].kind !== "area") { if (lies(one)) keep(lies(one), 0, 40); points(one, 12); }
    for (const node of records[view.level].record.nodes) if (!tied.has(node.id)) keep(lies(node.id), 0, apart);
    for (const [one, face] of Object.entries(faces)) if (one !== id && (!face.text.classList.contains("tucked") || face.text.classList.contains("shown"))) keep(lies(one), 2, tied.has(one) || face.text.matches(".past, .next") ? 40 : 4);
    for (const bar of [$("tools"), $("crumbs"), $("play")]) if (bar.id !== "play" || bar.classList.contains("show")) keep(bar.getBoundingClientRect(), 8, 400);
    const covers = (x, y, least) => dear.reduce((sum, held) => held.weight < least ? sum : sum + held.weight * Math.max(0, Math.min(x + w, held.right) - Math.max(x, held.left)) * Math.max(0, Math.min(y + h, held.bottom) - Math.max(y, held.top)), 0);
    const price = (x, y) => { // a spot twice as far costs four times as much, so a far clear spot loses to a near one that covers a little
      const far = Math.hypot(Math.max(spot.left - x - w, x - spot.right, 0), Math.max(spot.top - y - h, y - spot.bottom, 0));
      return covers(x, y, 0) + 20 * far + far * far / 4;
    };
    let best = null;
    const weigh = (x, y) => {
      const left = Math.min(Math.max(8, x), innerWidth - w - 8), top = Math.min(Math.max(8, y), innerHeight - h - 8), cost = price(left, top);
      if (!best || cost < best.cost) best = { left, top, cost };
    };
    for (let k = 0; k <= 8; k++) {
      for (const x of [spot.right + 12, spot.left - 12 - w]) weigh(x, spot.top - h + (h + spot.height) * k / 8);
      for (const y of [spot.bottom + 12, spot.top - 12 - h]) weigh(spot.left - w + (w + spot.width) * k / 8, y);
    }
    for (let x = 8; x <= innerWidth - w - 8; x += 40) for (let y = 8; y <= innerHeight - h - 8; y += 40) weigh(x, y);
    const rough = best;
    for (let x = -32; x <= 32; x += 8) for (let y = -32; y <= 32; y += 8) weigh(rough.left + x, rough.top + y); // the spots between those tried
    return { ...best, tied: covers(best.left, best.top, 40) }; // `tied` is what the spot still covers of the record and of what is tied to it
  }
  let leaf = 0; // the page of rows the kept card shows
  function card(id) {
    const { kind, record } = records[id], box = $("card"), kept = view.at === id, all = rows(id);
    if (box.dataset.for !== id || !kept) leaf = 0;
    const tags = make("div", {}, make("span", { class: "tag fill" }, tagName(record.tag || record.kind || kind)));
    for (const extra of [record.basis, record.strength, record.status, record.many ? "many" : ""]) if (extra) tags.append(make("span", { class: "tag" }, extra));
    const list = make("dl"), foot = make("footer", {}, make("kbd", {}, "esc"));
    box.replaceChildren(make("h2", {}, words(record.label || record.title || record.id)), tags, list, foot);
    box.dataset.for = id;
    box.classList.toggle("kept", kept);
    const limit = Math.floor(kept ? innerHeight * .7 : Math.min(innerHeight * .46, 400));
    const lay = (from, most = Infinity) => { // the rows from FROM on that the card's height holds, MOST at most, and the row after them
      box.classList.remove("long");
      box.style.maxHeight = "none";
      list.replaceChildren();
      let to = from;
      for (; to < all.length && to - from < most; to++) {
        const [name, form, data] = all[to];
        list.append(make("div", { "data-form": form }, make("dt", {}, name), make("dd", {}, ...value(form, data, kept ? Infinity : FOLD[form] || 3))));
        if (to > from && box.offsetHeight > limit) { list.lastChild.remove(); break; }
      }
      return to;
    };
    const starts = [0];
    for (let to = lay(0); to < all.length; to = lay(to)) starts.push(to);
    leaf = Math.min(leaf, starts.length - 1);
    const hint = (key, text) => make("span", {}, make("kbd", {}, key), text);
    const fill = most => { // the card with MOST rows at most, and the place it would take
      const end = lay(starts[leaf], most), turn = make("button", { class: "turn", type: "button", "aria-label": "More rows" }, `${starts[leaf] + 1}–${end} of ${all.length} ›`);
      turn.addEventListener("click", () => { leaf = (leaf + 1) % starts.length; card(id); });
      foot.replaceChildren(...(kept ? (starts.length < 2 ? [] : [turn]) : end < all.length ? [make("span", {}, `+${all.length - end} more`)] : []),
        make("span", { class: "hints" }, kept ? hint("esc", "close") : hint("click", "keep"), ...(record.opens ? [hint("double-click", "open")] : [])));
      box.style.maxHeight = limit + "px";
      box.classList.toggle("long", box.scrollHeight > limit + 1);
      return { ...beside(id, box.offsetWidth, box.offsetHeight), rows: end - starts[leaf] };
    };
    let at = fill(Infinity);
    for (let most = at.rows - 1, tried = at; !kept && tried.tied && most >= 1; most--) { // a card no place holds clear of what is tied sheds rows until one does
      tried = fill(most);
      if (tried.cost < at.cost) at = tried;
    }
    if (list.children.length !== at.rows) fill(at.rows);
    box.style.left = at.left + "px";
    box.style.top = at.top + "px";
    box.classList.add("show");
  }
  function hide(now) {
    clearTimeout(rest); clearTimeout(leave);
    if (now) { $("card").classList.remove("show"); $("card").dataset.for = ""; }
  }
  function hover(id) {
    clearTimeout(leave); clearTimeout(rest);
    if (hovered === id) return;
    const rested = () => { // no card rises over a level still on its way
      if (document.body.dataset.busy) rest = setTimeout(rested, 80);
      else { hovered = id; mark(); }
    };
    rest = setTimeout(rested, hovered ? (nearing ? 420 : 60) : 140);
  }
  function unhover() {
    clearTimeout(rest); clearTimeout(leave);
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
    bar.querySelector(".title").textContent = words(scenario.title);
    const dots = bar.querySelector(".dots");
    if (dots.dataset.for !== view.scenario) dots.replaceChildren(...steps.map((one, i) => { // kept while the scenario plays, so a pressed one keeps the focus
      const dot = make("button", { type: "button", "aria-label": `Step ${i + 1}`, title: words(label(one.at)) });
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
      chip.replaceChildren(...prose(step.note));
      const at = beside(step.at, chip.offsetWidth, chip.offsetHeight, 12); // a note is small enough to keep off every node
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
  const start = id => go({ scenario: id, step: 0, level: home(records[id].record.steps[0].at), at: null });
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
  function index() {
    const list = [], add = (id, kind, name, note, fields) => list.push({ id, kind, name, note, fields: fields.filter(([text]) => text).map(([text, weight]) => ({ text: plain(text), tokens: plain(text).split(" "), weight })) });
    const texts = info => words(JSON.stringify(info || {})).replace(/["{}\[\],:]+/g, " ");
    for (const level of contract.levels) {
      add(level.id, "level", words(level.title), "level", [[words(level.title), 10], [level.id, 8], [level.about && words(level.about), 2]]);
      for (const node of level.nodes) add(node.id, "node", node.label, tagName(node.tag), [[node.label, 10], [node.id, 8], [node.tag, 4], [node.purpose && words(node.purpose), 2], [texts(node.info), 1]]);
      for (const area of level.areas || []) add(area.id, "area", area.label, tagName(area.tag), [[area.label, 10], [area.id, 8], [area.tag, 4], [texts(area.info), 1]]);
      for (const edge of level.edges || []) add(edge.id, "edge", sentence(edge), tagName(edge.tag), [[words(edge.label), 9], [sentence(edge), 6], [edge.id, 5], [edge.tag, 3], [texts(edge.info), 1]]);
    }
    for (const scenario of contract.scenarios || []) add(scenario.id, "scenario", words(scenario.title), `${scenario.steps.length} steps`, [[words(scenario.title), 10], [scenario.id, 8], [scenario.purpose && words(scenario.purpose), 2]]);
    for (const property of contract.properties || []) add(property.id, "property", words(property.statement), property.kind, [[property.id, 9], [words(property.statement), 5], [property.kind, 4]]);
    for (const question of contract.questions || []) add(question.id, "question", words(question.asks), question.answers ? "question" : "open question", [[words(question.asks), 3], [question.id, 2]]);
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
  const ORDER = ["node", "level", "area", "edge", "scenario", "property", "question"];
  function match(token, field) {
    if (field.text === token) return 120;
    if (field.tokens.includes(token)) return 100;
    if (field.text.startsWith(token)) return 80;
    if (field.tokens.some(word => word.startsWith(token))) return 70;
    if (token.length > 1 && field.tokens.length >= token.length && field.tokens.map(word => word[0]).join("").startsWith(token)) return 40;
    if (token.length > 2 && field.text.includes(token)) return 30;
    const most = token.length >= 8 ? 2 : token.length >= 4 ? 1 : 0;
    if (most && field.tokens.some(word => slips(token, word.length > token.length + most ? word.slice(0, token.length) : word, most) <= most)) return 25;
    return 0;
  }
  function rank(query) {
    const scored = new Map();
    for (const form of new Set([plain(query), plain(typed(query))])) {
      const tokens = form.split(" ").filter(Boolean);
      if (!tokens.length) continue;
      for (const entry of entries) {
        let total = 0, whole = 0;
        for (const field of entry.fields) whole = Math.max(whole, match(tokens.join(" "), field) * field.weight * 1.2);
        for (const token of tokens) {
          let best = 0;
          for (const field of entry.fields) best = Math.max(best, match(token, field) * field.weight);
          if (!best) { total = 0; break; }
          total += best;
        }
        const score = Math.max(tokens.length > 1 ? whole : 0, total / tokens.length);
        if (score > (scored.get(entry) || 0)) scored.set(entry, score);
      }
    }
    const order = found => [...found].sort((a, b) => b[1] - a[1] || ORDER.indexOf(a[0].kind) - ORDER.indexOf(b[0].kind) || a[0].name.length - b[0].name.length || a[0].id.localeCompare(b[0].id)).map(([entry]) => entry);
    const asked = plain(query).split(" ").filter(Boolean);
    return scored.size || asked.length < 3 ? order(scored) : order(answering(asked));
  }
  const stem = word => word.length > 4 ? word.replace(/(ies|es|ed|ing|s)$/, "") : word;
  function answering(tokens) { // a sentence no record holds whole: each record by the words it shares, a word the fewer records hold counting the more
    const found = new Map();
    for (const token of new Set(tokens.map(stem))) {
      const weights = new Map();
      for (const entry of entries) {
        const weight = Math.max(0, ...entry.fields.filter(field => field.tokens.some(word => stem(word) === token)).map(field => field.weight));
        if (weight) weights.set(entry, weight);
      }
      const rare = Math.log(entries.length / (weights.size || 1));
      for (const [entry, weight] of weights) found.set(entry, (found.get(entry) || 0) + rare * Math.sqrt(weight));
    }
    return [...found].filter(([, score]) => score > 0);
  }
  let chosen = 0, listed = [], scope = null;
  const KINDS = { node: "Nodes", level: "Levels", area: "Areas", edge: "Edges", scenario: "Scenarios", property: "Properties", question: "Questions" };
  function list() {
    const query = $("query").value.trim(), box = $("hits");
    box.replaceChildren();
    const tokens = [plain(query), plain(typed(query))].flatMap(form => form.split(" ")).filter(Boolean);
    const lit = text => { // the letters of TEXT a query word matched, marked
      const low = text.toLowerCase(), spans = [];
      for (const token of tokens) for (let at = low.indexOf(token); at >= 0; at = low.indexOf(token, at + token.length)) spans.push([at, at + token.length]);
      spans.sort((a, b) => a[0] - b[0]);
      const parts = [];
      let done = 0;
      for (const [start, end] of spans) {
        if (start < done) continue;
        parts.push(text.slice(done, start), make("mark", {}, text.slice(start, end)));
        done = end;
      }
      return parts.concat(text.slice(done));
    };
    const found = query ? rank(query).slice(0, 8) : [];
    const groups = query ? [...new Set(found.map(entry => entry.kind))].map(kind => [KINDS[kind], found.filter(entry => entry.kind === kind)])
      : [["Questions", "question"], ["Scenarios", "scenario"], ["Levels", "level"], ["Properties", "property"]].filter(group => !scope || group[0] === scope).map(([title, kind]) => [title, entries.filter(entry => entry.kind === kind)]);
    listed = groups.flatMap(group => group[1]);
    chosen = Math.min(chosen, Math.max(0, listed.length - 1));
    if (!listed.length) return box.append(make("div", { class: "none" }, "No results found."));
    for (const [title, hits] of groups) {
      if (!hits.length) continue;
      box.append(make("h3", {}, title));
      for (const entry of hits) {
        const name = entry.name.replace(/`/g, "");
        const row = make("div", { class: "hit", role: "option", "data-hit": entry.id, "aria-selected": String(listed[chosen] === entry) }, make("b", {}, ...lit(name)),
          ...(tokens.some(token => entry.id.includes(token) && !name.toLowerCase().includes(token)) ? [make("code", {}, ...lit(entry.id))] : []), make("small", {}, entry.note));
        row.addEventListener("click", () => pick(entry));
        box.append(row);
      }
    }
    const current = box.querySelector('[aria-selected="true"]');
    if (current) current.scrollIntoView({ block: "nearest" });
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
    stage.addEventListener("click", event => { const id = hit(event.target); if (id) go({ at: view.at === id ? null : id }); });
    stage.addEventListener("dblclick", event => { const id = hit(event.target); if (id && records[id].record.opens) go({ level: records[id].record.opens, at: null }); });
    stage.addEventListener("keydown", event => {
      const id = hit(event.target);
      if (id && event.key === "Enter") go(records[id].record.opens && view.at === id ? { level: records[id].record.opens, at: null } : { at: id });
    });
    $("diagram").addEventListener("click", event => { if (event.target === $("diagram") || event.target === stage) go({ at: null }); });
    $("card").addEventListener("pointerenter", () => { clearTimeout(leave); clearTimeout(rest); });
    $("card").addEventListener("pointerleave", () => { if (hovered) unhover(); });
    $("search").addEventListener("click", () => ask());
    $("scenarios").addEventListener("click", () => ask("Scenarios"));
    $("properties").addEventListener("click", () => ask("Properties"));
    $("veil").addEventListener("click", shut);
    $("query").addEventListener("input", () => { chosen = 0; list(); });
    $("prev").addEventListener("click", () => stride(-1));
    $("next").addEventListener("click", () => stride(1));
    $("stop").addEventListener("click", () => go({ scenario: null }));
    $("run").addEventListener("click", run);
    $("again").addEventListener("click", () => start(view.scenario));
    $("onward").addEventListener("click", () => start(contract.scenarios[(contract.scenarios.indexOf(records[view.scenario].record) + 1) % contract.scenarios.length].id));
    addEventListener("keydown", event => {
      if (document.body.dataset.palette) {
        if (event.key === "Escape") shut();
        else if (event.key === "ArrowDown" || event.key === "ArrowUp") { chosen = (chosen + (event.key === "ArrowDown" ? 1 : listed.length - 1)) % Math.max(1, listed.length); list(); }
        else if (event.key === "Enter" && listed[chosen]) pick(listed[chosen]);
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
