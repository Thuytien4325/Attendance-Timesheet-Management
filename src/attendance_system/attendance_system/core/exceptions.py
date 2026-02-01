class DomainError(Exception):
    """Base exception for business rule violations."""


class ValidationError(DomainError):
    """Raised when input data is invalid or violates domain rules."""


class AuthenticationError(DomainError):
    """Raised when login credentials are invalid."""


class AuthorizationError(DomainError):
    """Raised when a user lacks permission for an action."""
