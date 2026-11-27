// The frame of every paperwork page: the crumbs at the top left, the tools at the top right with the search bar last, the record card and
// the search palette over them, and one Claims list grouped by status. A page calls `paperworkFrame(options)` before it draws, with
// paperworkCard's options but `make` and `claimsOn`, paperworkSearch's but `make`, and:
//   placeholder  what the search box says while empty
//   tools        the page's own buttons, each [id, label], before Claims and the search bar
//   claims()     the contract's claims; questions() its questions
// It returns the card's calls, `search`, `make`, crumbs(trail, pick), and entries() and rows(id) of the claims and questions.
window.paperworkFrame = options => {
  "use strict";
  const $ = id => document.getElementById(id);
  const make = (name, attributes = {}, ...children) => {
    const element = document.createElement(name);
    for (const [key, value] of Object.entries(attributes)) if (value !== undefined && value !== null && value !== false) element.setAttribute(key, value);
    element.append(...children.flat().filter(child => child !== null && child !== undefined && child !== false));
    return element;
  };
  const STATUSES = ["fails", "conflicting", "unknown", "holds"]; // the Claims list's groups, the least settled first
  const hint = (...keys) => keys.map(key => make("kbd", {}, key));
  document.body.append(
    make("nav", { id: "crumbs", class: "bar", "aria-label": "Levels" }),
    make("div", { id: "tools", class: "bar" }, ...(options.tools || []).map(([id, label]) => make("button", { id, class: "tool", type: "button" }, label)),
      make("button", { id: "claims", class: "tool", type: "button" }, "Claims"),
      make("button", { id: "search", class: "tool quiet", type: "button", title: options.placeholder }, "Search", make("kbd", {}, "/"))),
    make("aside", { id: "card", role: "tooltip" }), make("div", { id: "gloss", role: "tooltip" }), make("div", { id: "veil" }),
    make("div", { id: "palette", role: "dialog", "aria-label": "Search" },
      make("div", { id: "field" }, make("input", { id: "query", type: "text", placeholder: options.placeholder, autocomplete: "off", spellcheck: "false", role: "combobox",
        "aria-expanded": "true", "aria-controls": "hits", "aria-autocomplete": "list", "aria-label": "Search" }),
      make("button", { id: "regex", class: "tool icon quiet", type: "button", "aria-pressed": "false", "aria-label": "Regular expression", title: "Regular expression (Alt+R)" }, ".*")),
      make("div", { id: "hits", role: "listbox" }),
      make("footer", { id: "keys" }, make("span", {}, ...hint("↑", "↓"), " move"), make("span", {}, ...hint("↵"), " open"), make("span", {}, ...hint("esc"), " close"), make("span", {}, ...hint("alt", "R"), " regex"))));
  const claimsOn = id => (options.claims() || []).filter(claim => (claim.on || []).includes(id));
  const card = paperworkCard({ ...options, make, claimsOn });
  const browse = [...options.browse.filter(([, kind]) => kind !== "claim"), ...STATUSES.map(status => [`Claims: ${status}`, "claim", status, "Claims"])];
  const search = paperworkSearch({ ...options, make, browse });
  addEventListener("keydown", event => { if (search.key(event)) event.stopImmediatePropagation(); }, true); // an open palette, and the keys that open it, come before the page's own keys
  $("search").addEventListener("click", () => search.ask());
  $("claims").addEventListener("click", () => search.ask("Claims"));

  function crumbs(trail, pick) { // the way down from the first level to the shown one, each [id, title], the last the shown one, with each level's badges
    $("claims").hidden = !(options.claims() || []).length;
    $("crumbs").replaceChildren(...trail.flatMap(([id, title], k) => {
      const step = make("button", { type: "button", "data-level": id, ...(k === trail.length - 1 ? { "aria-current": "page" } : {}) }, title);
      step.addEventListener("click", () => pick(id));
      return [...(k ? [make("span", { class: "sep", "aria-hidden": "true" }, "/")] : []), step, card.badges(id)];
    }).filter(Boolean));
  }
  function entries() { // the search's entry of each claim, grouped by its status, and of each question, open when no answer settles it
    const claims = options.claims() || [], { words, bare, status } = card;
    return [...claims.map(claim => ({ id: claim.id, kind: "claim", name: claim.title, note: claim.kind, group: status(claim),
      fields: [[claim.title, 0], [claim.id, 1], [claim.kind, 2], [words(claim.statement), 3]], shown: [["kind", claim.kind], ["status", status(claim)], ["statement", bare(claim.statement)]] })),
    ...(options.questions() || []).map(question => ({ id: question.id, kind: "question", name: words(question.asks),
      note: question.answers.every(name => claims.some(claim => claim.id === name && claim.fault)) ? "open question" : "question",
      fields: [[words(question.asks), 0], [question.id, 1]], shown: [["id", question.id]] }))];
  }
  function rows(id) { // a claim's or a question's card rows, each naming the records it is about so the card leads back to each
    const { kind, record } = options.record(id), named = ids => (ids || []).map(one => `{${one}}`);
    if (kind === "claim") return [["statement", "text", record.statement], ["on", "list", named(record.on)], ...(record.fault ? [["fault", "text", record.fault]] : [])];
    if (kind === "question") return [["asks", "text", record.asks], ["answers", "list", named(record.answers)]];
    return [];
  }
  return { ...card, make, search, crumbs, entries, rows };
};
