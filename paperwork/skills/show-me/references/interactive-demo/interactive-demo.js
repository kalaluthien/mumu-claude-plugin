// One state per live block: every control writes it and every view reads it, so the preview and the result never disagree.
for (const live of document.querySelectorAll('[data-playbook="interactive-demo"] .live')) {
  const inputs = [...live.querySelectorAll('[data-param]')];
  const draw = () => {
    const state = {};
    for (const i of inputs) {
      state[i.dataset.param] = i.type === 'checkbox' ? i.checked : i.value;
      live.style.setProperty('--' + i.dataset.param, i.value + (i.dataset.unit || ''));
    }
    for (const o of live.querySelectorAll('[data-show]')) o.textContent = state[o.dataset.show];
    for (const t of live.querySelectorAll('[data-template]')) {
      t.textContent = t.dataset.template.replace(/\{([\w-]+)\}/g, (_, k) => state[k] ?? '');
      const reply = document.querySelector('.reply textarea');
      if (reply) reply.value = t.textContent;
    }
    live.dispatchEvent(new CustomEvent('demo-draw', { detail: state }));
  };
  for (const i of inputs) i.addEventListener('input', draw);
  for (const b of live.querySelectorAll('[data-preset]')) b.addEventListener('click', () => {
    for (const [k, v] of Object.entries(JSON.parse(b.dataset.preset))) {
      const i = live.querySelector(`[data-param="${k}"]`);
      if (i) i.type === 'checkbox' ? (i.checked = v) : (i.value = v);
    }
    draw();
  });
  draw();
}
for (const steps of document.querySelectorAll('[data-playbook="interactive-demo"] .steps')) {
  const boxes = [...steps.querySelectorAll('input[type=checkbox]')];
  const count = () => {
    for (const b of boxes) b.closest('li').classList.toggle('done', b.checked);
    for (const c of steps.parentElement.querySelectorAll('[data-steps-count]')) c.textContent = `${boxes.filter(b => b.checked).length} / ${boxes.length}`;
  };
  for (const b of boxes) b.addEventListener('change', count);
  count();
}
