# MoIP Manager

A web-based management interface for Binary MoIP 4K video distribution systems. Control your AV-over-IP matrix from any browser with an intuitive dashboard.

## Features

- **Dashboard View**: Visual grid of all receivers with current source assignments
- **Quick Source Switching**: Click any receiver to change its source transmitter
- **Resolution & HDCP Control**: Adjust output resolution and HDCP mode per receiver
- **Device Naming**: Customize transmitter and receiver names with icons
- **Transmitter Preview**: View live thumbnail previews from any transmitter
- **Configuration Snapshots**: Save and restore routing configurations
- **Device Inventory**: Sync and view detailed device information from the controller
- **Real-time Status**: Connection status, active streams, and device counts

## Requirements

- Binary MoIP Controller (B-900-MOIP-4K-CTRL) with firmware 4.5.x or compatible
- Network access to the MoIP controller (Telnet port 23 and HTTPS port 443)
- **For desktop app**: macOS 10.15+ or Windows 10+
- **For development**: Python 3.10 or higher

## Installation

### Option 1: Download Desktop App (Recommended)

The easiest way to get started - no Python or development tools required.

1. Go to the [Releases](https://github.com/bbellwfu/moip-manager/releases) page
2. Download the latest version for your platform:
   - **macOS**: `MoIP-Manager-vX.X.X-mac.dmg`
   - **Windows**: `MoIP-Manager-vX.X.X-win.zip`
3. Install and run:
   - **macOS**: Open the DMG, drag to Applications, double-click to launch
   - **Windows**: Extract the ZIP, run `MoIP Manager.exe`
4. Your browser will automatically open to the MoIP Manager interface

**Data Location**: Your settings and snapshots are stored in:
- macOS: `~/Library/Application Support/MoIP Manager/`
- Windows: `%APPDATA%\MoIP Manager\`

These files persist across app updates.

### Option 2: Run from Source (For Developers)

#### 1. Clone the Repository

```bash
git clone https://github.com/bbellwfu/moip-manager.git
cd moip_manager
```

#### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

#### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

#### 4. Configure Environment (Optional)

Copy the example environment file and edit it with your controller details:

```bash
cp .env.example .env
```

Edit `.env` with your controller's IP address and credentials:

```
MOIP_HOST=192.168.1.100
MOIP_API_USERNAME=your_username
MOIP_API_PASSWORD=your_password
```

**Note**: You can also configure these settings through the web UI after starting the application.

#### 5. Run the Application

```bash
python run.py
```

The web interface will be available at `http://localhost:8000`

## First-Time Setup

1. Open your browser to `http://localhost:8000`
2. Navigate to the **Settings** tab
3. Enter your controller's IP address and credentials
4. Click **Test Connection** to verify connectivity
5. Click **Save Settings**
6. Return to the **Dashboard** tab and click **Refresh**

## Usage

### Dashboard

- **Receiver Cards**: Each card shows a receiver with its current source
- **Quick Select Buttons**: Fast access to frequently used transmitters
- **Resolution/HDCP**: Dropdown controls for output settings
- **Change Source**: Click to select from all available transmitters

### Snapshots

Save your current routing configuration before events or changes:

1. Click **Save Current Config**
2. Enter a descriptive name
3. Restore later by selecting the snapshot and choosing what to restore

### Inventory

View detailed device information synced from the controller, including:
- Device type, ID, and name
- Model and MAC address
- IP address and last seen time

## Project Structure

```
moip_manager/
├── app/                    # FastAPI web application
│   ├── main.py            # Application entry point
│   ├── database.py        # SQLite database for local storage
│   ├── routes/            # API endpoints
│   │   ├── devices.py     # Device and routing endpoints
│   │   ├── switching.py   # Source switching endpoints
│   │   └── storage.py     # Snapshots and settings endpoints
│   └── static/            # Frontend files
│       ├── index.html     # Main UI
│       ├── style.css      # Styling
│       └── app.js         # Frontend logic
├── moip/                   # Python library for MoIP communication
│   ├── client.py          # Telnet client
│   ├── api_client.py      # REST API client
│   └── models.py          # Data models
├── packaging/             # Desktop app packaging
│   ├── moip-manager.spec  # PyInstaller configuration
│   └── icons/             # App icons for macOS/Windows
├── .github/workflows/     # CI/CD
│   └── release.yml        # Build and release automation
├── config.py              # Configuration management
├── run.py                 # Application launcher
├── requirements.txt       # Python dependencies
└── API_DOCUMENTATION.md   # Controller API reference
```

## Running as a Service

### Linux (systemd)

Create `/etc/systemd/system/moip-manager.service`:

```ini
[Unit]
Description=MoIP Manager
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/moip_manager
Environment=PATH=/path/to/moip_manager/venv/bin
ExecStart=/path/to/moip_manager/venv/bin/python run.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Then enable and start:

```bash
sudo systemctl enable moip-manager
sudo systemctl start moip-manager
```

### macOS (launchd)

Create `~/Library/LaunchAgents/com.moip.manager.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.moip.manager</string>
    <key>ProgramArguments</key>
    <array>
        <string>/path/to/moip_manager/venv/bin/python</string>
        <string>/path/to/moip_manager/run.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/path/to/moip_manager</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
```

Then load:

```bash
launchctl load ~/Library/LaunchAgents/com.moip.manager.plist
```

## API Reference

See [API_DOCUMENTATION.md](API_DOCUMENTATION.md) for details on the Binary MoIP Controller APIs.

## Updating

### Desktop App

1. Download the latest version from the [Releases](https://github.com/bbellwfu/moip-manager/releases) page
2. Replace the old app with the new version
3. Your settings and data are preserved (stored in user data directory)

### From Source

```bash
cd moip_manager
git pull origin main
pip install -r requirements.txt  # In case dependencies changed
```

## Troubleshooting

### Connection Refused
- Verify the controller IP address is correct
- Ensure ports 23 (Telnet) and 443 (HTTPS) are accessible
- Check that you're on the same network as the controller

### Authentication Failed
- Verify your username and password
- Check your controller's documentation for default credentials

### SSL Certificate Errors
- The MoIP controller uses a self-signed certificate
- Keep "Verify SSL Certificate" disabled in settings (default)

### Devices Not Showing
- Click the **Sync from Controller** button in the Inventory tab
- Ensure your credentials have permission to access device information

## License

MIT License - See LICENSE file for details.

## Disclaimer

This is an unofficial, community-developed tool. It is not affiliated with, endorsed by, or supported by SnapAV or Binary. Use at your own risk.

Binary and MoIP are trademarks of SnapAV.
