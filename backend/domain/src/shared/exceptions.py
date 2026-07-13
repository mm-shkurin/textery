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
