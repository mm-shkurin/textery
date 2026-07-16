class DomainException(Exception):
    pass


class ValidationException(DomainException):
    def __init__(self, message: str, error_code: str = "VALIDATION_ERROR") -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message


class NotFoundException(DomainException):
    pass


class ConfigurationException(DomainException):
    pass


class ConflictException(DomainException):
    pass


class RegistrationFailedException(DomainException):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class VerificationFailedException(DomainException):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class InvalidTokenException(DomainException):
    """A token is expired, tampered with, signed by another key, or the wrong type.

    Deliberately one exception for every cause: the client gets the same answer
    for all of them, so distinguishing them here would only invite a handler that
    leaks which one it was.
    """

    pass
