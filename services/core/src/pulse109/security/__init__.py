"""Identity and object-scope enforcement for public API routes."""

from .identity import ActorContext, AuthenticatedActor, require_actor

__all__ = ["ActorContext", "AuthenticatedActor", "require_actor"]
