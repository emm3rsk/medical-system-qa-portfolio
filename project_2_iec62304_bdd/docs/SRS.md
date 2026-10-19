# Software Requirements Specification (SRS)
## Sous-système : Acquisition Panoramique Dentaire 2D
**Norme de référence :** IEC 62304:2006+A1:2015 - Classe B  
**Projet :** Medical Dental Imaging Suite  

---

### 1. Introduction & Objet
Ce document définit les exigences fonctionnelles, de sécurité et d'intégrité pour le module d'acquisition 2D de la chaîne d'imagerie panoramique dentaire.

---

### 2. Liste des Exigences Logicielles (SRS)

#### SRS-ACQ-001 : Sélection Obligatoire du Dossier Patient
* **Description :** Le logiciel doit interdire toute mise en pré-chauffage ou armement du générateur tant qu'un dossier patient valide avec une catégorie morphologique (`ADULTE` ou `ENFANT`) n'a pas été sélectionné par l'opérateur.
* **Critère d'Acceptation :** Toute tentative d'armement sans patient actif déclenche une erreur `ERR_NO_PATIENT` et maintient le système à l'état `IDLE`.
* **Atténuation Risque Associé :** `RSK-MIS-01` (Exposition d'un mauvais patient ou mauvaise assignation des données de santé).

#### SRS-CAL-002 : Vérification Périodique de Calibration Capteur
* **Description :** Le logiciel doit vérifier l'horodatage de la dernière calibration de bruit de fond (Dark Current). Si celle-ci est antérieure à 24 heures, l'armement est verrouillé et une calibration rapide est exigée.
* **Critère d'Acceptation :** Une calibration datant de plus de 24h bloque l'acquisition avec le statut `ERR_CALIBRATION_EXPIRED`.
* **Atténuation Risque Associé :** `RSK-IMG-02` (Artefact d'image entraînant un diagnostic erroné).

#### SRS-SAF-003 : Plafond Strict de Dose Pédiatrique (DAP)
* **Description :** Pour un profil sélectionné en catégorie `ENFANT`, le logiciel calcule le produit dose-surface estimé ($DAP = k \times kV \times mA \times time$). Si le DAP dépasse $80\text{ mGy}\cdot\text{cm}^2$, l'armement doit être strictement rejeté.
* **Critère d'Acceptation :** Le calcul de DAP est bloquant avant l'envoi de la commande d'armement au générateur. Statut `REFUSÉ` si $DAP > 80\text{ mGy}\cdot\text{cm}^2$.
* **Atténuation Risque Associé :** `RSK-RAD-03` (Sur-exposition radiologique pédiatrique - Risque critique).

#### SRS-ACQ-004 : Confirmation d'Armement par Double Commande
* **Description :** L'activation du mode prêt à tirer (`ARMED`) doit exiger une confirmation explicite de l'opérateur (double commande ou maintien de bouton).
* **Critère d'Acceptation :** Transition vers l'état `ARMED` uniquement après confirmation explicite.
* **Atténuation Risque Associé :** `RSK-RAD-04` (Déclenchement intempestif de rayons X).

#### SRS-CYB-005 : Contrôle d'Intégrité Cryptographique de l'Image
* **Description :** Dès la fin du transfert de l'image brute depuis le capteur, le logiciel doit calculer son empreinte numérique SHA-256 et la sceller dans les métadonnées DICOM.
* **Critère d'Acceptation :** Le hash SHA-256 est calculé et validé lors de la relecture; toute modification d'un octet de l'image est détectée.
* **Atténuation Risque Associé :** `RSK-SEC-05` (Corruption silencieuse ou altération malveillante du cliché médical).
