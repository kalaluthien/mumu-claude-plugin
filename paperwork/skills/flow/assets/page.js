(() => {
  "use strict";
  const read = id => JSON.parse(document.getElementById(id).textContent);
  const contract = read("page-data"), TAGS = read("page-tags"), FORMULAS = read("page-formulas");
  const $ = id => document.getElementById(id);
  const make = (name, attributes = {}, ...children) => {
    const element = document.createElement(name);
    for (const [key, value] of Object.entries(attributes)) if (value !== undefined && value !== null && value !== false) element.setAttribute(key, value);
    element.append(...children.flat().filter(child => child !== null && child !== undefined && child !== false));
    return element;
  };
  const draw = (name, attributes = {}, ...children) => {
    const element = document.createElementNS("http://www.w3.org/2000/svg", name);
    for (const [key, value] of Object.entries(attributes)) if (value !== undefined && value !== null) element.setAttribute(key, value);
    element.append(...children);
    return element;
  };
  const GROUP_COLOURS = 8; // the KRDS scales page.css names, taken in turn and again past the eighth group
  const GAP = 48, TOP = 72, ROW = 64, HEAD = 28, PAD = 56;

  // ---- the contract's records ----
  const records = {}, counted = {}, openers = {};
  const add = (kind, list) => (list || []).forEach(record => { records[record.id] = { kind, record }; });
  add("group", contract.groups); add("level", contract.levels); add("node", contract.nodes); add("edge", contract.edges);
  add("task", contract.tasks); add("fragment", contract.fragments); add("milestone", contract.milestones);
  add("property", contract.properties); add("question", contract.questions);
  for (const edge of contract.edges || []) if (edge.opens) openers[edge.opens] = edge.id;
  for (const property of contract.properties || []) {
    const kind = property.kind === "gap" ? "gap" : property.status || "holds";
    for (const one of new Set(property.on || [])) ((counted[one] = counted[one] || {})[kind] = counted[one][kind] || []).push(property.id);
  }
  const groupIndex = Object.fromEntries((contract.groups || []).map((group, k) => [group.id, k % GROUP_COLOURS]));
  const of = (kind, level) => (contract[kind] || []).filter(record => record.level === level);
  const step = edge => of("edges", edge.level).indexOf(edge) + 1;
  const codes = edge => (TAGS.edge[edge.tag] ? TAGS.edge[edge.tag].items : []).filter(item => item.form === "code" && typeof (edge.info || {})[item.name] === "string" && edge.info[item.name] !== edge.label).map(item => edge.info[item.name]); // a value the name already says is not written twice
  const home = id => { // the level a record is drawn on: its own, or for a node the shown level when it lists the node, else the first that does
    const { kind, record } = records[id];
    if (kind === "level") return id;
    if (kind === "node") return records[view.level].record.nodes.includes(id) ? view.level : contract.levels.find(level => level.nodes.includes(id)).id;
    return record.level || view.level;
  };

  // ---- the card and the search lib holds ----
  let kept = null;
  const recordCard = paperworkCard({ make, formulas: FORMULAS, record: id => records[id], terms: () => contract.terms, sources: () => contract.sources,
    counted: () => counted, rows, place, kept: id => kept === id, light, follow });
  const { words, tagName, counts } = recordCard;
  const search = paperworkSearch({ make, entries: () => entries, terms: () => contract.terms, open,
    kinds: { node: "Nodes", edge: "Edges", task: "Tasks", milestone: "Milestones", fragment: "Fragments", level: "Levels", property: "Properties", question: "Questions" },
    browse: [["Questions", "question"], ["Levels", "level"], ["Properties", "property"]],
    shelf: () => `paperwork-flow-recent ${contract.title} ${location.pathname}` }); // every file:// page shares one storage

  function rows(id) {
    const { kind, record } = records[id], list = [], put = (name, form, data) => data !== undefined && data !== null && data !== "" && !(Array.isArray(data) && !data.length) && list.push([name, form, data]);
    const named = ids => (ids || []).map(one => `{${one}}`);
    if (kind === "edge") { put("step", "text", String(step(record))); put("between", "text", `{${record.from}} → {${record.to}}`); }
    if (kind === "task") put("on", "text", `{${record.node}}`);
    if (kind === "node") put("group", "text", records[record.group].record.label);
    if (kind === "fragment") put("operands", "list", record.operands.map(operand => (operand.guard ? `[${operand.guard}] ` : "") + named(operand.edges).join(", ")));
    if (kind === "property") { put("statement", "text", record.statement); put("on", "list", named(record.on)); put("fault", "text", record.fault); }
    if (kind === "question") { put("asks", "text", record.asks); put("answers", "list", named(record.answers)); put("gap", "text", record.gap && `{${record.gap}}`); }
    if (kind === "level") put("about", "text", record.about);
    put("purpose", "text", record.purpose);
    if (/^(node|edge|task|milestone|fragment)$/.test(kind)) for (const [name, form, data] of recordCard.countRows(id)) put(name, form, data);
    const catalogue = TAGS[kind] && TAGS[kind][record.tag] ? TAGS[kind][record.tag].items.concat(TAGS.common[kind] || []) : [];
    for (const [name, data] of Object.entries(record.info || {})) {
      const item = catalogue.find(one => one.name === name);
      put(item ? item.label : name, item ? item.form : Array.isArray(data) ? "list" : "text", data);
    }
    put("after", "list", named(record.after));
    if (record.opens) put("opens", "text", `{${record.opens}}`);
    if (record.evidence) put("evidence", "list", record.evidence.map(entry => {
      const [source, line] = entry.split(":"), known = (contract.sources || []).find(one => one.id === source);
      return (known ? known.path : source) + (line ? ":" + line : "");
    }));
    return list;
  }
  const spot = id => { const element = document.querySelector(`#stage [data-id="${id}"]`); return element && element.getBoundingClientRect(); };
  function place(id, w, h) { // beside the record, on the side with room, clear of the pointer that raised it
    const at = spot(id) || { left: innerWidth / 2, right: innerWidth / 2, top: 68, bottom: 68 };
    const right = at.right + 16 + w <= innerWidth - 8, left = right ? at.right + 16 : Math.max(8, at.left - 16 - w);
    return { left, top: Math.min(Math.max(60, at.top), innerHeight - h - 8), cost: 0, tied: 0 };
  }
  function light(id) {
    document.querySelectorAll("#stage .lit").forEach(element => element.classList.remove("lit"));
    if (id) document.querySelectorAll(`#stage [data-id="${id}"], #stage [data-for="${id}"]`).forEach(element => element.classList.add("lit"));
  }
  function follow(id) { // a chip opens its record's card, on the level that draws it
    if (!records[id]) return false;
    if (["property", "question", "group"].includes(records[id].kind)) { kept = id; recordCard.show(id); return true; }
    go(home(id), id);
    return true;
  }

  // ---- the search's entries ----
  const entries = [];
  const values = data => Array.isArray(data) ? data.map(values).join(" ") : data && typeof data === "object" ? Object.values(data).map(values).join(" ") : String(data ?? ""); // a list's, table's or tree's words, with no key
  const texts = info => words(values(info || {}));
  const entry = (id, kind, name, note, fields, shown) => entries.push({ id, kind, name, note, fields, shown });
  for (const level of contract.levels) entry(level.id, "level", level.title, `${level.kind} level`, [[level.title, 0], [level.id, 1], [level.kind, 2], [level.about && words(level.about), 3]], [["about", level.about]]);
  for (const kind of ["nodes", "edges", "tasks", "milestones"])
    for (const record of contract[kind] || []) entry(record.id, kind.slice(0, -1), record.label, record.tag ? tagName(record.tag) : kind.slice(0, -1),
      [[record.label, 0], [record.id, 1], [record.tag, 2], [record.purpose && words(record.purpose), 3], [texts(record.info), 4]],
      [["id", record.id], ["purpose", record.purpose], ...Object.entries(record.info || {}).map(([name, data]) => [name, values(data)])]);
  for (const fragment of contract.fragments || []) entry(fragment.id, "fragment", `${fragment.kind} ${fragment.operands.map(operand => operand.guard || "").join(" / ")}`.trim(), fragment.kind,
    [[fragment.kind, 0], [fragment.id, 1], [fragment.operands.map(operand => operand.guard || "").join(" "), 3]], [["id", fragment.id]]);
  for (const property of contract.properties || []) entry(property.id, "property", property.title, property.kind, [[property.title, 0], [property.id, 1], [property.kind, 2], [words(property.statement), 3]], [["statement", property.statement]]);
  for (const question of contract.questions || []) entry(question.id, "question", words(question.asks), question.answers ? "question" : "open question", [[words(question.asks), 0], [question.id, 1]], [["id", question.id]]);
  function open(hit) { // the record a search picked
    if (hit.kind === "question") {
      const question = records[hit.id].record;
      return open(entries.find(one => one.id === (question.answers || [question.gap])[0]));
    }
    if (hit.kind === "property") { kept = hit.id; return recordCard.show(hit.id); }
    go(home(hit.id), hit.kind === "level" ? null : hit.id);
  }

  // ---- the view: one level, and the record kept open on it ----
  const view = { level: contract.levels[0].id, at: null };
  function go(level, at) {
    const hash = `#level=${encodeURIComponent(level)}` + (at ? `&at=${encodeURIComponent(at)}` : "");
    if (location.hash === hash) render(); else location.hash = hash;
  }
  function fromAddress() {
    const held = new URLSearchParams(location.hash.slice(1)), level = held.get("level"), at = held.get("at");
    view.level = records[level] && records[level].kind === "level" ? level : contract.levels[0].id;
    view.at = records[at] ? at : null;
  }
  function crumbs() { // the way down from the first level to the shown one, each step an edge that opens the next
    const trail = [view.level];
    while (openers[trail[0]]) trail.unshift(records[openers[trail[0]]].record.level);
    $("crumbs").replaceChildren(...trail.flatMap((level, k) => [
      ...(k ? [make("span", { class: "sep", "aria-hidden": "true" }, "›")] : []),
      make("button", { type: "button", "data-level": level, ...(level === view.level ? { "aria-current": "page" } : {}) }, records[level].record.title)]));
  }

  // ---- drawing ----
  const stage = $("stage");
  const measure = element => { stage.append(element); const size = { w: element.offsetWidth, h: element.offsetHeight }; element.remove(); return size; };
  const colour = node => `--group-fill: var(--group-fill-${groupIndex[node.group]}); --group-edge: var(--group-edge-${groupIndex[node.group]})`;
  const nodeBox = node => make("div", { class: "node", "data-id": node.id, "data-group": node.group, style: colour(node) },
    make("span", { class: "group" }, records[node.group].record.label), make("span", { class: "label" }, node.label));
  const edgeCodes = edge => codes(edge).length ? make("div", { class: "edge-codes", "data-for": edge.id }, codes(edge).join(" · ")) : null;
  const edgeLabel = edge => make("div", { class: "edge-label", "data-id": edge.id }, edge.label, ...(edge.opens ? [make("span", { class: "opens-mark", "data-opens": edge.opens, title: `Open ${records[edge.opens].record.title}` }, "ref")] : []));
  const head = (x, y, toward) => draw("polygon", { class: "head", points: `${x},${y} ${x - 10 * toward},${y - 5} ${x - 10 * toward},${y + 5}` });

  function interaction(level, svg, put) {
    const nodes = level.nodes.map(id => records[id].record), edges = of("edges", level.id);
    const boxes = nodes.map(node => measure(nodeBox(node)));
    const index = Object.fromEntries(nodes.map((node, k) => [node.id, k]));
    const gaps = nodes.map((node, k) => k ? boxes[k - 1].w / 2 + boxes[k].w / 2 + GAP : 0);
    const labels = edges.map(edge => Math.max(measure(edgeLabel(edge)).w, edgeCodes(edge) ? measure(edgeCodes(edge)).w : 0) + 24);
    for (let round = 0; round < 2; round++) for (const [k, edge] of edges.entries()) { // widen the gap an edge's name needs, at the last column it spans
      const from = Math.min(index[edge.from], index[edge.to]), to = Math.max(index[edge.from], index[edge.to]);
      const span = gaps.slice(from + 1, to + 1).reduce((sum, gap) => sum + gap, 0);
      if (to > from && span < labels[k]) gaps[to] += labels[k] - span;
    }
    const left = PAD + 24 + boxes[0].w / 2, xs = [];
    gaps.forEach((gap, k) => xs.push((k ? xs[k - 1] : left) + gap));
    const headHeight = Math.max(...boxes.map(box => box.h));
    nodes.forEach((node, k) => {
      const box = nodeBox(node);
      box.style.left = xs[k] - boxes[k].w / 2 + "px"; box.style.top = TOP + "px"; box.style.width = boxes[k].w + "px"; box.style.height = headHeight + "px";
      put(box);
    });
    const order = edges.map(edge => edge.id), fragments = of("fragments", level.id).map(fragment => {
      const at = fragment.operands.flatMap(operand => operand.edges).map(id => order.indexOf(id));
      return { fragment, first: Math.min(...at), last: Math.max(...at), starts: fragment.operands.map(operand => order.indexOf(operand.edges[0])) };
    });
    fragments.forEach(one => { one.depth = fragments.filter(other => other !== one && other.first <= one.first && one.last <= other.last && (other.first < one.first || one.last < other.last || other.fragment.id < one.fragment.id)).length; });
    const seat = milestone => milestone.after.reduce(([at, depth], id) => { // after the last edge it waits on, through the milestones it waits on, and below those
      if (records[id].kind !== "milestone") return [Math.max(at, order.indexOf(id)), depth];
      const [before, under] = seat(records[id].record);
      return [Math.max(at, before), Math.max(depth, under + 1)];
    }, [-1, 0]);
    const milestones = of("milestones", level.id).map(milestone => { const [after, depth] = seat(milestone); return { milestone, after, depth }; });
    let y = TOP + headHeight + 32;
    const lineEnds = [xs[0] - PAD, xs[xs.length - 1] + PAD];
    const reach = edges.map((edge, k) => edge.from === edge.to ? xs[index[edge.from]] + 48 + labels[k] : Math.max(xs[index[edge.from]], xs[index[edge.to]])); // a self-call's name runs right of its loop
    const mark = k => {
      for (const one of milestones.filter(one => one.after === k).sort((a, b) => a.depth - b.depth)) {
        const lineY = y + 12;
        svg.append(draw("line", { class: "milestone", "data-for": one.milestone.id, x1: lineEnds[0], x2: lineEnds[1], y1: lineY, y2: lineY }));
        const label = make("div", { class: "milestone-label", "data-id": one.milestone.id }, one.milestone.label);
        label.style.left = lineEnds[0] + "px"; label.style.top = lineY - 24 + "px";
        put(label);
        y += 40;
      }
    };
    mark(-1);
    for (const [k, edge] of edges.entries()) {
      for (const one of fragments.filter(one => one.first === k).sort((a, b) => a.depth - b.depth)) { one.top = y; one.guards = [[one.fragment.operands[0].guard, y]]; y += HEAD; }
      for (const one of fragments) one.starts.forEach((start, j) => { if (j && start === k) { one.guards.push([one.fragment.operands[j].guard, y]); y += HEAD; } });
      const from = xs[index[edge.from]], to = xs[index[edge.to]], arrowY = y + 24, self = from === to;
      const group = draw("g", { class: "edge" + (edge.opens ? " opens" : ""), "data-for": edge.id, "data-tag": edge.tag });
      const path = self ? `M${from},${arrowY - 8} h40 v16 h-40` : `M${from},${arrowY} H${to}`;
      group.append(draw("path", { class: "arrow", d: path, "data-tag": edge.tag }), head(self ? from : to, self ? arrowY + 8 : arrowY, self ? -1 : Math.sign(to - from)),
        draw("path", { class: "hit", d: path }));
      group.append(draw("circle", { class: "step", cx: from, cy: self ? arrowY - 8 : arrowY, r: 9 }), draw("text", { class: "step-number", x: from, y: (self ? arrowY - 8 : arrowY) + 4 }, String(k + 1)));
      svg.append(group);
      const label = edgeLabel(edge);
      label.style.left = (self ? from + 48 + labels[k] / 2 : (from + to) / 2) + "px"; label.style.top = (self ? arrowY - 30 : y) + "px";
      const chips = make("div", { class: "edge-chips", "data-for": edge.id }, make("span", { class: "chip" }, tagName(edge.tag)), counts(edge.id));
      chips.style.left = (self ? from + 48 + labels[k] / 2 : (from + to) / 2) + "px"; chips.style.top = arrowY + (self ? 14 : 6) + "px"; // below a self-call's loop too
      put(label, chips);
      const written = edgeCodes(edge);
      if (written) { written.style.left = chips.style.left; written.style.top = arrowY + (self ? 34 : 26) + "px"; put(written); }
      y += ROW + (written ? 18 : 0) + (self ? 8 : 0);
      for (const one of fragments.filter(one => one.last === k).sort((a, b) => b.depth - a.depth)) { one.bottom = y; y += 8; }
      mark(k);
    }
    for (const one of fragments.slice().sort((a, b) => b.depth - a.depth)) { // the inner frames first, so each outer one takes their width
      const inner = fragments.filter(other => other.depth > one.depth && one.first <= other.first && other.last <= one.last);
      const ends = one.fragment.operands.flatMap(operand => operand.edges).flatMap(id => [xs[index[records[id].record.from]], xs[index[records[id].record.to]], reach[order.indexOf(id)] - PAD + 16]);
      const tab = measure(make("div", { class: "fragment-kind" }, one.fragment.kind)).w;
      const room = Math.max(...one.guards.map(([guard], j) => (j ? 8 : tab + 8) + (guard ? measure(make("div", { class: "guard" }, `[${guard}]`)).w + 8 : 0)));
      const x1 = Math.min(Math.min(...ends) - PAD + 8 * one.depth, ...inner.map(other => other.left - 8));
      const x2 = Math.max(Math.max(...ends) + PAD - 8 * one.depth, x1 + room, ...inner.map(other => other.right + 8));
      one.left = x1; one.right = x2;
      svg.append(draw("rect", { class: "fragment", "data-for": one.fragment.id, x: x1, y: one.top, width: x2 - x1, height: one.bottom - one.top, rx: 4 }));
      const kind = make("div", { class: "fragment-kind", "data-id": one.fragment.id }, one.fragment.kind);
      kind.style.left = x1 + "px"; kind.style.top = one.top + "px";
      put(kind);
      one.guards.forEach(([guard, at], j) => {
        if (j) svg.append(draw("line", { class: "operand-line", "data-for": one.fragment.id, x1, x2, y1: at, y2: at }));
        if (!guard) return;
        const text = make("div", { class: "guard", "data-for": one.fragment.id }, `[${guard}]`);
        text.style.left = x1 + (j ? 8 : tab + 8) + "px"; text.style.top = at + 2 + "px";
        put(text);
      });
    }
    const bottom = y + 16;
    nodes.forEach((node, k) => {
      const line = { x1: xs[k], x2: xs[k], y1: TOP + headHeight, y2: bottom };
      svg.prepend(draw("g", { class: "lifeline-hit", "data-for": node.id }, draw("line", { class: "lifeline", style: colour(node), ...line }), draw("line", { class: "hit", ...line })));
    });
    const right = Math.max(lineEnds[1], ...fragments.map(one => one.right), ...reach.map(x => x + 16));
    return { width: right + PAD, height: bottom + 48 };
  }

  function render() {
    fromAddress();
    recordCard.hide();
    kept = null;
    const level = records[view.level].record, svg = draw("svg", { "aria-hidden": "true" }), parts = [];
    stage.replaceChildren();
    const size = interaction(level, svg, (...elements) => parts.push(...elements));
    svg.setAttribute("width", size.width); svg.setAttribute("height", size.height);
    stage.style.width = size.width + "px"; stage.style.height = size.height + "px";
    stage.replaceChildren(svg, ...parts);
    crumbs();
    document.title = `${contract.title} · ${level.title}`;
    if (view.at && spot(view.at)) { kept = view.at; light(view.at); recordCard.show(view.at); }
  }

  // ---- the reader's moves ----
  const target = event => { const element = event.target.closest && event.target.closest("#stage [data-id], #stage [data-for]"); return element && (element.dataset.id || element.dataset.for); };
  stage.addEventListener("pointerover", event => {
    const id = target(event);
    if (!id || kept) return;
    light(id); recordCard.show(id);
  });
  stage.addEventListener("pointerout", event => {
    if (kept || target(event) === (event.relatedTarget && event.relatedTarget.closest && target({ target: event.relatedTarget }))) return;
    light(null); recordCard.hide();
  });
  stage.addEventListener("click", event => {
    const opener = event.target.closest(".opens-mark"), id = target(event);
    if (opener) return go(opener.dataset.opens, null);
    if (!id) { kept = null; light(null); return recordCard.hide(); }
    kept = id; light(id); recordCard.show(id);
  });
  stage.addEventListener("dblclick", event => { // an edge that opens a level opens it, as its card's hint says
    const id = target(event);
    if (id && records[id].record.opens) go(records[id].record.opens, null);
  });
  $("crumbs").addEventListener("click", event => { const step = event.target.closest("[data-level]"); if (step) go(step.dataset.level, null); });
  $("search").addEventListener("click", () => search.ask());
  addEventListener("keydown", event => {
    if (search.key(event)) return;
    if (event.key === "Escape") { kept = null; light(null); recordCard.hide(); }
  });
  addEventListener("hashchange", render);
  render();
})();
