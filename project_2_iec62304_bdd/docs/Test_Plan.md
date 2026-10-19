# Software Verification Plan (SVP / Test Plan)
## Conforme à l'IEC 62304 Section 5.7
**Projet :** Panoramic 2D Verification  
**Auteur :** Lead QA Engineer (SW/FW/HW Integration)  
**Classification logiciel :** Classe B  

---

### 1. Objectifs de la Vérification
Valider que le logiciel d'acquisition 2D satisfait à 100% de ses exigences fonctionnelles (`SRS-ACQ-xxx`), de ses exigences de réduction des risques (`SRS-SAF-xxx`), et de sécurité des données (`SRS-CYB-xxx`), tout en assurant l'absence de régression.

---

### 2. Stratégie de Test & Niveaux de Couverture
* **Méthodologie :** BDD (Behavior-Driven Development) avec spécifications exécutables Gherkin.
* **Environnement d'Exécution :** Banc de test automatisé sous PyTest-BDD en intégration continue (CI Jenkins).
* **Couverture Exigée :**
  * 100% des exigences logicielles tracées vers au moins un scénario de test.
  * 100% des mitigations de risques ISO 14971 validées par des cas de test aux limites (*Boundary Value Testing* et cas négatifs).
  * 0 défaut critique ou majeur ouvert lors de la revue de jalon (*Gate Review*).

---

### 3. Critères d'Arrêt et de Suspension
* **Suspension des tests :** Détection d'un échec sur une exigence de sécurité critique (`SRS-SAF-003` sur-exposition ou non-coupure d'interlock).
* **Reprise des tests :** Livraison d'un correctif avec analyse d'impact conjointe Développeur/QA et re-jeu complet de la suite de non-régression.

---

### 4. Responsabilités
* **QA Testeur :** Rédaction des fichiers `.feature`, implémentation des step definitions Python, génération et signature de la Matrice de Traçabilité des Exigences (RTM).
* **Lead Développeur :** Revue des tests, analyse d'impact des défauts signalés.
* **Responsable Affaires Réglementaires (RA/QA) :** Validation finale du Test Summary Report (TSR) pour le dossier technique de marquage CE / soumission FDA.
