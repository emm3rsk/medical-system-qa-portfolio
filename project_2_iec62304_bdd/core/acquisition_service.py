"""
Service d'acquisition panoramique dentaire 2D.
Implémente les règles de gestion médicale : validation de profil, calcul bloquant de dose (DAP),
contrôle de calibration et calcul d'intégrité cryptographique SHA-256.
"""

import hashlib
import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple


class PatientCategory(str, Enum):
    ADULT = "Adulte"
    PEDIATRIC = "Enfant"


@dataclass
class Patient:
    id: str
    name: str
    category: PatientCategory


class AcquisitionService:
    def __init__(self):
        self.state: str = "IDLE"
        self.active_patient: Optional[Patient] = None
        self.last_calibration_time: Optional[float] = time.time()  # Par défaut, calibration récente
        self.last_calculated_dap: float = 0.0
        self.last_acquired_hash: Optional[str] = None

    def select_patient(self, patient: Patient):
        self.active_patient = patient

    def clear_patient(self):
        self.active_patient = None

    def set_calibration_age_hours(self, hours: float):
        """Définit l'ancienneté de la calibration par rapport au temps présent."""
        self.last_calibration_time = time.time() - (hours * 3600.0)

    def calculate_dap(self, kv: int, ma: int, time_ms: int) -> float:
        """
        Calcule le Produit Dose-Surface estimé (DAP) en mGy.cm2.
        Formule normalisée : DAP = coeff * kV * mA * (time_ms / 1000)
        """
        # Constante d'atténuation et géométrie collimateur (ex: 0.15)
        coeff = 0.15
        dap = coeff * kv * ma * (time_ms / 1000.0)
        self.last_calculated_dap = round(dap, 2)
        return self.last_calculated_dap

    def request_arming(
        self,
        kv: int,
        ma: int,
        time_ms: int = 150,
        double_confirmed: bool = True,
    ) -> Tuple[bool, str]:
        """
        Valide l'ensemble des sécurités avant d'autoriser l'armement du générateur.
        Retourne : (succès: bool, message: str)
        """
        # 1. SRS-ACQ-001 : Dossier patient actif obligatoire
        if self.active_patient is None:
            self.state = "IDLE"
            return False, "ERR_NO_PATIENT"

        # 2. SRS-CAL-002 : Calibration capteur valide (< 24h)
        if self.last_calibration_time is None:
            return False, "ERR_CALIBRATION_REQUIRED"
        cal_age_hours = (time.time() - self.last_calibration_time) / 3600.0
        if cal_age_hours > 24.0:
            return False, "ERR_CALIBRATION_EXPIRED"

        # 3. SRS-SAF-003 : Plafond strict de dose pédiatrique (DAP <= 80 mGy.cm2)
        dap = self.calculate_dap(kv, ma, time_ms)
        if self.active_patient.category == PatientCategory.PEDIATRIC and dap > 80.0:
            return False, "ERR_PEDIATRIC_DOSE_EXCEEDED"

        # 4. SRS-ACQ-004 : Confirmation double commande
        if not double_confirmed:
            return False, "ERR_DOUBLE_CONFIRMATION_REQUIRED"

        self.state = "ARMED"
        return True, "ARMED_OK"

    def acquire_image(self, raw_data: bytes) -> Tuple[str, str]:
        """
        Traite le flux d'image brute et calcule l'empreinte SHA-256 (SRS-CYB-005).
        """
        if self.state != "ARMED":
            return "", "ERR_NOT_ARMED"

        sha256 = hashlib.sha256(raw_data).hexdigest()
        self.last_acquired_hash = sha256
        self.state = "ACQUIRED"
        return sha256, "ACQUIRED_OK"
