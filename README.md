# PrepaCours (pedago-ai)

![Vert Foret](https://img.shields.io/badge/Vert_For%C3%AAt-006A4E?style=for-the-badge&logoColor=white) ![Jaune Or](https://img.shields.io/badge/Jaune_Or-FFCE00?style=for-the-badge&logoColor=black) ![Rouge Sang](https://img.shields.io/badge/Rouge_Sang-D21034?style=for-the-badge&logoColor=white) ![Blanc Pur](https://img.shields.io/badge/Blanc_Pur-FFFFFF?style=for-the-badge&logoColor=black) ![Fond clair](https://img.shields.io/badge/Fond_clair-F8FAF9?style=for-the-badge&logoColor=black)

PrepaCours est un outil de génération de fiches pédagogiques assistée par intelligence artificielle pour l'Enseignement Secondaire Général (Collège et Lycée) au Togo, selon le cadre de l'Approche Par Compétences (APC).

## Pile technique

- Python 3.11+ géré avec uv
- Backend FastAPI
- Agents PydanticAI (orchestrateur, récupérateur, générateur, validateur)
- Proxy de modèle compatible OpenAI (URL de base et modèle configurables)
- Supabase avec pgvector pour la recherche documentaire (retrieval)
- Frontend : HTML5 / CSS3 / JavaScript ES6+ natif, sous forme d'application web progressive (PWA, voir ci-dessous)

## Système de design national togolais

L'interface reprend les couleurs du drapeau togolais, chacune ayant un rôle fonctionnel fixe.

| Jeton | Code hexadécimal | Rôle | Badge |
|---|---|---|---|
| Vert Forêt / Espoir | `#006A4E` | Éléments structurels principaux, accents de marque, états de réussite | ![#006A4E](https://img.shields.io/badge/Vert_For%C3%AAt-006A4E?style=flat-square) |
| Jaune Or / Travail | `#FFCE00` | Mises en avant secondaires, badges, avertissements, indicateurs APC | ![#FFCE00](https://img.shields.io/badge/Jaune_Or-FFCE00?style=flat-square&logoColor=black) |
| Rouge Sang / Fidélité | `#D21034` | Actions critiques, bouton d'action « Générer », bande de l'emblème | ![#D21034](https://img.shields.io/badge/Rouge_Sang-D21034?style=flat-square) |
| Blanc Pur | `#FFFFFF` | Surfaces et cartes | ![#FFFFFF](https://img.shields.io/badge/Blanc_Pur-FFFFFF?style=flat-square&logoColor=black) |
| Fond clair | `#F8FAF9` | Arrière-plan épuré des pages pédagogiques | ![#F8FAF9](https://img.shields.io/badge/Fond_clair-F8FAF9?style=flat-square&logoColor=black) |

## Architecture PWA du frontend

Statut : cette section décrit l'architecture cible du frontend. Les fichiers frontend listés ci-dessous ne sont pas encore présents dans le dépôt.

- HTML5 / CSS3 / JavaScript ES6+ natif, sans aucun framework JavaScript externe et sans surcharge d'exécution.
- Prise en charge complète de la PWA :
  - `manifest.json` pour l'installabilité et les métadonnées de l'application.
  - Service Worker (`sw.js`) qui met en cache les fiches générées afin que les enseignants puissent les consulter hors ligne dans les zones à faible connectivité au Togo.
- Persistance locale du profil administratif de l'enseignant (Nom, Prénom, DRE, IESG, Établissement, Téléphone) via `localStorage`, afin que l'en-tête de chaque fiche de cours soit pré-rempli.

### Style Carré

Les règles du système de design, appelées « Style Carré », garantissent une interface sobre et institutionnelle :

- Les cartes, champs de saisie et fenêtres modales utilisent un rayon de bordure de 4 px à 5 px.
- La forme en pilule (`rounded-full`) est réservée exclusivement aux boutons d'action principaux et aux badges.

## Installation

```bash
uv sync
cp .env.example .env
uv run uvicorn pedago_ai.main:app --reload
```

Contrôle de santé : GET /health

## Requête de fiche pédagogique

Les informations administratives de l'enseignant sont obligatoires avant la génération d'une fiche de cours. Le bloc `teacher` est validé en premier et est copié dans l'en-tête officiel du document Word généré.

```json
{
  "teacher": {
    "nom": "Mensah",
    "prenom": "Kofi",
    "dre": "DRE Maritime",
    "iesg": "IESG Vogan",
    "etablissement": "Lycée de Vogan",
    "telephone": "+228 90 00 00 00",
    "classe": "Seconde C",
    "serie": "C"
  },
  "subject": "Physique-Chimie",
  "level": "Seconde C",
  "theme": "Mécanique",
  "sub_theme": "Forces et mouvements",
  "duration_minutes": 55,
  "competence": "Expliquer le mouvement d'un solide soumis à des forces"
}
```

Notes sur les champs :

- `nom`, `prenom`, `dre`, `iesg`, `etablissement`, `telephone` et `classe` sont obligatoires.
- `serie` est facultatif.
- Une requête sans le bloc `teacher` est rejetée avec une erreur de validation.
