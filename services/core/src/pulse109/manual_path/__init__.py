"""ML-independent manual appeal workflow.

The package is intentionally backed by an in-memory repository for the pilot
vertical slice. The router factory lets the production root replace that
repository without changing the application service contract.
"""

from .models import (
    AssignmentCommand,
    ClassificationInput,
    ClassificationRecommendation,
    CreateRequest,
    OperatorDecision,
    StatusEventInput,
)
from .repository import InMemoryManualRepository
from .router import create_manual_router
from .service import ManualPathService

__all__ = [
    "AssignmentCommand",
    "ClassificationInput",
    "ClassificationRecommendation",
    "CreateRequest",
    "InMemoryManualRepository",
    "ManualPathService",
    "OperatorDecision",
    "StatusEventInput",
    "create_manual_router",
]
