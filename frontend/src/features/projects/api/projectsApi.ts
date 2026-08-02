// RED-phase stub for the «Мои проекты» feed client (story 12). The real binding is written in
// this scenario's `red-frontend-api`/`green-frontend-api` legs; `GET /api/v1/projects` does not
// exist on the backend yet, so nothing here may call it.
//
// `kind` and `status` are typed as plain strings on purpose, not as unions: the server owns both
// vocabularies and can add a member before this client knows it, and the story's deny-by-default
// rule (an unrecognised kind or status renders a neutral, non-interactive card) only has
// something to render if the unknown value survives the boundary instead of failing to parse.

// Summary projection — no `content`. See ProductSpecification/api-specs/projects_schemas.yaml.
export interface ProjectSummary {
  kind: string
  // String-serialized: a numeric id above 2^53 would round in the browser's JSON parse and
  // collapse two projects onto one key. Ids come from two tables and CAN collide, which is why
  // every consumer keys on (kind, id) and never on id alone.
  id: string
  title: string | null
  preview: string | null
  documentType: string
  status: string
  // Server-computed. Never derived here from `status`: a client computing it from an enum it
  // does not fully know would offer «Повторить» on an unknown status (fail-open).
  canRepeat: boolean
  createdAt: string
  updatedAt: string
}

export interface ProjectPage {
  items: ProjectSummary[]
  // Items in the filtered set, not on this page — offset paging needs it to know there is a
  // page 2.
  total: number
  page: number
  limit: number
}

export interface ListProjectsParams {
  q?: string
  sort?: string
  page?: number
  limit?: number
}

export async function listProjects(_params?: ListProjectsParams): Promise<ProjectPage> {
  throw new Error('Not implemented')
}
