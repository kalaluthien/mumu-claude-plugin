// The search palette of a paperwork page: a query ranked over the page's records by reciprocal rank fusion, read also as the keys of a
// Korean layout and through the terms' aliases, or a regular expression; recent queries kept per page. A page calls
// `paperworkSearch(options)` once its `#veil` and `#palette` exist, and hands each keydown to `key(event)` first:
//   make(name, attributes, ...children)  the element maker
//   entries()  each record as { id, kind, name, note, fields: [[text, place]], shown: [[field, text]] }, a field's place 0 for a name,
//              then 1 for an id, 2 for a tag, 3 for prose and 4 for details, its shown texts as a hit's excerpt draws them
//   kinds      the heading of each kind, in the order ties rank; browse: [heading, kind, group, under] groups an empty query lists,
//              each the entries of KIND whose `group` is GROUP when given, listed too by `ask(UNDER)` when given
//   terms()    the contract's terms; shelf(): the storage key of the page's recent queries
//   open(entry) the page moves to a picked record
window.paperworkSearch = options => {
  "use strict";
  const { make } = options;
  const $ = id => document.getElementById(id);
  const KINDS = options.kinds, ORDER = Object.keys(KINDS);
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
  const termed = query => (options.terms() || []).flatMap(term => (term.aliases || []).filter(alias => ` ${query} `.includes(` ${plain(alias)} `)).map(alias => [alias, term.term])); // the term aliases a query holds whole, each with its term
  const forms = query => { // a query read as typed and as the keys of a Korean layout, then each with its term aliases read as their terms
    const read = [plain(query), plain(typed(query))];
    return read.concat(read.filter(form => termed(form).length).map(form => termed(form).reduce((done, [alias, term]) => ` ${done} `.replace(` ${plain(alias)} `, ` ${plain(term)} `).trim(), form)));
  };
  const stem = word => word.length > 4 ? word.replace(/(ies|es|ed|ing|s|e)$/, "") : word;
  const RANKERS = { field: 6, quality: 3, bm25: .25, coverage: 1 }; // each ranker's weight in the fused rank, tuned by the mean reciprocal rank over the system skill's fixtures/ranking-queries.json
  function measure(entry, tokens, rare, partial) { // what each ranker reads of one record for one query, each the less the better; none for a record missing a word unless PARTIAL
    let field = 0, quality = 0, covered = 0, telling = 0;
    for (const token of tokens) { // the token's match in the first field it matches, the field ranked before the match
      let place = 5, grade = 7, size = 0;
      for (const one of entry.fields) { const got = match(token, one); if (got >= 0 && (one.place < place || one.place === place && got < grade)) { place = one.place; grade = got; size = one.text.length; } }
      if (grade === 7 && !partial) return null;
      covered += grade < 7 ? 1 : 0; telling += grade < 7 && !STOP.has(token) ? 1 : 0; field += place; quality += grade < 7 ? grade + 1 - token.length / Math.max(size, token.length) : grade; // within a grade, the more of the text the word covers the better
    }
    field /= tokens.length; quality /= tokens.length;
    if (tokens.length > 1) for (const one of entry.fields) { const got = match(tokens.join(" "), one); if (got >= 0) { field = Math.min(field, one.place); quality = Math.min(quality, got); } }
    let bm25 = 0;
    for (const [term, weight] of rare) { // BM25, k1 1.2 and b 0.75, over every text of the record
      const count = entry.terms.filter(word => word === term).length;
      bm25 += weight * count * 2.2 / (count + 1.2 * (.25 + .75 * entry.terms.length / lengths));
    }
    return { entry, covered, telling, field, quality, bm25: -bm25, coverage: -covered / tokens.length };
  }
  const STOP = new Set("a an and are as at be by for from has have how in is it its of on or that the this to was what when where which who why will with".split(" ")); // words nearly every text holds, so alone they tell no record apart
  function rank(query) { // the records a query finds, by reciprocal rank fusion of its rankers, k = 60
    const scored = new Map();
    slipping.clear();
    for (const form of new Set(forms(query))) {
      const tokens = form.split(" ").filter(Boolean);
      if (!tokens.length) continue;
      const rare = [...new Set(tokens.map(stem))].map(term => { const held = entries.filter(entry => entry.terms.includes(term)).length; return [term, Math.log(1 + (entries.length - held + .5) / (held + .5))]; });
      const told = tokens.some(token => !STOP.has(token));
      const pool = tokens.length < 3 ? entries.map(entry => measure(entry, tokens, rare, false)).filter(Boolean) // a sentence a person types seldom matches a record in every word, so the share of words ranks it
        : entries.map(entry => measure(entry, tokens, rare, true)).filter(row => told ? row.telling : row.covered || row.bm25 < 0);
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
  let entries = [], from = null, ready = [], lengths = 1;
  const prepared = () => { // each entry's fields as the search weighs them, made again only when the page's entries change
    const list = options.entries();
    if (list === from) return ready;
    from = list;
    ready = list.map(({ id, kind, name, note, group, fields, shown }) => ({ id, kind, name: name.replace(/`/g, ""), note, group,
      fields: fields.filter(([text]) => text).map(([text, place]) => ({ text: plain(text), tokens: plain(text).split(" "), place })), shown: shown.filter(([, text]) => text).map(([field, text]) => ({ field, text })) }));
    for (const entry of ready) entry.terms = entry.fields.flatMap(field => field.tokens).map(stem);
    lengths = ready.reduce((sum, entry) => sum + entry.terms.length, 0) / Math.max(1, ready.length);
    return ready;
  };
  const recalled = () => { // the last queries a pick was made from, each with its mode, the tab's own once the storage throws
    if (!memory) try { return JSON.parse(localStorage.getItem(options.shelf()) || "[]").map(one => typeof one === "string" ? { text: one, regex: false } : one); } catch { memory = []; }
    return memory;
  };
  const remember = queries => {
    if (!memory) try { return localStorage.setItem(options.shelf(), JSON.stringify(queries)); } catch { memory = queries; }
    memory = queries;
  };
  const CLOCK = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>';
  const CROSS = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M18 6 6 18M6 6l12 12"/></svg>';
  function list() {
    const query = $("query").value.trim(), box = $("hits"), input = $("query");
    entries = prepared();
    box.replaceChildren();
    const typing = regular ? [] : [...new Set(forms(query))].map(form => form.split(" ").filter(Boolean)), tokens = [...new Set(typing.flat())]; // a query read as typed and as the keys of a Korean layout
    const asked = regular && query ? sought() : {}, theirs = regular ? [] : termed(plain(query));
    const find = text => asked.pattern ? matches(text, asked.pattern) : spans(text, tokens);
    const found = !query || asked.error ? [] : (asked.pattern ? grep(asked.pattern) : rank(query)).slice(0, 8);
    const before = scope ? [] : recalled().filter(({ text }) => !query || text.toLowerCase().startsWith(query.toLowerCase()) && text.length > query.length).map(one => ({ recent: one.text, regex: one.regex }));
    const groups = [["Recent", before], ...(query ? [...new Set(found.map(entry => entry.kind))].map(kind => [KINDS[kind], found.filter(entry => entry.kind === kind)])
      : options.browse.filter(([title, , , under]) => !scope || (under || title) === scope).map(([title, kind, group]) => [title, entries.filter(entry => entry.kind === kind && (!group || entry.group === group))]))];
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
          row.addEventListener("click", event => event.target.closest(".forget") ? forget(item) : recall(item));
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
  const same = (one, item) => one.text.toLowerCase() === item.recent.toLowerCase(); // one row per text, kept in the mode it last ran in
  function recall(item) { $("query").value = item.recent; regex(item.regex); }
  function forget(item) { remember(recalled().filter(one => !same(one, item))); $("query").focus(); list(); }
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
    if (entry.recent) return recall(entry);
    if (query && document.body.dataset.palette) remember([{ text: query, regex: regular }, ...recalled().filter(one => !same(one, { recent: query, regex: regular }))].slice(0, 8));
    shut();
    options.open(entry);
  }
  function key(event) { // whether the palette took the key: every key while it is open, and the keys that open it
    if (document.body.dataset.palette) {
      if (event.key === "Escape") shut();
      else if (event.altKey && event.code === "KeyR") regex(!regular); // by the key's place, since Option on a Mac turns R into another letter
      else if (event.key === "ArrowDown" || event.key === "ArrowUp") { chosen = (chosen + (event.key === "ArrowDown" ? 1 : listed.length - 1)) % Math.max(1, listed.length); list(); }
      else if (event.key === "Enter" && listed[chosen] && !event.target.closest("button")) pick(listed[chosen]); // a focused button takes its own Enter
      else return true;
      event.preventDefault();
      return true;
    }
    if ((event.key === "k" && (event.metaKey || event.ctrlKey)) || (event.key === "/" && !event.metaKey && !event.ctrlKey)) { event.preventDefault(); ask(); return true; }
    return false;
  }
  $("veil").addEventListener("click", shut);
  $("query").addEventListener("input", () => { chosen = -1; list(); });
  $("regex").addEventListener("click", () => regex(!regular));
  return { ask, key };
};
