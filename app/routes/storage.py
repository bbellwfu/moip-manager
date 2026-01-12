"""Storage and snapshot API routes."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app import database as db
from app import sync

router = APIRouter()


class SnapshotCreate(BaseModel):
    """Request to create a snapshot."""
    name: str
    description: Optional[str] = None


class SnapshotRestore(BaseModel):
    """Request to restore a snapshot."""
    restore_routing: bool = True
    restore_names: bool = True


# --- Device Inventory Endpoints ---

@router.get("/inventory")
async def get_inventory():
    """Get all devices from local inventory."""
    devices = db.get_all_devices()
    transmitters = [d for d in devices if d['device_type'] == 'tx']
    receivers = [d for d in devices if d['device_type'] == 'rx']
    return {
        "transmitters": transmitters,
        "receivers": receivers,
        "total": len(devices)
    }


@router.get("/inventory/{device_type}/{device_index}")
async def get_device_details(device_type: str, device_index: int):
    """Get details for a specific device."""
    if device_type not in ('tx', 'rx'):
        raise HTTPException(status_code=400, detail="device_type must be 'tx' or 'rx'")

    device = db.get_device(device_type, device_index)
    if not device:
        raise HTTPException(status_code=404, detail=f"Device {device_type.upper()}{device_index} not found")

    return device


@router.post("/sync")
async def trigger_sync():
    """Trigger a sync of device data from the controller."""
    success = sync.sync_devices()
    if success:
        return {"success": True, "message": "Device sync completed"}
    else:
        raise HTTPException(status_code=500, detail="Device sync failed")


# --- Snapshot Endpoints ---

@router.get("/snapshots")
async def list_snapshots():
    """List all configuration snapshots."""
    snapshots = db.get_snapshots()
    return {"snapshots": snapshots}


@router.post("/snapshots")
async def create_snapshot(request: SnapshotCreate):
    """Create a new configuration snapshot."""
    try:
        # Ensure we have latest device data
        sync.sync_devices()

        snapshot_id = sync.create_config_snapshot(request.name, request.description)
        return {"success": True, "snapshot_id": snapshot_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/snapshots/{snapshot_id}")
async def get_snapshot(snapshot_id: int):
    """Get a specific snapshot with full data."""
    snapshot = db.get_snapshot(snapshot_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail=f"Snapshot {snapshot_id} not found")
    return snapshot


@router.post("/snapshots/{snapshot_id}/restore")
async def restore_snapshot(snapshot_id: int, request: SnapshotRestore):
    """Restore configuration from a snapshot."""
    try:
        results = sync.restore_config_snapshot(
            snapshot_id,
            restore_routing=request.restore_routing,
            restore_names=request.restore_names
        )
        return {
            "success": True,
            "routing_restored": results['routing_restored'],
            "names_restored": results['names_restored'],
            "errors": results['errors']
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/snapshots/{snapshot_id}")
async def delete_snapshot(snapshot_id: int):
    """Delete a snapshot."""
    if db.delete_snapshot(snapshot_id):
        return {"success": True}
    else:
        raise HTTPException(status_code=404, detail=f"Snapshot {snapshot_id} not found")


# --- App Settings Endpoints ---

# Default settings values - credentials should be configured via web UI or .env
DEFAULT_SETTINGS = {
    "controller_ip": "",
    "telnet_port": "23",
    "api_port": "443",
    "username": "",
    "password": "",
    "refresh_interval": "0",
    "quick_buttons": "5",
    "default_tab": "dashboard",
    "verify_ssl": "false",
    "timeout": "10"
}


@router.get("/settings")
async def get_settings():
    """Get all app settings with defaults."""
    stored = db.get_all_settings()
    # Merge with defaults (stored values override defaults)
    settings = {**DEFAULT_SETTINGS, **stored}
    # Don't return the actual password, just indicate if it's set
    if "password" in stored and stored["password"]:
        settings["password_set"] = True
        settings["password"] = ""  # Don't expose password
    else:
        settings["password_set"] = False
        settings["password"] = ""
    return settings


@router.put("/settings")
async def update_settings(settings: dict):
    """Update app settings."""
    # Filter out empty password (don't overwrite if not provided)
    if "password" in settings and not settings["password"]:
        del settings["password"]
    # Convert booleans to strings for storage
    for key, value in settings.items():
        if isinstance(value, bool):
            settings[key] = str(value).lower()
        elif isinstance(value, int):
            settings[key] = str(value)
    db.set_settings(settings)
    return {"success": True}


@router.post("/settings/test")
async def test_connection():
    """Test connection to the MoIP controller."""
    import socket
    from moip import MoIPClient, MoIPAPIClient

    stored = db.get_all_settings()
    settings = {**DEFAULT_SETTINGS, **stored}

    results = {
        "telnet": {"success": False, "message": ""},
        "api": {"success": False, "message": ""}
    }

    # Test telnet connection
    try:
        host = settings.get("controller_ip", "")
        port = int(settings.get("telnet_port", 23))
        timeout = int(settings.get("timeout", 10))

        client = MoIPClient(host, port, timeout)
        counts = client.get_device_counts()
        results["telnet"]["success"] = True
        results["telnet"]["message"] = f"Connected! Found {counts.tx_count} TX, {counts.rx_count} RX"
    except socket.timeout:
        results["telnet"]["message"] = "Connection timed out"
    except ConnectionRefusedError:
        results["telnet"]["message"] = "Connection refused"
    except Exception as e:
        results["telnet"]["message"] = str(e)

    # Test REST API connection
    try:
        host = settings.get("controller_ip", "")
        port = int(settings.get("api_port", 443))
        username = settings.get("username", "")
        password = settings.get("password", "")
        verify_ssl = settings.get("verify_ssl", "false").lower() == "true"
        timeout = int(settings.get("timeout", 10))

        api_client = MoIPAPIClient(
            host=host,
            username=username,
            password=password,
            port=port,
            verify_ssl=verify_ssl
        )
        # Try to get system info (requires auth)
        info = api_client.get_system_info()
        results["api"]["success"] = True
        results["api"]["message"] = f"Authenticated! API version: {info.get('kind', 'unknown')}"
    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg:
            results["api"]["message"] = "Authentication failed - check username/password"
        elif "connection" in error_msg.lower() or "timeout" in error_msg.lower():
            results["api"]["message"] = "Connection failed - check IP and port"
        else:
            results["api"]["message"] = error_msg

    return results
