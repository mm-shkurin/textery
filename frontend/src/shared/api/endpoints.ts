// The one place that knows the server's URL space.
//
// Before this file the same path was typed as a literal in every module that called it —
// `/api/v1/auth/login` in loginApi, `/api/v1/documents` in three separate modules — while the
// identity slice kept its paths in local constants. Two conventions in one codebase, and a
// server-side rename meant grepping for a string.
//
// Paths only. Everything about *how* a request is sent (headers, renewal, error shape) belongs to
// `httpClient`/`send`; this module is a map, not a client. Segments that vary are functions so a
// caller cannot forget to encode them.

// Assembled from its segments rather than written as one literal, mirroring the backend's
// `adapters/rest/src/router/api_routes.py`: the mount point and the version are what a bump
// actually edits, and a bare '/api/v1' hides the version inside a path string where nothing can
// name it. Not configuration — the URL space is part of the published contract
// (ProductSpecification/api-specs/*.yaml) and moves only with it.
const MOUNT = 'api'
export const API_VERSION = 'v1'

const V1 = `/${MOUNT}/${API_VERSION}`

export const API = {
  auth: {
    login: `${V1}/auth/login`,
    register: `${V1}/auth/register`,
    verify: `${V1}/auth/verify`,
    resendCode: `${V1}/auth/resend-code`,
    refresh: `${V1}/auth/refresh`,
    oauthExchange: `${V1}/auth/oauth/exchange`,
    oauthStart: (provider: string) => `${V1}/auth/oauth/${encodeURIComponent(provider)}/start`,
  },
  identity: {
    me: `${V1}/auth/me`,
    avatar: `${V1}/auth/me/avatar`,
    deletion: `${V1}/auth/me/deletion`,
  },
  documents: {
    collection: `${V1}/documents`,
    fromGeneration: `${V1}/documents/from-generation`,
    one: (id: string) => `${V1}/documents/${encodeURIComponent(id)}`,
    export: (id: string, format: string) =>
      `${V1}/documents/${encodeURIComponent(id)}/export?format=${encodeURIComponent(format)}`,
  },
  projects: {
    collection: `${V1}/projects`,
  },
  generations: {
    collection: `${V1}/generations`,
    one: (id: string) => `${V1}/generations/${encodeURIComponent(id)}`,
  },
} as const
