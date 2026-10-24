"""Lesson plan schemas for the APC (Approche Par Competences) Togolese secondary curriculum."""

import re
from enum import StrEnum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

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


class ActivityKind(StrEnum):
    """Phase type of a classroom activity."""

    MOTIVATION = "motivation"
    PREREQUISITES = "prerequisites"
    CONSTRUCTION = "construction"
    APPLICATION = "application"
    SYNTHESIS = "synthesis"
    EVALUATION = "evaluation"


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


class TimingSegment(BaseModel):
    """A timed phase of the lesson."""

    phase: ActivityKind
    duration_minutes: int = Field(..., ge=1)
    description: str | None = None


class Activity(BaseModel):
    """A professor or student activity within a lesson phase."""

    phase: ActivityKind
    professor_activity: str = Field(
        "",
        description="What the teacher does during this phase. Required in every activity; never omit it.",
    )
    student_activity: str = Field(
        "",
        description="What the learners do during this phase. Required in every activity; never omit it.",
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
    """Complete APC lesson plan."""

    title: str
    teacher: TeacherInfo | None = None
    subject: str
    level: str
    theme: str
    sub_theme: str | None = None
    competence: str
    duration_minutes: int
    objectives: list[Objective] = Field(..., min_length=1)
    prerequisites: list[str] = Field(default_factory=list)
    materials: list[str] = Field(default_factory=list)
    timing: list[TimingSegment] = Field(..., min_length=1)
    activities: list[Activity] = Field(..., min_length=1)
    evaluation: list[EvaluationItem] = Field(default_factory=list)
    notes: str | None = None
