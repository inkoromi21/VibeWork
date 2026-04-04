const STORAGE_KEY = "vibework_result_v6";
const STORAGE_PROFILE_DRAFT = "vibework_profile_draft_v1";
const STORAGE_SWIPES = "vibework_swipes_v1";
/** Серия дней с заходом при заполненном профиле: { lastYmd, count } */
const STORAGE_FOCUS_STREAK = "vibework_focus_streak_v2";

window.lastAnalysis = null;
window.serverLoggedIn = false;
window.serverEmail = null;
let chatMessages = [];
/** Прогресс профиля в шапке — только после разбора (тест пройден) */
let profileProgressUnlocked = false;

const MICRO_TIPS = [
  "Один мини-проект в портфолио ценнее десяти «почти начал».",
  "Спросите у знакомого на 15 минут разбор резюме — свежий взгляд бесценен.",
  "Спросите близких: «Какие сильные стороны ты во мне видишь?» и «С каким вопросом ты точно пришёл бы ко мне за помощью?» — часто подсвечивают то, что вы сами обесцениваете.",
  "Соберитесь с другом и вместе разберите резюме и достижения (body doubling): так проще стартовать.",
  "Страх «сделаю резюме неправильно» снимается структурой и примерами; страх «не возьмут» ближе к страху отказа — тут полезны опора близких или разговор с психологом.",
  "Карьерный консультант чаще про резюме и трек; профориентолог — про «кто я в профессии». Оба могут помочь на разных этапах.",
  "Если тянет к двум трекам — чередуйте недели, а не дни.",
  "Записывайте страхи перед собеседованием: после прочтения через неделю станет смешнее.",
  "Для стажировки важнее любопытство и дедлайны, чем «идеальные» навыки.",
  "Сравнивайте вакансии по обучению на месте, а не только по зарплате в строке.",
  "Если вам важен баланс жизни, вакансии «всегда на связи» быстро выжгут — честно сравнивайте с карьерными ценностями.",
];

function showToast(msg, ms = 4200) {
  const el = document.getElementById("app-toast");
  if (!el) return;
  el.textContent = msg;
  el.hidden = false;
  requestAnimationFrame(() => {
    el.classList.add("show");
  });
  clearTimeout(showToast._t);
  showToast._t = setTimeout(() => {
    el.classList.remove("show");
    setTimeout(() => {
      el.hidden = true;
    }, 400);
  }, ms);
}

function localYmd(d = new Date()) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function prevLocalYmd(ymd) {
  const [y, mo, da] = ymd.split("-").map(Number);
  const dt = new Date(y, mo - 1, da);
  dt.setDate(dt.getDate() - 1);
  return localYmd(dt);
}

/** Учёт календарной серии: не чаще одного шага в день, обрыв если пропущен день. */
function recordFocusStreakDay() {
  if (!profileBasicsOk()) return 0;
  const today = localYmd();
  let data;
  try {
    data = JSON.parse(localStorage.getItem(STORAGE_FOCUS_STREAK) || "null");
  } catch (_) {
    data = null;
  }
  if (!data || typeof data.lastYmd !== "string" || typeof data.count !== "number") {
    data = { lastYmd: today, count: 1 };
  } else if (data.lastYmd === today) {
    /* уже отмечен сегодня */
  } else if (data.lastYmd === prevLocalYmd(today)) {
    data = { lastYmd: today, count: data.count + 1 };
  } else {
    data = { lastYmd: today, count: 1 };
  }
  try {
    localStorage.setItem(STORAGE_FOCUS_STREAK, JSON.stringify(data));
  } catch (_) {}
  return data.count;
}

function updateStreakChip() {
  const chip = document.getElementById("streak-chip");
  if (!chip) return;
  if (!profileBasicsOk()) {
    chip.hidden = true;
    return;
  }
  const n = recordFocusStreakDay();
  chip.textContent = `${Math.min(999, n)}-дн. фокус`;
  chip.hidden = false;
  chip.title = "Подряд календарных дней с заходом в сервис (профиль заполнен)";
}

function updateAvatarBubble() {
  const el = document.getElementById("avatar-bubble");
  if (!el) return;
  const sel = document.getElementById("field-interest");
  const opt = sel?.selectedOptions?.[0];
  const raw = (opt?.text || "VW").trim();
  const initials = raw
    .split(/\s+/)
    .map((w) => w[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
  el.textContent = initials || "VW";
}

function updateHeaderStepper(tab) {
  const dots = document.querySelectorAll(".step-dot");
  if (!dots.length) return;
  const p = profileBasicsOk();
  const q = quizComplete();
  const r = !!window.lastAnalysis;
  dots.forEach((d) => d.classList.remove("step-done", "step-current"));
  if (!p) {
    dots[0].classList.add("step-current");
    return;
  }
  dots[0].classList.add("step-done");
  if (!q) {
    dots[1].classList.add("step-current");
    return;
  }
  dots[1].classList.add("step-done");
  if (!r) {
    dots[2].classList.add("step-current");
    return;
  }
  dots[2].classList.add("step-done");
  if (tab === "ai") {
    dots[3].classList.add("step-current");
  } else if (tab === "jobs" || tab === "sim") {
    dots[4].classList.add("step-current");
  } else if (tab === "test") {
    dots[2].classList.add("step-current");
  } else {
    dots[0].classList.add("step-done", "step-current");
  }
}

function skillsFromAnalysis(a) {
  if (!a?.gap_analysis?.bars) return [];
  const map = {
    "Технические навыки": "программирование",
    "Аналитика и данные": "аналитика",
    "Дизайн и визуал": "дизайн",
    "Коммуникации": "коммуникации",
    "Организация": "организация_и_управление",
  };
  return a.gap_analysis.bars
    .filter((b) => b.user_percent >= 47)
    .map((b) => map[b.label])
    .filter(Boolean);
}

/** Локальный запасной набор, если /api/quiz/questions недоступен */
const QUIZ_FALLBACK = [
  { id: 1, text: "В свободное время вас больше тянет к:", options: [
    { k: "A", t: "разбору данных, задачкам, стратегии в играх" },
    { k: "B", t: "рисованию, монтажу, визуальным экспериментам" },
    { k: "C", t: "общению, чату, организации встреч" },
    { k: "D", t: "сборке моделей, настройке железа, экспериментам" },
  ]},
  { id: 2, text: "В групповом проекте вы чаще:", options: [
    { k: "A", t: "считаете метрики и проверяете логику" },
    { k: "B", t: "отвечаете за визуал и презентацию" },
    { k: "C", t: "договариваетесь с людьми и синхронизируете команду" },
    { k: "D", t: "строите прототип / документируете техчасть" },
  ]},
  { id: 3, text: "Какая ошибка расстроит сильнее?", options: [
    { k: "A", t: "неверный вывод из-за опечатки в расчётах" },
    { k: "B", t: "«плохо смотрится» финальный макет" },
    { k: "C", t: "конфликт или недопонимание в команде" },
    { k: "D", t: "поломка процесса из-за неверной спецификации" },
  ]},
  { id: 4, text: "Что интереснее на ближайший месяц?", options: [
    { k: "A", t: "углубиться в Excel/SQL/Python" },
    { k: "B", t: "собрать мини-портфолио или редизайн" },
    { k: "C", t: "интервью/исследование пользователей" },
    { k: "D", t: "разобрать кейс отрасли и схему процесса" },
  ]},
  { id: 5, text: "Когда вы «в потоке», это скорее:", options: [
    { k: "A", t: "структурируете хаос в таблицы и выводы" },
    { k: "B", t: "перебираете варианты, пока не «щёлкнет»" },
    { k: "C", t: "ведёте диалог и находите компромисс" },
    { k: "D", t: "пошагово доводите задачу до результата" },
  ]},
  { id: 6, text: "Если задача неясна, вы в первую очередь:", options: [
    { k: "A", t: "соберете факты и ограничения, чтобы сузить проблему" },
    { k: "B", t: "поищете нестандартные аналогии и примеры" },
    { k: "C", t: "обсудите ожидания с людьми, которым важен результат" },
    { k: "D", t: "разложите работу по шагам и начнёте с самого безопасного" },
  ]},
  { id: 7, text: "В споре о приоритетах вас убедит скорее:", options: [
    { k: "A", t: "таблица сравнения и критерии" },
    { k: "B", t: "сильная история «зачем так будет лучше»" },
    { k: "C", t: "учёт интересов всех сторон" },
    { k: "D", t: "чёткий план: кто что делает и к какому сроку" },
  ]},
  { id: 8, text: "Что заряжает энергией на целый день:", options: [
    { k: "A", t: "разгадать закономерность или ошибку в данных" },
    { k: "B", t: "сделать вещь, которой не стыдно показать" },
    { k: "C", t: "плодотворный разговор один на один или в группе" },
    { k: "D", t: "закрыть всё по списку без срыва срока" },
  ]},
  { id: 9, text: "Рутинная часть проекта, которую «не хочется»:", options: [
    { k: "A", t: "автоматизирую или упрощу шаблоном" },
    { k: "B", t: "найду способ сделать её выразительнее/интереснее" },
    { k: "C", t: "договорюсь о разделении с кем-то из команды" },
    { k: "D", t: "сделаю ровно по регламенту, без отвлечений" },
  ]},
  { id: 10, text: "Через год хотите честно сказать о себе:", options: [
    { k: "A", t: "«я сильнее разбираюсь в цифрах и системах»" },
    { k: "B", t: "«я создаю работы, которые цепляют людей»" },
    { k: "C", t: "«со мной комфортно вести проекты и переговоры»" },
    { k: "D", t: "«на меня можно положиться с дедлайнами и качеством»" },
  ]},
];

/** Тест 2 — тип личности (id в payload 1–8, на фронте name=pq{id}). */
const PERSONALITY_QUIZ_FALLBACK = [
  { id: 1, text: "В напряжённый период вы чаще восстанавливаетесь через:", options: [
    { k: "A", t: "одиночный разбор: порядок, цифры, план на бумаге" },
    { k: "B", t: "творческий отвод: музыка, образ, что-то «своё» без чек-листа" },
    { k: "C", t: "живое общение: выговориться, посмеяться, синхрон с людьми" },
    { k: "D", t: "закрыть пару конкретных задач по списку — и стало легче" },
  ]},
  { id: 2, text: "Если описать вас одной фразой для команды, ближе:", options: [
    { k: "A", t: "«спокойно докапается до сути и проверяет детали»" },
    { k: "B", t: "«придумает нестандартный ход или подачу»" },
    { k: "C", t: "«сведёт людей и договорится»" },
    { k: "D", t: "«на нём можно зафиксировать процесс и сроки»" },
  ]},
  { id: 3, text: "После конфликта на проекте следующим утром вы скорее:", options: [
    { k: "A", t: "разложу факты: кто что обещал и что по регламенту" },
    { k: "B", t: "подумаю, как бы это выглядело «по-новому» и что можно смягчить" },
    { k: "C", t: "договорюсь о отдельном разговоре без зрителей" },
    { k: "D", t: "зафиксирую next steps в задаче/письме, чтобы не потерять нить" },
  ]},
  { id: 4, text: "Вас сильнее мотивирует ощущение:", options: [
    { k: "A", t: "«всё сошлось по цифрам, логике и критериям»" },
    { k: "B", t: "«это цепляет, свеже, есть характер»" },
    { k: "C", t: "«люди вокруг реально выдохнули или выросли»" },
    { k: "D", t: "«срок выдержан, процесс прозрачен, нет сюрпризов»" },
  ]},
  { id: 5, text: "Вы застреваете чаще, когда:", options: [
    { k: "A", t: "не хватает данных, критериев или ясных правил" },
    { k: "B", t: "нельзя попробовать свой вариант или эксперимент" },
    { k: "C", t: "никто не объясняет «зачем» людям и к чему это их" },
    { k: "D", t: "меняют условия посредине без формализации" },
  ]},
  { id: 6, text: "Новая роль: много неизвестного и мало инструкций. Ваш первый шаг:", options: [
    { k: "A", t: "соберу входные данные и критерии успеха, прежде чем действовать" },
    { k: "B", t: "быстро сделаю черновик/пробу, чтобы «пощупать» задачу" },
    { k: "C", t: "договорюсь о созвоне и ожиданиях с теми, кому важен результат" },
    { k: "D", t: "разложу риски и план на неделю, чтобы не потерять контроль" },
  ]},
  { id: 7, text: "Когда перед вами стоит чужой запрос (клиент, коллега, руководитель), вам проще:", options: [
    { k: "A", t: "формализовать задачу и согласовать метрики" },
    { k: "B", t: "предложить нестандартный ход или визуальную подачу" },
    { k: "C", t: "выяснить контекст людей и договориться о компромиссе" },
    { k: "D", t: "взять ответственность за срок и отчётность по шагам" },
  ]},
  { id: 8, text: "Представьте первый рабочий месяц: что даст больше уверенности?", options: [
    { k: "A", t: "ясные регламенты, доступ к данным и возможность проверять гипотезы" },
    { k: "B", t: "пространство для идей и обратной связи по качеству результата" },
    { k: "C", t: "понятный круг людей и регулярная синхронизация ожиданий" },
    { k: "D", t: "список задач с приоритетами и предсказуемый ритм сдачи" },
  ]},
];

let QUIZ = [...QUIZ_FALLBACK];
let PERSONALITY_QUIZ = [...PERSONALITY_QUIZ_FALLBACK];

const questionStartedAt = {};
const questionStartedAtPersonality = {};

function esc(s) {
  const d = document.createElement("div");
  d.textContent = s;
  return d.innerHTML;
}

function setTab(name) {
  document.querySelectorAll(".nav-pill, .tab-btn").forEach((b) => {
    b.classList.toggle("active", b.dataset.tab === name);
  });
  document.querySelectorAll(".panel").forEach((p) => {
    p.classList.toggle("active", p.dataset.panel === name);
  });
  try {
    localStorage.setItem("vibework_last_tab", name);
    if (name === "mts") localStorage.setItem("vibework_last_tab", "profile");
  } catch (_) {}
  updateHeaderStepper(name);
  updateAvatarBubble();
  updateFlowUI();
  schedulePushServerSnapshot();
}

document.querySelectorAll(".nav-pill, .tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => setTab(btn.dataset.tab));
});

document.getElementById("btn-go-profile").addEventListener("click", () => setTab("profile"));
document.getElementById("btn-go-test").addEventListener("click", () => setTab("test"));

function ensureQuestionTimer(qid) {
  if (!questionStartedAt[qid]) questionStartedAt[qid] = Date.now();
}

function ensurePersonalityQuestionTimer(qid) {
  if (!questionStartedAtPersonality[qid]) questionStartedAtPersonality[qid] = Date.now();
}

function getPreparationLevel() {
  const el = document.querySelector('input[name="preparation_level"]:checked');
  const v = el?.value;
  if (v === "слабый" || v === "сильный" || v === "средний") return v;
  return "средний";
}

async function fetchAndRenderQuiz() {
  const form = document.getElementById("diag-form");
  if (!form) return;
  const fd = new FormData(form);
  const interest = String(fd.get("interest") || "IT");
  try {
    const url = new URL("/api/quiz/questions", window.location.origin);
    url.searchParams.set("interest", interest);
    const res = await fetch(url.toString());
    if (!res.ok) throw new Error("quiz");
    const data = await res.json();
    if (data.questions && data.questions.length >= 10) {
      QUIZ = data.questions;
    } else {
      QUIZ = [...QUIZ_FALLBACK];
    }
    if (data.personality_questions && data.personality_questions.length >= 8) {
      PERSONALITY_QUIZ = data.personality_questions;
    } else {
      PERSONALITY_QUIZ = [...PERSONALITY_QUIZ_FALLBACK];
    }
  } catch (_) {
    QUIZ = [...QUIZ_FALLBACK];
    PERSONALITY_QUIZ = [...PERSONALITY_QUIZ_FALLBACK];
  }
  Object.keys(questionStartedAt).forEach((k) => delete questionStartedAt[k]);
  Object.keys(questionStartedAtPersonality).forEach((k) => delete questionStartedAtPersonality[k]);
  renderQuiz();
  renderPersonalityQuiz();
  clearReportUi();
  updateQuizProgress();
  updateFlowUI();
}

function collectTimings() {
  return QUIZ.map((q) => {
    const sel = document.querySelector(`input[name="q${q.id}"]:checked`);
    const start = questionStartedAt[q.id];
    if (!sel || !start) return { question_id: q.id, ms: 0 };
    return { question_id: q.id, ms: Math.min(600_000, Date.now() - start) };
  }).filter((t) => t.ms > 0);
}

function collectPersonalityTimings() {
  return PERSONALITY_QUIZ.map((q) => {
    const sel = document.querySelector(`input[name="pq${q.id}"]:checked`);
    const start = questionStartedAtPersonality[q.id];
    if (!sel || !start) return { question_id: q.id, ms: 0 };
    return { question_id: q.id, ms: Math.min(600_000, Date.now() - start) };
  }).filter((t) => t.ms > 0);
}

function quizTotal() {
  return Math.max(1, QUIZ.length + PERSONALITY_QUIZ.length);
}

function unlockProfileMetrics() {
  profileProgressUnlocked = true;
  refreshProfileMetricsVisibility();
  updateProfileProgress();
}

function refreshProfileMetricsVisibility() {
  const wrap = document.getElementById("profile-metrics-wrap");
  const hint = document.getElementById("profile-metrics-hint");
  const show = !!window.lastAnalysis;
  if (wrap) wrap.hidden = !show;
  if (hint) {
    hint.hidden = show;
    if (!show) {
      hint.textContent =
        "Эта шкала и итоговые метрики появятся после теста и разбора — до этого заполните поля и пройдите вопросы.";
    }
  }
}

function updateQuizMetricsVisibility() {
  const wrap = document.getElementById("quiz-metrics-wrap");
  const hint = document.getElementById("quiz-metrics-hint");
  const ok = profileBasicsOk();
  if (wrap) wrap.hidden = !ok;
  if (hint) hint.hidden = ok;
}

function updateQuizProgress() {
  updateQuizMetricsVisibility();
  const n1 = QUIZ.filter((q) => document.querySelector(`input[name="q${q.id}"]:checked`)).length;
  const n2 = PERSONALITY_QUIZ.filter((q) => document.querySelector(`input[name="pq${q.id}"]:checked`)).length;
  const label = document.getElementById("quiz-progress-label");
  const bar = document.getElementById("quiz-bar");
  const labelP = document.getElementById("quiz-personality-progress-label");
  const barP = document.getElementById("quiz-personality-bar");
  if (label) label.textContent = `${n1}/${QUIZ.length}`;
  if (bar) bar.style.width = `${(n1 / Math.max(1, QUIZ.length)) * 100}%`;
  if (labelP) labelP.textContent = `${n2}/${PERSONALITY_QUIZ.length}`;
  if (barP) barP.style.width = `${(n2 / Math.max(1, PERSONALITY_QUIZ.length)) * 100}%`;
  syncReportToQuizState();
  updateFlowUI();
  schedulePushServerSnapshot();
}

let PROFILE_SCHEMA = null;

async function loadProfileSchema() {
  if (PROFILE_SCHEMA !== null) return PROFILE_SCHEMA;
  try {
    const r = await fetch("/api/profile/schema");
    if (!r.ok) throw new Error("schema");
    const data = await r.json();
    PROFILE_SCHEMA = Array.isArray(data) ? data : [];
  } catch (_) {
    PROFILE_SCHEMA = [];
  }
  return PROFILE_SCHEMA;
}

function renderSheetField(f) {
  /* Колонка «зачем» из таблицы хранится в схеме для бэкенда/ИИ — в интерфейсе не показываем. */
  const ph = f.placeholder ? esc(f.placeholder) : "";
  if (f.type === "text") {
    return `<label class="field full sheet-field"><span>${esc(f.label)}</span><input type="text" data-sheet-field="${esc(f.id)}" placeholder="${ph}" autocomplete="off" /></label>`;
  }
  if (f.type === "number") {
    return `<label class="field sheet-field"><span>${esc(f.label)}</span><input type="number" data-sheet-field="${esc(f.id)}" placeholder="${ph}" min="0" /></label>`;
  }
  if (f.type === "textarea") {
    return `<label class="field full sheet-field"><span>${esc(f.label)}</span><textarea data-sheet-field="${esc(f.id)}" rows="2" placeholder="${ph}"></textarea></label>`;
  }
  if (f.type === "select" && f.options) {
    const opts = f.options
      .map((o) => `<option value="${esc(o.value)}">${esc(o.label)}</option>`)
      .join("");
    return `<label class="field full sheet-field"><span>${esc(f.label)}</span><select data-sheet-field="${esc(f.id)}">${opts}</select></label>`;
  }
  if (f.type === "multiselect" && f.options) {
    const max = f.max || 5;
    const opts = f.options
      .map(
        (o) =>
          `<label class="sheet-multi-opt"><input type="checkbox" class="sheet-multi" data-sheet-field="${esc(f.id)}" value="${esc(o.value)}" /> <span>${esc(o.label)}</span></label>`
      )
      .join("");
    return `<div class="field full sheet-field sheet-multigroup" data-multi-field="${esc(f.id)}" data-multi-max="${max}"><span>${esc(f.label)}</span><div class="sheet-multi-grid">${opts}</div></div>`;
  }
  if (f.type === "scale_1_5") {
    const nums = [1, 2, 3, 4, 5];
    const radios = nums
      .map(
        (n) =>
          `<label class="sheet-scale-opt"><input type="radio" name="sheet_sc_${esc(f.id)}" data-sheet-field="${esc(f.id)}" value="${n}" /> <span>${n}</span></label>`
      )
      .join("");
    return `<div class="field full sheet-field"><span>${esc(f.label)}</span><div class="sheet-scale-row" role="radiogroup">${radios}</div></div>`;
  }
  return "";
}

function renderSheetProfileFromSchema(schema) {
  const root = document.getElementById("sheet-profile-root");
  if (!root || !schema || !schema.length) return;
  root.innerHTML = schema
    .map((sec) => {
      const fields = (sec.fields || []).map(renderSheetField).join("");
      return `<section class="sheet-section"><h3 class="sheet-section-title">${esc(sec.title)}</h3><div class="sheet-section-body">${fields}</div></section>`;
    })
    .join("");

  root.querySelectorAll(".sheet-multigroup").forEach((wrap) => {
    const fid = wrap.dataset.multiField;
    const maxN = parseInt(wrap.dataset.multiMax || "5", 10);
    wrap.querySelectorAll(".sheet-multi").forEach((cb) => {
      cb.addEventListener("change", () => {
        enforceMultiMax(fid, maxN);
        scheduleSaveProfileDraft();
      });
    });
  });

  root.querySelectorAll('[data-sheet-field="education_detail"]').forEach((el) => {
    el.addEventListener("change", () => {
      syncEducationFromDetail();
      scheduleSaveProfileDraft();
    });
  });
  syncEducationFromDetail();
}

function enforceMultiMax(fieldId, maxN) {
  const boxes = [...document.querySelectorAll('.sheet-multi[data-sheet-field="' + fieldId + '"]')].filter((x) => x.checked);
  while (boxes.length > maxN) {
    const u = boxes.pop();
    if (u) u.checked = false;
  }
}

function syncEducationFromDetail() {
  const sel = document.querySelector('[data-sheet-field="education_detail"]');
  const hidden = document.getElementById("field-education-sync");
  if (!hidden) return;
  const maps = {
    school_8_11: "школа",
    spo: "колледж",
    uni_bachelor: "вуз",
    uni_master: "вуз",
    graduate: "вуз",
  };
  if (sel && sel.tagName === "SELECT") {
    const v = String(sel.value || "").trim();
    if (v) hidden.value = maps[v] || "школа";
  }
}

let sheetProfileRendered = false;

async function ensureProfileSchemaRendered() {
  await loadProfileSchema();
  if (sheetProfileRendered) return;
  const root = document.getElementById("sheet-profile-root");
  if (root) {
    renderSheetProfileFromSchema(PROFILE_SCHEMA || []);
    sheetProfileRendered = true;
  }
}

function collectSheetExtra() {
  const out = {};
  document.querySelectorAll("input.sheet-multi[type=checkbox]").forEach((cb) => {
    if (!cb.checked) return;
    const k = cb.dataset.sheetField;
    if (!k) return;
    if (!out[k]) out[k] = [];
    out[k].push(cb.value);
  });
  document.querySelectorAll("select[data-sheet-field], textarea[data-sheet-field]").forEach((el) => {
    const k = el.dataset.sheetField;
    if (!k) return;
    const v = String(el.value || "").trim();
    if (v) out[k] = v;
  });
  document.querySelectorAll('input[type="number"][data-sheet-field]').forEach((el) => {
    const k = el.dataset.sheetField;
    if (!k || el.classList.contains("sheet-multi")) return;
    const v = String(el.value || "").trim();
    if (v) out[k] = v;
  });
  document.querySelectorAll('input[type="text"][data-sheet-field]').forEach((el) => {
    const k = el.dataset.sheetField;
    if (!k) return;
    const v = String(el.value || "").trim();
    if (v) out[k] = v;
  });
  document.querySelectorAll('input[type="radio"][data-sheet-field]:checked').forEach((el) => {
    out[el.dataset.sheetField] = el.value;
  });
  return out;
}

function applySheetFieldValue(key, val) {
  const multiEls = document.querySelectorAll('.sheet-multi[data-sheet-field="' + key + '"]');
  if (multiEls.length) {
    const set = new Set(Array.isArray(val) ? val.map(String) : [String(val)]);
    multiEls.forEach((cb) => {
      cb.checked = set.has(cb.value);
    });
    return;
  }
  const t = document.querySelector(`textarea[data-sheet-field="${key}"]`);
  if (t) {
    t.value = val != null ? String(val) : "";
    return;
  }
  const s = document.querySelector(`select[data-sheet-field="${key}"]`);
  if (s) {
    s.value = val != null ? String(val) : "";
    return;
  }
  const n = document.querySelector(`input[type="number"][data-sheet-field="${key}"]`);
  if (n) {
    n.value = val != null ? String(val) : "";
    return;
  }
  const tx = document.querySelector(`input[type="text"][data-sheet-field="${key}"]`);
  if (tx) {
    tx.value = val != null ? String(val) : "";
    return;
  }
  const rad = document.querySelector(`input[type="radio"][data-sheet-field="${key}"][value="${val}"]`);
  if (rad) {
    rad.checked = true;
    return;
  }
}

function profileBasicsOk() {
  const form = document.getElementById("diag-form");
  if (!form) return false;
  const fd = new FormData(form);
  const age = parseInt(String(fd.get("age")), 10);
  if (!Number.isFinite(age) || age < 14 || age > 30) return false;
  if (!fd.get("interest") || !fd.get("education")) return false;
  const det = document.querySelector('[data-sheet-field="education_detail"]');
  if (det && det.tagName === "SELECT" && !String(det.value || "").trim()) return false;
  return true;
}

function quizComplete() {
  const t1 = QUIZ.every((q) => document.querySelector(`input[name="q${q.id}"]:checked`));
  const t2 = PERSONALITY_QUIZ.every((q) => document.querySelector(`input[name="pq${q.id}"]:checked`));
  return t1 && t2;
}

/** Отпечаток текущих ответов в DOM — разбор валиден только пока он совпадает с моментом расчёта */
let lastReportAnswerFingerprint = null;

function getCurrentQuizAnswerList() {
  return QUIZ.map((q) => {
    const sel = document.querySelector(`input[name="q${q.id}"]:checked`);
    return { question_id: q.id, choice: sel ? sel.value : null };
  });
}

function getCurrentPersonalityAnswerList() {
  return PERSONALITY_QUIZ.map((q) => {
    const sel = document.querySelector(`input[name="pq${q.id}"]:checked`);
    return { question_id: q.id, choice: sel ? sel.value : null };
  });
}

function quizAnswerFingerprint() {
  const main = getCurrentQuizAnswerList()
    .map((a) => `${a.question_id}:${a.choice || "-"}`)
    .join("|");
  const pers = getCurrentPersonalityAnswerList()
    .map((a) => `p${a.question_id}:${a.choice || "-"}`)
    .join("|");
  return `${main}||${pers}`;
}

function answersMatchPayloadTest(testAnswers, personalityTestAnswers) {
  if (!testAnswers || testAnswers.length !== QUIZ.length) return false;
  const want = new Map(testAnswers.map((a) => [a.question_id, a.choice]));
  if (
    !QUIZ.every((q) => {
      const sel = document.querySelector(`input[name="q${q.id}"]:checked`);
      return sel && want.get(q.id) === sel.value;
    })
  ) {
    return false;
  }
  if (!personalityTestAnswers || personalityTestAnswers.length !== PERSONALITY_QUIZ.length) return false;
  const wantP = new Map(personalityTestAnswers.map((a) => [a.question_id, a.choice]));
  return PERSONALITY_QUIZ.every((q) => {
    const sel = document.querySelector(`input[name="pq${q.id}"]:checked`);
    return sel && wantP.get(q.id) === sel.value;
  });
}

function clearReportUi() {
  window.lastAnalysis = null;
  lastReportAnswerFingerprint = null;
  const ptw = document.getElementById("post-test-wrap");
  if (ptw) ptw.hidden = true;
  const loadingEl = document.getElementById("post-test-loading");
  if (loadingEl) loadingEl.hidden = true;
  const gate = document.getElementById("ai-gate");
  const shell = document.getElementById("ai-chat-shell");
  if (gate) gate.hidden = false;
  if (shell) shell.hidden = true;
  chatMessages = [];
  const cm = document.getElementById("chat-messages");
  if (cm) cm.innerHTML = "";
  refreshProfileMetricsVisibility();
  updateProfileProgress();
  updateAiChecklist();
  updateFlowUI();
  updateHeaderStepper(document.querySelector(".nav-pill.active, .tab-btn.active")?.dataset.tab || "profile");
}

function syncReportToQuizState() {
  if (!window.lastAnalysis) return;
  if (!quizComplete()) {
    clearReportUi();
    return;
  }
  if (lastReportAnswerFingerprint && quizAnswerFingerprint() !== lastReportAnswerFingerprint) {
    clearReportUi();
  }
}

function applyTestAnswersToDom(testAnswers) {
  if (!testAnswers) return;
  testAnswers.forEach(({ question_id, choice }) => {
    const inp = document.querySelector(`input[name="q${question_id}"][value="${choice}"]`);
    if (inp) inp.checked = true;
  });
  updateQuizProgress();
}

function applyPersonalityAnswersToDom(personalityTestAnswers) {
  if (!personalityTestAnswers) return;
  personalityTestAnswers.forEach(({ question_id, choice }) => {
    const inp = document.querySelector(`input[name="pq${question_id}"][value="${choice}"]`);
    if (inp) inp.checked = true;
  });
  updateQuizProgress();
}

function applyAnalyzePayloadToDom(payload) {
  if (!payload) return;
  applyTestAnswersToDom(payload.test_answers);
  applyPersonalityAnswersToDom(payload.personality_test_answers);
}

function updateAiChecklist() {
  const c1 = document.getElementById("chk-profile");
  const c2 = document.getElementById("chk-test");
  const c3 = document.getElementById("chk-report");
  if (c1) c1.classList.toggle("checklist-done", profileBasicsOk());
  if (c2) c2.classList.toggle("checklist-done", quizComplete());
  if (c3) c3.classList.toggle("checklist-done", !!window.lastAnalysis);
}

function updateFlowUI() {
  try {
    const hint = document.getElementById("flow-hint");
    const btn = document.getElementById("btn-analyze");
    const tf = document.getElementById("test-footer");
    const tff = document.getElementById("test-footer-hint");
    const aiBtn = document.getElementById("btn-request-ai");
    if (!btn || !hint) {
      updateQuizMetricsVisibility();
      return;
    }

    updateAiChecklist();

    const pOk = profileBasicsOk();
    const qOk = quizComplete();

    const testBanner = document.getElementById("test-blocked-banner");
    if (testBanner) testBanner.hidden = pOk;

    const tag = document.getElementById("profile-tagline");
    if (tag && !window.lastAnalysis) {
      if (!pOk) tag.textContent = "Сначала профиль: укажите возраст, сферу и уровень образования.";
      else if (!qOk) tag.textContent = "Профиль готов — откройте «Тест»: два блока (сфера + тип личности).";
      else tag.textContent = "Дозаполните оба теста — затем появится разбор и метрики.";
    } else if (tag && window.lastAnalysis) {
      tag.textContent = "Разбор готов: листайте блоки ниже или откройте ИИ и вакансии.";
    }

    if (!pOk) {
      btn.disabled = true;
      btn.textContent = "Сначала заполните профиль";
      btn.classList.remove("glow");
      hint.textContent =
        "Шаг 1: укажите возраст, главную сферу и блок профиля (уровень образования).";
      if (tf) tf.hidden = true;
      updateQuizMetricsVisibility();
      updateHeaderStepper(document.querySelector(".nav-pill.active, .tab-btn.active")?.dataset.tab || "profile");
      return;
    }

    hint.textContent = "Профиль готов. Переходите к тесту — подставятся вопросы по выбранной сфере.";

    if (!qOk) {
      btn.disabled = false;
      btn.textContent = "Шаг 2: перейти к тесту";
      btn.classList.remove("glow");
      if (tf) {
        tf.hidden = false;
        if (tff)
          tff.textContent = `Пройдите оба теста на вкладке «Тест» (${QUIZ.length} + ${PERSONALITY_QUIZ.length} вопросов) — затем появятся навыки в %, разбор и чат.`;
        if (aiBtn) aiBtn.hidden = true;
      }
      updateQuizMetricsVisibility();
      updateHeaderStepper(document.querySelector(".nav-pill.active, .tab-btn.active")?.dataset.tab || "profile");
      return;
    }

    btn.disabled = false;
    btn.textContent = "К тесту и разбору";
    btn.classList.add("glow");
    hint.textContent = "После отправки ответов откроются метрики. Чат — на вкладке «ИИ».";
    if (tf) {
      tf.hidden = false;
      if (tff) tff.textContent = "Тест заполнен — нажмите «К тесту и разбору» или дождитесь авто-разбора.";
      if (aiBtn) aiBtn.hidden = !window.lastAnalysis;
    }
    updateQuizMetricsVisibility();
    updateHeaderStepper(document.querySelector(".nav-pill.active, .tab-btn.active")?.dataset.tab || "profile");
  } finally {
    updateStreakChip();
  }
}

function updateProfileProgress() {
  refreshProfileMetricsVisibility();
  if (!window.lastAnalysis) return;
  const form = document.getElementById("diag-form");
  const fd = new FormData(form);
  let pts = 0;
  if (fd.get("age")) pts += 28;
  if (fd.get("interest")) pts += 28;
  if (fd.get("education")) pts += 28;
  if (String(fd.get("motivation") || "").trim().length > 10) pts += 10;
  if (document.querySelector('input[name="preparation_level"]:checked')) pts += 6;
  const g = window.lastAnalysis.gap_analysis?.overall_hp;
  if (Number.isFinite(g)) pts = Math.min(100, Math.round((pts + g) / 2));
  else pts = Math.min(100, pts);
  const pctEl = document.getElementById("profile-pct");
  const barEl = document.getElementById("profile-bar");
  if (pctEl) pctEl.textContent = `${pts}%`;
  if (barEl) barEl.style.width = `${pts}%`;
}

function renderQuiz() {
  const root = document.getElementById("quiz");
  if (!root) return;
  root.innerHTML = QUIZ.map(
    (q) => `
    <div class="quiz-item" data-q="${q.id}">
      <p>${q.id}. ${esc(q.text)}</p>
      <div class="quiz-options">
        ${q.options
          .map(
            (o) => `
          <label>
            <input type="radio" name="q${q.id}" value="${o.k}" required />
            <span><strong>${o.k}.</strong> ${esc(o.t)}</span>
          </label>`
          )
          .join("")}
      </div>
    </div>`
  ).join("");

  root.querySelectorAll('.quiz-item input[type="radio"]').forEach((inp) => {
    inp.addEventListener("focus", () => ensureQuestionTimer(parseInt(inp.closest(".quiz-item").dataset.q, 10)));
    inp.addEventListener("change", () => {
      ensureQuestionTimer(parseInt(inp.closest(".quiz-item").dataset.q, 10));
      updateQuizProgress();
      debouncedReanalyze();
    });
  });
}

function renderPersonalityQuiz() {
  const root = document.getElementById("quiz-personality");
  if (!root) return;
  root.innerHTML = PERSONALITY_QUIZ.map(
    (q) => `
    <div class="quiz-item" data-pq="${q.id}">
      <p>${q.id}. ${esc(q.text)}</p>
      <div class="quiz-options">
        ${q.options
          .map(
            (o) => `
          <label>
            <input type="radio" name="pq${q.id}" value="${o.k}" required />
            <span><strong>${o.k}.</strong> ${esc(o.t)}</span>
          </label>`
          )
          .join("")}
      </div>
    </div>`
  ).join("");

  root.querySelectorAll('.quiz-item input[type="radio"]').forEach((inp) => {
    inp.addEventListener("focus", () =>
      ensurePersonalityQuestionTimer(parseInt(inp.closest(".quiz-item").dataset.pq, 10))
    );
    inp.addEventListener("change", () => {
      ensurePersonalityQuestionTimer(parseInt(inp.closest(".quiz-item").dataset.pq, 10));
      updateQuizProgress();
      debouncedReanalyze();
    });
  });
}

function collectPayload() {
  const form = document.getElementById("diag-form");
  const fd = new FormData(form);
  syncEducationFromDetail();
  const age = parseInt(String(fd.get("age")), 10);
  if (!Number.isFinite(age) || age < 14 || age > 30) {
    throw new Error("Укажите возраст от 14 до 30.");
  }
  const interest = String(fd.get("interest"));
  const education = String(fd.get("education") || "").trim();
  if (!education) {
    throw new Error("Выберите уровень образования в блоке профиля.");
  }

  const test_answers = QUIZ.map((q) => {
    const sel = document.querySelector(`input[name="q${q.id}"]:checked`);
    if (!sel) return null;
    return { question_id: q.id, choice: sel.value };
  });

  const personality_test_answers = PERSONALITY_QUIZ.map((q) => {
    const sel = document.querySelector(`input[name="pq${q.id}"]:checked`);
    if (!sel) return null;
    return { question_id: q.id, choice: sel.value };
  });

  if (test_answers.some((a) => !a)) {
    throw new Error(`Ответьте на все вопросы теста 1 — сфера (${QUIZ.length} шт., вкладка «Тест»).`);
  }
  if (personality_test_answers.some((a) => !a)) {
    throw new Error(`Ответьте на все вопросы теста 2 — тип личности (${PERSONALITY_QUIZ.length} шт.).`);
  }

  const skills = [];
  const question_timings = collectTimings();
  const personality_question_timings = collectPersonalityTimings();
  const motivationRaw = String(fd.get("motivation") || "").trim();
  const motivation = motivationRaw || null;
  const preparation_level = getPreparationLevel();
  const extra = collectSheetExtra();
  const profile_extra = Object.keys(extra).length ? extra : null;

  return {
    age,
    interests: [interest],
    education,
    test_answers,
    personality_test_answers,
    skills,
    question_timings,
    personality_question_timings,
    motivation,
    profile_extra,
    preparation_level,
    target_mts_role_id: null,
  };
}

function buildJobContextBlob() {
  const parts = [];
  const a = window.lastAnalysis;
  if (a?.directions?.[0]) parts.push(String(a.directions[0].name));
  if (a?.style_fit?.length) {
    parts.push(a.style_fit.map((b) => `${b.label}: ${b.percent}%`).join("; "));
  }
  chatMessages.filter((m) => m.role === "user").slice(-6).forEach((m) => {
    parts.push(String(m.content).slice(0, 320));
  });
  const s = parts.join("\n").trim();
  return s.length ? s.slice(0, 2400) : null;
}

function collectMatchBody() {
  const form = document.getElementById("diag-form");
  const fd = new FormData(form);
  const interest = String(fd.get("interest"));
  const skills = skillsFromAnalysis(window.lastAnalysis);
  const profession = document.getElementById("job-profession").value.trim() || null;
  const level = document.getElementById("job-level").value || null;
  let city = document.getElementById("job-city").value.trim() || null;
  if (!city) {
    const cityIn = document.querySelector('[data-sheet-field="city"]');
    const c = cityIn && String(cityIn.value || "").trim();
    if (c) city = c;
  }
  const work_format = document.getElementById("job-format").value || null;
  const salary_bracket = document.getElementById("job-salary").value || null;
  return {
    interests: [interest],
    skills,
    profession,
    level,
    city,
    work_format,
    salary_bracket,
    conversation_summary: buildJobContextBlob(),
    recommended_track_hint: window.lastAnalysis?.directions?.[0]?.name || null,
  };
}

/** Снимок профиля — чтобы после перезагрузки не сбрасывалось на IT/школа/18 */
function collectProfileFields() {
  const form = document.getElementById("diag-form");
  if (!form) return null;
  syncEducationFromDetail();
  const fd = new FormData(form);
  const age = parseInt(String(fd.get("age")), 10);
  const prep = document.querySelector('input[name="preparation_level"]:checked')?.value || "средний";
  return {
    age: Number.isFinite(age) && age >= 14 && age <= 30 ? age : 18,
    interest: String(fd.get("interest") || "IT"),
    education: String(fd.get("education") || "школа"),
    motivation: String(fd.get("motivation") || ""),
    preparation_level: prep === "слабый" || prep === "сильный" || prep === "средний" ? prep : "средний",
    sheet: collectSheetExtra(),
  };
}

function applyProfileToForm(p) {
  if (!p || typeof p !== "object") return;
  const form = document.getElementById("diag-form");
  if (!form) return;
  const ageEl = form.querySelector('[name="age"]');
  if (ageEl && p.age != null) {
    const a = parseInt(String(p.age), 10);
    if (Number.isFinite(a) && a >= 14 && a <= 30) ageEl.value = String(a);
  }
  const intSel = form.querySelector('[name="interest"]');
  if (intSel && p.interest && [...intSel.options].some((o) => o.value === p.interest)) {
    intSel.value = p.interest;
  }
  const eduHid = document.getElementById("field-education-sync");
  if (eduHid && p.education && ["школа", "колледж", "вуз"].includes(String(p.education))) {
    eduHid.value = String(p.education);
  }
  const mot = form.querySelector('[name="motivation"]');
  if (mot && p.motivation != null) mot.value = String(p.motivation);
  const pl = p.preparation_level;
  if (pl === "слабый" || pl === "средний" || pl === "сильный") {
    form.querySelectorAll('input[name="preparation_level"]').forEach((radio) => {
      radio.checked = radio.value === pl;
    });
  }
  if (p.sheet && typeof p.sheet === "object") {
    for (const [k, v] of Object.entries(p.sheet)) {
      applySheetFieldValue(k, v);
    }
  }
  syncEducationFromDetail();
}

function saveProfileDraft() {
  try {
    const p = collectProfileFields();
    if (p) localStorage.setItem(STORAGE_PROFILE_DRAFT, JSON.stringify(p));
  } catch (_) {}
}

function loadProfileDraft() {
  try {
    const raw = localStorage.getItem(STORAGE_PROFILE_DRAFT);
    if (!raw) return;
    applyProfileToForm(JSON.parse(raw));
  } catch (_) {}
}

let saveProfileDraftTimer = null;
function scheduleSaveProfileDraft() {
  if (saveProfileDraftTimer) clearTimeout(saveProfileDraftTimer);
  saveProfileDraftTimer = setTimeout(() => {
    saveProfileDraftTimer = null;
    saveProfileDraft();
    schedulePushServerSnapshot();
  }, 400);
}

function buildServerSnapshot() {
  const profile = collectProfileFields();
  const answers = getCurrentQuizAnswerList().filter((a) => a.choice);
  const pAnswers = getCurrentPersonalityAnswerList().filter((a) => a.choice);
  let stored_result = null;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) stored_result = JSON.parse(raw);
  } catch (_) {}
  if (!stored_result && window.lastAnalysis) {
    stored_result = {
      savedAt: Date.now(),
      data: window.lastAnalysis,
      profile,
    };
  }
  return {
    profile,
    analysis: window.lastAnalysis || undefined,
    test_answers: answers.length === QUIZ.length ? answers : undefined,
    personality_test_answers: pAnswers.length === PERSONALITY_QUIZ.length ? pAnswers : undefined,
    chat_messages: chatMessages.length ? chatMessages : undefined,
    last_tab: localStorage.getItem("vibework_last_tab") || undefined,
    stored_result: stored_result || undefined,
  };
}

let pushServerTimer = null;
function schedulePushServerSnapshot() {
  if (!window.serverLoggedIn) return;
  if (pushServerTimer) clearTimeout(pushServerTimer);
  pushServerTimer = setTimeout(() => {
    pushServerTimer = null;
    pushServerSnapshot();
  }, 1400);
}

async function pushServerSnapshot() {
  if (!window.serverLoggedIn) return;
  const pill = document.getElementById("sync-pill");
  const textEl = document.getElementById("sync-pill-text");
  try {
    const body = buildServerSnapshot();
    const r = await fetch("/api/auth/snapshot", {
      method: "PUT",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (r.ok && textEl) {
      const prev = textEl.textContent;
      textEl.textContent = "Сохранено";
      pill.title = "Черновик отправлен на сервер.";
      clearTimeout(pushServerSnapshot._toastT);
      pushServerSnapshot._toastT = setTimeout(() => {
        textEl.textContent = prev;
        updateSyncPill();
      }, 2000);
    }
  } catch (_) {
    if (textEl) {
      textEl.textContent = "Нет связи";
      pill.title = "Не удалось сохранить на сервер — проверьте сеть и что бэкенд запущен.";
      clearTimeout(pushServerSnapshot._toastT);
      pushServerSnapshot._toastT = setTimeout(() => updateSyncPill(), 3500);
    }
  }
}

/** Восстановление с сервера: профиль, localStorage-обёртка, чат, вкладка */
function applyServerSnapshot(snap) {
  if (!snap || typeof snap !== "object") return;
  if (snap.profile) applyProfileToForm(snap.profile);
  if (snap.stored_result && (snap.stored_result.data || snap.stored_result.profile)) {
    try {
      const env = {
        savedAt: snap.stored_result.savedAt || Date.now(),
        data: snap.stored_result.data,
        profile: snap.stored_result.profile || snap.profile,
      };
      if (env.data) localStorage.setItem(STORAGE_KEY, JSON.stringify(env));
    } catch (_) {}
  }
  if (Array.isArray(snap.chat_messages)) chatMessages = snap.chat_messages;
  if (snap.last_tab) {
    try {
      localStorage.setItem("vibework_last_tab", snap.last_tab);
    } catch (_) {}
  }
}

/** Новый аккаунт: не переносим в него анонимный localStorage и уже заполненный профиль в этом браузере */
function resetClientStateForNewAccount() {
  try {
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem(STORAGE_PROFILE_DRAFT);
    localStorage.removeItem(STORAGE_FOCUS_STREAK);
    localStorage.removeItem("vibework_streak_demo_v1");
    localStorage.removeItem("vibework_last_tab");
  } catch (_) {}
  window.lastAnalysis = null;
  chatMessages = [];
  const form = document.getElementById("diag-form");
  if (form) {
    form.reset();
    document.querySelectorAll("input.sheet-multi[type=checkbox]").forEach((cb) => {
      cb.checked = false;
    });
    document.querySelectorAll("select[data-sheet-field], textarea[data-sheet-field]").forEach((el) => {
      el.value = "";
    });
    document.querySelectorAll('input[type="number"][data-sheet-field], input[type="text"][data-sheet-field]').forEach((el) => {
      if (!el.classList.contains("sheet-multi")) el.value = "";
    });
    document.querySelectorAll('input[type="radio"][data-sheet-field]').forEach((el) => {
      el.checked = false;
    });
  }
  syncEducationFromDetail();
  renderChatMessages();
  refreshProfileMetricsVisibility();
  updateProfileProgress();
  updateStreakChip();
  updateAvatarBubble();
}

/** Индикатор: без аккаунта — только браузер; после входа — сессия и синхронизация с сервером. */
function updateSyncPill() {
  const pill = document.getElementById("sync-pill");
  const textEl = document.getElementById("sync-pill-text");
  if (!pill || !textEl) return;
  pill.classList.toggle("live-pill--server", !!window.serverLoggedIn);
  pill.classList.toggle("live-pill--local", !window.serverLoggedIn);
  if (window.serverLoggedIn) {
    textEl.textContent = "Аккаунт";
    pill.title = "Вы вошли — профиль и разбор можно сохранять на сервере.";
  } else {
    textEl.textContent = "Локально";
    pill.title = "Без входа данные хранятся только в этом браузере.";
  }
}

function updateAuthPanel() {
  const lab = document.getElementById("auth-email-label");
  const em = document.getElementById("auth-email");
  const pw = document.getElementById("auth-password");
  const loginB = document.getElementById("btn-auth-login");
  const regB = document.getElementById("btn-auth-register");
  const outB = document.getElementById("btn-auth-logout");
  const forgot = document.getElementById("auth-forgot-hint");
  if (window.serverLoggedIn) {
    if (lab) {
      lab.hidden = false;
      lab.textContent = window.serverEmail || "";
    }
    if (em) em.hidden = true;
    if (pw) pw.hidden = true;
    if (loginB) loginB.hidden = true;
    if (regB) regB.hidden = true;
    if (outB) outB.hidden = false;
    if (forgot) forgot.hidden = true;
    document.body.classList.add("app-ready");
  } else {
    if (lab) lab.hidden = true;
    if (em) em.hidden = false;
    if (pw) pw.hidden = false;
    if (loginB) loginB.hidden = false;
    if (regB) regB.hidden = false;
    if (outB) outB.hidden = true;
    if (forgot) forgot.hidden = false;
    document.body.classList.remove("app-ready");
  }
  updateSyncPill();
}

async function refreshAuthState() {
  await ensureProfileSchemaRendered();
  try {
    const r = await fetch("/api/auth/me", { credentials: "include" });
    const j = await r.json();
    if (j.authenticated) {
      window.serverLoggedIn = true;
      window.serverEmail = j.email || "";
      updateAuthPanel();
      applyServerSnapshot(j.snapshot || {});
      return j;
    }
  } catch (_) {}
  window.serverLoggedIn = false;
  window.serverEmail = null;
  updateAuthPanel();
  return { authenticated: false };
}

function saveResult(data, analyzePayload = null) {
  try {
    const profile = collectProfileFields();
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ savedAt: Date.now(), data, profile, analyzePayload })
    );
    if (profile) localStorage.setItem(STORAGE_PROFILE_DRAFT, JSON.stringify(profile));
    schedulePushServerSnapshot();
  } catch (_) {}
}

function loadResult() {
  try {
    let raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) raw = localStorage.getItem("vibework_result_v5");
    if (!raw) raw = localStorage.getItem("vibework_result_v3");
    if (!raw) raw = localStorage.getItem("vibework_result_v2");
    if (!raw) return null;
    return JSON.parse(raw);
  } catch (_) {
    return null;
  }
}

function collectOptionalTestAnswers() {
  const main = [];
  for (const q of QUIZ) {
    const sel = document.querySelector(`input[name="q${q.id}"]:checked`);
    if (!sel) return null;
    main.push({ question_id: q.id, choice: sel.value });
  }
  const pers = [];
  for (const q of PERSONALITY_QUIZ) {
    const sel = document.querySelector(`input[name="pq${q.id}"]:checked`);
    if (!sel) return null;
    pers.push({ question_id: q.id, choice: sel.value });
  }
  return { test_answers: main, personality_test_answers: pers };
}

function renderStyleFit(root, bars, { showHints = false } = {}) {
  if (!root) return;
  if (!bars || !bars.length) {
    root.innerHTML = "<p class=\"muted small\">Нет данных — пересчитайте отчёт.</p>";
    return;
  }
  root.innerHTML = bars
    .map(
      (b) => `
    <div class="hp-row style-fit-row">
      <div class="hp-label">
        <span>${esc(b.label)}</span>
        <span class="mono">${b.percent}%</span>
      </div>
      <div class="hp-track"><div class="hp-fill" style="width:${b.percent}%"></div></div>
      ${showHints && b.hint ? `<p class="muted small" style="margin:0.25rem 0 0">${esc(b.hint)}</p>` : ""}
    </div>`
    )
    .join("");
}

/** Сегментная шкала (как «субъективная минута» / дашборд CDEK): 0–100 %. */
function renderSegmentedGauge(host, value) {
  if (!host) return;
  const v = Math.max(0, Math.min(100, Number(value) || 0));
  const segs = [
    { w: 20, cls: "cdek-seg cdek-seg--1", lab: "0–20" },
    { w: 20, cls: "cdek-seg cdek-seg--2", lab: "21–40" },
    { w: 20, cls: "cdek-seg cdek-seg--3", lab: "41–60" },
    { w: 20, cls: "cdek-seg cdek-seg--4", lab: "61–80" },
    { w: 20, cls: "cdek-seg cdek-seg--5", lab: "81–100" },
  ];
  const track = segs
    .map((s) => `<div class="${s.cls}" style="flex:${s.w}" title="${esc(s.lab)}"></div>`)
    .join("");
  host.innerHTML = `
    <div class="cdek-seg-gauge">
      <div class="cdek-seg-pointer-wrap" style="left:${v}%">
        <div class="cdek-seg-value">${v}%</div>
        <div class="cdek-seg-pointer" aria-hidden="true"></div>
      </div>
      <div class="cdek-seg-track">${track}</div>
      <div class="cdek-seg-ticks">${segs.map((s) => `<span>${esc(s.lab)}</span>`).join("")}</div>
    </div>`;
}

/** Полярная «лепестковая» диаграмма по осям style_fit (длина лепестка = выраженность, %). */
function renderStyleFitRadar(host, legendRoot, bars) {
  if (!host) return;
  if (!bars || !bars.length) {
    host.innerHTML = "<p class=\"muted small\">Нет данных.</p>";
    if (legendRoot) legendRoot.innerHTML = "";
    return;
  }
  const n = bars.length;
  const cx = 100;
  const cy = 100;
  const R = 78;
  const half = Math.PI / n;

  let grid = "";
  for (const g of [0.25, 0.5, 0.75, 1]) {
    const rg = R * g;
    grid += `<circle class="cdek-radar-ring" cx="${cx}" cy="${cy}" r="${rg.toFixed(2)}" />`;
  }
  for (let i = 0; i < n; i += 1) {
    const ang = -Math.PI / 2 + (2 * Math.PI * i) / n - half;
    const x2 = cx + R * Math.cos(ang);
    const y2 = cy + R * Math.sin(ang);
    grid += `<line class="cdek-radar-spoke" x1="${cx}" y1="${cy}" x2="${x2.toFixed(2)}" y2="${y2.toFixed(2)}" />`;
  }

  const withIdx = bars.map((b, i) => ({
    label: b.label,
    pct: Math.max(0, Math.min(100, Number(b.percent) || 0)),
    i,
  }));
  const ordered = [...withIdx].sort((a, b) => a.pct - b.pct);

  const steps = 18;
  let petals = "";
  for (const row of ordered) {
    const theta = -Math.PI / 2 + (2 * Math.PI * row.i) / n;
    const r = Math.max(1.2, (R * row.pct) / 100);
    const a0 = theta - half;
    const a1 = theta + half;
    let d = `M ${cx} ${cy}`;
    d += ` L ${cx + r * Math.cos(a0)} ${cy + r * Math.sin(a0)}`;
    for (let s = 1; s <= steps; s += 1) {
      const t = a0 + ((a1 - a0) * s) / steps;
      d += ` L ${cx + r * Math.cos(t)} ${cy + r * Math.sin(t)}`;
    }
    d += " Z";
    const fillOp = (0.16 + 0.52 * (row.pct / 100)).toFixed(2);
    petals += `<path class="cdek-radar-petal" d="${d}" fill-opacity="${fillOp}" />`;
  }

  host.innerHTML = `<svg viewBox="0 0 200 200" class="cdek-radar-svg cdek-radar-svg--petals" role="img" aria-label="Профиль задач: лепестковая диаграмма по четырём осям">${grid}${petals}</svg>`;

  if (legendRoot) {
    legendRoot.innerHTML = bars
      .map(
        (b) =>
          `<div class="radar-legend-row"><span class="radar-legend-pct">${esc(String(b.percent))}%</span><span class="radar-legend-label">${esc(b.label)}</span></div>`
      )
      .join("");
  }
}

/** Целевой профиль трека по названию (как на бэкенде `_profession_personality_target`). */
function professionPersonalityTarget(...titles) {
  const n = titles.filter(Boolean).join(" ").toLowerCase() || "направление";
  let rawA = 1;
  let rawC = 1;
  let rawP = 1;
  const KA = [
    "данн", "sql", "python", "backend", "devops", "ml", "аналит", "систем", "контрол", "отчёт", "модел", "качеств",
    "тест", "авто", "процесс", "финанс", "метрик", "платформ", "api", "инженер", "учёт", "аудит", "юрис", "договор",
    "консультац", "научн", "лабор", "логистик", "закуп",
  ];
  const KC = [
    "дизайн", "ux", "ui", "контент", "продукт", "front", "бренд", "визуал", "исслед", "гипотез", "сторител", "маркет",
    "копирайт", "креатив", "презентац",
  ];
  const KP = [
    "клиент", "продаж", "поддерж", "hr", "команд", "проект", "партнёр", "обучен", "сопровожден", "успех", "сервис",
    "рекрут", "переговор", "pmo", "координ", "менеджер", "администр", "корпоратив",
  ];
  for (const kw of KA) if (n.includes(kw)) rawA += 4;
  for (const kw of KC) if (n.includes(kw)) rawC += 4;
  for (const kw of KP) if (n.includes(kw)) rawP += 4;
  const s = rawA + rawC + rawP;
  const ta = Math.round((100 * rawA) / s);
  const tc = Math.round((100 * rawC) / s);
  const tp = Math.max(0, 100 - ta - tc);
  return [ta, tc, tp];
}

function userSharesFromStyleFit(res) {
  const sf = res.style_fit || [];
  const ua = sf[0]?.percent;
  const uc = sf[1]?.percent;
  const up = sf[2]?.percent;
  if ([ua, uc, up].every((x) => Number.isFinite(x))) {
    return [Math.round(ua), Math.round(uc), Math.round(up)];
  }
  return [34, 33, 33];
}

/** 4 плитки (как на бэкенде после смены метрик); fallback для кэша и офлайна. */
function computeFallbackInsightTiles(res) {
  const dirs = res.directions || [];
  if (!dirs.length) {
    const z = { title: "—", value: "—", subtitle: "Нет рекомендованного трека" };
    return [z, z, z, z];
  }
  const planA = dirs[0];
  const mts = res.mts_matrix || [];
  const mts0 = mts.length ? [...mts].sort((a, b) => b.relevance - a.relevance)[0] : null;
  const titleParts = mts0 ? [planA.name, mts0.title] : [planA.name];
  const [ta, tc, tp] = professionPersonalityTarget(...titleParts);
  const [ua, uc, up] = userSharesFromStyleFit(res);
  const align = (u, t) => Math.max(0, Math.min(100, 100 - Math.abs(u - t)));
  const fa = align(ua, ta);
  const fc = align(uc, tc);
  const fp = align(up, tp);
  const combined = Math.round((fa + fc + fp) / 3);
  const personalityBoost = Math.min(100, Math.round(combined * 1.08));
  const psych = Math.max(41, Math.min(97, Math.round(0.78 * combined + 0.22 * 74)));
  const sphereFit = Math.round((fa + combined) / 2);
  const peopleReady = fp;
  const trackShort = planA.name.length <= 44 ? planA.name : `${planA.name.slice(0, 41)}…`;
  const sph = (document.getElementById("field-interest")?.selectedOptions?.[0]?.text || "сфера").trim();
  return [
    {
      title: "Психологическая готовность к роли",
      value: `${psych}%`,
      subtitle: `Ориентир по стилю и близости к типичному профилю «${trackShort}» (${sph}). Обновите разбор на сервере для точных значений.`,
    },
    {
      title: "Тест личности и роль",
      value: `${personalityBoost}%`,
      subtitle: `Усиленная оценка по профилю с опорой на тест личности относительно «${trackShort}».`,
    },
    {
      title: "Совпадение теста сферы с треком",
      value: `${sphereFit}%`,
      subtitle: `Насколько блок по сфере близок к ожиданиям для «${trackShort}» (упрощённо в офлайне).`,
    },
    {
      title: "Люди, переговоры и чужие запросы",
      value: `${peopleReady}%`,
      subtitle: `Ось «люди» относительно типичного профиля трека: у вас ≈${up}%, для трека ≈${tp}%.`,
    },
  ];
}

function renderInsightTiles(tiles) {
  const card = document.getElementById("res-quad-insights");
  const root = document.getElementById("insight-tiles-grid");
  if (!card || !root) return;
  if (!tiles || !tiles.length) {
    card.hidden = true;
    root.innerHTML = "";
    return;
  }
  card.hidden = false;
  root.innerHTML = tiles
    .map(
      (t) => `
    <div class="insight-tile">
      <p class="insight-tile-title">${esc(t.title)}</p>
      <p class="insight-tile-value">${esc(t.value)}</p>
      <p class="insight-tile-sub muted small">${esc(t.subtitle || "")}</p>
    </div>`
    )
    .join("");
}

function renderInsightTilesFromResult(res) {
  const api = res.insight_tiles;
  const legacyRadar =
    api &&
    api.length >= 4 &&
    (api[0].title === "Ведущий стиль в тесте" || api[0].title === "Сильнейшая ось (радар)");
  const tiles =
    api && api.length >= 4 && !legacyRadar ? api.slice(0, 4) : computeFallbackInsightTiles(res);
  renderInsightTiles(tiles);
}

function renderGradePlan(rows) {
  const wrap = document.getElementById("grade-plan-wrap");
  const root = document.getElementById("grade-plan-block");
  if (!wrap || !root) return;
  if (!rows || !rows.length) {
    wrap.hidden = true;
    root.innerHTML = "";
    return;
  }
  wrap.hidden = false;
  root.innerHTML = `
    <table class="grade-plan-table">
      <thead>
        <tr><th>Грейд</th><th>Этап</th><th>Типовые роли</th><th>Критерии роста</th></tr>
      </thead>
      <tbody>
        ${rows
          .map(
            (r) => `
          <tr>
            <td class="mono grade-code">${esc(r.code)}</td>
            <td>${esc(r.stage_name)}</td>
            <td>${esc(r.typical_roles)}</td>
            <td>${esc(r.level_up_criteria)}</td>
          </tr>`
          )
          .join("")}
      </tbody>
    </table>`;
}

function renderMtsMetrics(root, items) {
  const card = document.getElementById("res-mts-metrics");
  if (!root || !card) return;
  if (!items || !items.length) {
    card.hidden = true;
    root.innerHTML = "";
    return;
  }
  card.hidden = false;
  const top = [...items].sort((a, b) => b.relevance - a.relevance).slice(0, 8);
  root.innerHTML = top
    .map(
      (m, i) => `
    <div class="mts-thermo-row">
      <span class="mts-thermo-title" title="${esc(m.title)}">${esc(m.title)}</span>
      <div class="mts-thermo-track">
        <div class="mts-thermo-fill mts-tone-${i % 5}" style="width:${m.relevance}%"></div>
      </div>
      <span class="mts-thermo-pct mono">${m.relevance}%</span>
    </div>`
    )
    .join("");
}

function renderAdviceBlock(root, res) {
  if (!root) return;
  const dirs = res.directions || [];
  const chunks = dirs.map((d) => {
    const steps = (d.first_steps || []).map((s) => `<li>${esc(s)}</li>`).join("");
    const sal = d.salary_motivation_hint
      ? `<p class="muted small advice-salary">${esc(d.salary_motivation_hint)}</p>`
      : "";
    return `<section class="advice-dir"><h3 class="advice-dir-title">${esc(d.plan_code)} · ${esc(d.name)}</h3><ul class="advice-steps">${steps}</ul>${sal}</section>`;
  });
  const g = res.gap_analysis;
  if (g && g.closing_skills && g.closing_skills.length) {
    chunks.push(
      `<p class="advice-gap muted"><strong>В приоритете по навыкам:</strong> ${g.closing_skills.map((x) => esc(x)).join(", ")}</p>`
    );
  }
  root.innerHTML =
    chunks.length > 0 ? chunks.join("") : '<p class="muted small">Нет собранных советов.</p>';
}

async function refreshMtsPreview() {
  /* Матрица МТС показывается только в разборе после теста */
}

function renderGap(gap) {
  const head = document.getElementById("gap-headline");
  if (head) head.textContent = gap.headline;
  renderSegmentedGauge(document.getElementById("gap-segmented-host"), gap.overall_hp);

  const barsEl = document.getElementById("gap-bars");
  if (barsEl) {
    barsEl.innerHTML = gap.bars
      .map(
        (b) => `
    <div class="hp-row metric-gap-row">
      <div class="hp-label"><span>${esc(b.label)}</span><span class="mono">${b.user_percent}% → ${b.target_percent}%</span></div>
      <div class="hp-track hp-track--dual">
        <div class="hp-fill hp-fill--user" style="width:${b.user_percent}%"></div>
      </div>
    </div>`
      )
      .join("");
  }
  const closeEl = document.getElementById("gap-closing");
  if (closeEl) {
    closeEl.textContent = gap.closing_skills.length
      ? "В фокусе: " + gap.closing_skills.join(", ")
      : "";
  }
}

function unlockChatUi() {
  if (!window.lastAnalysis) return;
  const gate = document.getElementById("ai-gate");
  const shell = document.getElementById("ai-chat-shell");
  if (gate) gate.hidden = true;
  if (shell) shell.hidden = false;
  seedChatIfNeeded();
}

function seedChatIfNeeded() {
  if (!window.lastAnalysis || chatMessages.length > 0) return;
  chatMessages.push({
    role: "assistant",
    content:
      "Привет! Я вижу ваш разбор после теста. Спросите про стажировки, страх перед резюме или отказом, подачу достижений, города и узкие навыки — отвечу с опорой на профиль. Напомню: я не заменяю живого профориентолога или карьерного консультанта по резюме, но могу структурировать шаги.",
  });
  renderChatMessages();
}

function renderChatMessages() {
  const root = document.getElementById("chat-messages");
  if (!root) return;
  root.innerHTML = "";
  chatMessages.forEach((m) => {
    const row = document.createElement("div");
    row.className = `chat-bubble ${m.role}`;
    const lab = document.createElement("span");
    lab.className = "chat-role";
    lab.textContent = m.role === "user" ? "Вы" : "ИИ";
    const text = document.createElement("div");
    text.className = "chat-text";
    text.textContent = m.content;
    row.appendChild(lab);
    row.appendChild(text);
    root.appendChild(row);
  });
  root.scrollTop = root.scrollHeight;
}

function renderResults(res) {
  if (!quizComplete()) {
    return;
  }
  window.lastAnalysis = res;
  lastReportAnswerFingerprint = quizAnswerFingerprint();
  unlockProfileMetrics();
  updateStreakChip();
  updateAvatarBubble();
  const av = document.getElementById("avatar-bubble");
  if (av) {
    av.classList.remove("pulse");
    void av.offsetWidth;
    av.classList.add("pulse");
  }
  const ptw = document.getElementById("post-test-wrap");
  if (ptw) ptw.hidden = false;
  const wrap = document.getElementById("results");
  if (wrap) wrap.hidden = false;
  unlockChatUi();
  updateAiChecklist();

  const tsLine = document.getElementById("results-timestamp");
  if (tsLine) {
    tsLine.hidden = false;
    tsLine.textContent = `Разбор: ${new Date().toLocaleString("ru-RU", { dateStyle: "short", timeStyle: "short" })}`;
  }

  if (res.gap_analysis) renderGap(res.gap_analysis);

  const radarHost = document.getElementById("style-radar-host");
  const radarLeg = document.getElementById("style-fit-legend");
  if (radarHost) {
    renderStyleFitRadar(radarHost, radarLeg, res.style_fit);
  }

  const mtsMet = document.getElementById("mts-metrics-block");
  if (mtsMet) renderMtsMetrics(mtsMet, res.mts_matrix);

  renderInsightTilesFromResult(res);

  document.getElementById("learning-block").innerHTML = res.learning_path
    .map(
      (r) => `
      <div class="learn-card">
        <span class="badge">${esc(r.type)}</span>
        <h4 style="margin:0.5rem 0 0.35rem">${esc(r.title)}</h4>
        <p class="muted small" style="margin:0">${esc(r.description)}</p>
        ${r.url ? `<a href="${esc(r.url)}" target="_blank" rel="noopener" style="display:inline-block;margin-top:0.5rem;color:var(--primary2)">Открыть →</a>` : ""}
      </div>`
    )
    .join("");

  const adviceRoot = document.getElementById("advice-block");
  if (adviceRoot) renderAdviceBlock(adviceRoot, res);

  renderGradePlan(res.grade_plan || []);

  document.getElementById("stages-block").innerHTML = (res.career_stages || [])
    .map(
      (s, idx) => `
      <article class="stage-card">
        <header class="stage-card-head">
          <span class="stage-idx" aria-hidden="true">${idx + 1}</span>
          <div>
            <h3 class="stage-card-title">${esc(s.title)}</h3>
            ${s.subtitle ? `<p class="stage-card-sub muted small">${esc(s.subtitle)}</p>` : ""}
          </div>
        </header>
        <p class="stage-desc">${esc(s.description)}</p>
        <p class="stage-duration muted small"><strong>Сроки:</strong> ${esc(s.typical_duration)}</p>
        ${
          s.focus_areas && s.focus_areas.length
            ? `<div class="stage-tags">${s.focus_areas.map((f) => `<span class="stage-tag">${esc(f)}</span>`).join("")}</div>`
            : ""
        }
        ${
          s.milestones && s.milestones.length
            ? `<ul class="stage-milestones">${s.milestones.map((m) => `<li>${esc(m)}</li>`).join("")}</ul>`
            : ""
        }
        ${s.transition_hint ? `<p class="stage-transition muted small">${esc(s.transition_hint)}</p>` : ""}
      </article>`
    )
    .join("");

  const tabNow = document.querySelector(".nav-pill.active, .tab-btn.active")?.dataset.tab || "test";
  updateHeaderStepper(tabNow);
}

function showError(msg) {
  const e = document.getElementById("form-error");
  e.hidden = !msg;
  e.textContent = msg || "";
}

async function fetchJobsMatch() {
  const res = await fetch("/api/jobs/match", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(collectMatchBody()),
  });
  if (!res.ok) throw new Error("Не удалось загрузить матчинг");
  return res.json();
}

function renderEnrichedJobCard(e, compact) {
  const j = e.vacancy;
  const rows = e.rows
    .map(
      (r) => `
    <div class="match-row">
      <span style="width:52px;color:${r.covered ? "var(--ok)" : "var(--danger)"}">${r.covered ? "✓" : "·"}</span>
      <span style="flex:1;font-size:0.78rem">${esc(r.requirement)}</span>
      <span class="mono" style="width:36px;text-align:right">${r.hp}</span>
    </div>
    <div class="match-meter"><i style="width:${r.hp}%"></i></div>`
    )
    .join("");

  return `
    <article class="job-card" data-id="${esc(j.id)}">
      <h4>${esc(j.title)}</h4>
      <div class="job-meta">
        ${esc(j.company)} · ${esc(j.level)} · ${esc(j.city)} · ${esc(j.work_format)}
        ${j.salary_hint ? " · " + esc(j.salary_hint) : ""}
      </div>
      <p class="muted small" style="margin:0.35rem 0"><strong>Матч ${e.match_percent}%</strong> — ${esc(e.why_match)}</p>
      ${e.why_not ? `<p class="muted small" style="margin:0">${esc(e.why_not)}</p>` : ""}
      ${compact ? "" : `<div class="match-grid">${rows}</div>`}
      ${
        j.source_url
          ? `<p style="margin:0.5rem 0 0"><a href="${esc(j.source_url)}" target="_blank" rel="noopener noreferrer" style="color:var(--primary2);font-size:0.88rem">Открыть на hh.ru →</a></p>`
          : ""
      }
    </article>`;
}

function renderJobsMatch(list) {
  const el = document.getElementById("jobs-match");
  if (!list.length) {
    el.innerHTML = "<p class=\"muted\">Нет вакансий — ослабьте фильтры.</p>";
    return;
  }
  el.innerHTML = list.map((e) => renderEnrichedJobCard(e, false)).join("");
}

function renderJobsListFromEnriched(list) {
  const el = document.getElementById("jobs-list");
  el.innerHTML = list.map((e) => renderEnrichedJobCard(e, true)).join("");
}

let swipeData = [];
let swipeIndex = 0;

function loadSwipeLikes() {
  try {
    return new Set(JSON.parse(localStorage.getItem(STORAGE_SWIPES) || "[]"));
  } catch (_) {
    return new Set();
  }
}

function saveSwipeLike(id) {
  const s = loadSwipeLikes();
  s.add(id);
  localStorage.setItem(STORAGE_SWIPES, JSON.stringify([...s]));
}

function tinderStampReset() {
  document.getElementById("tinder-stamp-nope")?.classList.remove("visible");
  document.getElementById("tinder-stamp-like")?.classList.remove("visible");
}

function tinderStampDx(dx) {
  const sn = document.getElementById("tinder-stamp-nope");
  const sy = document.getElementById("tinder-stamp-like");
  if (!sn || !sy) return;
  if (dx > 48) {
    sy.classList.add("visible");
    sn.classList.remove("visible");
  } else if (dx < -48) {
    sn.classList.add("visible");
    sy.classList.remove("visible");
  } else {
    sn.classList.remove("visible");
    sy.classList.remove("visible");
  }
}

function renderSwipeStack() {
  const stack = document.getElementById("swipe-stack");
  stack.innerHTML = "";
  tinderStampReset();
  const rest = swipeData.slice(swipeIndex, swipeIndex + 2);
  rest.forEach((e, i) => {
    const div = document.createElement("div");
    const v = e.vacancy;
    div.className = "swipe-card tinder-card";
    div.style.zIndex = String(10 - i);
    div.style.transform = `scale(${1 - i * 0.045}) translateY(${i * 12}px)`;
    div.innerHTML = `
      <span class="tinder-match-badge">${e.match_percent}% match</span>
      <h4>${esc(v.title)}</h4>
      <p class="job-meta">${esc(v.company)} · ${esc(v.level)} · ${esc(v.city)} · ${esc(v.work_format)}${v.salary_hint ? " · " + esc(v.salary_hint) : ""}</p>
      <p class="tinder-why">${esc(e.why_match)}</p>
      ${e.why_not ? `<p class="muted small" style="margin-top:0.5rem">${esc(e.why_not)}</p>` : ""}`;
    div.dataset.id = v.id;
    attachSwipeHandlers(div, i === 0);
    stack.appendChild(div);
  });
  if (!rest.length) {
    stack.innerHTML = "<p class=\"muted\" style=\"text-align:center;padding:3rem 1rem\">Колода пуста — смените фильтры или откройте «Классика».</p>";
  }
}

function attachSwipeHandlers(el, isTop) {
  let sx = 0,
    sy = 0,
    dx = 0,
    dragging = false;

  const onDown = (x, y) => {
    if (!isTop) return;
    dragging = true;
    sx = x;
    sy = y;
    dx = 0;
    tinderStampReset();
  };
  const onMove = (x, y) => {
    if (!dragging || !isTop) return;
    dx = x - sx;
    el.style.transform = `translateX(${dx}px) rotate(${dx * 0.06}deg)`;
    tinderStampDx(dx);
  };
  const onUp = () => {
    if (!dragging || !isTop) return;
    dragging = false;
    if (dx > 80) swipeVote(1);
    else if (dx < -80) swipeVote(-1);
    else {
      el.style.transform = "";
      tinderStampReset();
    }
  };

  el.addEventListener("mousedown", (ev) => onDown(ev.clientX, ev.clientY));
  window.addEventListener("mousemove", (ev) => onMove(ev.clientX, ev.clientY));
  window.addEventListener("mouseup", onUp);

  el.addEventListener(
    "touchstart",
    (ev) => {
      const t = ev.touches[0];
      onDown(t.clientX, t.clientY);
    },
    { passive: true }
  );
  el.addEventListener(
    "touchmove",
    (ev) => {
      const t = ev.touches[0];
      onMove(t.clientX, t.clientY);
    },
    { passive: true }
  );
  el.addEventListener("touchend", onUp);
}

function swipeVote(dir) {
  const top = document.querySelector("#swipe-stack .swipe-card");
  if (!top) return;
  tinderStampReset();
  const id = top.dataset.id;
  top.style.transition = "transform 0.35s ease, opacity 0.35s ease";
  top.style.transform = `translateX(${dir * 520}px) rotate(${dir * 22}deg)`;
  top.style.opacity = "0";
  if (dir > 0) saveSwipeLike(id);
  setTimeout(() => {
    swipeIndex += 1;
    renderSwipeStack();
  }, 320);
}

function setJobsView(view) {
  document.querySelectorAll(".view-toggle .tab-toggle").forEach((b) => {
    b.classList.toggle("active", b.dataset.view === view);
  });
  document.querySelectorAll(".jobs-view").forEach((v) => {
    v.classList.toggle("active", v.id === `jobs-${view}`);
  });
}

document.querySelectorAll(".view-toggle .tab-toggle").forEach((b) => {
  b.addEventListener("click", () => setJobsView(b.dataset.view));
});

async function loadJobsData() {
  const data = await fetchJobsMatch();
  renderJobsMatch(data);
  renderJobsListFromEnriched(data);
  swipeData = data;
  swipeIndex = 0;
  renderSwipeStack();
}

async function runConsultation(opts = {}) {
  const { switchToTestTab = true, quietErrors = false } = opts;
  let payload;
  try {
    payload = collectPayload();
  } catch (err) {
    showError(err.message || "Проверьте форму");
    setTab("test");
    return;
  }

  const btnMain = document.getElementById("btn-analyze");
  const btnTest = document.getElementById("btn-request-ai");
  const loadingEl = document.getElementById("post-test-loading");
  const ptw = document.getElementById("post-test-wrap");

  const setLoading = (v) => {
    if (btnMain) {
      btnMain.disabled = v;
      if (v) btnMain.textContent = "Строим разбор…";
    }
    if (btnTest) btnTest.disabled = v;
    if (loadingEl) loadingEl.hidden = !v;
    if (v && ptw) ptw.hidden = false;
  };

  setLoading(true);
  try {
    const res = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const body = await res.json().catch(() => ({}));
    if (!res.ok) {
      const detail = body.detail;
      const msg = Array.isArray(detail)
        ? detail.map((d) => d.msg || d).join("; ")
        : typeof detail === "string"
          ? detail
          : "Ошибка сервера";
      throw new Error(msg);
    }
    saveResult(body, payload);
    renderResults(body);
    chatMessages = [];
    if (switchToTestTab) setTab("test");
    await loadJobsData();
  } catch (err) {
    if (!quietErrors) showError(err.message || "Сеть или сервер недоступны");
  } finally {
    setLoading(false);
    updateFlowUI();
  }
}

document.getElementById("btn-analyze").addEventListener("click", async () => {
  showError("");
  if (!profileBasicsOk()) return;
  if (!quizComplete()) {
    setTab("test");
    return;
  }
  await runConsultation({ switchToTestTab: true });
});

document.getElementById("btn-request-ai").addEventListener("click", () => {
  showError("");
  if (!profileBasicsOk()) {
    setTab("profile");
    return;
  }
  if (!quizComplete()) {
    setTab("test");
    return;
  }
  if (!window.lastAnalysis) {
    runConsultation({ switchToTestTab: true }).catch(() => {});
    return;
  }
  setTab("ai");
  unlockChatUi();
});

document.getElementById("btn-restore").addEventListener("click", async () => {
  const stored = loadResult();
  if (!stored || !stored.data) {
    showError("Сохранённых результатов нет.");
    return;
  }
  showError("");
  if (stored.profile) applyProfileToForm(stored.profile);
  try {
    await fetchAndRenderQuiz();
  } catch (_) {}
  if (stored.analyzePayload) {
    applyAnalyzePayloadToDom(stored.analyzePayload);
  } else {
    applyTestAnswersToDom(stored.data.test_answers);
    applyPersonalityAnswersToDom(stored.data.personality_test_answers);
  }
  if (!quizComplete()) {
    showError("Отчёт не подходит к текущему набору вопросов (смените сферу в профиле на ту же, что при сохранении, или пройдите оба теста заново).");
    clearReportUi();
    return;
  }
  const pay = stored.analyzePayload;
  const okMatch = pay
    ? answersMatchPayloadTest(pay.test_answers, pay.personality_test_answers)
    : answersMatchPayloadTest(stored.data.test_answers, stored.data.personality_test_answers);
  if (!okMatch) {
    showError("Ответы в форме не совпадают с сохранённым отчётом.");
    clearReportUi();
    return;
  }
  chatMessages = [];
  renderResults(stored.data);
  setTab("test");
  loadJobsData().catch(() => {});
});

document.getElementById("diag-form").addEventListener("input", () => {
  scheduleSaveProfileDraft();
  updateAvatarBubble();
  updateFlowUI();
});

const debouncedJobs = debounce(() => loadJobsData().catch(() => {}), 450);
["job-profession", "job-level", "job-city", "job-format", "job-salary"].forEach((id) => {
  const el = document.getElementById(id);
  const ev = id === "job-profession" ? "input" : "change";
  el.addEventListener(ev, () => debouncedJobs());
});

function debounce(fn, ms) {
  let t;
  return () => {
    clearTimeout(t);
    t = setTimeout(fn, ms);
  };
}

const debouncedQuizReload = debounce(() => {
  fetchAndRenderQuiz().catch(() => {});
}, 380);

const debouncedReanalyze = debounce(() => {
  if (!profileBasicsOk() || !quizComplete()) return;
  runConsultation({ switchToTestTab: false, quietErrors: true }).catch(() => {});
}, 1000);

document.getElementById("diag-form").addEventListener("change", (e) => {
  scheduleSaveProfileDraft();
  updateAvatarBubble();
  updateFlowUI();
  if (e.target && e.target.id === "field-interest") debouncedQuizReload();
});
document.querySelectorAll('input[name="preparation_level"]').forEach((r) => {
  r.addEventListener("change", () => {
    scheduleSaveProfileDraft();
    updateFlowUI();
  });
});

document.getElementById("btn-spark-tip")?.addEventListener("click", () => {
  const t = MICRO_TIPS[Math.floor(Math.random() * MICRO_TIPS.length)];
  showToast(t);
});

document.getElementById("swipe-rewind")?.addEventListener("click", () => {
  if (swipeIndex <= 0) return;
  swipeIndex -= 1;
  renderSwipeStack();
});

document.getElementById("chat-form")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!window.lastAnalysis) return;
  const inp = document.getElementById("chat-input");
  const t = (inp?.value || "").trim();
  if (!t) return;
  chatMessages.push({ role: "user", content: t });
  if (inp) inp.value = "";
  renderChatMessages();
  const dirs = (window.lastAnalysis.directions || [])
    .slice(0, 3)
    .map((d) => `${d.plan_code}: ${d.name}`)
    .join("; ");
  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        messages: chatMessages.slice(-24),
        context_summary: window.lastAnalysis.profile_summary,
        directions_hint: dirs,
      }),
    });
    const j = await res.json().catch(() => ({}));
    if (!res.ok) {
      const det = j.detail;
      const msg = Array.isArray(det) ? det.map((x) => x.msg || x).join("; ") : typeof det === "string" ? det : "Чат недоступен";
      throw new Error(msg);
    }
    chatMessages.push({ role: "assistant", content: j.reply || "…" });
    if (j.source === "mock") {
      showToast(
        j.notice ||
          "Ответ без нейросети (заглушка). Откройте окно сервера — там причина в логе."
      );
    }
  } catch (err) {
    chatMessages.push({ role: "assistant", content: err.message || "Ошибка сети." });
  }
  renderChatMessages();
  schedulePushServerSnapshot();
  loadJobsData().catch(() => {});
});

document.getElementById("swipe-left")?.addEventListener("click", () => swipeVote(-1));
document.getElementById("swipe-right")?.addEventListener("click", () => swipeVote(1));

/** Симулятор */
let simState = { role_key: "analyst", step_index: 0, career_points: 50, history: [] };

function renderSim(step) {
  document.getElementById("sim-step-badge").textContent = step.is_final ? "Финал" : `Шаг ${step.step_index + 1}`;
  document.getElementById("sim-points").textContent = `Очки: ${step.career_points}`;
  document.getElementById("sim-title").textContent = step.title;
  document.getElementById("sim-text").textContent = step.narrative;
  const ch = document.getElementById("sim-choices");
  ch.innerHTML = "";
  step.choices.forEach((c) => {
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = c.label;
    b.addEventListener("click", async () => {
      simState.career_points = step.career_points;
      simState.step_index = step.step_index;
      const res = await fetch("/api/simulator/step", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ state: simState, choice_id: c.id }),
      });
      const next = await res.json();
      simState.step_index = next.step_index;
      simState.career_points = next.career_points;
      simState.history = [...simState.history, c.id];
      renderSim(next);
    });
    ch.appendChild(b);
  });
}

async function startSim() {
  const role = document.getElementById("sim-role").value;
  simState = { role_key: role, step_index: 0, career_points: 50, history: [] };
  const res = await fetch(`/api/simulator/start?role=${encodeURIComponent(role)}`);
  const step = await res.json();
  simState.step_index = step.step_index;
  simState.career_points = step.career_points;
  renderSim(step);
}

document.getElementById("sim-restart").addEventListener("click", () => {
  startSim().catch((e) => alert(e.message));
});

async function authRequest(path, email, password) {
  const r = await fetch(path, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const j = await r.json().catch(() => ({}));
  return { ok: r.ok, j };
}

document.getElementById("btn-auth-login").addEventListener("click", async () => {
  const email = document.getElementById("auth-email")?.value?.trim();
  const password = document.getElementById("auth-password")?.value || "";
  if (!email || password.length < 8) {
    showToast("Укажите email и пароль не короче 8 символов.");
    return;
  }
  const { ok, j } = await authRequest("/api/auth/login", email, password);
  if (!ok) {
    showToast(typeof j.detail === "string" ? j.detail : "Не вышло войти");
    return;
  }
  const me = await refreshAuthState();
  await fetchAndRenderQuiz();
  if (me.snapshot?.test_answers?.length === QUIZ.length) {
    applyTestAnswersToDom(me.snapshot.test_answers);
  }
  if (me.snapshot?.personality_test_answers?.length === PERSONALITY_QUIZ.length) {
    applyPersonalityAnswersToDom(me.snapshot.personality_test_answers);
  }
  if (
    me.snapshot?.analysis &&
    quizComplete() &&
    me.snapshot.test_answers?.length === QUIZ.length &&
    me.snapshot.personality_test_answers?.length === PERSONALITY_QUIZ.length &&
    answersMatchPayloadTest(me.snapshot.test_answers, me.snapshot.personality_test_answers)
  ) {
    renderResults(me.snapshot.analysis);
    await loadJobsData().catch(() => {});
  } else {
    clearReportUi();
  }
  updateQuizProgress();
  showToast("Вошли: профиль с сервера.");
  schedulePushServerSnapshot();
});

document.getElementById("btn-auth-register").addEventListener("click", async () => {
  const email = document.getElementById("auth-email")?.value?.trim();
  const password = document.getElementById("auth-password")?.value || "";
  if (!email || password.length < 8) {
    showToast("Укажите email и пароль не короче 8 символов.");
    return;
  }
  const { ok, j } = await authRequest("/api/auth/register", email, password);
  if (!ok) {
    showToast(typeof j.detail === "string" ? j.detail : "Регистрация не удалась");
    return;
  }
  await refreshAuthState();
  resetClientStateForNewAccount();
  await fetchAndRenderQuiz();
  updateQuizProgress();
  showToast("Аккаунт создан. Данные сохраняются на сервере.");
  schedulePushServerSnapshot();
});

document.getElementById("btn-auth-logout").addEventListener("click", async () => {
  try {
    await fetch("/api/auth/logout", { method: "POST", credentials: "include" });
  } catch (_) {}
  window.serverLoggedIn = false;
  window.serverEmail = null;
  const pw = document.getElementById("auth-password");
  if (pw) pw.value = "";
  updateAuthPanel();
  showToast("Вы вышли.");
});

(async () => {
  const me = await refreshAuthState();
  if (!me.authenticated) {
    const storedOnLoad = loadResult();
    if (storedOnLoad && storedOnLoad.profile) {
      applyProfileToForm(storedOnLoad.profile);
    } else {
      loadProfileDraft();
    }
  }

  renderQuiz();
  renderPersonalityQuiz();
  refreshProfileMetricsVisibility();
  updateProfileProgress();
  updateQuizProgress();
  updateFlowUI();
  updateAvatarBubble();

  try {
    const t = localStorage.getItem("vibework_last_tab");
    if (t && t !== "mts") setTab(t);
  } catch (_) {}

  await fetchAndRenderQuiz();

  const stored = loadResult();
  if (!me.authenticated && stored?.profile) {
    applyProfileToForm(stored.profile);
  }

  if (me.authenticated && me.snapshot?.test_answers?.length === QUIZ.length) {
    applyTestAnswersToDom(me.snapshot.test_answers);
  } else if (stored?.analyzePayload?.test_answers?.length === QUIZ.length) {
    applyTestAnswersToDom(stored.analyzePayload.test_answers);
  } else if (stored?.data?.test_answers?.length === QUIZ.length) {
    applyTestAnswersToDom(stored.data.test_answers);
  }
  if (me.authenticated && me.snapshot?.personality_test_answers?.length === PERSONALITY_QUIZ.length) {
    applyPersonalityAnswersToDom(me.snapshot.personality_test_answers);
  } else if (stored?.analyzePayload?.personality_test_answers?.length === PERSONALITY_QUIZ.length) {
    applyPersonalityAnswersToDom(stored.analyzePayload.personality_test_answers);
  } else if (stored?.data?.personality_test_answers?.length === PERSONALITY_QUIZ.length) {
    applyPersonalityAnswersToDom(stored.data.personality_test_answers);
  }

  if (
    me.authenticated &&
    me.snapshot?.analysis &&
    quizComplete() &&
    me.snapshot.test_answers?.length === QUIZ.length &&
    me.snapshot.personality_test_answers?.length === PERSONALITY_QUIZ.length &&
    answersMatchPayloadTest(me.snapshot.test_answers, me.snapshot.personality_test_answers)
  ) {
    renderResults(me.snapshot.analysis);
    loadJobsData().catch(() => {});
  } else if (
    stored &&
    stored.data &&
    quizComplete() &&
    stored.analyzePayload &&
    answersMatchPayloadTest(stored.analyzePayload.test_answers, stored.analyzePayload.personality_test_answers)
  ) {
    renderResults(stored.data);
    loadJobsData().catch(() => {});
  } else if (
    stored &&
    stored.data &&
    quizComplete() &&
    answersMatchPayloadTest(stored.data.test_answers, stored.data.personality_test_answers)
  ) {
    renderResults(stored.data);
    loadJobsData().catch(() => {});
  } else {
    clearReportUi();
  }
  updateQuizProgress();
  updateHeaderStepper(document.querySelector(".nav-pill.active, .tab-btn.active")?.dataset.tab || "profile");
})();

const THEME_STORAGE_KEY = "vibework_theme";

function syncThemeToggleButton(isDark) {
  const btn = document.getElementById("btn-theme-toggle");
  if (!btn) return;
  btn.setAttribute("aria-pressed", isDark ? "true" : "false");
  btn.title = isDark ? "Светлая тема" : "Тёмная тема";
  btn.setAttribute("aria-label", isDark ? "Включить светлую тему" : "Включить тёмную тему");
  btn.textContent = isDark ? "☀️" : "🌙";
}

function applyTheme(mode) {
  const root = document.documentElement;
  if (mode === "dark") root.setAttribute("data-theme", "dark");
  else root.removeAttribute("data-theme");
  try {
    localStorage.setItem(THEME_STORAGE_KEY, mode === "dark" ? "dark" : "light");
  } catch (_) {}
  syncThemeToggleButton(mode === "dark");
}

function initThemeToggle() {
  try {
    const stored = localStorage.getItem(THEME_STORAGE_KEY);
    if (stored === "dark") document.documentElement.setAttribute("data-theme", "dark");
    else if (stored === "light") document.documentElement.removeAttribute("data-theme");
  } catch (_) {}
  syncThemeToggleButton(document.documentElement.getAttribute("data-theme") === "dark");
  const btn = document.getElementById("btn-theme-toggle");
  if (btn && !btn.dataset.themeBound) {
    btn.dataset.themeBound = "1";
    btn.addEventListener("click", () => {
      const next = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
      applyTheme(next);
    });
  }
}

initThemeToggle();
