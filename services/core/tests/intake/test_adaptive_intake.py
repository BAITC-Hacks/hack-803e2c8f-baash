from __future__ import annotations

import pytest
from pulse109.intake import (
    AdaptiveIntake,
    AppealFacts,
    FieldState,
    IntakePolicy,
    RequiredField,
)


@pytest.fixture
def policy() -> IntakePolicy:
    return IntakePolicy(
        service_id="water_supply",
        topic_id="water_outage",
        version="v1",
        approved=True,
        required_fields=(
            RequiredField(
                "location",
                {"kk": "Мекенжайды көрсетіңіз.", "ru": "Укажите адрес."},
            ),
            RequiredField(
                "started_at",
                {"kk": "Қашан басталғанын көрсетіңіз.", "ru": "Укажите, когда это началось."},
            ),
            RequiredField(
                "scope",
                {"kk": "Қай аумақта су жоқ?", "ru": "Где именно нет воды?"},  # noqa: RUF001
            ),
        ),
    )


def test_selects_only_unknown_and_missing_requirements_in_policy_order(
    policy: IntakePolicy,
) -> None:
    plan = AdaptiveIntake().plan(
        policy=policy,
        facts=AppealFacts({"location": FieldState.KNOWN, "scope": FieldState.MISSING}),
        locale="ru",
    )

    assert plan.complete is False
    assert plan.field_states == {
        "location": FieldState.KNOWN,
        "started_at": FieldState.UNKNOWN,
        "scope": FieldState.MISSING,
    }
    assert plan.questions == (
        "Укажите, когда это началось.",
        "Где именно нет воды?",
    )
    assert not hasattr(plan, "values")


def test_known_required_facts_produce_complete_plan_without_questions(
    policy: IntakePolicy,
) -> None:
    plan = AdaptiveIntake().plan(
        policy=policy,
        facts=AppealFacts(
            {
                "location": "known",
                "started_at": "known",
                "scope": "known",
            }
        ),
        locale="kk",
    )

    assert plan.complete is True
    assert plan.questions == ()


def test_question_limit_is_bounded_but_completeness_remains_accurate(
    policy: IntakePolicy,
) -> None:
    plan = AdaptiveIntake().plan(policy=policy, facts=AppealFacts({}), locale="kk", max_questions=1)

    assert plan.complete is False
    assert plan.questions == ("Мекенжайды көрсетіңіз.",)
    assert len(plan.questions) <= 1


@pytest.mark.parametrize(
    ("policy_override", "locale", "limit"),
    [
        (False, "kk", 5),
        (True, "en", 5),
        (True, "ru", -1),
    ],
)
def test_rejects_unapproved_or_unsupported_plan_inputs(
    policy: IntakePolicy, policy_override: bool, locale: str, limit: int
) -> None:
    unapproved = IntakePolicy(
        service_id=policy.service_id,
        topic_id=policy.topic_id,
        version=policy.version,
        approved=policy_override,
        required_fields=policy.required_fields,
    )
    with pytest.raises(ValueError):
        AdaptiveIntake().plan(
            policy=unapproved, facts=AppealFacts({}), locale=locale, max_questions=limit
        )


def test_policy_and_fact_inputs_are_immutable() -> None:
    questions = {"kk": "Сұрақ", "ru": "Вопрос"}
    field = RequiredField("location", questions)
    questions["ru"] = "changed"
    facts_source = {"location": "known"}
    facts = AppealFacts(facts_source)
    facts_source["location"] = "missing"

    assert field.questions["ru"] == "Вопрос"
    assert facts.states["location"] is FieldState.KNOWN
    with pytest.raises(TypeError):
        field.questions["ru"] = "changed"  # type: ignore[index]


def test_rejects_duplicate_policy_fields() -> None:
    field = RequiredField("location", {"kk": "Мекенжай", "ru": "Адрес"})
    with pytest.raises(ValueError, match="unique"):
        IntakePolicy("service", "topic", "v1", True, (field, field))


def test_conditional_evidence_is_asked_only_after_prerequisite_state() -> None:
    conditional = IntakePolicy(
        service_id="roads",
        topic_id="road_damage",
        version="synthetic-conditional-v1",
        approved=True,
        required_fields=(
            RequiredField("location", {"kk": "Қайда?", "ru": "Где?"}),
            RequiredField(
                "photo",
                {"kk": "Фото қосыңыз.", "ru": "Добавьте фото."},
                when_states={"location": FieldState.KNOWN},
                evidence_type="photo",
            ),
        ),
    )
    before_location = AdaptiveIntake().plan(policy=conditional, facts=AppealFacts({}), locale="ru")
    assert before_location.questions == ("Где?",)
    assert before_location.required_evidence_types == ()
    assert before_location.complete is False

    after_location = AdaptiveIntake().plan(
        policy=conditional,
        facts=AppealFacts({"location": "known", "photo": "missing"}),
        locale="ru",
    )
    assert after_location.questions == ("Добавьте фото.",)
    assert after_location.question_items[0].field_id == "photo"
    assert after_location.question_items[0].evidence_type == "photo"
    assert after_location.required_evidence_types == ("photo",)
    assert after_location.complete is False


def test_conditional_policy_rejects_unknown_or_cyclic_dependencies() -> None:
    first = RequiredField(
        "photo", {"kk": "Фото", "ru": "Фото"}, when_states={"location": FieldState.KNOWN}
    )
    with pytest.raises(ValueError, match="earlier unconditional"):
        IntakePolicy("roads", "road_damage", "v1", True, (first,))
    with pytest.raises(ValueError, match="earlier unconditional"):
        IntakePolicy(
            "roads",
            "road_damage",
            "v1",
            True,
            (
                first,
                RequiredField("location", {"kk": "Қайда?", "ru": "Где?"}),
            ),
        )
