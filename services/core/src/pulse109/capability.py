"""Three honest states for every algorithmic capability.

A detector, a recommender or a retrieval boundary can be right, can decline to
answer, or can be out of service. Collapsing the last two into an empty result
is what makes a system quietly lie: an operator cannot tell "nothing found" from
"nothing ran". Every algorithmic section of a read model therefore carries one
of these states together with a controlled reason code.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class CapabilityState(str, Enum):
    """Why a capability's payload looks the way it does."""

    AVAILABLE = "available"
    """The capability ran and its result stands."""

    ABSTAINED = "abstained"
    """The capability ran and declined, for example below a coverage threshold."""

    UNAVAILABLE = "unavailable"
    """The capability did not run. Its payload carries no information."""


class CapabilityStatus(BaseModel):
    """State plus a controlled reason, never free text from a model."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    state: CapabilityState
    reason_code: str | None = Field(default=None, pattern=r"^[A-Z][A-Z0-9_]{0,63}$")

    @classmethod
    def available(cls, reason_code: str | None = None) -> CapabilityStatus:
        return cls(state=CapabilityState.AVAILABLE, reason_code=reason_code)

    @classmethod
    def abstained(cls, reason_code: str) -> CapabilityStatus:
        return cls(state=CapabilityState.ABSTAINED, reason_code=reason_code)

    @classmethod
    def unavailable(cls, reason_code: str) -> CapabilityStatus:
        return cls(state=CapabilityState.UNAVAILABLE, reason_code=reason_code)

    @property
    def carries_information(self) -> bool:
        """False when the payload must not be read as evidence of absence."""
        return self.state is not CapabilityState.UNAVAILABLE
