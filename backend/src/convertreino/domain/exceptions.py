class DomainValidationError(ValueError):
    """Raised when domain entity validation fails."""


class DomainIntegrityError(Exception):
    """Raised when a persistence operation violates domain integrity constraints."""


class StravaAuthError(Exception):
    """Raised when Strava OAuth or token refresh fails."""


class StravaApiError(Exception):
    """Raised when the Strava API is temporarily unavailable."""


class UserNotFoundError(Exception):
    """Raised when a requested user does not exist."""
