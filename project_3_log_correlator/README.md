# Project 3 : Outil d'Analyse et de Corrélation de Logs Multi-Niveaux

Ce sous-projet implémente un outil CLI de diagnostic et de corrélation temporelle d'anomalies pour systèmes distribués médicaux. Il permet de résoudre les incidents complexes où logiciel PC (Qt), pilote (C++) et firmware (MCU) émettent des journaux hétérogènes.

## Fonctionnalités

1. **Ingestion Multi-Sources :**
   * Log Applicatif Windows/Qt (`app_qt.log`) : Horodatage ISO 8601, threads UI et Comm.
   * Log Pilote C++ (`driver_comm.log`) : Traces de paquets USB hexadécimaux et états de socket.
   * Log Firmware MCU (`firmware_mcu.log`) : Compteur relatif temps réel `[T+ms]`, états FSM et capteurs.
2. **Synchronisation Temporelle Automatique :**
   * Calcule le décalage d'horloge (*clock skew*) à partir des événements de poignée de main communs.
   * Aligne l'ensemble des événements sur une timeline milliseconde unique.
3. **Moteur d'Analyse de Cause Racine (RCA) :**
   * Différencie le précurseur physique initial des pannes en cascade (ex. surintensité moteur $\rightarrow$ Safe State $\rightarrow$ Timeout pilote $\rightarrow$ Erreur IHM).
4. **Génération de Fiche Target Process / ALM :**
   * Génère automatiquement un rapport Markdown normé avec classification de risque IEC 62304 et recommandations aux équipes.

## Utilisation

```bash
# Diagnostic avec génération du ticket Target Process
python project_3_log_correlator/log_triage.py \
    --app-log project_3_log_correlator/fixtures/app_qt.log \
    --driver-log project_3_log_correlator/fixtures/driver_comm.log \
    --fw-log project_3_log_correlator/fixtures/firmware_mcu.log \
    --output-defect docs/Defect_Report_TargetProcess.md
```
