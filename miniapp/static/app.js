// miniapp/static/app.js

const tg = window.Telegram?.WebApp;
if (tg) tg.ready();

const usdtBalEl = document.getElementById("usdtBal");

// ✅ win баланс убран — но элемент может остаться в старом HTML.
// Мы безопасно прячем/игнорируем его, чтобы ничего не ломалось.
const winBalEl  = document.getElementById("winBal");
const wheelBalEl = document.getElementById("wheelBal");
const toastEl   = document.getElementById("toast");

// Старый вертикальный барабан был удалён из разметки, поэтому элемент с id="wheel" отсутствует.
// Мы оставляем переменную для обратной совместимости, но она не используется.
const wheelEl   = null;

// Ссылка на SVG-контейнер кругового колеса. Доступен после загрузки DOM.
const circleWheelSvg = document.getElementById("circleWheelSVG");
const spinBtn   = document.getElementById("spinBtn");
const autoBtn   = document.getElementById("autoBtn"); // если удалил из html — не мешает

let spinning = false;
let autoOn = false;
let autoTimer = null;

// Текущий угол поворота кругового колеса. При накоплении вращений мы
// учитываем эту величину, чтобы последующие спины начинались с правильного угла.
let wheelRotation = 0;

// ===== Фоновая музыка =====
const CUSTOM_AUDIO_SRC = "/miniapp/static/custom-music.mp3";
let bgAudio = null;

function startBackgroundMusic() {
  if (bgAudio) {
    bgAudio.play().catch(() => {});
    return;
  }
  try {
    bgAudio = new Audio(CUSTOM_AUDIO_SRC);
    bgAudio.loop = true;
    bgAudio.volume = 0.2;
    bgAudio.play().catch(() => {});
  } catch (e) {
    console.warn("BGM play failed", e);
  }
}

document.addEventListener("click", () => startBackgroundMusic(), { once: true });
document.addEventListener("touchstart", () => startBackgroundMusic(), { once: true });

// порядок должен совпадать с backend
let wheelValues = [100, 250, 50, 25, 10, 5, 2, 1, 1.2, 0.5, 0.7];

/* ===== Win modal (visual only) ===== */
const winModalEl  = document.getElementById("winModal");
const winAmountEl = document.getElementById("winAmount");
const winCloseEl  = document.getElementById("winClose");

function fmt(x){ return Number(x || 0).toFixed(2); }

function showWinModal(win){
  if (!winModalEl || !winAmountEl) return;
  winAmountEl.textContent = fmt(win);
  winModalEl.classList.add("show");
  winModalEl.setAttribute("aria-hidden", "false");
  tg?.HapticFeedback?.notificationOccurred?.("success");
}
function hideWinModal(){
  if (!winModalEl) return;
  winModalEl.classList.remove("show");
  winModalEl.setAttribute("aria-hidden", "true");
}
if (winCloseEl) winCloseEl.addEventListener("click", hideWinModal);
if (winModalEl){
  winModalEl.addEventListener("click", (e) => {
    if (e.target === winModalEl || e.target.classList?.contains("win-backdrop")) hideWinModal();
  });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") hideWinModal(); });
}

function toast(msg){
  if (!toastEl) return;
  toastEl.textContent = msg;
  toastEl.classList.add("show");
  setTimeout(() => toastEl.classList.remove("show"), 1800);
}

function getInitData(){
  return (window.__tgInitData || tg?.initData || "").trim();
}
async function waitForInitData(timeoutMs = 2000){
  const start = Date.now();
  while (Date.now() - start < timeoutMs){
    const d = getInitData();
    if (d && d.length > 10) return d;
    await new Promise(r => setTimeout(r, 100));
  }
  return getInitData();
}

function buildHeaders(initData){
  const h = { "X-Tg-InitData": initData };
  if (initData) h["Authorization"] = `tma ${initData}`;
  return h;
}
async function safeJson(res){
  try { return await res.json(); }
  catch { return { ok: false, error: "bad_json" }; }
}
async function apiPost(path, body){
  const initData = getInitData();
  const payload = { ...(body || {}) };
  if (initData && !payload.initData) payload.initData = initData;

  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...buildHeaders(initData) },
    body: JSON.stringify(payload),
  });

  const data = await safeJson(res);
  if (typeof data.ok === "undefined") data.ok = res.ok;
  if (!res.ok && !data.error) data.error = `http_${res.status}`;
  return data;
}

function _hideWinBalanceUI(){
  // ✅ если в HTML остался блок/строка "winBal" — прячем, чтобы не путало
  if (!winBalEl) return;
  const wrap = winBalEl.closest(".balance-sub") || winBalEl.parentElement;
  if (wrap) wrap.style.display = "none";
}

async function refreshMe(){
  const r = await apiPost("/api/me", {});
  if (!r.ok){
    toast(r.error === "unauthorized" || r.error === "http_401"
      ? "Ошибка авторизации (открой MiniApp из бота)"
      : "Ошибка авторизации Mini App");
    return;
  }
  if (usdtBalEl) usdtBalEl.textContent = fmt(r.usdt_balance);

  // ✅ win_balance больше не приходит из backend — не трогаем
  if (wheelBalEl) wheelBalEl.textContent = fmt(r.usdt_balance);
}

/* ===== Tabs ===== */
function setTab(tab){
  document.querySelectorAll(".tab").forEach(b => b.classList.remove("active"));
  document.querySelectorAll(".panel").forEach(p => p.classList.remove("active"));

  document.querySelector(`.tab[data-tab="${tab}"]`)?.classList.add("active");
  document.getElementById(`tab-${tab}`)?.classList.add("active");

  hideWinModal();
}
document.querySelectorAll(".tab").forEach(btn => {
  btn.addEventListener("click", () => setTab(btn.dataset.tab));
});

/* ===== Explosion FX (visual only) ===== */
function burstAtElement(el){
  if (!el) return;
  const rect = el.getBoundingClientRect();
  const cx = rect.left + rect.width / 2;
  const cy = rect.top + rect.height / 2;

  const layer = document.createElement("div");
  layer.className = "fx-burst";
  document.body.appendChild(layer);

  const colors = [
    "#ffe07a", "#4ab4ff", "#29d3c4", "#ff65de",
    "#61df7c", "#9a5bff", "#b8c3d6", "#ff9b55"
  ];
  const count = 24;
  for (let i = 0; i < count; i++){
    const s = document.createElement("span");
    s.className = "confetti";
    const color = colors[Math.floor(Math.random() * colors.length)];
    s.style.backgroundColor = color;

    const w = 6 + Math.random() * 5;
    const h = 4 + Math.random() * 4;
    s.style.width = `${w}px`;
    s.style.height = `${h}px`;

    const ang = Math.random() * Math.PI * 2;
    const dist = 60 + Math.random() * 80;
    const dx = Math.cos(ang) * dist;
    const dy = Math.sin(ang) * dist;

    const rot = `${Math.floor(Math.random() * 360 - 180)}deg`;
    s.style.left = `${cx}px`;
    s.style.top  = `${cy}px`;
    s.style.setProperty("--dx", `${dx}px`);
    s.style.setProperty("--dy", `${dy}px`);
    s.style.setProperty("--dr", rot);
    layer.appendChild(s);
  }
  setTimeout(() => layer.remove(), 900);
}

/* ===== Boxes effects (visual only) ===== */
function boxAnimStart(card){
  if (!card) return;
  card.classList.remove("is-opened");
  card.classList.add("is-opening");
  card.disabled = true;
}
function boxAnimEnd(card, ok){
  if (!card) return;
  card.classList.remove("is-opening");
  if (ok) card.classList.add("is-opened");
  card.disabled = false;
}

document.querySelectorAll(".card").forEach(card => {
  card.addEventListener("click", async () => {
    const tier = parseInt(card.dataset.tier, 10);

    boxAnimStart(card);

    const r = await apiPost("/api/box/open", { tier });

    if (!r.ok){
      boxAnimEnd(card, false);
      if (r.error === "insufficient_usdt") toast("Недостаточно USDT");
      else if (r.error === "unauthorized" || r.error === "http_401") toast("Нет авторизации (открой MiniApp из бота)");
      else toast("Ошибка открытия");
      return;
    }

    // ✅ обновляем только основной баланс
    if (usdtBalEl) usdtBalEl.textContent = fmt(r.usdt_balance);
    if (wheelBalEl) wheelBalEl.textContent = fmt(r.usdt_balance);

    burstAtElement(card);
    tg?.HapticFeedback?.impactOccurred?.("heavy");

    boxAnimEnd(card, true);

    setTimeout(() => {
      toast(`Выигрыш: ${fmt(r.win)} USDT`);
      showWinModal(r.win);
    }, 420);
  });
});

/* ===== Roulette tickets rendering (legacy, not used) ===== */
let ticketHeightPx = 148;
let baseLoop = 12;
let currentOffset = 0;

function ticketClassByValue(v){
  const n = Number(v);
  if (n >= 50) return "gold";
  if (n >= 10) return "blue";
  if (n >= 2) return "teal";
  if (n >= 1) return "green";
  if (n >= 0.7) return "purple";
  if (n >= 0.5) return "gray";
  return "pink";
}

const wheelColorMap = {
  gold:   "#ffe07a",
  blue:   "#4ab4ff",
  teal:   "#29d3c4",
  green:  "#61df7c",
  purple: "#9a5bff",
  gray:   "#b8c3d6",
  pink:   "#ff65de"
};

const WHEEL_BASE_COLOR = "#4ab4ff";

function shadeColor(color, amt) {
  let col = color.replace("#", "");
  let num = parseInt(col, 16);
  let r = (num >> 16) + amt;
  let g = ((num >> 8) & 0x00FF) + amt;
  let b = (num & 0x0000FF) + amt;
  r = Math.max(0, Math.min(255, r));
  g = Math.max(0, Math.min(255, g));
  b = Math.max(0, Math.min(255, b));
  return "#" + ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1);
}

function polarToCartesian(cx, cy, radius, angleInDegrees){
  const rad = (angleInDegrees - 90) * Math.PI / 180.0;
  return {
    x: cx + radius * Math.cos(rad),
    y: cy + radius * Math.sin(rad)
  };
}

function describeArc(cx, cy, radius, startAngle, endAngle){
  const start = polarToCartesian(cx, cy, radius, endAngle);
  const end   = polarToCartesian(cx, cy, radius, startAngle);
  const largeArcFlag = endAngle - startAngle <= 180 ? "0" : "1";
  return [
    "M", start.x, start.y,
    "A", radius, radius, 0, largeArcFlag, 0, end.x, end.y,
    "L", cx, cy,
    "Z"
  ].join(" ");
}

function renderWheel(values){
  if (!circleWheelSvg) return;
  const n = values.length;
  const cx = 300;
  const cy = 300;
  const radius = 280;
  const labelRadius = 200;
  const anglePer = 360 / n;
  const parts = [];
  const texts = [];
  for (let i = 0; i < n; i++){
    const startAngle = i * anglePer;
    const endAngle   = (i + 1) * anglePer;
    const d = describeArc(cx, cy, radius, startAngle, endAngle);
    const stepCount = Math.max(1, n - 1);
    const amt = Math.round(((i / stepCount) - 0.5) * 80);
    const fillColor = shadeColor(WHEEL_BASE_COLOR, amt);
    parts.push(`<path d="${d}" fill="${fillColor}" stroke="rgba(0,0,0,0.15)" stroke-width="2" />`);
    const midAngle = startAngle + anglePer / 2;
    const pt = polarToCartesian(cx, cy, labelRadius, midAngle);
    const val = String(values[i]);
    texts.push(`<text x="${pt.x}" y="${pt.y}" fill="#05121c" font-size="24" font-weight="900" dominant-baseline="middle" text-anchor="middle">${val}</text>`);
  }
  circleWheelSvg.innerHTML = parts.concat(texts).join("");
  circleWheelSvg.style.transition = "none";
  circleWheelSvg.style.transform = `rotate(${wheelRotation}deg)`;
  circleWheelSvg.getBoundingClientRect();
  circleWheelSvg.style.transition = "";
}

function findIndexForWin(win){
  const n = wheelValues.length;
  const winNum = Number(win);

  let idx = wheelValues.indexOf(win);
  if (idx === -1) idx = wheelValues.indexOf(winNum);
  if (idx === -1) idx = 0;
  return idx % n;
}

function spinWheelToWin(win){
  if (!circleWheelSvg) return;
  const n = wheelValues.length;
  const idx = findIndexForWin(win);
  const anglePer = 360 / n;
  const centerAngle = (idx + 0.5) * anglePer;
  const extraSpins = 3;
  const targetRotation = extraSpins * 360 - centerAngle;
  const finalRotation = wheelRotation + targetRotation;
  wheelRotation = finalRotation;
  circleWheelSvg.style.transition = "transform 4.2s cubic-bezier(.15,.85,.05,1)";
  circleWheelSvg.style.transform = `rotate(${finalRotation}deg)`;
  setTimeout(() => {
    tg?.HapticFeedback?.impactOccurred?.("heavy");
    circleWheelSvg.style.transition = "transform 120ms ease-out";
    circleWheelSvg.style.transform = `rotate(${finalRotation + 8}deg)`;
    setTimeout(() => {
      circleWheelSvg.style.transform = `rotate(${finalRotation}deg)`;
    }, 120);
  }, 4250);
}

/* ===== Auto spin ===== */
function stopAuto(){
  autoOn = false;
  autoBtn?.classList.remove("on");
  if (autoTimer) clearTimeout(autoTimer);
  autoTimer = null;
}
function scheduleNextAuto(){
  if (!autoOn) return;
  autoTimer = setTimeout(() => {
    if (!autoOn) return;
    if (!spinning) spinBtn?.click();
    scheduleNextAuto();
  }, 5200);
}
if (autoBtn){
  autoBtn.addEventListener("click", () => {
    autoOn = !autoOn;
    autoBtn.classList.toggle("on", autoOn);
    if (autoOn) scheduleNextAuto();
    else stopAuto();
  });
}

/* ===== Spin button ===== */
async function doSpin(){
  if (spinning) return;
  spinning = true;
  spinBtn.disabled = true;

  const r = await apiPost("/api/wheel/spin", {});
  if (!r.ok){
    if (r.error === "insufficient_usdt") toast("Недостаточно USDT");
    else if (r.error === "unauthorized" || r.error === "http_401") toast("Нет авторизации (открой MiniApp из бота)");
    else toast("Ошибка спина");

    spinning = false;
    spinBtn.disabled = false;
    stopAuto();
    return;
  }

  // ⚠️ новые значения перерисуем только ПОСЛЕ анимации
  let pendingWheelValues = null;
  if (Array.isArray(r.wheel_values)) pendingWheelValues = r.wheel_values;

  spinWheelToWin(r.win);

  setTimeout(() => {
    if (usdtBalEl) usdtBalEl.textContent = fmt(r.usdt_balance);
    if (wheelBalEl) wheelBalEl.textContent = fmt(r.usdt_balance);

    toast(`Выигрыш: ${fmt(r.win)} USDT`);
    showWinModal(r.win);

    tg?.HapticFeedback?.impactOccurred?.("medium");

    if (pendingWheelValues) {
      wheelValues = pendingWheelValues;
      renderWheel(wheelValues);
    }

    spinning = false;
    spinBtn.disabled = false;
  }, 4300);
}

if (spinBtn){
  spinBtn.addEventListener("click", doSpin);
}

/* ===== BOOT ===== */
async function boot(){
  const initData = await waitForInitData(2000);
  if (!initData){
    toast("Открой MiniApp через кнопку 🎰 Игры в боте");
    return;
  }

  // ✅ прячем win-баланс, если он остался в старой вёрстке
  _hideWinBalanceUI();

  startBackgroundMusic();

  renderWheel(wheelValues);
  await refreshMe();
}

boot();
