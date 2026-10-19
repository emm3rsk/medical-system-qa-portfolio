"""
Algorithme de synchronisation temporelle et fusion de logs multi-sources.
Compense la dérive d'horloge et aligne les timestamps relatifs MCU sur l'heure système PC.
"""

from typing import List, Tuple
from .models import LogEntry, Subsystem


def synchronize_and_merge(
    app_entries: List[LogEntry],
    driver_entries: List[LogEntry],
    mcu_entries: List[LogEntry],
) -> Tuple[List[LogEntry], float]:
    """
    Calcule l'offset temporel entre l'heure PC et le compteur relatif MCU,
    puis produit une timeline chronologique unifiée.
    Retourne : (timeline_ordonnée, offset_ms_appliqué)
    """
    offset_ms = 0.0

    # 1. Recherche d'un événement pivot commun entre le pilote et le MCU
    # Exemple : Envoi de CMD_ARM_XRAY par le pilote et réception par le MCU
    driver_pivot = None
    for entry in driver_entries:
        if "CMD_ARM_XRAY" in entry.message or "TX ->" in entry.message:
            driver_pivot = entry
            break

    mcu_pivot = None
    for entry in mcu_entries:
        if "CMD_ARM_XRAY" in entry.message or "ARM" in entry.message:
            mcu_pivot = entry
            break

    if driver_pivot and mcu_pivot:
        # L'événement au MCU s'est produit quelques millisecondes après le départ du pilote (latence USB ~3ms)
        offset_ms = driver_pivot.timestamp_abs_ms - mcu_pivot.timestamp_abs_ms + 3.0
    elif driver_entries and mcu_entries:
        # Repli : alignement sur le premier événement
        offset_ms = driver_entries[0].timestamp_abs_ms - mcu_entries[0].timestamp_abs_ms

    # 2. Application de l'offset aux entrées MCU
    for entry in mcu_entries:
        entry.timestamp_abs_ms += offset_ms

    # 3. Fusion et tri chronologique
    merged: List[LogEntry] = app_entries + driver_entries + mcu_entries
    merged.sort(key=lambda x: x.timestamp_abs_ms)

    return merged, offset_ms
