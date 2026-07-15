# Errors use the uniform { error_code, message } shape per
# ProductSpecification/stories/07-authorization/endpoints.md.
MALFORMED_EMAIL_ERROR: dict = {
    "error_code": "INVALID_EMAIL",
    "message": "The email address is not valid.",
}
WEAK_PASSWORD_ERROR: dict = {
    "error_code": "INVALID_PASSWORD",
    "message": "The password does not meet the password policy.",
}
PASSWORD_MISMATCH_ERROR: dict = {
    "error_code": "PASSWORD_MISMATCH",
    "message": "The password confirmation does not match.",
}
DUPLICATE_EMAIL_ERROR: dict = {
    "error_code": "EMAIL_ALREADY_REGISTERED",
    "message": "An account with this email address already exists.",
}
