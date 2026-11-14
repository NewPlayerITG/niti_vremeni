(() => {
"use strict";

/* ---------- утилиты ---------- */
const $ = (s, r = document) => r.querySelector(s);
const esc = s => String(s).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const IMG = "/static/img/";
const EMPTY_FILL = "#EEF2FA", EMPTY_LINE = "#9DB0DA";

const S = {
  st: null, screen: "welcome", step: 0, chapter: 1,
  levelId: null, task: null, tk: null, modal: null, name: "", toastT: null,
};

const STORY = [
  "Вы получили старую мастерскую от родственника, которого почти не помнили. Среди инструментов лежит большая книга — Атлас узоров России.",
  "Когда узор восстановлен, на странице проступают воспоминания тех, кто его создавал. Но многие страницы пусты: нити, которые их связывали, оборваны.",
  "На первой странице осталась одна строка:",
];

async function api(path, body) {
  const res = await fetch("/api/" + path, {
    method: body === undefined ? "GET" : "POST",
    headers: {"Content-Type": "application/json"},
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || "Что-то пошло не так. Попробуйте ещё раз.");
  return data;
}
const loadState = async () => { S.st = await api("state"); };

function toast(msg) {
  const t = $("#toast");
  t.textContent = msg;
  t.classList.add("show");
  clearTimeout(S.toastT);
  S.toastT = setTimeout(() => t.classList.remove("show"), 2800);
}

function go(screen, extra = {}) {
  Object.assign(S, extra, {screen});
  render();
  $("#screen").scrollTop = 0;
}

const findLevel = id => S.st.chapters.flatMap(c => c.levels).find(l => l.id === id);

/* ---------- иконки и рисунки ---------- */
const sparkIcon = (s = 15) => `<svg width="${s}" height="${s}" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 1.5l2.6 7.9 7.9 2.6-7.9 2.6L12 22.5l-2.6-7.9L1.5 12l7.9-2.6z" fill="#E0A526"/></svg>`;
const threadIcon = (s = 15) => `<svg width="${s}" height="${s}" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="8" fill="none" stroke="#C9971C" stroke-width="2.4"/><path d="M5 10c5 3 9 3 14 0M6 15c4 2 8 2 12 0" stroke="#C9971C" stroke-width="1.6" fill="none"/></svg>`;
const starIcon = (on, s = 26) => `<svg width="${s}" height="${s}" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2.5l2.9 6.1 6.6.8-4.9 4.6 1.3 6.6L12 17.3 6.1 20.6l1.3-6.6L2.5 9.4l6.6-.8z" fill="${on ? "#E0A526" : "#E3E9F5"}" stroke="${on ? "#B7791F" : "#CBD5EA"}" stroke-width="1.2" stroke-linejoin="round"/></svg>`;
const stars = (n, s = 20) => `<span class="stars" aria-label="Звёзд: ${n} из 3">${[1,2,3].map(i => starIcon(i <= n, s)).join("")}</span>`;

const TASK_ICON = {
  puzzle: '<svg viewBox="0 0 24 24"><rect x="3" y="3" width="8" height="8" rx="1.5"/><rect x="13" y="3" width="8" height="8" rx="1.5"/><rect x="3" y="13" width="8" height="8" rx="1.5"/><path d="M13 17h8M17 13v8"/></svg>',
  memory: '<svg viewBox="0 0 24 24"><rect x="3" y="4" width="8" height="11" rx="1.5"/><rect x="13" y="9" width="8" height="11" rx="1.5"/><path d="M7 8.5v2M17 13.5v2"/></svg>',
  color: '<svg viewBox="0 0 24 24"><path d="M20 4l-9 9"/><path d="M11 13c-3 0-5 2-5 5 0 1-1 2-2 2 4 1 9 0 9-5z"/></svg>',
};

const buddyInner = () => `
  <path d="M44 49c8 1 14 5 14 9" fill="none" stroke="#C8372D" stroke-width="3" stroke-linecap="round"/>
  <circle cx="30" cy="32" r="22" fill="#C8372D"/>
  <path d="M14 24c10 6 22 4 32-4M10 34c12 7 28 6 38-3M16 46c9 3 20 2 27-5" fill="none" stroke="#E8776C" stroke-width="2" stroke-linecap="round"/>
  <circle cx="23" cy="30" r="5" fill="#fff"/><circle cx="37" cy="30" r="5" fill="#fff"/>
  <circle cx="24" cy="31" r="2.4" fill="#1B2340"/><circle cx="38" cy="31" r="2.4" fill="#1B2340"/>
  <path d="M26 39c2 3 6 3 8 0" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round"/>`;
const buddySvg = () => `<svg viewBox="0 0 64 64" role="img" aria-label="Клубочек">${buddyInner()}</svg>`;
const buddy = (text, cls = "") => `<div class="buddy ${cls}">${buddySvg()}<p class="bubble">${esc(text)}</p></div>`;

function sceneSvg(st) {
  const has = id => st.items.includes(id);
  const vase = st.artifacts.includes(1);
  return `<svg class="scene" viewBox="0 0 360 250" role="img" aria-label="Ваша мастерская">
    <rect width="360" height="170" fill="#DCE3F0"/>
    <rect y="170" width="360" height="80" fill="#A07A55"/>
    <path d="M0 196H360M0 223H360M70 170v26M210 196v27M130 223v27M290 223v27M300 170v26" stroke="#8B6743" stroke-width="1.2"/>
    <rect y="164" width="360" height="8" fill="#7A5638"/>
    <rect x="34" y="28" width="96" height="100" rx="3" fill="#7A5638"/>
    <rect x="40" y="34" width="84" height="88" fill="#BFD3F2"/>
    <path d="M82 34v88M40 78h84" stroke="#7A5638" stroke-width="4"/>
    ${has("curtains") ? `<rect x="24" y="22" width="116" height="6" rx="3" fill="#5A3E27"/>
      <path d="M30 28h34c-3 30-3 62 3 106H30z" fill="#C8372D"/><path d="M134 28h-34c3 30 3 62-3 106h37z" fill="#C8372D"/>
      <path d="M40 28c1 40 1 70 3 106M54 28c0 40 0 70 2 106M124 28c-1 40-1 70-3 106M110 28c0 40 0 70-2 106" stroke="#E8776C" stroke-width="1.6" fill="none"/>` : ""}
    ${has("lamp") ? `<circle cx="160" cy="76" r="62" fill="#FFE9A8" opacity=".38"/>
      <path d="M160 0v38" stroke="#5A3E27" stroke-width="2"/><path d="M141 64h38l-9-26h-20z" fill="#E0A526" stroke="#B7791F" stroke-width="2" stroke-linejoin="round"/><circle cx="160" cy="66" r="4" fill="#FFF6D6"/>` : ""}
    <rect x="188" y="96" width="150" height="7" rx="1" fill="#7A5638"/>
    <path d="M200 103v12l12-12M326 103v12l-12-12" fill="#5A3E27"/>
    ${vase ? `<image href="${IMG}motifs/m3.png" x="214" y="42" width="40" height="54" style="mix-blend-mode:multiply"/>`
           : `<rect x="212" y="46" width="44" height="50" rx="6" fill="none" stroke="#8791AB" stroke-dasharray="4 4"/>`}
    <rect x="278" y="62" width="26" height="34" rx="5" fill="none" stroke="#8791AB" stroke-dasharray="4 4"/>
    <rect x="308" y="62" width="26" height="34" rx="5" fill="none" stroke="#8791AB" stroke-dasharray="4 4"/>
    ${has("rug") ? `<ellipse cx="190" cy="232" rx="120" ry="15" fill="#C8372D"/><ellipse cx="190" cy="232" rx="100" ry="11" fill="#F7F9FC"/><ellipse cx="190" cy="232" rx="82" ry="8" fill="#1E3A9E"/><ellipse cx="190" cy="232" rx="60" ry="5" fill="#E8776C"/>` : ""}
    <rect x="122" y="167" width="9" height="62" fill="#5A3E27"/><rect x="324" y="167" width="9" height="62" fill="#5A3E27"/>
    <rect x="112" y="158" width="230" height="9" rx="2" fill="#6B4A30"/>
    <rect x="206" y="140" width="66" height="18" rx="2" fill="#1E3A9E"/><rect x="208" y="155" width="62" height="3" fill="#fff"/>
    <path d="M239 140v18" stroke="#15286B" stroke-width="2"/><path d="M252 140v22l4-4 4 4v-22z" fill="#C8372D"/>
    <g transform="translate(290 124) scale(.62)">${buddyInner()}</g>
  </svg>`;
}

/* ---------- экраны ---------- */
const views = {
  welcome: () => `
    <section class="screen center welcome">
      <div class="stitch"></div>
      <div class="welcome-buddy buddy">${buddySvg()}</div>
      <h1 class="wordmark">Нити времени</h1>
      <p class="muted">Восстановите Атлас узоров России и соберите свою мастерскую.</p>
      <button class="btn block" data-act="start">Начать</button>
      <div class="stitch"></div>
    </section>`,

  story: () => `
    <section class="screen center">
      <div class="story-card">
        ${esc(STORY[S.step])}
        ${S.step === 2 ? "<q>Узор живёт, пока помнят, кто его создал и зачем.</q>" : ""}
      </div>
      <div class="dots">${STORY.map((_, i) => `<i class="${i === S.step ? "on" : ""}"></i>`).join("")}</div>
      <button class="btn block" data-act="story-next">${S.step === STORY.length - 1 ? "Продолжить" : "Дальше"}</button>
    </section>`,

  name: () => `
    <section class="screen center">
      ${buddy("Я Клубочек. Живу в Атласе. А тебя как зовут?", "welcome-buddy")}
      <input id="name" type="text" maxlength="20" placeholder="Ваше имя" autocomplete="off" value="${esc(S.name)}" aria-label="Ваше имя">
      <button class="btn block" data-act="name-submit">Войти в мастерскую</button>
    </section>`,

  workshop() {
    const st = S.st;
    const done = st.chapters.filter(c => c.status === "done").length;
    const next = nextLevel();
    let line = "Я Клубочек и чую оборванные нити. Первая ведёт в Московскую землю — идём?";
    if (done >= 1) line = "Первая страница Атласа ожила! Загляни в Атлас — там история вазы.";
    else if (st.chapters[0].levels.some(l => l.stars)) line = "Нить поддаётся. Следующий узор уже ждёт.";
    return `<section class="screen">
      ${sceneSvg(st)}
      ${buddy(line)}
      <div class="stats">
        <div class="stat"><b>${st.atlas.filter(a => a.unlocked).length} из ${st.atlas.length}</b><span>страниц Атласа</span></div>
        <div class="stat"><b>${st.artifacts.length} из ${st.atlas.length}</b><span>экспонатов</span></div>
      </div>
      ${next ? `<button class="btn block" data-act="level" data-id="${next.id}">Играть: ${esc(next.title)}</button>`
             : `<button class="btn block" data-act="tab" data-id="map">Открыть карту</button>`}
      <button class="linkbtn" data-act="reset">Начать заново</button>
    </section>`;
  },

  map() {
    const st = S.st;
    return `<section class="screen">
      <h1>Карта нитей</h1>
      <div class="path">${st.chapters.map(ch => {
        const status = {done: `Пройдено · ${ch.stars} из ${ch.max_stars} звёзд`, open: "Играть",
          soon: "Откроется в следующей версии", locked: `Откроется после главы ${ch.id - 1}`}[ch.status];
        return `<button class="node ${ch.status}" style="--c:${ch.color}" data-act="chapter" data-id="${ch.id}">
          <span class="num">${ch.id}</span>
          <span class="region">${esc(ch.region)}</span>
          <h2>${esc(ch.title)}</h2>
          <span class="small muted">${esc(ch.focus)}</span>
          <span class="status">${esc(status)}</span>
        </button>`;
      }).join("")}</div>
    </section>`;
  },

  chapter() {
    const ch = S.st.chapters[S.chapter - 1];
    const found = S.st.secrets.includes("gzhel-signature");
    return `<section class="screen" style="--c:${ch.color}">
      <button class="back" data-act="tab" data-id="map">‹ Карта</button>
      <div class="chapter-hero"><span class="region">${esc(ch.region)}</span><h1>${esc(ch.title)}</h1></div>
      <p>${esc(ch.story)}</p>
      <div class="levels">${ch.levels.map(l => `
        <button class="lvrow ${l.status === "locked" ? "locked" : ""}" data-act="level" data-id="${l.id}" ${l.status === "locked" ? "aria-disabled=true" : ""}>
          <span class="t"><b>${esc(l.title)}</b><span>Пазл · найди пару · раскраска</span></span>
          ${l.status === "locked" ? "" : stars(l.stars)}
        </button>`).join("")}</div>
      ${ch.id === 1 ? `<div class="signature-card">
        <div class="sigimg"><img src="${IMG}motifs/m3.png" alt="Гжельская ваза">
          <button class="trace" data-act="secret" data-id="gzhel-signature" aria-label="Что-то у основания вазы">
            <svg viewBox="0 0 24 10" aria-hidden="true"><path d="M2 6c3-6 5 4 8-1s3 4 7 0" fill="none" stroke="${found ? "#C8372D" : "#1E3A9E"}" stroke-width="1.6" stroke-linecap="round" opacity="${found ? 1 : .35}"/></svg>
          </button></div>
        <p>${found ? "Подпись мастера найдена и записана в Атлас." : "Мастера иногда оставляли на посуде подписи. Присмотрись к вазе — вдруг что-то спрятано у основания?"}</p>
      </div>` : ""}
    </section>`;
  },

  /* выбор одного из трёх заданий */
  level() {
    const lv = findLevel(S.levelId);
    return `<section class="screen">
      <button class="back" data-act="back-chapter">‹ К главе</button>
      <h1>${esc(lv.title)}</h1>
      ${buddy(lv.intro)}
      <h3>Выбери задание</h3>
      <div class="tasks">${lv.tasks.map(t => `
        <button class="taskcard ${t.stars ? "done" : ""}" data-act="task" data-task="${t.id}">
          <span class="ico">${TASK_ICON[t.id]}</span>
          <span class="t"><b>${esc(t.title)}</b><span>${esc(t.desc)}</span></span>
          ${t.stars ? stars(t.stars, 18) : ""}
        </button>`).join("")}</div>
      <p class="muted small">Достаточно пройти любое одно задание. Остальные можно пройти позже ради бонусных искорок.</p>
    </section>`;
  },

  task() {
    const T = S.task, v = S.tk;
    const body = T.task === "puzzle" ? puzzleBody() : T.task === "memory" ? memoryBody() : colorBody();
    const hintOff = S.st.sparks < S.st.hint_cost || v.busy || v.done;
    return `<section class="screen">
      <button class="back" data-act="back-level">‹ К заданиям</button>
      <h1>${esc(T.task === "color" ? T.subtitle : T.title)}</h1>
      ${buddy(v.msg)}
      ${body}
      <div class="lv-actions">
        <button class="btn ghost sm" data-act="ref">Справка Атласа</button>
        <button class="btn ghost sm" data-act="hint" ${hintOff ? "disabled" : ""}>Подсказка <span class="price">${S.st.hint_cost} ${sparkIcon(14)}</span></button>
      </div>
      ${v.showRef ? `<div class="ref"><b>Справка Атласа</b>${esc(T.reference)}</div>` : ""}
    </section>`;
  },

  atlas() {
    const framed = S.st.items.includes("frame");
    return `<section class="screen">
      <h1>Атлас узоров</h1>
      ${S.st.atlas.map(p => p.unlocked ? `
        <article class="page ${framed ? "framed" : ""}">
          <span class="region">${esc(p.region)}</span><h2>${esc(p.title)}</h2>
          <ul>${p.facts.map(f => `<li>${esc(f)}</li>`).join("")}</ul>
        </article>` : `
        <article class="page blank"><span class="region">${esc(p.region)}</span>
          <p>Страница пуста: нить оборвана. Восстановите узор этого региона.</p></article>`).join("")}
    </section>`;
  },

  shop() {
    const st = S.st;
    const groups = [...new Set(st.shop.map(i => i.category))];
    return `<section class="screen">
      <h1>Лавка</h1>
      <p class="muted small">Искорки тратятся только на украшения и необязательные подсказки. Сюжет от покупок не зависит.</p>
      ${groups.map(g => `<h3 class="group-title">${esc(g)}</h3>${st.shop.filter(i => i.category === g).map(i => `
        <div class="item"><div class="t"><b>${esc(i.title)}</b><span>${esc(i.desc)}</span></div>
          ${i.owned ? `<span class="muted small">Куплено</span>`
            : `<button class="btn sm" data-act="buy" data-id="${i.id}" ${st.sparks < i.price ? "disabled" : ""}><span class="price">${i.price} ${sparkIcon(14)}</span></button>`}
        </div>`).join("")}`).join("")}
    </section>`;
  },
};

/* ---------- задание 1: пазл 10x10 ---------- */
function puzzleBody() {
  const T = S.task, v = S.tk, n = T.grid * T.grid;
  return `<div class="pzbar"><span id="pz-count"></span><button class="linkbtn" data-act="peek">${v.peek ? "Скрыть образец" : "Образец"}</button></div>
    ${v.peek ? `<img class="thumb" src="${esc(T.image)}" alt="Образец узора">` : ""}
    <div class="pz" id="pz" style="--img:url('${esc(T.image)}');--g:${T.grid}">${Array.from({length: n}, (_, i) =>
      `<button class="pc" data-act="pz" data-pos="${i}" aria-label="Кусочек ${i + 1}"></button>`).join("")}</div>`;
}

function paintBoard() {
  const T = S.task, v = S.tk, g = T.grid;
  let ok = 0;
  document.querySelectorAll("#pz .pc").forEach((el, pos) => {
    const piece = v.order[pos];
    el.style.backgroundPosition = `${(piece % g) * 100 / (g - 1)}% ${Math.floor(piece / g) * 100 / (g - 1)}%`;
    const locked = piece === pos;
    if (locked) ok++;
    el.classList.toggle("locked", locked);
    el.classList.toggle("sel", v.sel === pos);
  });
  const c = $("#pz-count");
  if (c) c.textContent = `Собрано ${ok} из ${g * g}`;
}

async function submitPuzzle() {
  const v = S.tk;
  v.busy = true;
  try {
    const r = await api(`level/${S.task.level}/check`, {order: v.order});
    if (r.correct) { v.done = true; v.busy = false; v.msg = "Узор собран!"; render(); setTimeout(() => finish(r.result), 700); return; }
    v.msg = "Что-то не сходится. Проверь кусочки по образцу.";
  } catch (e) { toast(e.message); }
  v.busy = false;
  render();
}

/* ---------- задание 2: найди пару ---------- */
const sleep = ms => new Promise(r => setTimeout(r, ms));

function memoryBody() {
  const T = S.task;
  const cols = T.count === 10 ? 5 : 4;
  return `<div class="pzbar"><span id="mm-count"></span></div>
    <div class="mem" style="--cols:${cols}">${Array.from({length: T.count}, (_, i) =>
      `<button class="mc" data-act="mflip" data-pos="${i}" aria-label="Карточка ${i + 1}"><span class="mcin"><span class="mback"></span><span class="mface"><img alt=""></span></span></button>`).join("")}</div>`;
}

function paintMemory() {
  const T = S.task, v = S.tk;
  document.querySelectorAll(".mc").forEach((el, i) => {
    const gone = v.gone.has(i);
    el.classList.toggle("gone", gone);
    el.classList.toggle("up", gone || v.up.has(i));
    el.disabled = gone;
    const img = el.querySelector("img"), face = v.faces[i];
    if (face && img.dataset.f !== String(face)) { img.src = `${IMG}motifs/m${face}.png`; img.dataset.f = face; }
  });
  const c = $("#mm-count");
  if (c) c.textContent = `Найдено пар: ${v.gone.size / 2} из ${T.pairs} · промахов: ${v.misses}`;
}

/* ---------- задание 3: раскраска ---------- */
const shadeColor = id => (S.task.shades.find(s => s.id === id) || {}).color;

function regionStyle(rid) {
  const f = S.tk.fills[rid];
  return f ? `fill:${shadeColor(f)};stroke:${shadeColor(f)}` : `fill:${EMPTY_FILL};stroke:${EMPTY_LINE}`;
}

function colorBody() {
  const T = S.task, v = S.tk, d = v.data;
  return `<div class="pzbar"><span id="cl-count"></span>
      <span><button class="linkbtn" data-act="peek">${v.peek ? "Скрыть образец" : "Образец"}</button>
      <button class="linkbtn" data-act="zoom">${v.zoom > 1 ? "Уменьшить" : "Увеличить"}</button></span></div>
    ${v.peek ? `<img class="thumb" src="${esc(T.ref)}" alt="Образец мастера">` : ""}
    <div class="tilecard paintwrap"><svg class="paint" viewBox="${d.vb.join(" ")}" style="width:${v.zoom * 100}%" role="img" aria-label="Раскраска: ${esc(T.subtitle)}">
      ${d.regions.map(r => `<path class="rg" data-act="fill" data-id="${r.id}" d="${r.d}" fill-rule="evenodd" style="${regionStyle(r.id)}"/>`).join("")}
    </svg></div>
    <div class="palette" role="group" aria-label="Оттенки">
      ${T.shades.map(s => `<button class="sw" data-act="shade" data-id="${s.id}" style="background:${s.color}" aria-label="${esc(s.label)}"></button>`).join("")}
      <button class="sw eraser" data-act="shade" data-id="" aria-label="Ластик">Ластик</button>
    </div>
    <p class="shadename" id="shadename"></p>
    <button class="btn block" id="cl-done" data-act="check">Готово</button>`;
}

function paintColorUI() {
  const T = S.task, v = S.tk;
  const req = v.data.regions.filter(r => r.required);
  const filled = req.filter(r => v.fills[r.id]).length;
  const c = $("#cl-count");
  if (c) c.textContent = `Закрашено ${filled} из ${req.length}`;
  const b = $("#cl-done");
  if (b) b.disabled = filled < req.length || v.busy || v.done;
  document.querySelectorAll(".sw").forEach(el => el.setAttribute("aria-pressed", String((el.dataset.id || "") === (v.shade || ""))));
  const nm = $("#shadename");
  if (nm) nm.textContent = v.shade ? (T.shades.find(s => s.id === v.shade) || {}).label : "Ластик";
}

/* ---------- окна ---------- */
function modalHtml() {
  const m = S.modal;
  if (!m) return "";
  if (m.type === "result") {
    const r = m.data;
    const rewards = r.rewards.length
      ? `<ul class="rewards">${r.rewards.map(x => `<li><span>${esc(x.label)}</span><b>+${x.sparks} ${sparkIcon(14)}</b></li>`).join("")}</ul>`
      : `<p class="muted" style="text-align:center">Награды за этот результат уже получены.</p>`;
    const acc = r.accuracy !== undefined ? `<p class="muted" style="text-align:center">Совпадение с образцом мастера: ${r.accuracy}%</p>` : "";
    const line = r.stars === 3 ? "Блестяще! Мастер бы гордился." : "Узор снова целый. А можно ли ещё лучше?";
    const label = r.chapter_done ? "Дальше" : (r.next_level ? "Следующий уровень" : "К главе");
    return `<div class="sheet" role="dialog" aria-modal="true" aria-label="Результат">
      ${stars(r.stars, 44)}
      <h2>Задание выполнено</h2>
      ${acc}${rewards}
      ${buddy(line)}
      <button class="btn block" data-act="result-next">${label}</button>
      ${r.chapter_done || !r.next_level ? "" : `<button class="btn ghost block" data-act="back-chapter">К главе</button>`}
    </div>`;
  }
  const c = m.data;
  return `<div class="sheet" role="dialog" aria-modal="true" aria-label="Глава завершена">
    <h2>Глава «${esc(c.title)}» завершена</h2>
    <div class="tilecard"><img src="${IMG}motifs/m3.png" alt="Гжельская ваза"></div>
    <ul class="rewards">
      <li><span>Золотая нить</span><b>+1 ${threadIcon(14)}</b></li>
      ${c.artifact ? `<li><span>Экспонат</span><b>${esc(c.artifact)}</b></li>` : ""}
      ${c.page ? `<li><span>Страница Атласа</span><b>${esc(c.page)}</b></li>` : ""}
    </ul>
    ${buddy(c.next_ready ? "Следующая нить уже зовёт!" : "Продолжение истории — скоро. А пока можно обставить мастерскую.")}
    <button class="btn block" data-act="to-workshop">В мастерскую</button>
    <button class="btn ghost block" data-act="to-atlas">Открыть Атлас</button>
  </div>`;
}

/* ---------- отрисовка ---------- */
const TABS = [
  ["workshop", "Мастерская", '<path d="M3 11l9-7 9 7v9H3z"/><path d="M10 20v-6h4v6"/>'],
  ["map", "Карта", '<path d="M3 6l6-2 6 2 6-2v14l-6 2-6-2-6 2z"/><path d="M9 4v14M15 6v14"/>'],
  ["atlas", "Атлас", '<path d="M5 4h11a3 3 0 0 1 3 3v13H8a3 3 0 0 1-3-3z"/><path d="M5 17a3 3 0 0 1 3-3h11"/>'],
  ["shop", "Лавка", '<path d="M5 8h14l-1 12H6z"/><path d="M9 8V6a3 3 0 0 1 6 0v2"/>'],
];

function render() {
  const st = S.st;
  const intro = ["welcome", "story", "name"].includes(S.screen);
  const top = $("#topbar");
  top.hidden = intro || !st;
  if (!top.hidden) {
    top.innerHTML = `<div class="bar"><span class="brand">${esc(st.name || "Нити времени")}</span>
      <span class="chips"><span class="chip" aria-label="Искорки памяти">${sparkIcon()} ${st.sparks}</span>
      <span class="chip" aria-label="Золотые нити">${threadIcon()} ${st.threads}</span></span></div><div class="stitch"></div>`;
  }
  const scr = $("#screen"), keep = scr.scrollTop;
  scr.innerHTML = views[S.screen]();
  scr.scrollTop = keep;
  if (S.screen === "task") {
    if (S.task.task === "puzzle") paintBoard();
    if (S.task.task === "memory") paintMemory();
    if (S.task.task === "color") paintColorUI();
  }

  const tabs = $("#tabs");
  const showTabs = ["workshop", "map", "chapter", "atlas", "shop"].includes(S.screen);
  tabs.hidden = !showTabs;
  if (showTabs) {
    const active = S.screen === "chapter" ? "map" : S.screen;
    tabs.innerHTML = TABS.map(([id, label, icon]) =>
      `<button data-act="tab" data-id="${id}" ${id === active ? 'aria-current="page"' : ""}><svg viewBox="0 0 24 24" aria-hidden="true">${icon}</svg>${label}</button>`).join("");
  }
  const modal = $("#modal");
  modal.hidden = !S.modal;
  modal.innerHTML = modalHtml();
}

function nextLevel() {
  for (const ch of S.st.chapters) {
    if (ch.status !== "open") continue;
    const l = ch.levels.find(l => l.status === "open");
    if (l) return l;
  }
  return null;
}

/* ---------- действия ---------- */
const START_MSG = {
  puzzle: "Коснись двух кусочков — и они поменяются местами. Верные кусочки закрепятся сами.",
  memory: "Переверни две карточки. Совпали — исчезнут, нет — перевернутся обратно. Запоминай!",
  color: "Выбери оттенок и коснись области. Образец мастера всегда под рукой.",
};

async function openTask(taskId) {
  try {
    const d = await api(`level/${S.levelId}/start`, {task: taskId});
    S.st.sparks = d.sparks;
    const T = d.task;
    const v = {msg: START_MSG[T.task], busy: false, done: false, showRef: false, peek: false};
    if (T.task === "puzzle") Object.assign(v, {order: T.order.slice(), sel: null});
    if (T.task === "memory") Object.assign(v, {faces: {}, up: new Set(), gone: new Set(T.found), first: null, misses: T.misses});
    if (T.task === "color") {
      const data = await (await fetch(T.json)).json();
      Object.assign(v, {data, fills: {}, shade: T.shades[2].id, zoom: 1});
    }
    S.task = T; S.tk = v;
    go("task");
  } catch (e) { toast(e.message); }
}

async function finish(data) {
  await loadState();
  S.modal = {type: "result", data};
  render();
}

const actions = {
  start: () => go("story", {step: 0}),
  "story-next": () => S.step < STORY.length - 1 ? go("story", {step: S.step + 1}) : go("name"),

  async "name-submit"() {
    const name = ($("#name").value || "").trim();
    if (!name) return toast("Введите имя.");
    try { S.st = await api("start", {name}); go("workshop"); } catch (e) { toast(e.message); }
  },

  tab: el => go(el.dataset.id),

  chapter(el) {
    const ch = S.st.chapters[+el.dataset.id - 1];
    if (ch.status === "locked") return toast(`Сначала завершите главу ${ch.id - 1}.`);
    if (ch.status === "soon") return toast("Эта глава появится в следующей версии.");
    go("chapter", {chapter: ch.id});
  },

  level(el) {
    const lv = findLevel(el.dataset.id);
    if (lv && lv.status === "locked") return toast("Сначала пройдите предыдущий уровень.");
    go("level", {levelId: el.dataset.id});
  },

  task: el => openTask(el.dataset.task),

  "back-level"() { S.modal = null; go("level"); },
  "back-chapter"() { S.modal = null; go("chapter", {chapter: S.levelId ? +S.levelId.split("-")[0] : 1}); },

  ref() { S.tk.showRef = !S.tk.showRef; render(); },
  peek() { S.tk.peek = !S.tk.peek; render(); },

  async hint() {
    const v = S.tk, T = S.task;
    if (v.busy) return;
    const body = T.task === "puzzle" ? {order: v.order} : T.task === "memory" ? {} : {fills: v.fills};
    v.busy = true;
    try {
      const h = await api(`level/${T.level}/hint`, body);
      S.st.sparks = h.sparks;
      v.msg = h.text;
      if (h.place) {
        const {piece, pos} = h.place, from = v.order.indexOf(piece);
        [v.order[from], v.order[pos]] = [v.order[pos], v.order[from]];
        v.sel = null;
      }
      if (h.reveal) v.fills[h.reveal.region] = h.reveal.shade;
      if (h.show) {                                   // память: на 1,6 с показываем пару
        render();
        h.show.forEach(s => { v.faces[s.pos] = s.card; v.up.add(s.pos); });
        paintMemory();
        await sleep(1600);
        h.show.forEach(s => v.up.delete(s.pos));
      }
    } catch (e) { v.msg = e.message; }
    v.busy = false;
    render();
    if (T.task === "puzzle" && v.order.every((p, i) => p === i)) submitPuzzle();
  },

  /* пазл */
  pz(el) {
    const v = S.tk, pos = +el.dataset.pos;
    if (v.busy || v.done || v.order[pos] === pos) return;
    if (v.sel === null) v.sel = pos;
    else if (v.sel === pos) v.sel = null;
    else { [v.order[v.sel], v.order[pos]] = [v.order[pos], v.order[v.sel]]; v.sel = null; }
    paintBoard();
    if (v.order.every((p, i) => p === i)) submitPuzzle();
  },

  /* найди пару */
  async mflip(el) {
    const v = S.tk, T = S.task, pos = +el.dataset.pos;
    if (v.busy || v.done || v.gone.has(pos) || v.up.has(pos)) return;
    v.busy = true;
    try {
      const r = await api(`level/${T.level}/check`, {flip: pos});
      v.faces[pos] = r.card;
      v.up.add(pos);
      paintMemory();
      if (r.match === undefined) { v.first = pos; v.busy = false; return; }   // первая карточка хода
      const a = v.first;
      v.first = null;
      v.misses = r.misses;
      if (r.match) {
        const info = T.info[r.card];
        v.msg = `Пара! ${info.name}. ${info.fact}`;
        await sleep(650);
        v.up.delete(a); v.up.delete(pos);
        v.gone.add(a); v.gone.add(pos);
        paintMemory();
        if (r.result) { v.done = true; await sleep(500); render(); await sleep(300); finish(r.result); return; }
      } else {
        v.msg = "Не пара. Запомни, где что лежит.";
        await sleep(950);
        v.up.delete(a); v.up.delete(pos);
        paintMemory();
      }
      await sleep(300);
    } catch (e) { toast(e.message); }
    v.busy = false;
    render();
  },

  /* раскраска */
  shade(el) { S.tk.shade = el.dataset.id || null; paintColorUI(); },
  zoom() { S.tk.zoom = S.tk.zoom > 1 ? 1 : 2; render(); },
  fill(el) {
    const v = S.tk;
    if (v.busy || v.done) return;
    const rid = el.dataset.id;
    if (v.shade) v.fills[rid] = v.shade; else delete v.fills[rid];
    el.setAttribute("style", regionStyle(rid));
    paintColorUI();
  },

  async check() {
    const v = S.tk, T = S.task;
    if (v.busy) return;
    v.busy = true;
    paintColorUI();
    try {
      const r = await api(`level/${T.level}/check`, {fills: v.fills});
      if (r.correct) { v.done = true; v.busy = false; v.msg = "Готово! Какая красота."; render(); setTimeout(() => finish(r.result), 650); return; }
    } catch (e) { toast(e.message); }
    v.busy = false;
    render();
  },

  async secret(el) {
    try {
      const r = await api(`secret/${el.dataset.id}`, {});
      await loadState();
      render();
      toast(r.new ? `${r.text} +${r.reward} искорок` : r.text);
    } catch (e) { toast(e.message); }
  },

  async buy(el) {
    try { await api("shop/buy", {item: el.dataset.id}); await loadState(); render(); toast("Куплено. Загляните в мастерскую."); }
    catch (e) { toast(e.message); }
  },

  "result-next"() {
    const r = S.modal.data;
    S.modal = null;
    if (r.chapter_done) { S.modal = {type: "chapter", data: r.chapter_done}; return render(); }
    if (r.next_level) go("level", {levelId: r.next_level});
    else go("chapter", {chapter: +S.levelId.split("-")[0]});
  },
  "to-workshop"() { S.modal = null; go("workshop"); },
  "to-atlas"() { S.modal = null; go("atlas"); },

  async reset() {
    if (!confirm("Стереть весь прогресс и начать заново?")) return;
    try { await api("reset", {}); await loadState(); S.name = ""; S.levelId = null; S.task = S.tk = null; go("welcome"); }
    catch (e) { toast(e.message); }
  },
};

document.addEventListener("click", e => {
  const el = e.target.closest("[data-act]");
  if (!el || el.disabled) return;
  const fn = actions[el.dataset.act];
  if (fn) fn(el);
});
document.addEventListener("keydown", e => {
  if (e.key === "Enter" && e.target.id === "name") actions["name-submit"]();
});
document.addEventListener("input", e => { if (e.target.id === "name") S.name = e.target.value; });

(async function init() {
  try { await loadState(); } catch (e) { $("#screen").textContent = e.message; return; }
  S.screen = S.st.name ? "workshop" : "welcome";
  render();
})();
})();
