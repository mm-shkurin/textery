"""The composition root, split by slice.

One flat `container.py` grew past the 200-line limit as documents and history
landed. The split is by slice rather than by layer -- auth, generation, document --
because that is how the file was actually read: someone wiring a document usecase
never needed the JWT factories on screen.

`runtime.py` holds the process-wide singletons every slice shares (engine, session
factory, token service, provider selection). It is imported by the slices, never the
other way round, so there is no cycle.

This package re-exports the whole surface so `from container import X` keeps working
unchanged -- main.py's import list is the contract, and moving code between files
should not touch it.
"""

from container.auth_wiring import (
    create_login_user,
    create_refresh_access_token,
    create_register_user,
    create_resend_code,
    create_token_service,
    create_verify_account,
)
from container.document_wiring import (
    create_create_document,
    create_get_document,
    create_list_documents,
    create_save_document,
)
from container.generation_wiring import (
    NoOpGenerationQueue,
    create_generate_document,
    create_get_generation,
    create_list_generations,
    create_request_generation,
    run_stale_generation_sweep,
)
from container.oauth_wiring import (
    create_complete_oauth_callback,
    create_exchange_handoff_code,
    create_frontend_callback_url,
    create_start_oauth,
)
from container.runtime import (
    DEFAULT_STALE_AFTER_MINUTES,
    GENERATION_PROVIDER_ENV_VAR,
    JWT_SECRET_ENV_VAR,
    STALE_AFTER_MINUTES_ENV_VAR,
)

__all__ = [
    "DEFAULT_STALE_AFTER_MINUTES",
    "GENERATION_PROVIDER_ENV_VAR",
    "JWT_SECRET_ENV_VAR",
    "NoOpGenerationQueue",
    "STALE_AFTER_MINUTES_ENV_VAR",
    "create_complete_oauth_callback",
    "create_create_document",
    "create_exchange_handoff_code",
    "create_frontend_callback_url",
    "create_generate_document",
    "create_start_oauth",
    "create_get_document",
    "create_get_generation",
    "create_list_documents",
    "create_list_generations",
    "create_login_user",
    "create_refresh_access_token",
    "create_register_user",
    "create_request_generation",
    "create_save_document",
    "create_token_service",
    "create_resend_code",
    "create_verify_account",
    "run_stale_generation_sweep",
]
