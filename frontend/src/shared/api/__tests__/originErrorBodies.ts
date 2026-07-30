// The bodies the ORIGIN actually answers with, measured — not invented. Every suite that stubs a
// refusal reaches for these, because the whole class of bug H9.4 keeps rediscovering is a fixture
// that is more convenient than the real wire: a hand-rolled Russian `message` on a 500 makes the
// "server text reaches the user" claim look proven while the live origin sends English.
//
// Lives under `shared/api` rather than inside a feature's `__tests__` because three features
// (generation, history, and the `describeFailure` unit) all stub the same origin.
export const ORIGIN_INTERNAL_ERROR_BODY = {
  error_code: 'INTERNAL_ERROR',
  message: 'An unexpected error occurred. Please try again.',
}

// A 5xx that is NOT the catch-all: an error the backend deliberately explains, whose text is the
// only place the explanation exists. Present so every suite that pins "INTERNAL_ERROR falls back
// to Russian" also pins the boundary of that carve-out with a body of the same status class.
export const ORIGIN_PROVIDER_UNAVAILABLE_BODY = {
  error_code: 'PROVIDER_UNAVAILABLE',
  message: 'Лимит запросов к провайдеру исчерпан. Попробуйте через час.',
}
