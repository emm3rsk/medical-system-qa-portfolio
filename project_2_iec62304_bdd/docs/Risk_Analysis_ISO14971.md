# Analyse de Risques Logiciels (ISO 14971:2019 / FMEA)
## Système d'Imagerie Dentaire Numérique
**Classification dispositif :** Classe IIb (CE) / Classe II (FDA 510k)  
**Norme logicielle :** IEC 62304:2006+A1:2015  

---

### Matrice FMEA des Risques Logiciels

| ID Risque | Phénomène Dangereux (Hazard) | Cause Logicielle Initiale | Sévérité Initiale | Mesure de Maîtrise Logicielle (Mitigation) | Exigence Traçable | Sévérité Résiduelle | Risque Acceptable |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **RSK-MIS-01** | Exposition d'un mauvais patient | Tir radiologique sans affectation de dossier préalable | Moyenne (3/5) | Verrouillage IHM : sélection obligatoire avant déverrouillage de la commande d'armement | `SRS-ACQ-001` | Faible (1/5) | OUI |
| **RSK-IMG-02** | Diagnostic erroné menant à acte chirurgical inapproprié | Image bruitée suite à dérive thermique du capteur non calibré | Élevée (4/5) | Blocage systématique de l'armement si calibration > 24h | `SRS-CAL-002` | Négligeable (1/5) | OUI |
| **RSK-RAD-03** | Sur-exposition radiologique pédiatrique (Cancérogenèse induite) | Paramétrage de dose adulte appliqué accidentellement à un enfant | Critique (5/5) | Plafond strict et calcul bloquant du Produit Dose-Surface ($DAP \le 80\text{ mGy}\cdot\text{cm}^2$) | `SRS-SAF-003` | Faible (1/5) | OUI |
| **RSK-RAD-04** | Émission involontaire de rayons X | Clic accidentel sur l'interface graphique | Élevée (4/5) | Séquence d'armement à double confirmation explicite | `SRS-ACQ-004` | Négligeable (1/5) | OUI |
| **RSK-SEC-05** | Altération ou corruption silencieuse des données d'imagerie | Erreur de bus de stockage ou altération externe des fichiers | Élevée (4/5) | Calcul systématique d'empreinte SHA-256 et vérification d'intégrité à la lecture | `SRS-CYB-005` | Négligeable (1/5) | OUI |
