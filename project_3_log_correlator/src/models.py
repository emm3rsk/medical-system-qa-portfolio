"""
Modèles de données pour l'analyse, la corrélation et le diagnostic de logs multi-niveaux.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class Subsystem(str, Enum):
    GUI_PC = "GUI (Qt)"
    DRIVER_CPP = "PILOTE (C++)"
    FIRMWARE_MCU = "FIRMWARE (MCU)"
    HARDWARE = "MATÉRIEL"


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class LogEntry:
    subsystem: Subsystem
    timestamp_raw: str
    timestamp_abs_ms: float
    level: LogLevel
    module: str
    message: str
    is_anomaly: bool = False
    raw_line: str = ""

    @property
    def formatted_time(self) -> str:
        """Retourne HH:MM:SS.mmm à partir des millisecondes du jour."""
        total_seconds = self.timestamp_abs_ms / 1000.0
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = total_seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:06.3f}"


@dataclass
class RCAFinding:
    root_cause_entry: LogEntry
    faulty_subsystem: Subsystem
    severity_level: str
    category: str
    clinical_impact: str
    technical_summary: str
    recommendations: List[str] = field(default_factory=list)


@dataclass
class DefectTicket:
    title: str
    component: str
    severity: str
    iec62304_risk_class: str
    timeline: List[LogEntry]
    rca: RCAFinding
