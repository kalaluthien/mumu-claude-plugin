(() => {
  const served = /^https?:$/.test(location.protocol);
  const key = (name) => `relay:${location.pathname}:${name}`;
  const recall = (name) => { try { return sessionStorage.getItem(key(name)); } catch (error) { return null; } };
  const remember = (name, value) => {
    try { if (value) sessionStorage.setItem(key(name), value); else sessionStorage.removeItem(key(name)); } catch (error) {}
  };
  const api = (route) => new URL(route, location.href).href;
  const readBlock = (id) => {
    const block = document.getElementById(id);
    if (!block) return null;
    try { return JSON.parse(block.textContent); } catch (error) { console.warn(`relay: #${id} is not JSON`, error); return null; }
  };
  const isObject = (value) => value !== null && typeof value === "object" && !Array.isArray(value);
  const data = readBlock("page-data");
  window.pageData = isObject(data) ? data : {};
  const threadState = readBlock("page-threads");
  const threads = isObject(threadState) && isObject(threadState.threads) ? threadState.threads : {};
  window.relayChanges = [];
  let pending = [];
  // kept in sessionStorage, so a change made while the server is down survives a reload and is sent on the next connect
  let unsent = [];
  try { unsent = JSON.parse(recall("unsent") || "[]"); } catch (error) {}
  if (!Array.isArray(unsent)) unsent = [];
  const keepUnsent = () => remember("unsent", unsent.length ? JSON.stringify(unsent) : null);
  let flushing = false;
  let connection = served ? "connecting to the server" : "opened as file";
  let ui, layer, panel, bar;

  window.recordChange = (kind, target, payload) => {
    const change = { kind, target, payload, ts: new Date().toISOString() };
    window.relayChanges.push(change);
    if (served) { unsent.push(change); keepUnsent(); draw(); flush(); } else { pending = window.relayChanges; draw(); }
    return change;
  };

  async function flush() {
    if (flushing) return;
    flushing = true;
    while (unsent.length) {
      const change = unsent[0];
      try {
        const response = await fetch(api("api/changes"), {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ kind: change.kind, target: change.target, payload: change.payload }),
        });
        if (response.ok) Object.assign(change, await response.json());
        else change.refused = response.status;
      } catch (error) { break; }
      unsent.shift();
      keepUnsent();
    }
    flushing = false;
    await loadPending();
  }

  async function loadPending() {
    try {
      const response = await fetch(api("api/changes"), { cache: "no-store" });
      if (response.ok) pending = await response.json();
    } catch (error) {}
    draw();
  }

  const waiting = (anchor) => pending.concat(unsent).filter((change) => change.kind === "comment" && change.target === anchor);
  const anchors = () => [...document.querySelectorAll("[data-id]")].filter((element) => !ui.contains(element));

  // a badge is updated in place, never rebuilt, since a redraw between a press and its release would drop the click
  function placeBadges() {
    const old = new Map([...layer.children].map((badge) => [badge.dataset.anchor, badge]));
    for (const element of anchors()) {
      const box = element.getBoundingClientRect();
      if (!box.width && !box.height) continue;
      const anchor = element.getAttribute("data-id");
      const count = (Array.isArray(threads[anchor]) ? threads[anchor].length : 0) + waiting(anchor).length;
      let badge = old.get(anchor);
      old.delete(anchor);
      if (!badge) {
        badge = document.createElement("button");
        badge.type = "button";
        badge.dataset.anchor = anchor;
        badge.title = `Comment on ${anchor}`;
        badge.addEventListener("click", (event) => { event.stopPropagation(); remember("open", anchor); drawPanel(); });
        layer.appendChild(badge);
      }
      const text = count ? `\u{1F4AC} ${count}` : "\u{1F4AC}";
      if (badge.textContent !== text) badge.textContent = text;
      badge.style.left = `${box.right + scrollX - 12}px`;
      badge.style.top = `${box.top + scrollY - 10}px`;
    }
    old.forEach((badge) => badge.remove());
  }

  function entryItem(entry, by, text, note) {
    const item = document.createElement("li");
    item.dataset.by = by;
    item.innerHTML = "<b></b> <span class=text></span> <span class=meta></span>";
    item.querySelector("b").textContent = by;
    item.querySelector(".text").textContent = text;
    item.querySelector(".meta").textContent = note;
    if (entry) item.dataset.entry = entry;
    return item;
  }

  function drawPanel() {
    const anchor = recall("open");
    panel.hidden = !anchor;
    if (!anchor) return;
    const typing = document.activeElement && panel.contains(document.activeElement);
    const thread = Array.isArray(threads[anchor]) ? threads[anchor].filter(isObject) : [];
    panel.innerHTML = `<header><b class=title></b><button type=button class=close aria-label=Close>×</button></header>
      <ol class=thread></ol><form><textarea rows=3 placeholder="Comment on this part"></textarea><button type=submit>Send</button></form>`;
    panel.querySelector(".title").textContent = anchor;
    const list = panel.querySelector(".thread");
    const ids = new Set(thread.map((entry) => String(entry.id)));
    const add = (entry, into) => {
      const item = entryItem(String(entry.id), String(entry.by), String(entry.text), "");
      into.appendChild(item);
      const replies = thread.filter((each) => each !== entry && each.replies_to != null && String(each.replies_to) === String(entry.id));
      if (!replies.length) return;
      const nested = document.createElement("ol");
      item.appendChild(nested);
      replies.forEach((reply) => add(reply, nested));
    };
    thread.filter((entry) => entry.replies_to == null || !ids.has(String(entry.replies_to))).forEach((entry) => add(entry, list));
    for (const change of waiting(anchor)) {
      const item = entryItem(change.id == null ? "" : String(change.id), "you", String(change.payload && change.payload.text), unsent.includes(change) ? "not sent" : "waiting");
      item.classList.add("waiting");
      list.appendChild(item);
    }
    const field = panel.querySelector("textarea");
    field.value = recall(`draft:${anchor}`) || "";
    field.addEventListener("input", () => remember(`draft:${anchor}`, field.value));
    if (typing) {
      field.focus();
      field.setSelectionRange(field.value.length, field.value.length);
    }
    panel.querySelector("form").addEventListener("submit", (event) => {
      event.preventDefault();
      if (!field.value.trim()) return;
      window.recordChange("comment", anchor, { text: field.value });
      remember(`draft:${anchor}`, null);
      field.value = "";
    });
    panel.querySelector(".close").addEventListener("click", () => { remember("open", null); panel.hidden = true; });
  }

  function drawStatus() {
    bar.querySelector(".state").textContent = `${connection} · ${pending.length} pending` + (unsent.length ? `, ${unsent.length} not sent` : "");
    bar.querySelector(".export").hidden = served && !unsent.length;
  }

  function draw() {
    if (!ui) return;
    placeBadges();
    drawPanel();
    drawStatus();
  }

  function exportChanges() {
    const link = document.createElement("a");
    link.href = URL.createObjectURL(new Blob([JSON.stringify(served ? unsent : window.relayChanges, null, 2)], { type: "application/json" }));
    link.download = "changes.json";
    link.click();
    setTimeout(() => URL.revokeObjectURL(link.href), 1000);
  }

  function start() {
    const style = document.createElement("style");
    style.textContent = `
      #relay-ui { position: absolute; left: 0; top: 0; width: 0; height: 0; z-index: 2147483000; font: 13px sans-serif; }
      #relay-ui .layer button { position: absolute; font: 12px sans-serif; border: 1px solid #345; border-radius: 10px; background: #fff; cursor: pointer; padding: 1px 6px; }
      #relay-ui aside { position: fixed; right: 0; top: 0; bottom: 0; width: 340px; background: #fff; border-left: 1px solid #bbb; padding: 12px; overflow: auto; box-shadow: -2px 0 8px #0002; }
      #relay-ui aside[hidden] { display: none; }
      #relay-ui header { display: flex; justify-content: space-between; align-items: center; }
      #relay-ui ol { list-style: none; padding-left: 0; }
      #relay-ui ol ol { padding-left: 14px; border-left: 2px solid #ddd; }
      #relay-ui li { margin: 6px 0; }
      #relay-ui li[data-by=session] > b { color: #276; }
      #relay-ui li.waiting { background: #fff3c4; }
      #relay-ui .meta { color: #777; font-size: 12px; }
      #relay-ui textarea { width: 100%; box-sizing: border-box; }
      #relay-ui .bar { position: fixed; left: 8px; bottom: 8px; background: #fff; border: 1px solid #345; border-radius: 8px; padding: 4px 8px; display: flex; gap: 8px; align-items: center; }
    `;
    document.head.appendChild(style);
    ui = document.createElement("div");
    ui.id = "relay-ui";
    ui.innerHTML = "<div class=layer></div><aside hidden></aside><div class=bar><span class=state></span></div>";
    layer = ui.querySelector(".layer");
    panel = ui.querySelector("aside");
    bar = ui.querySelector(".bar");
    document.body.appendChild(ui);
    const button = document.createElement("button");
    button.type = "button";
    button.className = "export";
    button.textContent = "Export changes";
    button.addEventListener("click", exportChanges);
    bar.appendChild(button);
    if (typeof window.pageRender === "function") {
      try { window.pageRender(window.pageData); } catch (error) { console.error("relay: pageRender failed", error); }
    }
    let scheduled = false;
    const later = () => {
      if (scheduled) return;
      scheduled = true;
      requestAnimationFrame(() => { scheduled = false; placeBadges(); });
    };
    new MutationObserver((records) => { if (records.some((record) => !ui.contains(record.target))) later(); })
      .observe(document.body, { childList: true, subtree: true, attributes: true, characterData: true });
    addEventListener("resize", later);
    draw();
    if (!served) return;
    if (!window.EventSource) return flush();
    const events = new EventSource(api("api/events"));
    // each connect reads the queue again, since an ack while the stream was down sends no `changes` event
    events.addEventListener("open", () => { connection = "server connected"; flush(); });
    events.addEventListener("error", () => { connection = "server not reachable"; drawStatus(); });
    events.addEventListener("reload", () => location.reload());
    events.addEventListener("changes", loadPending);
  }

  const safeStart = () => { try { start(); } catch (error) { console.error("relay: runtime failed", error); } };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", safeStart);
  else safeStart();
})();
