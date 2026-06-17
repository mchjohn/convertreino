class DomainValidationError(ValueError):
    """Raised when domain entity validation fails."""


class DomainIntegrityError(Exception):
    """Raised when a persistence operation violates domain integrity constraints."""
