"""Unit tests for LessonPlan: didactic moment normalization, header coercion and duration parsing."""

import pytest
from pydantic import ValidationError

from pedago_ai.schemas.lesson_plan import (
    CANONICAL_MOMENTS,
    Activity,
    DidacticMoment,
    LessonPlan,
    Objective,
    TimingSegment,
    parse_duration_minutes,
)


def _timing(moments, duration=10):
    return [TimingSegment(phase=m, duration_minutes=duration) for m in moments]


def _activities(moments, duration=10):
    return [
        Activity(
            phase=m,
            professor_activity=f"prof {m.value}",
            student_activity=f"eleves {m.value}",
            duration_minutes=duration,
        )
        for m in moments
    ]


def _plan(**overrides):
    data = {
        "title": "Titre de la lecon",
        "subject": "Physique-Chimie",
        "level": "Seconde C",
        "theme": "Mecanique",
        "competence": "Resoudre un probleme de mouvement",
        "duration_minutes": 55,
        "objectives": [Objective(description="Calculer une vitesse moyenne", domain="cognitif")],
        "timing": _timing(CANONICAL_MOMENTS),
        "activities": _activities(CANONICAL_MOMENTS),
    }
    data.update(overrides)
    return LessonPlan(**data)


def test_canonical_moments_are_the_six_expected_in_order():
    assert list(CANONICAL_MOMENTS) == [
        DidacticMoment.PREREQUIS,
        DidacticMoment.SITUATION_PROBLEME,
        DidacticMoment.RECHERCHE_RESOLUTION,
        DidacticMoment.MISE_EN_COMMUN,
        DidacticMoment.INSTITUTIONNALISATION,
        DidacticMoment.REINVESTISSEMENT,
    ]


def test_timing_already_ordered_is_kept_unchanged():
    plan = _plan()
    assert [s.phase for s in plan.timing] == list(CANONICAL_MOMENTS)


def test_timing_out_of_order_is_sorted_into_canonical_order():
    shuffled = list(reversed(CANONICAL_MOMENTS))
    plan = _plan(timing=_timing(shuffled))
    assert [s.phase for s in plan.timing] == list(CANONICAL_MOMENTS)


def test_activities_out_of_order_are_sorted_into_canonical_order():
    shuffled = [CANONICAL_MOMENTS[i] for i in (3, 0, 5, 1, 4, 2)]
    plan = _plan(activities=_activities(shuffled))
    assert [a.phase for a in plan.activities] == list(CANONICAL_MOMENTS)
    # Each activity keeps its own content after reordering.
    assert plan.activities[0].professor_activity == "prof prerequis"


def test_duplicate_timing_keeps_first_occurrence_only():
    timing = [
        TimingSegment(phase=DidacticMoment.PREREQUIS, duration_minutes=5),
        TimingSegment(phase=DidacticMoment.PREREQUIS, duration_minutes=20),
        *_timing(CANONICAL_MOMENTS[1:]),
    ]
    plan = _plan(timing=timing)
    assert len(plan.timing) == 6
    assert [s.phase for s in plan.timing] == list(CANONICAL_MOMENTS)
    assert plan.timing[0].duration_minutes == 5


def test_duplicate_activities_keep_first_occurrence_only():
    activities = [
        *_activities([DidacticMoment.MISE_EN_COMMUN]),
        *_activities([DidacticMoment.MISE_EN_COMMUN], duration=99),
        *_activities(CANONICAL_MOMENTS[:3] + CANONICAL_MOMENTS[4:]),
    ]
    plan = _plan(activities=activities)
    phases = [a.phase for a in plan.activities]
    assert phases.count(DidacticMoment.MISE_EN_COMMUN) == 1
    assert len(plan.activities) == 6
    mise = next(a for a in plan.activities if a.phase == DidacticMoment.MISE_EN_COMMUN)
    assert mise.duration_minutes == 10


def test_missing_moments_do_not_crash_and_keep_sorted_subset():
    present = [DidacticMoment.REINVESTISSEMENT, DidacticMoment.PREREQUIS]
    plan = _plan(timing=_timing(present), activities=_activities(present))
    assert [s.phase for s in plan.timing] == [DidacticMoment.PREREQUIS, DidacticMoment.REINVESTISSEMENT]
    assert [a.phase for a in plan.activities] == [DidacticMoment.PREREQUIS, DidacticMoment.REINVESTISSEMENT]


def test_single_moment_does_not_crash():
    plan = _plan(
        timing=_timing([DidacticMoment.SITUATION_PROBLEME]),
        activities=_activities([DidacticMoment.SITUATION_PROBLEME]),
    )
    assert len(plan.timing) == 1
    assert len(plan.activities) == 1


def test_empty_timing_is_rejected():
    with pytest.raises(ValidationError):
        _plan(timing=[])


def test_empty_activities_are_rejected():
    with pytest.raises(ValidationError):
        _plan(activities=[])


def test_moment_strings_are_coerced_to_enum():
    timing = [{"phase": "mise_en_commun", "duration_minutes": 10}, {"phase": "prerequis", "duration_minutes": 5}]
    plan = _plan(timing=timing)
    assert [s.phase for s in plan.timing] == [DidacticMoment.PREREQUIS, DidacticMoment.MISE_EN_COMMUN]


@pytest.mark.parametrize("value", [None, "null"])
def test_null_or_non_numeric_fiche_numero_becomes_one(value):
    assert _plan(fiche_numero=value).fiche_numero == 1


def test_fiche_numero_defaults_to_one_when_omitted():
    assert _plan().fiche_numero == 1


@pytest.mark.parametrize(("value", "expected"), [("3", 3), (4, 4), ("0", 1), (-2, 1), (True, 1)])
def test_fiche_numero_coercion_edge_cases(value, expected):
    assert _plan(fiche_numero=value).fiche_numero == expected


@pytest.mark.parametrize("field", ["dre", "etablissement", "semaine", "annee_scolaire"])
def test_null_header_text_becomes_empty_string(field):
    plan = _plan(**{field: None})
    assert getattr(plan, field) == ""


def test_header_text_fields_default_to_empty_string_when_omitted():
    plan = _plan()
    assert plan.dre == ""
    assert plan.etablissement == ""
    assert plan.semaine == ""
    assert plan.annee_scolaire == ""


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (110, 110),
        ("110", 110),
        ("55 min", 55),
        ("55 min × 2", 110),
        ("1 h (55 min)", 55),
        ("2 h (55 min × 2)", 110),
        ("6 h (55 min x 6)", 330),
    ],
)
def test_parse_duration_minutes_accepts_known_formats(value, expected):
    assert parse_duration_minutes(value) == expected


@pytest.mark.parametrize("value", ["7 h (55 min × 7)", "0 h (55 min)", "abc", True, None])
def test_parse_duration_minutes_rejects_invalid_values(value):
    with pytest.raises(ValueError):
        parse_duration_minutes(value)
