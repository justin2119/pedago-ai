"""Generator agent: produces an APC lesson plan using PydanticAI and an OpenAI-compatible model."""

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from pedago_ai.config import get_settings
from pedago_ai.schemas.lesson_plan import PERIOD_MINUTES, LessonPlan, LessonPlanRequest

OUTPUT_RETRIES = 3

# Canonical APC fiche (Physique 2nde S, APC Togo) used as the reference form and content model.
# Used in the fallback prompt when the corpus returns no extract. It is a template, not a source:
# it must never be presented as a retrieved reference.
APC_FICHE_TEMPLATE = (
    "MODÈLE CANONIQUE DE FICHE APC (Physique 2nde S, APC Togo). Reproduis cette forme et cette "
    "logique. Ne cite aucune source à partir de ce modèle.\n"
    "\n"
    "1. EN-TÊTE\n"
    "- Infos administratives : DRE, Établissement, Professeur, Année scolaire, Classe, Discipline, "
    "Fiche N°, Semaine, Durée (multiple de 55 min : 55, 110, 165, 220, 275 ou 330 minutes).\n"
    "- Éléments pédagogiques : Compétence terminale, Thème, Leçon, Supports didactiques / matériels, "
    "Prérequis.\n"
    "\n"
    "2. MATRICE CAPACITÉS / CONTENUS\n"
    "- Articule systématiquement chaque capacité opérationnelle visée (verbe observable) avec les "
    "contenus notionnels associés (notions, lois, formules, unités).\n"
    "\n"
    "3. GRILLE DIDACTIQUE (ACTIVITÉS), séquençage APC strict :\n"
    "- Mobilisation des prérequis\n"
    "- Situation-problème / présentation de la situation d'apprentissage\n"
    "- Organisation du travail / recherche et résolution\n"
    "- Mise en commun / discussion\n"
    "- Institutionnalisation / trace écrite (synthèse)\n"
    "- Réinvestissement / évaluation formative\n"
    "Posture d'action pour chaque moment :\n"
    "- Enseignant : pose des questions, organise les groupes, oriente, institutionnalise les notions clés.\n"
    "- Élève : observe, expérimente ou calcule, échange avec ses pairs, formule des hypothèses, "
    "prend note.\n"
    "\n"
    "4. CONSOLIDATION FINALE\n"
    "- Essentiel à retenir : définitions, lois, formules mathématiques et unités.\n"
    "- Exercices d'application immédiats, avec éléments de correction.\n"
    "- Exercice de maison.\n"
)

# Priority rule for the corpus. Real fiches and guides ingested in the corpus are the reference.
CORPUS_PRIORITY_RULE = (
    "RÈGLE DE PRIORITÉ (absolue) : les extraits 'Contexte curriculaire retrouvé' proviennent "
    "de fiches réelles et de guides d'exécution ingérés dans le corpus. Ils sont la référence "
    "prioritaire, avant toute connaissance générale ou gabarit.\n"
    "- Forme : reprends le canevas de ces fiches (sections, intitulés des phases, découpage "
    "des phases, formulation des activités professeur et élève, interactions prof/élève, "
    "timing, rubriques d'évaluation).\n"
    "- Fond : reprends leur contenu scientifique, la situation-problème, les activités "
    "d'apprentissage et les notions, en les adaptant à la matière, au niveau, au thème et à "
    "la compétence demandés.\n"
    "- Ne contredis pas ces extraits. Ne cite une source que si elle figure dans les extraits.\n"
    "- Si un point n'est couvert par aucun extrait, reste prudent et n'invente ni formule, ni "
    "fait, ni référence."
)

SYSTEM_PROMPT = (
    "You are an expert pedagogue for Togolese secondary schools following the APC "
    "(Approche Par Competences) framework. Produce a complete lesson plan with operational "
    "pedagogical objectives, timed phases, professor and student activities, and evaluation "
    "items. The request contains the teacher's administrative information (teacher block); "
    "keep it unchanged and do not invent any teacher, DRE, IESG or school details. "
    "Canonical form: the lesson follows the APC Physique 2nde S fiche model given in the user "
    "message: header (administrative and pedagogical elements), capacities-to-contents matrix, "
    "didactic grid with the strict APC sequence (prerequisites, situation-problem, work "
    "organisation and resolution, discussion, institutionalisation and written trace, "
    "reinvestment and formative evaluation) with teacher and student postures, then final "
    "consolidation (key points with definitions, laws, formulas and units; application exercises "
    "with corrections; homework). "
    "When the user message contains real corpus extracts, they are the absolute reference for "
    "form and content, with priority over general knowledge and over the canonical model. "
    "When no extract is present, follow the canonical model and do not claim or cite any "
    "source, guide or fiche. "
    "Every entry in activities MUST include a non-empty professor_activity (what the teacher "
    "does) and a non-empty student_activity (what the learners do), in addition to phase, "
    "duration_minutes and materials. Never omit these two fields. "
    "Togolese secondary lessons are measured in official periods of 55 minutes. The total "
    "duration is always 1 to 6 periods (55, 110, 165, 220, 275 or 330 minutes). Distribute the "
    "timing and activities so that the phase durations add up exactly to the total duration, "
    "and so that each period is accounted for: the sum of timing durations must equal the total "
    "minutes, and the sum of activity durations must equal the total minutes. Give longer phases "
    "(construction, application) the larger share in multi-period lessons, keep a short motivation "
    "and synthesis, and reserve the final period time for evaluation when there are several periods. "
    "Each phase's duration_minutes must be a positive integer. Keep the scientific content "
    "rigorous and consistent with the curriculum; do not invent facts or formulas."
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
        f"Durée totale : {duration_minutes} minutes, soit {periods} période(s) de {PERIOD_MINUTES} minutes "
        f"({periods} x {PERIOD_MINUTES} min, affichée comme {hours} h {minutes:02d} min). "
        "Répartissez les phases et les activités sur ces périodes, sans dépasser ni laisser de temps vide."
    )


def build_prompt(request: LessonPlanRequest, feedback: list[str]) -> str:
    """Assemble the generation prompt.

    With corpus extracts: the priority rule and the extracts come first, then the canonical model.
    Without extracts: the canonical model is used as the fallback and no source is invented.
    """
    prompt = request.model_dump_json(indent=2)
    prompt += "\n\n" + period_hint(request.duration_minutes)
    if request.context and request.context.strip():
        prompt += (
            "\n\n" + CORPUS_PRIORITY_RULE
            + "\n\nContexte curriculaire retrouvé (fiches réelles et guides ingérés) :\n"
            + request.context
            + "\n\n" + APC_FICHE_TEMPLATE
        )
    else:
        prompt += (
            "\n\nAucun contexte curriculaire retrouvé dans le corpus : utilise le modèle canonique "
            "ci-dessous et n'invente aucune référence ni source.\n\n" + APC_FICHE_TEMPLATE
        )
    if feedback:
        prompt += "\n\nFix these issues from the previous attempt:\n- " + "\n- ".join(feedback)
    return prompt


async def generate_lesson_plan(request: LessonPlanRequest, feedback: list[str]) -> LessonPlan:
    """Generate a lesson plan for the request, incorporating validator feedback if any."""
    result = await build_generator().run(build_prompt(request, feedback))
    plan = result.output
    # The teacher's administrative block comes from the request, never from the model output.
    return plan.model_copy(update={"teacher": request.teacher})
