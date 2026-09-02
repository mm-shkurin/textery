import projectsScreenStyles from './ProjectsScreen.module.css'

/**
 * Заголовок экрана: название и одна строка копирайта под ним.
 *
 * Кнопки «Назад» здесь НЕТ. Она вела `backToLanding` — на лендинг, то есть на страницу-продажу
 * для того, кто уже купил; для авторизованного пользователя «Мои проекты» И ЕСТЬ дом, и выход
 * из дома «назад» никуда не ведёт. На проде она читалась как сломанная, потому что нажатие
 * возвращало на витрину, а не туда, откуда пользователь пришёл.
 */
export function ProjectsPageHeader() {
  return (
    <div className={projectsScreenStyles['projects-header']}>
      <div className="projects-titles">
        <h1 className={projectsScreenStyles['projects-heading']}>Мои проекты</h1>
        {/* Единственная строка копирайта экрана, и она фиксированная, а не пользовательская:
            она называет, что лежит на странице, — поэтому живёт в разметке. */}
        <p className={projectsScreenStyles['projects-subtitle']} data-testid="projects-subtitle">
          Все ваши рефераты, курсовые, статьи и другие работы — в одном месте
        </p>
      </div>
    </div>
  )
}
