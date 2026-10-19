@Component:Acquisition @IEC62304:ClassB
Feature: Vérification du workflow d'acquisition panoramique 2D

  Background:
    Given le système d'imagerie est sous tension et en état "IDLE"

  @SRS-ACQ-001 @Risk-RSK-MIS-01
  Scenario: Refus d'armement si aucun dossier patient n'est actif
    Given aucun profil patient n'est sélectionné
    When le praticien demande l'armement pour un cliché panoramique à 70 kV et 8 mA
    Then le système refuse l'armement avec l'erreur "ERR_NO_PATIENT"
    And l'état du système reste "IDLE"

  @SRS-CAL-002 @Risk-RSK-IMG-02
  Scenario: Détection de calibration capteur expirée
    Given un patient sélectionné avec le profil "Adulte"
    And la dernière calibration du capteur date de 30 heures
    When le praticien demande l'armement pour un cliché panoramique à 70 kV et 8 mA
    Then le système refuse l'armement avec l'erreur "ERR_CALIBRATION_EXPIRED"
    And l'état du système reste "IDLE"

  @SRS-SAF-003 @Risk-RSK-RAD-03 @SafetyCritical
  Scenario Outline: Contrôle du seuil de dose maximale selon la morphologie
    Given un patient sélectionné avec le profil "<profil>"
    And la dernière calibration du capteur date de 2 heures
    When le praticien configure l'exposition à "<kv>" kV et "<ma>" mA pour une durée de "<duree>" ms
    Then l'armement du générateur doit retourner le statut "<statut>"
    And la dose calculée ne doit pas excéder "<dose_max>" mGy.cm2

    Examples:
      | profil  | kv | ma | duree | statut  | dose_max |
      | Adulte  | 75 | 10 | 150   | AUTORISÉ| 250      |
      | Enfant  | 60 | 4  | 150   | AUTORISÉ| 80       |
      | Enfant  | 85 | 12 | 600   | REFUSÉ  | 80       |

  @SRS-ACQ-004 @Risk-RSK-RAD-04
  Scenario: Validation de l'armement après double confirmation
    Given un patient sélectionné avec le profil "Adulte"
    And la dernière calibration du capteur date de 2 heures
    When le praticien demande l'armement avec confirmation explicite validée
    Then l'armement est validé et le système passe en état "ARMED"

  @SRS-CYB-005 @Risk-RSK-SEC-05
  Scenario: Contrôle de conformité de l'empreinte SHA-256 de l'image
    Given un patient sélectionné avec le profil "Adulte"
    And le générateur est armé avec succès
    When un flux d'image brute de 2048 octets est transféré par le capteur
    Then l'image est acceptée avec le statut "ACQUIRED_OK"
    And une empreinte cryptographique SHA-256 de 64 caractères est enregistrée
