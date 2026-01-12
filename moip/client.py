"""Telnet client for Binary MoIP controller."""
import socket
import re
from typing import Optional
from .models import DeviceCounts, Transmitter, Receiver, RoutingEntry


class MoIPClient:
    """Client for communicating with Binary MoIP controller via Telnet."""

    def __init__(self, host: str, port: int = 23, timeout: float = 5.0):
        """
        Initialize MoIP client.

        Args:
            host: MoIP controller IP address
            port: Telnet port (default 23)
            timeout: Socket timeout in seconds
        """
        self.host = host
        self.port = port
        self.timeout = timeout

    def _send_command(self, command: str) -> str:
        """
        Send a command and return the response.

        Args:
            command: Command to send (without newline)

        Returns:
            Response string
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(self.timeout)
            sock.connect((self.host, self.port))

            # Send command with newline
            sock.sendall(f"{command}\n".encode())

            # Read response
            response = b""
            while True:
                try:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    response += chunk
                    # Check if we've received complete response
                    if b"\n" in chunk or b"#Error" in response:
                        break
                except socket.timeout:
                    break

            return response.decode().strip()

    def switch(self, tx: int, rx: int) -> bool:
        """
        Switch a receiver to a transmitter.

        Args:
            tx: Transmitter number (0 to unassign)
            rx: Receiver number

        Returns:
            True if successful
        """
        response = self._send_command(f"!Switch={tx},{rx}")
        return "OK" in response

    def get_device_counts(self) -> DeviceCounts:
        """
        Get the count of transmitters and receivers.

        Returns:
            DeviceCounts with tx_count and rx_count
        """
        response = self._send_command("?Devices")
        # Response format: ?Devices=7,10
        match = re.search(r"\?Devices=(\d+),(\d+)", response)
        if match:
            return DeviceCounts(tx_count=int(match.group(1)), rx_count=int(match.group(2)))
        return DeviceCounts(tx_count=0, rx_count=0)

    def get_routing(self) -> list[RoutingEntry]:
        """
        Get current Tx->Rx routing assignments.

        Returns:
            List of RoutingEntry objects
        """
        response = self._send_command("?Receivers")
        # Response format: ?Receivers=1:10,1:2,2:8,...
        entries = []
        match = re.search(r"\?Receivers=(.+)", response)
        if match:
            pairs = match.group(1).split(",")
            for pair in pairs:
                parts = pair.split(":")
                if len(parts) == 2:
                    entries.append(RoutingEntry(
                        tx=int(parts[0]),
                        rx=int(parts[1])
                    ))
        return entries

    def get_transmitter_names(self) -> list[Transmitter]:
        """
        Get list of transmitters with names.

        Returns:
            List of Transmitter objects
        """
        response = self._send_command("?Name=1")
        # Response format: ?Name=1,1,AppleTV\n?Name=1,2,Roku TV\n...
        transmitters = []
        for line in response.split("\n"):
            match = re.search(r"\?Name=1,(\d+),(.+)", line)
            if match:
                transmitters.append(Transmitter(
                    id=int(match.group(1)),
                    name=match.group(2).strip()
                ))
        return transmitters

    def get_receiver_names(self) -> list[Receiver]:
        """
        Get list of receivers with names.

        Returns:
            List of Receiver objects
        """
        response = self._send_command("?Name=0")
        # Response format: ?Name=0,1,Rec Room\n?Name=0,2,NewRx\n...
        receivers = []
        for line in response.split("\n"):
            match = re.search(r"\?Name=0,(\d+),(.+)", line)
            if match:
                receivers.append(Receiver(
                    id=int(match.group(1)),
                    name=match.group(2).strip()
                ))
        return receivers

    def get_all_transmitters(self) -> list[Transmitter]:
        """
        Get all transmitters with routing info.

        Returns:
            List of Transmitter objects with receiver counts
        """
        counts = self.get_device_counts()
        names = {tx.id: tx.name for tx in self.get_transmitter_names()}
        routing = self.get_routing()

        # Count receivers per transmitter
        rx_counts = {}
        for entry in routing:
            if entry.tx > 0:
                rx_counts[entry.tx] = rx_counts.get(entry.tx, 0) + 1

        transmitters = []
        for i in range(1, counts.tx_count + 1):
            transmitters.append(Transmitter(
                id=i,
                name=names.get(i, f"Tx{i}"),
                receiver_count=rx_counts.get(i, 0),
                status="streaming" if rx_counts.get(i, 0) > 0 else "idle"
            ))
        return transmitters

    def get_all_receivers(self) -> list[Receiver]:
        """
        Get all receivers with current source info.

        Returns:
            List of Receiver objects with current_tx
        """
        counts = self.get_device_counts()
        names = {rx.id: rx.name for rx in self.get_receiver_names()}
        tx_names = {tx.id: tx.name for tx in self.get_transmitter_names()}
        routing = self.get_routing()

        # Build routing map
        routing_map = {entry.rx: entry.tx for entry in routing}

        receivers = []
        for i in range(1, counts.rx_count + 1):
            current_tx = routing_map.get(i, 0)
            receivers.append(Receiver(
                id=i,
                name=names.get(i, f"Rx{i}"),
                current_tx=current_tx if current_tx > 0 else None,
                current_tx_name=tx_names.get(current_tx) if current_tx > 0 else None,
                status="streaming" if current_tx > 0 else "idle"
            ))
        return receivers

    def send_raw(self, command: str) -> str:
        """
        Send a raw command and return the response.

        Args:
            command: Raw command string

        Returns:
            Raw response string
        """
        return self._send_command(command)

    # --- CEC TV Control Commands ---

    def cec_power_on(self, rx: int) -> bool:
        """
        Send CEC Power On (Image View On) to TV connected to receiver.

        Args:
            rx: Receiver number

        Returns:
            True if command accepted
        """
        response = self._send_command(f"!CEC={rx},04")
        return "OK" in response

    def cec_power_off(self, rx: int) -> bool:
        """
        Send CEC Power Off (Standby) to TV connected to receiver.

        Args:
            rx: Receiver number

        Returns:
            True if command accepted
        """
        response = self._send_command(f"!CEC={rx},36")
        return "OK" in response

    def cec_volume_up(self, rx: int) -> bool:
        """
        Send CEC Volume Up to TV/AVR connected to receiver.

        Args:
            rx: Receiver number

        Returns:
            True if command accepted
        """
        # Send key press, then key release
        response1 = self._send_command(f"!CEC={rx},44 41")
        response2 = self._send_command(f"!CEC={rx},45")
        return "OK" in response1 and "OK" in response2

    def cec_volume_down(self, rx: int) -> bool:
        """
        Send CEC Volume Down to TV/AVR connected to receiver.

        Args:
            rx: Receiver number

        Returns:
            True if command accepted
        """
        response1 = self._send_command(f"!CEC={rx},44 42")
        response2 = self._send_command(f"!CEC={rx},45")
        return "OK" in response1 and "OK" in response2

    def cec_mute(self, rx: int) -> bool:
        """
        Send CEC Mute Toggle to TV/AVR connected to receiver.

        Args:
            rx: Receiver number

        Returns:
            True if command accepted
        """
        response1 = self._send_command(f"!CEC={rx},44 43")
        response2 = self._send_command(f"!CEC={rx},45")
        return "OK" in response1 and "OK" in response2
