// MoIP Manager Frontend

// State
let transmitters = [];
let receivers = [];
let routing = [];
let inventory = { transmitters: [], receivers: [] };
let snapshots = [];
let videoStats = {};  // Map of tx_id -> video stats
let receiverVideoSettings = {};  // Map of rx_id -> video settings (resolution, etc.)
let deviceIcons = {};  // Map of device_type_index -> icon_type
let selectedRx = null;
let editingDevice = null;
let restoringSnapshotId = null;
let previewingTxId = null;

// Available icon types
const ICON_TYPES = [
    { id: 'default', name: 'Default (TV)', icon: '\uD83D\uDCFA' },
    { id: 'apple', name: 'Apple TV', image: '/static/icons/apple.svg' },
    { id: 'roku', name: 'Roku', image: '/static/icons/roku.png' },
    { id: 'xbox', name: 'Xbox', icon: '\uD83C\uDFAE' },
    { id: 'playstation', name: 'PlayStation', icon: '\uD83C\uDFAE' },
    { id: 'nintendo', name: 'Nintendo', icon: '\uD83C\uDFAE' },
    { id: 'gaming', name: 'Gaming', icon: '\uD83C\uDFAE' },
    { id: 'computer', name: 'Computer', icon: '\uD83D\uDCBB' },
    { id: 'cable', name: 'Cable/Satellite', icon: '\uD83D\uDCE1' },
    { id: 'streaming', name: 'Fire TV/Chromecast', icon: '\uD83D\uDD25' },
    { id: 'disc', name: 'Blu-ray/DVD', icon: '\uD83D\uDCBF' },
    { id: 'camera', name: 'Camera/Security', icon: '\uD83D\uDCF7' }
];

// API Base URL
const API_BASE = '/api';

// Activity indicator (no longer dims the page)
function showActivity(message) {
    const indicator = document.getElementById('activity-status');
    indicator.textContent = message;
    indicator.classList.add('active');
}

function hideActivity() {
    const indicator = document.getElementById('activity-status');
    indicator.classList.remove('active');
}

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
    await loadAppSettings();

    // Check URL hash for initial tab (priority: URL hash > default_tab setting > dashboard)
    const hashTab = getTabFromHash();
    if (hashTab) {
        showTab(hashTab, false);
    } else if (appSettings.default_tab && appSettings.default_tab !== 'dashboard') {
        showTab(appSettings.default_tab);
    } else {
        // Set initial hash for dashboard
        history.replaceState({ tab: 'dashboard' }, '', '#dashboard');
    }

    refreshAll();
    // Note: Auto-refresh is now controlled by settings (applyAppSettings)
});

// App settings (saved to server database)
let appSettings = {};

async function loadAppSettings() {
    try {
        const response = await fetch(`${API_BASE}/settings`);
        if (response.ok) {
            appSettings = await response.json();
            applyAppSettings();
        }
    } catch (error) {
        console.error('Error loading app settings:', error);
    }
}

function applyAppSettings() {
    // Apply TX sort/filter
    if (appSettings.tx_sort) {
        const sortEl = document.getElementById('tx-sort');
        if (sortEl) sortEl.value = appSettings.tx_sort;
    }
    if (appSettings.tx_filter) {
        const filterEl = document.getElementById('tx-filter');
        if (filterEl) filterEl.value = appSettings.tx_filter;
    }

    // Apply refresh interval
    const interval = parseInt(appSettings.refresh_interval) || 0;
    if (window.autoRefreshTimer) {
        clearInterval(window.autoRefreshTimer);
    }
    if (interval > 0) {
        window.autoRefreshTimer = setInterval(refreshAll, interval * 1000);
    }

    // Store quick buttons count for use in rendering
    window.quickButtonsCount = parseInt(appSettings.quick_buttons) || 5;
}

async function saveAppSettings() {
    const txSort = document.getElementById('tx-sort')?.value;
    const txFilter = document.getElementById('tx-filter')?.value;

    const newSettings = {};
    if (txSort) newSettings.tx_sort = txSort;
    if (txFilter) newSettings.tx_filter = txFilter;

    // Only save if changed
    if (newSettings.tx_sort !== appSettings.tx_sort ||
        newSettings.tx_filter !== appSettings.tx_filter) {
        appSettings = { ...appSettings, ...newSettings };
        try {
            await fetch(`${API_BASE}/settings`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(newSettings)
            });
        } catch (error) {
            console.error('Error saving app settings:', error);
        }
    }
}

// Tab Navigation
// Valid tab names for routing
const VALID_TABS = ['dashboard', 'inventory', 'snapshots', 'settings'];

function showTab(tabName, updateHash = true) {
    // Validate tab name
    if (!VALID_TABS.includes(tabName)) {
        tabName = 'dashboard';
    }

    // Update tab buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.textContent.toLowerCase().includes(tabName)) {
            btn.classList.add('active');
        }
    });

    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(`${tabName}-tab`).classList.add('active');

    // Update URL hash (without triggering hashchange if already correct)
    if (updateHash && window.location.hash !== `#${tabName}`) {
        history.pushState({ tab: tabName }, '', `#${tabName}`);
    }

    // Load tab-specific data
    if (tabName === 'inventory') {
        loadInventory();
    } else if (tabName === 'snapshots') {
        loadSnapshots();
    } else if (tabName === 'settings') {
        loadSettings();
    }
}

// Handle browser back/forward navigation
window.addEventListener('popstate', (event) => {
    const tab = event.state?.tab || getTabFromHash() || 'dashboard';
    showTab(tab, false);
});

// Get tab name from URL hash
function getTabFromHash() {
    const hash = window.location.hash.slice(1); // Remove '#'
    return VALID_TABS.includes(hash) ? hash : null;
}

// API Functions
async function fetchDevices() {
    const response = await fetch(`${API_BASE}/devices`);
    if (!response.ok) throw new Error('Failed to fetch devices');
    return response.json();
}

async function fetchRouting() {
    const response = await fetch(`${API_BASE}/routing`);
    if (!response.ok) throw new Error('Failed to fetch routing');
    return response.json();
}

async function fetchStatus() {
    const response = await fetch(`${API_BASE}/status`);
    if (!response.ok) throw new Error('Failed to fetch status');
    return response.json();
}

async function fetchInventory() {
    const response = await fetch(`${API_BASE}/inventory`);
    if (!response.ok) throw new Error('Failed to fetch inventory');
    return response.json();
}

async function fetchSnapshots() {
    const response = await fetch(`${API_BASE}/snapshots`);
    if (!response.ok) throw new Error('Failed to fetch snapshots');
    return response.json();
}

async function fetchDeviceIcons() {
    const response = await fetch(`${API_BASE}/device-icons`);
    if (!response.ok) throw new Error('Failed to fetch device icons');
    return response.json();
}

async function updateDeviceIcon(deviceType, deviceId, iconType) {
    const endpoint = deviceType === 'tx'
        ? `${API_BASE}/transmitters/${deviceId}/icon`
        : `${API_BASE}/receivers/${deviceId}/icon`;
    const response = await fetch(endpoint, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ icon_type: iconType })
    });
    if (!response.ok) throw new Error('Failed to update device icon');
    return response.json();
}

async function fetchVideoStats() {
    const response = await fetch(`${API_BASE}/transmitters/video/all`);
    if (!response.ok) throw new Error('Failed to fetch video stats');
    return response.json();
}

async function fetchTxVideoStats(txId) {
    const response = await fetch(`${API_BASE}/transmitters/${txId}/video`);
    if (!response.ok) throw new Error('Failed to fetch video stats');
    return response.json();
}

async function fetchReceiverVideoSettings() {
    const response = await fetch(`${API_BASE}/receivers/video/all`);
    if (!response.ok) throw new Error('Failed to fetch receiver video settings');
    return response.json();
}

async function setReceiverResolution(rxId, resolution) {
    const response = await fetch(`${API_BASE}/receivers/${rxId}/resolution`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ resolution })
    });
    if (!response.ok) throw new Error('Failed to set resolution');
    return response.json();
}

async function setReceiverHdcp(rxId, hdcp) {
    const response = await fetch(`${API_BASE}/receivers/${rxId}/hdcp`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ hdcp })
    });
    if (!response.ok) throw new Error('Failed to set HDCP');
    return response.json();
}

async function switchSource(tx, rx) {
    const response = await fetch(`${API_BASE}/switch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tx, rx })
    });
    if (!response.ok) throw new Error('Failed to switch source');
    return response.json();
}

async function updateReceiverName(rxId, name) {
    const response = await fetch(`${API_BASE}/receivers/${rxId}/name`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name })
    });
    if (!response.ok) throw new Error('Failed to update name');
    return response.json();
}

async function updateTransmitterName(txId, name) {
    const response = await fetch(`${API_BASE}/transmitters/${txId}/name`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name })
    });
    if (!response.ok) throw new Error('Failed to update name');
    return response.json();
}

// Refresh all data
async function refreshAll() {
    try {
        showActivity('Loading devices...');

        const [devicesData, routingData, statusData, iconsData] = await Promise.all([
            fetchDevices(),
            fetchRouting(),
            fetchStatus(),
            fetchDeviceIcons().catch(() => ({}))  // Don't fail if icons can't be loaded
        ]);

        transmitters = devicesData.transmitters;
        receivers = devicesData.receivers;
        routing = routingData;
        deviceIcons = iconsData;

        updateConnectionStatus(statusData.connected);
        updateStatusBar(statusData);
        renderReceivers();
        renderTransmitters();

        // Fetch video stats and receiver settings (shows its own activity indicator)
        loadVideoStats();
        loadReceiverVideoSettings();
    } catch (error) {
        console.error('Error refreshing data:', error);
        updateConnectionStatus(false);
        hideActivity();
    }
}

// Track video stats loading state
let videoStatsLoading = false;

// Load video stats for all transmitters
async function loadVideoStats() {
    videoStatsLoading = true;
    showActivity('Loading video stats...');

    // Re-render to show loading indicators
    renderTransmitters();

    try {
        const data = await fetchVideoStats();
        videoStats = {};
        for (const stat of data.stats) {
            videoStats[stat.tx_id] = stat;
        }
    } catch (error) {
        console.error('Error loading video stats:', error);
    } finally {
        videoStatsLoading = false;
        hideActivity();
        // Re-render transmitters to show stats
        renderTransmitters();
    }
}

// Load video settings for all receivers (resolution, etc.)
async function loadReceiverVideoSettings() {
    try {
        const data = await fetchReceiverVideoSettings();
        receiverVideoSettings = {};
        for (const setting of data.settings) {
            receiverVideoSettings[setting.rx_id] = setting;
        }
        // Re-render receivers to show resolution
        renderReceivers();
    } catch (error) {
        console.error('Error loading receiver video settings:', error);
    }
}

// Update connection status indicator
function updateConnectionStatus(connected) {
    const indicator = document.getElementById('connection-status');
    if (connected) {
        indicator.textContent = 'Connected';
        indicator.className = 'status-indicator connected';
    } else {
        indicator.textContent = 'Disconnected';
        indicator.className = 'status-indicator disconnected';
    }
}

// Update status bar
function updateStatusBar(status) {
    document.getElementById('tx-count').textContent = `TX: ${status.tx_count}`;
    document.getElementById('rx-count').textContent = `RX: ${status.rx_count}`;
    document.getElementById('active-streams').textContent = `Active: ${status.active_streams}`;
    document.getElementById('controller-ip').textContent = `Controller: ${status.controller_ip}`;
}

// Get icon data for a specific icon type
function getIconDataByType(iconType) {
    const iconDef = ICON_TYPES.find(t => t.id === iconType);
    if (iconDef) {
        return {
            icon: iconDef.icon || null,
            image: iconDef.image || null,
            class: `icon-${iconType}`
        };
    }
    return { icon: '\uD83D\uDCFA', image: null, class: 'icon-default' };
}

// Detect icon type from device name (for name-based fallback)
function detectIconTypeFromName(name) {
    const lowerName = name.toLowerCase();

    if (lowerName.includes('apple') || lowerName.includes('appletv') || lowerName.includes('apple tv')) {
        return 'apple';
    }
    if (lowerName.includes('roku')) {
        return 'roku';
    }
    if (lowerName.includes('xbox')) {
        return 'xbox';
    }
    if (lowerName.includes('playstation') || lowerName.includes('ps4') || lowerName.includes('ps5')) {
        return 'playstation';
    }
    if (lowerName.includes('nintendo') || lowerName.includes('switch')) {
        return 'nintendo';
    }
    if (lowerName.includes('pc') || lowerName.includes('computer') || lowerName.includes('htpc')) {
        return 'computer';
    }
    if (lowerName.includes('cable') || lowerName.includes('satellite') || lowerName.includes('dish') || lowerName.includes('directv')) {
        return 'cable';
    }
    if (lowerName.includes('fire') || lowerName.includes('chromecast') || lowerName.includes('firestick')) {
        return 'streaming';
    }
    if (lowerName.includes('blu') || lowerName.includes('dvd') || lowerName.includes('disc')) {
        return 'disc';
    }
    if (lowerName.includes('camera') || lowerName.includes('security') || lowerName.includes('cctv')) {
        return 'camera';
    }

    return 'default';
}

// Get device icon - checks stored icons first, then infers from name
function getDeviceIcon(name, deviceType = 'tx', deviceIndex = null) {
    // Check if we have a stored icon for this device
    if (deviceIndex !== null) {
        const key = `${deviceType}_${deviceIndex}`;
        if (deviceIcons[key]) {
            return getIconDataByType(deviceIcons[key]);
        }
    }

    // Fall back to name-based detection
    const lowerName = name.toLowerCase();

    // Apple devices - use image
    if (lowerName.includes('apple') || lowerName.includes('appletv') || lowerName.includes('apple tv')) {
        return { icon: null, image: '/static/icons/apple.svg', class: 'icon-apple' };
    }
    // Roku - use image
    if (lowerName.includes('roku')) {
        return { icon: null, image: '/static/icons/roku.png', class: 'icon-roku' };
    }
    // Gaming - Xbox
    if (lowerName.includes('xbox')) {
        return { icon: '\uD83C\uDFAE', image: null, class: 'icon-xbox' };
    }
    // Gaming - PlayStation
    if (lowerName.includes('playstation') || lowerName.includes('ps4') || lowerName.includes('ps5')) {
        return { icon: '\uD83C\uDFAE', image: null, class: 'icon-playstation' };
    }
    // Gaming - Nintendo
    if (lowerName.includes('nintendo') || lowerName.includes('switch')) {
        return { icon: '\uD83C\uDFAE', image: null, class: 'icon-nintendo' };
    }
    // Generic gaming
    if (lowerName.includes('game') || lowerName.includes('gaming') || lowerName.includes('console')) {
        return { icon: '\uD83C\uDFAE', image: null, class: 'icon-gaming' };
    }
    // Computer/PC
    if (lowerName.includes('pc') || lowerName.includes('computer') || lowerName.includes('mac') || lowerName.includes('laptop')) {
        return { icon: '\uD83D\uDCBB', image: null, class: 'icon-computer' };
    }
    // Cable/Satellite
    if (lowerName.includes('cable') || lowerName.includes('satellite') || lowerName.includes('directv') || lowerName.includes('dish') || lowerName.includes('xfinity') || lowerName.includes('comcast')) {
        return { icon: '\uD83D\uDCE1', image: null, class: 'icon-cable' };
    }
    // Chromecast/Fire TV
    if (lowerName.includes('chromecast') || lowerName.includes('fire') || lowerName.includes('firetv') || lowerName.includes('amazon')) {
        return { icon: '\uD83D\uDD25', image: null, class: 'icon-streaming' };
    }
    // Blu-ray/DVD
    if (lowerName.includes('bluray') || lowerName.includes('blu-ray') || lowerName.includes('dvd')) {
        return { icon: '\uD83D\uDCBF', image: null, class: 'icon-disc' };
    }
    // Camera/Security
    if (lowerName.includes('camera') || lowerName.includes('security') || lowerName.includes('nvr')) {
        return { icon: '\uD83D\uDCF7', image: null, class: 'icon-camera' };
    }
    // Default - generic TV/video source
    return { icon: '\uD83D\uDCFA', image: null, class: 'icon-default' };
}

// Get the most recently used (active) transmitters
function getRecentTransmitters(maxCount = 5) {
    // Get TXs that are currently streaming to at least one receiver
    const activeTxIds = new Set();
    for (const route of routing) {
        if (route.tx > 0) {
            activeTxIds.add(route.tx);
        }
    }

    // Convert to array and sort by TX number
    const activeTxs = [...activeTxIds]
        .sort((a, b) => a - b)
        .slice(0, maxCount)
        .map(txId => {
            const tx = transmitters.find(t => t.id === txId);
            const name = tx ? tx.name : `Tx${txId}`;
            const deviceIcon = getDeviceIcon(name, 'tx', txId);
            return {
                id: txId,
                name: name,
                isActive: true,
                icon: deviceIcon.icon,
                image: deviceIcon.image || null,
                iconClass: deviceIcon.class
            };
        });

    return activeTxs;
}

// Render receiver cards
function renderReceivers() {
    const grid = document.getElementById('receivers-grid');
    grid.innerHTML = '';

    // Sort receivers by ID
    const sortedReceivers = [...receivers].sort((a, b) => a.id - b.id);

    // Get recent/active transmitters for quick select
    const recentTxs = getRecentTransmitters(5);

    for (const rx of sortedReceivers) {
        // Find current routing for this receiver
        const route = routing.find(r => r.rx === rx.id);
        const currentTx = route ? route.tx : 0;
        const txName = currentTx > 0 ? getTxName(currentTx) : 'No Source';

        // Build quick select buttons
        const quickButtonCount = window.quickButtonsCount || 5;
        let quickSelectHtml = '<div class="quick-select">';
        for (let i = 0; i < quickButtonCount; i++) {
            if (i < recentTxs.length) {
                const tx = recentTxs[i];
                const isCurrentSource = tx.id === currentTx;
                // Use image if available, otherwise emoji
                const iconHtml = tx.image
                    ? `<img src="${tx.image}" class="quick-tx-img" alt="">`
                    : `<span class="quick-tx-icon">${tx.icon}</span>`;
                quickSelectHtml += `
                    <button class="quick-tx-btn ${isCurrentSource ? 'current' : ''} ${tx.iconClass}"
                            onclick="quickSwitch(${tx.id}, ${rx.id}); event.stopPropagation();"
                            title="Tx${tx.id}: ${escapeHtml(tx.name)}">
                        ${iconHtml}
                        <span class="quick-tx-num">${tx.id}</span>
                    </button>
                `;
            } else {
                // Empty placeholder
                quickSelectHtml += `<div class="quick-tx-placeholder"></div>`;
            }
        }
        quickSelectHtml += '</div>';

        // Build video settings row (resolution + HDCP) - only for AV receivers, not audio-only
        let videoSettingsHtml = '';
        if (rx.subtype !== 'audio') {
            const videoSettings = receiverVideoSettings[rx.id] || {};
            const currentResolution = videoSettings.resolution || 'passthrough';
            const currentHdcp = videoSettings.hdcp || 'passthrough';

            // Use supported options from API, or fallback to common defaults
            const defaultResolutions = ['passthrough', 'uhd2160p60', 'uhd2160p30', 'fhd1080p60', 'fhd1080p30', 'hd720p60'];
            const defaultHdcp = ['passthrough', 'hdcp14', 'hdcp22'];
            const supportedResolutions = videoSettings.supported_resolutions?.length > 0
                ? videoSettings.supported_resolutions
                : defaultResolutions;
            const supportedHdcp = videoSettings.supported_hdcp?.length > 0
                ? videoSettings.supported_hdcp
                : defaultHdcp;

            videoSettingsHtml = '<div class="receiver-video-settings">';

            // Resolution selector
            videoSettingsHtml += `
                <div class="video-setting-group">
                    <label class="video-setting-label">Resolution</label>
                    <select class="video-setting-select" onchange="changeResolution(${rx.id}, this.value)" title="Output Resolution">
                        ${supportedResolutions.map(res => `
                            <option value="${res}" ${res === currentResolution ? 'selected' : ''}>
                                ${formatResolutionLabel(res)}
                            </option>
                        `).join('')}
                    </select>
                </div>
            `;

            // HDCP selector
            videoSettingsHtml += `
                <div class="video-setting-group">
                    <label class="video-setting-label">HDCP</label>
                    <select class="video-setting-select" onchange="changeHdcp(${rx.id}, this.value)" title="HDCP Mode">
                        ${supportedHdcp.map(mode => `
                            <option value="${mode}" ${mode === currentHdcp ? 'selected' : ''}>
                                ${formatHdcpLabel(mode)}
                            </option>
                        `).join('')}
                    </select>
                </div>
            `;

            videoSettingsHtml += '</div>';
        }

        // Icon for receiver type (TV for AV, speaker for Audio)
        const rxTypeIcon = rx.subtype === 'audio'
            ? `<svg class="rx-type-icon audio" viewBox="0 0 24 24" fill="currentColor"><path d="M3 9V15H7L12 20V4L7 9H3ZM16.5 12C16.5 10.23 15.48 8.71 14 7.97V16.02C15.48 15.29 16.5 13.77 16.5 12ZM14 3.23V5.29C16.89 6.15 19 8.83 19 12S16.89 17.85 14 18.71V20.77C18.01 19.86 21 16.28 21 12S18.01 4.14 14 3.23Z"/></svg>`
            : `<svg class="rx-type-icon" viewBox="0 0 24 24" fill="currentColor"><path d="M21 3H3C1.9 3 1 3.9 1 5V17C1 18.1 1.9 19 3 19H8V21H16V19H21C22.1 19 23 18.1 23 17V5C23 3.9 22.1 3 21 3ZM21 17H3V5H21V17Z"/></svg>`;

        // Index badge - shows "Rx4" or "Rx4 Audio" for differentiation
        const indexBadge = rx.subtype === 'audio'
            ? `<span class="rx-index-badge audio">Rx${rx.id} Audio</span>`
            : `<span class="rx-index-badge">Rx${rx.id}</span>`;

        const card = document.createElement('div');
        card.className = `receiver-card ${currentTx > 0 ? 'streaming' : 'no-source'} ${rx.subtype === 'audio' ? 'audio-receiver' : ''}`;
        card.innerHTML = `
            <div class="receiver-header">
                ${indexBadge}
            </div>
            <div class="receiver-name" onclick="editName('rx', ${rx.id}, '${escapeHtml(rx.name)}')">
                ${rxTypeIcon}
                ${escapeHtml(rx.name)}
                <span class="edit-icon">&#9998;</span>
            </div>
            <div class="receiver-source ${currentTx > 0 ? 'active' : ''}">
                ${currentTx > 0 ? `Tx${currentTx}: ${escapeHtml(txName)}` : txName}
            </div>
            ${videoSettingsHtml}
            ${quickSelectHtml}
            <a class="more-sources-link" href="#" onclick="openSwitchModal(${rx.id}, '${escapeHtml(rx.name)}'); return false;">
                More Sources...
            </a>
        `;
        grid.appendChild(card);
    }
}

// Format resolution for display
function formatResolutionLabel(resolution) {
    const labels = {
        'passthrough': 'Auto',
        'uhd2160p60': '4K 60Hz',
        'uhd2160p50': '4K 50Hz',
        'uhd2160p30': '4K 30Hz',
        'uhd2160p25': '4K 25Hz',
        'uhd2160p24': '4K 24Hz',
        'fhd1080p60': '1080p 60Hz',
        'fhd1080p50': '1080p 50Hz',
        'fhd1080p30': '1080p 30Hz',
        'fhd1080p25': '1080p 25Hz',
        'fhd1080p24': '1080p 24Hz',
        'hd720p60': '720p 60Hz',
        'hd720p50': '720p 50Hz',
        'hd720p30': '720p 30Hz',
        'hd720p25': '720p 25Hz',
        'hd720p24': '720p 24Hz'
    };
    return labels[resolution] || resolution;
}

// Change receiver output resolution
async function changeResolution(rxId, resolution) {
    const rxName = receivers.find(r => r.id === rxId)?.name || `Rx${rxId}`;

    try {
        showActivity(`Setting ${rxName} to ${formatResolutionLabel(resolution)}...`);
        await setReceiverResolution(rxId, resolution);

        // Update local state
        if (receiverVideoSettings[rxId]) {
            receiverVideoSettings[rxId].resolution = resolution;
        }

        hideActivity();
    } catch (error) {
        console.error('Error changing resolution:', error);
        alert('Failed to change resolution. Please try again.');
        hideActivity();
        // Reload to get correct state
        loadReceiverVideoSettings();
    }
}

// Format HDCP mode for display
function formatHdcpLabel(hdcp) {
    const labels = {
        'passthrough': 'Auto',
        'hdcp14': '1.4',
        'hdcp22': '2.2'
    };
    return labels[hdcp] || hdcp;
}

// Change receiver HDCP mode
async function changeHdcp(rxId, hdcp) {
    const rxName = receivers.find(r => r.id === rxId)?.name || `Rx${rxId}`;

    try {
        showActivity(`Setting ${rxName} to ${formatHdcpLabel(hdcp)}...`);
        await setReceiverHdcp(rxId, hdcp);

        // Update local state
        if (receiverVideoSettings[rxId]) {
            receiverVideoSettings[rxId].hdcp = hdcp;
        }

        hideActivity();
    } catch (error) {
        console.error('Error changing HDCP:', error);
        alert('Failed to change HDCP mode. Please try again.');
        hideActivity();
        // Reload to get correct state
        loadReceiverVideoSettings();
    }
}

// Quick switch source (one-click)
async function quickSwitch(txId, rxId) {
    const rxName = receivers.find(r => r.id === rxId)?.name || `Rx${rxId}`;
    const txName = transmitters.find(t => t.id === txId)?.name || `Tx${txId}`;

    try {
        showActivity(`Switching ${rxName} to ${txName}...`);
        await switchSource(txId, rxId);
        showActivity('Source changed. Refreshing...');
        await refreshAll();
    } catch (error) {
        console.error('Error switching source:', error);
        alert('Failed to switch source. Please try again.');
        hideActivity();
    }
}

// Render transmitter list
function renderTransmitters() {
    const list = document.getElementById('transmitters-list');
    list.innerHTML = '';

    // Get sort and filter values
    const sortBy = document.getElementById('tx-sort')?.value || 'id';
    const filterBy = document.getElementById('tx-filter')?.value || 'all';

    // Save settings to server
    saveAppSettings();

    // Build transmitter list with status info
    let txList = transmitters.map(tx => {
        const rxCount = routing.filter(r => r.tx === tx.id).length;
        return { ...tx, rxCount, isActive: rxCount > 0 };
    });

    // Apply filter (use is_online for actual hardware status)
    if (filterBy === 'online') {
        txList = txList.filter(tx => tx.is_online !== false);
    } else if (filterBy === 'offline') {
        txList = txList.filter(tx => tx.is_online === false);
    }

    // Apply sort
    if (sortBy === 'id') {
        txList.sort((a, b) => a.id - b.id);
    } else if (sortBy === 'name') {
        txList.sort((a, b) => a.name.localeCompare(b.name));
    } else if (sortBy === 'status') {
        txList.sort((a, b) => {
            // Active first, then by ID
            if (a.isActive && !b.isActive) return -1;
            if (!a.isActive && b.isActive) return 1;
            return a.id - b.id;
        });
    }

    // Show empty state if no results
    if (txList.length === 0) {
        list.innerHTML = `<div class="empty-row">No transmitters match the filter</div>`;
        return;
    }

    for (const tx of txList) {
        const stats = videoStats[tx.id];
        const row = document.createElement('div');
        row.className = 'transmitter-row';

        // Build video stats display
        let statsHtml = '';
        if (videoStatsLoading) {
            // Show loading placeholder
            statsHtml = `<div class="tx-video-stats">
                <span class="stat loading">Loading...</span>
            </div>`;
        } else if (stats && stats.has_signal) {
            const parts = [];
            if (stats.resolution) parts.push(stats.resolution);
            if (stats.frame_rate) parts.push(stats.frame_rate);
            if (stats.color_depth) parts.push(`${stats.color_depth}-bit`);
            if (parts.length > 0) {
                statsHtml = `<div class="tx-video-stats">
                    ${parts.map(p => `<span class="stat streaming">${p}</span>`).join('')}
                </div>`;
            }
        }

        // Determine indicator status: offline (red), streaming (green), idle (gray)
        const isOffline = tx.is_online === false;
        const indicatorClass = isOffline ? 'offline' : (tx.isActive ? 'active' : 'inactive');

        // Audio badge for audio-only transmitters
        const audioBadge = tx.subtype === 'audio' ? '<span class="tx-audio-badge">Audio</span>' : '';

        // Status text
        let statusText;
        if (isOffline) {
            statusText = 'Offline';
        } else if (tx.isActive) {
            statusText = `Streaming to ${tx.rxCount} receiver${tx.rxCount > 1 ? 's' : ''}`;
        } else {
            statusText = 'Idle';
        }

        row.innerHTML = `
            <div class="tx-indicator ${indicatorClass}"></div>
            <span class="tx-name" onclick="editName('tx', ${tx.id}, '${escapeHtml(tx.name)}')">
                Tx${tx.id}: ${escapeHtml(tx.name)} ${audioBadge}
            </span>
            ${statsHtml}
            <button class="tx-preview-btn" onclick="openPreviewModal(${tx.id}, '${escapeHtml(tx.name)}'); event.stopPropagation();">Preview</button>
            <span class="tx-status ${isOffline ? 'offline' : ''}">
                ${statusText}
            </span>
        `;
        list.appendChild(row);
    }
}

// Get transmitter name by ID
function getTxName(txId) {
    const tx = transmitters.find(t => t.id === txId);
    return tx ? tx.name : `Tx${txId}`;
}

// Open switch source modal
function openSwitchModal(rxId, rxName) {
    selectedRx = rxId;
    document.getElementById('modal-rx-name').textContent = rxName;

    const optionsContainer = document.getElementById('tx-options');
    optionsContainer.innerHTML = '';

    // Add "No Source" option
    const noSourceOption = document.createElement('div');
    noSourceOption.className = 'tx-option';
    noSourceOption.innerHTML = `
        <div class="tx-indicator inactive"></div>
        <span>No Source (Unassign)</span>
    `;
    noSourceOption.onclick = () => selectSource(0);
    optionsContainer.appendChild(noSourceOption);

    // Add transmitter options
    const sortedTransmitters = [...transmitters].sort((a, b) => a.id - b.id);
    for (const tx of sortedTransmitters) {
        const rxCount = routing.filter(r => r.tx === tx.id).length;
        const isActive = rxCount > 0;

        const option = document.createElement('div');
        option.className = 'tx-option';
        option.innerHTML = `
            <div class="tx-indicator ${isActive ? 'active' : 'inactive'}"></div>
            <span>Tx${tx.id}: ${escapeHtml(tx.name)}</span>
        `;
        option.onclick = () => selectSource(tx.id);
        optionsContainer.appendChild(option);
    }

    document.getElementById('switch-modal').classList.add('active');
}

// Close switch modal
function closeModal() {
    document.getElementById('switch-modal').classList.remove('active');
    selectedRx = null;
}

// Select a source
async function selectSource(txId) {
    if (selectedRx === null) return;

    const rxName = receivers.find(r => r.id === selectedRx)?.name || `Rx${selectedRx}`;
    const txName = txId === 0 ? 'No Source' : (transmitters.find(t => t.id === txId)?.name || `Tx${txId}`);

    try {
        showActivity(`Switching ${rxName} to ${txName}...`);
        await switchSource(txId, selectedRx);
        showActivity(`Source changed. Refreshing...`);
        closeModal();
        await refreshAll();
    } catch (error) {
        console.error('Error switching source:', error);
        alert('Failed to switch source. Please try again.');
        hideActivity();
    }
}

// Open edit name modal
function editName(type, id, currentName) {
    editingDevice = { type, id };
    document.getElementById('name-input').value = currentName;

    // Get icon picker elements
    const pickerContainer = document.getElementById('icon-picker');
    const pickerLabel = document.getElementById('icon-picker-label');

    // Only show icon picker for TX devices
    if (type === 'tx') {
        pickerContainer.style.display = '';
        if (pickerLabel) pickerLabel.style.display = '';

        // Get current icon type - check saved icons first, then use name-based detection
        let currentIconType = deviceIcons[`${type}_${id}`];
        if (!currentIconType) {
            // Fall back to name-based detection (same logic as getDeviceIcon)
            currentIconType = detectIconTypeFromName(currentName);
        }

        pickerContainer.innerHTML = ICON_TYPES.map(iconType => {
            const isSelected = iconType.id === currentIconType;
            const iconHtml = iconType.image
                ? `<img src="${iconType.image}" alt="${iconType.name}">`
                : iconType.icon;
            return `
                <div class="icon-picker-option ${isSelected ? 'selected' : ''}"
                     data-icon-type="${iconType.id}"
                     onclick="selectIcon('${iconType.id}')">
                    <div class="icon-display">${iconHtml}</div>
                    <div class="icon-label">${iconType.name}</div>
                </div>
            `;
        }).join('');
    } else {
        // Hide icon picker for RX devices
        pickerContainer.style.display = 'none';
        if (pickerLabel) pickerLabel.style.display = 'none';
    }

    document.getElementById('name-modal').classList.add('active');
    document.getElementById('name-input').focus();
}

// Select an icon in the picker
function selectIcon(iconType) {
    document.querySelectorAll('.icon-picker-option').forEach(opt => {
        opt.classList.remove('selected');
        if (opt.dataset.iconType === iconType) {
            opt.classList.add('selected');
        }
    });
}

// Get currently selected icon
function getSelectedIcon() {
    const selected = document.querySelector('.icon-picker-option.selected');
    return selected ? selected.dataset.iconType : null;
}

// Close name modal
function closeNameModal() {
    document.getElementById('name-modal').classList.remove('active');
    editingDevice = null;
}

// Save name and icon
async function saveName() {
    if (!editingDevice) return;

    const newName = document.getElementById('name-input').value.trim();
    if (!newName) {
        alert('Please enter a name');
        return;
    }

    const deviceType = editingDevice.type.toUpperCase();
    const deviceId = editingDevice.id;
    const selectedIcon = getSelectedIcon();

    try {
        showActivity(`Updating ${deviceType}${deviceId}...`);

        // Update name
        if (editingDevice.type === 'rx') {
            await updateReceiverName(editingDevice.id, newName);
        } else {
            await updateTransmitterName(editingDevice.id, newName);
        }

        // Update icon if selected
        if (selectedIcon) {
            await updateDeviceIcon(editingDevice.type, editingDevice.id, selectedIcon);
        }

        showActivity('Saved. Refreshing...');
        closeNameModal();
        await refreshAll();
    } catch (error) {
        console.error('Error updating device:', error);
        alert('Failed to update device. Please try again.');
        hideActivity();
    }
}

// === Inventory Functions ===

async function loadInventory() {
    try {
        showActivity('Loading inventory...');
        const data = await fetchInventory();
        inventory = data;
        renderInventory();
    } catch (error) {
        console.error('Error loading inventory:', error);
    } finally {
        hideActivity();
    }
}

function isVirtualDevice(device) {
    // Virtual devices have IP 0.0.0.0 (like Control4 EA3 audio-only transmitters)
    return device.ip_address === '0.0.0.0';
}

function renderInventory() {
    const tbody = document.getElementById('inventory-tbody');
    tbody.innerHTML = '';

    const includeVirtual = document.getElementById('include-virtual-toggle')?.checked ?? true;

    let allDevices = [
        ...inventory.transmitters.map(d => ({ ...d, sortKey: `tx${String(d.device_index).padStart(3, '0')}` })),
        ...inventory.receivers.map(d => ({ ...d, sortKey: `rx${String(d.device_index).padStart(3, '0')}` }))
    ].sort((a, b) => a.sortKey.localeCompare(b.sortKey));

    // Filter out virtual devices if toggle is off
    if (!includeVirtual) {
        allDevices = allDevices.filter(d => !isVirtualDevice(d));
    }

    if (allDevices.length === 0) {
        const message = includeVirtual
            ? 'No devices in inventory. Click "Sync from Controller" to populate.'
            : 'No physical devices in inventory. Enable "Include Virtual Devices" to see all devices.';
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="empty-state">
                    ${message}
                </td>
            </tr>
        `;
        return;
    }

    let hasVirtualDevices = false;

    for (const device of allDevices) {
        const row = document.createElement('tr');
        const typeClass = device.device_type === 'tx' ? 'device-type-tx' : 'device-type-rx';
        const lastSeen = device.last_seen ? formatDate(device.last_seen) : 'Never';
        const isVirtual = isVirtualDevice(device);

        if (isVirtual) hasVirtualDevices = true;

        // Build subtype badge
        let subtypeBadge = '';
        const subtype = device.subtype || 'av';
        if (subtype === 'audio') {
            subtypeBadge = ' <span class="subtype-badge audio">Audio</span>';
        } else if (subtype === 'videowall') {
            subtypeBadge = ' <span class="subtype-badge videowall">Video Wall</span>';
        }
        // Don't show badge for 'av' as it's the default

        // Virtual badge takes precedence for display
        const badges = isVirtual ? ' <span class="virtual-badge">Virtual</span>' : subtypeBadge;

        row.innerHTML = `
            <td class="${typeClass}">${device.device_type.toUpperCase()}${badges}</td>
            <td>${device.device_index}</td>
            <td>${escapeHtml(device.name || '-')}</td>
            <td>${escapeHtml(device.model || '-')}</td>
            <td><code>${device.mac_address || '-'}</code></td>
            <td>${device.ip_address || '-'}</td>
            <td>${lastSeen}</td>
        `;
        tbody.appendChild(row);
    }

    // Add footnote if virtual devices are shown
    const footnoteEl = document.getElementById('virtual-footnote');
    if (footnoteEl) {
        footnoteEl.style.display = hasVirtualDevices ? 'block' : 'none';
    }
}

async function syncDevices() {
    try {
        showActivity('Fetching device info from controller...');
        const response = await fetch(`${API_BASE}/sync`, { method: 'POST' });
        if (!response.ok) throw new Error('Sync failed');
        showActivity('Sync complete. Loading inventory...');
        await loadInventory();
        alert('Device sync completed successfully');
    } catch (error) {
        console.error('Error syncing devices:', error);
        alert('Failed to sync devices. Please try again.');
        hideActivity();
    }
}

// === Snapshot Functions ===

async function loadSnapshots() {
    try {
        showActivity('Loading snapshots...');
        const data = await fetchSnapshots();
        snapshots = data.snapshots;
        renderSnapshots();
    } catch (error) {
        console.error('Error loading snapshots:', error);
    } finally {
        hideActivity();
    }
}

function renderSnapshots() {
    const container = document.getElementById('snapshots-list');
    container.innerHTML = '';

    if (snapshots.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                No snapshots saved yet. Click "Save Current Config" to create your first snapshot.
            </div>
        `;
        return;
    }

    for (const snapshot of snapshots) {
        const card = document.createElement('div');
        card.className = 'snapshot-card';
        card.innerHTML = `
            <div class="snapshot-info">
                <div class="snapshot-name">${escapeHtml(snapshot.name)}</div>
                <div class="snapshot-meta">${formatDate(snapshot.created_at)}</div>
                ${snapshot.description ? `<div class="snapshot-desc">${escapeHtml(snapshot.description)}</div>` : ''}
            </div>
            <div class="snapshot-actions">
                <button class="restore-btn" onclick="openRestoreModal(${snapshot.id}, '${escapeHtml(snapshot.name)}')">Restore</button>
                <button class="delete-btn" onclick="deleteSnapshot(${snapshot.id})">Delete</button>
            </div>
        `;
        container.appendChild(card);
    }
}

function openSnapshotModal() {
    document.getElementById('snapshot-name').value = '';
    document.getElementById('snapshot-desc').value = '';
    document.getElementById('snapshot-modal').classList.add('active');
    document.getElementById('snapshot-name').focus();
}

function closeSnapshotModal() {
    document.getElementById('snapshot-modal').classList.remove('active');
}

async function saveSnapshot() {
    const name = document.getElementById('snapshot-name').value.trim();
    const description = document.getElementById('snapshot-desc').value.trim();

    if (!name) {
        alert('Please enter a snapshot name');
        return;
    }

    try {
        showActivity('Capturing current configuration...');
        const response = await fetch(`${API_BASE}/snapshots`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, description: description || null })
        });

        if (!response.ok) throw new Error('Failed to save snapshot');

        showActivity('Snapshot saved. Refreshing list...');
        closeSnapshotModal();
        await loadSnapshots();
        alert('Snapshot saved successfully');
    } catch (error) {
        console.error('Error saving snapshot:', error);
        alert('Failed to save snapshot. Please try again.');
        hideActivity();
    }
}

function openRestoreModal(snapshotId, snapshotName) {
    restoringSnapshotId = snapshotId;
    document.getElementById('restore-snapshot-name').textContent = snapshotName;
    document.getElementById('restore-routing').checked = true;
    document.getElementById('restore-names').checked = true;
    document.getElementById('restore-modal').classList.add('active');
}

function closeRestoreModal() {
    document.getElementById('restore-modal').classList.remove('active');
    restoringSnapshotId = null;
}

async function confirmRestore() {
    if (!restoringSnapshotId) return;

    const restoreRouting = document.getElementById('restore-routing').checked;
    const restoreNames = document.getElementById('restore-names').checked;

    if (!restoreRouting && !restoreNames) {
        alert('Please select at least one option to restore');
        return;
    }

    try {
        let restoring = [];
        if (restoreRouting) restoring.push('routing');
        if (restoreNames) restoring.push('names');
        showActivity(`Restoring ${restoring.join(' and ')}...`);

        const response = await fetch(`${API_BASE}/snapshots/${restoringSnapshotId}/restore`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                restore_routing: restoreRouting,
                restore_names: restoreNames
            })
        });

        if (!response.ok) throw new Error('Failed to restore snapshot');

        const result = await response.json();
        showActivity('Restore complete. Refreshing...');
        closeRestoreModal();
        await refreshAll();

        let message = 'Restore completed: ';
        if (restoreRouting) message += `${result.routing_restored} routes`;
        if (restoreRouting && restoreNames) message += ', ';
        if (restoreNames) message += `${result.names_restored} names`;
        if (result.errors && result.errors.length > 0) {
            message += `\n\nWarnings:\n${result.errors.join('\n')}`;
        }
        alert(message);
    } catch (error) {
        console.error('Error restoring snapshot:', error);
        alert('Failed to restore snapshot. Please try again.');
        hideActivity();
    }
}

async function deleteSnapshot(snapshotId) {
    if (!confirm('Are you sure you want to delete this snapshot?')) return;

    try {
        showActivity('Deleting snapshot...');
        const response = await fetch(`${API_BASE}/snapshots/${snapshotId}`, {
            method: 'DELETE'
        });

        if (!response.ok) throw new Error('Failed to delete snapshot');

        await loadSnapshots();
    } catch (error) {
        console.error('Error deleting snapshot:', error);
        alert('Failed to delete snapshot. Please try again.');
        hideActivity();
    }
}

// === Preview Modal Functions ===

function openPreviewModal(txId, txName) {
    previewingTxId = txId;
    document.getElementById('preview-tx-name').textContent = `Tx${txId}: ${txName}`;
    document.getElementById('preview-modal').classList.add('active');
    loadPreview(txId);
}

function closePreviewModal() {
    document.getElementById('preview-modal').classList.remove('active');
    previewingTxId = null;
    // Reset image state
    const img = document.getElementById('preview-image');
    img.classList.remove('loaded');
    img.src = '';
}

async function loadPreview(txId) {
    const img = document.getElementById('preview-image');
    const loading = document.getElementById('preview-loading');
    const error = document.getElementById('preview-error');
    const statsContainer = document.getElementById('preview-video-stats');

    // Reset state
    img.classList.remove('loaded');
    loading.classList.add('active');
    error.classList.remove('active');
    statsContainer.innerHTML = '';

    try {
        // Load video stats
        const stats = await fetchTxVideoStats(txId);

        // Display stats
        const statsHtml = [];
        if (stats.resolution) {
            statsHtml.push(`<div class="stat-item"><span class="stat-label">Resolution</span><span class="stat-value">${stats.resolution}</span></div>`);
        }
        if (stats.frame_rate) {
            statsHtml.push(`<div class="stat-item"><span class="stat-label">Frame Rate</span><span class="stat-value">${stats.frame_rate} fps</span></div>`);
        }
        if (stats.color_depth) {
            statsHtml.push(`<div class="stat-item"><span class="stat-label">Color Depth</span><span class="stat-value">${stats.color_depth}</span></div>`);
        }
        if (stats.signal_type) {
            statsHtml.push(`<div class="stat-item"><span class="stat-label">Signal</span><span class="stat-value">${stats.signal_type}</span></div>`);
        }
        if (stats.hdcp !== null && stats.hdcp !== undefined) {
            statsHtml.push(`<div class="stat-item"><span class="stat-label">HDCP</span><span class="stat-value">${stats.hdcp ? 'Yes' : 'No'}</span></div>`);
        }
        if (stats.state) {
            statsHtml.push(`<div class="stat-item"><span class="stat-label">State</span><span class="stat-value">${stats.state}</span></div>`);
        }
        statsContainer.innerHTML = statsHtml.join('');

        // Load preview image
        img.onload = function() {
            loading.classList.remove('active');
            img.classList.add('loaded');
        };
        img.onerror = function() {
            loading.classList.remove('active');
            error.classList.add('active');
        };

        // Add timestamp to prevent caching
        img.src = `${API_BASE}/transmitters/${txId}/preview?t=${Date.now()}`;
    } catch (err) {
        console.error('Error loading preview:', err);
        loading.classList.remove('active');
        error.classList.add('active');
        statsContainer.innerHTML = '<div class="stat-item"><span class="stat-label">Error</span><span class="stat-value">Could not load stats</span></div>';
    }
}

function refreshPreview() {
    if (previewingTxId) {
        loadPreview(previewingTxId);
    }
}

// === Controller Info Modal Functions ===

async function openControllerInfoModal() {
    document.getElementById('controller-info-modal').classList.add('active');
    document.getElementById('controller-info-body').innerHTML = '<div class="info-loading">Loading controller information...</div>';

    try {
        const response = await fetch(`${API_BASE}/controller/info`);
        if (!response.ok) throw new Error('Failed to fetch controller info');
        const data = await response.json();

        renderControllerInfo(data);
    } catch (error) {
        console.error('Error loading controller info:', error);
        document.getElementById('controller-info-body').innerHTML = `
            <div class="info-loading" style="color: var(--danger-color);">
                Failed to load controller information
            </div>
        `;
    }
}

function renderControllerInfo(data) {
    const base = data.base || {};
    const stats = data.stats || {};
    const lan = data.lan || {};
    const firmware = data.firmware || {};
    const counts = data.device_counts || {};

    let html = '';

    // === Device Section ===
    html += '<div class="info-section">';
    html += '<div class="info-section-header">Device</div>';
    html += '<div class="info-grid">';

    if (base.model) {
        html += `
            <div class="info-item full-width">
                <div class="info-item-label">Model</div>
                <div class="info-item-value mono">${base.model}</div>
            </div>
        `;
    }

    if (base.name || lan.deviceName) {
        html += `
            <div class="info-item">
                <div class="info-item-label">Hostname</div>
                <div class="info-item-value">${base.name || lan.deviceName}</div>
            </div>
        `;
    }

    if (base.version || firmware.version) {
        html += `
            <div class="info-item">
                <div class="info-item-label">Firmware</div>
                <div class="info-item-value mono">${base.version || firmware.version}</div>
            </div>
        `;
    }

    if (base.platform) {
        html += `
            <div class="info-item">
                <div class="info-item-label">Platform</div>
                <div class="info-item-value">${base.platform}</div>
            </div>
        `;
    }

    if (base.serviceTag) {
        html += `
            <div class="info-item">
                <div class="info-item-label">Service Tag</div>
                <div class="info-item-value mono">${base.serviceTag}</div>
            </div>
        `;
    }

    html += '</div></div>';

    // === Network Section ===
    html += '<div class="info-section">';
    html += '<div class="info-section-header">Network</div>';
    html += '<div class="info-grid">';

    html += `
        <div class="info-item">
            <div class="info-item-label">IP Address</div>
            <div class="info-item-value mono">${lan.lanAddress || data.controller_ip || 'Unknown'}</div>
        </div>
    `;

    if (lan.lanSubnetMask) {
        html += `
            <div class="info-item">
                <div class="info-item-label">Subnet Mask</div>
                <div class="info-item-value mono">${lan.lanSubnetMask}</div>
            </div>
        `;
    }

    if (lan.lanDefaultGateway) {
        html += `
            <div class="info-item">
                <div class="info-item-label">Gateway</div>
                <div class="info-item-value mono">${lan.lanDefaultGateway}</div>
            </div>
        `;
    }

    if (lan.dhcpEnabled !== undefined) {
        html += `
            <div class="info-item">
                <div class="info-item-label">DHCP</div>
                <div class="info-item-value">${lan.dhcpEnabled ? 'Enabled' : 'Static'}</div>
            </div>
        `;
    }

    if (base.mac || lan.macAddress) {
        html += `
            <div class="info-item full-width">
                <div class="info-item-label">MAC Address</div>
                <div class="info-item-value mono">${base.mac || lan.macAddress}</div>
            </div>
        `;
    }

    html += '</div></div>';

    // === System Status Section ===
    html += '<div class="info-section">';
    html += '<div class="info-section-header">System Status</div>';
    html += '<div class="info-grid">';

    html += `
        <div class="info-item">
            <div class="info-item-label">Transmitters</div>
            <div class="info-item-value">${counts.transmitters || 0}</div>
        </div>
        <div class="info-item">
            <div class="info-item-label">Receivers</div>
            <div class="info-item-value">${counts.receivers || 0}</div>
        </div>
    `;

    if (stats.uptime) {
        html += `
            <div class="info-item">
                <div class="info-item-label">Uptime</div>
                <div class="info-item-value">${formatUptime(stats.uptime)}</div>
            </div>
        `;
    }

    if (stats.cpu !== undefined) {
        html += `
            <div class="info-item">
                <div class="info-item-label">CPU</div>
                <div class="info-item-value">${stats.cpu}%</div>
            </div>
        `;
    }

    if (stats.mem !== undefined) {
        const memUsed = stats.memTotal && stats.memFree ?
            Math.round((stats.memTotal - stats.memFree) / 1024) : null;
        const memTotal = stats.memTotal ? Math.round(stats.memTotal / 1024) : null;
        html += `
            <div class="info-item">
                <div class="info-item-label">Memory</div>
                <div class="info-item-value">${stats.mem}%${memUsed && memTotal ? ` (${memUsed}/${memTotal} MB)` : ''}</div>
            </div>
        `;
    }

    html += '</div></div>';

    document.getElementById('controller-info-body').innerHTML = html;
}

function formatUptime(seconds) {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const mins = Math.floor((seconds % 3600) / 60);

    if (days > 0) {
        return `${days}d ${hours}h ${mins}m`;
    } else if (hours > 0) {
        return `${hours}h ${mins}m`;
    } else {
        return `${mins}m`;
    }
}

function closeControllerInfoModal() {
    document.getElementById('controller-info-modal').classList.remove('active');
}

// Format MAC address with colons
function formatMac(mac) {
    if (!mac || mac.length !== 12) return mac;
    return mac.match(/.{2}/g).join(':');
}

// Format uptime seconds to human readable
function formatUptime(seconds) {
    if (!seconds) return 'Unknown';
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);

    let parts = [];
    if (days > 0) parts.push(`${days}d`);
    if (hours > 0) parts.push(`${hours}h`);
    if (minutes > 0) parts.push(`${minutes}m`);
    return parts.join(' ') || '< 1m';
}

// === Settings Functions ===

async function loadSettings() {
    try {
        const response = await fetch(`${API_BASE}/settings`);
        if (!response.ok) throw new Error('Failed to load settings');
        const settings = await response.json();
        appSettings = settings;

        // Populate form fields
        document.getElementById('setting-controller-ip').value = settings.controller_ip || '';
        document.getElementById('setting-telnet-port').value = settings.telnet_port || '23';
        document.getElementById('setting-api-port').value = settings.api_port || '443';
        document.getElementById('setting-username').value = settings.username || '';
        document.getElementById('setting-password').value = '';
        document.getElementById('setting-password').placeholder = settings.password_set ? '(password saved)' : 'Enter password';
        document.getElementById('setting-refresh-interval').value = settings.refresh_interval || '0';
        document.getElementById('setting-quick-buttons').value = settings.quick_buttons || '5';
        document.getElementById('setting-default-tab').value = settings.default_tab || 'dashboard';
        document.getElementById('setting-verify-ssl').checked = settings.verify_ssl === 'true';
        document.getElementById('setting-timeout').value = settings.timeout || '10';

        // Clear any previous status
        const status = document.getElementById('settings-status');
        status.className = 'settings-status';
        status.textContent = '';
    } catch (error) {
        console.error('Error loading settings:', error);
        showSettingsStatus('error', 'Failed to load settings');
    }
}

async function saveSettings(event) {
    event.preventDefault();

    const settings = {
        controller_ip: document.getElementById('setting-controller-ip').value,
        telnet_port: document.getElementById('setting-telnet-port').value,
        api_port: document.getElementById('setting-api-port').value,
        username: document.getElementById('setting-username').value,
        password: document.getElementById('setting-password').value,
        refresh_interval: document.getElementById('setting-refresh-interval').value,
        quick_buttons: document.getElementById('setting-quick-buttons').value,
        default_tab: document.getElementById('setting-default-tab').value,
        verify_ssl: document.getElementById('setting-verify-ssl').checked,
        timeout: document.getElementById('setting-timeout').value
    };

    try {
        const response = await fetch(`${API_BASE}/settings`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(settings)
        });

        if (!response.ok) throw new Error('Failed to save settings');

        showSettingsStatus('success', 'Settings saved successfully! Refresh the page to apply changes.');

        // Update cached settings
        appSettings = { ...appSettings, ...settings };

        // Apply settings that can take effect immediately
        applySettings(settings);

        // Clear password field after save
        document.getElementById('setting-password').value = '';
        document.getElementById('setting-password').placeholder = '(password saved)';
    } catch (error) {
        console.error('Error saving settings:', error);
        showSettingsStatus('error', 'Failed to save settings: ' + error.message);
    }
}

async function testConnection() {
    // Open modal with loading state
    const modal = document.getElementById('test-connection-modal');
    const body = document.getElementById('test-connection-body');
    body.innerHTML = '<div class="test-loading">Testing connections...</div>';
    modal.classList.add('active');

    try {
        const response = await fetch(`${API_BASE}/settings/test`, {
            method: 'POST'
        });

        if (!response.ok) throw new Error('Test failed');

        const results = await response.json();

        // Build results HTML
        let html = '<div class="test-results">';

        // Telnet result
        html += `<div class="test-result ${results.telnet.success ? 'success' : 'error'}">`;
        html += `<div class="test-result-header">`;
        html += `<span class="test-result-icon">${results.telnet.success ? '\u2705' : '\u274C'}</span>`;
        html += `<span class="test-result-name">Telnet Connection</span>`;
        html += `</div>`;
        html += `<div class="test-result-message">${results.telnet.message}</div>`;
        html += `</div>`;

        // REST API result
        html += `<div class="test-result ${results.api.success ? 'success' : 'error'}">`;
        html += `<div class="test-result-header">`;
        html += `<span class="test-result-icon">${results.api.success ? '\u2705' : '\u274C'}</span>`;
        html += `<span class="test-result-name">REST API Connection</span>`;
        html += `</div>`;
        html += `<div class="test-result-message">${results.api.message}</div>`;
        html += `</div>`;

        html += '</div>';
        body.innerHTML = html;

    } catch (error) {
        console.error('Error testing connection:', error);
        body.innerHTML = `<div class="test-result error">
            <div class="test-result-header">
                <span class="test-result-icon">\u274C</span>
                <span class="test-result-name">Connection Test Failed</span>
            </div>
            <div class="test-result-message">${error.message}</div>
        </div>`;
    }
}

function closeTestConnectionModal() {
    document.getElementById('test-connection-modal').classList.remove('active');
}

function togglePasswordVisibility() {
    const passwordInput = document.getElementById('setting-password');
    const toggleBtn = document.querySelector('.toggle-password');

    if (passwordInput.type === 'password') {
        passwordInput.type = 'text';
        toggleBtn.textContent = 'Hide';
    } else {
        passwordInput.type = 'password';
        toggleBtn.textContent = 'Show';
    }
}

function showSettingsStatus(type, message) {
    const status = document.getElementById('settings-status');
    status.className = `settings-status ${type}`;
    status.textContent = message;
    status.style.whiteSpace = 'pre-line';
}

function applySettings(settings) {
    // Apply refresh interval
    const interval = parseInt(settings.refresh_interval) || 0;
    if (window.refreshTimer) {
        clearInterval(window.refreshTimer);
    }
    if (interval > 0) {
        window.refreshTimer = setInterval(refreshAll, interval * 1000);
    }

    // Store quick buttons count for use in rendering
    window.quickButtonsCount = parseInt(settings.quick_buttons) || 5;
}

// === Utility Functions ===

// Handle Enter key in modals
document.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
        if (document.getElementById('name-modal').classList.contains('active')) {
            saveName();
        } else if (document.getElementById('snapshot-modal').classList.contains('active')) {
            saveSnapshot();
        }
    }
    if (e.key === 'Escape') {
        closeModal();
        closeNameModal();
        closeSnapshotModal();
        closeRestoreModal();
        closePreviewModal();
        closeControllerInfoModal();
    }
});

// Escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Format date
function formatDate(dateStr) {
    const date = new Date(dateStr);
    return date.toLocaleString();
}
