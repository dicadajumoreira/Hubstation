/* HubStation — Editorial Premium JS */
(function () {
  'use strict';

  /* ── NAV ── */
  const nav = document.getElementById('nav');
  const tick = () => nav && (window.scrollY > 48 ? nav.classList.add('scrolled') : nav.classList.remove('scrolled'));
  window.addEventListener('scroll', tick, { passive: true });
  tick();

  /* ── BURGER ── */
  const burger = document.getElementById('burger');
  const mob    = document.getElementById('mobNav');
  if (burger && mob) {
    burger.addEventListener('click', () => {
      const o = burger.classList.toggle('open');
      mob.classList.toggle('open', o);
      document.body.style.overflow = o ? 'hidden' : '';
    });
    mob.querySelectorAll('a').forEach(a => a.addEventListener('click', () => {
      burger.classList.remove('open');
      mob.classList.remove('open');
      document.body.style.overflow = '';
    }));
  }

  /* ── ACTIVE LINK ── */
  /* Normaliza pra comparar URL limpa: '/' → 'index', '/sobre' → 'sobre'. */
  const slug = p => (p.replace(/\.html$/, '').replace(/^\/+|\/+$/g, '') || 'index');
  const cur = slug(location.pathname);
  document.querySelectorAll('.nav-links a, .mob-nav a').forEach(a => {
    const href = a.getAttribute('href') || '';
    if (!href.startsWith('/')) return;
    if (slug(href) === cur) a.classList.add('active');
  });

  /* ── SCROLL OBSERVER ── */
  if ('IntersectionObserver' in window) {
    const obs = new IntersectionObserver(entries => {
      entries.forEach(e => {
        if (e.isIntersecting) { e.target.classList.add('in'); obs.unobserve(e.target); }
      });
    }, { threshold: 0.10, rootMargin: '0px 0px -40px 0px' });
    document.querySelectorAll('.fu,.fl,.fr').forEach(el => obs.observe(el));
  } else {
    document.querySelectorAll('.fu,.fl,.fr').forEach(el => el.classList.add('in'));
  }

  /* ── COUNTER ── */
  function count(el) {
    const t = +el.dataset.target, dur = 1600;
    const s = performance.now();
    (function loop(now) {
      const p = Math.min((now - s) / dur, 1);
      const e = 1 - Math.pow(1 - p, 4);
      el.textContent = Math.floor(e * t);
      if (p < 1) requestAnimationFrame(loop); else el.textContent = t;
    })(s);
  }
  const cobs = new IntersectionObserver(entries => {
    entries.forEach(e => { if (e.isIntersecting) { count(e.target); cobs.unobserve(e.target); } });
  }, { threshold: 0.5 });
  document.querySelectorAll('.counter').forEach(el => cobs.observe(el));

  /* ── TICKER DUPLICATE ── */
  const tk = document.querySelector('.ticker-track');
  if (tk) tk.innerHTML += tk.innerHTML;

  /* ── FORM ── */
  const form = document.getElementById('contactForm');
  if (form) {
    /* Caixa de erro criada sob demanda — o HTML só traz o estado de sucesso. */
    let box = null;
    const erro = msg => {
      if (!box) {
        box = document.createElement('p');
        box.setAttribute('role', 'alert');
        box.style.cssText = 'margin:16px 0 0;padding:14px 18px;background:rgba(244,67,54,0.07);' +
          'border-left:3px solid #F44336;font-size:14px;line-height:1.6;color:#4A4A4A';
        form.appendChild(box);
      }
      box.textContent = msg;
    };

    form.addEventListener('submit', async e => {
      e.preventDefault();
      const btn = form.querySelector('[type=submit]');
      const rotulo = btn.textContent;
      const dados = Object.fromEntries(new FormData(form).entries());

      if (box) box.textContent = '';
      btn.textContent = 'Enviando...';
      btn.disabled = true;

      try {
        const r = await fetch('/api/contato', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(dados)
        });
        if (!r.ok) {
          const d = await r.json().catch(() => ({}));
          throw new Error(d.error || 'Não foi possível enviar agora.');
        }
        const s = document.getElementById('formSuccess');
        if (s) { s.style.display = 'block'; form.style.display = 'none'; }
      } catch (err) {
        erro(
          (err && err.message ? err.message : 'Não foi possível enviar agora.') +
          ' Você também pode escrever direto para contato@hubstation.com.br.'
        );
        btn.textContent = rotulo;
        btn.disabled = false;
      }
    });
  }

  /* ── SMOOTH ANCHOR ── */
  document.querySelectorAll('a[href^="#"]').forEach(a => {
    a.addEventListener('click', e => {
      const t = document.querySelector(a.getAttribute('href'));
      if (t) { e.preventDefault(); t.scrollIntoView({ behavior: 'smooth' }); }
    });
  });

})();
