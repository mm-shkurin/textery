/* Редактор с готовым текстом — снимок ManualEditor / ManualEditorToolbar /
   ManualEditorBreadcrumb / ManualEditorSaveStatus / ExportControl, как они выглядят сейчас.
   Это НЕ макет: сюда смотрим, чтобы сравнить с фреймом и править. */

// Шапка редактора — Navbar в варианте `bar` (AppHeader), во всю ширину с линией снизу.
// На этом экране у компонента нет ни выхода из сессии, ни тумблера темы: AppHeader
// вызывается без onLogoutClick, поэтому меню профиля не рисуется вообще.
function editorHeader() {
  return `
    <header class="navbar navbar-bar">
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
      </div>
    </header>`
}

// Рамка-заглушка PlaceholderImage — компонент рисует её в чипе типа и в статусе «Сохранено».
const PLACEHOLDER_SVG = `
  <svg viewBox="0 0 100 100" fill="none" aria-hidden="true">
    <rect x="1" y="1" width="98" height="98" rx="10" stroke="currentColor" stroke-width="2" />
    <circle cx="66" cy="34" r="9" stroke="currentColor" stroke-width="2" />
    <path d="M1 72 L34 44 L60 66 L99 34" stroke="currentColor" stroke-width="2" />
  </svg>`

// Документ пришёл из генерации, поэтому чипа «Ручной режим» нет — он рисуется только когда
// редактор открыт вручную (showManualModeChip={!fromGeneration}).
function editorBreadcrumb() {
  return `
    <div class="me-breadcrumb">
      <button type="button" class="me-breadcrumb-back" aria-label="Назад">
        <span aria-hidden="true">←</span>
        Назад
      </button>
      <div class="me-breadcrumb-chips">
        <span class="me-breadcrumb-chip">
          <span class="me-chip-icon">${PLACEHOLDER_SVG}</span>
          Доклад
        </span>
      </div>
    </div>`
}

function editorExport() {
  return `
    <div class="me-export-control">
      <button type="button" class="me-export-trigger" aria-haspopup="menu" aria-expanded="false">
        Экспорт
      </button>
    </div>`
}

// Кнопки панели — TOOLBAR_ACTIONS в том же порядке и с теми же подписями; разделитель
// стоит перед «B» (TOOLBAR_DIVIDER_BEFORE). Подписи здесь текстовые, а не иконки, ровно
// как в компоненте — это одно из главных расхождений с дизайном.
const TOOLBAR = [
  ['H3', 'Заголовок 3'],
  ['B', 'Жирный'],
  ['I', 'Курсив'],
  ['S', 'Зачёркнутый'],
  ['U', 'Подчёркнутый'],
  ['<>', 'Код'],
  ['"', 'Цитата'],
  ['•', 'Маркированный список'],
  ['1.', 'Нумерованный список'],
  ['―', 'Горизонтальная линия'],
  ['{}', 'Блок кода'],
  ['↔', 'Выравнивание по центру'],
  ['⊞', 'Вставить таблицу'],
  ['+—', 'Добавить строку'],
  ['+|', 'Добавить столбец'],
  ['⌫⊞', 'Удалить таблицу'],
  ['🔗', 'Ссылка'],
  ['↶', 'Отменить'],
  ['↷', 'Повторить'],
]

// Действия над таблицей и отмена/повтор в компоненте отключены, пока их нельзя применить:
// каретка не в таблице, история пуста.
const DISABLED = new Set(['Добавить строку', 'Добавить столбец', 'Удалить таблицу', 'Отменить', 'Повторить'])

function editorToolbar() {
  const buttons = TOOLBAR.map(([label, aria]) => {
    const divider = aria === 'Жирный' ? '<div class="me-toolbar-divider" aria-hidden="true"></div>' : ''
    const off = DISABLED.has(aria) ? ' disabled' : ''
    return `${divider}<button type="button" class="me-toolbar-btn" aria-label="${aria}" aria-pressed="false"${off}>${label}</button>`
  }).join('')

  return `
    <div class="me-toolbar">
      ${buttons}
      <div class="me-toolbar-status">
        <span class="me-save-status me-save-status--saved">${PLACEHOLDER_SVG} Сохранено</span>
        <button type="button" class="me-save-btn">Сохранить</button>
      </div>
    </div>`
}

// Готовый текст — то, что редактор получает из генерации: разметка ProseMirror после
// разбора Markdown с сервера. Заголовки h3, абзацы, список и цитата — всё, что панель
// умеет ставить, чтобы на одном экране было видно, как это выглядит.
function editorContent() {
  return `
    <div class="ProseMirror" contenteditable="true" role="textbox" aria-multiline="true">
      <h3>Введение</h3>
      <p>
        Искусственный интеллект перестал быть предметом отдалённых прогнозов и стал рабочим
        инструментом: он пишет код, ставит диагнозы и отбирает резюме. Вопрос уже не в том,
        заменит ли он человека, а в том, какие именно задачи перейдут к машине и что останется
        людям.
      </p>
      <h3>Как меняется рынок труда</h3>
      <p>
        Автоматизация затрагивает не профессии целиком, а отдельные операции внутри них.
        Профессия исчезает лишь тогда, когда из неё уходит почти всё, что поддавалось описанию
        в виде правил.
      </p>
      <ul>
        <li>Рутинные операции с данными автоматизируются первыми.</li>
        <li>Работа с людьми и ответственность за решение остаются человеку.</li>
        <li>Появляется спрос на тех, кто проверяет и настраивает модели.</li>
      </ul>
      <blockquote>
        <p>
          Технология не отменяет труд — она меняет его состав, и вместе с ним требования к
          образованию.
        </p>
      </blockquote>
      <h3>Выводы</h3>
      <p>
        Выигрывают не те отрасли, где людей заменили дешевле всего, а те, где нашли разделение
        задач между человеком и моделью. Издержки перехода несут работники, которых никто не
        переучил заранее, поэтому переобучение — не социальная надбавка, а часть внедрения.
      </p>
    </div>`
}

document.querySelectorAll('[data-mock="editor-header"]').forEach((s) => (s.outerHTML = editorHeader()))
document.querySelectorAll('[data-mock="editor-breadcrumb"]').forEach((s) => (s.outerHTML = editorBreadcrumb()))
document.querySelectorAll('[data-mock="editor-export"]').forEach((s) => (s.outerHTML = editorExport()))
document.querySelectorAll('[data-mock="editor-toolbar"]').forEach((s) => (s.outerHTML = editorToolbar()))
document.querySelectorAll('[data-mock="editor-content"]').forEach((s) => (s.innerHTML = editorContent()))

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
