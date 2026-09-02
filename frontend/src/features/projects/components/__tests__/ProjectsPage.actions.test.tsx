import { describe, expect, it, vi } from 'vitest'
import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { mockFeed, resetFeedMocks, renderProjectsPage } from './feedTestHarness'
import { DOCUMENT, GENERATION } from './projectFixtures'
import * as documentActionsApi from '../../api/documentActionsApi'

vi.mock('../../api/projectsApi')
vi.mock('../../api/documentActionsApi')

// «···» на карточке была нарисована отключённой — «действия появятся позже», — и менеджер на
// проде прочитал это как сломанную кнопку. Оба действия контракт умеет: DELETE /documents/{id}
// есть, переименование делается PUT'ом с тем же телом и новым названием.
describe('ProjectsPage — действия над проектом', () => {
  resetFeedMocks()

  it('удаляет проект и перечитывает ленту', async () => {
    mockFeed([DOCUMENT], 1)
    vi.mocked(documentActionsApi.deleteDocument).mockResolvedValue(undefined)
    renderProjectsPage()

    const card = await screen.findByTestId('project-card-document-1')
    fireEvent.click(within(card).getByTestId('project-card-menu'))
    fireEvent.click(screen.getByTestId('project-card-menu-delete'))

    expect(documentActionsApi.deleteDocument).toHaveBeenCalledWith(DOCUMENT.id)
    // Лента перечитывается, а не правится на месте: сортировка и поиск живут на сервере.
    await waitFor(() =>
      expect(vi.mocked(documentActionsApi.deleteDocument)).toHaveBeenCalledTimes(1),
    )
  })

  it('переименовывает проект введённым названием', async () => {
    mockFeed([DOCUMENT], 1)
    vi.mocked(documentActionsApi.renameDocument).mockResolvedValue(undefined)
    renderProjectsPage()

    const card = await screen.findByTestId('project-card-document-1')
    fireEvent.click(within(card).getByTestId('project-card-menu'))
    fireEvent.click(screen.getByTestId('project-card-menu-rename'))
    fireEvent.change(screen.getByTestId('project-card-menu-rename-input'), {
      target: { value: '  Новое название  ' },
    })
    fireEvent.click(screen.getByTestId('project-card-menu-rename-submit'))

    // Обрезка по краям здесь, а не на сервере: пользователь не должен получить проект с
    // пробелом в начале названия только потому, что промахнулся мимо поля.
    expect(documentActionsApi.renameDocument).toHaveBeenCalledWith(DOCUMENT.id, 'Новое название')
  })

  it('не шлёт запрос, когда название не изменилось', async () => {
    mockFeed([DOCUMENT], 1)
    renderProjectsPage()

    const card = await screen.findByTestId('project-card-document-1')
    fireEvent.click(within(card).getByTestId('project-card-menu'))
    fireEvent.click(screen.getByTestId('project-card-menu-rename'))
    fireEvent.click(screen.getByTestId('project-card-menu-rename-submit'))

    expect(documentActionsApi.renameDocument).not.toHaveBeenCalled()
  })

  // У генерации нет ни своего DELETE, ни названия, которое можно править. Кнопки там нет
  // вовсе — отключённая обещала бы меню, которого не будет.
  it('не предлагает действий у генерации', async () => {
    mockFeed([GENERATION], 1)
    renderProjectsPage()

    const card = await screen.findByTestId('project-card-generation-1')
    expect(within(card).queryByTestId('project-card-menu')).toBeNull()
  })

  // Сообщение приходит из `describeFailure`: у ошибки с текстом это её собственный текст, а
  // запасная фраза — для отказов, которые сказать о себе ничего не могут (обрыв связи, таймаут).
  it('показывает отказ на той карточке, которой он касается', async () => {
    mockFeed([DOCUMENT], 1)
    vi.mocked(documentActionsApi.deleteDocument).mockRejectedValue(
      new Error('Проект уже удалён на другом устройстве'),
    )
    renderProjectsPage()

    const card = await screen.findByTestId('project-card-document-1')
    fireEvent.click(within(card).getByTestId('project-card-menu'))
    fireEvent.click(screen.getByTestId('project-card-menu-delete'))

    expect(await screen.findByTestId('project-card-action-error')).toHaveTextContent(
      'Проект уже удалён на другом устройстве',
    )
  })
})
