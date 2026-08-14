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

const V1 = '/api/v1'

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
  generations: {
    collection: `${V1}/generations`,
    one: (id: string) => `${V1}/generations/${encodeURIComponent(id)}`,
  },
} as const
