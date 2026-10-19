# Requirements Traceability Matrix (RTM)
**Projet :** Panoramic 2D Verification Suite  
**Généré le :** 2026-10-19 12:25:30  
**Normes :** IEC 62304 Classe B / ISO 14971:2019  

| ID Exigence | Description Exigence | Risque ISO 14971 | Scénario de Test BDD | Statut Vérification |
| :--- | :--- | :--- | :--- | :--- |
| `SRS-ACQ-001` | Sélection obligatoire d'un profil patient avant armement | `Risk-RSK-MIS-01` | Refus d'armement si aucun dossier patient n'est actif | **PASS** |
| `SRS-CAL-002` | Vérification de la calibration capteur (Dark current < 24h) | `Risk-RSK-IMG-02` | Détection de calibration capteur expirée | **PASS** |
| `SRS-SAF-003` | Plafond de dose pédiatrique strict (DAP <= 80 mGy.cm2) | `Risk-RSK-RAD-03` | Contrôle du seuil de dose maximale selon la morphologie | **PASS** |
| `SRS-ACQ-004` | Séquence d'armement à double confirmation explicite | `Risk-RSK-RAD-04` | Validation de l'armement après double confirmation | **PASS** |
| `SRS-CYB-005` | Contrôle d'intégrité cryptographique SHA-256 du cliché | `Risk-RSK-SEC-05` | Contrôle de conformité de l'empreinte SHA-256 de l'image | **PASS** |

### Synthèse de Couverture
* **Couverture des exigences :** 100% (5/5 exigences couvertes)
* **Couverture des risques ISO 14971 :** 100% (5/5 risques mitigés et testés)
* **Statut Global :** **CONFORME POUR AUDIT**
