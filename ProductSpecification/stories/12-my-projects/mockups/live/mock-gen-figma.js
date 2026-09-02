/* Экран «Создание "Тип документа"» — НОВЫЙ дизайн (фрейм заказчика, 26 августа), шаг 1.
   Отличие от 06-generation-form.html: тот снимок текущего компонента, этот — макет, к
   которому его надо привести. Загрузка файлов заменена параметрами генерации: файлов в
   продукте нет, а требования / объём / стиль / пожелания композер собирает уже сегодня. */

// Шапка на этом экране — пилюля с «Мои проекты», как на фрейме, а не сплошная полоса
// AppHeader, которую рисует компонент сегодня.
function genNavbar() {
  return `
    <div class="navbar-projects-placement">
      <header class="navbar navbar-pill">
        <img class="navbar-logo navbar-logo-light" src="${ASSETS}/logo-textery.svg" alt="Textery">
        <img class="navbar-logo navbar-logo-dark" src="${ASSETS}/logo-textery-dark.svg" alt="">
        <div class="navbar-actions">
          <button type="button" class="theme-switch" role="switch" aria-checked="false"
                  aria-label="Тёмная тема">
            <svg class="theme-switch-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                 stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79Z" />
            </svg>
            <svg class="theme-switch-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                 stroke-width="2" stroke-linecap="round" aria-hidden="true">
              <circle cx="12" cy="12" r="4" />
              <path d="M12 3v2M12 19v2M5.2 5.2l1.4 1.4M17.4 17.4l1.4 1.4M3 12h2M19 12h2M6.6 17.4l-1.4 1.4M18.8 5.2l-1.4 1.4" />
            </svg>
            <span class="theme-switch-knob" aria-hidden="true"></span>
          </button>
          <button type="button" class="projects-create-button">Мои проекты</button>
          <div class="profile-menu">
            <button type="button" class="profile-trigger" aria-haspopup="menu" aria-expanded="false">
              <span class="profile-avatar profile-avatar-trigger">АС</span>
              <svg class="profile-chevron" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path d="m7 10 5 5 5-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
              </svg>
            </button>
          </div>
        </div>
      </header>
    </div>`
}

const STEPS = ['Укажите тему', 'Введите параметры', 'Получите документ']

function genSteps(current) {
  return STEPS.map((label, index) => {
    const step = `
      <div class="genform-step${index + 1 === current ? ' genform-step-current' : ''}">
        <span class="genform-step-num">${index + 1}</span>
        <span class="genform-step-label">${label}</span>
      </div>`
    return index === STEPS.length - 1 ? step : step + '<span class="genform-step-line"></span>'
  }).join('')
}

// Регистры текста — те же три, что отдаёт TEXT_STYLE_OPTIONS.
const STYLES = [
  ['Научный', 'Термины, безличные конструкции'],
  ['Публицистический', 'Живая аргументация, примеры'],
  ['Художественный', 'Образная речь, описания'],
]

function genForm() {
  return `
    <div class="genform-field">
      <label class="genform-label" for="genform-topic">Тема «Доклада»</label>
      <input class="genform-input" id="genform-topic" placeholder="Например: Влияние ИИ на рынок труда">
    </div>

    <div class="genform-field">
      <label class="genform-label" for="genform-req">Требования (необязательно)</label>
      <p class="genform-hint">
        Если ничего не указывать, Textery подберёт параметры сам по выбранному типу документа.
      </p>
      <textarea class="genform-textarea" id="genform-req"
                placeholder="Например: официально-деловой стиль, ссылки на источники"></textarea>
    </div>

    <div class="genform-field genform-row">
      <div>
        <label class="genform-label" for="genform-volume">Объём, страниц</label>
        <input class="genform-input" id="genform-volume" type="number" min="1" max="10" value="5">
      </div>
      <div>
        <label class="genform-label" for="genform-style">Стиль текста</label>
        <select class="genform-select" id="genform-style">
          <option value="">Не указан</option>
          ${STYLES.map(([label]) => `<option>${label}</option>`).join('')}
        </select>
        <p class="genform-field-note">${STYLES[0][1]}</p>
      </div>
    </div>

    <div class="genform-field">
      <label class="genform-label" for="genform-wishes">Дополнительные пожелания</label>
      <textarea class="genform-textarea" id="genform-wishes"
                placeholder="Что-то ещё, что стоит учесть при генерации"></textarea>
    </div>

    <div class="genform-actions">
      <button type="button" class="genform-btn genform-btn-ghost">Отмена</button>
      <button type="button" class="genform-btn genform-btn-primary" disabled>Далее</button>
    </div>`
}

// Правая карточка: тип, план документа и замечание про редактирование.
const PLAN = [
  ['Структура по типу', 'Введение, основная часть и выводы — как требует «Доклад»'],
  ['Текст на 5 страниц', 'Объём и стиль берутся из параметров слева'],
]

function genSide() {
  return `
    <div class="genform-side-type">
      <span class="genform-side-tile">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"
             stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M6 3h8l4 4v14H6z" /><path d="M9 12h6M9 16h6M9 8h3" />
        </svg>
      </span>
      <div>
        <div class="genform-side-caption">Тип документа</div>
        <div class="genform-side-name">«Доклад»</div>
      </div>
    </div>

    <h2 class="genform-side-heading">Что будет в документе?</h2>
    <ul class="genform-side-list">
      ${PLAN.map(
        ([title, text]) => `
        <li class="genform-side-item">
          <span class="genform-side-dot" aria-hidden="true"></span>
          <span>
            <span class="genform-side-item-title">${title}</span>
            <span class="genform-side-item-text">${text}</span>
          </span>
        </li>`,
      ).join('')}
    </ul>

    <p class="genform-side-note">Сгенерированный документ можно будет отредактировать</p>`
}

document.querySelectorAll('[data-mock="gen-navbar"]').forEach((s) => (s.outerHTML = genNavbar()))
document.querySelectorAll('[data-mock="gen-steps"]').forEach((s) => (s.innerHTML = genSteps(1)))
document.querySelectorAll('[data-mock="gen-form"]').forEach((s) => (s.innerHTML = genForm()))
document.querySelectorAll('[data-mock="gen-side"]').forEach((s) => (s.innerHTML = genSide()))

// Тумблер темы рабочий — тёмную правим, глядя на неё.
document.querySelectorAll('.theme-switch').forEach((button) => {
  const sync = () => {
    const dark = document.documentElement.dataset.theme === 'dark'
    button.setAttribute('aria-checked', String(dark))
  }
  new MutationObserver(sync).observe(document.documentElement, {
    attributes: true,
    attributeFilter: ['data-theme'],
  })
  button.addEventListener('click', () => {
    const dark = document.documentElement.dataset.theme === 'dark'
    document.documentElement.dataset.theme = dark ? 'light' : 'dark'
    sync()
  })
  sync()
})
