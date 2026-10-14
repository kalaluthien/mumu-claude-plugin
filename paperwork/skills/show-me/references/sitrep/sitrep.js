// Charts are drawn here from their data so their numbers stay the ones written on the page.
for (const svg of document.querySelectorAll('svg[data-chart]')) {
  const pts = svg.dataset.values.split(',').map(s => { const i = s.lastIndexOf(':'); return [s.slice(0, i).trim(), +s.slice(i + 1)]; });
  const W = Math.max(320, svg.parentElement.clientWidth), H = Math.min(280, Math.round(W * .6)), L = 48, B = 40, T = 16, max = Math.max(...pts.map(p => p[1])) || 1, unit = svg.dataset.unit || '';
  const x = i => L + (i + .5) * (W - L - 8) / pts.length, y = v => T + (1 - v / max) * (H - T - B);
  let out = `<line x1="${L}" y1="${H - B}" x2="${W}" y2="${H - B}" stroke="#6f6b63"/>`
    + `<text x="4" y="${T + 4}" font-size="13" fill="#67635c">${max}${unit}</text>`;
  const top = pts.findIndex(p => p[1] === max);
  pts.forEach(([k, v], i) => {
    if (svg.dataset.chart === 'bar') {
      const w = (W - L - 8) / pts.length * .7;
      out += `<rect x="${x(i) - w / 2}" y="${y(v)}" width="${w}" height="${H - B - y(v)}" fill="#c96442"/>`;
    }
    out += `<text x="${x(i)}" y="${y(v) - 6}" font-size="12" text-anchor="middle">${v}</text>`;
    out += `<text class="x" data-i="${i}" x="${x(i)}" y="${H - B + 18}" font-size="12" text-anchor="middle" fill="#67635c">${k}</text>`;
  });
  if (svg.dataset.chart === 'line')
    out += `<polyline fill="none" stroke="#c96442" stroke-width="3" points="${pts.map(([, v], i) => `${x(i)},${y(v)}`).join(' ')}"/>`
      + pts.map(([, v], i) => `<circle cx="${x(i)}" cy="${y(v)}" r="4" fill="#c96442"/>`).join('');
  svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
  svg.setAttribute('role', 'img');
  svg.innerHTML = out;
  // axis labels: kept inside the drawing, then thinned so none overlaps another, the peak's kept first
  const xs = [...svg.querySelectorAll('text.x')], kept = [];
  for (const t of [xs[top], ...xs.filter((_, i) => i !== top)]) {
    const b = t.getBBox(), shift = Math.min(0, W - 2 - (b.x + b.width)) + Math.max(0, 2 - b.x);
    if (shift) t.setAttribute('x', +t.getAttribute('x') + shift);
    const l = b.x + shift, r = l + b.width;
    if (kept.some(([kl, kr]) => l < kr + 6 && r > kl - 6)) t.remove(); else kept.push([l, r]);
  }
}
