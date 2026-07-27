"""Local folder-based scan history for OBD-Insight."""

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from parser import normalize_scan_text, parse_scan_session


DEFAULT_DATA_DIR = Path.home() / "Documents" / "OBD-Insight Data"


@dataclass
class HistorySaveResult:
    """Result of storing one scan in local vehicle history."""

    scan_path: Path
    vehicle_folder: Path
    created: bool


def save_scan_to_history(scan_text, data_dir=None, scanned_at=None):
    """Save a recognizable scan under its vehicle without duplicating it."""
    normalized_text = normalize_scan_text(scan_text).strip()
    session = parse_scan_session(normalized_text)
    if not any((session["vehicle"], session["modules"], session["dtcs"])):
        raise ValueError("No recognizable FORScan scan data was found.")

    data_dir = Path(data_dir) if data_dir else DEFAULT_DATA_DIR
    vehicles_dir = data_dir / "vehicles"
    incoming_dir = data_dir / "incoming"
    vehicle_folder = vehicles_dir / _vehicle_folder_name(session["vehicle"])
    scans_dir = vehicle_folder / "scans"

    incoming_dir.mkdir(parents=True, exist_ok=True)
    scans_dir.mkdir(parents=True, exist_ok=True)
    _write_vehicle_file(vehicle_folder, session["vehicle"])

    content_hash = hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()[:12]
    existing_scans = list(scans_dir.glob(f"*_{content_hash}.txt"))
    if existing_scans:
        return HistorySaveResult(
            scan_path=existing_scans[0],
            vehicle_folder=vehicle_folder,
            created=False,
        )

    scanned_at = scanned_at or datetime.now()
    timestamp = scanned_at.strftime("%Y-%m-%d_%H%M%S")
    scan_path = scans_dir / f"{timestamp}_{content_hash}.txt"
    scan_path.write_text(f"{normalized_text}\n", encoding="utf-8")

    return HistorySaveResult(
        scan_path=scan_path,
        vehicle_folder=vehicle_folder,
        created=True,
    )


def _vehicle_folder_name(vehicle_info):
    vehicle_name = vehicle_info.get("vehicle") or "Unknown Vehicle"
    name_tokens = re.findall(r"[A-Za-z0-9]+", vehicle_name)
    short_name = "-".join(name_tokens[:2]) or "Unknown-Vehicle"

    vin = vehicle_info.get("vin") or ""
    visible_vin = re.sub(r"[^A-Za-z0-9]", "", vin).upper()
    identifier = visible_vin[-5:] if len(visible_vin) >= 5 else ""
    if not identifier:
        identifier = hashlib.sha256(vehicle_name.encode("utf-8")).hexdigest()[:6]

    return f"{short_name}-{identifier}"


def _write_vehicle_file(vehicle_folder, vehicle_info):
    vehicle_file = vehicle_folder / "vehicle.json"
    vehicle_data = {
        "vehicle": vehicle_info.get("vehicle"),
        "vin": vehicle_info.get("vin"),
    }
    vehicle_file.write_text(
        f"{json.dumps(vehicle_data, indent=2)}\n",
        encoding="utf-8",
    )
