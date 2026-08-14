import os

# `container.runtime` builds the SQLAlchemy engine and the JWT token service at
# import time (module-level singletons), so importing any wiring module requires
# DATABASE_URL and JWT_SECRET to be present. The engine is lazy (no connection is
# opened until a session is used) and these wiring tests patch `session_factory`,
# so dummy values are enough to let the import succeed in isolation. `setdefault`
# never overrides the real values a full `pytest backend/` run already exports.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
os.environ.setdefault("JWT_SECRET", "test-secret-for-wiring-import-only")
# runtime also builds the generation provider at import; the fake needs no
# credentials, so the composition root imports without GIGACHAT_CREDENTIALS.
os.environ.setdefault("GENERATION_PROVIDER", "fake")
# The `container` package __init__ now also imports `oauth_wiring`, which fail-fasts
# at import unless the Yandex credentials are present (invariant I7 — Yandex is the
# shipped provider). The fake OAuth provider needs no network, so dummy non-blank
# values are enough to let the wiring import succeed in isolation, exactly as the
# DATABASE_URL/JWT_SECRET dummies above do.
os.environ.setdefault("YANDEX_CLIENT_ID", "wiring-import-only")
os.environ.setdefault("YANDEX_CLIENT_SECRET", "wiring-import-only")
os.environ.setdefault("OAUTH_PROVIDER", "fake")
# The two callback URLs are required now rather than defaulting to a localhost
# address inside the source: the handoff code exchanges for a token pair, and a
# plaintext fallback is not something a misconfigured deployment should get
# silently. Same dummy treatment as the credentials above.
os.environ.setdefault("YANDEX_REDIRECT_URI", "https://wiring-import-only.example/auth/callback")
os.environ.setdefault(
    "OAUTH_FRONTEND_CALLBACK_URL", "https://wiring-import-only.example/auth/callback"
)
# Read only under OAUTH_PROVIDER=fake, which this conftest selects.
os.environ.setdefault("OAUTH_FAKE_AUTHORIZE_URL", "https://wiring-import-only.example/authorize")
