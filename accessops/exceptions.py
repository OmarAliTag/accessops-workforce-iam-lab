class AccessOpsError(Exception):
    """Base class for expected lab errors."""


class ValidationError(AccessOpsError):
    """The change request is incomplete or malformed."""


class PolicyViolation(AccessOpsError):
    """The requested access would violate a lab policy."""


class IdentityNotFound(AccessOpsError):
    """The requested synthetic identity does not exist."""


class IdentityConflict(AccessOpsError):
    """The requested identity already exists or conflicts with current state."""


class IdempotencyConflict(AccessOpsError):
    """An event ID was reused with a different request body."""


class ProviderError(AccessOpsError):
    """The identity provider could not complete the request."""
