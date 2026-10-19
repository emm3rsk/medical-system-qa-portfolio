# Plateforme de Validation QA Système, Firmware & Dispositif Médical
### Banc de Test Temps Réel • Vérification BDD IEC 62304 • Triage de Logs Multi-Niveaux

Ce dépôt regroupe une plateforme intégrée d'automatisation de tests, de validation d'exigences de sécurité et de diagnostic multi-niveaux pour les systèmes d'imagerie médicale (radiologie 2D/3D panoramique, chaîne hybride IHM Qt $\leftrightarrow$ Pilotes C++ $\leftrightarrow$ Firmware MCU sous Linux/RTOS).

---

## 📦 Les Projets de la Plateforme

### 1. `project_1_fw_testbench/` — Banc de Test Automatisé Firmware & Injection de Pannes
* **Rôle :** Qualification du firmware temps réel pilotant les cinématiques (moteurs pas-à-pas) et l'émission de rayons X.
* **Protocole Binaire :** Cadrage STX/ETX, calcul de checksum CRC8-CCITT, encodage et décodage bidirectionnel.
* **Machine à États (FSM) :** Gestion déterministe des états du sous-système (`IDLE`, `POSITIONING`, `READY`, `ARMED`, `EMITTING`, `SAFE_HALT`).
* **Moteur d'Injection de Pannes :**
  * Altération de trames (bit-flips, désynchronisation d'octets, délimiteurs erronés).
  * Simulation de ruptures physiques (ouverture d'interlock de porte, arrêt d'urgence).
* **Invariant de Sécurité Critique :** Vérification de la coupure matérielle de la haute tension en $< 50\text{ ms}$ et du basculement immédiat en `Safe State` (IEC 62304 Classe C).

### 2. `project_2_iec62304_bdd/` — Vérification BDD & Traçabilité Médicale IEC 62304 / ISO 14971
* **Rôle :** Vérification logicielle du workflow d'acquisition panoramique 2D et conformité réglementaire (marquage CE / FDA).
* **Spécifications BDD Gherkin (`features/` & `step_defs/`) :** Scénarios exécutables liant directement chaque comportement aux exigences et aux risques :
  * Arborescence patient et vérification d'état.
  * Blocage préventif sur calibration expirée (> 24h).
  * Plafond de dose pédiatrique strict ($DAP \le 80\text{ mGy}\cdot\text{cm}^2$).
  * Double confirmation de sécurité d'armement.
  * Hachage cryptographique SHA-256 pour l'intégrité de l'image brute (IEC 81001-5-1).
* **Matrice de Traçabilité Automatique (RTM) :** Script (`tools/generate_rtm.py`) extrayant les métadonnées de tests pour générer automatiquement la matrice bidirectionnelle `Exigences SRS` $\leftrightarrow$ `Risques ISO 14971` $\leftrightarrow$ `Tests BDD`.

### 3. `project_3_log_correlator/` — Diagnostic Multi-Niveaux & Corrélation RCA
* **Rôle :** Outil CLI de diagnostic et d'analyse de cause racine (Root Cause Analysis - RCA) pour architectures distribuées (IHM Windows/Qt, pilote USB/Ethernet C++, microcontrôleur embarqué).
* **Ingestion Hétérogène :**
  * Logs applicatifs Qt (horodatage ISO 8601, threads UI et Comm).
  * Logs pilote C++ (traces USB hexadécimales).
  * Logs firmware MCU (temps relatif `[T+ms]`, états FSM).
* **Synchronisation Temporelle :** Calcul automatique du *clock skew* et recalage sur une timeline milliseconde unifiée.
* **Moteur Heuristique RCA :** Isolement du précurseur physique réel (ex. surintensité moteur) masqué par les erreurs applicatives en cascade (timeout socket, crash IHM).
* **Génération de Fiche ALM :** Production automatique d'un ticket d'anomalie normé pour Target Process / Jira avec sévérité médicale.

---

## 🏗️ Architecture du Répertoire

```
.
├── Makefile                            # Commandes d'automatisation et cibles de test
├── README.md                           # Documentation technique de la plateforme
├── requirements.txt                    # Dépendances Python (pytest, pytest-bdd, rich, etc.)
├── run_all_demos.py                    # Orchestrateur d'exécution globale des 3 projets
├── pytest.ini                          # Configuration des marqueurs médicaux IEC 62304
│
├── docs/                               # Livrables d'ingénierie et spécifications
│   ├── PRD-01-Firmware-Safety-Testbench.md
│   ├── PRD-02-IEC62304-BDD-Traceability.md
│   ├── PRD-03-Multilevel-Log-Correlator.md
│   ├── RTM_Report.md                   # Matrice RTM générée automatiquement
│   └── Defect_Report_TargetProcess.md  # Rapport Target Process généré automatiquement
│
├── project_1_fw_testbench/             # PROJET 1 : Banc FW & Injection de Pannes
│   ├── firmware_sim/                   # Émulateur MCU & protocole binaire CRC8
│   ├── harness/                        # Client de test & injecteur de pannes
│   ├── tests/                          # 10 tests PyTest (nominaux, pannes, sécurité)
│   └── README.md
│
├── project_2_iec62304_bdd/             # PROJET 2 : Vérification Médicale & Suite BDD
│   ├── docs/                           # SRS, Analyse FMEA ISO 14971, Plan SVP, TSR
│   ├── core/                           # Logique métier (calcul DAP, contrôle dose, SHA-256)
│   ├── features/                       # Spécifications Gherkin exécutables
│   ├── step_defs/                      # Step definitions PyTest-BDD
│   ├── tools/                          # Générateur automatique de la matrice RTM
│   └── README.md
│
└── project_3_log_correlator/           # PROJET 3 : Triage de Logs & Détection Cause Racine
    ├── fixtures/                       # Jeux de logs hétérogènes réels
    ├── src/                            # Parsers multi-sources, synchroniseur temporel, moteur RCA
    ├── tests/                          # Tests unitaires et d'intégration
    ├── log_triage.py                   # Outil CLI prêt à l'emploi
    └── README.md
```

---

## 🚀 Démarrage Rapide

### 1. Installation de l'environnement

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Exécution Globale de la Plateforme

Pour exécuter l'ensemble des suites de tests, générer la matrice de traçabilité et produire le diagnostic d'incident :
```bash
make demo
# ou
python run_all_demos.py
```

### 3. Commandes Spécifiques

```bash
# Exécuter les 21 tests automatisés
make test

# Tester spécifiquement le banc firmware et la coupure de sécurité (< 50 ms)
make test-p1

# Exécuter la suite BDD Gherkin (IEC 62304)
make test-p2

# Régénérer la matrice de traçabilité des exigences (RTM)
make rtm

# Exécuter l'outil de corrélation de logs et générer le ticket Target Process
make triage
```
