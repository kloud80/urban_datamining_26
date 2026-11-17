// 11주차 실습 화면 — 서버가 보내는 '블록'을 그리고, [승인]을 받아 한 칸씩 진행한다.
const $ = (s, el = document) => el.querySelector(s);
const h = (tag, attrs = {}, ...kids) => {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === 'class') e.className = v;
    else if (k.startsWith('on')) e.addEventListener(k.slice(2), v);
    else e.setAttribute(k, v);
  }
  for (const k of kids.flat()) if (k != null) e.append(k.nodeType ? k : document.createTextNode(k));
  return e;
};

const AGENT_COLOR = { '총괄': '#4434E2', '계획문서 담당': '#00B37A', '웹 리서치 담당': '#E08A00',
                      '하네스': '#D93636', '모델': '#9E5DF9' };
const KIND = { llm: '모델 호출 · 비용', tool: '도구 실행', local: '내 컴퓨터 안 · 비용 없음',
               cost: '시간·비용 큼' };

let STEPS = [], cur = null, runId = null, busy = false, chatHistory = [];

// ── 블록 그리기 ─────────────────────────────────────────────────────────
const R = {
  text: b => h('div', { class: 'text' }, b.text),
  answer: b => h('div', { class: 'answer' }, b.text),
  alert: b => h('div', { class: 'alert ' + (b.level || '') }, b.text),
  kv: b => h('div', { class: 'kv' }, b.items.map(([k, v]) => h('span', {}, k, h('b', {}, v)))),
  code: b => { const d = h('details', { class: 'code' }, h('summary', {}, b.title), h('pre', {}, b.text));
               if (b.open) d.open = true; return d; },
  messages: b => h('div', { class: 'msgs' }, b.items.map(m =>
    h('div', { class: 'msg' }, h('div', { class: 'role ' + m.role }, m.role), h('div', { class: 'body' }, m.content)))),
  chunks: b => h('div', { class: 'chunks' }, b.items.map(c => {
    const el = h('div', { class: 'chunk', onclick: () => el.classList.toggle('open') },
      h('div', { class: 'top' }, h('span', { class: 'page' }, 'p.' + c.page),
        c.score == null ? null : h('div', { class: 'sim' }, h('i', { style: `width:${Math.max(0, c.score) * 100}%` })),
        c.score == null ? null : h('span', { class: 'score' }, '유사도 ' + c.score.toFixed(3))),
      h('div', { class: 'body' }, c.text));
    return el;
  })),
  vector: b => {
    const m = Math.max(...b.values.map(Math.abs)) || 1;
    return h('div', {}, h('div', { class: 'vector' }, b.values.map(v => {
      const a = Math.min(1, Math.abs(v) / m);
      const col = v >= 0 ? `rgba(68,52,226,${a})` : `rgba(217,54,54,${a})`;
      return h('i', { style: `background:${col}`, title: v.toFixed(4) });
    })), h('div', { class: 'cap' }, `${b.dims.toLocaleString()}차원 중 앞 ${b.values.length}개 · 파랑 +, 빨강 −, 진할수록 크다`));
  },
  samples: b => {
    const cnt = {}; b.items.forEach(a => cnt[a] = (cnt[a] || 0) + 1);
    return h('div', { class: 'samples' }, Object.entries(cnt).map(([a, n]) => h('span', {}, a, h('b', {}, '×' + n))));
  },
  logprobs: b => logprobs(b),
  history: b => { chatHistory = b.items; renderHist(); return null; },
};

function logprobs(b) {
  const wrap = h('div', { class: 'lp' });
  const mk = (label, min, max, step, val) => {
    const inp = h('input', { type: 'range', min, max, step, value: val });
    const out = h('output', {}, val);
    wrap.append(h('div', { class: 'ctl' }, label, inp, out));
    return [inp, out];
  };
  const [tIn, tOut] = mk('temperature', 0.05, 2, 0.05, b.temperature || 1);
  const [pIn, pOut] = mk('top_p', 0.05, 1, 0.05, b.top_p || 1);
  const rows = h('div', {}); wrap.append(rows,
    h('div', { class: 'note' }, 'p_T ∝ p^(1/T) — 상위 10개만으로 다시 정규화한 값. 회색은 top_p 밖이라 추첨 후보에서 빠진다.'));
  const draw = () => {
    const T = +tIn.value, P = +pIn.value; tOut.value = T; pOut.value = P;
    const w = b.items.map(t => Math.exp(t.logprob / T)); const z = w.reduce((a, c) => a + c, 0);
    let cum = 0; rows.replaceChildren(...b.items.map((t, i) => {
      const p = w[i] / z; const inside = cum < P; cum += p;
      return h('div', { class: 'row' + (inside ? '' : ' cut') }, h('div', { class: 'tok' }, JSON.stringify(t.token)),
        h('div', { class: 'track' }, h('i', { style: `width:${(p * 100).toFixed(1)}%` })),
        h('div', { class: 'p' }, p.toFixed(2)));
    }));
  };
  tIn.oninput = pIn.oninput = draw; draw();
  return wrap;
}

function blocks(list) { return list.map(b => (R[b.type] || R.text)(b)).filter(Boolean); }

function agentBadge(a) {
  return a ? h('span', { class: 'agent', style: `background:${AGENT_COLOR[a] || '#666'}` }, a) : null;
}

// ── 카드 ────────────────────────────────────────────────────────────────
function shownCard(ev) {
  if (ev.title === '_history') { blocks(ev.blocks); return null; }
  const c = h('div', { class: 'card', style: `border-left-color:${AGENT_COLOR[ev.agent] || '#C9C7D6'}` },
    h('h3', {}, agentBadge(ev.agent), ev.title), ...blocks(ev.blocks));
  return c;
}

function pendingCard(ev) {
  const c = h('div', { class: 'card pending', id: 'pending' },
    h('h3', {}, agentBadge(ev.agent), '다음 — ' + ev.title, h('span', { class: 'kind ' + ev.kind }, KIND[ev.kind] || ev.kind)),
    ev.detail ? h('div', { class: 'detail' }, ev.detail) : null, ...blocks(ev.blocks),
    h('div', { class: 'acts' },
      h('button', { class: 'approve', onclick: approve }, '승인 ▶'),
      h('button', { class: 'stopb', onclick: stop }, '중단')));
  return c;
}

function apply(res) {
  $('#pending')?.remove();
  const tl = $('#timeline');
  for (const ev of res.shown) { const c = shownCard(ev); if (c) tl.append(c); }
  if (res.pending) tl.append(pendingCard(res.pending));
  if (res.done) {
    tl.append(h('div', { class: 'done' }, `끝 — 승인 ${res.approvals}번`));
    runId = null; $('#run').disabled = false;
  }
  (res.pending ? $('#pending') : tl.lastElementChild)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

async function call(url, body) {
  busy = true; document.body.style.cursor = 'progress';
  $('#pending .approve')?.setAttribute('disabled', '');
  try {
    const r = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' },
                                 body: JSON.stringify(body || {}) });
    if (!r.ok) throw new Error((await r.json()).detail || r.status);
    return await r.json();
  } finally { busy = false; document.body.style.cursor = ''; }
}

async function approve() { if (!runId || busy) return; apply(await call('/api/approve/' + runId)); }
async function stop() {
  if (!runId) return; await call('/api/stop/' + runId);
  $('#pending')?.remove(); $('#timeline').append(h('div', { class: 'done' }, '중단했다 — 그 뒤의 호출은 일어나지 않았다.'));
  runId = null; $('#run').disabled = false;
}

// ── 단계 화면 ───────────────────────────────────────────────────────────
function renderHist() {
  const el = $('#hist'); if (!el) return;
  el.textContent = chatHistory.length ? `대화 ${chatHistory.length}개 메시지가 다음 요청에 함께 간다` : '';
}

function show(step) {
  if (runId) { fetch('/api/stop/' + runId, { method: 'POST' }); runId = null; }   // 조용히 닫는다
  cur = step; chatHistory = [];
  document.querySelectorAll('#steps li').forEach(li => li.classList.toggle('on', li.dataset.id === step.id));
  $('#head').replaceChildren(h('h1', {}, h('span', { class: 'no' }, step.no), step.title), h('p', {}, step.sub));
  $('#doc pre').textContent = step.doc;
  const f = $('#form'); f.replaceChildren();
  for (const fd of step.fields) {
    const id = 'f_' + fd.name; let ctl;
    if (fd.type === 'textarea') ctl = h('textarea', { id, name: fd.name }, fd.default);
    else if (fd.type === 'range') {
      const inp = h('input', { type: 'range', id, name: fd.name, min: fd.min, max: fd.max, step: fd.step, value: fd.default });
      const out = h('output', {}, fd.default); inp.oninput = () => out.value = inp.value;
      ctl = h('div', { class: 'range' }, inp, out);
    } else if (fd.type === 'select') {
      ctl = h('select', { id, name: fd.name }, fd.options.map(o => h('option', o === fd.default ? { selected: '' } : {}, o)));
      if (fd.fills) ctl.onchange = () => { $('#f_' + fd.fills).value = fd.values[ctl.value]; };
    } else if (fd.type === 'checkbox') {
      const cb = h('input', { type: 'checkbox', id, name: fd.name }); cb.checked = !!fd.default;
      f.append(h('div', { class: 'f wide' }, h('label', { class: 'check' }, cb, fd.label))); continue;
    }
    f.append(h('div', { class: 'f' + (fd.type === 'textarea' ? ' wide' : '') }, h('label', { for: id }, fd.label), ctl));
  }
  f.append(h('div', { class: 'bar' },
    h('button', { class: 'go', id: 'run', type: 'submit' }, '실행 — 첫 단계 보기'),
    h('button', { class: 'ghost', type: 'button', onclick: () => $('#timeline').replaceChildren() }, '화면 비우기'),
    step.chat ? h('button', { class: 'ghost', type: 'button', onclick: () => { chatHistory = []; renderHist(); } }, '대화 초기화') : null,
    step.chat ? h('span', { class: 'hist', id: 'hist' }) : null));
  $('#timeline').replaceChildren();
  history.replaceState(null, '', '#' + step.no);
}

$('#form').addEventListener('submit', async e => {
  e.preventDefault(); if (busy) return;
  const p = {};
  for (const fd of cur.fields) {
    const el = $('#f_' + fd.name);
    p[fd.name] = fd.type === 'checkbox' ? el.checked : fd.type === 'range' ? +el.value : el.value;
  }
  if (cur.chat) p.history = chatHistory;
  $('#timeline').append(h('div', { class: 'done' }, '── 새 실행 ──'));
  $('#run').disabled = true;
  const res = await call('/api/run/' + cur.id, p);
  runId = res.run; apply(res);
});

document.addEventListener('keydown', e => {
  if (['TEXTAREA', 'INPUT', 'SELECT'].includes(document.activeElement.tagName)) return;
  if (e.key === 'a' || e.key === 'A') approve();
  if (e.key === 's' || e.key === 'S') stop();
});

(async () => {
  const d = await (await fetch('/api/steps')).json();
  STEPS = d.steps;
  if (!d.ready.pdf) $('#ready').append(h('div', { class: 'alert block' },
    '보고서 PDF 가 없다 — 터미널에서 python data/get_paju.py 를 먼저 실행할 것. (03·04 이후 단계에 필요)'));
  else if (!d.ready.index) $('#ready').append(h('div', { class: 'alert warn' },
    '벡터 인덱스가 아직 없다 — 04 단계 ①에서 승인하면 만든다 (1~2분, 몇십 원).'));
  $('#steps').replaceChildren(...STEPS.map(s => {
    const li = h('li', { 'data-id': s.id, onclick: () => show(s) },
      h('span', { class: 'no' }, s.no), h('span', { class: 't' }, s.title), h('span', { class: 's' }, s.sub));
    return li;
  }));
  const want = STEPS.find(s => '#' + s.no === location.hash) || STEPS[0];
  show(want);
  window.addEventListener('hashchange', () => {
    const s = STEPS.find(s => '#' + s.no === location.hash);
    if (s && s !== cur) show(s);
  });
})();
