/* Экран генерации — снимок ChatWorkspace / ComposerPanel / Composer / ComposerParameters /
   ComposerStyle / TopicSuggestions. Отдельный файл: mock.js держит «Мои проекты», а здесь
   другой экран и другой предмет правки. */

// Шапка рабочей области — Navbar в варианте `bar` (AppHeader.tsx): во всю ширину,
// с волосяной линией снизу, а не пилюлей, как на «Моих проектах».
function appHeader() {
  return `
    <header class="navbar navbar-bar">
      <img class="navbar-logo navbar-logo-light" src="${ASSETS}/logo-textery.svg" alt="Textery">
      <img class="navbar-logo navbar-logo-dark" src="${ASSETS}/logo-textery-dark.svg" alt="">
      <div class="navbar-actions">
        <div class="profile-menu">
          <button type="button" class="profile-trigger" aria-haspopup="menu" aria-expanded="false">
            <span class="profile-avatar profile-avatar-trigger">АС</span>
            <svg class="profile-chevron" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path d="m7 10 5 5 5-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
            </svg>
          </button>
        </div>
      </div>
    </header>`
}

// Примеры тем — те же, что отдаёт suggestionsFor('doklad').
const TOPIC_SUGGESTIONS = [
  'Искусственный интеллект в современной медицине',
  'Освоение Арктики: история и перспективы',
  'Возобновляемая энергетика в России',
]

// Регистры текста с их подсказками (TEXT_STYLE_OPTIONS).
const TEXT_STYLES = [
  ['Научный', 'Термины, безличные конструкции'],
  ['Публицистический', 'Живая аргументация, примеры'],
  ['Художественный', 'Образная речь, описания'],
]

function composer() {
  return `
    <div class="composer">
      <h3 class="required">
        Тема доклада<span class="composer-required-marker" aria-hidden="true"> *</span>
      </h3>
      <textarea class="composer-input" rows="4"
                placeholder="Например: Влияние искусственного интеллекта на образование"></textarea>

      <div class="topic-suggestions">
        <span class="topic-suggestions-label">Например:</span>
        <ul class="topic-suggestions-list">
          ${TOPIC_SUGGESTIONS.map(
            (topic) => `<li><button type="button" class="topic-suggestion">${topic}</button></li>`,
          ).join('')}
        </ul>
      </div>

      <div class="composer-parameters">
        <div class="composer-parameters-row">
          <div class="composer-field composer-field-grow">
            <span class="composer-field-label">Требования</span>
            <textarea class="composer-field-input" rows="2"
                      placeholder="Например: официально-деловой стиль, ссылки на источники"></textarea>
          </div>
          <div class="composer-field composer-field-volume">
            <span class="composer-field-label required">
              Объём, страниц<span class="composer-required-marker" aria-hidden="true"> *</span>
            </span>
            <input type="number" class="composer-field-input" min="1" max="10" value="5">
          </div>
        </div>

        <div class="composer-field composer-field-style">
          <span class="composer-field-label">Стиль текста</span>
          <select class="composer-field-input composer-style-select">
            <option value="">Не указан</option>
            ${TEXT_STYLES.map(([label]) => `<option>${label}</option>`).join('')}
          </select>
          <span class="composer-style-hint">${TEXT_STYLES[0][1]}</span>
        </div>

        <div class="composer-field">
          <span class="composer-field-label">Дополнительные пожелания</span>
          <textarea class="composer-field-input" rows="2"
                    placeholder="Что-то ещё, что стоит учесть при генерации"></textarea>
        </div>
      </div>

      <button type="button" class="cw-btn cw-btn-primary composer-send">Сгенерировать</button>
      <p class="composer-hint">Обычно занимает 1–2 минуты</p>
    </div>`
}

document.querySelectorAll('[data-mock="app-header"]').forEach((slot) => (slot.outerHTML = appHeader()))
document.querySelectorAll('[data-mock="composer"]').forEach((slot) => (slot.innerHTML = composer()))
