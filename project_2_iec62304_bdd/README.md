# Project 2 : Dossier de Vérification Médicale IEC 62304 & Suite BDD

Ce sous-projet implémente un dossier complet de vérification logicielle médicale pour le workflow d'acquisition panoramique 2D d'un équipement d'imagerie dentaire. Il réconcilie le développement agile BDD (Gherkin) avec les exigences réglementaires des organismes notifiés (TÜV, FDA).

## Contenu Réglementaire (`docs/`)

* **`SRS.md` :** Spécification des exigences logicielles (`SRS-ACQ-001`, `SRS-CAL-002`, `SRS-SAF-003`, `SRS-ACQ-004`, `SRS-CYB-005`).
* **`Risk_Analysis_ISO14971.md` :** Analyse de risques (FMEA) associant les dangers cliniques aux mesures d'atténuation logicielle.
* **`Test_Plan.md` :** Plan de vérification logicielle formel (SVP) conforme à l'IEC 62304 §5.7.
* **`Test_Summary_Report_Template.md` :** Modèle de rapport de fin de vérification (TSR) pour revue de jalon (*Gate Review*).
* **`RTM_Report.md` :** Matrice de traçabilité bidirectionnelle des exigences générée automatiquement.

## Spécifications Exécutables BDD (`features/` & `step_defs/`)

Les scénarios sont écrits en Gherkin et taggés directement avec les identifiants d'exigences et de risques :
* Vérification de l'arborescence patient obligatoire.
* Blocage sur calibration expirée (> 24h).
* Plafond bloquant de dose pédiatrique ($DAP \le 80\text{ mGy}\cdot\text{cm}^2$).
* Double confirmation de sécurité d'armement.
* Intégrité cryptographique SHA-256 du cliché brut.

## Commandes

```bash
# 1. Exécution des tests BDD
pytest project_2_iec62304_bdd/step_defs/ -v

# 2. Génération automatique de la matrice RTM
python project_2_iec62304_bdd/tools/generate_rtm.py
```
