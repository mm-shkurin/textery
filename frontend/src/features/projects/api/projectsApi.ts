// The «Мои проекты» feed client (story 12). Goes through `send` -> `authorizedRequest` like every
// other authenticated client, so the token travels and a 401 renews and replays.
//
// `kind` and `status` are typed as plain strings on purpose, not as unions: the server owns both
// vocabularies and can add a member before this client knows it, and the story's deny-by-default
// rule (an unrecognised kind or status renders a neutral, non-interactive card) only has
// something to render if the unknown value survives the boundary instead of failing to parse.

import { send } from '../../../shared/api/send'

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

// The wire is snake_case on every field (ProductSpecification/api-specs/projects_schemas.yaml);
// `ProjectSummary` is camelCase. Returning the parsed body untouched would hand `ProjectCard`
// `undefined` for `documentType` and `updatedAt`, so the mapping below is the whole job.
interface ProjectSummaryWire {
  kind: string
  id: string
  title: string | null
  preview: string | null
  document_type: string
  status: string
  can_repeat: boolean
  created_at: string
  updated_at: string
}

interface ProjectPageWire {
  items: ProjectSummaryWire[]
  total: number
  page: number
  limit: number
}

// `_params` is unread on purpose: search, sort and paging query building belong to scenarios
// 2.x/3.x, and building a default `?limit=20` here would pre-decide a contract they own.
export async function listProjects(_params?: ListProjectsParams): Promise<ProjectPage> {
  const data = await send<ProjectPageWire>(
    '/api/v1/projects',
    {},
    'Не удалось загрузить проекты',
  )
  return {
    items: data.items.map((item) => ({
      kind: item.kind,
      id: item.id,
      title: item.title,
      preview: item.preview,
      documentType: item.document_type,
      status: item.status,
      canRepeat: item.can_repeat,
      createdAt: item.created_at,
      updatedAt: item.updated_at,
    })),
    total: data.total,
    page: data.page,
    limit: data.limit,
  }
}
