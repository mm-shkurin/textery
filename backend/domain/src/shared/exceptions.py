class DomainException(Exception):
    pass


class ValidationException(DomainException):
    pass


class NotFoundException(DomainException):
    pass


class ConfigurationException(DomainException):
    pass


class ConflictException(DomainException):
    pass
