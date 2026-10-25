/* Custom tasks of this book. Each one reads its own markup, calls bookSolve(card) when the reader gets it right,
   and sets card.__solve so `book.py render` can drive it. */
/* kit:
  .tree-pick  buttons the reader taps in order; data-want lists the right order
*/
document.querySelectorAll('[data-c="task"][data-kind="custom"] .tree-pick').forEach(function (box) {
  var card = box.closest('[data-c="task"]'), want = box.dataset.want.split(' '), got = [];
  var hint = card.querySelector('.qhint');
  box.querySelectorAll('button').forEach(function (b) {
    b.onclick = function () {
      if (card.classList.contains('solved') || b.disabled) return;
      var name = b.textContent.trim().charAt(0);
      if (name !== want[got.length]) { hint.className = 'qhint no'; hint.textContent = 'Not yet: ask first about the dish that ends the most games.'; return; }
      got.push(name); b.disabled = true;
      if (got.length === want.length) window.bookSolve(card);
    };
  });
  card.__solve = function () { want.forEach(function (w) { box.querySelectorAll('button').forEach(function (b) { if (b.textContent.trim().charAt(0) === w) b.click(); }); }); };
});
