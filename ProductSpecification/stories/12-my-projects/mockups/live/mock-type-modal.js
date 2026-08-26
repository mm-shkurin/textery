/* Модалка «Создание проекта» — снимок текущих компонентов TypeModal.tsx и TypeCard.tsx.
   Отдельный файл: mock.js описывает экран «Мои проекты» и упирается в лимит 200 строк,
   а модалка — другой компонент и другой предмет правки. */

// Карточки типов документа — те же четыре, что отдаёт DOCUMENT_TYPES в приложении.
// Плитка выбирается классом `type-card-<цвет>`, как TILE_BY_TYPE в TypeCard.tsx.
const DOCUMENT_TYPES = [
  { tile: 'blue', name: 'Реферат', description: 'Изложение темы с выводами' },
  { tile: 'coral', name: 'Эссе', description: 'Личный взгляд на проблему' },
  { tile: 'violet', name: 'Доклад', description: 'Текст для устного выступления' },
  { tile: 'teal', name: 'Сочинение', description: 'Рассуждение на тему с позицией' },
]

function typeCard(type) {
  return `
    <button type="button" class="type-card type-card-${type.tile}">
      <span class="type-card-tile"></span>
      <span class="type-card-heading">
        <span class="type-card-name">${type.name}</span>
        <svg class="type-card-chevron" viewBox="8 4 9 16" fill="none" aria-hidden="true">
          <path d="m9 5 7 7-7 7" stroke="currentColor" stroke-width="2"
                stroke-linecap="round" stroke-linejoin="round" />
        </svg>
      </span>
      <span class="type-card-description">${type.description}</span>
    </button>`
}

document.querySelectorAll('[data-types]').forEach((slot) => {
  slot.innerHTML = DOCUMENT_TYPES.map(typeCard).join('')
})
