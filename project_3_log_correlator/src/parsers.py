"""
Parsers de logs multi-formats pour systèmes d'imagerie médicale.
Gère les logs applicatifs Windows/Qt, les logs de pilotes C++ et les traces microcontrôleur.
"""

import re
from typing import List, Optional
from .models import LogEntry, LogLevel, Subsystem

QT_LOG_REGEX = re.compile(
    r"^\d{4}-\d{2}-\d{2}\s+(\d{2}):(\d{2}):(\d{2})\.(\d{3})\s+\[(\w+)\]\s+\[(\w+)\]\s+([\w\.\-]+)\s+-\s+(.*)$"
)

DRIVER_LOG_REGEX = re.compile(
    r"^\[(\d{2}):(\d{2}):(\d{2})\.(\d{3})\]\s+\[\d+:\d+\]\s+\[([\w_]+)\]\s+(.*)$"
)

MCU_LOG_REGEX = re.compile(
    r"^\[T\+(\d+)\]\s+\[([\w_]+)\]\s+(?:(\w+):\s+)?(.*)$"
)


def _to_day_ms(h: int, m: int, s: int, ms: int) -> float:
    return float(h * 3600000 + m * 60000 + s * 1000 + ms)


def _map_log_level(level_str: str) -> LogLevel:
    lvl = level_str.upper()
    if "CRIT" in lvl:
        return LogLevel.CRITICAL
    elif "ERR" in lvl:
        return LogLevel.ERROR
    elif "WARN" in lvl:
        return LogLevel.WARN
    elif "DEBUG" in lvl:
        return LogLevel.DEBUG
    return LogLevel.INFO


def parse_qt_log(lines: List[str]) -> List[LogEntry]:
    entries = []
    for line in lines:
        line_clean = line.strip()
        if not line_clean:
            continue
        m = QT_LOG_REGEX.match(line_clean)
        if m:
            h, m_min, s, ms, lvl, thread, module, msg = m.groups()
            abs_ms = _to_day_ms(int(h), int(m_min), int(s), int(ms))
            level = _map_log_level(lvl)
            is_anomaly = level in (LogLevel.ERROR, LogLevel.CRITICAL)
            entries.append(
                LogEntry(
                    subsystem=Subsystem.GUI_PC,
                    timestamp_raw=f"{h}:{m_min}:{s}.{ms}",
                    timestamp_abs_ms=abs_ms,
                    level=level,
                    module=f"{thread}/{module}",
                    message=msg,
                    is_anomaly=is_anomaly,
                    raw_line=line_clean,
                )
            )
    return entries


def parse_driver_log(lines: List[str]) -> List[LogEntry]:
    entries = []
    for line in lines:
        line_clean = line.strip()
        if not line_clean:
            continue
        m = DRIVER_LOG_REGEX.match(line_clean)
        if m:
            h, m_min, s, ms, subsys, msg = m.groups()
            abs_ms = _to_day_ms(int(h), int(m_min), int(s), int(ms))

            level = LogLevel.INFO
            if "expired" in msg.lower() or "breakdown" in msg.lower() or "error" in msg.lower():
                level = LogLevel.ERROR
            elif "trip" in msg.lower() or "warn" in msg.lower():
                level = LogLevel.WARN
            elif "debug" in msg.lower() or "tx ->" in msg.lower() or "rx <-" in msg.lower():
                level = LogLevel.DEBUG

            is_anomaly = level in (LogLevel.ERROR, LogLevel.CRITICAL) or "SAFETY_TRIP" in msg
            entries.append(
                LogEntry(
                    subsystem=Subsystem.DRIVER_CPP,
                    timestamp_raw=f"{h}:{m_min}:{s}.{ms}",
                    timestamp_abs_ms=abs_ms,
                    level=level,
                    module=subsys,
                    message=msg,
                    is_anomaly=is_anomaly,
                    raw_line=line_clean,
                )
            )
    return entries


def parse_mcu_log(lines: List[str]) -> List[LogEntry]:
    entries = []
    for line in lines:
        line_clean = line.strip()
        if not line_clean:
            continue
        m = MCU_LOG_REGEX.match(line_clean)
        if m:
            t_ms, module, lvl_candidate, msg = m.groups()
            level = LogLevel.INFO
            if lvl_candidate:
                level = _map_log_level(lvl_candidate)
            elif "warn" in msg.lower() or "spike" in msg.lower():
                level = LogLevel.WARN
            elif "critical" in msg.lower() or "trip" in msg.lower():
                level = LogLevel.CRITICAL

            is_anomaly = level in (LogLevel.ERROR, LogLevel.CRITICAL, LogLevel.WARN) and (
                "spike" in msg.lower() or "trip" in msg.lower() or "halt" in msg.lower()
            )

            entries.append(
                LogEntry(
                    subsystem=Subsystem.FIRMWARE_MCU,
                    timestamp_raw=f"T+{t_ms}",
                    timestamp_abs_ms=float(t_ms),  # Temps relatif temporaire avant synchronisation
                    level=level,
                    module=module,
                    message=msg,
                    is_anomaly=is_anomaly,
                    raw_line=line_clean,
                )
            )
    return entries
