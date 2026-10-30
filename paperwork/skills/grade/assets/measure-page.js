// Each page fact as null or what broke it; make-page.py --check passes what the data says the page must hold.
want => {
  const all = selector => [...document.querySelectorAll(selector)];
  const text = document.querySelector("main").innerText;
  const bottom = element => element.getBoundingClientRect().bottom;
  const ids = selector => all(selector).map(e => e.dataset.criterion);
  const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
  const firstScreen = [...all(".rating"), ...all("li.critical"), ...all("ol.fixes li").slice(0, 1)];
  const folds = all("details");
  const judged = all(".crit[data-runs]");
  const fixShown = want.fixes.filter(fix => text.split(fix).length !== 2);
  const unlinked = all("li[id^='fix-']").map(e => e.id).filter(id => !document.querySelector(`.crit a[href="#${id}"]`));
  const personTop = document.querySelector("#needs-person").getBoundingClientRect().top;
  const fixTop = document.querySelector("#fix-first").getBoundingClientRect().top;
  return {
    "first screen": firstScreen.every(e => bottom(e) <= 900) ? null : `ends at ${Math.max(...firstScreen.map(bottom))} px`,
    "run counts": judged.every(e => e.querySelectorAll(".dots i").length === Number(e.dataset.runs) && e.querySelector(".runs").innerText.includes(` of ${e.dataset.runs} `)) && judged.length === want.judged && !/accuracy/i.test(text) ? null : "a card's dots or count differ from its runs",
    "needs a person": same(ids("ol.person li"), want.person) && personTop < fixTop && all("ol.person li").every(e => /runs disagreed|not judged/i.test(e.innerText) && e.querySelector(".where").innerText.trim()) ? null : `listed ${ids("ol.person li")}, want ${want.person}`,
    "evidence folded": folds.every(e => !e.open && [...e.children].every(child => child.matches("summary, blockquote.evidence, .where"))) ? null : "a fold is open or holds more than a quote and its place",
    "grader text": all(".warn li").length === want.grader && !document.querySelector("details .warn") ? null : `${all(".warn li").length} passages, want ${want.grader}`,
    "empty fixes": want.fixes.length || (/\d+ criteria were checked/.test(text) && /rubric itself was not judged/.test(document.querySelector("#fix-first").parentElement.innerText)) ? null : "the empty fix list does not say what was checked",
    "fix once": !fixShown.length && !unlinked.length ? null : `shown other than once: ${fixShown}; unlinked: ${unlinked}`,
    "no response path": !document.querySelector("main form, main input, main select, main textarea, main button") ? null : "the page takes an answer",
    "split rule": /split on a critical criterion is a gap/.test(document.querySelector(".rating").innerText) ? null : "the rating does not state the split rule",
    "outside fold": !document.querySelector("details .crit-text, details .status, details a[href^='#fix-']") ? null : "the fold hides a criterion, its status or its fix",
  };
}
