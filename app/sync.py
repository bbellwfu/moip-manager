"""Sync device data from Binary MoIP controller to local database."""
import logging
from datetime import datetime

import config
from moip import MoIPClient, MoIPAPIClient
from app import database as db

logger = logging.getLogger(__name__)


def determine_subtype(group: dict, model: str = None) -> str:
    """
    Determine device subtype (av, audio, videowall) from group settings or model.

    Binary MoIP has different device types:
    - AV: Full audio/video receivers/transmitters (e.g., B-900-MOIP-4K-RX)
    - Audio: Audio-only extractors (e.g., B-900-MOIP-A-RX)
    - Video Wall: Logical video wall groupings
    """
    # Check group type field if available
    group_type = group.get('settings', {}).get('type', '').lower()
    if 'video' in group_type and 'wall' in group_type:
        return 'videowall'
    if group_type == 'audio':
        return 'audio'
    if group_type == 'av':
        return 'av'

    # Fall back to model name detection
    if model:
        model_lower = model.lower()
        if '-a-rx' in model_lower or '-a-tx' in model_lower:
            return 'audio'
        if 'wall' in model_lower:
            return 'videowall'

    # Default to AV
    return 'av'


def sync_devices():
    """
    Sync all device information from the controller to the local database.

    Fetches data from both telnet (for counts/routing) and REST API (for details).
    """
    logger.info("Starting device sync from controller...")

    try:
        settings = config.get_moip_settings()
        telnet_client = MoIPClient(settings["host"], settings["telnet_port"])
        api_client = MoIPAPIClient(
            settings["host"],
            settings["username"],
            settings["password"]
        )

        # Get device counts from telnet
        counts = telnet_client.get_device_counts()
        logger.info(f"Found {counts.tx_count} transmitters, {counts.rx_count} receivers")

        # Get detailed info from REST API
        units = api_client.get_all_units_detailed()
        tx_groups = api_client.get_all_group_tx_detailed()
        rx_groups = api_client.get_all_group_rx_detailed()

        # Build lookup maps from units
        unit_by_id = {u.get('id'): u for u in units}

        # Process transmitters
        for group in tx_groups:
            idx = group.get('settings', {}).get('index')
            group_id = group.get('id')
            if idx is None or group_id is None:
                continue

            name = group.get('settings', {}).get('name')
            unit_id = group.get('associations', {}).get('unit')

            # Get unit details if available
            mac = ip = model = firmware = None
            if unit_id and unit_id in unit_by_id:
                unit = unit_by_id[unit_id]
                mac = unit.get('status', {}).get('mac')
                ip = unit.get('status', {}).get('ip')
                model = unit.get('status', {}).get('model')
                firmware = unit.get('status', {}).get('firmware')

            subtype = determine_subtype(group, model)

            db.upsert_device(
                device_type='tx',
                device_index=idx,
                group_id=group_id,
                subtype=subtype,
                name=name,
                mac_address=mac,
                ip_address=ip,
                model=model,
                firmware=firmware,
                unit_id=unit_id
            )
            logger.debug(f"Synced Tx{idx} ({subtype}): {name}")

        # Process receivers
        for group in rx_groups:
            idx = group.get('settings', {}).get('index')
            group_id = group.get('id')
            if idx is None or group_id is None:
                continue

            name = group.get('settings', {}).get('name')
            unit_id = group.get('associations', {}).get('unit')

            # Get unit details if available
            mac = ip = model = firmware = None
            if unit_id and unit_id in unit_by_id:
                unit = unit_by_id[unit_id]
                mac = unit.get('status', {}).get('mac')
                ip = unit.get('status', {}).get('ip')
                model = unit.get('status', {}).get('model')
                firmware = unit.get('status', {}).get('firmware')

            subtype = determine_subtype(group, model)

            db.upsert_device(
                device_type='rx',
                device_index=idx,
                group_id=group_id,
                subtype=subtype,
                name=name,
                mac_address=mac,
                ip_address=ip,
                model=model,
                firmware=firmware,
                unit_id=unit_id
            )
            logger.debug(f"Synced Rx{idx} ({subtype}): {name}")

        logger.info("Device sync completed successfully")
        return True

    except Exception as e:
        logger.error(f"Device sync failed: {e}")
        return False


def create_config_snapshot(name: str, description: str = None) -> int:
    """
    Create a snapshot of current configuration.

    Captures:
    - All device names
    - Current routing assignments
    - Device characteristics
    """
    settings = config.get_moip_settings()
    telnet_client = MoIPClient(settings["host"], settings["telnet_port"])

    # Get current routing
    routing = telnet_client.get_routing()
    routing_data = [{'tx': r.tx, 'rx': r.rx} for r in routing]

    # Get all devices from database
    devices = db.get_all_devices()

    snapshot_data = {
        'timestamp': datetime.now().isoformat(),
        'controller_ip': settings["host"],
        'routing': routing_data,
        'devices': devices
    }

    snapshot_id = db.save_snapshot(name, snapshot_data, description)
    logger.info(f"Created snapshot '{name}' with ID {snapshot_id}")
    return snapshot_id


def restore_config_snapshot(snapshot_id: int, restore_routing: bool = True, restore_names: bool = True) -> dict:
    """
    Restore configuration from a snapshot.

    Args:
        snapshot_id: ID of the snapshot to restore
        restore_routing: Whether to restore routing assignments
        restore_names: Whether to restore device names

    Returns:
        Dict with results of restore operations
    """
    snapshot = db.get_snapshot(snapshot_id)
    if not snapshot:
        raise ValueError(f"Snapshot {snapshot_id} not found")

    data = snapshot['snapshot_data']
    results = {'routing_restored': 0, 'names_restored': 0, 'errors': []}

    settings = config.get_moip_settings()
    telnet_client = MoIPClient(settings["host"], settings["telnet_port"])
    api_client = MoIPAPIClient(
        settings["host"],
        settings["username"],
        settings["password"]
    )

    # Restore routing
    if restore_routing:
        for route in data.get('routing', []):
            try:
                telnet_client.switch(route['tx'], route['rx'])
                results['routing_restored'] += 1
            except Exception as e:
                results['errors'].append(f"Failed to restore route Tx{route['tx']}->Rx{route['rx']}: {e}")

    # Restore names
    if restore_names:
        for device in data.get('devices', []):
            if not device.get('name') or not device.get('group_id'):
                continue
            try:
                if device['device_type'] == 'tx':
                    api_client.set_group_tx_name(device['group_id'], device['name'])
                else:
                    api_client.set_group_rx_name(device['group_id'], device['name'])
                results['names_restored'] += 1
            except Exception as e:
                results['errors'].append(f"Failed to restore name for {device['device_type'].upper()}{device['device_index']}: {e}")

    logger.info(f"Restored snapshot {snapshot_id}: {results['routing_restored']} routes, {results['names_restored']} names")
    return results
