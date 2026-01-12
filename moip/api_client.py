"""REST API client for Binary MoIP controller management."""
import time
import httpx
from typing import Optional, Any, Union


class MoIPAPIClient:
    """Client for communicating with Binary MoIP controller REST API."""

    def __init__(
        self,
        host: str,
        username: str = "",
        password: str = "",
        port: int = 443,
        verify_ssl: bool = False
    ):
        """
        Initialize MoIP API client.

        Args:
            host: MoIP controller IP address
            username: API username
            password: API password
            port: HTTPS port (default 443)
            verify_ssl: Whether to verify SSL certificate
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl
        self.base_url = f"https://{host}:{port}/api/v1"

        self._token: Optional[str] = None
        self._token_expires: float = 0

    def _get_client(self) -> httpx.Client:
        """Get an HTTP client with appropriate settings."""
        return httpx.Client(verify=self.verify_ssl, timeout=10.0)

    def _ensure_token(self) -> str:
        """Ensure we have a valid access token."""
        # Refresh if token expires in less than 60 seconds
        if self._token and time.time() < self._token_expires - 60:
            return self._token

        self._login()
        return self._token

    def _login(self) -> None:
        """Authenticate and get access token."""
        with self._get_client() as client:
            response = client.post(
                f"{self.base_url}/base/auth/login",
                json={"username": self.username, "password": self.password}
            )
            response.raise_for_status()
            data = response.json()
            self._token = data["accessToken"]
            self._token_expires = time.time() + data["expiresIn"]

    def _request(self, method: str, endpoint: str, **kwargs) -> Any:
        """
        Make an authenticated API request.

        Args:
            method: HTTP method (GET, POST, PUT, etc.)
            endpoint: API endpoint (without base URL)
            **kwargs: Additional arguments for httpx request

        Returns:
            Response JSON or None for 204 responses
        """
        token = self._ensure_token()
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {token}"

        with self._get_client() as client:
            response = client.request(
                method,
                f"{self.base_url}{endpoint}",
                headers=headers,
                **kwargs
            )
            response.raise_for_status()

            if response.status_code == 204:
                return None
            return response.json()

    def get_system_info(self) -> dict:
        """Get system information."""
        return self._request("GET", "/moip/system")

    def get_firmware_info(self) -> dict:
        """Get firmware information."""
        return self._request("GET", "/base/firmware")

    def get_base_info(self) -> dict:
        """Get base device information (model, platform, version, etc.)."""
        return self._request("GET", "/base")

    def get_base_stats(self) -> dict:
        """Get hardware statistics (CPU, memory, uptime)."""
        return self._request("GET", "/base/stats")

    def get_lan_info(self) -> dict:
        """Get LAN/network configuration."""
        return self._request("GET", "/base/lan")

    def get_time_info(self) -> dict:
        """Get time and timezone information."""
        return self._request("GET", "/base/time")

    def get_system_status(self) -> dict:
        """Get status summary of all units."""
        return self._request("GET", "/moip/system/status")

    def get_unit_ids(self) -> list[int]:
        """Get list of all unit IDs."""
        data = self._request("GET", "/moip/unit")
        return data.get("items", [])

    def get_unit(self, unit_id: int) -> dict:
        """
        Get unit details.

        Args:
            unit_id: Unit ID

        Returns:
            Unit data including settings and status
        """
        return self._request("GET", f"/moip/unit/{unit_id}")

    def set_unit_name(self, unit_id: int, name: str) -> None:
        """
        Set unit name (shown in OvrC).

        Args:
            unit_id: Unit ID
            name: New name
        """
        self._request("PUT", f"/moip/unit/{unit_id}", json={"settings": {"name": name}})

    def get_group_rx_ids(self) -> list[int]:
        """Get list of all group_rx IDs."""
        data = self._request("GET", "/moip/group_rx")
        return data.get("items", [])

    def get_group_rx(self, group_id: int) -> dict:
        """
        Get group_rx details.

        Args:
            group_id: Group Rx ID

        Returns:
            Group data including settings (name, index)
        """
        return self._request("GET", f"/moip/group_rx/{group_id}")

    def set_group_rx_name(self, group_id: int, name: str) -> None:
        """
        Set group_rx name (shown in telnet ?Name=0).

        Args:
            group_id: Group Rx ID
            name: New name
        """
        self._request("PUT", f"/moip/group_rx/{group_id}", json={"settings": {"name": name}})

    def get_group_tx_ids(self) -> list[int]:
        """Get list of all group_tx IDs."""
        data = self._request("GET", "/moip/group_tx")
        return data.get("items", [])

    def get_group_tx(self, group_id: int) -> dict:
        """
        Get group_tx details.

        Args:
            group_id: Group Tx ID

        Returns:
            Group data including settings (name, index)
        """
        return self._request("GET", f"/moip/group_tx/{group_id}")

    def set_group_tx_name(self, group_id: int, name: str) -> None:
        """
        Set group_tx name (shown in telnet ?Name=1).

        Args:
            group_id: Group Tx ID
            name: New name
        """
        self._request("PUT", f"/moip/group_tx/{group_id}", json={"settings": {"name": name}})

    def get_all_units_detailed(self) -> list[dict]:
        """
        Get detailed information for all units.

        Returns:
            List of unit data dictionaries
        """
        unit_ids = self.get_unit_ids()
        units = []
        for unit_id in unit_ids:
            try:
                unit = self.get_unit(unit_id)
                units.append(unit)
            except Exception:
                pass
        return units

    def get_all_group_rx_detailed(self) -> list[dict]:
        """
        Get detailed information for all receiver groups.

        Returns:
            List of group_rx data dictionaries
        """
        group_ids = self.get_group_rx_ids()
        groups = []
        for group_id in group_ids:
            try:
                group = self.get_group_rx(group_id)
                groups.append(group)
            except Exception:
                pass
        return groups

    def get_all_group_tx_detailed(self) -> list[dict]:
        """
        Get detailed information for all transmitter groups.

        Returns:
            List of group_tx data dictionaries
        """
        group_ids = self.get_group_tx_ids()
        groups = []
        for group_id in group_ids:
            try:
                group = self.get_group_tx(group_id)
                groups.append(group)
            except Exception:
                pass
        return groups

    def _get_video_tx_id(self, tx_index: int) -> Optional[int]:
        """
        Get the internal video_tx ID for a transmitter index.

        Args:
            tx_index: Transmitter index (1-based)

        Returns:
            video_tx ID or None if not found
        """
        groups = self.get_all_group_tx_detailed()
        for g in groups:
            if g.get("settings", {}).get("index") == tx_index:
                return g.get("associations", {}).get("video_tx")
        return None

    def get_video_tx(self, tx_index: int) -> dict:
        """
        Get video statistics for a transmitter.

        Args:
            tx_index: Transmitter index (1-based)

        Returns:
            Video stats including resolution, frame_rate, color_depth, etc.
        """
        video_tx_id = self._get_video_tx_id(tx_index)
        if not video_tx_id:
            return {"status": {}, "error": "No video_tx found for this transmitter"}
        return self._request("GET", f"/moip/video_tx/{video_tx_id}")

    def get_video_tx_preview(self, tx_index: int) -> bytes:
        """
        Get JPEG preview thumbnail for a transmitter.

        Args:
            tx_index: Transmitter index (1-based)

        Returns:
            JPEG image bytes
        """
        video_tx_id = self._get_video_tx_id(tx_index)
        if not video_tx_id:
            raise ValueError("No video_tx found for this transmitter")

        token = self._ensure_token()
        headers = {"Authorization": f"Bearer {token}"}

        with self._get_client() as client:
            response = client.get(
                f"{self.base_url}/moip/video_tx/{video_tx_id}/preview",
                headers=headers
            )
            response.raise_for_status()
            return response.content

    def get_audio_tx(self, tx_id: int) -> dict:
        """
        Get audio statistics for a transmitter.

        Args:
            tx_id: Transmitter index (1-based)

        Returns:
            Audio stats
        """
        return self._request("GET", f"/moip/audio_tx/{tx_id}")

    def _get_video_rx_id(self, rx_index: int) -> Optional[int]:
        """
        Get the internal video_rx ID for a receiver index.

        Args:
            rx_index: Receiver index (1-based)

        Returns:
            video_rx ID or None if not found
        """
        groups = self.get_all_group_rx_detailed()
        for g in groups:
            if g.get("settings", {}).get("index") == rx_index:
                return g.get("associations", {}).get("video_rx")
        return None

    def get_video_rx(self, rx_index: int) -> dict:
        """
        Get video settings and status for a receiver.

        Args:
            rx_index: Receiver index (1-based)

        Returns:
            Video settings including resolution, supported_resolution, hdcp, etc.
        """
        video_rx_id = self._get_video_rx_id(rx_index)
        if not video_rx_id:
            return {"settings": {}, "error": "No video_rx found for this receiver"}
        return self._request("GET", f"/moip/video_rx/{video_rx_id}")

    def set_video_rx_resolution(self, rx_index: int, resolution: str) -> dict:
        """
        Set output resolution for a receiver.

        Args:
            rx_index: Receiver index (1-based)
            resolution: Resolution setting (e.g., 'passthrough', 'fhd1080p60', 'uhd2160p60')

        Returns:
            Updated video_rx data
        """
        video_rx_id = self._get_video_rx_id(rx_index)
        if not video_rx_id:
            raise ValueError(f"No video_rx found for receiver {rx_index}")
        return self._request("PUT", f"/moip/video_rx/{video_rx_id}",
                           json={"settings": {"resolution": resolution}})

    def set_video_rx_hdcp(self, rx_index: int, hdcp: str) -> dict:
        """
        Set HDCP mode for a receiver.

        Args:
            rx_index: Receiver index (1-based)
            hdcp: HDCP mode ('passthrough', 'hdcp14', 'hdcp22')

        Returns:
            Updated video_rx data
        """
        video_rx_id = self._get_video_rx_id(rx_index)
        if not video_rx_id:
            raise ValueError(f"No video_rx found for receiver {rx_index}")
        return self._request("PUT", f"/moip/video_rx/{video_rx_id}",
                           json={"settings": {"hdcp": hdcp}})
