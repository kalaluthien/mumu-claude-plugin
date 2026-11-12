(() => {
  const base = location.pathname.replace(/[^/]*$/, "");
  const store = sessionStorage;
  const key = (name) => `page-threads:${location.pathname}:${name}`;
  let state = { threads: {} };
  const block = document.getElementById("page-threads");
  const post = (route, body) => fetch(base + route, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  try {
    if (block) state = JSON.parse(block.textContent);
  } catch (error) {
    post("error", { text: `the page-threads block does not parse: ${error.message}` });
  }
  state.threads = state.threads || {};
  const sentinel = (entry) => entry.by === "sentinel";
  const stamps = window.pageThreadsStamps || {};
  const named = new URLSearchParams(location.search).get("as");
  if (named) store.setItem(key("author"), named.trim().slice(0, 40) || "owner");
  const author = () => store.getItem(key("author")) || "owner";
  const localTime = () => new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 19);
  const VALID = /^[\p{L}\p{N}_.:-]{1,80}$/u;
  function derive() {
    const taken = new Set([...document.querySelectorAll("[data-thread-anchor]")].map((element) => element.dataset.threadAnchor));
    for (const element of document.querySelectorAll("section[id], article[id], figure[id], table[id], h1, h2, h3")) {
      if (element.dataset.threadAnchor || element.closest("[data-thread-anchor]")?.matches("section, article")) continue;
      const title = (element.querySelector("h1, h2, h3") || element).textContent.normalize("NFC").trim();
      const words = [...title.toLowerCase().replace(/[^\p{L}\p{N}]+/gu, "-").replace(/^-|-$/g, "")].slice(0, 60).join("");
      const first = VALID.test(element.id) ? element.id : words ? `h-${words}` : "h";
      let slug = first;
      for (let n = 2; taken.has(slug); n += 1) slug = `${first}-${n}`;
      taken.add(slug);
      element.dataset.threadAnchor = slug;
      if (!element.getAttribute("aria-label")) element.dataset.threadLabel = title.slice(0, 60);
    }
  }
  derive();

  const style = document.createElement("style");
  style.textContent = `
    #page-threads-layer { position: absolute; left: 0; top: 0; width: 0; height: 0; z-index: 2147483000; }
    #page-threads-layer button { position: absolute; font: 12px sans-serif; border: 1px solid #345; border-radius: 10px; background: #fff; cursor: pointer; padding: 1px 6px; }
    #page-threads-layer button[data-status=waiting], #page-threads-layer button[data-status=working] { background: #fff3c4; }
    #page-threads-layer button[data-status=asks] { background: #ffd9d9; }
    #page-threads-panel { position: fixed; right: 0; top: 0; bottom: 0; width: 360px; background: #fff; border-left: 1px solid #bbb; padding: 12px; overflow: auto; font: 14px sans-serif; z-index: 2147483001; box-shadow: -2px 0 8px #0002; }
    #page-threads-panel[hidden] { display: none; }
    #page-threads-gone { position: fixed; left: 8px; bottom: 8px; max-height: 50vh; overflow: auto; background: #fff; border: 1px solid #345; border-radius: 8px; padding: 4px 8px; font: 12px sans-serif; z-index: 2147483000; }
    #page-threads-gone[hidden] { display: none; }
    #page-threads-gone button { display: block; margin: 4px 0; font: inherit; cursor: pointer; }
    #page-threads-panel ol { list-style: none; padding-left: 0; margin: 0; }
    #page-threads-panel ol ol { padding-left: 14px; border-left: 2px solid #ddd; }
    #page-threads-panel li { margin: 6px 0; }
    #page-threads-panel li[data-by=sentinel] > b { color: #276; }
    #page-threads-panel .meta { color: #777; font-size: 12px; }
    #page-threads-panel textarea { width: 100%; box-sizing: border-box; }
    #page-threads-panel header { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
  `;
  document.head.appendChild(style);
  const layer = document.createElement("div");
  layer.id = "page-threads-layer";
  document.body.appendChild(layer);
  const shelf = document.createElement("details");
  shelf.id = "page-threads-gone";
  shelf.hidden = true;
  document.body.appendChild(shelf);
  const panel = document.createElement("aside");
  panel.id = "page-threads-panel";
  panel.hidden = true;
  document.body.appendChild(panel);

  function status(thread) {
    if (thread.some((entry) => sentinel(entry) && entry.ask && !entry.answered)) return "asks";
    const last = [...thread].reverse().find((entry) => !sentinel(entry) && !entry.quiet);
    const replies = last ? thread.filter((entry) => sentinel(entry) && entry.replies_to === last.id) : [];
    if (last && !replies.some((entry) => !entry.working)) return replies.length ? "working" : "waiting";
    const note = [...thread].reverse().find((entry) => !sentinel(entry) && entry.quiet);
    const after = (entry) => !stamps[String(entry.id)] || stamps[String(entry.id)] >= note.at;
    if (note && !thread.some((entry) => sentinel(entry) && !entry.working && after(entry))) return "quiet";
    return thread.length ? "answered" : "none";
  }

  const shown = (element) => {
    const box = element.getBoundingClientRect();
    return !("threadGone" in element.dataset) && Boolean(box.width || box.height) && box.right + scrollX > 0 && box.bottom + scrollY > 0 && getComputedStyle(element).visibility !== "hidden";
  };
  const layout = () => [...document.querySelectorAll("[data-thread-anchor]")].filter(shown).map((element) => {
    const box = element.getBoundingClientRect();
    return `${element.dataset.threadAnchor}:${Math.round(box.right + scrollX)},${Math.round(box.top + scrollY)},${Math.round(box.width)},${Math.round(box.height)}`;
  }).join(" ") + " | " + gone().join(" ");
  let placed = "";
  // a thread outlives its part when an edit removes or renames it, so the page lists it instead of losing it
  const gone = () => {
    const live = new Set([...document.querySelectorAll("[data-thread-anchor]:not([data-thread-gone])")].map((element) => element.dataset.threadAnchor));
    return Object.keys(state.threads).filter((anchor) => (state.threads[anchor] || []).length && !live.has(anchor));
  };

  function badges() {
    placed = layout();
    layer.innerHTML = "";
    for (const element of document.querySelectorAll("[data-thread-anchor]")) {
      const anchor = element.dataset.threadAnchor;
      const thread = state.threads[anchor] || [];
      const box = element.getBoundingClientRect();
      if (!shown(element)) continue;
      const button = document.createElement("button");
      button.type = "button";
      button.dataset.anchor = anchor;
      button.dataset.status = status(thread);
      button.textContent = thread.length ? `💬 ${thread.length}` : "💬";
      button.title = `comment on ${anchor}`;
      button.style.left = `${box.right + scrollX - 14}px`;
      button.style.top = `${box.top + scrollY - 10}px`;
      button.addEventListener("click", (event) => { event.stopPropagation(); open(anchor); });
      layer.appendChild(button);
    }
    const lost = gone();
    const was = shelf.open;
    shelf.hidden = !lost.length;
    shelf.innerHTML = `<summary>💬 ${lost.length} thread${lost.length === 1 ? "" : "s"} of parts no longer on the page</summary>`;
    shelf.open = was;
    for (const anchor of lost) {
      const button = document.createElement("button");
      button.type = "button";
      button.dataset.anchor = anchor;
      button.textContent = `💬 ${state.threads[anchor].length} ${anchor}`;
      button.addEventListener("click", () => open(anchor));
      shelf.appendChild(button);
    }
  }

  let selection = JSON.parse(store.getItem(key("selection")) || "null");
  document.addEventListener("mouseup", (event) => {
    const chosen = getSelection();
    const start = chosen && chosen.rangeCount ? chosen.getRangeAt(0).startContainer : null;
    const anchor = start && (start.nodeType === 1 ? start : start.parentElement)?.closest("[data-thread-anchor]");
    if (!anchor || !String(chosen).trim()) {
      // a click in the panel or on a badge drops the browser's selection on the way to commenting on it; one on the page itself lets it go
      const within = event.target instanceof Element && event.target.closest("#page-threads-panel, #page-threads-layer, #page-threads-gone");
      if (!String(chosen).trim() && !within) {
        selection = null;
        store.removeItem(key("selection"));
      }
      return;
    }
    selection = { anchor: anchor.dataset.threadAnchor, text: String(chosen).trim().slice(0, 500) };
    store.setItem(key("selection"), JSON.stringify(selection));
  });

  function since(at) {
    const seconds = Math.round((Date.now() - Date.parse(at)) / 1000);
    return Number.isFinite(seconds) ? seconds : 0;
  }

  function open(anchor) {
    store.setItem(key("open"), anchor);
    draw();
  }

  function draw() {
    const anchor = store.getItem(key("open"));
    const element = anchor && document.querySelector(`[data-thread-anchor="${CSS.escape(anchor)}"]:not([data-thread-gone])`);
    if (!anchor || !(element || (state.threads[anchor] || []).length)) { panel.hidden = true; return; }
    panel.hidden = false;
    const thread = state.threads[anchor] || [];
    panel.innerHTML = `<header><b class="title"></b><span><button type="button" class="undo">Undo last change</button> <button type="button" class="close">×</button></span></header>
      <p class="meta state"></p><ol class="messages"></ol>
      <form><textarea name="text" rows="3" placeholder="Comment, or ask the sentinel"></textarea><button type="submit">Send</button> <span class="sent meta"></span>
      <label class="meta">as <input name="author" size="10"></label></form>`;
    const name = panel.querySelector("input[name=author]");
    name.value = author();
    name.addEventListener("change", () => store.setItem(key("author"), name.value.trim().slice(0, 40) || "owner"));
    panel.querySelector(".title").textContent = element ? element.getAttribute("aria-label") || element.dataset.threadLabel || anchor : `${anchor} (its part is no longer on the page)`;
    const current = status(thread);
    const last = [...thread].reverse().find((entry) => !sentinel(entry) && !entry.quiet);
    const words = { none: "No comments yet.", answered: "Answered.", quiet: "Noted for the page; the sentinel is told only of a comment that names @sentinel.", asks: "The sentinel asks you to choose.", working: "The sentinel is working on it.",
      waiting: last && since(last.at) > 120 ? `No answer after ${since(last.at)} s: the sentinel may be stopped.` : "Sent; waiting for the sentinel." };
    const line = panel.querySelector(".state");
    line.dataset.status = current;
    line.textContent = words[current];
    const list = panel.querySelector(".messages");
    const ids = new Set(thread.map((entry) => entry.id));
    const children = (id) => thread.filter((entry) => entry.replies_to === id && entry.id !== id);
    const add = (entry, into) => {
      const item = document.createElement("li");
      item.dataset.by = sentinel(entry) ? "sentinel" : entry.by;
      item.dataset.message = entry.id;
      item.innerHTML = "<b></b> <span class=text></span> <span class=meta></span>";
      item.querySelector("b").textContent = entry.by;
      item.querySelector(".text").textContent = entry.text;
      const at = sentinel(entry) ? stamps[String(entry.id)] : entry.at;
      item.querySelector(".meta").textContent = (at ? at.slice(11, 16) : "") + (entry.quiet ? " noted, not sent to the sentinel" : "");
      if (sentinel(entry) && entry.ask && Array.isArray(entry.ask.options)) {
        const choices = document.createElement("div");
        choices.className = "choices";
        for (const option of entry.ask.options) {
          const button = document.createElement("button");
          button.type = "button";
          button.dataset.option = option;
          button.textContent = option;
          button.disabled = !!entry.answered;
          button.addEventListener("click", () => send(anchor, option, entry.id));
          choices.appendChild(button);
        }
        item.appendChild(choices);
      }
      if (sentinel(entry) && entry.proposal) {
        const box = document.createElement("div");
        box.className = "proposal";
        box.innerHTML = `<a target="_blank">Preview</a> <button type="button" data-verdict="accept">Accept</button> <button type="button" data-verdict="reject">Reject</button> <span class="meta"></span>`;
        box.querySelector("a").href = `${base}?proposal=${encodeURIComponent(entry.id)}`;
        box.querySelector(".meta").textContent = entry.decided ? `${entry.decided}ed` : "";
        for (const button of box.querySelectorAll("button")) {
          button.disabled = !!entry.decided;
          button.addEventListener("click", async () => {
            const response = await post("decide", { reply: entry.id, verdict: button.dataset.verdict });
            box.querySelector(".meta").textContent = response.ok ? "sent" : (await response.text()) || `refused ${response.status}`;
          });
        }
        item.appendChild(box);
      }
      into.appendChild(item);
      const replies = children(entry.id);
      if (replies.length) {
        const nested = document.createElement("ol");
        item.appendChild(nested);
        replies.forEach((reply) => add(reply, nested));
      }
    };
    thread.filter((entry) => entry.replies_to == null || !ids.has(entry.replies_to)).forEach((entry) => add(entry, list));
    const field = panel.querySelector("textarea");
    field.value = store.getItem(key(`draft:${anchor}`)) || "";
    field.addEventListener("input", () => store.setItem(key(`draft:${anchor}`), field.value));
    if (store.getItem(key("focus"))) {
      store.removeItem(key("focus"));
      field.focus();
      field.setSelectionRange(field.value.length, field.value.length);
    }
    panel.querySelector("form").addEventListener("submit", (event) => { event.preventDefault(); send(anchor, field.value, null); });
    panel.querySelector(".close").addEventListener("click", () => { store.removeItem(key("open")); panel.hidden = true; });
    panel.querySelector(".undo").addEventListener("click", async () => {
      const response = await post("undo", {});
      panel.querySelector(".sent").textContent = response.ok ? "undo sent" : `nothing to undo (${response.status})`;
    });
  }

  async function send(anchor, text, repliesTo) {
    const element = document.querySelector(`[data-thread-anchor="${CSS.escape(anchor)}"]`);
    const response = await post("comment", {
      anchor, text, replies_to: repliesTo, author: author(),
      selection: selection && selection.anchor === anchor ? selection.text : null,
      element: element ? element.outerHTML.slice(0, 2000) : null,
    });
    if (response.ok) {
      if (repliesTo == null) store.removeItem(key(`draft:${anchor}`));
      if (selection && selection.anchor === anchor) {
        selection = null;
        store.removeItem(key("selection"));
      }
      const id = Number(await response.text());
      const by = author();
      const thread = state.threads[anchor] = state.threads[anchor] || [];
      if (!thread.some((entry) => entry.id === id)) {
        thread.push({ id, by, text, replies_to: repliesTo, at: localTime(), quiet: by !== "owner" && !/@sentinel\b/.test(text) });
      }
      const asked = [...thread].reverse().find((entry) => sentinel(entry) && entry.ask && !entry.answered && (repliesTo == null ? by === "owner" : entry.id === repliesTo));
      if (asked) asked.answered = text;
      draw();
      badges();
    }
    const sent = panel.querySelector(".sent");
    if (sent) sent.textContent = response.ok ? "sent" : `refused ${response.status}`;
  }

  window.pageThreads = { open, state };
  const restore = Number(store.getItem(key("scroll")));
  if (restore) scrollTo(0, restore);
  addEventListener("scroll", () => store.setItem(key("scroll"), String(scrollY)));
  addEventListener("resize", badges);
  addEventListener("hashchange", badges);
  badges();
  draw();
  setInterval(() => {
    if (panel.hidden || panel.contains(document.activeElement)) return;
    if (status(state.threads[store.getItem(key("open"))] || []) === "waiting") draw();
  }, 5000);

  let version = null;
  const poll = async () => {
    try {
      const now = await (await fetch(base + "version", { cache: "no-store" })).text();
      if (version !== null && now !== version) {
        const field = panel.querySelector("textarea");
        if (field && document.activeElement === field) {
          store.setItem(key(`draft:${store.getItem(key("open"))}`), field.value);
          store.setItem(key("focus"), "1");
        }
        location.reload();
        return;
      }
      version = now;
    } catch (error) {}
    derive();
    if (layout() !== placed) badges();
    setTimeout(poll, 500);
  };
  poll();
})();
