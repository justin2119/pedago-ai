"""Export a LessonPlan to a formatted Word document."""

from io import BytesIO

from docx import Document

from pedago_ai.schemas.lesson_plan import LessonPlan


def lesson_plan_to_docx(plan: LessonPlan) -> bytes:
    """Render the lesson plan as a .docx file and return its bytes."""
    document = Document()
    document.add_heading(plan.title, level=0)
    document.add_paragraph(
        f"Matiere : {plan.subject} | Classe : {plan.level} | Duree : {plan.duration_minutes} min"
    )
    theme_line = f"Theme : {plan.theme}" + (f" - {plan.sub_theme}" if plan.sub_theme else "")
    document.add_paragraph(theme_line)
    document.add_paragraph(f"Competence : {plan.competence}")

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
