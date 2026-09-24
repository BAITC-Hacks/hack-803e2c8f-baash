"""Application errors for ownership commands."""


class HandoffOutcomeError(Exception):
    """Safe application error for a rejected handoff outcome command."""

    def __init__(self, code: str, message: str, status_code: int = 409) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
