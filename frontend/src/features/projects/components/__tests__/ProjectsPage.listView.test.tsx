import { describe, expect, it, vi } from 'vitest'
import { fireEvent, screen, within } from '@testing-library/react'
import { mockFeed, resetFeedMocks, renderProjectsPage } from './feedTestHarness'
import { DOCUMENT, GENERATION } from './projectFixtures'

vi.mock('../../api/projectsApi')

// Вид списком — не та же сетка с другим классом: фрейм «Мои проекты — вид списком — вариант 1»
// рисует таблицу с шапкой столбцов. Проверяется структура, а не класс: класс переживёт любую
// перестановку разметки, а объявление «Тип» рядом со значением — нет.
describe('ProjectsPage — вид списком', () => {
  resetFeedMocks()

  it('показывает ленту таблицей со столбцами и значениями в них', async () => {
    mockFeed([DOCUMENT, GENERATION], 2)

    renderProjectsPage()
    await screen.findAllByTestId('project-card')
    fireEvent.click(screen.getByTestId('projects-view-list'))

    // Таблиц на экране две — рейл недавних и полный список; берётся вторая, «Все проекты».
    const table = screen.getAllByRole('table')[1]
    const headers = within(table)
      .getAllByRole('columnheader')
      .map((cell) => cell.textContent)
    expect(headers).toEqual(['Название', 'Тип', 'Дата создания', ''])

    // Строк ровно столько же, сколько карточек было в сетке: переключение вида перерисовывает
    // данные, которые уже на руках, и не должно ни терять, ни добавлять записи.
    const rows = within(table).getAllByRole('row')
    expect(rows).toHaveLength(3)
    expect(within(rows[1]).getByTestId('project-card-title')).toHaveTextContent(DOCUMENT.title!)
    expect(within(rows[1]).getByTestId('project-card-type')).toHaveTextContent('Реферат')
  })

  // Рейл «Недавние проекты» следует выбранному виду: на фрейме «вид списком» шапка столбцов
  // стоит и над ним, и над «Всеми проектами». Рейл, застрявший карточками, показал бы одну и ту
  // же запись на одном экране в двух разных формах.
  it('переводит в таблицу и рейл недавних, и полный список', async () => {
    mockFeed([DOCUMENT, GENERATION], 2)

    renderProjectsPage()
    await screen.findAllByTestId('project-card')
    fireEvent.click(screen.getByTestId('projects-view-list'))

    const [recent, all] = screen.getAllByRole('table')
    // Рейл — те же первые записи ленты, а не отдельный запрос: строк в нём не больше четырёх,
    // а в полном списке — столько же, сколько записей отдал сервер.
    expect(within(recent).getAllByTestId('recent-project-card')).toHaveLength(2)
    expect(within(all).getAllByTestId('project-card')).toHaveLength(2)
  })
})
