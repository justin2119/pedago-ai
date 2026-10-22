# Corpus d'ingestion

Ce dossier regroupe les documents de référence utilisés pour l'ingestion du corpus pédagogique. Il est organisé par type de document, niveau scolaire, matière, série et chapitre.

## Deux types de documents

### `guides_execution/` (Ancre 1 : Rulebook)
Guides d'exécution pédagogique officiels. Ils définissent les règles, attendus et contraintes de mise en œuvre du programme (objectifs, compétences exigibles, modalités d'évaluation, déroulement attendu). Ils servent de référence normative : ce qui est prescrit doit être respecté.

### `fiches_modeles/` (Ancre 2 : Gold Standard)
Fiches de cours modèles étalons. Ce sont des exemples de référence de haute qualité, qui illustrent le niveau de rédaction, la structure et le contenu attendus pour une fiche de cours. Ils servent de modèle de qualité (gold standard) pour la génération et l'évaluation.

## Structure

```
corpus/
  guides_execution/
    lycee/
      sciences_physiques/
        seconde/
        premiere/
        terminale/
          a4/
  fiches_modeles/
    lycee/
      sciences_physiques/
        seconde/
        premiere/
        terminale/
          a4/
```

Les séries sont indiquées par leur code (par exemple `a4` pour la Terminale A4, ou `s` / `cd` pour les séries scientifiques de seconde selon le besoin). Ajouter de nouvelles séries revient à créer un nouveau sous-dossier au même niveau.

## Convention de nommage des fichiers

Format général : `<type>_<matiere>_<niveau>_<serie>[_<chapitre>].pdf`

- `<type>` : `guide` pour un guide d'exécution, `fiche_modele` pour une fiche modèle.
- `<matiere>` : `sp` pour Sciences Physiques.
- `<niveau>` : `seconde`, `premiere` ou `tle` (ou `2nde`, `1ere`, `tle`, au choix mais à conserver de manière cohérente).
- `<serie>` : `a4`, `s`, `cd`, etc. Omettre si non applicable.
- `<chapitre>` : slug du chapitre en minuscules, sans accents ni espaces (par exemple `optique`).

Exemples :
- `guide_sp_tle_a4.pdf`
- `fiche_modele_sp_tle_a4_optique.pdf`
- `fiche_modele_sp_2nde_cd_mouvement_et_forces.pdf`

Règles : tout en minuscules, underscores comme séparateurs, pas d'accents, pas d'espaces.

## Métadonnées attendues lors de l'ingestion

Chaque document doit être associé aux champs suivants :

- `classe` : niveau scolaire (`seconde`, `premiere`, `terminale`).
- `matiere` : matière (`sciences_physiques`).
- `serie` : série (`a4`, `s`, `cd`, ... ou `general` / `non_applicable`).
- `chapitre` : intitulé ou slug du chapitre (vide pour un guide couvrant tout le programme).
- `type_document` : `guide_execution` ou `fiche_modele` (déduit du dossier parent).

## Ajouter un document

1. Placer le fichier dans le dossier correspondant au type, au niveau et à la série.
2. Nommer le fichier selon la convention ci-dessus.
3. Renseigner les métadonnées lors de l'ingestion.
