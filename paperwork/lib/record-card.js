// The record card of a paperwork page with its badges: a record's rows drawn as prose with its quotes, formulas, named records, terms and
// guesses, paged to the room beside the record, and the note over the card that a term or the sources raise. A page calls
// `paperworkCard(options)` once its `#card` and `#gloss` exist; each option is a function it answers from its own records:
//   make(name, attributes, ...children)  the element maker
//   record(id)       { kind, record } of a record, or nothing
//   terms()          the contract's terms; sources() its sources; counted() each record's properties by the kind a badge counts
//   formulas         the MathML of each formula, by `$tex` or `$$tex`
//   rows(id)         the card's rows, each [name, form, data]
//   place(id, w, h)  { left, top, cost, tied } where a card that big rests, `tied` what it still covers
//   kept(id)         whether the card is kept open
//   light(id)        mark in the drawing the record a chip names, or nothing for null
//   follow(id, event) a click on a chip: true when the page moved for it, so the card does nothing more
window.paperworkCard = options => {
  "use strict";
  const { make, formulas } = options;
  const $ = id => document.getElementById(id);
  let termsFrom = null, patterns = [];
  const terms = () => { // each term's pattern, made again only when the contract's terms change
    const list = options.terms() || [];
    if (list === termsFrom) return patterns;
    termsFrom = list;
    patterns = list.map(entry => ({ entry, pattern: new RegExp(String.raw`(?<![\p{L}\p{N}./-])` + entry.term.trim().split(/\s+/).map(word => word.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join(String.raw`\s+`)
      + (/[가-힣]$/.test(entry.term) ? "" : String.raw`(?:e?s)?(?![\p{L}\p{N}-]|[./][\p{L}\p{N}])`), "iu") })); // a Korean term takes a particle after it; a file name is no term
    return patterns;
  };
  const label = id => options.record(id) ? (options.record(id).record.label || options.record(id).record.title || id) : id;
  // a quote, a formula or a named record in a text; the formula's pattern is tex_mathml.py's, which make-page.py drew each one by
  const MARKS = /(```[\s\S]*?```|`[^`]+`)|\$\$([^$`]+?)\$\$|\$(?!\{[A-Z_]+\})([^\s$`](?:[^$`]*?[^\s$`])?)\$(?!\d)|\{([a-z0-9-]+)\}/g;
  const words = text => String(text).replace(MARKS, (whole, quote, block, inline, id) => (id && options.record(id) ? label(id) : whole));
  const bare = text => words(text).replace(/`([^`]+)`/g, "$1"); // text drawn where no code face can show, such as a tooltip, keeps a code span's words without its marks
  const tagName = tag => String(tag).replace(/[A-Z]/g, letter => " " + letter.toLowerCase()); // a tag's id as the words it joins
  const COUNTS = [["holds", "✓", "holds"], ["unknown", "?", "unknown"], ["broken", "✗", "broken"], ["gap", "!", "gaps"]]; // each kind a badge counts: its symbol, so it reads without its colour, and its card row's name
  const counts = id => { // the badges of a record the properties on it earn, one per kind it holds
    const held = options.counted()[id] || {}, shown = COUNTS.filter(([kind]) => held[kind]);
    if (!shown.length) return null;
    return make("span", { class: "counts", "data-for": id }, ...shown.map(([kind, symbol, name]) =>
      make("span", { class: "count", "data-count": kind, "aria-label": `${held[kind].length} ${name}` }, symbol + held[kind].length)));
  };
  const countRows = id => COUNTS.filter(([kind]) => (options.counted()[id] || {})[kind]).map(([kind, , name]) => [name, "list", options.counted()[id][kind].map(one => `{${one}}`)]); // a card's row per kind of badge its record earns
  const quoted = text => words(text).split(/(`[^`]+`)/).filter(Boolean).map(part => part[0] === "`" ? make("em", {}, part.slice(1, -1)) : part); // a code span inside code has no code face to take, so it reads as a literal term
  let glossed = new Set(); // the terms the card has marked, each at its first match only
  const spoken = piece => { // a run of prose: a `(guess)` as a badge, and the first match of each term the card has not marked as a term
    const guess = piece.search(/\(guess\)/i);
    let first = null;
    for (const one of terms()) if (!glossed.has(one.entry.term)) { const found = one.pattern.exec(piece); if (found && (!first || found.index < first.found.index)) first = { one, found }; }
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
    const markup = formulas[(display ? "$$" : "$") + tex];
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
      if (id && !options.record(id)) continue;
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
  let leaf = 0; // the page of rows the card shows
  function card(id) { // one card for a record, the same under the pointer and kept, its rows over pages its height holds
    const { kind, record } = options.record(id), box = $("card"), kept = options.kept(id), all = options.rows(id);
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
      const first = Math.min(box.offsetHeight, limit), place = options.place(id, box.offsetWidth, first), bottom = place.top + first, cap = Math.min(limit, bottom - 8);
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
    const [source, line] = entry.split(":"), known = (options.sources() || []).find(one => one.id === source);
    return make("div", { class: "source" }, make("code", {}, (known ? known.path : source) + (line ? ":" + line : "")), ...(known && known.says ? [make("blockquote", {}, words(known.says))] : []));
  });
  function hide() {
    unGloss();
    options.light(null);
    $("card").classList.remove("show"); $("card").dataset.for = "";
  }
  $("card").addEventListener("pointerover", event => {
    const chip = event.target.closest(".ref"), term = event.target.closest(".term");
    if (chip) options.light(chip.dataset.ref);
    if (term) gloss(term, make("strong", {}, term.dataset.term), make("p", {}, ...prose(term.dataset.meaning, true)));
  });
  $("card").addEventListener("pointerout", event => {
    if (event.target.closest(".ref") && !(event.relatedTarget && event.relatedTarget.closest && event.relatedTarget.closest(".ref"))) options.light(null);
    if (event.target.closest(".term")) unGloss();
  });
  $("card").addEventListener("click", event => {
    const named = event.target.closest(".ref");
    if (named && options.follow(named.dataset.ref, event)) return;
    const cite = event.target.closest(".cite"), shown = $("gloss").classList.contains("show") && $("gloss").dataset.for === $("card").dataset.for;
    if (!cite || shown) return unGloss();
    gloss(cite, ...sources(options.record($("card").dataset.for).record));
    $("gloss").dataset.for = $("card").dataset.for;
  });
  return { MARKS, words, bare, tagName, label, counts, countRows, prose, show: card, hide };
};
