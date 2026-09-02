/* Редактор — дизайн по фрейму, НАБОР КОНТРОЛОВ по компоненту.
   Сравнивать с 09-editor.html (как это выглядит сейчас) и с фреймом (как должно выглядеть).

   Правило этого файла: на панели стоит только то, что редактор реально умеет сегодня —
   TOOLBAR_ACTIONS из editorToolbarActions.ts, сохранение (useDocumentSave) и экспорт
   (ExportControl, форматы pdf/docx). Всё, чего в коде нет, вынесено вниз файла списком,
   а не нарисовано: кнопка, которая ничего не делает, хуже её отсутствия.

   Страниц нет: разбиения листа на A4 в продукте не существует. */

const ICONS = {
  back: '<path d="M15 5l-7 7 7 7" />',
  download: '<path d="M12 4v10m0 0 4-4m-4 4-4-4M5 19h14" />',
  bulletList: '<path d="M4 6h.01M4 12h.01M4 18h.01M9 6h11M9 12h11M9 18h11" />',
  orderedList:
    '<path d="M9 6h11M9 12h11M9 18h11" /><text x="2" y="8" font-size="7" fill="currentColor" stroke="none">1</text><text x="2" y="20" font-size="7" fill="currentColor" stroke="none">2</text>',
  quote: '<path d="M9 7H5v5h4v-2c0 2-1 3-3 3M19 7h-4v5h4v-2c0 2-1 3-3 3" />',
  rule: '<path d="M4 12h16" />',
  codeBlock: '<path d="M4 5h16v14H4zM9 10l-2 2 2 2M15 10l2 2-2 2" />',
  alignCenter: '<path d="M4 6h16M7 12h10M5 18h14" />',
  table: '<path d="M4 5h16v14H4zM4 10h16M10 10v9" />',
  rowAdd: '<path d="M4 5h16v6H4zM7 17h6M10 14v6" />',
  columnAdd: '<path d="M4 5h6v14H4zM14 8h6M17 5v6" />',
  tableDelete: '<path d="M4 5h16v14H4zM4 10h16M10 10v9M15 14l4 4m0-4-4 4" />',
  link: '<path d="M10 13a5 5 0 0 0 7 0l2-2a5 5 0 0 0-7-7l-1 1M14 11a5 5 0 0 0-7 0l-2 2a5 5 0 0 0 7 7l1-1" />',
  undo: '<path d="M9 8H5V4M5 8a8 8 0 1 1 3 12" />',
  redo: '<path d="M15 8h4V4m0 4a8 8 0 1 0-3 12" />',
  chevron: '<path d="m6 9 6 6 6-6" />',
  saved: '<path d="m5 12 5 5 9-10" />',
}

function icon(name, extraClass) {
  return `
    <svg class="${extraClass ?? ''}" viewBox="0 0 24 24" fill="none" stroke="currentColor"
         stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
      ${ICONS[name]}
    </svg>`
}

const DOC_TITLE = 'Влияние ИИ на рынок труда'

/* Верхняя полоса.
   - «Назад» вместо иконки дома: у компонента ровно одна навигация — onBack, и она ведёт
     туда, откуда редактор открыли, а не всегда в «Мои проекты».
   - Название — ТЕКСТ, а не поле: переименования документа в контракте нет. Оно приехало из
     генерации и правится только вместе с текстом.
   - Счётчика слов на фрейме нет в коде вообще — вместо него стоит статус сохранения,
     который у компонента есть и который пользователю важнее.
   - «Скачать» открывает меню с двумя форматами — это ExportControl (pdf, docx). */
function topbar() {
  return `
    <div class="edf-topbar">
      <button type="button" class="edf-back">${icon('back')} Назад</button>
      <span class="edf-title-static" title="${DOC_TITLE}">${DOC_TITLE}</span>
      <span class="edf-chip">Доклад</span>
      <span class="edf-status">${icon('saved', 'edf-status-icon')} Сохранено</span>
      <button type="button" class="edf-btn edf-btn-quiet">Сохранить</button>
      <div class="edf-export">
        <button type="button" class="edf-btn edf-btn-primary" aria-haspopup="menu"
                aria-expanded="false">${icon('download')} Скачать ${icon('chevron', 'edf-btn-chevron')}</button>
        <div class="edf-export-menu" role="menu">
          <button type="button" role="menuitem">PDF</button>
          <button type="button" role="menuitem">DOCX</button>
        </div>
      </div>
    </div>`
}

/* Панель форматирования — TOOLBAR_ACTIONS в том же порядке и с теми же значениями, но
   иконками и группами по фрейму вместо текстовых литералов («B», «⌫⊞», «+|»).
   `text` — подпись буквой там, где буква и есть общепринятый знак (B, I, U, S, код). */
const GROUPS = [
  [
    { text: 'H3', aria: 'Заголовок 3', pressed: false },
  ],
  [
    { text: 'B', aria: 'Жирный', pressed: false, style: 'font-weight:700' },
    { text: 'I', aria: 'Курсив', pressed: false, style: 'font-style:italic;font-family:Georgia,serif' },
    { text: 'U', aria: 'Подчёркнутый', pressed: false, style: 'text-decoration:underline' },
    { text: 'S', aria: 'Зачёркнутый', pressed: false, style: 'text-decoration:line-through' },
    { text: '</>', aria: 'Код', pressed: false, style: 'font-size:13px' },
  ],
  [
    { icon: 'bulletList', aria: 'Маркированный список', pressed: false },
    { icon: 'orderedList', aria: 'Нумерованный список', pressed: false },
    { icon: 'quote', aria: 'Цитата', pressed: false },
    { icon: 'codeBlock', aria: 'Блок кода', pressed: false },
    { icon: 'rule', aria: 'Горизонтальная линия' },
  ],
  [{ icon: 'alignCenter', aria: 'Выравнивание по центру', pressed: false }],
  [
    { icon: 'table', aria: 'Вставить таблицу', pressed: false },
    // Три действия над таблицей отключены, пока каретка не внутри неё — так же, как в
    // компоненте, где они гасятся через editor.can().
    { icon: 'rowAdd', aria: 'Добавить строку', disabled: true },
    { icon: 'columnAdd', aria: 'Добавить столбец', disabled: true },
    { icon: 'tableDelete', aria: 'Удалить таблицу', disabled: true },
  ],
  [{ icon: 'link', aria: 'Ссылка', pressed: false }],
  [
    { icon: 'undo', aria: 'Отменить', disabled: true },
    { icon: 'redo', aria: 'Повторить', disabled: true },
  ],
]

function tool(item) {
  const pressed = item.pressed === undefined ? '' : ` aria-pressed="${item.pressed}"`
  const disabled = item.disabled ? ' disabled' : ''
  const style = item.style ? ` style="${item.style}"` : ''
  const body = item.icon ? icon(item.icon) : item.text
  return `<button type="button" class="edf-tool" aria-label="${item.aria}"${pressed}${disabled}${style}>${body}</button>`
}

function toolbar() {
  const groups = GROUPS.map((group) => group.map(tool).join('')).join(
    '<span class="edf-divider" aria-hidden="true"></span>',
  )
  return `
    <div class="edf-toolbar">
      <div class="edf-toolbar-group">${groups}</div>
    </div>`
}

// Текст — то, что редактор получает из генерации: заголовок документа, разделы, абзацы,
// список, цитата. Один непрерывный поток без разрывов страниц.
function doc() {
  return `
    <div class="edf-doc" contenteditable="true" role="textbox" aria-multiline="true"
         aria-label="Текст документа">
      <p class="edf-doc-title">${DOC_TITLE}</p>

      <h3>Введение</h3>
      <p>
        Данный доклад посвящён теме «Влияние ИИ на рынок труда». Актуальность темы обусловлена
        стремительным развитием технологий и необходимостью глубокого осмысления происходящих
        изменений. Цель работы — комплексное исследование ключевых аспектов заявленной темы на
        основе анализа научной литературы и актуальных данных.
      </p>
      <p>Для достижения поставленной цели были определены следующие задачи:</p>
      <ul>
        <li>изучить теоретические основы исследуемого явления;</li>
        <li>проанализировать актуальное состояние проблемы;</li>
        <li>оценить последствия для отдельных отраслей и профессий.</li>
      </ul>

      <h3>Основная часть</h3>
      <p>
        Исследуемая область представляет собой сложный многоаспектный феномен, который привлекал
        внимание учёных на протяжении нескольких десятилетий. Согласно ключевым исследованиям,
        данная тема занимает центральное место в современных научных дискуссиях.
      </p>
      <p>
        Автоматизация затрагивает не профессии целиком, а отдельные операции внутри них.
        Профессия исчезает лишь тогда, когда из неё уходит почти всё, что поддавалось описанию
        в виде правил.
      </p>
      <blockquote>
        <p>
          Технология не отменяет труд — она меняет его состав, а вместе с ним требования к
          образованию.
        </p>
      </blockquote>

      <h3>Заключение</h3>
      <p>
        Выигрывают не те отрасли, где людей заменили дешевле всего, а те, где нашли разделение
        задач между человеком и моделью. Издержки перехода несут работники, которых никто не
        переучил заранее, поэтому переобучение — часть внедрения, а не социальная надбавка.
      </p>
    </div>`
}

/* Чего на панели НЕТ и почему — то, что фрейм рисует, а редактор не умеет:
   шрифт и кегль, цвет текста, отступы (indent), выравнивание по меню (есть только «по
   центру»), межстрочный интервал, счётчик слов, структура документа слева, переименование.
   Ни один из этих атрибутов не хранится: документ уходит на сервер как разметка Tiptap,
   в которой их попросту нет. Каждый из них — отдельная задача (схема документа + контракт),
   а не вопрос вёрстки. */

document.querySelectorAll('[data-mock="edf-topbar"]').forEach((s) => (s.outerHTML = topbar()))
document.querySelectorAll('[data-mock="edf-toolbar"]').forEach((s) => (s.outerHTML = toolbar()))
document.querySelectorAll('[data-mock="edf-doc"]').forEach((s) => (s.innerHTML = doc()))
