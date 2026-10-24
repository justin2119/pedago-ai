"""Lesson plan schemas for the APC (Approche Par Competences) Togolese secondary curriculum."""

import re
from collections.abc import Callable, Iterable
from enum import StrEnum
from typing import Any, Optional, TypeVar

from pydantic import BaseModel, Field, field_validator, model_validator

PERIOD_MINUTES = 55
MAX_PERIODS = 6

# Matches "2 h (55 min × 2)", "2 h (55 min x 2)" and "1 h (55 min)".
_HOURS_FORMAT = re.compile(r"^(\d+)\s*h\s*\(\s*55\s*min(?:\s*[x×*]\s*\d+)?\s*\)$", re.IGNORECASE)
# Matches "55 min × 2", "55 min x 2" and "55 min".
_PERIOD_FORMAT = re.compile(r"^55\s*min(?:\s*[x×*]\s*(\d+))?$", re.IGNORECASE)


def parse_duration_minutes(value: Any) -> int:
    """Convert a duration into total minutes.

    Accepts an integer number of minutes (e.g. 110), a numeric string ("110"), or a Togolese
    period label such as "2 h (55 min × 2)", "55 min × 2" or "55 min". Period labels are
    converted to minutes using official 55-minute periods, from 1 to 6 periods.
    """
    if isinstance(value, bool):
        raise ValueError("Durée invalide.")
    if isinstance(value, int):
        return value
    if not isinstance(value, str):
        raise ValueError("Durée invalide.")
    text = value.strip()
    if text.isdigit():
        return int(text)
    hours_match = _HOURS_FORMAT.match(text)
    if hours_match:
        periods = int(hours_match.group(1))
    else:
        period_match = _PERIOD_FORMAT.match(text)
        if not period_match:
            raise ValueError("Durée invalide : utilisez par exemple « 2 h (55 min × 2) ».")
        periods = int(period_match.group(1) or 1)
    if not 1 <= periods <= MAX_PERIODS:
        raise ValueError("La durée doit comprendre entre 1 et 6 périodes de 55 minutes.")
    return periods * PERIOD_MINUTES


class DidacticMoment(StrEnum):
    """The 6 canonical didactic moments of the Togolese APC lesson fiche, in order."""

    PREREQUIS = "prerequis"
    SITUATION_PROBLEME = "situation_probleme"
    RECHERCHE_RESOLUTION = "recherche_resolution"
    MISE_EN_COMMUN = "mise_en_commun"
    INSTITUTIONNALISATION = "institutionnalisation"
    REINVESTISSEMENT = "reinvestissement"


# Kept so existing imports of ActivityKind keep working; the values are the didactic moments.
ActivityKind = DidacticMoment

CANONICAL_MOMENTS: tuple[DidacticMoment, ...] = (
    DidacticMoment.PREREQUIS,
    DidacticMoment.SITUATION_PROBLEME,
    DidacticMoment.RECHERCHE_RESOLUTION,
    DidacticMoment.MISE_EN_COMMUN,
    DidacticMoment.INSTITUTIONNALISATION,
    DidacticMoment.REINVESTISSEMENT,
)

_MomentItem = TypeVar("_MomentItem")


def _normalize_moments(
    items: Iterable[_MomentItem], phase_of: Callable[[_MomentItem], DidacticMoment]
) -> list[_MomentItem]:
    """Sort items into canonical moment order and keep only the first item of each moment.

    Never raises: an out-of-order or duplicated LLM output is repaired instead of failing generation.
    """
    order = {moment: index for index, moment in enumerate(CANONICAL_MOMENTS)}
    seen: set[DidacticMoment] = set()
    kept: list[_MomentItem] = []
    for item in sorted(items, key=lambda it: order[phase_of(it)]):
        phase = phase_of(item)
        if phase in seen:
            continue
        seen.add(phase)
        kept.append(item)
    return kept


class TeacherInfo(BaseModel):
    """Administrative identity of the teacher, required on every fiche de cours in Togo."""

    nom: str = Field(..., description="Nom de famille de l'enseignant.")
    prenom: str = Field(..., description="Prenom de l'enseignant.")
    dre: str = Field(..., description="Direction Regionale de l'Education, e.g. DRE Maritime.")
    iesg: str = Field(..., description="Inspection de l'Enseignement Secondaire General.")
    etablissement: str = Field(..., description="Nom de l'etablissement scolaire, e.g. Lycee de Vogan.")
    telephone: str = Field(..., description="Numero de telephone de l'enseignant.")
    classe: str = Field(..., description="Classe, e.g. Seconde C.")
    serie: Optional[str] = Field(None, description="Serie, if applicable.")


class Objective(BaseModel):
    """Operational pedagogical objective (OPO) for a lesson."""

    description: str = Field(..., description="Observable, measurable action statement.")
    domain: str = Field(..., description="Cognitive, affective or psychomotor domain.")
    bloom_level: str | None = Field(None, description="Bloom taxonomy level, if used.")


class CapaciteContenu(BaseModel):
    """One row of the Capacites / Contenus matrix: an operational capacity and its notional contents."""

    capacite: str = Field(..., description="Capacite operationnelle observable visee.")
    contenus: list[str] = Field(default_factory=list, description="Contenus notionnels associes.")


class TimingSegment(BaseModel):
    """A timed didactic moment of the lesson."""

    phase: DidacticMoment
    duration_minutes: int = Field(..., ge=1)
    description: str | None = None


class Activity(BaseModel):
    """A professor or student activity within a didactic moment."""

    phase: DidacticMoment
    professor_activity: str = Field(
        "",
        description="What the teacher does during this moment. Required in every activity; never omit it.",
    )
    student_activity: str = Field(
        "",
        description="What the learners do during this moment. Required in every activity; never omit it.",
    )
    duration_minutes: int = Field(..., ge=1)
    materials: list[str] = Field(default_factory=list)


class EvaluationItem(BaseModel):
    """An evaluation question or criterion tied to the objectives."""

    question: str
    expected_answer: str
    linked_objective: str | None = None
    points: float | None = Field(None, ge=0)


class LessonPlanHeader(BaseModel):
    """Official header of the fiche de cours: teacher administration plus lesson identification."""

    teacher: TeacherInfo
    discipline: str = Field(..., description="Discipline / matiere, e.g. Physique-Chimie.")
    theme: str
    sub_theme: str | None = None
    competence: str = Field(..., description="Target APC competence.")
    duration_minutes: int = Field(55, ge=10, description="Total minutes; a multiple of 55 (1 to 6 periods).")

    @field_validator("duration_minutes", mode="before")
    @classmethod
    def _check_duration(cls, value: Any) -> int:
        return parse_duration_minutes(value)


class LessonPlanRequest(BaseModel):
    """Input describing the lesson to generate. The teacher block is mandatory before generation."""

    teacher: TeacherInfo = Field(..., description="Teacher administrative information (required).")
    subject: str = Field(..., description="Discipline, e.g. Physique-Chimie.")
    level: str = Field(..., description="Class level, e.g. Seconde C.")
    theme: str
    sub_theme: str | None = None
    duration_minutes: int = Field(55, ge=10, description="Total minutes; a multiple of 55 (1 to 6 periods).")
    competence: str = Field(..., description="Target APC competence.")
    context: str | None = Field(None, description="Retrieved curriculum context.")

    @field_validator("duration_minutes", mode="before")
    @classmethod
    def _check_duration(cls, value: Any) -> int:
        return parse_duration_minutes(value)


class LessonPlan(BaseModel):
    """Complete APC lesson plan following the official Togolese fiche structure."""

    title: str
    teacher: TeacherInfo | None = None
    # Official header metadata (filled from the teacher block when known).
    dre: str = ""
    etablissement: str = ""
    fiche_numero: int = 1
    semaine: str = ""
    annee_scolaire: str = ""
    subject: str
    level: str
    theme: str
    sub_theme: str | None = None
    competence: str
    duration_minutes: int
    objectives: list[Objective] = Field(..., min_length=1)
    prerequisites: list[str] = Field(default_factory=list)
    materials: list[str] = Field(default_factory=list)
    # Matrix of operational capacities and the notional contents they rely on.
    capacites_contenus: list[CapaciteContenu] = Field(default_factory=list)
    # Expected to hold the 6 canonical moments in order; repaired (not rejected) when they do not.
    timing: list[TimingSegment] = Field(..., min_length=1)
    activities: list[Activity] = Field(..., min_length=1)
    evaluation: list[EvaluationItem] = Field(default_factory=list)
    # Final consolidation block.
    essentiel_a_retenir: str = ""
    exercices_application: list[dict[str, Any]] = Field(default_factory=list)
    devoir_maison: str = ""
    notes: str | None = None

    @field_validator("fiche_numero", mode="before")
    @classmethod
    def _coerce_fiche_numero(cls, value: Any) -> int:
        """Accept a missing (null) or non-numeric fiche number and fall back to 1.

        The frontend sends null when the teacher leaves the fiche number empty, which used to
        fail validation with HTTP 422 on POST /api/v1/export/docx.
        """
        if value is None or isinstance(value, bool):
            return 1
        try:
            number = int(value)
        except (TypeError, ValueError):
            return 1
        return number if number >= 1 else 1

    @field_validator("dre", "etablissement", "semaine", "annee_scolaire", mode="before")
    @classmethod
    def _coerce_header_text(cls, value: Any) -> str:
        """Treat a null header field as an empty string instead of rejecting the plan."""
        return "" if value is None else value

    @model_validator(mode="after")
    def _normalize_canonical_moments(self) -> "LessonPlan":
        """Repair timing and activities to the canonical moment order instead of failing.

        Items are sorted into the order prerequis, situation_probleme, recherche_resolution,
        mise_en_commun, institutionnalisation, reinvestissement, and duplicated moments keep
        their first occurrence. A missing moment is tolerated: the plan is kept as produced so
        generation does not fail after the output retries.
        """
        self.timing = _normalize_moments(self.timing, lambda segment: segment.phase)
        self.activities = _normalize_moments(self.activities, lambda activity: activity.phase)
        return self
