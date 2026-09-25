#!/bin/sh
# usage: page-check.sh <page.html>
# Loads the page in a 320 px frame twice, with motion and with reduced motion, clicks
# each control once, and prints one line per run:
# `<mode> <scroll>/<client> <smallest text>px <smallest Hangul or Han>px anim <running> steps <shown>/<total> pass|FAIL`,
# then `pass` or `FAIL`. A run fails on a sideways scroll, text under 11 px (Hangul or Han
# under 12 px) or an uncaught error; the reduced run also on a running animation or
# transition, or a player showing fewer captions than it has steps.
# Exit 0 pass, 1 FAIL, 2 when it could not run, saying why.
set -eu
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
[ $# -eq 1 ] || { echo "usage: page-check.sh <page.html>" >&2; exit 2; }
[ -f "$1" ] || { echo "page-check.sh: no file $1" >&2; exit 2; }
[ -x "$CHROME" ] || { echo "page-check.sh: no Chrome at $CHROME" >&2; exit 2; }
P=$(cd "$(dirname "$1")" && pwd -P)/$(basename "$1")
F="${TMPDIR:-/tmp}/page-check-frame.html"
cat >| "$F" <<'EOF'
<iframe id=f style="width:320px;height:800px;border:0"></iframe>
<script>
f.onload = function () {
  f.onload = null;
  var d = f.contentDocument, w = f.contentWindow;
  d.querySelectorAll('button,summary,input,select').forEach(function (c) { c.click(); });
  var anim = d.getAnimations().filter(function (a) { return a.playState === 'running'; }).length;
  setTimeout(function () {
    var e = d.documentElement, t = d.createTreeWalker(d.body, 4), n, z, s = [1 / 0, 1 / 0];
    while ((n = t.nextNode())) if (n.data.trim() && !/^(script|style|title)$/i.test(n.parentElement.tagName)) {
      z = /[\p{sc=Hangul}\p{sc=Han}]/u.test(n.data) ? 1 : 0;
      s[z] = Math.min(s[z], parseFloat(w.getComputedStyle(n.parentElement).fontSize));
    }
    var shown = 0, total = 0;
    d.querySelectorAll('[data-player]').forEach(function (p) {
      var li = p.querySelectorAll('.steps > li');
      total += li.length;
      shown += Array.prototype.filter.call(li, function (l) { return l.checkVisibility(); }).length;
    });
    var reduced = w.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var ok = e.scrollWidth == e.clientWidth && s[0] >= 11 && s[1] >= 12 && (!reduced || (anim == 0 && shown == total));
    document.body.dataset.r = (reduced ? 'reduced ' : 'motion ') + e.scrollWidth + '/' + e.clientWidth + ' ' + s[0] + 'px ' + s[1] + 'px anim ' + anim + ' steps ' + shown + '/' + total + (ok ? ' pass' : ' FAIL');
  }, 500);
};
f.src = location.hash.slice(1);
</script>
EOF
run() {
  R=$("$CHROME" --headless --disable-gpu --allow-file-access-from-files --dump-dom "$@" \
    --enable-logging=stderr --virtual-time-budget=3000 "file://$F#file://$P" 2>"$F.log" |
    sed -n 's/.*data-r="\([^"]*\)".*/\1/p')
  [ -n "$R" ] || { echo "page-check.sh: could not read $P" >&2; exit 2; }
  grep -q 'CONSOLE.*"Uncaught' "$F.log" && R="${R% *} error FAIL"
  echo "$R"
}
A=$(run)
B=$(run --force-prefers-reduced-motion)
printf '%s\n%s\n' "$A" "$B"
case "$A $B" in *FAIL*) echo FAIL; exit 1 ;; *) echo pass; exit 0 ;; esac
