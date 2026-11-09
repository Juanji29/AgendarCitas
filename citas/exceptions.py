class DomainValidationError(Exception):
    """Raised when domain input violates a business rule."""


class NotFoundError(Exception):
    """Raised when a requested domain resource does not exist."""


class ConflictError(Exception):
    """Raised when an operation conflicts with the current domain state."""
