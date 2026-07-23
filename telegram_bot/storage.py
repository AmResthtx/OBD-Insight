"""SQLite-backed scan history and premium status for the Telegram bot."""

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path


def _connect(db_path):
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            vehicle_key TEXT NOT NULL,
            scanned_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS dtc_observations (
            session_id INTEGER NOT NULL,
            module TEXT NOT NULL,
            code TEXT NOT NULL,
            FOREIGN KEY(session_id) REFERENCES sessions(id)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            premium_until TEXT
        )
        """
    )
    return conn


def record_scan(db_path, user_id, vehicle_key, dtcs):
    """Store one scan session and tag each DTC as new, repeated, or returning.

    - new: never observed before for this user+vehicle.
    - repeated: present in this scan and the immediately previous scan.
    - returning: seen before, absent from the immediately previous scan,
      then present again (i.e. it looked cleared and came back).
    """
    conn = _connect(db_path)
    try:
        previous_session_ids = [
            row[0]
            for row in conn.execute(
                "SELECT id FROM sessions WHERE user_id = ? AND vehicle_key = ? ORDER BY scanned_at",
                (user_id, vehicle_key),
            ).fetchall()
        ]
        last_session_id = previous_session_ids[-1] if previous_session_ids else None

        ever_seen = set()
        last_seen = set()
        if previous_session_ids:
            placeholders = ",".join("?" * len(previous_session_ids))
            rows = conn.execute(
                f"SELECT session_id, module, code FROM dtc_observations WHERE session_id IN ({placeholders})",
                previous_session_ids,
            ).fetchall()
            for session_id, module, code in rows:
                ever_seen.add((module, code))
                if session_id == last_session_id:
                    last_seen.add((module, code))

        scanned_at = datetime.now(timezone.utc).isoformat()
        new_session_id = conn.execute(
            "INSERT INTO sessions (user_id, vehicle_key, scanned_at) VALUES (?, ?, ?)",
            (user_id, vehicle_key, scanned_at),
        ).lastrowid

        tracked = []
        for dtc in dtcs:
            key = (dtc["module"], dtc["code"])
            if key not in ever_seen:
                status = "new"
            elif key in last_seen:
                status = "repeated"
            else:
                status = "returning"

            conn.execute(
                "INSERT INTO dtc_observations (session_id, module, code) VALUES (?, ?, ?)",
                (new_session_id, dtc["module"], dtc["code"]),
            )
            tracked.append({**dtc, "status": status})

        conn.commit()
        return tracked
    finally:
        conn.close()


def set_premium(db_path, user_id, days=30):
    """Mark a user premium for the given number of days from now."""
    conn = _connect(db_path)
    try:
        premium_until = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()
        conn.execute(
            "INSERT INTO users (user_id, premium_until) VALUES (?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET premium_until = excluded.premium_until",
            (user_id, premium_until),
        )
        conn.commit()
    finally:
        conn.close()


def is_premium(db_path, user_id):
    """Return whether a user currently has an active premium subscription."""
    conn = _connect(db_path)
    try:
        row = conn.execute(
            "SELECT premium_until FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
        if not row or not row[0]:
            return False
        return datetime.fromisoformat(row[0]) > datetime.now(timezone.utc)
    finally:
        conn.close()
