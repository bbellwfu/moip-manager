"""Data models for MoIP devices and operations."""
from typing import Optional
from pydantic import BaseModel, Field


class DeviceCounts(BaseModel):
    """Device count summary."""
    tx_count: int = Field(description="Number of transmitters")
    rx_count: int = Field(description="Number of receivers")


class Transmitter(BaseModel):
    """Transmitter device model."""
    id: int = Field(description="Transmitter number (1-based)")
    name: str = Field(description="Display name")
    mac: Optional[str] = Field(default=None, description="MAC address")
    ip: Optional[str] = Field(default=None, description="APIPA IP address")
    model: Optional[str] = Field(default=None, description="Device model")
    unit_id: Optional[int] = Field(default=None, description="API unit ID")
    group_id: Optional[int] = Field(default=None, description="API group_tx ID")
    status: str = Field(default="unknown", description="Device status")
    subtype: str = Field(default="av", description="Device subtype: av or audio")
    is_online: bool = Field(default=False, description="Whether device has valid IP (is powered on)")
    receiver_count: int = Field(default=0, description="Number of receivers streaming from this Tx")


class Receiver(BaseModel):
    """Receiver device model."""
    id: int = Field(description="Receiver number (1-based)")
    name: str = Field(description="Display name")
    mac: Optional[str] = Field(default=None, description="MAC address")
    ip: Optional[str] = Field(default=None, description="APIPA IP address")
    model: Optional[str] = Field(default=None, description="Device model")
    unit_id: Optional[int] = Field(default=None, description="API unit ID")
    group_id: Optional[int] = Field(default=None, description="API group_rx ID")
    status: str = Field(default="unknown", description="Device status")
    subtype: str = Field(default="av", description="Device subtype: av, audio, or videowall")
    current_tx: Optional[int] = Field(default=None, description="Currently assigned transmitter (0 = unassigned)")
    current_tx_name: Optional[str] = Field(default=None, description="Name of current transmitter")


class SwitchRequest(BaseModel):
    """Request to switch a receiver to a transmitter."""
    tx: int = Field(description="Transmitter number (0 to unassign)")
    rx: int = Field(description="Receiver number")


class SwitchResponse(BaseModel):
    """Response from a switch operation."""
    success: bool
    message: str
    tx: int
    rx: int


class DeviceNameUpdate(BaseModel):
    """Request to update a device name."""
    name: str = Field(min_length=1, max_length=50, description="New device name")


class RoutingEntry(BaseModel):
    """A single Tx->Rx routing entry."""
    tx: int
    rx: int
    tx_name: Optional[str] = None
    rx_name: Optional[str] = None


class SystemStatus(BaseModel):
    """Overall system status."""
    connected: bool
    tx_count: int
    rx_count: int
    active_streams: int
    controller_ip: str
    controller_firmware: Optional[str] = None


class VideoWall(BaseModel):
    """Video wall configuration."""
    id: int = Field(description="Video wall ID")
    index: int = Field(description="Receiver index for this video wall")
    name: str = Field(description="Display name")
    width: int = Field(description="Number of columns (2-4)")
    height: int = Field(description="Number of rows (2-4)")
    state: str = Field(default="stopped", description="Current state (running/stopped)")
    current_tx: Optional[int] = Field(default=None, description="Currently assigned transmitter index")
    current_tx_name: Optional[str] = Field(default=None, description="Name of current transmitter")


class VideoWallUpdate(BaseModel):
    """Request to update video wall settings."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=50)
    width: Optional[int] = Field(default=None, ge=2, le=4)
    height: Optional[int] = Field(default=None, ge=2, le=4)
    tx: Optional[int] = Field(default=None, ge=0, description="Transmitter index (0 to unassign)")
