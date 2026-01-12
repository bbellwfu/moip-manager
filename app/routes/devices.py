"""Device management API routes."""
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional

import config
from moip import MoIPClient, MoIPAPIClient
from moip.models import Transmitter, Receiver, DeviceCounts, DeviceNameUpdate, SystemStatus
from app import database as db

router = APIRouter()


class VideoStats(BaseModel):
    """Video statistics for a transmitter."""
    tx_id: int
    resolution: Optional[str] = None
    frame_rate: Optional[str] = None
    color_depth: Optional[str] = None
    hdcp: Optional[bool] = None
    signal_type: Optional[str] = None
    state: Optional[str] = None
    has_signal: bool = False


class DeviceIconUpdate(BaseModel):
    """Request to update device icon."""
    icon_type: str


def get_telnet_client() -> MoIPClient:
    """Get a MoIP telnet client with current settings."""
    settings = config.get_moip_settings()
    return MoIPClient(
        settings["host"],
        settings["telnet_port"],
        settings["timeout"]
    )


def get_api_client() -> MoIPAPIClient:
    """Get a MoIP API client with current settings."""
    settings = config.get_moip_settings()
    return MoIPAPIClient(
        host=settings["host"],
        username=settings["username"],
        password=settings["password"],
        port=settings["api_port"],
        verify_ssl=settings["verify_ssl"]
    )


class DevicesResponse(BaseModel):
    """Response containing all devices."""
    transmitters: list[Transmitter]
    receivers: list[Receiver]
    counts: DeviceCounts


@router.get("/devices", response_model=DevicesResponse)
async def get_all_devices():
    """Get all transmitters and receivers with status."""
    telnet_client = get_telnet_client()
    api_client = get_api_client()

    try:
        # Get device counts and routing from telnet (fast)
        counts = telnet_client.get_device_counts()
        routing = telnet_client.get_routing()

        # Build routing maps
        rx_to_tx = {entry.rx: entry.tx for entry in routing}
        tx_rx_counts = {}
        for entry in routing:
            if entry.tx > 0:
                tx_rx_counts[entry.tx] = tx_rx_counts.get(entry.tx, 0) + 1

        # Get names from REST API (authoritative source)
        tx_groups = api_client.get_all_group_tx_detailed()
        rx_groups = api_client.get_all_group_rx_detailed()

        # Get unit details for model detection
        units = api_client.get_all_units_detailed()
        unit_by_id = {u.get('id'): u for u in units}

        # Build name maps from group data
        tx_names = {}
        for g in tx_groups:
            idx = g.get("settings", {}).get("index")
            name = g.get("settings", {}).get("name", f"Tx{idx}")
            if idx is not None:
                tx_names[idx] = name

        # Helper to detect device subtype (based on associated unit model)
        def get_subtype(group):
            unit_id = group.get('associations', {}).get('unit')
            if unit_id and unit_id in unit_by_id:
                model = unit_by_id[unit_id].get('status', {}).get('model', '')
                if '-a-rx' in model.lower() or '-a-tx' in model.lower():
                    return 'audio'
            # TODO: detect videowall when we have better API support
            return 'av'

        # Helper to check if device is online (has valid IP, not 0.0.0.0)
        def is_online(group):
            unit_id = group.get('associations', {}).get('unit')
            if unit_id and unit_id in unit_by_id:
                ip = unit_by_id[unit_id].get('status', {}).get('ip', '')
                return ip and ip != '0.0.0.0'
            return False

        # Build transmitter list from all group_tx entries
        def tx_sort_key(g):
            idx = g.get("settings", {}).get("index") or 999
            subtype = get_subtype(g)
            subtype_order = 0 if subtype == 'av' else 1
            return (idx, subtype_order)

        sorted_tx_groups = sorted(tx_groups, key=tx_sort_key)

        transmitters = []
        for group in sorted_tx_groups:
            idx = group.get("settings", {}).get("index")
            if idx is None:
                continue

            name = group.get("settings", {}).get("name", f"Tx{idx}")
            subtype = get_subtype(group)
            online = is_online(group)
            group_id = group.get("id")
            rx_count = tx_rx_counts.get(idx, 0)

            transmitters.append(Transmitter(
                id=idx,
                name=name,
                subtype=subtype,
                is_online=online,
                group_id=group_id,
                receiver_count=rx_count,
                status="streaming" if rx_count > 0 else "idle"
            ))

        # Build receiver list from all group_rx entries (not just one per index)
        # Sort by index, then by subtype (av first, then audio) for consistent ordering
        def rx_sort_key(g):
            idx = g.get("settings", {}).get("index") or 999
            subtype = get_subtype(g)
            subtype_order = 0 if subtype == 'av' else 1  # AV first
            return (idx, subtype_order)

        sorted_rx_groups = sorted(rx_groups, key=rx_sort_key)

        # Track how many devices we've seen at each index (for differentiating duplicates)
        index_counts = {}

        receivers = []
        for group in sorted_rx_groups:
            idx = group.get("settings", {}).get("index")
            if idx is None:
                continue

            name = group.get("settings", {}).get("name", f"Rx{idx}")
            subtype = get_subtype(group)
            group_id = group.get("id")

            # Track duplicates at same index
            if idx not in index_counts:
                index_counts[idx] = 0
            index_counts[idx] += 1

            current_tx = rx_to_tx.get(idx, 0)
            receivers.append(Receiver(
                id=idx,
                name=name,
                subtype=subtype,
                group_id=group_id,
                current_tx=current_tx if current_tx > 0 else None,
                current_tx_name=tx_names.get(current_tx) if current_tx > 0 else None,
                status="streaming" if current_tx > 0 else "idle"
            ))

        return DevicesResponse(
            transmitters=transmitters,
            receivers=receivers,
            counts=counts
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/transmitters", response_model=list[Transmitter])
async def get_transmitters():
    """Get all transmitters."""
    telnet_client = get_telnet_client()
    api_client = get_api_client()

    try:
        counts = telnet_client.get_device_counts()
        routing = telnet_client.get_routing()

        # Count receivers per transmitter
        tx_rx_counts = {}
        for entry in routing:
            if entry.tx > 0:
                tx_rx_counts[entry.tx] = tx_rx_counts.get(entry.tx, 0) + 1

        # Get names from REST API
        tx_groups = api_client.get_all_group_tx_detailed()
        tx_names = {}
        for g in tx_groups:
            idx = g.get("settings", {}).get("index")
            name = g.get("settings", {}).get("name", f"Tx{idx}")
            if idx is not None:
                tx_names[idx] = name

        transmitters = []
        for i in range(1, counts.tx_count + 1):
            rx_count = tx_rx_counts.get(i, 0)
            transmitters.append(Transmitter(
                id=i,
                name=tx_names.get(i, f"Tx{i}"),
                receiver_count=rx_count,
                status="streaming" if rx_count > 0 else "idle"
            ))
        return transmitters
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/receivers", response_model=list[Receiver])
async def get_receivers():
    """Get all receivers."""
    telnet_client = get_telnet_client()
    api_client = get_api_client()

    try:
        counts = telnet_client.get_device_counts()
        routing = telnet_client.get_routing()
        rx_to_tx = {entry.rx: entry.tx for entry in routing}

        # Get names from REST API
        tx_groups = api_client.get_all_group_tx_detailed()
        rx_groups = api_client.get_all_group_rx_detailed()

        tx_names = {}
        for g in tx_groups:
            idx = g.get("settings", {}).get("index")
            name = g.get("settings", {}).get("name", f"Tx{idx}")
            if idx is not None:
                tx_names[idx] = name

        rx_names = {}
        for g in rx_groups:
            idx = g.get("settings", {}).get("index")
            name = g.get("settings", {}).get("name", f"Rx{idx}")
            if idx is not None:
                rx_names[idx] = name

        receivers = []
        for i in range(1, counts.rx_count + 1):
            current_tx = rx_to_tx.get(i, 0)
            receivers.append(Receiver(
                id=i,
                name=rx_names.get(i, f"Rx{i}"),
                current_tx=current_tx if current_tx > 0 else None,
                current_tx_name=tx_names.get(current_tx) if current_tx > 0 else None,
                status="streaming" if current_tx > 0 else "idle"
            ))
        return receivers
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status", response_model=SystemStatus)
async def get_system_status():
    """Get overall system status."""
    client = get_telnet_client()
    try:
        counts = client.get_device_counts()
        routing = client.get_routing()

        # Count active streams (receivers with tx > 0)
        active_streams = sum(1 for r in routing if r.tx > 0)

        return SystemStatus(
            connected=True,
            tx_count=counts.tx_count,
            rx_count=counts.rx_count,
            active_streams=active_streams,
            controller_ip=config.get_moip_settings()["host"]
        )
    except Exception as e:
        return SystemStatus(
            connected=False,
            tx_count=0,
            rx_count=0,
            active_streams=0,
            controller_ip=config.get_moip_settings()["host"]
        )


@router.get("/devices/detailed")
async def get_devices_detailed():
    """Get detailed device information from REST API."""
    api_client = get_api_client()
    try:
        units = api_client.get_all_units_detailed()
        return {"units": units}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/controller/info")
async def get_controller_info():
    """Get detailed controller information."""
    api_client = get_api_client()
    telnet_client = get_telnet_client()

    try:
        # Get comprehensive info from REST API v1.3
        base_info = api_client.get_base_info()
        stats = api_client.get_base_stats()
        lan_info = api_client.get_lan_info()
        firmware_info = api_client.get_firmware_info()

        # Get device counts from telnet
        counts = telnet_client.get_device_counts()

        return {
            "base": base_info,
            "stats": stats,
            "lan": lan_info,
            "firmware": firmware_info,
            "device_counts": {
                "transmitters": counts.tx_count,
                "receivers": counts.rx_count
            },
            "controller_ip": config.get_moip_settings()["host"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/receivers/{rx_id}/name")
async def set_receiver_name(rx_id: int, update: DeviceNameUpdate):
    """
    Set receiver name.

    Note: This requires finding the group_rx ID for the given rx_id.
    """
    api_client = get_api_client()
    telnet_client = get_telnet_client()

    try:
        # Find the group_rx with matching index
        groups = api_client.get_all_group_rx_detailed()
        target_group = None
        for group in groups:
            if group.get("settings", {}).get("index") == rx_id:
                target_group = group
                break

        if not target_group:
            raise HTTPException(status_code=404, detail=f"Receiver {rx_id} not found")

        # Set the name on the controller
        api_client.set_group_rx_name(target_group["id"], update.name)

        # Also update the unit name if we can find it
        unit_id = target_group.get("associations", {}).get("unit")
        if unit_id:
            api_client.set_unit_name(unit_id, update.name)

        # Update local database
        db.upsert_device(
            device_type='rx',
            device_index=rx_id,
            name=update.name,
            group_id=target_group["id"],
            unit_id=unit_id
        )

        return {"success": True, "rx_id": rx_id, "name": update.name}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/transmitters/{tx_id}/name")
async def set_transmitter_name(tx_id: int, update: DeviceNameUpdate):
    """
    Set transmitter name.

    Note: This requires finding the group_tx ID for the given tx_id.
    """
    api_client = get_api_client()

    try:
        # Find the group_tx with matching index
        groups = api_client.get_all_group_tx_detailed()
        target_group = None
        for group in groups:
            if group.get("settings", {}).get("index") == tx_id:
                target_group = group
                break

        if not target_group:
            raise HTTPException(status_code=404, detail=f"Transmitter {tx_id} not found")

        # Set the name on the controller
        api_client.set_group_tx_name(target_group["id"], update.name)

        # Also update the unit name if we can find it
        unit_id = target_group.get("associations", {}).get("unit")
        if unit_id:
            api_client.set_unit_name(unit_id, update.name)

        # Update local database
        db.upsert_device(
            device_type='tx',
            device_index=tx_id,
            name=update.name,
            group_id=target_group["id"],
            unit_id=unit_id
        )

        return {"success": True, "tx_id": tx_id, "name": update.name}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/device-icons")
async def get_device_icons():
    """Get all device icon assignments."""
    return db.get_device_icons()


@router.put("/transmitters/{tx_id}/icon")
async def set_transmitter_icon(tx_id: int, update: DeviceIconUpdate):
    """Set the icon type for a transmitter."""
    # First ensure the device exists in the database
    device = db.get_device('tx', tx_id)
    if not device:
        # Create a basic entry if it doesn't exist
        db.upsert_device(device_type='tx', device_index=tx_id, icon_type=update.icon_type)
    else:
        db.set_device_icon('tx', tx_id, update.icon_type)
    return {"success": True, "tx_id": tx_id, "icon_type": update.icon_type}


@router.put("/receivers/{rx_id}/icon")
async def set_receiver_icon(rx_id: int, update: DeviceIconUpdate):
    """Set the icon type for a receiver."""
    device = db.get_device('rx', rx_id)
    if not device:
        db.upsert_device(device_type='rx', device_index=rx_id, icon_type=update.icon_type)
    else:
        db.set_device_icon('rx', rx_id, update.icon_type)
    return {"success": True, "rx_id": rx_id, "icon_type": update.icon_type}


@router.get("/transmitters/{tx_id}/video", response_model=VideoStats)
async def get_transmitter_video_stats(tx_id: int):
    """Get video statistics for a transmitter."""
    api_client = get_api_client()

    try:
        video_data = api_client.get_video_tx(tx_id)

        # Check for error (no video_tx for this transmitter)
        if video_data.get("error"):
            return VideoStats(tx_id=tx_id, has_signal=False)

        status = video_data.get("status", {})

        # Resolution comes as a string like "3840x2160"
        resolution = status.get("resolution")

        # Check if there's an active signal
        state = status.get("state", "")
        has_signal = state.lower() == "streaming" if state else False

        # HDCP comes as a string like "2.2", convert to bool for display
        hdcp_val = status.get("hdcp")
        hdcp = hdcp_val is not None and hdcp_val != "none"

        return VideoStats(
            tx_id=tx_id,
            resolution=resolution,
            frame_rate=status.get("frame_rate"),
            color_depth=status.get("color_depth"),
            hdcp=hdcp,
            signal_type=status.get("signal_type"),
            state=state,
            has_signal=has_signal
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/transmitters/{tx_id}/preview")
async def get_transmitter_preview(tx_id: int):
    """Get JPEG preview thumbnail for a transmitter."""
    api_client = get_api_client()

    try:
        image_bytes = api_client.get_video_tx_preview(tx_id)
        return Response(
            content=image_bytes,
            media_type="image/jpeg",
            headers={"Cache-Control": "no-cache"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/transmitters/video/all")
async def get_all_transmitter_video_stats():
    """Get video statistics for all transmitters (fetched in parallel)."""
    import asyncio
    from concurrent.futures import ThreadPoolExecutor

    telnet_client = get_telnet_client()
    api_client = get_api_client()

    try:
        counts = telnet_client.get_device_counts()

        def fetch_video_stat(tx_id: int) -> VideoStats:
            """Fetch video stats for a single transmitter."""
            try:
                video_data = api_client.get_video_tx(tx_id)

                # Check for error (no video_tx for this transmitter)
                if video_data.get("error"):
                    return VideoStats(tx_id=tx_id, has_signal=False)

                status = video_data.get("status", {})
                resolution = status.get("resolution")
                state = status.get("state", "")
                has_signal = state.lower() == "streaming" if state else False

                hdcp_val = status.get("hdcp")
                hdcp = hdcp_val is not None and hdcp_val != "none"

                return VideoStats(
                    tx_id=tx_id,
                    resolution=resolution,
                    frame_rate=status.get("frame_rate"),
                    color_depth=status.get("color_depth"),
                    hdcp=hdcp,
                    signal_type=status.get("signal_type"),
                    state=state,
                    has_signal=has_signal
                )
            except Exception:
                return VideoStats(tx_id=tx_id, has_signal=False)

        # Fetch all video stats in parallel using a thread pool
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=10) as executor:
            tx_ids = list(range(1, counts.tx_count + 1))
            stats = await loop.run_in_executor(
                None,
                lambda: list(executor.map(fetch_video_stat, tx_ids))
            )

        return {"stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ReceiverVideoSettings(BaseModel):
    """Video settings for a receiver."""
    rx_id: int
    resolution: Optional[str] = None
    supported_resolutions: list[str] = []
    hdcp: Optional[str] = None
    supported_hdcp: list[str] = []
    state: Optional[str] = None


class ResolutionUpdate(BaseModel):
    """Request to update receiver resolution."""
    resolution: str


class HdcpUpdate(BaseModel):
    """Request to update receiver HDCP mode."""
    hdcp: str


@router.get("/receivers/{rx_id}/video", response_model=ReceiverVideoSettings)
async def get_receiver_video_settings(rx_id: int):
    """Get video settings for a receiver including resolution options."""
    api_client = get_api_client()

    try:
        video_data = api_client.get_video_rx(rx_id)

        # Check for error
        if video_data.get("error"):
            return ReceiverVideoSettings(rx_id=rx_id)

        settings = video_data.get("settings", {})
        status = video_data.get("status", {})

        return ReceiverVideoSettings(
            rx_id=rx_id,
            resolution=settings.get("resolution"),
            supported_resolutions=settings.get("supported_resolution", []),
            hdcp=settings.get("hdcp"),
            supported_hdcp=settings.get("supported_hdcp", []),
            state=status.get("state")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/receivers/{rx_id}/resolution")
async def set_receiver_resolution(rx_id: int, update: ResolutionUpdate):
    """Set output resolution for a receiver."""
    api_client = get_api_client()

    try:
        result = api_client.set_video_rx_resolution(rx_id, update.resolution)
        return {
            "success": True,
            "rx_id": rx_id,
            "resolution": update.resolution
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/receivers/{rx_id}/hdcp")
async def set_receiver_hdcp(rx_id: int, update: HdcpUpdate):
    """Set HDCP mode for a receiver."""
    api_client = get_api_client()

    try:
        result = api_client.set_video_rx_hdcp(rx_id, update.hdcp)
        return {
            "success": True,
            "rx_id": rx_id,
            "hdcp": update.hdcp
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/receivers/video/all")
async def get_all_receiver_video_settings():
    """Get video settings for all receivers."""
    import asyncio
    from concurrent.futures import ThreadPoolExecutor

    telnet_client = get_telnet_client()
    api_client = get_api_client()

    try:
        counts = telnet_client.get_device_counts()

        def fetch_video_settings(rx_id: int) -> dict:
            """Fetch video settings for a single receiver."""
            try:
                video_data = api_client.get_video_rx(rx_id)

                if video_data.get("error"):
                    return {"rx_id": rx_id, "resolution": None, "supported_resolutions": [], "hdcp": None, "supported_hdcp": []}

                settings = video_data.get("settings", {})
                status = video_data.get("status", {})

                return {
                    "rx_id": rx_id,
                    "resolution": settings.get("resolution"),
                    "supported_resolutions": settings.get("supported_resolution", []),
                    "hdcp": settings.get("hdcp"),
                    "supported_hdcp": settings.get("supported_hdcp", []),
                    "state": status.get("state")
                }
            except Exception:
                return {"rx_id": rx_id, "resolution": None, "supported_resolutions": [], "hdcp": None, "supported_hdcp": []}

        # Fetch all video settings in parallel
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=10) as executor:
            rx_ids = list(range(1, counts.rx_count + 1))
            settings = await loop.run_in_executor(
                None,
                lambda: list(executor.map(fetch_video_settings, rx_ids))
            )

        return {"settings": settings}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- CEC TV Control Endpoints ---

class CecCommand(BaseModel):
    """CEC command type."""
    command: str  # 'power_on', 'power_off', 'volume_up', 'volume_down', 'mute'


@router.post("/receivers/{rx_id}/cec/power-on")
async def cec_power_on(rx_id: int):
    """Send CEC Power On command to TV connected to receiver."""
    client = get_telnet_client()
    try:
        success = client.cec_power_on(rx_id)
        if success:
            return {"success": True, "rx_id": rx_id, "action": "power_on"}
        else:
            raise HTTPException(status_code=500, detail="CEC command failed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/receivers/{rx_id}/cec/power-off")
async def cec_power_off(rx_id: int):
    """Send CEC Power Off (Standby) command to TV connected to receiver."""
    client = get_telnet_client()
    try:
        success = client.cec_power_off(rx_id)
        if success:
            return {"success": True, "rx_id": rx_id, "action": "power_off"}
        else:
            raise HTTPException(status_code=500, detail="CEC command failed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/receivers/{rx_id}/cec/volume-up")
async def cec_volume_up(rx_id: int):
    """Send CEC Volume Up command to TV/AVR connected to receiver."""
    client = get_telnet_client()
    try:
        success = client.cec_volume_up(rx_id)
        if success:
            return {"success": True, "rx_id": rx_id, "action": "volume_up"}
        else:
            raise HTTPException(status_code=500, detail="CEC command failed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/receivers/{rx_id}/cec/volume-down")
async def cec_volume_down(rx_id: int):
    """Send CEC Volume Down command to TV/AVR connected to receiver."""
    client = get_telnet_client()
    try:
        success = client.cec_volume_down(rx_id)
        if success:
            return {"success": True, "rx_id": rx_id, "action": "volume_down"}
        else:
            raise HTTPException(status_code=500, detail="CEC command failed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/receivers/{rx_id}/cec/mute")
async def cec_mute(rx_id: int):
    """Send CEC Mute Toggle command to TV/AVR connected to receiver."""
    client = get_telnet_client()
    try:
        success = client.cec_mute(rx_id)
        if success:
            return {"success": True, "rx_id": rx_id, "action": "mute"}
        else:
            raise HTTPException(status_code=500, detail="CEC command failed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
