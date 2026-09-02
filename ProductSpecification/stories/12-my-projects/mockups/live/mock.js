/* Повторяющиеся куски разметки мока: шапка, тулбар, карточка, строка таблицы.
   Футера на фреймах «Мои проекты» нет — экран кончается лентой карточек.
   Каждый описан один раз — как соответствующий компонент. Данные — в mock-data.js.
   Слоты в HTML: data-mock="navbar|toolbar", data-feed="N" (сетка), data-table="N". */

function card(project) {
  return `
    <div class="project-card project-card-accent-${project.accent} project-card-openable">
      <div class="project-card-thumb">${FOLDER_SVG()}</div>
      <div class="project-card-body">
        <!-- Бейдж и «···» стоят в одной строке: на мобильных фреймах у карточки появляется
             кнопка действий, которой в десктопной сетке нет (там она только в таблице).
             Кнопка рисуется всегда, а прячется на широких экранах — разметка одна. -->
        <div class="project-card-head">
          <span class="project-card-type">${project.type}</span>
          <button type="button" class="project-card-more" aria-label="Действия над проектом">
            <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
              <circle cx="5" cy="12" r="2" /><circle cx="12" cy="12" r="2" /><circle cx="19" cy="12" r="2" />
            </svg>
          </button>
        </div>
        <div class="project-card-title">
          <button type="button" class="project-card-open">${project.title}</button>
        </div>
        <div class="project-card-date">${project.date}</div>
      </div>
    </div>`
}

// Строка таблицы вида списком: плитка с иконкой, название, бейдж типа, дата, «···».
function row(project) {
  return `
    <tr>
      <td>
        <div class="projects-row-name">
          <span class="projects-row-thumb project-card-accent-${project.accent}">${FOLDER_SVG()}</span>
          <span class="projects-row-title">${project.title}</span>
        </div>
      </td>
      <td class="project-card-accent-${project.accent}"><span class="project-card-type">${project.type}</span></td>
      <td class="projects-row-date">${project.date}</td>
      <td>
        <button type="button" class="projects-row-more" aria-label="Действия над проектом">
          <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
            <circle cx="5" cy="12" r="2" /><circle cx="12" cy="12" r="2" /><circle cx="19" cy="12" r="2" />
          </svg>
        </button>
      </td>
    </tr>`
}

// Бейдж и папка тонируются одним классом акцента, поэтому в таблице класс висит и на
// плитке, и на бейдже — иначе цвет типа пришлось бы держать в двух местах.
function table(count) {
  return `
    <table class="projects-table">
      <thead>
        <tr>
          <th>Название</th>
          <th class="projects-table-type">Тип</th>
          <th class="projects-table-date">Дата создания</th>
          <th class="projects-table-actions"></th>
        </tr>
      </thead>
      <tbody>${PROJECTS.slice(0, count).map(row).join('')}</tbody>
    </table>`
}

function navbar() {
  return `
    <div class="navbar-projects-placement">
      <nav class="navbar navbar-pill">
        <img class="navbar-logo navbar-logo-light" src="${ASSETS}/logo-textery.svg" alt="Textery">
        <!-- Две картинки, показывается одна: словесный знак чёрный и в тёмной теме исчезал бы
             на пилюле, а фильтром его не вывернуть — глиф рядом должен остаться синим. -->
        <img class="navbar-logo navbar-logo-dark" src="${ASSETS}/logo-textery-dark.svg" alt="">
        <div class="navbar-actions">
          <button type="button" class="theme-switch" role="switch" aria-checked="false" aria-label="Тёмная тема">
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
          <div class="profile-menu">
            <button type="button" class="profile-trigger" aria-haspopup="menu" aria-expanded="false">
              <span class="profile-avatar profile-avatar-trigger">АС</span>
              <svg class="profile-chevron" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path d="m7 10 5 5 5-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
              </svg>
            </button>
          </div>
        </div>
      </nav>
    </div>`
}

// Тулбар: поиск, фильтр, сортировка, счётчик найденного, «Создать проект» и переключатель
// вида (ProjectsToolbar.tsx). Счётчик рисуется только при активном поиске.
function toolbar({ query = '', view = 'grid', count = null }) {
  return `
      <div class="projects-toolbar">
        <div class="projects-toolbar-filters">
          <search class="projects-search">
            <form class="projects-search-field" onsubmit="return false">
              <svg class="projects-search-icon" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <circle cx="11" cy="11" r="7" stroke="currentColor" stroke-width="2" />
                <path d="M16.5 16.5 21 21" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
              </svg>
              <input type="search" class="projects-search-input" aria-label="Поиск по проектам"
                     placeholder="Поиск проектов..." value="${query}">
            </form>
          </search>
          <button type="button" class="projects-icon-button" aria-label="Фильтры">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"
                 stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M4.5 6.2h15a1 1 0 0 1 .74 1.67l-5.1 5.6a1.5 1.5 0 0 0-.39 1v3.2a1 1 0 0 1-.55.9l-2.4 1.2a1 1 0 0 1-1.45-.9v-4.4a1.5 1.5 0 0 0-.39-1l-5.1-5.6A1 1 0 0 1 4.5 6.2Z" />
            </svg>
          </button>
          <button type="button" class="projects-icon-button" aria-label="Сортировка">
            <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8"
                 stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path class="projects-sort-arrow-idle" stroke="currentColor" d="M8 4.5v14m0 0-3.2-3.2M8 18.5l3.2-3.2" />
              <path stroke="currentColor" d="M16 19.5v-14m0 0-3.2 3.2M16 5.5l3.2 3.2" />
            </svg>
          </button>
          ${count === null ? '' : `<span class="projects-result-count">Найдено: ${count}</span>`}
        </div>
        <div class="projects-toolbar-actions">
          <button type="button" class="projects-create-button">
            <svg class="projects-create-sparkle" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
              <path d="M10 2.5 11.9 8.1 17.5 10 11.9 11.9 10 17.5 8.1 11.9 2.5 10 8.1 8.1Z" />
              <path d="M18 14.5 18.9 17.1 21.5 18 18.9 18.9 18 21.5 17.1 18.9 14.5 18 17.1 17.1Z" />
            </svg>
            Создать проект
          </button>
          <fieldset class="projects-view-toggle" aria-label="Вид списка">
            <button type="button" aria-label="Сеткой" aria-pressed="${view === 'grid'}">
              <svg class="projects-view-icon" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <rect x="3" y="3" width="8" height="8" rx="2" /><rect x="13" y="3" width="8" height="8" rx="2" />
                <rect x="3" y="13" width="8" height="8" rx="2" /><rect x="13" y="13" width="8" height="8" rx="2" />
              </svg>
            </button>
            <button type="button" aria-label="Списком" aria-pressed="${view === 'list'}">
              <svg class="projects-view-icon" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <circle cx="5" cy="6" r="1.6" /><circle cx="5" cy="12" r="1.6" /><circle cx="5" cy="18" r="1.6" />
                <rect x="9" y="5" width="12" height="2" rx="1" /><rect x="9" y="11" width="12" height="2" rx="1" />
                <rect x="9" y="17" width="12" height="2" rx="1" />
              </svg>
            </button>
          </fieldset>
        </div>
      </div>`
}

// data-mock="navbar|toolbar" — вставить кусок; data-feed="N" — N карточек из PROJECTS.
document.querySelectorAll('[data-mock="navbar"]').forEach((slot) => (slot.outerHTML = navbar()))

// Тумблер в моке рабочий: тёмную тему правят, глядя на неё, а не переписывая атрибут в
// HTML руками. Состояние держит сам `<html data-theme>`, как в приложении.
document.querySelectorAll('.theme-switch').forEach((button) => {
  const sync = () => {
    const dark = document.documentElement.dataset.theme === 'dark'
    button.setAttribute('aria-checked', String(dark))
  }
  // Атрибут может менять не только клик (скриншотер выставляет его снаружи), поэтому
  // состояние тумблера следит за `<html>`, а не за собственным обработчиком.
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
document.querySelectorAll('[data-mock="toolbar"]').forEach((slot) => {
  const { query, view, count } = slot.dataset
  slot.outerHTML = toolbar({ query, view, count: count === undefined ? null : Number(count) })
})
document.querySelectorAll('[data-table]').forEach((slot) => {
  slot.outerHTML = table(Number(slot.dataset.table))
})
document.querySelectorAll('[data-feed]').forEach((feed) => {
  const count = Number(feed.dataset.feed)
  feed.innerHTML = PROJECTS.slice(0, count).map(card).join('')
})
