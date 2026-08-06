interface ProjectsPagerProps {
  page: number
  limit: number
  total: number
  onPage: (page: number) => void
}

/**
 * Previous/next over the offset-paginated feed.
 *
 * The page count comes from `total`, which is the size of the FILTERED set rather than of the
 * window — deriving it from `items.length` would hide page 2 from every user whose first page
 * happened to be full.
 */
export function ProjectsPager({ page, limit, total, onPage }: ProjectsPagerProps) {
  const pageCount = Math.max(1, Math.ceil(total / Math.max(1, limit)))
  if (pageCount <= 1) return null

  return (
    <nav className="projects-pager" data-testid="projects-pager" aria-label="Страницы проектов">
      <button
        type="button"
        data-testid="projects-page-prev"
        disabled={page <= 1}
        onClick={() => onPage(page - 1)}
      >
        Назад
      </button>
      <span data-testid="projects-page-position">
        {page} из {pageCount}
      </span>
      <button
        type="button"
        data-testid="projects-page-next"
        disabled={page >= pageCount}
        onClick={() => onPage(page + 1)}
      >
        Вперёд
      </button>
    </nav>
  )
}
