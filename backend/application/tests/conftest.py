import os

# `container.runtime` builds the SQLAlchemy engine and the JWT token service at
# import time (module-level singletons), so importing any wiring module requires
# DATABASE_URL and JWT_SECRET to be present. The engine is lazy (no connection is
# opened until a session is used) and these wiring tests patch `session_factory`,
# so dummy values are enough to let the import succeed in isolation. `setdefault`
# never overrides the real values a full `pytest backend/` run already exports.
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test"
)
os.environ.setdefault("JWT_SECRET", "test-secret-for-wiring-import-only")
# runtime also builds the generation provider at import; the fake needs no
# credentials, so the composition root imports without GIGACHAT_CREDENTIALS.
os.environ.setdefault("GENERATION_PROVIDER", "fake")
