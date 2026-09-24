import pytest
from pulse109.ownership import HandoffOutcomeCommand
from pydantic import ValidationError


def test_handoff_outcome_command_is_human_disposition_only() -> None:
    command = HandoffOutcomeCommand(
        organization_id="org:roads",
        disposition="accepted",
        reason_code="regional_operator_confirmed",
        source_event_id="regional-event-1",
        evidence_refs=["sha256:" + "a" * 64],
    )

    assert command.disposition == "accepted"
    with pytest.raises(ValidationError):
        HandoffOutcomeCommand(
            organization_id="org:roads",
            disposition="accepted",
            reason_code="regional_operator_confirmed",
            source_event_id="regional-event-1",
            evidence_refs=["regional://unverified/path"],
        )
    with pytest.raises(ValidationError):
        HandoffOutcomeCommand(
            organization_id="org:roads",
            disposition="automatic",
            reason_code="auto",
            source_event_id="regional-event-2",
        )
