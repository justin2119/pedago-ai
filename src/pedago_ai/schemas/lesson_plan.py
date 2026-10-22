"""Lesson plan schemas for the APC (Approche Par Competences) Togolese secondary curriculum."""

from enum import StrEnum
from typing import Optional

from pydantic import BaseModel, Field


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
    professor_activity: str = Field(..., description="What the teacher does.")
    student_activity: str = Field(..., description="What the learners do.")
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
    duration_minutes: int = Field(55, ge=10)


class LessonPlanRequest(BaseModel):
    """Input describing the lesson to generate. The teacher block is mandatory before generation."""

    teacher: TeacherInfo = Field(..., description="Teacher administrative information (required).")
    subject: str = Field(..., description="Discipline, e.g. Physique-Chimie.")
    level: str = Field(..., description="Class level, e.g. Seconde C.")
    theme: str
    sub_theme: str | None = None
    duration_minutes: int = Field(55, ge=10)
    competence: str = Field(..., description="Target APC competence.")
    context: str | None = Field(None, description="Retrieved curriculum context.")


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
