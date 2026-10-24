"""Generator agent: produces an APC lesson plan using PydanticAI and an OpenAI-compatible model."""

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from pedago_ai.config import get_settings
from pedago_ai.schemas.lesson_plan import PERIOD_MINUTES, LessonPlan, LessonPlanRequest

OUTPUT_RETRIES = 3

# Canonical APC fiche (Physique Seconde, APC Togo) used as the reference form and content model.
# Used in the fallback prompt when the corpus returns no extract. It is a template, not a source:
# it must never be presented as a retrieved reference.
APC_FICHE_TEMPLATE = (
    "MODELE CANONIQUE DE FICHE APC (Physique Seconde, APC Togo). Reproduis cette forme et cette "
    "logique. Ne cite aucune source a partir de ce modele.\n"
    "\n"
    "1. EN-TETE\n"
    "- Infos administratives : DRE, Etablissement, Professeur, Annee scolaire, Classe, Discipline, "
    "Fiche N, Semaine, Duree (multiple de 55 min : 55, 110, 165, 220, 275 ou 330 minutes).\n"
    "- Elements pedagogiques : Competence terminale, Theme, Lecon, Supports didactiques / materiels, "
    "Prerequis.\n"
    "\n"
    "2. MATRICE CAPACITES / CONTENUS\n"
    "- Pour chaque capacite operationnelle observable, liste les contenus notionnels associes "
    "(notions, lois, formules, unites). Une ligne par capacite.\n"
    "\n"
    "3. GRILLE DIDACTIQUE : exactement 6 moments, dans cet ordre, avec ces identifiants :\n"
    "- prerequis : 1. Mobilisation des prerequis. Enseignant : pose des questions de rappel, "
    "oriente. Eleves : repondent, rappellent leurs acquis.\n"
    "- situation_probleme : 2. Situation-probleme / presentation de la situation d'apprentissage. "
    "Enseignant : presente la situation contextualisee et pose la question-probleme. Eleves : "
    "observent, lisent, reformulent la consigne, formulent des hypotheses.\n"
    "- recherche_resolution : 3. Recherche / resolution. Enseignant : organise les groupes, "
    "distribue le materiel, guide sans donner la reponse. Eleves : experimentent ou calculent, "
    "echangent avec leurs pairs, prennent note.\n"
    "- mise_en_commun : 4. Mise en commun / discussion. Enseignant : anime, fait comparer les "
    "resultats, valide ou corrige. Eleves : presentent leurs resultats, argumentent.\n"
    "- institutionnalisation : 5. Institutionnalisation / trace ecrite (synthese). Enseignant : "
    "institutionnalise les notions cles. Eleves : prennent note de la synthese.\n"
    "- reinvestissement : 6. Reinvestissement / evaluation formative. Enseignant : propose des "
    "exercices d'application et l'evaluation. Eleves : resolvent individuellement.\n"
    "\n"
    "4. CONSOLIDATION FINALE\n"
    "- essentiel_a_retenir : definitions, lois, formules mathematiques et unites.\n"
    "- exercices_application : exercices d'application immediats, chacun avec un enonce et une "
    "correction.\n"
    "- devoir_maison : un exercice de maison.\n"
)

# Priority rule for the corpus. Real fiches and guides ingested in the corpus are the reference.
CORPUS_PRIORITY_RULE = (
    "REGLE DE PRIORITE (absolue) : les extraits 'Contexte curriculaire retrouve' proviennent "
    "de fiches reelles et de guides d'execution ingeres dans le corpus. Ils sont la reference "
    "prioritaire, avant toute connaissance generale ou gabarit.\n"
    "- Forme : reprends le canevas de ces fiches (sections, intitules des phases, decoupage "
    "des phases, formulation des activites professeur et eleve, interactions prof/eleve, "
    "timing, rubriques d'evaluation).\n"
    "- Fond : reprends leur contenu scientifique, la situation-probleme, les activites "
    "d'apprentissage et les notions, en les adaptant a la matiere, au niveau, au theme et a "
    "la competence demandes.\n"
    "- Ne contredis pas ces extraits. Ne cite une source que si elle figure dans les extraits.\n"
    "- Si un point n'est couvert par aucun extrait, reste prudent et n'invente ni formule, ni "
    "fait, ni reference."
)

SYSTEM_PROMPT = (
    "You are an expert pedagogue for Togolese secondary schools following the APC "
    "(Approche Par Competences) framework. Produce a complete lesson plan with operational "
    "pedagogical objectives, a capacities-to-contents matrix, timed didactic moments, professor "
    "and student activities, evaluation items and a final consolidation block. "
    "The request contains the teacher's administrative information (teacher block); keep it "
    "unchanged and do not invent any teacher, DRE, IESG or school details. "
    "STRICT STRUCTURE: the timing and the activities must each contain the 6 canonical "
    "didactic moments, in this order. The field phase (in timing and in activities) must be "
    "exactly one of these literal lowercase values, with no accents, spaces, numbering or "
    "translation: prerequis, situation_probleme, recherche_resolution, mise_en_commun, "
    "institutionnalisation, reinvestissement. Never use any other value for phase. Do not add, "
    "remove, rename or reorder them. Each activity must describe the teacher role AND the learners "
    "role for its moment (professor_activity and student_activity, both non-empty). "
    "Capacities matrix: capacites_contenus lists each operational capacity with its notional "
    "contents. "
    "Consolidation: essentiel_a_retenir (definitions, laws, formulas and units), "
    "exercices_application (each item with an enonce and a correction), devoir_maison (one "
    "homework exercise). "
    "Canonical form: the APC Physique Seconde fiche model given in the user message is the "
    "reference for form. When the user message contains real corpus extracts, they are the "
    "absolute reference for form and content, with priority over general knowledge and over the "
    "canonical model. When no extract is present, follow the canonical model and do not claim or "
    "cite any source, guide or fiche. "
    "Togolese secondary lessons are measured in official periods of 55 minutes. The total "
    "duration is always 1 to 6 periods (55, 110, 165, 220, 275 or 330 minutes). The sum of the "
    "timing durations and the sum of the activity durations must each equal the total minutes "
    "exactly. Give recherche_resolution and reinvestissement the larger share in multi-period "
    "lessons, keep prerequis and institutionnalisation short. Each duration_minutes must be a "
    "positive integer. Keep the scientific content rigorous; do not invent facts or formulas."
)


def build_model() -> OpenAIChatModel:
    """Create the OpenAI-compatible chat model from settings."""
    settings = get_settings()
    provider = OpenAIProvider(base_url=settings.model_base_url, api_key=settings.model_api_key)
    return OpenAIChatModel(settings.model_name, provider=provider)


def build_generator() -> Agent[None, LessonPlan]:
    """Create the PydanticAI agent that returns a structured LessonPlan."""
    return Agent(
        build_model(),
        output_type=LessonPlan,
        system_prompt=SYSTEM_PROMPT,
        retries={"output": OUTPUT_RETRIES},
    )


def period_hint(duration_minutes: int) -> str:
    """Describe the 55-minute period breakdown of a lesson duration for the model."""
    periods = max(1, round(duration_minutes / PERIOD_MINUTES))
    hours = duration_minutes // 60
    minutes = duration_minutes % 60
    return (
        f"Duree totale : {duration_minutes} minutes, soit {periods} periode(s) de {PERIOD_MINUTES} minutes "
        f"({periods} x {PERIOD_MINUTES} min, affichee comme {hours} h {minutes:02d} min). "
        "Repartis les 6 moments et les activites sur ces periodes, sans depasser ni laisser de temps vide."
    )


def build_prompt(request: LessonPlanRequest, feedback: list[str]) -> str:
    """Assemble the generation prompt.

    With corpus extracts: the priority rule and the extracts come first, then the canonical model.
    Without extracts: the canonical model is used as the fallback and no source is invented.
    """
    prompt = request.model_dump_json(indent=2)
    prompt += "\n\n" + period_hint(request.duration_minutes)
    prompt += (
        "\n\nRappel : dans timing et dans activities, le champ phase doit valoir exactement "
        "l'une de ces valeurs : prerequis, situation_probleme, recherche_resolution, "
        "mise_en_commun, institutionnalisation, reinvestissement (6 moments, dans cet ordre)."
    )
    if request.context and request.context.strip():
        prompt += (
            "\n\n" + CORPUS_PRIORITY_RULE
            + "\n\nContexte curriculaire retrouve (fiches reelles et guides ingeres) :\n"
            + request.context
            + "\n\n" + APC_FICHE_TEMPLATE
        )
    else:
        prompt += (
            "\n\nAucun contexte curriculaire retrouve dans le corpus : utilise le modele canonique "
            "ci-dessous et n'invente aucune reference ni source.\n\n" + APC_FICHE_TEMPLATE
        )
    if feedback:
        prompt += "\n\nFix these issues from the previous attempt:\n- " + "\n- ".join(feedback)
    return prompt


async def generate_lesson_plan(request: LessonPlanRequest, feedback: list[str]) -> LessonPlan:
    """Generate a lesson plan for the request, incorporating validator feedback if any."""
    result = await build_generator().run(build_prompt(request, feedback))
    plan = result.output
    # The teacher's administrative block comes from the request, never from the model output.
    return plan.model_copy(
        update={
            "teacher": request.teacher,
            "dre": request.teacher.dre,
            "etablissement": request.teacher.etablissement,
        }
    )
