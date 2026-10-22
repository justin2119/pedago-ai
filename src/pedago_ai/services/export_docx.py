"""Export a LessonPlan to a formatted Word document."""

from io import BytesIO

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH

from pedago_ai.schemas.lesson_plan import LessonPlan, TeacherInfo


def _add_header_table(document: Document, plan: LessonPlan) -> None:
    """Add the official administrative header table (teacher identity and lesson identification)."""
    teacher: TeacherInfo | None = plan.teacher
    rows = [
        ("DRE", teacher.dre if teacher else ""),
        ("IESG", teacher.iesg if teacher else ""),
        ("Etablissement", teacher.etablissement if teacher else ""),
        ("Nom et prenom", f"{teacher.nom} {teacher.prenom}" if teacher else ""),
        ("Contact / Numero", teacher.telephone if teacher else ""),
        ("Classe", f"{teacher.classe}" + (f" - Serie {teacher.serie}" if teacher and teacher.serie else "") if teacher else plan.level),
        ("Discipline / Matiere", plan.subject),
        ("Theme", plan.theme + (f" - {plan.sub_theme}" if plan.sub_theme else "")),
        ("Competence", plan.competence),
        ("Duree", f"{plan.duration_minutes} min"),
    ]
    table = document.add_table(rows=0, cols=2)
    table.style = "Table Grid"
    for label, value in rows:
        cells = table.add_row().cells
        cells[0].text = label
        cells[1].text = value
        for run in cells[0].paragraphs[0].runs:
            run.bold = True


def lesson_plan_to_docx(plan: LessonPlan) -> bytes:
    """Render the lesson plan as a .docx file and return its bytes."""
    document = Document()
    republic = document.add_paragraph("REPUBLIQUE TOGOLAISE")
    republic.alignment = WD_ALIGN_PARAGRAPH.CENTER
    ministry = document.add_paragraph("Ministere des Enseignements Primaire, Secondaire, Technique et de la Formation Professionnelle")
    ministry.alignment = WD_ALIGN_PARAGRAPH.CENTER
    document.add_heading("FICHE DE COURS", level=0).alignment = WD_ALIGN_PARAGRAPH.CENTER
    _add_header_table(document, plan)

    document.add_heading(plan.title, level=1)

    document.add_heading("Objectifs pedagogiques operationnels", level=1)
    for objective in plan.objectives:
        document.add_paragraph(objective.description, style="List Bullet")

    if plan.prerequisites:
        document.add_heading("Prerequis", level=1)
        for item in plan.prerequisites:
            document.add_paragraph(item, style="List Bullet")

    if plan.materials:
        document.add_heading("Materiel", level=1)
        for item in plan.materials:
            document.add_paragraph(item, style="List Bullet")

    document.add_heading("Deroulement", level=1)
    table = document.add_table(rows=1, cols=4)
    table.style = "Table Grid"
    headers = ["Phase", "Duree", "Activite du professeur", "Activite des eleves"]
    for cell, header in zip(table.rows[0].cells, headers, strict=True):
        cell.text = header
    for activity in plan.activities:
        row = table.add_row().cells
        row[0].text = activity.phase.value
        row[1].text = f"{activity.duration_minutes} min"
        row[2].text = activity.professor_activity
        row[3].text = activity.student_activity

    if plan.evaluation:
        document.add_heading("Evaluation", level=1)
        for item in plan.evaluation:
            document.add_paragraph(f"{item.question} : {item.expected_answer}", style="List Number")

    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()
