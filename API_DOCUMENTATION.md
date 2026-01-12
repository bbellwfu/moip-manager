# Binary MoIP Controller API Documentation

This document provides a reference for the Binary MoIP Controller (B-900-MOIP-4K-CTRL) APIs.

This documentation was created through testing and exploration of the controller API. For official documentation, please refer to [SnapAV/Binary's official resources](https://www.snapav.com/).

**API Version**: 1.3.0
**Firmware Tested**: 4.5.4

## Overview

The Binary MoIP Controller supports two communication interfaces:
1. **Telnet API** (Port 23) - ASCII text protocol for switching and basic control
2. **REST API** (Port 443) - HTTPS JSON API for detailed device management

---

## Telnet API (Port 23)

### Connection Details
- **Port**: 23
- **Protocol**: TCP/Telnet
- **Max Connections**: 10 simultaneous
- **Authentication**: Required (username/password prompt on connect)

### Message Format
- `?` - Query/Request message
- `!` - Control/Command message
- `#` - Error message
- `~` - Unsolicited message (broadcast)
- `\n` - End of message (ASCII 0x0A)

### Query Commands

| Command | Description | Response Format |
|---------|-------------|-----------------|
| `?Help` | List all available commands | Command list |
| `?Devices` | Get TX and RX count | `?Devices=TX_COUNT,RX_COUNT` |
| `?Receivers` | Get all receiver routing | `?Receivers=TX1:RX1,TX2:RX2,...` |
| `?Name=0` | Get all receiver names | `?Name=0,INDEX,NAME` (one per line) |
| `?Name=1` | Get all transmitter names | `?Name=1,INDEX,NAME` (one per line) |
| `?Firmware` | Get firmware version | `?Firmware=VERSION` |
| `?Model` | Get controller model | `?Model=MODEL_NAME` |
| `?Hostname` | Get controller hostname | `?Hostname=NAME` |
| `?ServiceTag` | Get service tag | `?ServiceTag=TAG` |
| `?AudioVolumeLevel` | Get audio volume | `?AudioVolumeLevel=VALUE` |
| `?HDMIAudioMute` | Get HDMI audio mute state | `?HDMIAudioMute=VALUE` |

### Control Commands

| Command | Description | Response |
|---------|-------------|----------|
| `!Switch=TX,RX` | Route transmitter to receiver (TX=0 to unassign) | `OK` or `#Error` |
| `!Resolution=RX,R` | Set receiver output resolution | `OK` or `#Error` |
| `!OSD=RX,MSG` | Display OSD message on receiver (use "CLEAR" to clear) | `OK` or `#Error` |
| `!Reboot` | Reboot the controller | `OK` or `#Error` |
| `!CEC=RX,MODE` | Control CEC (0=OFF, 1=ON) | `OK` or `#Error` |
| `!Serial=TYPE,INDEX,BAUD,DATA` | Send serial data | `OK` or `#Error` |
| `!IR=TYPE,INDEX,PRONTOCODE` | Send IR command (Pronto hex format) | `OK` or `#Error` |
| `!HDMIAudioMute=RX,STATE` | Set HDMI audio mute | `OK` or `#Error` |
| `!SetAudioVolumeLevel=RX,LEVEL` | Set audio volume level | `OK` or `#Error` |
| `!FirmwareUpdate` | Initiate firmware update | `OK` or `#Error` |
| `!Exit` | Disconnect telnet session | - |

#### Resolution Values
| Value | Resolution |
|-------|------------|
| 0 | Pass-through (from source) |
| 1 | 1080p 60Hz |
| 2 | 1080p 50Hz |
| 3 | 2160p 30Hz |
| 4 | 2160p 25Hz |

#### Serial Command Format
```
!Serial=TYPE,INDEX,BAUD-DATABITS_PARITY_STOPBITS,HEX_DATA
```
- TYPE: 0=RX (output), 1=TX (input)
- INDEX: Device index
- BAUD: Baud rate (e.g., 9600)
- DATABITS: 5, 6, 7, or 8
- PARITY: n=none, e=even, o=odd
- STOPBITS: 1 or 2
- HEX_DATA: Space-separated hex bytes

Example: `!Serial=1,2,9600-8n1,61 62 63`

#### IR Command Format
```
!IR=TYPE,INDEX,PRONTOCODE
```
- TYPE: 0=RX (output), 1=TX (input)
- INDEX: Device index
- PRONTOCODE: Pronto hex format string

#### Unsolicited Messages

| Message | Description |
|---------|-------------|
| `~Receivers=TX:RX,...` | Broadcast when routing changes |
| `~Serial=TYPE,INDEX,DATA` | Incoming serial data notification |

---

## REST API v1.3 (Port 443)

### Connection Details
- **Port**: 443 (HTTPS)
- **Base URL**: `https://{host}/api/v1`
- **Authentication**: JWT Bearer token
- **SSL**: Self-signed certificate (verify=false recommended)

### Authentication

#### POST Login
```
POST /base/auth/login
Content-Type: application/json

{
  "username": "your_username",
  "password": "your_password"
}
```

Response:
```json
{
  "accessToken": "eyJ...",
  "expiresIn": 900
}
```

#### GET Login (Digest Auth)
```
GET /base/auth/login
Authorization: Digest ...
```

Use token in subsequent requests:
```
Authorization: Bearer {accessToken}
```

Token expires in 15 minutes (900 seconds).

---

## Base/System Endpoints

### GET /base
Get base device information.

**Response:**
```json
{
  "mac": "XX:XX:XX:XX:XX:XX",
  "model": "B-900-MOIP-4K-CTRL",
  "name": "OvrC-MoIP",
  "platform": "BPi",
  "platformVersion": "4.5.4",
  "serial": "",
  "serviceTag": "XXXXXXXXXXXXXXXXX",
  "version": "4.5.4"
}
```

### GET /base/info
Get hardware information.

**Response:**
```json
{
  "model": "B-900-MOIP-4K-CTRL",
  "platform": "BPi",
  "serial": "",
  "serviceTag": "ST2145063202001B"
}
```

### GET /base/stats
Get hardware statistics.

**Response:**
```json
{
  "cpu": 3,
  "mem": 3,
  "memFree": 962920,
  "memTotal": 1028864,
  "uptime": 191696
}
```

### GET /base/firmware
Get firmware information.

**Response:**
```json
{
  "applyDate": "Feb 21 2025 09:01:56",
  "buildDate": "Feb 21 2025 09:01:56",
  "buildNumber": 0,
  "imageName": "image.bin",
  "platformVersion": "4.5.4",
  "size": 0,
  "version": "4.5.4"
}
```

### GET /base/lan
Get LAN/network configuration.

**Response:**
```json
{
  "deviceName": "OvrC-MoIP",
  "dhcpEnabled": true,
  "dnsServer1": "192.168.1.1",
  "dnsServer2": "8.8.8.8",
  "lanAddress": "192.168.1.100",
  "lanDefaultGateway": "192.168.1.1",
  "lanDnsServer": "192.168.1.1",
  "lanSubnetMask": "255.255.255.0",
  "macAddress": "XX:XX:XX:XX:XX:XX",
  "staticdns": true
}
```

### GET /base/time
Get time information.

**Response:**
```json
{
  "dst": { "enabled": false },
  "time": 1768167900.0,
  "timezone": { "offset": 0 }
}
```

### GET /base/config
Get device configuration (text format).

### PUT /base/config
Upload device configuration.

### GET /base/log
Get combined debug and error log.

### GET /base/log/debug
Get debug log.

### GET /base/log/error
Get error log.

### GET /base/log/download
Download logs as file.

### DELETE /base/log
Clear all logs.

---

## MoIP System Endpoints

### GET /moip/system
Get global MoIP settings.

**Response:**
```json
{
  "diag_mode": "idle",
  "kind": "v1v2",
  "legacy_api": true,
  "name": "Default Name",
  "supported_diag_mode": ["idle", "cycle", "identify"]
}
```

### GET /moip/system/status
Get status summary of ALL units (very useful!).

**Response:**
```json
{
  "units": [
    {
      "ip": "169.254.8.203",
      "mac": "D46A9121EBA3",
      "model": "B-900-MOIP-4K-TX",
      "name": "AppleTV",
      "stats": {
        "cpu_usage": -1,
        "failed_connections": 0,
        "mem_usage": -1,
        "reboots": 0,
        "temp": []
      },
      "unit_state": "operating",
      "upgrade_state": { "percent": 0, "stage": "idle" },
      "version": "v1.6.5"
    }
  ]
}
```

### POST /moip/system
Perform global actions.

### PUT /moip/system
Update global settings.

---

## Unit Endpoints

### GET /moip/unit
Get list of all unit IDs.

**Response:**
```json
{ "items": [1003, 1032, 1038, ...] }
```

### GET /moip/unit/{id}
Get unit details.

**Response:**
```json
{
  "id": 1026,
  "associations": {
    "audio": { "rx": [], "tx": [1027] },
    "group": { "rx": [], "tx": [1031] },
    "ir": { "rx": [], "tx": [1029] },
    "serial": { "rx": [], "tx": [1030] },
    "usb": { "rx": [], "tx": [] },
    "video": { "rx": [], "tx": [1028] }
  },
  "settings": {
    "disabled": false,
    "name": "AppleTV",
    "led_brightness": 1.0
  },
  "status": {
    "ip": "169.254.8.203",
    "mac": "D46A9121EBA3",
    "model": "B-900-MOIP-4K-TX",
    "power_source": "poe",
    "unit_state": "operating",
    "version": "v1.6.5"
  }
}
```

### PUT /moip/unit/{id}
Update unit settings.

### POST /moip/unit/{id}
Perform actions on unit (reboot, identify, etc.).

### DELETE /moip/unit/{id}
Remove unit from system.

### GET /moip/unit/{id}/stats
Get unit statistics.

### GET /moip/unit/{id}/log
Get unit log.

### DELETE /moip/unit/{id}/log
Clear unit log.

---

## Group Endpoints (Logical Groupings)

### GET /moip/group_tx
Get list of all transmitter group IDs.

### GET /moip/group_tx/{id}
Get transmitter group details.

**Response:**
```json
{
  "id": 1031,
  "desc": "audio_video",
  "associations": {
    "audio_tx": 1027,
    "video_tx": 1028,
    "ir_tx": 1029,
    "serial_tx": 1030,
    "usb_tx": null,
    "unit": 1026
  },
  "settings": {
    "index": 1,
    "name": "AppleTV"
  },
  "status": {
    "enabled": true,
    "state": "streaming"
  }
}
```

### PUT /moip/group_tx/{id}
Update group settings.

### GET /moip/group_rx
Get list of all receiver group IDs.

### GET /moip/group_rx/{id}
Get receiver group details.

**Response:**
```json
{
  "id": 1025,
  "desc": "audio_video",
  "associations": {
    "audio_rx": 1021,
    "video_rx": 1022,
    "ir_rx": 1023,
    "serial_rx": 1024,
    "usb_rx": null,
    "unit": 1020,
    "paired_tx": 1031,
    "mv_paired_tx": [],
    "pip_paired_tx": null,
    "vidwall": null
  },
  "settings": {
    "index": 6,
    "name": "Living Room RX",
    "mv": { "enabled": false },
    "pip": { "enabled": false }
  },
  "status": { "state": "streaming" }
}
```

### PUT /moip/group_rx/{id}
Update group settings.

---

## Video Endpoints

### GET /moip/video_tx/{id}
Get video transmitter details and statistics.

**Response:**
```json
{
  "id": 1028,
  "desc": "audio_video",
  "label": "HDMI In",
  "associations": { "unit": 1026 },
  "settings": {
    "name": "TX-D46A9121EBA3",
    "hdcpcap": "hdcpcap2x",
    "edid": {
      "video_format": "hdr_4k30",
      "supported_video_format": ["sdr_4k30", "hdr_4k30"]
    }
  },
  "status": {
    "state": "streaming",
    "resolution": "3840x2160",
    "frame_rate": "60Hz",
    "color_depth": "24",
    "hdcp": "2.2",
    "signal_type": "HDMI 16:9",
    "pixel_rate": "296703KHz",
    "scan_mode": "Progressive"
  }
}
```

### PUT /moip/video_tx/{id}
Update video TX settings.

### GET /moip/video_tx/{id}/preview
Get JPEG preview thumbnail.

**Response:** Raw JPEG image bytes (Content-Type: image/jpeg)

### GET /moip/video_tx/{id}/edid
Get EDID data.

### GET /moip/video_rx/{id}
Get video receiver details.

**Response:**
```json
{
  "id": 1022,
  "desc": "audio_video",
  "label": "HDMI Out",
  "associations": {
    "unit": 1020,
    "paired_tx": 1028
  },
  "settings": {
    "name": "RX-D46A91E1185E",
    "resolution": "passthrough",
    "hdcp": "passthrough",
    "rotation": "none",
    "osd": "",
    "supported_resolution": [
      "passthrough", "uhd2160p30", "uhd2160p25", "uhd2160p24",
      "fhd1080p60", "fhd1080p50", "fhd1080p30", "fhd1080p25", "fhd1080p24",
      "hd720p60", "hd720p50", "hd720p30", "hd720p25", "hd720p24"
    ],
    "supported_rotation": [
      "none", "cw90", "cw180", "cw270", "mirrorx", "mirrory"
    ],
    "pip": { "enabled": false },
    "vidwall": { "enabled": false, "mode": "v1" }
  },
  "status": { "state": "streaming" }
}
```

### PUT /moip/video_rx/{id}
Update video RX settings (resolution, OSD, pairing).

### POST /moip/video_rx/{id}
Perform actions on video RX.

### GET /moip/video_rx/{id}/edid
Get EDID data.

---

## Audio Endpoints

### GET /moip/audio_tx/{id}
Get audio transmitter details.

**Response:**
```json
{
  "id": 1027,
  "desc": "audio_video",
  "label": "Audio Input",
  "settings": {
    "enabled": true,
    "volume": 100,
    "gain": 0.0,
    "delay": 0,
    "downmix": "passthrough",
    "source": ["hdmi"]
  },
  "status": {
    "state": "streaming",
    "format": "lpcm",
    "rate": 48000,
    "depth": 24,
    "source": "hdmi"
  }
}
```

### PUT /moip/audio_tx/{id}
Update audio TX settings.

### GET /moip/audio_rx/{id}
Get audio receiver details.

### PUT /moip/audio_rx/{id}
Update audio RX settings.

### POST /moip/audio_rx/{id}
Perform actions on audio RX.

### Audio Channel/Biquad Endpoints (EQ)
- `GET /moip/audio_rx/{id}/channel/{channel}` - Get channel settings
- `PUT /moip/audio_rx/{id}/channel/{channel}` - Update channel settings
- `GET /moip/audio_rx/{id}/channel/{channel}/bq` - Get all biquads
- `GET /moip/audio_rx/{id}/channel/{channel}/bq/{bq}` - Get specific biquad
- `PUT /moip/audio_rx/{id}/channel/{channel}/bq/{bq}` - Update biquad
- `GET /moip/audio_rx/{id}/main_bq/{bq}` - Get main channel biquad
- `PUT /moip/audio_rx/{id}/main_bq/{bq}` - Update main channel biquad
- `GET /moip/audio_rx/{id}/sub_bq/{bq}` - Get sub channel biquad
- `PUT /moip/audio_rx/{id}/sub_bq/{bq}` - Update sub channel biquad

---

## IR Endpoints

### GET /moip/ir_tx/{id}
Get IR transmitter details.

### PUT /moip/ir_tx/{id}
Update IR TX settings.

### GET /moip/ir_rx/{id}
Get IR receiver details.

**Response:**
```json
{
  "id": 1023,
  "label": "IR",
  "associations": {
    "unit": 1020,
    "paired_tx": 1029
  },
  "settings": {
    "name": "RX-D46A91E1185E",
    "ir_power": false,
    "static_routing": false,
    "supported_max_repeat": 16
  },
  "status": { "state": "streaming" }
}
```

### PUT /moip/ir_rx/{id}
Update IR RX settings.

### POST /moip/ir_rx/{id}
Send IR command.

---

## Serial Endpoints

### GET /moip/serial_tx/{id}
Get serial transmitter details.

### PUT /moip/serial_tx/{id}
Update serial TX settings.

### POST /moip/serial_tx/{id}
Send serial data.

### GET /moip/serial_tx/{id}/message
Get next queued serial message.

### DELETE /moip/serial_tx/{id}/message
Clear next serial message.

### GET /moip/serial_rx/{id}
Get serial receiver details.

**Response:**
```json
{
  "id": 1024,
  "label": "RS-232",
  "settings": {
    "baud_rate": 9600,
    "data_bits": 8,
    "parity": "none",
    "stop_bits": 1,
    "mode": "dce",
    "format": "hex_space",
    "static_routing": true
  },
  "status": {
    "state": "streaming",
    "messages": 0
  }
}
```

### PUT /moip/serial_rx/{id}
Update serial RX settings.

### POST /moip/serial_rx/{id}
Send serial data.

### GET /moip/serial_rx/{id}/message
Get next queued serial message.

### DELETE /moip/serial_rx/{id}/message
Clear next serial message.

---

## USB Endpoints

### GET /moip/usb_tx/{id}
Get USB transmitter details.

### PUT /moip/usb_tx/{id}
Update USB TX settings.

### GET /moip/usb_rx/{id}
Get USB receiver details.

### PUT /moip/usb_rx/{id}
Update USB RX settings.

---

## Video Wall Endpoints

### GET /moip/vidwall
Get all video walls.

### POST /moip/vidwall
Create a new video wall.

### GET /moip/vidwall/{id}
Get video wall details.

### PUT /moip/vidwall/{id}
Update video wall settings.

### DELETE /moip/vidwall/{id}
Delete video wall.

---

## Multiview Layout Endpoints

### GET /moip/fixed_layout/{fixed_layout}
Get multiview layout window information.

---

## Eventing (WebSocket)

### GET /moip/change
WebSocket endpoint for real-time change events.

Connect via WebSocket to receive real-time updates when:
- Routing changes
- Device status changes
- Serial messages arrive
- Settings are modified

### GET /moip/raw_change
Get raw change event socket information.

---

## Action Endpoints

### POST /base/hwcon/reboot
Reboot the controller.

### POST /base/config/reset
Factory reset.

### PUT /base/firmware
Upload and apply firmware update.

### PUT /base/auth/credentials
Update authentication credentials.

---

## ID Mapping

The REST API uses internal IDs. To map telnet indices to REST API IDs:

1. **TX Index to group_tx ID**:
   ```python
   groups = api.get("/moip/group_tx")
   for group_id in groups["items"]:
       group = api.get(f"/moip/group_tx/{group_id}")
       if group["settings"]["index"] == tx_index:
           return group_id
   ```

2. **TX Index to video_tx ID**:
   Get the group_tx, then use `associations.video_tx`

3. **RX Index to video_rx ID**:
   Get the group_rx, then use `associations.video_rx`

---

## Controller Information

- **Model**: B-900-MOIP-4K-CTRL
- **Firmware Tested**: 4.5.4
- **API Version**: 1.3.0
- **Default Credentials**: Refer to your controller documentation
- **Telnet Port**: 23
- **HTTPS Port**: 443
- **Token Expiry**: 15 minutes (900 seconds)

---

## References

- [SnapAV Binary MoIP Product Page](https://www.snapav.com/shop/en/snapav/binary)
- [SnapAV Binary MoIP API V1.2 (PDF)](https://www.snapav.com/wcsstore/ExtendedSitesCatalogAssetStore/attachments/documents/MediaDistribution/ProtocolsAndDrivers/SnapAV_Binary_MoIP_API_V1.2.pdf)
