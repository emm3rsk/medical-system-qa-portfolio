# [DEFECT] [MATÉRIEL] Électronique / Mécanique (Axe Collimateur) - Collimator step motor current s...

## 1. Métadonnées du Défaut (Target Process)
* **Composant Affecté :** `MATÉRIEL`
* **Sévérité :** `MAJEURE (IEC 62304 Classe B/C)`
* **Classification Risque IEC 62304 :** `Non-acceptable sans mitigation matérielle`
* **Statut :** Ouvert (Prêt pour Triage Pluridisciplinaire)
* **Équipes Notifiées :** Matériel, Firmware, QA Système

---

## 2. Impact Clinique & Patient
Interruption prématurée du tir radiologique (exposition partielle). Sécurité patient préservée par la coupure immédiate en Safe State (< 50ms). Nouvelle acquisition requise après intervention.

---

## 3. Analyse Technique de Cause Racine (RCA)
Surintensité détectée sur l'axe collimateur (Collimator step motor current spike detected (1.75A > Limit 1.20A)) ayant déclenché la coupure matérielle par interlock et le passage du firmware en STATE_SAFE_HALT. Les erreurs ultérieures côté pilote C++ (Watchdog Expired) et IHM (Erreur 0x503) sont des conséquences directes de cette mise en sécurité.

---

## 4. Chronologie Unifiée des Événements (Corrélation Horodatée)
| Heure | Sous-Système | Niveau | Module | Message |
| :--- | :--- | :--- | :--- | :--- |
| `14:15:01.850` | `GUI (Qt)` | `INFO` | `UIThread/SessionManager` | Nouvelle session d'acquisition démarrée pour Patient P-001 |
| `14:15:02.100` | `GUI (Qt)` | `INFO` | `UIThread/AcqWorkflow` | Praticien clique sur 'Démarrer Exposition' (Profil: Adulte, 75kV, 10mA) |
| `14:15:02.150` | `GUI (Qt)` | `DEBUG` | `CommThread/DeviceProxy` | Envoi requête d'armement au pilote C++ |
| `14:15:02.152` | `PILOTE (C++)` | `DEBUG` | `USB_IO` | TX -> 02 11 05 04 4B 0A 00 96 C8 03 (CMD_ARM_XRAY) |
| `14:15:02.155` | `FIRMWARE (MCU)` | `INFO` | `COMM` | CMD_ARM_XRAY (Payload: kV=75, mA=10, Time=150ms) |
| `14:15:02.160` | `FIRMWARE (MCU)` | `INFO` | `FSM` | State transition: STATE_READY -> STATE_ARMED |
| `14:15:02.165` | `FIRMWARE (MCU)` | `INFO` | `COMM` | RSP_ACK (State=STATE_ARMED) |
| `14:15:02.168` | `PILOTE (C++)` | `DEBUG` | `USB_IO` | RX <- 02 F0 05 01 03 3A 03 (RSP_ACK: STATE_ARMED) |
| `14:15:02.170` | `GUI (Qt)` | `INFO` | `CommThread/DeviceProxy` | Confirmation armement reçue du pilote (Statut: READY_TO_FIRE) |
| `14:15:02.290` | `GUI (Qt)` | `INFO` | `UIThread/AcqWorkflow` | Déclenchement de la commande de tir radiologique |
| `14:15:02.300` | `GUI (Qt)` | `DEBUG` | `CommThread/DeviceProxy` | Envoi commande FIRE_XRAY au pilote |
| `14:15:02.302` | `PILOTE (C++)` | `DEBUG` | `USB_IO` | TX -> 02 12 06 02 AA 55 E1 03 (CMD_FIRE_XRAY) |
| `14:15:02.305` | `FIRMWARE (MCU)` | `INFO` | `COMM` | CMD_FIRE_XRAY (Key=0xAA55) |
| `14:15:02.310` | `FIRMWARE (MCU)` | `INFO` | `GEN` | High Voltage Generator enabled (kV=75, mA=10) |
| `14:15:02.315` | `FIRMWARE (MCU)` | `INFO` | `FSM` | State transition: STATE_ARMED -> STATE_EMITTING |
| `14:15:02.320` | `PILOTE (C++)` | `DEBUG` | `USB_IO` | RX <- 02 F0 06 01 04 4F 03 (RSP_ACK: STATE_EMITTING) |
| `14:15:02.475` | `FIRMWARE (MCU)` | `WARN` | `MOTOR` | Collimator step motor current spike detected (1.75A > Limit 1.20A) 🚨 **[ROOT CAUSE]** |
| `14:15:02.480` | `FIRMWARE (MCU)` | `CRITICAL` | `SAFETY` | Hard trip triggered by Collimator Mechanical Stall! |
| `14:15:02.482` | `FIRMWARE (MCU)` | `INFO` | `GEN` | High Voltage Generator CUT OFF by HW Interlock (Actual Exposure: 172ms) |
| `14:15:02.485` | `FIRMWARE (MCU)` | `INFO` | `FSM` | State forced to STATE_SAFE_HALT (Reason: FAULT_COLLIMATOR_STALL) |
| `14:15:02.488` | `FIRMWARE (MCU)` | `INFO` | `COMM` | EVT_SAFETY_TRIP (Code=0x04) |
| `14:15:02.490` | `PILOTE (C++)` | `WARN` | `USB_ASYNC` | RX_ASYNC <- 02 FE FF 03 04 00 87 91 03 (EVT_SAFETY_TRIP: FAULT_COLLIMATOR_STALL) |
| `14:15:05.305` | `PILOTE (C++)` | `ERROR` | `USB_IO` | Watchdog Expired: No EXP_COMPLETE packet received within 3000ms |
| `14:15:05.308` | `PILOTE (C++)` | `ERROR` | `DEV_DRV` | Notifying upper layer of communication breakdown |
| `14:15:05.310` | `GUI (Qt)` | `ERROR` | `CommThread/DeviceProxy` | TIMEOUT: Aucune trame de fin d'exposition reçue dans le délai imparti (3000ms) |
| `14:15:05.315` | `GUI (Qt)` | `WARN` | `UIThread/AlertManager` | Notification praticien: Affichage Pop-up [Erreur Équipement 0x503 - Échec Acquisition] |
| `14:15:05.320` | `GUI (Qt)` | `ERROR` | `UIThread/AcqWorkflow` | Abandon de la session et passage en mode dégradé |


---

## 5. Recommandations & Actions Correctives
- Contrôler la résistance mécanique et les frottements du chariot de collimation.
- Vérifier le calibre et la stabilité du capteur de courant moteur.
- Informer l'équipe logicielle PC qu'aucune correction logicielle n'est nécessaire : le timeout applicatif est la conséquence attendue de la coupure matérielle.

---
*Généré automatiquement par `med-log-correlator`.*
