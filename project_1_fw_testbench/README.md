# Project 1 : Banc de Test Automatisé & Injection de Pannes Firmware

Ce sous-projet implémente un banc de test automatisé pour sous-système critique de radiologie dentaire. Il démontre la maîtrise du test bas niveau, des protocoles binaires, de la robustesse et des sécurités matérielles (IEC 62304 Classe C).

## Architecture

* **Simulateur Firmware (`firmware_sim/`) :**
  * `protocol.py` : Cadrage binaire STX/ETX, calcul CRC8-CCITT, encodage/décodage de trames.
  * `fsm.py` : Machine à états finis (`IDLE`, `POSITIONING`, `READY`, `ARMED`, `EMITTING`, `SAFE_HALT`), registre de sécurités.
  * `server.py` : Serveur TCP asynchrone émulant le microcontrôleur temps réel.
* **Harness de Test (`harness/`) :**
  * `client.py` : Client synchrone gérant les requêtes/réponses et l'écoute asynchrone des alertes.
  * `fault_injector.py` : Moteur d'injection de pannes (corruption CRC, troncature, violations de protocole).
* **Suite de Tests (`tests/`) :**
  * `test_nominal_flow.py` : Scénarios nominaux complets d'armement et de tir.
  * `test_protocol_faults.py` : Tests aux limites et injection de trames corrompues.
  * `test_safety_critical.py` : Vérification des invariants de sécurité (ouverture de porte pendant tir $< 50\text{ ms}$, arrêts d'urgence).

## Exécution des Tests

```bash
source ../.venv/bin/activate
pytest project_1_fw_testbench/tests/ -v
```
