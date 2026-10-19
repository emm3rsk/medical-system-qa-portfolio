# PRD 03 : Outil d'Analyse et de Corrélation de Logs Multi-Niveaux
**Nom du projet :** `med-log-correlator`  
**Outil :** CLI Python d'investigation et d'aide au diagnostic pour équipes pluridisciplinaires  
**Version :** 1.0.0 | **Statut :** Prêt pour implémentation  

---

## 1. Contexte & Problématique Métier

Dans les systèmes d'imagerie médicale, l'architecture est distribuée sur plusieurs couches hétérogènes :
* **Niveau Applicatif (PC Windows) :** IHM en Qt/QML, logiciel de gestion d'acquisition, outils de calibration et maintenance.
* **Niveau Pilotes / Bibliothèques (C++) :** Couches de communication USB, Ethernet/Sockets, gestion des buffers d'images.
* **Niveau Embarqué / Bas Niveau (Firmware / Linux embarqué / MCU) :** Pilotage temps réel des moteurs, asservissement thermique, contrôle du tube à rayons X.

Lorsqu'un problème survient sur machine réelle (ex. interruption inattendue de tir, écran d'erreur générique `ERR_DEVICE_BUSY`), chaque équipe regarde son propre fichier journal :
* Le développeur IHM voit : `"Timeout 5000ms en attente de l'image"`.
* Le développeur pilote voit : `"Socket fermé par le périphérique"`.
* L'ingénieur firmware voit : `"Safety trip: Collimator motor stall / Current limit 1.5A exceeded"`.

Sans corrélation, le triage prend des heures voire des jours avec des renvois de responsabilité (*"Ce n'est pas mon bug"*). Cet outil permet au testeur d'ingérer instantanément les 3 logs, de reconstruire la chronologie exacte et de **désigner la cause racine (*Root Cause*) avec un ticket Target Process pré-rempli**.

---

## 2. Architecture & Pipeline de Traitement

```
+--------------------+   +--------------------+   +--------------------+
|    app_qt.log      |   |   driver_comm.log  |   |  firmware_mcu.log  |
| (Format ISO8601)   |   | (Format Horodaté)  |   | (Format T+millisec)|
+---------+----------+   +---------+----------+   +---------+----------+
          |                        |                        |
          +------------------------+------------------------+
                                   |
                                   v
             +---------------------------------------------+
             |    PARSER UNIFIÉ & ALIGNEMENT TEMPOREL      |
             |   (Normalisation vers horodatage absolu)    |
             +---------------------+-----------------------+
                                   |
                                   v
             +---------------------------------------------+
             |        MOTEUR D'ANALYSE HEURISTIQUE         |
             |   - Détection d'événements précurseurs      |
             |   - Règles de causalité (HW -> FW -> SW)    |
             |   - Évaluation de sévérité médicale         |
             +---------------------+-----------------------+
                                   |
                                   +-----------------------+
                                   |                       |
                                   v                       v
               +-----------------------+       +-----------------------+
               | Vue Console Enrichie  |       | Fiche Défaut Markdown |
               | (Timeline avec `rich`)|       | (Target Process / ALM)|
               +-----------------------+       +-----------------------+
```

---

## 3. Spécification des Formats de Logs en Entrée

### 3.1 Log Applicatif PC (`app_qt.log`)
* Format : `YYYY-MM-DD HH:MM:SS.mmm [LEVEL] [Thread] Module - Message`
* Exemple :
  ```
  2026-10-17 14:15:02.100 [INFO] [UIThread] AcqWorkflow - Praticien clique sur 'Démarrer Exposition'
  2026-10-17 14:15:02.150 [DEBUG] [CommThread] DeviceProxy - Envoi commande PREPARE_XRAY
  2026-10-17 14:15:05.155 [ERROR] [CommThread] DeviceProxy - Timeout: Pas de confirmation dans les 3000ms
  2026-10-17 14:15:05.160 [WARN] [UIThread] AlertManager - Affichage Pop-up: "Erreur équipement 0x503"
  ```

### 3.2 Log Pilote C++ (`driver_comm.log`)
* Format : `[HH:MM:SS.mmm] [PID:TID] [SUBSYS] Message`
* Exemple :
  ```
  [14:15:02.152] [1204:4512] [USB_IO] TX -> 02 11 05 00 4B 0A 01 F4 C8 03 (CMD_ARM_XRAY)
  [14:15:02.165] [1204:4512] [USB_IO] RX <- 02 02 05 00 00 00 00 00 3A 03 (RSP_ARM_OK)
  [14:15:02.300] [1204:4512] [USB_IO] TX -> 02 12 06 00 AA 55 00 00 E1 03 (CMD_FIRE_XRAY)
  [14:15:02.450] [1204:8890] [USB_IO] RX_ASYNC <- 02 FE 07 00 04 00 00 00 77 03 (EVT_SAFETY_TRIP)
  [14:15:05.150] [1204:4512] [USB_IO] Driver watchdog expired on command 0x12
  ```

### 3.3 Log Microcontrôleur Firmware (`firmware_mcu.log`)
* Format : `[T+ms] [MODULE] Level: Message` *(l'horodatage est relatif au boot)*
* Exemple :
  ```
  [T+08451200] [FSM] State changed: READY -> ARMED
  [T+08451335] [GEN] High Voltage Generator enabled (75kV / 10mA)
  [T+08451480] [MOTOR] WARN: Collimator axis current spike detected (1.65A > max 1.20A)
  [T+08451485] [SAFETY] CRITICAL: Hard trip triggered by Collimator Overcurrent
  [T+08451486] [GEN] High Voltage Generator cut OFF by HW interlock (Duration: 151ms)
  [T+08451487] [FSM] State forced to STATE_SAFE_HALT
  ```

---

## 4. Spécifications Fonctionnelles de l'Outil CLI

### 4.1 Synchronisation Temporelle
* L'outil calcule l'offset entre le temps relatif firmware `[T+ms]` et l'heure système PC à partir de la première trame d'échange identifiée (ex. poignée de main `CMD_ARM_XRAY` / `RSP_ARM_OK`).
* Tous les logs sont alignés sur un même fuseau milliseconde.

### 4.2 Moteur de Détection de Cause Racine (Heuristique)
L'outil applique un ensemble de règles pour classifier l'anomalie :
1. **Règle R-MOTOR-01 :** Si un événement `MOTOR Overcurrent/Stall` précède un `EVT_SAFETY_TRIP` et un `Timeout UI`, la cause racine est classée : **Matériel / Mécanique (Collimation)**.
2. **Règle R-CRC-02 :** Si des trames `BAD_CRC` ou des déconnexions USB apparaissent sans anomalie firmware, la cause racine est classée : **Liaison physique / Pilote C++**.
3. **Règle R-APP-03 :** Si le firmware confirme l'envoi de l'image mais que l'IHM n'affiche rien, la cause racine est classée : **Logiciel Applicatif (Qt)**.

### 4.3 Générateur de Rapport Target Process
L'outil extrait la fenêtre temporelle critique (ex. 500 ms avant et après l'incident) et produit un fichier Markdown conforme au modèle de défaut de l'entreprise.

---

## 5. Spécifications Techniques

* **Langage :** Python 3.10+
* **Dépendances :**
  * `rich` : Pour le rendu de la timeline dans le terminal (couleurs, table, panneau récapitulatif).
  * `click` ou `argparse` : Interface en ligne de commande.
  * Standard library : `re`, `datetime`, `dataclasses`.
* **Interface CLI :**
  ```bash
  python log_triage.py analyze \
      --app-log tests/fixtures/app_qt.log \
      --driver-log tests/fixtures/driver_comm.log \
      --fw-log tests/fixtures/firmware_mcu.log \
      --output-defect defect_report.md
  ```

---

## 6. Exemple de Rendu Console (Sortie Attendue)

```
================================================================================
          SYSTÈME MÉDICAL - ANALYSEUR MULTI-LOGS DE DIAGNOSTIC
================================================================================
[*] Synchronisation temporelle calculée: Offset FW = +14:15:02.135
[*] Ingestion terminée: 142 lignes de logs parsées

------------------------- TIMELINE D'INCIDENT ALIGNÉE --------------------------
14:15:02.100 | [GUI]    | Click 'Démarrer Exposition'
14:15:02.152 | [DRIVER] | TX -> CMD_ARM_XRAY (75kV, 10mA)
14:15:02.165 | [FW]     | State transition: READY -> ARMED
14:15:02.300 | [DRIVER] | TX -> CMD_FIRE_XRAY
14:15:02.335 | [FW]     | Generator High Voltage ON
14:15:02.480 | [FW]     | [!] MOTOR: Collimator current spike 1.65A (max 1.20A) <-- [CAUSE RACINE]
14:15:02.485 | [FW]     | [!] SAFETY CRITICAL: Hard trip triggered
14:15:02.486 | [FW]     | Generator cut OFF by HW interlock (Exposition interrompue)
14:15:02.487 | [FW]     | State forced to STATE_SAFE_HALT
14:15:05.155 | [GUI]    | [!] Timeout 3000ms: Erreur 0x503

--------------------------------- DIAGNOSTIC ----------------------------------
Composant Responsable : MATÉRIEL / FIRMWARE (Axe Moteur Collimateur)
Sévérité Médicale     : MAJEURE (Interruption d'exposition, arrêt sécurisé immédiat)
Recommandation        : Vérifier le frottement mécanique ou le capteur de courant
                        avant toute intervention sur le logiciel PC.
Rapport généré        : defect_report.md (Prêt pour Target Process)
================================================================================
```

---

## 7. Structure du Projet

```
med-log-correlator/
├── README.md                   # Guide d'utilisation et cas d'usage
├── requirements.txt            # rich, click
├── fixtures/                   # Jeux de données simulant de vrais incidents
│   ├── app_qt.log
│   ├── driver_comm.log
│   └── firmware_mcu.log
├── src/
│   ├── __init__.py
│   ├── parsers.py              # Parsers regex pour les 3 formats de logs
│   ├── synchronizer.py         # Réalignement des horloges et tri chronologique
│   ├── rca_engine.py           # Moteur heuristique de cause racine
│   └── report_generator.py     # Génération template Target Process & rendu rich
└── log_triage.py               # Point d'entrée CLI
```

---

## 8. Critères d'Acceptation & Livrables de Qualification

1. **Outil CLI opérationnel :** Une commande unique générant la timeline couleur et le diagnostic.
2. **Fixtures d'incidents représentatives :** Au moins 2 scénarios d'incidents réels (ex. blocage moteur vs perte de paquets USB).
3. **Fiche Target Process normée :** Classification rigoureuse des anomalies, analyse d'impact et sévérité médicale.
