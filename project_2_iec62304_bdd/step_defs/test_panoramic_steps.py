"""
Step definitions PyTest-BDD pour le workflow panoramique dentaire 2D.
Vérifie la conformité aux exigences IEC 62304 et aux réductions de risques ISO 14971.
"""

import os
import pytest
from pytest_bdd import given, when, then, parsers, scenarios
from project_2_iec62304_bdd.core.acquisition_service import (
    AcquisitionService,
    Patient,
    PatientCategory,
)

# Chargement du fichier feature
FEATURE_FILE = os.path.join(
    os.path.dirname(__file__), "..", "features", "panoramic_acquisition.feature"
)
scenarios(FEATURE_FILE)


@pytest.fixture
def context():
    """Contexte partagé entre les étapes d'un scénario."""
    service = AcquisitionService()
    return {
        "service": service,
        "last_result": None,
        "last_message": None,
        "raw_image": None,
        "image_hash": None,
    }


# --- Background & Givens ---


@given('le système d\'imagerie est sous tension et en état "IDLE"')
def system_in_idle(context):
    assert context["service"].state == "IDLE"


@given("aucun profil patient n'est sélectionné")
def no_patient_selected(context):
    context["service"].clear_patient()


@given(parsers.parse('un patient sélectionné avec le profil "{profil}"'))
def patient_selected(context, profil):
    cat = PatientCategory.PEDIATRIC if profil.lower() == "enfant" else PatientCategory.ADULT
    patient = Patient(id="P-001", name="Jean Dupont", category=cat)
    context["service"].select_patient(patient)


@given(parsers.parse("la dernière calibration du capteur date de {heures:d} heures"))
def calibration_age_int(context, heures):
    context["service"].set_calibration_age_hours(heures)


@given(parsers.parse('la dernière calibration du capteur date de "{heures}" heures'))
def calibration_age_str(context, heures):
    context["service"].set_calibration_age_hours(float(heures))


@given("le générateur est armé avec succès")
def generator_armed(context):
    ok, msg = context["service"].request_arming(kv=70, ma=8, time_ms=150, double_confirmed=True)
    assert ok is True
    assert context["service"].state == "ARMED"


# --- Whens ---


@when(
    parsers.parse(
        "le praticien demande l'armement pour un cliché panoramique à {kv:d} kV et {ma:d} mA"
    )
)
def request_arming_simple(context, kv, ma):
    ok, msg = context["service"].request_arming(kv=kv, ma=ma, time_ms=150, double_confirmed=True)
    context["last_result"] = ok
    context["last_message"] = msg


@when(
    parsers.parse(
        'le praticien configure l\'exposition à "{kv}" kV et "{ma}" mA pour une durée de "{duree}" ms'
    )
)
def configure_exposure_outline(context, kv, ma, duree):
    ok, msg = context["service"].request_arming(
        kv=int(kv),
        ma=int(ma),
        time_ms=int(duree),
        double_confirmed=True,
    )
    context["last_result"] = ok
    context["last_message"] = msg


@when("le praticien demande l'armement avec confirmation explicite validée")
def arm_with_double_confirmation(context):
    ok, msg = context["service"].request_arming(kv=70, ma=8, time_ms=150, double_confirmed=True)
    context["last_result"] = ok
    context["last_message"] = msg


@when(
    parsers.parse(
        "un flux d'image brute de {taille:d} octets est transféré par le capteur"
    )
)
def transfer_raw_image(context, taille):
    raw_data = bytes([0x42] * taille)
    h, status = context["service"].acquire_image(raw_data)
    context["image_hash"] = h
    context["last_message"] = status


# --- Thens ---


@then(parsers.parse('le système refuse l\'armement avec l\'erreur "{erreur}"'))
def arming_refused_with_error(context, erreur):
    assert context["last_result"] is False
    assert context["last_message"] == erreur


@then('l\'état du système reste "IDLE"')
def state_remains_idle(context):
    assert context["service"].state == "IDLE"


@then(parsers.parse('l\'armement du générateur doit retourner le statut "{statut}"'))
def verify_arming_status_outline(context, statut):
    expected_ok = statut == "AUTORISÉ"
    assert context["last_result"] is expected_ok


@then(parsers.parse('la dose calculée ne doit pas excéder "{dose_max}" mGy.cm2'))
def verify_dose_ceiling(context, dose_max):
    dap = context["service"].last_calculated_dap
    max_dap = float(dose_max)
    if context["last_result"] is True:
        assert dap <= max_dap


@then('l\'armement est validé et le système passe en état "ARMED"')
def arming_validated_state(context):
    assert context["last_result"] is True
    assert context["service"].state == "ARMED"


@then(parsers.parse('l\'image est acceptée avec le statut "{statut}"'))
def image_accepted_status(context, statut):
    assert context["last_message"] == statut
    assert context["service"].state == "ACQUIRED"


@then(
    parsers.parse(
        "une empreinte cryptographique SHA-256 de {nb_caract:d} caractères est enregistrée"
    )
)
def sha256_recorded(context, nb_caract):
    h = context["image_hash"]
    assert len(h) == nb_caract
    assert context["service"].last_acquired_hash == h
