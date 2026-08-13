"""Binds each router's placeholder dependency to its composition-root factory.

Split out of `main.py`, which was at the 200-line cap: this list grows by one line
per endpoint and nothing else in that file does. Nothing here decides anything --
every choice lives in `container/`; this is the single place where the rest layer's
`raise NotImplementedError("wired by the application composition root")` stubs are
replaced by the real thing.

Imported by `main` AFTER it has set up sys.path, so the adapter packages below
resolve.
"""

from fastapi import FastAPI

from container import (
    create_account_existence,
    create_check_health,
    create_complete_oauth_callback,
    create_create_document,
    create_create_document_from_generation,
    create_exchange_handoff_code,
    create_export_document,
    create_frontend_callback_url,
    create_generate_document,
    create_get_document,
    create_get_generation,
    create_get_profile,
    create_list_documents,
    create_list_generations,
    create_list_projects,
    create_login_user,
    create_refresh_access_token,
    create_register_user,
    create_rename_account,
    create_request_generation,
    create_resend_code,
    create_retry_generation,
    create_save_document,
    create_start_oauth,
    create_token_service,
    create_verify_account,
)
from router.auth.auth_router import (
    get_login_user_usecase,
    get_refresh_access_token_usecase,
    get_register_user_usecase,
    get_resend_code_usecase,
    get_verify_account_usecase,
)
from router.auth.oauth_router import (
    get_complete_oauth_callback_usecase,
    get_exchange_handoff_code_usecase,
    get_frontend_callback_url,
    get_start_oauth_usecase,
)
from router.auth.profile_router import (
    get_get_profile_usecase,
    get_rename_account_usecase,
)
from router.document.document_router import (
    get_create_document_from_generation_usecase,
    get_create_document_usecase,
    get_export_document_usecase,
    get_get_document_usecase,
    get_list_documents_usecase,
    get_save_document_usecase,
)
from router.generation.generation_router import (
    get_generate_document_usecase,
    get_get_generation_usecase,
    get_list_generations_usecase,
    get_request_generation_usecase,
    get_retry_generation_usecase,
)
from router.health.health_router import get_check_health_usecase
from router.project.project_router import get_list_projects_usecase
from security.current_owner import get_account_existence, get_token_service


def install_dependency_overrides(app: FastAPI) -> None:
    app.dependency_overrides[get_request_generation_usecase] = create_request_generation
    app.dependency_overrides[get_get_generation_usecase] = create_get_generation
    app.dependency_overrides[get_list_generations_usecase] = create_list_generations
    app.dependency_overrides[get_retry_generation_usecase] = create_retry_generation
    app.dependency_overrides[get_generate_document_usecase] = create_generate_document
    app.dependency_overrides[get_register_user_usecase] = create_register_user
    app.dependency_overrides[get_verify_account_usecase] = create_verify_account
    app.dependency_overrides[get_resend_code_usecase] = create_resend_code
    app.dependency_overrides[get_login_user_usecase] = create_login_user
    app.dependency_overrides[get_get_profile_usecase] = create_get_profile
    app.dependency_overrides[get_rename_account_usecase] = create_rename_account
    app.dependency_overrides[get_refresh_access_token_usecase] = create_refresh_access_token
    app.dependency_overrides[get_create_document_usecase] = create_create_document
    app.dependency_overrides[get_get_document_usecase] = create_get_document
    app.dependency_overrides[get_export_document_usecase] = create_export_document
    app.dependency_overrides[get_create_document_from_generation_usecase] = (
        create_create_document_from_generation
    )
    app.dependency_overrides[get_list_documents_usecase] = create_list_documents
    app.dependency_overrides[get_save_document_usecase] = create_save_document
    app.dependency_overrides[get_token_service] = create_token_service
    app.dependency_overrides[get_account_existence] = create_account_existence
    app.dependency_overrides[get_check_health_usecase] = create_check_health
    app.dependency_overrides[get_list_projects_usecase] = create_list_projects
    app.dependency_overrides[get_start_oauth_usecase] = create_start_oauth
    app.dependency_overrides[get_complete_oauth_callback_usecase] = create_complete_oauth_callback
    app.dependency_overrides[get_exchange_handoff_code_usecase] = create_exchange_handoff_code
    app.dependency_overrides[get_frontend_callback_url] = create_frontend_callback_url
