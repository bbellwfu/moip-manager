"""SQLite database for MoIP Manager local storage."""
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from contextlib import contextmanager

# Database file location
DB_PATH = Path(__file__).parent.parent / "moip.db"


def get_connection() -> sqlite3.Connection:
    """Get a database connection with row factory."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def get_db():
    """Context manager for database connections."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """Initialize the database schema."""
    with get_db() as conn:
        conn.executescript("""
            -- Devices table: stores all TX/RX with their characteristics
            CREATE TABLE IF NOT EXISTS devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_type TEXT NOT NULL,  -- 'tx' or 'rx'
                device_index INTEGER NOT NULL,  -- The TX/RX number (1-based)
                subtype TEXT DEFAULT 'av',  -- 'av', 'audio', 'videowall' for receivers; 'av', 'audio' for transmitters
                name TEXT,
                icon_type TEXT,  -- Icon identifier (e.g., 'apple', 'roku', 'gaming', etc.)
                mac_address TEXT,
                ip_address TEXT,
                model TEXT,
                firmware TEXT,
                unit_id INTEGER,  -- REST API unit ID
                group_id INTEGER UNIQUE,  -- REST API group_tx/group_rx ID (unique identifier)
                last_seen TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- Config snapshots: point-in-time routing and device names
            CREATE TABLE IF NOT EXISTS config_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                snapshot_data TEXT NOT NULL,  -- JSON blob
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- App settings: shared settings for all users
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- Create indexes for common queries
            CREATE INDEX IF NOT EXISTS idx_devices_type ON devices(device_type);
            CREATE INDEX IF NOT EXISTS idx_devices_mac ON devices(mac_address);
            CREATE INDEX IF NOT EXISTS idx_snapshots_created ON config_snapshots(created_at);
        """)


def upsert_device(
    device_type: str,
    device_index: int,
    group_id: int,
    subtype: str = 'av',
    name: Optional[str] = None,
    icon_type: Optional[str] = None,
    mac_address: Optional[str] = None,
    ip_address: Optional[str] = None,
    model: Optional[str] = None,
    firmware: Optional[str] = None,
    unit_id: Optional[int] = None
):
    """Insert or update a device record. Uses group_id as unique key."""
    with get_db() as conn:
        conn.execute("""
            INSERT INTO devices (device_type, device_index, subtype, name, icon_type, mac_address, ip_address,
                                 model, firmware, unit_id, group_id, last_seen, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT(group_id) DO UPDATE SET
                device_type = excluded.device_type,
                device_index = excluded.device_index,
                subtype = excluded.subtype,
                name = COALESCE(excluded.name, devices.name),
                icon_type = COALESCE(excluded.icon_type, devices.icon_type),
                mac_address = COALESCE(excluded.mac_address, devices.mac_address),
                ip_address = COALESCE(excluded.ip_address, devices.ip_address),
                model = COALESCE(excluded.model, devices.model),
                firmware = COALESCE(excluded.firmware, devices.firmware),
                unit_id = COALESCE(excluded.unit_id, devices.unit_id),
                last_seen = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
        """, (device_type, device_index, subtype, name, icon_type, mac_address, ip_address,
              model, firmware, unit_id, group_id))


def get_all_devices(device_type: Optional[str] = None) -> list[dict]:
    """Get all devices, optionally filtered by type."""
    with get_db() as conn:
        if device_type:
            rows = conn.execute(
                "SELECT * FROM devices WHERE device_type = ? ORDER BY device_index",
                (device_type,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM devices ORDER BY device_type, device_index"
            ).fetchall()
        return [dict(row) for row in rows]


def get_device(device_type: str, device_index: int) -> Optional[dict]:
    """Get a specific device."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM devices WHERE device_type = ? AND device_index = ?",
            (device_type, device_index)
        ).fetchone()
        return dict(row) if row else None


def set_device_icon(device_type: str, device_index: int, icon_type: str) -> bool:
    """Set the icon type for a device."""
    with get_db() as conn:
        cursor = conn.execute(
            """UPDATE devices SET icon_type = ?, updated_at = CURRENT_TIMESTAMP
               WHERE device_type = ? AND device_index = ?""",
            (icon_type, device_type, device_index)
        )
        return cursor.rowcount > 0


def get_device_icons() -> dict:
    """Get icon types for all devices as a dict of {device_type}_{device_index}: icon_type."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT device_type, device_index, icon_type FROM devices WHERE icon_type IS NOT NULL"
        ).fetchall()
        return {f"{row['device_type']}_{row['device_index']}": row['icon_type'] for row in rows}


def save_snapshot(name: str, snapshot_data: dict, description: Optional[str] = None) -> int:
    """Save a configuration snapshot."""
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO config_snapshots (name, description, snapshot_data) VALUES (?, ?, ?)",
            (name, description, json.dumps(snapshot_data))
        )
        return cursor.lastrowid


def get_snapshots() -> list[dict]:
    """Get all configuration snapshots."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, name, description, created_at FROM config_snapshots ORDER BY created_at DESC"
        ).fetchall()
        return [dict(row) for row in rows]


def get_snapshot(snapshot_id: int) -> Optional[dict]:
    """Get a specific snapshot with full data."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM config_snapshots WHERE id = ?",
            (snapshot_id,)
        ).fetchone()
        if row:
            result = dict(row)
            result['snapshot_data'] = json.loads(result['snapshot_data'])
            return result
        return None


def delete_snapshot(snapshot_id: int) -> bool:
    """Delete a snapshot."""
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM config_snapshots WHERE id = ?", (snapshot_id,))
        return cursor.rowcount > 0


def get_latest_snapshot() -> Optional[dict]:
    """Get the most recent snapshot."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM config_snapshots ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        if row:
            result = dict(row)
            result['snapshot_data'] = json.loads(result['snapshot_data'])
            return result
        return None


# --- App Settings ---

def get_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    """Get an app setting by key."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT value FROM app_settings WHERE key = ?",
            (key,)
        ).fetchone()
        return row['value'] if row else default


def set_setting(key: str, value: str) -> None:
    """Set an app setting."""
    with get_db() as conn:
        conn.execute("""
            INSERT INTO app_settings (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = CURRENT_TIMESTAMP
        """, (key, value))


def get_all_settings() -> dict:
    """Get all app settings as a dictionary."""
    with get_db() as conn:
        rows = conn.execute("SELECT key, value FROM app_settings").fetchall()
        return {row['key']: row['value'] for row in rows}


def set_settings(settings: dict) -> None:
    """Set multiple app settings at once."""
    for key, value in settings.items():
        set_setting(key, value)


def migrate_db():
    """Run database migrations."""
    with get_db() as conn:
        # Check existing columns
        cursor = conn.execute("PRAGMA table_info(devices)")
        columns = [row[1] for row in cursor.fetchall()]

        # Add icon_type column if missing
        if 'icon_type' not in columns:
            conn.execute("ALTER TABLE devices ADD COLUMN icon_type TEXT")

        # Add subtype column if missing (for AV/Audio/VideoWall distinction)
        if 'subtype' not in columns:
            conn.execute("ALTER TABLE devices ADD COLUMN subtype TEXT DEFAULT 'av'")

        # Add resolution and hdcp columns for receiver video settings cache
        if 'resolution' not in columns:
            conn.execute("ALTER TABLE devices ADD COLUMN resolution TEXT")

        if 'hdcp' not in columns:
            conn.execute("ALTER TABLE devices ADD COLUMN hdcp TEXT")


# --- Receiver Video Settings Cache ---

def cache_receiver_video_settings(rx_index: int, resolution: str, hdcp: str) -> None:
    """Cache receiver video settings (resolution, HDCP) for quick loading."""
    with get_db() as conn:
        conn.execute("""
            UPDATE devices SET resolution = ?, hdcp = ?, updated_at = CURRENT_TIMESTAMP
            WHERE device_type = 'rx' AND device_index = ?
        """, (resolution, hdcp, rx_index))


def get_cached_receiver_video_settings() -> dict:
    """Get cached video settings for all receivers as {rx_id: {resolution, hdcp}}."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT device_index, resolution, hdcp FROM devices
            WHERE device_type = 'rx' AND (resolution IS NOT NULL OR hdcp IS NOT NULL)
        """).fetchall()
        return {
            row['device_index']: {
                'resolution': row['resolution'],
                'hdcp': row['hdcp']
            }
            for row in rows
        }


# Initialize database on module import
init_db()
migrate_db()
