for (const b of document.querySelectorAll('[data-reply]'))
  b.addEventListener('click', () => { document.querySelector('.reply textarea').value = b.dataset.reply; });
