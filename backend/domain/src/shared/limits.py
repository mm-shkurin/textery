"""The product's size limits, loaded from `limits.toml` beside this module.

Data rather than a dozen scattered module constants: each of these is a number a
product decision can change, and each used to be a source edit in a different
file. The TOML carries the reasoning for every entry, which is where a reader
looking for "why 254" should end up.

stdlib only — the domain layer takes no third-party dependency, and `tomllib` has
been part of the standard library since 3.11.
"""

import tomllib
from pathlib import Path

_LIMITS_FILE = Path(__file__).with_name("limits.toml")

with _LIMITS_FILE.open("rb") as _handle:
    _LIMITS = tomllib.load(_handle)

_AUTH = _LIMITS["auth"]
_DOCUMENT = _LIMITS["document"]
_GENERATION = _LIMITS["generation"]
_FEED = _LIMITS["feed"]
_ANALYTICS = _LIMITS["analytics"]

MAX_EMAIL_LENGTH: int = _AUTH["max_email_length"]
MAX_PASSWORD_LENGTH: int = _AUTH["max_password_length"]
MAX_RAW_NAME_LENGTH: int = _AUTH["max_raw_name_length"]
MAX_AVATAR_SIDE_PIXELS: int = _AUTH["max_avatar_side_pixels"]
MAX_HANDOFF_CODE_LENGTH: int = _AUTH["max_handoff_code_length"]

MAX_QUERY_LENGTH: int = _DOCUMENT["max_query_length"]
MAX_GENERATED_TITLE_LENGTH: int = _DOCUMENT["max_generated_title_length"]
MAX_IDEMPOTENCY_KEY_LENGTH: int = _DOCUMENT["max_idempotency_key_length"]

MAX_TOPIC_LENGTH: int = _GENERATION["max_topic_length"]
MAX_REQUIREMENTS_LENGTH: int = _GENERATION["max_requirements_length"]
MAX_EXTRA_WISHES_LENGTH: int = _GENERATION["max_extra_wishes_length"]

PAGE_MAX: int = _FEED["page_max"]
LIMIT_MAX: int = _FEED["limit_max"]
PREVIEW_MAX_CODE_POINTS: int = _FEED["preview_max_code_points"]
PREVIEW_SOURCE_MAX_CHARS: int = _FEED["preview_source_max_chars"]
QUERY_MAX_CODE_POINTS: int = _FEED["query_max_code_points"]

MAX_PAYLOAD_SERIALIZED_BYTES: int = _ANALYTICS["max_payload_serialized_bytes"]
MAX_ATTRIBUTION_VALUE_CODE_POINTS: int = _ANALYTICS["max_attribution_value_code_points"]
MAX_USER_AGENT_LENGTH: int = _ANALYTICS["max_user_agent_length"]
MAX_LANGUAGE_HEADER_LENGTH: int = _ANALYTICS["max_language_header_length"]
